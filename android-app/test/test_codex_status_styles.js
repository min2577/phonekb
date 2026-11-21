var fs = require('fs')
var path = require('path')

var source = fs.readFileSync(path.resolve(__dirname, '../components/PanelCodexMicro.vue'), 'utf8')
var failed = 0

function assert(condition, message) {
  if (condition) console.log('  PASS', message)
  else { console.log('  FAIL', message); failed++ }
}

var cardStates = ['running', 'starting', 'waiting_input', 'completed', 'attention', 'failed', 'cancelled']
cardStates.forEach(function(state) {
  assert(source.indexOf('.agent-key.state-' + state) >= 0, state + ' card background is explicitly scoped')
})

assert(!/^\.state-(running|starting|waiting_input|completed|attention|failed|cancelled)\b/m.test(source), 'status backgrounds do not leak through broad selectors')
assert(source.indexOf('.summary-bar.state-running') >= 0, 'summary status bar keeps an explicit running color')
assert(source.indexOf('.summary-bar.state-waiting_input') >= 0, 'input request summary bar keeps an explicit amber color')
assert(source.indexOf('.legend-dot.state-completed') >= 0, 'legend status dot keeps an explicit completed color')
assert(source.indexOf("state === 'waiting_input'") >= 0, 'input request remains an active task until answered')

if (failed) process.exit(1)
console.log('\n[test] ALL PASSED')
