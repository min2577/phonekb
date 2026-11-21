/**
 * componentRegistry.js - 面板组件注册表
 *
 * 设计:
 *   - 每个面板组件对应一个 type 字符串(text-input / key-grid / mouse-control ...)
 *   - type 在 panel_schemes.json 的 components[].type 里出现
 *   - 本文件集中注册 "type -> Vue 组件" 的映射
 *   - 新增组件:加一行 import + 一行 componentMap,无需改 panel.vue
 *
 * 命名约定:
 *   - type 用短横线(kebab-case),如 "text-input"
 *   - 组件文件名用 PascalCase,如 PanelTextInput.vue
 *   - 注册表 key 与 type 字符串严格一致
 */
import PanelTextInput from '@/components/PanelTextInput.vue'
import PanelKeyGrid from '@/components/PanelKeyGrid.vue'
import PanelMouseControl from '@/components/PanelMouseControl.vue'
import PanelCodexMicro from '@/components/PanelCodexMicro.vue'
import PanelVolumeControl from '@/components/PanelVolumeControl.vue'
import PanelFullKeyboard from '@/components/PanelFullKeyboard.vue'
import PanelGamepad from '@/components/PanelGamepad.vue'
import PanelJianyingWorkbench from '@/components/PanelJianyingWorkbench.vue'

const componentMap = {
  'text-input': PanelTextInput,
  'key-grid': PanelKeyGrid,
  'mouse-control': PanelMouseControl,
  'codex-micro': PanelCodexMicro,
  'volume-control': PanelVolumeControl,
  'full-keyboard': PanelFullKeyboard,
  'gamepad': PanelGamepad,
  'jianying-workbench': PanelJianyingWorkbench,
}

export function getComponent(type) {
  return componentMap[type] || null
}

export function isKnownType(type) {
  return Object.prototype.hasOwnProperty.call(componentMap, type)
}

export function listTypes() {
  return Object.keys(componentMap)
}

export const componentMeta = {
  'text-input': { name: '文字输入', icon: '⌨️', description: '输入框 + 发送按钮' },
  'key-grid': { name: '快捷键网格', icon: '⚡', description: '来自当前 layout 的按键网格' },
  'mouse-control': { name: '鼠标控制', icon: '🖱', description: '触摸板 + 操作按钮' },
  'codex-micro': { name: 'Codex Micro', icon: '◉', description: '实体键盘式 Codex 任务控制台' },
  'volume-control': { name: '音量控制', icon: '🔊', description: '音量增减和静音' },
  'full-keyboard': { name: '大键盘', icon: '⌨', description: 'F1-F12、全键盘和自定义快捷行' },
  'gamepad': { name: '自定义手柄', icon: '◉', description: '横屏游戏手柄控件(摇杆/ABXY/dpad)' },
  'jianying-workbench': { name: '剪映工作台', icon: '剪', description: '可编排的时间轴触控工作台' },
}

export function getMeta(type) {
  return componentMeta[type] || { name: type, icon: '❓', description: '未知组件' }
}

export default componentMap
