<template>
<view :class="['page', 'layout-page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="section preview-section">
    <view class="layout-card-head">
    <view class="breadcrumb">
      <text class="breadcrumb-item">{{activeLayoutName}}</text>
      <text class="breadcrumb-sep"> / </text>
      <text class="breadcrumb-item breadcrumb-active">{{activePageName}}</text>
    </view>
      <view class="topbar-btn" @tap="onReload">↻ 刷新</view>
    </view>
    <view class="preview-header">
      <text class="preview-size-label">{{gridRows}} × {{gridCols}} 网格</text>
      <view class="preview-edit-btn" @tap="onShowSizePicker">改尺寸</view>
    </view>
    <view class="lp-hint">点空格添加按键 · 点已有按键进入“设置按键” · <text class="lp-hint-bold">长按</text>拖动换位</view>
    <view class="preview-grid">
      <view v-for="row in previewRows" :key="row.row" class="preview-grid-row">
      <view v-for="item in row.cells" :key="item.rc"
            :class="['preview-cell', cellClass(item), item.slot && (item.slot.colspan || item.slot.span || 1) > 1 ? 'span-' + (item.slot.colspan || item.slot.span || 1) : '', item.slot && (item.slot.rowspan || 1) > 1 ? 'rs-' + (item.slot.rowspan || 1) : '', dragSource && dragSource.r === item.r && dragSource.c === item.c ? 'dragging' : '', dropTarget && dropTarget.r === item.r && dropTarget.c === item.c ? 'drop-target' : '']"
            :style="cellStyle(item)"
            :data-r="item.r" :data-c="item.c"
            :data-id="item.slot && item.slot.key ? item.slot.key.id : ''"
            :data-has-slot="item.slot ? 1 : 0"
            @tap="onPreviewCellTap"
            @touchstart="onCellTouchStart"
            @touchmove.prevent.stop="onCellTouchMove"
            @touchend="onCellTouchEnd"
            @touchcancel="onCellTouchEnd"
            :hover-class="'' + ('preview-cell-hover' + '')">
        <block v-if="item.slot && item.slot.key">
          <text class="slot-label">{{item.slot.key.label || ""}}</text>
          <text v-if="item.slot.key.sub" class="slot-sub">{{item.slot.key.sub}}</text>
          <view v-if="dragSource && dragSource.r === item.r && dragSource.c === item.c" class="slot-del-x" @tap.stop="onSlotDelTap">×</view>
        </block>
      </view>
      </view>
    </view>
    <view v-if="dragGhost" class="drag-ghost" :style="ghostStyle">
      <text class="slot-label">{{dragGhost.label || ""}}</text>
    </view>
    <view v-if="dragSource" class="drag-mask" @touchstart="onMaskTouchStart" @touchmove.prevent.stop="onCellTouchMove" @touchend="onCellTouchEnd" @touchcancel="onCellTouchEnd"></view>
    <view v-if="!slots.length" class="empty-hint">还没有任何按键 · 点空格子添加第一个</view>
  </view>

  <view class="section templates-section">
    <view class="section-head">
      <text class="section-title">快捷键方案 ({{layouts.length}})</text>
      <view class="section-actions">
        <view class="section-action" :class="editMode ? 'section-action-on' : ''" @tap="onToggleEditMode">{{editMode ? '完成' : '编辑'}}</view>
        <view v-if="editMode" class="section-action section-action-primary" @tap="onAddLayout">+ 新建</view>
      </view>
    </view>
    <view v-if="lastCreatedId" class="new-template-banner" @tap="onScrollToCreated">
      <text class="new-template-banner-icon">✨</text>
      <view class="new-template-banner-text">
        <text class="new-template-banner-title">已新建：{{lastCreatedName}}</text>
        <text class="new-template-banner-desc">点击此处进入编辑</text>
      </view>
      <view class="new-template-banner-close" @tap.stop="onDismissCreated">×</view>
    </view>
    <view class="template-list">
      <view v-for="(item, idx) in layouts" :key="idx"
            :class="[item.id === activeLayoutId ? 'template-item on' : 'template-item', item.id === lastCreatedId ? 'is-new' : '', editMode ? 'template-item-edit' : '']"
            :data-id="item.id" :data-name="item.name" @tap="onTemplateItemTap">
        <text class="template-icon">{{layoutIcon(item)}}</text>
        <view class="template-info">
          <text class="template-name">{{item.name}}</text>
          <text class="template-meta">{{item.pages.length}} 页</text>
        </view>
        <text v-if="item.built_in && !editMode" class="template-badge">内置</text>
        <text v-else-if="!item.built_in && !editMode" class="template-badge template-badge-user">我的</text>
        <text v-if="item.id === lastCreatedId && !editMode" class="template-badge template-badge-new">新</text>
        <view v-if="editMode" class="template-del" :data-id="item.id" :data-name="item.name" hover-class="template-del-hover" @tap.stop="onManageLayoutTap">⋯</view>
      </view>
    </view>
  </view>

  <view class="config-bar">
    <view class="config-btn" @tap="onShowSizePicker">尺寸</view>
    <view class="config-btn" @tap="onRenameCurrentLayout">改名</view>
    <view class="config-btn" @tap="onGoTemplates">模板库</view>
    <view class="config-btn" @tap="onArchiveCurrentLayout">归档</view>
    <view class="config-btn config-btn-danger" @tap="onDeleteCurrentLayout">删除</view>
  </view>
  <view class="footer-safe"></view>

  <view v-if="showAddTypePicker" class="modal-mask" @tap="onAddTypeCancel">
    <view class="modal" @tap="noop">
      <view class="modal-head"><text class="modal-title">添加按键</text></view>
      <view class="modal-body">
        <view class="type-picker">
          <view class="type-btn" data-t="shortcut" @tap="onPickAddType">
            <text class="type-icon">⌨</text><text class="type-name">快捷键</text>
            <text class="type-desc">发送键盘组合</text>
          </view>
          <view class="type-btn" data-t="text" @tap="onPickAddType">
            <text class="type-icon">文</text><text class="type-name">文本</text>
            <text class="type-desc">注入一段文字</text>
          </view>
          <view class="type-btn" data-t="combo" @tap="onPickAddType">
            <text class="type-icon">＋</text><text class="type-name">多步操作</text>
            <text class="type-desc">多步骤动作</text>
          </view>
          <view class="type-btn" data-t="link" @tap="onPickAddType">
            <text class="type-icon">◎</text><text class="type-name">打开网站</text>
            <text class="type-desc">用电脑默认浏览器打开</text>
          </view>
          <view class="type-btn" data-t="app" @tap="onPickAddType">
            <text class="type-icon">▣</text><text class="type-name">打开软件</text>
            <text class="type-desc">启动已确认的软件</text>
          </view>
          <view class="type-btn" data-t="codex" @tap="onPickAddType">
            <text class="type-icon">C</text><text class="type-name">Codex 功能</text>
            <text class="type-desc">切换任务、批准或拒绝</text>
          </view>
        </view>
      </view>
      <view class="modal-foot"><view class="btn-cancel" @tap="onAddTypeCancel">取消</view></view>
    </view>
  </view>

  <view v-if="showSizePicker" class="modal-mask" @tap="onSizePickerCancel">
    <view class="modal" @tap="noop">
      <view class="modal-head"><text class="modal-title">选择网格尺寸</text></view>
      <view class="modal-body">
        <view class="size-picker">
          <view v-for="(item, idx) in sizePresets" :key="idx"
                :class="gridRows === item.rows && gridCols === item.cols ? 'size-option on' : 'size-option'"
                :data-key="item.key" @tap="onPickSize">
            <view class="size-label">{{item.label}}</view>
            <view class="size-info">{{item.rows * item.cols}} 键</view>
            <view class="size-mini" :class="'size-mini-' + item.cols + 'x' + item.rows">
              <view v-for="(c, idx) in item.previewCells" :key="idx" class="size-mini-cell"></view>
            </view>
          </view>
        </view>
      </view>
      <view class="modal-foot"><view class="btn-cancel" @tap="onSizePickerCancel">取消</view></view>
    </view>
  </view>

  <CustomTabBar />
</view>
</template>

<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
let app = null
try { app = getApp({ allowDefault: true }) } catch (e) {}
import WS from '@/utils/net.js'

export default {
  components: { CustomTabBar },
  data() { return {
      statusBarHeight: 24,
    layouts: [],
    activeLayoutId: "default",
    activeLayoutName: "默认",
    pages: [],
    activePageId: null,
    activePageName: "—",
    slots: [],
    gridRows: 4,
    gridCols: 4,
    previewCells: [],
    editMode: false,
    showSizePicker: false,
    showAddTypePicker: false,
    pendingAddR: -1,
    pendingAddC: -1,
    lastCreatedId: "",
    lastCreatedName: "",
    dragSource: null,       // {r, c, icon, label, slot}
    dragGhost: null,        // 同上（用于 ghost 元素渲染）
    dragGhostPos: null,     // {x, y} 屏幕坐标
    dropTarget: null,       // {r, c}
    _gridRect: null,        // 缓存 preview-grid 的 boundingClientRect
    _longPressTimer: null,
    _touchStart: null,      // {x, y, r, c, hasSlot}
    sizePresets: [
      { key: "3x3", label: "3 × 3", rows: 3, cols: 3, previewCells: Array(9).fill(0) },
      { key: "4x4", label: "4 × 4", rows: 4, cols: 4, previewCells: Array(16).fill(0) },
      { key: "3x4", label: "3 × 4", rows: 3, cols: 4, previewCells: Array(12).fill(0) },
      { key: "4x5", label: "4 × 5", rows: 4, cols: 5, previewCells: Array(20).fill(0) },
      { key: "5x4", label: "5 × 4", rows: 5, cols: 4, previewCells: Array(20).fill(0) },
    ],
  } },

  onShow() {
    const cached = (() => { try { return uni.getStorageSync("phonekb.last_layouts") } catch (e) { return null } })()
    console.log("[layout] onShow, cached layouts count=", cached && cached.layouts ? cached.layouts.length : 0, "active=", cached && cached.active_layout_id)
    if (cached) this._apply(cached)
    const self = this
    if (!this._layoutsListener) {
      this._layoutsListener = function(d) { console.log("[layout] onLayouts push, layouts count=", d && d.layouts ? d.layouts.length : 0); self._apply(d) }
      WS.onLayouts(this._layoutsListener)
    }
    WS.send({ action: "reload_layouts" })
  },

  onHide() {
    // 离开页面：兜底解锁 body 滚动锁，避免离开时还在拖动留下脏状态
    try { this._lockPageScroll && this._lockPageScroll(false) } catch (e) {}
  },

  onUnload() {
    try { this._lockPageScroll && this._lockPageScroll(false) } catch (e) {}
    if (this._layoutsListener) {
      WS.offLayouts(this._layoutsListener)
      this._layoutsListener = null
    }
  },

  computed: {
    previewRows() {
      const rowCount = Math.max(1, Number(this.gridRows) || 4)
      const rows = []
      for (let row = 0; row < rowCount; row++) {
        rows.push({
          row: row,
          cells: this.previewCells.filter(function(item) { return item.r === row }),
        })
      }
      return rows
    },
    ghostStyle() {
      if (!this.dragGhostPos) return "display: none;"
      const x = this.dragGhostPos.x
      const y = this.dragGhostPos.y
      return "left: " + x + "px; top: " + y + "px;"
    },
  },

  onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
    _apply(d) {
      if (!d) return
      const activeId = d.active_layout_id || (d.layouts[0] && d.layouts[0].id) || "default"
      const lay = (d.layouts || []).find(function(l) { return l.id === activeId }) || (d.layouts || [])[0]
      let pageId = d.active_page_id
      if (!pageId && lay && lay.pages && lay.pages[0]) pageId = lay.pages[0].id
      const page = lay && lay.pages ? lay.pages.find(function(p) { return p.id === pageId }) : null
      const gridRows = d.grid_rows || 4
      const gridCols = d.grid_cols || 4
      this.layouts = d.layouts || []; this.activeLayoutId = activeId; this.activeLayoutName = lay ? lay.name : "默认"; this.pages = lay ? lay.pages : []; this.activePageId = pageId; this.activePageName = page ? page.name : "—"; this.slots = page ? (page.slots || []) : []; this.gridRows = gridRows; this.gridCols = gridCols; this.previewCells = this._buildPreviewCells(page ? page.slots : [], gridRows, gridCols)
    },

    _buildPreviewCells(slots, rows, cols) {
      const cells = []
      const covered = new Set()
      for (const s of slots || []) {
        let cs = Number(s.colspan)
        const rawSpan = Number(s.span)
        if (!cs || cs < 1) cs = rawSpan || 1
        if (cs === 1 && rawSpan > 1) cs = rawSpan
        if (cs < 1) cs = 1
        s.colspan = cs
        let rs = Number(s.rowspan)
        if (!rs || rs < 1) rs = 1
        s.rowspan = rs
        for (let dr = 0; dr < rs; dr++) {
          for (let dc = 0; dc < cs; dc++) {
            if (dr === 0 && dc === 0) continue
            covered.add((s.r + dr) + "-" + (s.c + dc))
          }
        }
      }
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (covered.has(r + "-" + c)) continue
          const slot = (slots || []).find(function(s) { return s.r === r && s.c === c })
          cells.push({ r: r, c: c, slot: slot || null, rc: r + "-" + c })
        }
      }
      return cells
    },

    cellClass(item) { return item.slot ? "filled" : "empty" },

    cellStyle(item) {
      const cols = Math.max(1, Number(this.gridCols) || 4)
      const rows = Math.max(1, Number(this.gridRows) || 4)
      const gap = 8
      const available = 634
      const baseWidth = Math.floor((available - gap * (cols - 1)) / cols)
      const span = Math.max(1, Number(item && item.slot && (item.slot.colspan || item.slot.span)) || 1)
      const rowSpan = Math.max(1, Number(item && item.slot && item.slot.rowspan) || 1)
      const width = baseWidth * span + gap * (span - 1)
      const height = 82 * rowSpan + gap * (rowSpan - 1)
      const marginRight = item.c + span < cols ? gap : 0
      const marginBottom = item.r + rowSpan < rows ? gap : 0
      return 'width:' + width + 'rpx;flex:0 0 ' + width + 'rpx;min-height:' + height + 'rpx;margin-right:' + marginRight + 'rpx;margin-bottom:' + marginBottom + 'rpx;'
    },

    layoutIcon(item) {
      const id = String(item && item.id || '').toLowerCase()
      const name = String(item && item.name || '')
      const iconMap = {
        default: '⌨',
        vscode: '</>',
        jetbrains: 'JB',
        chrome: '◎',
        office: '▦',
        obs: '●',
        vim: 'V',
        terminal: '>_',
        windows: '⊞',
        keysilk: '⌘',
      }
      if (iconMap[id]) return iconMap[id]
      const ascii = name.replace(/[^A-Za-z0-9]/g, '')
      if (ascii) return ascii.slice(0, 2).toUpperCase()
      return name.slice(0, 1) || '◇'
    },

    onToggleEditMode() {
      this.editMode = !this.editMode
    },
    onTemplateItemTap(e) {
      if (this.editMode) return this.onManageLayoutTap(e)
      return this.onPickLayout(e)
    },
    onPickLayout(e) {
      const id = e.currentTarget.dataset.id
      if (id === this.activeLayoutId) return
      const lay = this.layouts.find(function(l) { return l.id === id })
      if (!lay) return
      this._syncLocalLayout(lay)
      const page = lay.pages && lay.pages[0]
      this.activeLayoutId = id; this.activeLayoutName = lay.name; this.pages = lay.pages || []; this.activePageId = page ? page.id : null; this.activePageName = page ? page.name : "—"; this.slots = page ? (page.slots || []) : []; this.previewCells = this._buildPreviewCells(page ? page.slots : [], this.gridRows, this.gridCols)
      // 模板安装和切换在离线时也只写本机缓存；连接电脑后再同步当前选择。
      try {
        const cached = uni.getStorageSync('phonekb.last_layouts') || {}
        cached.active_layout_id = id
        cached.active_page_id = page ? page.id : null
        if (!cached.grid_rows) cached.grid_rows = 4
        if (!cached.grid_cols) cached.grid_cols = 4
        uni.setStorageSync('phonekb.last_layouts', cached)
      } catch (e) {}
      if (!lay.local_only && (typeof WS.isConnected !== 'function' || WS.isConnected())) {
        WS.send({ action: "set_active", layout_id: id, page_id: page ? page.id : null })
      }
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
    },

    _syncLocalLayout(layout) {
      if (!layout || !layout.local_only) return true
      if (typeof WS.isConnected === 'function' && !WS.isConnected()) return false
      const page = layout.pages && layout.pages[0]
      if (!page) return false
      const sent = WS.send({
        action: 'add_layout',
        id: layout.id,
        name: layout.name || '新方案',
        icon: layout.icon || '',
        page_id: page.id,
        grid_cols: this.gridCols || 4,
        grid_rows: this.gridRows || 4,
      })
      if (!sent) return false
      layout.local_only = false
      try {
        const cached = uni.getStorageSync('phonekb.last_layouts') || {}
        const item = (cached.layouts || []).find(function(candidate) { return candidate.id === layout.id })
        if (item) item.local_only = false
        uni.setStorageSync('phonekb.last_layouts', cached)
      } catch (e) {}
      return true
    },

    onScrollToCreated() {
      if (!this.lastCreatedId) return
      this.onPickLayout({ currentTarget: { dataset: { id: this.lastCreatedId } } })
    },

    onDismissCreated() { this.lastCreatedId = ""; this.lastCreatedName = "" },

    onShowSizePicker() { this.showSizePicker = true },
    onSizePickerCancel() { this.showSizePicker = false },

    onPickSize(e) {
      const key = e.currentTarget.dataset.key
      const preset = this.sizePresets.find(function(p) { return p.key === key })
      if (!preset) return
      this.gridRows = preset.rows; this.gridCols = preset.cols; this.showSizePicker = false; this.previewCells = this._buildPreviewCells(this.slots, preset.rows, preset.cols)
      WS.send({ action: "set_grid_rows", rows: preset.rows })
      WS.send({ action: "set_grid_cols", cols: preset.cols })
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
    },

    // ===== 长按拖动 + 右上角 x 删除 =====
    onCellTouchStart(e) {
      const ds = e.currentTarget.dataset
      const r = Number(ds.r), c = Number(ds.c)
      const hasSlot = String(ds.hasSlot) === "1"
      const t = e.touches && e.touches[0]
      if (!t) return
      this._touchStart = { x: t.clientX, y: t.clientY, r: r, c: c, hasSlot: hasSlot }
      this.dragSource = null
      this.dragGhost = null
      this.dragGhostPos = null
      this.dropTarget = null
      if (this._longPressTimer) clearTimeout(this._longPressTimer)
      // 仅已填格子支持长按拖动/删除
      if (!hasSlot) return
      const self = this
      this._longPressTimer = setTimeout(function() {
        self._longPressTimer = null
        if (!self._touchStart) return
        const idx = self.previewCells.findIndex(function(it) { return it.r === r && it.c === c })
        if (idx < 0) return
        const item = self.previewCells[idx]
        self.dragSource = { r: item.r, c: item.c, icon: item.slot && item.slot.key && item.slot.key.icon, label: item.slot && item.slot.key && item.slot.key.label, slot: item.slot }
        self.dragGhost = { icon: self.dragSource.icon, label: self.dragSource.label }
        self.dragGhostPos = { x: t.clientX, y: t.clientY }
        self.dropTarget = null
        self._refreshGridRect()
        self._lockPageScroll(true)
        try { uni.vibrateShort({ type: "medium" }) } catch (e2) {}
      }, 350)
    },

    onMaskTouchStart(e) {
      // 点在 mask 上（手指滑出格子区）：当作 touchend 处理，取消拖动
      this.onCellTouchEnd(e)
    },

    onCellTouchMove(e) {
      try { e.preventDefault && e.preventDefault() } catch (e2) {}
      if (!this._touchStart) return
      const t = e.touches && e.touches[0]
      if (!t) return
      if (!this.dragSource) {
        // 还没进入 drag mode：若手指移动太多，取消长按意图
        const dx = t.clientX - this._touchStart.x
        const dy = t.clientY - this._touchStart.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist > 10) {
          if (this._longPressTimer) { clearTimeout(this._longPressTimer); this._longPressTimer = null }
          this._touchStart = null
        }
        return
      }
      // 拖动中：更新 ghost 位置和 dropTarget
      this.dragGhostPos = { x: t.clientX, y: t.clientY }
      this.dropTarget = this._findCellAt(t.clientX, t.clientY)
    },

    onCellTouchEnd(e) {
      if (this._longPressTimer) { clearTimeout(this._longPressTimer); this._longPressTimer = null }
      if (this.dragSource) {
        const src = this.dragSource
        const dst = this.dropTarget
        this._exitDragMode()
        if (dst && (dst.r !== src.r || dst.c !== src.c)) {
          this._commitMove(src.r, src.c, dst.r, dst.c)
        }
        return
      }
      // 短按：清掉 _touchStart，让 @tap 接管（uni-app 在 touchend 后会自动触发 tap）
      this._touchStart = null
    },

    _exitDragMode() {
      this.dragSource = null
      this.dragGhost = null
      this.dragGhostPos = null
      this.dropTarget = null
      this._touchStart = null
      this._lockPageScroll(false)
    },

    _lockPageScroll(lock) {
      try {
        var body = (typeof document !== "undefined") ? document.body : null
        var root = (typeof document !== "undefined") ? document.documentElement : null
        if (!body || !root) return
        if (lock) {
          if (!body.dataset._kbScrollY) body.dataset._kbScrollY = String(window.scrollY || 0)
          body.style.overflow = "hidden"
          body.style.touchAction = "none"
          body.style.position = "fixed"
          body.style.left = "0"
          body.style.right = "0"
          body.style.top = "-" + (body.dataset._kbScrollY || "0") + "px"
          body.style.width = "100%"
        } else {
          var y = parseInt(body.dataset._kbScrollY || "0", 10) || 0
          body.style.overflow = ""
          body.style.touchAction = ""
          body.style.position = ""
          body.style.left = ""
          body.style.right = ""
          body.style.top = ""
          body.style.width = ""
          delete body.dataset._kbScrollY
          try { window.scrollTo(0, y) } catch (e3) {}
        }
      } catch (e) {}
    },

    _refreshGridRect() {
      const self = this
      try {
        const query = uni.createSelectorQuery().in(this)
        query.select('.preview-grid').boundingClientRect()
        query.exec(function(res) {
          if (res && res[0]) self._gridRect = res[0]
        })
      } catch (e) {}
    },

    _findCellAt(x, y) {
      const rect = this._gridRect
      if (!rect) return null
      const localX = x - rect.left
      const localY = y - rect.top
      if (localX < 0 || localY < 0 || localX > rect.width || localY > rect.height) return null

      const cols = Math.max(1, Number(this.gridCols) || 4)
      const rows = Math.max(1, Number(this.gridRows) || 4)
      const gap = typeof uni.upx2px === 'function' ? uni.upx2px(10) : 5
      const cellWidth = (rect.width - gap * (cols - 1)) / cols
      const cellHeight = (rect.height - gap * (rows - 1)) / rows
      const strideX = cellWidth + gap
      const strideY = cellHeight + gap

      let col = Math.floor(localX / strideX)
      let row = Math.floor(localY / strideY)
      if (col < 0) col = 0
      if (col >= cols) col = cols - 1
      if (row < 0) row = 0
      if (row >= rows) row = rows - 1
      return { r: row, c: col }
    },

    _commitMove(srcR, srcC, dstR, dstC) {
      try {
        if (typeof WS.isConnected === 'function' && !WS.isConnected()) {
          uni.showToast({ title: '未连接，无法移动', icon: 'none' })
          return
        }
      } catch (e) {}
      const ok = WS.moveSlot(this.activeLayoutId, this.activePageId, srcR, srcC, dstR, dstC)
      if (ok === false) {
        uni.showToast({ title: '发送失败，请检查连接', icon: 'none' })
        return
      }
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      uni.showToast({ title: '已移动', icon: 'success', duration: 600 })
    },

    onSlotDelTap() {
      if (!this.dragSource) return
      const slot = this.dragSource.slot
      const key = slot && slot.key
      const label = (key && key.label) || '这个按键'
      const row = this.dragSource.r
      const col = this.dragSource.c
      const self = this
      this._exitDragMode()
      uni.showModal({
        title: '删除按键',
        content: '确认删除「' + label + '」吗？',
        confirmText: '删除',
        confirmColor: '#e34c4c',
        cancelText: '取消',
        success: function(res) {
          if (!res.confirm) return
          try {
            if (typeof WS.isConnected === 'function' && !WS.isConnected()) {
              uni.showToast({ title: '未连接，删不了', icon: 'none' })
              return
            }
          } catch (e) {}
          const ok = WS.deleteSlot(self.activeLayoutId, self.activePageId, row, col)
          if (ok === false) {
            uni.showToast({ title: '发送失败，请检查连接', icon: 'none' })
            return
          }
          uni.showToast({ title: '已删除', icon: 'success', duration: 600 })
        }
      })
    },

    onPreviewCellTap(e) {
      if (this.dragSource) return
      const ds = (e && (e.currentTarget && e.currentTarget.dataset)) || (e && e.target && e.target.dataset) || {}
      const slotId = String(ds.id || '')
      const row = (ds.r !== undefined && ds.r !== '') ? Number(ds.r) : -1
      const col = (ds.c !== undefined && ds.c !== '') ? Number(ds.c) : -1
      if (slotId) {
        const url = '/pages/layout/edit-key?id=' + encodeURIComponent(slotId) + '&layout_id=' + encodeURIComponent(this.activeLayoutId || 'default') + '&page_id=' + encodeURIComponent(this.activePageId || '') + '&r=' + row + '&c=' + col
        try {
          uni.navigateTo({
            url: url,
            success: function() {},
            fail: function(err) {
              try { uni.showModal({ title: '跳转失败', content: 'open edit-key: ' + (err && err.errMsg ? err.errMsg : 'unknown') + '\nurl=' + url, showCancel: false }) } catch (e) {}
            },
          })
        } catch (e) {
          try { uni.showToast({ title: '调用失败', icon: 'none' }) } catch (e2) {}
        }
      } else {
        this.showAddTypePicker = true
        this.pendingAddR = row
        this.pendingAddC = col
      }
    },



    onPickAddType(e) {
      const type = e.currentTarget.dataset.t
      const row = this.pendingAddR
      const col = this.pendingAddC
      const layout = (this.layouts || []).find((item) => item.id === this.activeLayoutId)
      if (layout && layout.local_only && !this._syncLocalLayout(layout)) {
        uni.showToast({ title: '请先连接电脑再添加按键', icon: 'none' })
        return
      }
      this.showAddTypePicker = false
      this.pendingAddR = -1
      this.pendingAddC = -1
      uni.navigateTo({ url: '/pages/layout/edit-key?isNew=1&layout_id=' + this.activeLayoutId + '&page_id=' + this.activePageId + '&r=' + row + '&c=' + col + '&type=' + type })
    },

    onAddTypeCancel() {
      this.showAddTypePicker = false
      this.pendingAddR = -1
      this.pendingAddC = -1
    },

    onAddLayout() {
      const names = (this.layouts || []).map(function(item) { return item && item.name })
      let index = 1
      let name = '快捷键方案 ' + index
      while (names.indexOf(name) >= 0) {
        index += 1
        name = '快捷键方案 ' + index
      }
      this._createLocalLayout(name)
    },
    noop() {},
    _createLocalLayout(name) {
      let cached = {}
      try { cached = uni.getStorageSync('phonekb.last_layouts') || {} } catch (e) {}
      const stamp = Date.now().toString(36)
      const newId = 'u_' + stamp
      const newPageId = 'p_' + stamp
      const newLayout = { id: newId, name: name, icon: '', local_only: true, pages: [{ id: newPageId, name: '页面 1', slots: [] }] }
      const layouts = (cached.layouts || this.layouts || []).concat([newLayout])
      cached.layouts = layouts
      cached.active_layout_id = newId
      cached.active_page_id = newPageId
      cached.grid_cols = cached.grid_cols || 4
      cached.grid_rows = cached.grid_rows || 4
      if (!Array.isArray(cached.global_pages)) cached.global_pages = []
      try { uni.setStorageSync('phonekb.last_layouts', cached) } catch (e) {}
      this.layouts = layouts
      this.lastCreatedId = newId
      this.lastCreatedName = name
      this.onPickLayout({ currentTarget: { dataset: { id: newId } } })
      uni.showToast({ title: '已新建 ' + name, icon: 'success', duration: 900 })
    },

    onManageLayoutTap(e) {
      const id = (e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id) || ''
      const layout = (this.layouts || []).find(function(item) { return item.id === id })
      if (!layout) return
      const self = this
      uni.showActionSheet({
        itemList: ['重命名', '归档到模板库', '删除'],
        success: function(res) {
          if (res.tapIndex === 0) self.onRenameLayout(layout)
          else if (res.tapIndex === 1) self.onArchiveLayout(layout)
          else if (res.tapIndex === 2) self.onDeleteLayout(layout.id, layout.name)
        },
      })
    },

    onRenameCurrentLayout() {
      const layout = (this.layouts || []).find((item) => item.id === this.activeLayoutId)
      if (layout) this.onRenameLayout(layout)
    },
    onRenameLayout(layout) {
      const self = this
      uni.showModal({
        title: '重命名方案',
        content: '请输入新名称',
        editable: true,
        placeholderText: layout.name || '快捷键方案',
        success: function(res) {
          if (!res.confirm) return
          const name = String(res.content || '').trim()
          if (!name) return
          layout.name = name
          if (layout.id === self.activeLayoutId) self.activeLayoutName = name
          try {
            const cached = uni.getStorageSync('phonekb.last_layouts') || {}
            const item = (cached.layouts || []).find(function(candidate) { return candidate.id === layout.id })
            if (item) item.name = name
            uni.setStorageSync('phonekb.last_layouts', cached)
          } catch (e) {}
          if (!layout.local_only && (typeof WS.isConnected !== 'function' || WS.isConnected())) {
            WS.send({ action: 'rename_layout', layout_id: layout.id, name: name })
          }
          uni.showToast({ title: '已重命名', icon: 'success', duration: 700 })
        },
      })
    },

    onArchiveCurrentLayout() {
      const layout = (this.layouts || []).find((item) => item.id === this.activeLayoutId)
      if (layout) this.onArchiveLayout(layout)
    },
    onArchiveLayout(layout) {
      if (!layout) return
      if (layout.local_only || (typeof WS.isConnected === 'function' && !WS.isConnected())) {
        this._removeLocalLayout(layout, true)
      } else {
        WS.send({ action: 'archive_layout', layout_id: layout.id })
      }
      uni.showToast({ title: '已归档到模板库', icon: 'success', duration: 900 })
    },

    onDeleteCurrentLayout() {
      this.onDeleteLayout(this.activeLayoutId, this.activeLayoutName)
    },

    onDeleteLayout(id, name) {
      if (!id) id = this.activeLayoutId
      const layout = (this.layouts || []).find(function(item) { return item.id === id })
      if (!layout) return
      const self = this
      uni.showModal({
        title: '删除方案',
        content: '确定删除「' + (name || layout.name) + '」吗？此操作不可恢复。',
        confirmText: '删除',
        confirmColor: '#D64545',
        success: function(res) {
          if (!res.confirm) return
          if (layout.local_only || (typeof WS.isConnected === 'function' && !WS.isConnected())) {
            self._removeLocalLayout(layout, false)
          } else {
            WS.send({ action: 'delete_layout', layout_id: layout.id })
          }
          uni.showToast({ title: '已删除', icon: 'success', duration: 700 })
        },
      })
    },

    _removeLocalLayout(layout, archive) {
      let cached = {}
      try { cached = uni.getStorageSync('phonekb.last_layouts') || {} } catch (e) {}
      let nextLayouts = (cached.layouts || this.layouts || []).filter(function(item) { return item.id !== layout.id })
      if (archive) {
        cached.archived_layouts = (cached.archived_layouts || []).filter(function(item) { return item.id !== layout.id })
        cached.archived_layouts.push(Object.assign({}, layout, { local_only: true }))
      }
      if (!nextLayouts.length) {
        const stamp = Date.now().toString(36)
        nextLayouts = [{ id: 'u_' + stamp, name: '空白方案', icon: '', local_only: true, pages: [{ id: 'p_' + stamp, name: '页面 1', slots: [] }] }]
      }
      const nextLayout = nextLayouts[0]
      const nextPage = nextLayout.pages && nextLayout.pages[0]
      cached.layouts = nextLayouts
      cached.active_layout_id = nextLayout.id
      cached.active_page_id = nextPage ? nextPage.id : null
      if (!cached.grid_rows) cached.grid_rows = 4
      if (!cached.grid_cols) cached.grid_cols = 4
      try { uni.setStorageSync('phonekb.last_layouts', cached) } catch (e) {}
      this.layouts = nextLayouts
      this.lastCreatedId = ''
      this.lastCreatedName = ''
      this._apply(cached)
    },

    onGoTemplates() { uni.navigateTo({ url: "/pages/templates/templates" }) },

    onReload() {
      WS.send({ action: "reload_layouts" })
      uni.showToast({ title: "已刷新", icon: "success", duration: 800 })
    },
  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 20rpx 24rpx calc(132rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}
.section {
  margin: 0 8rpx 16rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(47, 78, 113, 0.06);
}
.preview-section {
  padding: 20rpx 26rpx 22rpx;
}
.layout-card-head,
.preview-header,
.section-head,
.section-actions,
.template-item,
.config-bar,
.modal-head,
.modal-foot,
.type-picker,
.size-picker {
  display: flex;
  align-items: center;
}
.layout-card-head,
.preview-header,
.section-head {
  justify-content: space-between;
}
.breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
}
.breadcrumb-item {
  color: #172033;
  font-size: 24rpx;
  font-weight: 700;
}
.breadcrumb-active {
  color: #2F78F6;
}
.breadcrumb-sep {
  color: #91A0B2;
  font-size: 24rpx;
}
.topbar-btn,
.preview-edit-btn,
.section-action {
  min-height: 44rpx;
  padding: 0 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 11rpx;
  background: #FFFFFF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 650;
}
.preview-header {
  margin-top: 14rpx;
}
.preview-size-label {
  color: #64758B;
  font-size: 20rpx;
  font-weight: 600;
}
.lp-hint {
  margin-top: 12rpx;
  padding: 12rpx 16rpx;
  border-radius: 12rpx;
  background: #EAF3FF;
  color: #55708F;
  font-size: 19rpx;
  line-height: 1.45;
}
.lp-hint-bold {
  color: #2F78F6;
  font-weight: 700;
}
.preview-grid {
  margin-top: 14rpx;
}
.preview-grid-row {
  display: flex;
  align-items: flex-start;
}
.preview-cell {
  min-width: 0;
  min-height: 82rpx;
  padding: 8rpx 6rpx;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border: 1rpx solid #D5E1EE;
  border-radius: 14rpx;
  background: #FBFDFF;
  box-shadow: 0 2rpx 7rpx rgba(47, 78, 113, 0.035);
  box-sizing: border-box;
}
.preview-cell.filled {
  border-color: #BCD2EB;
  background: #FFFFFF;
}
.preview-cell-hover {
  background: #F7FAFE;
}
.preview-cell.dragging {
  opacity: 0.45;
}
.preview-cell.drop-target {
  border-color: #2F78F6;
  background: #EAF3FF;
}
.span-2 {
  grid-column: span 2;
}
.span-3 {
  grid-column: span 3;
}
.span-4 {
  grid-column: span 4;
}
.rs-2 {
  grid-row: span 2;
}
.rs-3 {
  grid-row: span 3;
}
.slot-icon {
  color: #506177;
  font-size: 22rpx;
  line-height: 1;
}
.slot-label {
  max-width: 100%;
  margin-top: 4rpx;
  color: #172033;
  font-size: 19rpx;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.slot-sub {
  margin-top: 3rpx;
  color: #7E8B9E;
  font-size: 15rpx;
}
.slot-del-x {
  position: absolute;
  top: 7rpx;
  right: 7rpx;
  width: 34rpx;
  height: 34rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #FDE7E9;
  color: #D13438;
  font-size: 21rpx;
}
.empty-hint {
  padding: 28rpx 0 4rpx;
  color: #8996A7;
  font-size: 22rpx;
  text-align: center;
}
.drag-ghost {
  position: fixed;
  width: 120rpx;
  height: 100rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border: 2rpx solid #2F78F6;
  border-radius: 18rpx;
  background: #FFFFFF;
  box-shadow: 0 16rpx 36rpx rgba(47, 78, 113, 0.18);
  z-index: 101;
}
.drag-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
}
.templates-section {
  padding: 18rpx;
}
.section-head {
  min-height: 58rpx;
}
.section-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.section-actions {
  gap: 10rpx;
}
.section-action-on,
.section-action-primary {
  border-color: #2F78F6;
  background: #EAF3FF;
}
.new-template-banner {
  margin-top: 16rpx;
  padding: 16rpx 18rpx;
  display: flex;
  align-items: center;
  border-radius: 16rpx;
  background: #EAF8EF;
}
.new-template-banner-icon {
  margin-right: 12rpx;
  font-size: 26rpx;
}
.new-template-banner-text {
  display: flex;
  flex: 1;
  flex-direction: column;
}
.new-template-banner-title {
  color: #16783D;
  font-size: 23rpx;
  font-weight: 700;
}
.new-template-banner-desc {
  margin-top: 3rpx;
  color: #5C8A6C;
  font-size: 19rpx;
}
.new-template-banner-close {
  color: #5C8A6C;
  font-size: 30rpx;
}
.template-list {
  margin-top: 10rpx;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
}
.template-item {
  width: calc(50% - 6rpx);
  min-height: 112rpx;
  margin-bottom: 12rpx;
  padding: 14rpx;
  position: relative;
  border: 1rpx solid #E1E9F2;
  border-radius: 16rpx;
  background: #FBFDFF;
  box-sizing: border-box;
}
.template-item.on {
  border-color: #74A8FF;
  background: #F4F8FF;
  box-shadow: 0 5rpx 14rpx rgba(47, 120, 246, 0.10);
}
.template-item.is-new {
  background: #F0F8FF;
}
.template-icon {
  width: 46rpx;
  height: 46rpx;
  margin-right: 10rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  background: #EEF5FD;
  color: #2F78F6;
  font-size: 19rpx;
  font-weight: 750;
}
.template-info {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.template-name {
  color: #172033;
  font-size: 22rpx;
  font-weight: 650;
}
.template-meta {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 18rpx;
}
.template-badge {
  position: absolute;
  right: 10rpx;
  bottom: 8rpx;
  padding: 3rpx 8rpx;
  border-radius: 8rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 16rpx;
  font-weight: 650;
}
.template-badge-user {
  background: #EEF4FA;
  color: #607087;
}
.template-badge-new {
  margin-left: 6rpx;
  background: #EAF8EF;
  color: #159447;
}
.template-del {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  width: 36rpx;
  height: 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #FDE7E9;
  color: #D13438;
  font-size: 23rpx;
}
.config-bar {
  margin: 0 8rpx 16rpx;
  gap: 12rpx;
}
.config-btn {
  flex: 1;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 13rpx;
  background: #FFFFFF;
  color: #506177;
  font-size: 20rpx;
  font-weight: 650;
}
.config-btn-danger {
  color: #D13438;
}
.modal-mask {
  position: fixed;
  inset: 0;
  padding: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(23, 32, 51, 0.34);
  z-index: 300;
}
.modal {
  width: 100%;
  max-height: 78vh;
  overflow: hidden;
  border: 1rpx solid #DCE6F1;
  border-radius: 28rpx;
  background: #FFFFFF;
  box-shadow: 0 28rpx 70rpx rgba(29, 55, 86, 0.22);
}
.modal-head {
  min-height: 92rpx;
  padding: 0 26rpx;
  border-bottom: 1rpx solid #E8EEF5;
}
.modal-title {
  color: #172033;
  font-size: 29rpx;
  font-weight: 700;
}
.modal-body {
  max-height: 58vh;
  padding: 24rpx 26rpx;
  overflow-y: auto;
}
.modal-foot {
  min-height: 90rpx;
  padding: 0 26rpx;
  justify-content: flex-end;
  gap: 14rpx;
  border-top: 1rpx solid #E8EEF5;
}
.btn-cancel,
.btn-save {
  min-width: 112rpx;
  height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  font-size: 23rpx;
  font-weight: 650;
}
.btn-cancel {
  background: #EEF4FA;
  color: #506177;
}
.btn-save {
  background: #2F78F6;
  color: #FFFFFF;
}
.type-picker,
.size-picker {
  flex-wrap: wrap;
  gap: 14rpx;
}
.type-btn,
.size-option {
  width: calc(50% - 7rpx);
  padding: 20rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 18rpx;
  background: #F7FAFE;
  box-sizing: border-box;
}
.type-btn {
  display: flex;
  flex-direction: column;
}
.type-icon {
  font-size: 30rpx;
}
.type-name {
  margin-top: 10rpx;
  color: #172033;
  font-size: 25rpx;
  font-weight: 700;
}
.type-desc,
.size-info {
  margin-top: 5rpx;
  color: #7E8B9E;
  font-size: 20rpx;
}
.size-option.on {
  border-color: #2F78F6;
  background: #EAF3FF;
}
.size-label {
  color: #172033;
  font-size: 24rpx;
  font-weight: 700;
}
.size-mini {
  margin-top: 14rpx;
  display: grid;
  gap: 4rpx;
}
.size-mini-cell {
  height: 15rpx;
  border-radius: 4rpx;
  background: #CBD9E8;
}
.size-mini-2x2,
.size-mini-2x3,
.size-mini-2x4 {
  grid-template-columns: repeat(2, 1fr);
}
.size-mini-3x2,
.size-mini-3x3,
.size-mini-3x4 {
  grid-template-columns: repeat(3, 1fr);
}
.size-mini-4x2,
.size-mini-4x3,
.size-mini-4x4 {
  grid-template-columns: repeat(4, 1fr);
}
.modal-input {
  height: 76rpx;
  padding: 0 20rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 15rpx;
  background: #F7FAFE;
  color: #172033;
  font-size: 26rpx;
}
.modal-input-hint {
  margin-bottom: 10rpx;
  color: #64758B;
  font-size: 22rpx;
}
.modal-from-template {
  margin-top: 18rpx;
  color: #2F78F6;
  font-size: 23rpx;
  text-align: right;
}
.footer-safe {
  height: 20rpx;
}

.page.app-appearance-active {
  background: var(--app-page-bg-color);
  color: var(--app-color-text);
}
.page.app-appearance-active .section {
  background: var(--app-surface);
  border-color: var(--app-color-border);
}
.page.app-appearance-active .breadcrumb-item,
.page.app-appearance-active .section-title,
.page.app-appearance-active .slot-label,
.page.app-appearance-active .template-name,
.page.app-appearance-active .modal-title,
.page.app-appearance-active .type-name,
.page.app-appearance-active .size-label {
  color: var(--app-color-text);
}
.page.app-appearance-active .breadcrumb-sep,
.page.app-appearance-active .preview-size-label,
.page.app-appearance-active .slot-icon,
.page.app-appearance-active .slot-sub,
.page.app-appearance-active .empty-hint,
.page.app-appearance-active .template-meta,
.page.app-appearance-active .type-desc,
.page.app-appearance-active .size-info,
.page.app-appearance-active .modal-input-hint {
  color: var(--app-color-text-mid);
}
.page.app-appearance-active .topbar-btn,
.page.app-appearance-active .preview-edit-btn,
.page.app-appearance-active .section-action,
.page.app-appearance-active .config-btn,
.page.app-appearance-active .preview-cell,
.page.app-appearance-active .template-item,
.page.app-appearance-active .type-btn,
.page.app-appearance-active .size-option,
.page.app-appearance-active .btn-cancel,
.page.app-appearance-active .modal-input {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.page.app-appearance-active .config-btn,
.page.app-appearance-active .btn-cancel,
.page.app-appearance-active .modal-input {
  color: var(--app-color-text-mid);
}
.page.app-appearance-active .preview-cell.filled {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.page.app-appearance-active .preview-cell-hover,
.page.app-appearance-active .preview-cell.drop-target,
.page.app-appearance-active .section-action-on,
.page.app-appearance-active .section-action-primary,
.page.app-appearance-active .template-item.on,
.page.app-appearance-active .size-option.on,
.page.app-appearance-active .lp-hint {
  background: var(--app-color-primary-bg);
}
.page.app-appearance-active .template-item.is-new,
.page.app-appearance-active .new-template-banner {
  background: var(--app-success-surface);
}
.page.app-appearance-active .template-icon,
.page.app-appearance-active .template-badge {
  background: var(--app-color-primary-bg);
  color: var(--app-color-primary);
}
.page.app-appearance-active .template-badge-user {
  background: var(--app-color-bg-alt);
  color: var(--app-color-text-mid);
}
.page.app-appearance-active .template-badge-new {
  background: var(--app-success-surface);
  color: var(--color-success);
}
.page.app-appearance-active .slot-del-x,
.page.app-appearance-active .template-del {
  background: var(--app-danger-surface);
  color: var(--color-danger);
}
.page.app-appearance-active .drag-ghost,
.page.app-appearance-active .modal {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.page.app-appearance-active .modal-head,
.page.app-appearance-active .modal-foot {
  border-color: var(--app-color-divider);
}
.page.app-appearance-active .size-mini-cell {
  background: var(--app-color-border);
}

.statusbar-spacer { width: 100%; }
</style>
