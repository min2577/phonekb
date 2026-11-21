export const STORAGE_KEY = 'phonekb.codex.micro.keymap.v1'
const STORAGE_VERSION_KEY = 'phonekb.codex.micro.keymap.version'
const STORAGE_VERSION = 2

export const CONTROL_GROUPS = [
  {
    id: 'dials',
    label: '旋钮',
    controls: [
      { id: 'reasoning_dial', label: '左上旋钮', position: '左上' },
      { id: 'workflow_dial', label: '右上旋钮', position: '右上' },
    ],
  },
  {
    id: 'actions',
    label: '功能键',
    controls: [
      { id: 'action_skill', label: '技能键', position: '第三排左一' },
      { id: 'action_approve', label: '批准键', position: '第三排左二' },
      { id: 'action_reject', label: '拒绝键', position: '第三排左三' },
      { id: 'action_switch', label: '右上功能键', position: '第三排右一' },
      { id: 'action_refresh', label: '左下圆键', position: '第四排左一' },
      { id: 'action_voice', label: '中间长键', position: '第四排中间' },
      { id: 'action_new', label: '右下功能键', position: '第四排右一' },
    ],
  },
]

export const ACTION_OPTIONS = [
  { id: 'reasoning', label: '推理强度', symbol: '推', hint: '切换当前任务的推理强度' },
  { id: 'workflow', label: '工作流', symbol: '流', hint: '循环切换代码工作流' },
  { id: 'skill', label: '技能', symbol: 'ϟ', hint: '打开工作流选择菜单' },
  { id: 'approve', label: '批准', symbol: '✓', hint: '批准当前待确认操作' },
  { id: 'reject', label: '拒绝', symbol: '×', hint: '拒绝当前待确认操作' },
  { id: 'switch_task', label: '切换', symbol: '↗', hint: '打开选中任务或查看结果' },
  { id: 'refresh', label: '刷新', symbol: '↻', hint: '同步电脑端 Codex 状态' },
  { id: 'voice', label: '按住说话', symbol: '麦', hint: '按住进行电脑端语音输入', hold: true },
  { id: 'new_task', label: '新任务', symbol: '+', hint: '打开 Codex 空白任务页面' },
  { id: 'submit_enter', label: 'Enter 回车', symbol: '↵', hint: '发送 Codex 输入框中的内容' },
  { id: 'test_input', label: '测试输入', symbol: '测', hint: '向 Codex 输入框发送测试文字' },
  { id: 'bind_current', label: '绑定当前任务', symbol: '绑', hint: '绑定电脑当前任务到选中槽' },
  { id: 'cancel', label: '停止任务', symbol: '■', hint: '停止选中任务' },
]

export const DEFAULT_KEYMAP = {
  reasoning_dial: 'reasoning',
  workflow_dial: 'workflow',
  action_skill: 'skill',
  action_approve: 'approve',
  action_reject: 'reject',
  action_switch: 'new_task',
  action_refresh: 'refresh',
  action_voice: 'voice',
  action_new: 'submit_enter',
}

const ACTION_IDS = ACTION_OPTIONS.map(function(item) { return item.id })
const CONTROL_IDS = CONTROL_GROUPS.reduce(function(ids, group) {
  return ids.concat(group.controls.map(function(control) { return control.id }))
}, [])

export function normalizeKeyMap(value) {
  const source = value && typeof value === 'object' ? value : {}
  const result = {}
  CONTROL_IDS.forEach(function(controlId) {
    const action = source[controlId]
    result[controlId] = ACTION_IDS.indexOf(action) >= 0 ? action : DEFAULT_KEYMAP[controlId]
  })
  return result
}

export function loadCodexMicroKeyMap() {
  try {
    let cached = uni.getStorageSync(STORAGE_KEY)
    const version = Number(uni.getStorageSync(STORAGE_VERSION_KEY) || 1)
    if (cached && version < STORAGE_VERSION) {
      cached = Object.assign({}, cached)
      if (cached.action_switch === 'switch_task' && cached.action_new === 'new_task') {
        cached.action_switch = 'new_task'
        cached.action_new = 'submit_enter'
      }
      uni.setStorageSync(STORAGE_KEY, cached)
      uni.setStorageSync(STORAGE_VERSION_KEY, STORAGE_VERSION)
    }
    return normalizeKeyMap(cached)
  } catch (e) {
    return normalizeKeyMap(DEFAULT_KEYMAP)
  }
}

export function saveCodexMicroKeyMap(value) {
  const normalized = normalizeKeyMap(value)
  try {
    uni.setStorageSync(STORAGE_KEY, normalized)
    uni.setStorageSync(STORAGE_VERSION_KEY, STORAGE_VERSION)
    try { uni.$emit('phonekb:codex-micro-keymap-updated', normalized) } catch (e) {}
    return true
  } catch (e) {
    return false
  }
}

export function resetCodexMicroKeyMap() {
  return saveCodexMicroKeyMap(DEFAULT_KEYMAP)
}

export function getCodexActionMeta(actionId) {
  return ACTION_OPTIONS.find(function(item) { return item.id === actionId }) || ACTION_OPTIONS[0]
}
