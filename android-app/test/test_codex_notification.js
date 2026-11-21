var path = require('path')
var url = require('url')
var register = require('node:module').register

register('./alias-loader.mjs', { parentURL: url.pathToFileURL(__filename).href })

;(async function() {
  var file = path.resolve(__dirname, '../utils/codexNotification.js')
  var mod = await import(url.pathToFileURL(file).href)
  var failed = 0

  function assert(condition, message) {
    if (condition) console.log('  PASS', message)
    else { console.log('  FAIL', message); failed++ }
  }

  var completed = mod.buildTaskNotification({ slot: 2, task_id: 'task-2', name: '运行测试', state: 'completed' })
  assert(completed.title === 'Codex 任务完成', 'completed task uses completion title')
  assert(completed.payload.slot === 2 && completed.payload.task_id === 'task-2', 'task payload keeps slot and id')

  var failedTask = mod.buildTaskNotification({ slot: 3, task_id: 'task-3', name: '代码审查', state: 'failed' })
  assert(failedTask.title === 'Codex 任务失败', 'failed task uses failure title')

  var cancelledTask = mod.buildTaskNotification({ slot: 5, task_id: 'task-5', state: 'cancelled' })
  assert(cancelledTask.title === 'Codex 任务已停止', 'cancelled task uses stopped title')
  assert(cancelledTask.content === '任务已停止', 'cancelled task uses stopped fallback content')

  var beepCount = 0
  global.plus = { device: { beep: function(count) { beepCount = count } } }
  assert(mod.playCodexTerminalSound('completed') === true && beepCount === 1, 'completed task plays one beep')
  assert(mod.playCodexTerminalSound('cancelled') === true && beepCount === 2, 'cancelled task plays two beeps')
  assert(mod.playCodexTerminalSound('failed') === true && beepCount === 3, 'failed task plays three beeps')
  assert(mod.playCodexInputSound() === true && beepCount === 4, 'input request plays a distinct four-beep alert')

  var notificationSound = ''
  global.plus.push = { createMessage: function(content, payload, options) { notificationSound = options.sound } }
  assert(mod.postLocalNotification(completed, { silent: true }) === true && notificationSound === 'none', 'terminal notification does not duplicate beep sound')
  delete global.plus

  var approval = mod.buildApprovalNotification(
    { slot: 4, thread_id: 'thread-4', fingerprint: 'fp-4' },
    { title: '修复鼠标问题' }
  )
  assert(approval.title === 'Codex 等待确认', 'approval uses confirmation title')
  assert(approval.content === '修复鼠标问题', 'approval uses bound task title')
  assert(approval.payload.fingerprint === 'fp-4', 'approval payload keeps fingerprint')
  assert(mod.postLocalNotification(approval) === false, 'notification gracefully skips outside app runtime')

  var input = mod.buildInputNotification({ slot: 2, thread_id: 'thread-2', attention_id: 'call-2', title: '等待选择' })
  assert(input.title === 'Codex 等待输入', 'input request uses its own notification title')
  assert(input.payload.attention_id === 'call-2', 'input notification keeps its stable request id')

  if (failed) process.exit(1)
  console.log('\n[test] ALL PASSED')
})().catch(function(error) {
  console.error(error)
  process.exit(1)
})
