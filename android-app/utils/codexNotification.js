export const POST_NOTIFICATIONS_PERMISSION = 'android.permission.POST_NOTIFICATIONS'

let permissionRequest = null

function androidSdkInt() {
  try {
    if (typeof plus === 'undefined' || !plus.android) return 0
    const Build = plus.android.importClass('android.os.Build')
    return Number(plus.android.getAttribute(Build.VERSION, 'SDK_INT') || 0)
  } catch (e) {
    return 0
  }
}

export function requestCodexNotificationPermission() {
  if (permissionRequest) return permissionRequest
  if (typeof plus === 'undefined' || !plus.android || typeof plus.android.requestPermissions !== 'function') {
    return Promise.resolve(false)
  }
  const sdk = androidSdkInt()
  if (sdk && sdk < 33) return Promise.resolve(true)

  permissionRequest = new Promise(function(resolve) {
    plus.android.requestPermissions([POST_NOTIFICATIONS_PERMISSION], function(result) {
      const denied = (result && result.deniedPresent || []).concat(result && result.deniedAlways || [])
      resolve(denied.indexOf(POST_NOTIFICATIONS_PERMISSION) < 0)
    }, function() {
      resolve(false)
    })
  })
  return permissionRequest
}

export function buildTaskNotification(task) {
  const state = String(task && task.state || '')
  const completed = state === 'completed'
  const cancelled = state === 'cancelled'
  return {
    title: completed ? 'Codex 任务完成' : (cancelled ? 'Codex 任务已停止' : 'Codex 任务失败'),
    content: String(task && task.name || (completed ? '任务已完成' : (cancelled ? '任务已停止' : '任务执行失败'))),
    payload: {
      action: 'codex_result',
      slot: Number(task && task.slot || 0),
      task_id: String(task && task.task_id || ''),
    },
  }
}

export function playCodexTerminalSound(state) {
  const counts = { completed: 1, cancelled: 2, failed: 3 }
  const count = counts[String(state || '')]
  if (!count) return false
  try {
    if (typeof plus === 'undefined' || !plus.device || typeof plus.device.beep !== 'function') return false
    plus.device.beep(count)
    return true
  } catch (e) {
    return false
  }
}

export function playCodexInputSound() {
  try {
    if (typeof plus === 'undefined' || !plus.device || typeof plus.device.beep !== 'function') return false
    plus.device.beep(4)
    return true
  } catch (e) {
    return false
  }
}

export function buildInputNotification(binding) {
  const slot = Number(binding && binding.slot || 0)
  return {
    title: 'Codex 等待输入',
    content: String(binding && binding.title || (slot ? ('任务槽 ' + slot + ' 需要你的输入') : '有任务需要你的输入')),
    payload: {
      action: 'codex_user_input',
      slot: slot,
      thread_id: String(binding && binding.thread_id || ''),
      attention_id: String(binding && binding.attention_id || ''),
    },
  }
}

export function buildApprovalNotification(approval, binding) {
  const slot = Number(approval && approval.slot || 0)
  return {
    title: 'Codex 等待确认',
    content: String(binding && binding.title || (slot ? ('任务槽 ' + slot + ' 等待批准') : '有任务等待批准')),
    payload: {
      action: 'codex_approval',
      slot: slot,
      thread_id: String(approval && approval.thread_id || ''),
      fingerprint: String(approval && approval.fingerprint || ''),
    },
  }
}

export function postLocalNotification(notification, options) {
  if (!notification || !notification.content) return false
  try {
    if (typeof plus === 'undefined' || !plus.push || typeof plus.push.createMessage !== 'function') return false
    plus.push.createMessage(notification.content, JSON.stringify(notification.payload || {}), {
      title: notification.title || 'Codex',
      cover: false,
      sound: options && options.silent ? 'none' : 'system',
      when: Date.now(),
    })
    return true
  } catch (e) {
    return false
  }
}
