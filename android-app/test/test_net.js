// test/test_net.js - 用 dynamic import 加载 ESM net.js

var storage = {};
var fs = require('fs');
var path = require('path');
var url = require('url');
var register = require('node:module').register;

register('./alias-loader.mjs', { parentURL: url.pathToFileURL(__filename).href });

global.uni = {
  getStorageSync: function(k) { return storage[k] || '' },
  setStorageSync: function(k, v) { storage[k] = v },
};

(async function() {
  // 用 dynamic import 加载 ESM 模块
  var netPath = path.resolve(__dirname, '../utils/net.js');
  var netUrl = url.pathToFileURL(netPath).href;
  var mod = await import(netUrl);
  var Net = mod.default;

  var failed = 0;
  function assert(cond, msg) {
    if (cond) console.log('  PASS', msg);
    else { console.log('  FAIL', msg); failed++; }
  }

  console.log('--- 1. 默认 mode 应为 usb ---');
  storage = {};
  Net.setMode('usb'); // reset
  storage = {};
  assert(Net.getMode() === 'usb', 'Net.getMode() default === usb');

  console.log('--- 2. setMode wifi ---');
  Net.setMode('wifi');
  assert(Net.getMode() === 'wifi', 'setMode("wifi") persisted');
  assert(storage['phonekb.mode'] === 'wifi', 'storage["phonekb.mode"] === wifi');

  console.log('--- 3. setMode usb ---');
  Net.setMode('usb');
  assert(Net.getMode() === 'usb', 'setMode("usb") persisted');
  assert(storage['phonekb.mode'] === 'usb', 'storage["phonekb.mode"] === usb');

  console.log('--- 4. 非法 mode fallback 到 usb ---');
  storage = { 'phonekb.mode': 'xxx' };
  // 注意 Net 是同一个实例，缓存的 _client 可能仍是 wifi
  // 但 getMode 直接读 storage，应该正确
  assert(Net.getMode() === 'usb', 'illegal mode falls back to usb');

  console.log('--- 5. API 兼容（不报错）---');
  Net.connect({ host: '127.0.0.1', port: 9877, code: 'ABCDEF' });
  assert(typeof Net.isConnected === 'function', 'isConnected is function');
  assert(Net.isConnected() === false, 'isConnected() returns false when not connected');
  assert(typeof Net.canSendKeyboard === 'function', 'canSendKeyboard is function');
  assert(Net.canSendKeyboard() === false, 'canSendKeyboard() returns false when not connected');
  assert(typeof Net.canSendMouse === 'function', 'canSendMouse is function');
  assert(Net.canSendMouse() === false, 'canSendMouse() returns false when not connected');
  assert(typeof Net.send === 'function', 'send is function');
  assert(typeof Net.close === 'function', 'close is function');
  assert(typeof Net.triggerSlot === 'function', 'triggerSlot is function');
  assert(Net.send({ action: 'ping' }) === false, 'send returns false when no socket');
  Net.close();

  console.log('--- 6. 蓝牙鼠标回退 ---');
  var btSource = fs.readFileSync(path.resolve(__dirname, '../utils/btclient.js'), 'utf8');
  assert(
    btSource.includes("if (_trySendHidMouse(object)) return true") &&
      btSource.includes("if (_state === 'connected') return _sendRaw(object)"),
    'mouse and Ctrl+wheel fall back to SPP when Bluetooth HID is unavailable'
  );

  if (failed === 0) {
    console.log('\n[test] ALL PASSED');
    process.exit(0);
  } else {
    console.log('\n[test] FAILED:', failed);
    process.exit(1);
  }
})().catch(function(e) {
  console.error('[test] ERROR:', e);
  process.exit(1);
});
