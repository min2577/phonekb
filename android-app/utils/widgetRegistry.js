/**
 * widgetRegistry.js - widget 类型注册表
 *
 * 未来新增 widget 只需要:
 *   1) 在这里加一条 widgetMeta(type / title / icon)
 *   2) 在 components/ 加一个 PanelXxx.vue 组件
 *   3) 在 panel.vue 的 v-if 链加一个分支(或后续阶段改为 component :is)
 *
 * 注意:本文件不引入 Vue 组件(避免循环依赖),组件导入在 panel.vue 里完成
 */

export const widgetMeta = [
  { type: 'key-grid',      title: '快捷键',   icon: '⚡', description: '4×4 按键网格' },
  { type: 'text-input',    title: '文字输入', icon: '⌨', description: '输入框 + 发送按钮' },
  { type: 'mouse-control', title: '鼠标控制', icon: '🖱', description: '触摸板 + 操作按钮' },
  { type: 'volume-control', title: '音量控制', icon: '🔊', description: '音量增减 + 静音' },
  { type: 'full-keyboard',  title: '大键盘',   icon: '⌨', description: 'F1-F12 + 全键盘 + 自定义快捷行' },
  { type: 'codex-micro', title: 'Codex Micro', icon: '◉', description: '实体键盘式 Codex 任务控制台' },
  { type: 'gamepad', title: '自定义手柄', icon: '🎮', description: '横屏游戏手柄控件(摇杆/ABXY/dpad)' },
  { type: 'jianying-workbench', title: '剪映工作台', icon: '剪', description: '可编排的时间轴触控工作台' },
  { type: 'focus-mode', title: '专注模式', icon: '◐', description: '正计时 / 倒计时 / 严格锁机 / 白名单' },
]

export function findMeta(type) {
  return widgetMeta.find(function (m) { return m.type === type }) || null
}

export function listAvailableTypes() {
  return widgetMeta.map(function (m) { return m.type })
}

// 快速构造一个新 widget 实例(加入 layout 时用)
export function newWidgetInstance(type) {
  const m = findMeta(type)
  if (!m) return null
  return {
    id: 'w-' + type + '-' + Date.now().toString(36),
    type: m.type,
    title: m.title,
    icon: m.icon,
    visible: true,
    collapsed: false,
    order: 0,
  }
}
