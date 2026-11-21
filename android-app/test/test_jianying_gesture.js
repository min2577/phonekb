var path = require('path')
var url = require('url')

;(async function() {
  var file = path.resolve(__dirname, '../utils/jianyingGesture.js')
  var mod = await import(url.pathToFileURL(file).href)
  var failed = 0
  function equal(actual, expected, message) {
    if (actual === expected) console.log('  PASS', message)
    else { console.log('  FAIL', message, '(expected:', expected, 'actual:', actual + ')'); failed++ }
  }

  equal(mod.thresholdFor('stable', 'swipe'), 14, 'stable swipe uses a larger threshold')
  equal(mod.thresholdFor('medium', 'pinch'), 7, 'medium pinch responds without a long delay')
  equal(mod.thresholdFor('sensitive', 'swipe'), 6, 'sensitive swipe uses a smaller threshold')

  equal(mod.clampGestureMultiplier(5), 3, 'gesture multiplier is capped')
  equal(mod.clampGestureMultiplier('bad', 1.2), 1.2, 'invalid gesture multiplier uses its fallback')
  equal(mod.swipeMultiplierForScale(0.5, 1), 2, 'zoomed-out timeline makes one-finger movement faster')
  equal(mod.swipeMultiplierForScale(2, 1), 0.5, 'zoomed-in timeline makes one-finger movement more precise')

  var partial = mod.consumeGestureSteps(10, 14)
  equal(partial.steps, 0, 'partial movement does not trigger')
  equal(partial.remaining, 10, 'partial movement is retained')
  var multi = mod.consumeGestureSteps(70, 14)
  equal(multi.steps, 4, 'one event is capped to four steps')
  equal(multi.remaining, 14, 'capped movement remains queued')
  var reverse = mod.consumeGestureSteps(-31, 14)
  equal(reverse.steps, -2, 'negative movement preserves direction')
  equal(reverse.remaining, -3, 'negative movement preserves remainder')

  equal(mod.scaleForPinch(1, 100, 130), 1.3, 'pinch out expands the local timeline ruler')
  equal(mod.scaleForPinch(1, 100, 70), 0.7, 'pinch in contracts the local timeline ruler')
  equal(mod.scaleForPinch(3, 100, 200), 3.2, 'timeline ruler scale is capped')
  equal(mod.scaleForPinch(0.6, 100, 20), 0.42, 'timeline ruler scale keeps a readable minimum')
  equal(mod.scaleForPinch(1, 100, 120, 0.42, 3.2, 2), 1.44, 'pinch multiplier changes local zoom response')

  var shortcut = mod.messageForGestureAction({ type: 'shortcut', modifiers: ['shift'], key: 'right' })
  equal(shortcut.action, 'simulate_key', 'shortcut gestures use generic keyboard simulation')
  equal(shortcut.key, 'right', 'shortcut gesture keeps the main key')
  var zoom = mod.messageForGestureAction({ type: 'mouse_zoom', delta: 120 })
  equal(zoom.action, 'mouse', 'timeline zoom uses generic mouse transport')
  equal(zoom.op, 'zoom', 'timeline zoom maps to Ctrl plus wheel')
  equal(zoom.delta, 120, 'timeline zoom preserves direction')
  equal(mod.messageForGestureAction({ type: 'mouse_zoom', delta: -120 }, 3).delta, -360, 'multiple pinch steps are coalesced into one wheel message')
  var wheel = mod.messageForGestureAction({ type: 'mouse_wheel', delta: -120 })
  equal(wheel.op, 'wheel', 'one-finger timeline swipe uses normal mouse wheel input')
  equal(wheel.delta, -120, 'timeline wheel input preserves direction')
  equal(mod.messageForGestureAction({ type: 'none' }), null, 'disabled gesture sends nothing')

  var distance = mod.touchDistance([{ clientX: 0, clientY: 0 }, { clientX: 3, clientY: 4 }])
  equal(distance, 5, 'two-finger distance uses both axes')
  equal(mod.touchDistance([{ pageX: 2, pageY: 3 }, { pageX: 8, pageY: 11 }]), 10, 'touch coordinates fall back to page values on App-Plus')

  if (failed) process.exit(1)
  console.log('\n[test] ALL PASSED')
})().catch(function(error) {
  console.error(error)
  process.exit(1)
})
