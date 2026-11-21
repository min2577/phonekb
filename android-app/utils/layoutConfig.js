/**
 * layoutConfig.js - 用户面板方案管理
 *
 * 第三阶段:从"单一 widgets 数组"升级为"多 layout + currentLayoutId"
 *
 * 存储:
 *   key = phonekb.panel.layouts
 *   value = layouts 数组
 *   key = phonekb.panel.currentLayoutId
 *   value = string (id)
 *
 * 字段约定(每个 layout):
 *   id        string  唯一 id
 *   name      string  显示名
 *   built_in  bool    true = 默认面板,不可删除
 *   widgets   Widget[]
 *
 * Widget 字段(不变):
 *   id / type / title / icon / visible / collapsed / order
 */

export const LAYOUTS_KEY = 'phonekb.panel.layouts'
export const CURRENT_KEY = 'phonekb.panel.currentLayoutId'
const CODEX_MICRO_MIGRATION_KEY = 'phonekb.panel.codex_micro.v1'

function makeCodexMicroWidget(order) {
  return {
    id: 'w-codex-micro',
    type: 'codex-micro',
    title: 'Codex Micro',
    icon: '◉',
    visible: false,
    collapsed: false,
    order: typeof order === 'number' ? order : 0,
  }
}

// 合法 widget type 列表(用于过滤历史残留 / 乱改 storage 造成的无效 widget)
// 与 utils/widgetRegistry.js 的 widgetMeta 保持一致
// 新增 widget 时记得在这里也加一行
const VALID_WIDGET_TYPES = [
  'key-grid',
  'text-input',
  'mouse-control',
  'volume-control',
  'full-keyboard',
  'codex-micro',
  'gamepad',
  'jianying-workbench',
  'focus-mode',
]

// 默认布局(只有这一份,first run 用)
export const DEFAULT_LAYOUT = {
  id: 'default',
  name: '默认面板',
  built_in: true,
  widgets: [
    { id: "w-key", type: "key-grid", title: "快捷键", icon: "⚡", visible: true, collapsed: false, order: 0 },
    { id: "w-text", type: "text-input", title: "文字输入", icon: "⌨", visible: true, collapsed: false, order: 1 },
    { id: "w-mouse", type: "mouse-control", title: "鼠标控制", icon: "🖱", visible: true, collapsed: false, order: 2 },
    makeCodexMicroWidget(3),
  ],
}

function _ensureWidget(w) {
  return {
    id: w.id,
    type: w.type,
    title: w.title || w.type || "",
    icon: w.icon || "◇",
    visible: w.visible !== false,
    collapsed: !!w.collapsed,
    order: typeof w.order === "number" ? w.order : 0,
  }
}

function genId(prefix) {
  return prefix + '-' + Date.now().toString(36) + '-' + Math.floor(Math.random() * 10000).toString(36)
}

function migrateCodexMicro(layouts) {
  let migrated = false
  try { migrated = uni.getStorageSync(CODEX_MICRO_MIGRATION_KEY) === true } catch (e) {}
  if (migrated) return layouts

  let changed = false
  const next = (layouts || []).map(function (layout) {
    const widgets = (layout.widgets || []).slice()
    if (!widgets.some(function (widget) { return widget && widget.type === 'codex-micro' })) {
      widgets.push(makeCodexMicroWidget(widgets.length))
      changed = true
    }
    return Object.assign({}, layout, { widgets: widgets })
  })

  try {
    if (changed) uni.setStorageSync(LAYOUTS_KEY, next)
    uni.setStorageSync(CODEX_MICRO_MIGRATION_KEY, true)
  } catch (e) {
    console.warn('[layoutConfig] Codex Micro migration failed', e)
  }
  return next
}

// ===== layouts CRUD =====

export function loadLayouts() {
  try {
    const cached = uni.getStorageSync(LAYOUTS_KEY)
    if (Array.isArray(cached) && cached.length > 0) {
      // 每个 layout 内部 widgets 补齐字段
      const normalized = cached.map(function (l) {
        return {
          id: l.id,
          name: l.name || '未命名',
          built_in: !!l.built_in,
          widgets: (l.widgets || []).map(_ensureWidget).sort(function (a, b) {
            return (a.order || 0) - (b.order || 0)
          }),
        }
      })
      // 自动清理:删除所有 type 不在白名单里的 widget
      // (例如之前的 'controller' / 空 type / 拼写错误)
      let cleaned = false
      normalized.forEach(function (l) {
        const before = l.widgets.length
        l.widgets = l.widgets.filter(function (w) {
          return w && w.type && VALID_WIDGET_TYPES.indexOf(w.type) >= 0
        })
        if (l.widgets.length !== before) cleaned = true
      })
      // 如果清理掉了东西,立刻把干净的列表回写 storage
      if (cleaned) {
        try { uni.setStorageSync(LAYOUTS_KEY, normalized) } catch (e) {}
      }
      return migrateCodexMicro(normalized)
    }
  } catch (e) {
    console.warn('[layoutConfig] load failed', e)
  }
  return [DEFAULT_LAYOUT]
}

export function saveLayouts(layouts) {
  try {
    uni.setStorageSync(LAYOUTS_KEY, layouts)
    return true
  } catch (e) {
    console.warn('[layoutConfig] save failed', e)
    return false
  }
}

export function findLayout(id) {
  return loadLayouts().find(function (l) { return l.id === id }) || null
}

// ===== currentLayoutId =====

export function getCurrentLayoutId() {
  try {
    return uni.getStorageSync(CURRENT_KEY) || 'default'
  } catch (e) {
    return 'default'
  }
}

export function setCurrentLayoutId(id) {
  try {
    uni.setStorageSync(CURRENT_KEY, id)
    return true
  } catch (e) {
    return false
  }
}

export function getCurrentLayout() {
  const id = getCurrentLayoutId()
  return findLayout(id) || loadLayouts()[0]
}

// ===== 按 layout 维度的 widgets CRUD =====

function mutateLayout(layoutId, mutator) {
  const layouts = loadLayouts()
  const idx = layouts.findIndex(function (l) { return l.id === layoutId })
  if (idx < 0) return { layouts: layouts, layout: null }
  mutator(layouts[idx])
  saveLayouts(layouts)
  return { layouts: layouts, layout: layouts[idx] }
}

export function reorderLayoutWidgets(layoutId, ids) {
  return mutateLayout(layoutId, function (layout) {
    const map = {}
    layout.widgets.forEach(function (w) { map[w.id] = w })
    const next = ids.map(function (id, i) {
      const w = map[id]
      if (!w) return null
      return Object.assign({}, w, { order: i })
    }).filter(Boolean)
    if (next.length < layout.widgets.length) {
      const used = {}
      next.forEach(function (w) { used[w.id] = true })
      layout.widgets.forEach(function (w) {
        if (!used[w.id]) next.push(Object.assign({}, w, { order: next.length }))
      })
    }
    layout.widgets = next
  })
}

export function setLayoutWidgetVisible(layoutId, widgetId, visible) {
  return mutateLayout(layoutId, function (layout) {
    const w = layout.widgets.find(function (x) { return x.id === widgetId })
    if (w) w.visible = !!visible
  })
}

// 批量设置当前 layout 所有 widget 的 visible(三个点菜单的「收起/展开」用)
export function setAllLayoutWidgetsVisible(layoutId, visible) {
  return mutateLayout(layoutId, function (layout) {
    const v = !!visible
    layout.widgets.forEach(function (w) { w.visible = v })
  })
}

export function setLayoutWidgetCollapsed(layoutId, widgetId, collapsed) {
  return mutateLayout(layoutId, function (layout) {
    const w = layout.widgets.find(function (x) { return x.id === widgetId })
    if (w) w.collapsed = !!collapsed
  })
}

// 把 widget meta 加到 layout(如果 type 重复则跳过)
export function addWidgetToLayout(layoutId, widgetMeta) {
  let added = false
  mutateLayout(layoutId, function (layout) {
    if (layout.widgets.find(function (w) { return w.type === widgetMeta.type })) return
    layout.widgets.push(Object.assign({}, widgetMeta, {
      id: genId('w'),
      visible: true,
      collapsed: false,
      order: layout.widgets.length,
    }))
    added = true
  })
  return added
}

export function removeWidgetFromLayout(layoutId, widgetId) {
  return mutateLayout(layoutId, function (layout) {
    layout.widgets = layout.widgets.filter(function (w) { return w.id !== widgetId })
  })
}

// ===== layout 生命周期 =====

export function createLayout(name, sourceId) {
  const layouts = loadLayouts()
  const source = sourceId ? layouts.find(function (l) { return l.id === sourceId }) : null
  const newLayout = {
    id: genId('l'),
    name: name || ('面板 ' + (layouts.length + 1)),
    built_in: false,
    widgets: source ? source.widgets.map(function (w, i) {
      return Object.assign({}, w, { id: genId('w'), order: i })
    }) : [],
  }
  layouts.push(newLayout)
  saveLayouts(layouts)
  return newLayout
}

export function deleteLayout(layoutId) {
  if (layoutId === 'default') return loadLayouts()
  const layouts = loadLayouts().filter(function (l) { return l.id !== layoutId })
  saveLayouts(layouts)
  if (getCurrentLayoutId() === layoutId) {
    setCurrentLayoutId('default')
  }
  return layouts
}

export function renameLayout(layoutId, newName) {
  return mutateLayout(layoutId, function (layout) {
    if (layout.built_in) return
    layout.name = newName || layout.name
  })
}

export const CODE_SMITH_LAYOUT_ID = 'code-smith'

export function installCodeSmithLayout() {
  const layouts = loadLayouts()
  const existing = layouts.find(function(layout) { return layout.id === CODE_SMITH_LAYOUT_ID })
  if (existing) return existing
  const layout = {
    id: CODE_SMITH_LAYOUT_ID,
    name: 'Code Smith',
    built_in: false,
    widgets: [{
      id: 'w-code-smith-codex',
      type: 'codex-micro',
      title: 'Codex Micro',
      icon: '◉',
      visible: true,
      collapsed: false,
      order: 0,
    }],
  }
  layouts.push(layout)
  saveLayouts(layouts)
  return layout
}

export function isCodeSmithInstalled() {
  return loadLayouts().some(function(layout) { return layout.id === CODE_SMITH_LAYOUT_ID })
}
