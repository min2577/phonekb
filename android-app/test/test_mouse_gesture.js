var path = require('path');
var url = require('url');

(async function() {
  var modulePath = path.resolve(__dirname, '../utils/mouseGesture.js');
  var gesture = await import(url.pathToFileURL(modulePath).href);
  var failed = 0;

  function assertEqual(actual, expected, message) {
    if (actual === expected) console.log('  PASS', message);
    else {
      console.log('  FAIL', message, '(expected:', expected, 'actual:', actual + ')');
      failed++;
    }
  }

  console.log('--- 滚轮按钮手势换算 ---');
  var upward = gesture.consumeWheelMovement(-18);
  assertEqual(upward.delta, 120, '手指向上滑动发送向上滚轮');
  assertEqual(upward.remainingY, 0, '完整一步不保留余量');

  var downward = gesture.consumeWheelMovement(18);
  assertEqual(downward.delta, -120, '手指向下滑动发送向下滚轮');

  var partial = gesture.consumeWheelMovement(-10);
  assertEqual(partial.delta, 0, '不足一步时暂不发送');
  assertEqual(partial.remainingY, -10, '不足一步的位移会累积');

  var multiStep = gesture.consumeWheelMovement(41);
  assertEqual(multiStep.delta, -240, '一次大幅滑动可发送多格');
  assertEqual(multiStep.remainingY, 5, '多格滚动后保留剩余位移');

  if (failed === 0) {
    console.log('\n[test] ALL PASSED');
    process.exit(0);
  }
  console.log('\n[test] FAILED:', failed);
  process.exit(1);
})().catch(function(error) {
  console.error('[test] ERROR:', error);
  process.exit(1);
});
