/**
 * widgetConfig.js - 面板组件配置
 *
 * 第二阶段:增加编辑能力(reorder / setVisible)
 *
 * 字段约定(不变):
 *   id        实例 id
 *   type      组件类型
 *   title     卡片标题
 *   icon      卡片图标
 *   collapsed 是否收起
 *   visible   是否在面板首页显示(true = 显示,false = 隐藏)
 *   order     排序(数字小在前)
 *
 * 存储:
 *   key = phonekb.panel.widgets
 *   value = widgets 数组
 *   额外维护 SCHEMA_VERSION,老数据自动迁移
 */
export const STORAGE_KEY = 'phonekb.panel.widgets'
export const SCHEMA_VERSION = 2

// 默认配置(第一次启动 / 用户清空时用)
export const DEFAULT_WIDGETS = [
  {
    id: 'w-key',
    type: 'key-grid',
    title: '快捷键',
    icon: '⚡',
    collapsed: false,
    visible: true,
    order: 0,
  },
  {
    id: 'w-text',
    type: 'text-input',
    title: '文字输入',
    icon: '⌨',
    collapsed: false,
    visible: true,
    order: 1,
  },
  {
    id: 'w-mouse',
    type: 'mouse-control',
    title: '鼠标控制',
    icon: '🖱',
    collapsed: false,
    visible: true,
    order: 2,
  },
]

function byOrder(a, b) {
  return (a.order || 0) - (b.order || 0)
}

function ensureFields(w) {
  // 防御:缺字段时填默认值(老数据迁移)
  return {
    id: w.id,
    type: w.type,
    title: w.title || w.type || '',
    icon: w.icon || '◇',
    collapsed: !!w.collapsed,
    visible: w.visible !== false,
    order: typeof w.order === 'number' ? w.order : 0,
  }
}

// 合法 type 列表(用于过滤历史残留 / 乱改 storage 造成的无效 widget)
// 新增 widget 时只需要往这里加一行,旧的坏数据下次启动会被自动清理
const VALID_TYPES = [
  'key-grid',
  'text-input',
  'mouse-control',
  'volume-control',
  'full-keyboard',
  'codex-micro',
  'gamepad',
  'jianying-workbench',
]

// 读本地存储
// 返回值:已按 order 排序、字段齐全、已清理无效 type 的数组
export function loadWidgets() {
  try {
    const cached = uni.getStorageSync(STORAGE_KEY)
    if (Array.isArray(cached) && cached.length > 0) {
      // 校验:必须包含三个默认 type 才算有效(防止外部乱改导致丢失 widget)
      const required = ['key-grid', 'text-input', 'mouse-control']
      const haveTypes = cached.map(function (w) { return w && w.type })
      const ok = required.every(function (t) { return haveTypes.indexOf(t) >= 0 })
      if (ok) {
        // 自动清理:任何 type 不在 VALID_TYPES 里的 widget 都视为历史残留
        // (例如之前的 'controller'、空 type、拼写错误的 type 等)
        const cleaned = cached.filter(function (w) {
          return w && w.type && VALID_TYPES.indexOf(w.type) >= 0
        })
        // 如果清理掉了东西,立刻把干净的列表回写 storage,避免下次再清理
        if (cleaned.length !== cached.length) {
          try { uni.setStorageSync(STORAGE_KEY, cleaned) } catch (e) {}
        }
        return cleaned.map(ensureFields).sort(byOrder)
      }
    }
  } catch (e) {
    console.warn('[widgetConfig] load failed', e)
  }
  return DEFAULT_WIDGETS.slice().sort(byOrder)
}

// 保存整个数组
export function saveWidgets(widgets) {
  try {
    uni.setStorageSync(STORAGE_KEY, widgets)
    return true
  } catch (e) {
    console.warn('[widgetConfig] save failed', e)
    return false
  }
}

// 单字段更新(避免每次重写整个数组)
export function updateCollapsed(id, collapsed) {
  const list = loadWidgets()
  const found = list.find(function (w) { return w.id === id })
  if (!found) return list
  found.collapsed = !!collapsed
  saveWidgets(list)
  return list
}

// 第二阶段新增:重新排序
// ids 为新的完整顺序(从第一个到最后一个)
// 内部按顺序重写每个 widget 的 order,然后保存
export function reorder(ids) {
  const list = loadWidgets()
  const map = {}
  list.forEach(function (w) { map[w.id] = w })
  const next = ids.map(function (id, idx) {
    const w = map[id]
    if (!w) return null
    return Object.assign({}, w, { order: idx })
  }).filter(Boolean)
  // 容错:如果 ids 数量少于 list,补回缺失项到末尾
  if (next.length < list.length) {
    const usedIds = {}
    next.forEach(function (w) { usedIds[w.id] = true })
    list.forEach(function (w) {
      if (!usedIds[w.id]) {
        next.push(Object.assign({}, w, { order: next.length }))
      }
    })
  }
  saveWidgets(next)
  return next
}

// 第二阶段新增:切换 visible
export function setVisible(id, visible) {
  const list = loadWidgets()
  const found = list.find(function (w) { return w.id === id })
  if (!found) return list
  found.visible = !!visible
  saveWidgets(list)
  return list
}

// 找出指定 type 的 widget 配置
export function findByType(type) {
  const list = loadWidgets()
  return list.find(function (w) { return w.type === type }) || null
}

// 工具:过滤出可见的 widgets(给 panel.vue 用)
export function filterVisible(widgets) {
  return (widgets || []).filter(function (w) { return w && w.visible !== false })
}
