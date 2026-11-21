var path = require('path');
var url = require('url');

(async function() {
  var api = await import(url.pathToFileURL(path.resolve(__dirname, '../utils/touchpadController.js')).href);
  var failed = 0;
  function assert(cond, message) {
    if (cond) console.log('  PASS', message);
    else { console.log('  FAIL', message); failed++; }
  }
  function touch(x, y) { return { clientX: x, clientY: y }; }
  function make(options) {
    var actions = [];
    var timers = {};
    var nextTimer = 1;
    var controller = api.createTouchpadController({
      emit: function(action) { actions.push(action); },
      options: Object.assign({ inertia: false }, options || {}),
      setTimeout: function(callback) { var id = nextTimer++; timers[id] = callback; return id; },
      clearTimeout: function(id) { delete timers[id]; },
    });
    return {
      actions: actions,
      controller: controller,
      flushTimers: function() {
        var pending = Object.keys(timers).map(function(id) { return timers[id]; });
        timers = {};
        pending.forEach(function(callback) { callback(); });
      },
    };
  }

  console.log('--- 触控板共享手势 ---');
  var one = make();
  one.controller.start([touch(10, 10)], 1000); one.controller.move([touch(30, 15)], 1020); one.controller.end([], 1040);
  assert(one.actions.length === 1 && one.actions[0].op === 'move' && one.actions[0].dx === 30, '单指移动应用光标灵敏度且不误触点击');

  var tap = make();
  tap.controller.start([touch(1, 1)], 1000); tap.controller.end([], 1100);
  assert(tap.actions.length === 0, '单击会等待双击判定窗口');
  tap.flushTimers();
  assert(tap.actions.length === 1 && tap.actions[0].op === 'click' && tap.actions[0].button === 'left', '单指轻点发送左键');

  var drag = make();
  drag.controller.start([touch(1, 1)], 1000); drag.controller.end([], 1080);
  drag.controller.start([touch(1, 1)], 1200); drag.controller.move([touch(40, 1)], 1240); drag.controller.end([], 1280);
  assert(drag.actions.length === 3 && drag.actions[0].op === 'down' && drag.actions[1].op === 'move' && drag.actions[2].op === 'up', '轻点后再次按住只拖动，不触发双击');

  var doubleTap = make();
  doubleTap.controller.start([touch(1, 1)], 1000); doubleTap.controller.end([], 1080);
  doubleTap.controller.start([touch(1, 1)], 1200); doubleTap.controller.end([], 1280);
  assert(doubleTap.actions.length === 1 && doubleTap.actions[0].op === 'click' && doubleTap.actions[0].count === 2, '连续两次轻点且不移动才发送双击');

  var right = make();
  right.controller.start([touch(0, 0), touch(20, 0)], 1000); right.controller.end([], 1100);
  assert(right.actions.length === 1 && right.actions[0].button === 'right', '双指轻点发送右键');

  var scroll = make();
  scroll.controller.start([touch(0, 0), touch(20, 0)], 1000); scroll.controller.move([touch(0, 20), touch(20, 20)], 1020); scroll.controller.end([], 1040);
  assert(scroll.actions.some(function(a) { return a.op === 'wheel' && a.delta === 120; }), '双指垂直滑动发送自然滚动');

  var horizontal = make();
  horizontal.controller.start([touch(0, 0), touch(20, 0)], 1000); horizontal.controller.move([touch(20, 0), touch(40, 0)], 1020); horizontal.controller.end([], 1040);
  assert(horizontal.actions.some(function(a) { return a.op === 'hwheel'; }), '双指水平滑动发送水平滚动');

  var pinch = make();
  pinch.controller.start([touch(0, 0), touch(20, 0)], 1000); pinch.controller.move([touch(-10, 0), touch(30, 0)], 1020); pinch.controller.end([], 1040);
  assert(pinch.actions.some(function(a) { return a.op === 'zoom' && a.delta > 0; }), '双指张开产生放大动作');

  var three = api.systemGestureFor(3, 0, -80, false);
  var four = api.systemGestureFor(4, -80, 0, false);
  assert(three && three.modifiers[0] === 'win' && three.key === 'tab', '三指上滑打开任务视图');
  assert(four && four.modifiers.indexOf('ctrl') >= 0 && four.key === 'right', '四指横滑切换虚拟桌面');

  if (failed) process.exit(1);
  console.log('\n[test] ALL PASSED');
})().catch(function(error) { console.error('[test] ERROR:', error); process.exit(1); });
