var path = require('path')
var url = require('url')

var shown = []
var hidden = 0
var scheduled = []
var cleared = []
var originalSetTimeout = global.setTimeout
var originalClearTimeout = global.clearTimeout

global.uni = {
  showToast: function(options) { shown.push(options) },
  hideToast: function() { hidden++ },
}
global.setTimeout = function(callback, delay) {
  var timer = { callback: callback, delay: delay }
  scheduled.push(timer)
  return timer
}
global.clearTimeout = function(timer) { cleared.push(timer) }

function assert(condition, message) {
  if (!condition) throw new Error(message)
  console.log('  PASS ' + message)
}

(async function() {
  var modulePath = path.resolve(__dirname, '../utils/transientToast.js')
  var toast = await import(url.pathToFileURL(modulePath).href)

  toast.showTransientToast('当前任务没有待批准请求', 2000)
  assert(shown[0].duration === 2000, 'toast has an explicit two-second duration')
  assert(scheduled[0].delay === 2100, 'fallback hide is scheduled after the toast duration')

  toast.showTransientToast('再次提示', 2000)
  assert(cleared[0] === scheduled[0], 'repeated toast clears the previous hide timer')

  scheduled[1].callback()
  assert(hidden === 1, 'fallback timer actively hides the toast')
})().catch(function(error) {
  console.error('[test] ERROR:', error)
  process.exitCode = 1
}).finally(function() {
  global.setTimeout = originalSetTimeout
  global.clearTimeout = originalClearTimeout
})
