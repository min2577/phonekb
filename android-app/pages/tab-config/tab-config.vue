<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <!-- 顶部导航:深色背景,白字 -->
  <view class="topbar" :style="{ paddingTop: statusBarHeight + 'px' }">
    <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">
      <text class="topbar-back-icon">‹</text>
    </view>
    <text class="topbar-title">自定义APP</text>
    <view class="topbar-icon"
          hover-class="topbar-icon-hover"
          @tap="onResetDefault">
      <text class="topbar-icon-text">↺</text>
    </view>
    <view class="topbar-icon"
          :class="{ active: dirty, disabled: saving }"
          hover-class="topbar-icon-hover"
          @tap="onSave">
      <text class="topbar-icon-text">✓</text>
    </view>
  </view>

  <view class="preview-area">
    <CustomAppPreview
      :widgets="panelWidgets"
      :tabs="enabledTabs"
      :connected="connected"
      :slots="previewSlots"
      :grid-cols="previewGridCols"
      :layouts="previewLayouts"
      :active-layout-id="previewActiveLayoutId"
      :active-page-id="previewActivePageId"
      :layout-name="currentLayoutName"
      :theme="currentTheme" />
  </view>

  <!-- 底部 sheet(图 1 风格) -->
  <view class="sheet">
    <view class="sheet-cats">
      <text class="sheet-cat" :class="{ active: sheetCat === 'tab' }" @tap="sheetCat = 'tab'">选项卡</text>
      <text class="sheet-cat disabled">主题</text>
      <text class="sheet-cat disabled">背景</text>
      <text class="sheet-cat disabled">字体</text>
    </view>

    <!-- tab 分类:水平滚动卡片 -->
    <scroll-view v-if="sheetCat === 'tab'" class="sheet-cards" :scroll-x="!isDragging" :show-scrollbar="false">
      <view v-for="(t, idx) in enabledTabs" :key="t.id"
            class="sheet-card"
            :class="{
              'is-pressing': pressId === t.id && !isDragging,
              'is-dragging': dragId === t.id,
              'is-builtin': t.built_in,
            }"
            :style="{
              width: cardSize + 'rpx',
              height: cardSize + 'rpx',
              marginRight: cardGap + 'rpx',
              transform: dragId === t.id ? ('translateX(' + dragOffsetPx + 'px) scale(1.12)') : 'none',
              zIndex: dragId === t.id ? 10 : 1,
              opacity: isDragging && dragId !== t.id ? 0.5 : 1,
            }"
            :data-id="t.id"
            hover-class="sheet-card-hover"
            @touchstart="onTouchStart($event, t.id, idx)"
            @touchmove="onTouchMove"
            @touchend="onTouchEnd"
            @touchcancel="onTouchEnd"
            @tap="onCardTap(t)">
        <view v-if="!t.built_in" class="sheet-card-badge" hover-class="sheet-card-badge-hover" @touchstart.stop @tap.stop="onRemoveTab(t)">
          <text class="sheet-card-badge-text">−</text>
        </view>
        <view class="sheet-card-icon">{{tabDisplayIcon(t)}}</view>
        <text class="sheet-card-label">{{t.label}}</text>
      </view>
      <view v-if="enabledTabs.length < 6"
            class="sheet-card sheet-card-add"
            :style="{ width: cardSize + 'rpx', height: cardSize + 'rpx' }"
            hover-class="sheet-card-hover"
            @tap="onOpenAddSheet">
        <view class="sheet-card-icon sheet-card-add-icon-wrap"><text class="sheet-card-add-icon">＋</text></view>
        <text class="sheet-card-label">添加</text>
      </view>
    </scroll-view>

    <!-- 主题 分类:垂直网格 -->
    <scroll-view v-else-if="sheetCat === 'theme'" class="sheet-cards sheet-themes" scroll-y="true" :show-scrollbar="false">
      <view v-for="t in themes" :key="t.id"
            class="theme-card"
            :class="{ active: currentThemeId === t.id }"
            hover-class="theme-card-hover"
            @tap="onPickTheme(t)">
        <view class="theme-card-head">
          <text class="theme-card-emoji">{{ t.emoji }}</text>
          <text class="theme-card-name">{{ t.name }}</text>
          <view v-if="currentThemeId === t.id" class="theme-card-check">
            <text class="theme-card-check-text">✓</text>
          </view>
        </view>
        <text class="theme-card-style">{{ t.style }}</text>
        <view class="theme-card-swatches">
          <view class="theme-swatch" :style="{ background: t.vars['--color-primary'] }"></view>
          <view class="theme-swatch" :style="{ background: t.vars['--color-bg'] }"></view>
          <view class="theme-swatch" :style="{ background: t.vars['--color-card'] }"></view>
          <view class="theme-swatch" :style="{ background: t.vars['--color-text'] }"></view>
          <view class="theme-swatch theme-swatch-accent" :style="{ background: t.vars['--color-accent'] }"></view>
        </view>
      </view>
      <view class="theme-footer-hint">
        <text class="theme-footer-hint-text">点击立即切换 · 当前 {{ currentTheme ? currentTheme.name : '默认' }}</text>
      </view>
    </scroll-view>

    <!-- 其他分类:占位 -->
    <view v-else class="sheet-cards sheet-empty">
      <text class="sheet-empty-text">「{{ sheetCatName }}」分类暂未开放</text>
    </view>

    <text class="sheet-hint" :class="{ 'sheet-hint-active': isDragging }">长按 0.3 秒拖动改顺序 · 松开即落位 · 最多 6 个 · 当前 {{enabledTabs.length}} / 6</text>
  </view>

  <!-- 图 2:添加选项卡 弹层 -->
  <view v-if="addSheetShow" class="add-mask" @tap="onCloseAddSheet">
    <view class="add-sheet" @tap.stop="">
      <view class="add-topbar">
        <view class="add-topbar-btn" hover-class="add-topbar-btn-hover" @tap="onCloseAddSheet">
          <text class="add-topbar-text">返回</text>
        </view>
        <text class="add-topbar-title">添加选项卡</text>
        <view class="add-topbar-btn" :class="{ disabled: addPicked.length === 0 }" hover-class="add-topbar-btn-hover" @tap="onConfirmAdd">
          <text class="add-topbar-text">确定</text>
        </view>
      </view>

      <view class="add-body">
        <!-- 左侧分组 -->
        <view class="add-cats">
          <view v-for="c in addCats" :key="c.key"
                class="add-cat"
                :class="{ active: addCat === c.key }"
                hover-class="add-cat-hover"
                @tap="addCat = c.key">
            <text class="add-cat-text">{{c.title}}</text>
          </view>
        </view>

        <!-- 右侧:横向滚动的手机缩略图 -->
        <scroll-view class="add-grid-scroll" scroll-x="true" :show-scrollbar="false">
          <view class="add-grid">
            <view v-for="o in currentAddOptions" :key="o.key"
                  class="add-card"
                  :class="{ selected: isPicked(o), disabled: isAlreadyOn(o) }"
                  hover-class="add-card-hover"
                  @tap="onPickAddOption(o)">
              <TabOptionThumbnail :option="o" />
                <view v-if="isPicked(o)" class="add-card-check">✓</view>
                <view v-else-if="isAlreadyOn(o)" class="add-card-on">已添加</view>
                <view v-else class="add-card-add">＋</view>
              <text class="add-card-name">{{o.title}}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</view>
</template>


<script>
import CustomAppPreview from '@/components/custom-app/CustomAppPreview.vue'
import TabOptionThumbnail from '@/components/custom-app/TabOptionThumbnail.vue'
import { loadLayouts, getCurrentLayoutId } from '@/utils/layoutConfig.js'
import { listThemes, getTheme, loadThemeId, saveThemeId, applyThemeToDocument, DEFAULT_THEME_ID } from '@/utils/themeConfig.js'
// 底部 Tab 配置统一从这里读/写,dedup + p-profile 修正都内置了,CustomTabBar 也用同一份
import {
  loadTabs as loadTabsFromStore,
  saveTabs as saveTabsToStore,
  DEFAULT_TABS as DEFAULT_TABS_FROM_STORE,
  ALL_OPTIONS as ALL_OPTIONS_FROM_STORE,
  enabledTabs as enabledTabsFromStore,
  pickAddOption,
  removeTab as removeTabFromStore,
  syncBuiltIn as syncBuiltInFromStore,
  syncLayoutTabs,
  calcCardSize as calcCardSizeFromStore,
  MAX_TABS as MAX_TABS_FROM_STORE,
  SHEET_GAP_RPX,
} from '@/utils/tabConfig.js'

// 本页面独有的分组定义(应用 / 其他)
const ADD_CATS = [
  { key: 'app',   title: '应用' },
  { key: 'other', title: '其他' },
]

// 本页面封装:把外部 util 的 import 重命名成本页面已熟悉的名字,避免大改 methods
const loadTabs = loadTabsFromStore
const saveTabs = saveTabsToStore
const DEFAULT_TABS = DEFAULT_TABS_FROM_STORE
const ALL_OPTIONS = ALL_OPTIONS_FROM_STORE
const MAX_TABS = MAX_TABS_FROM_STORE
const CARD_GAP_RPX = SHEET_GAP_RPX
const calcCardSize = calcCardSizeFromStore

export default {
  components: { CustomAppPreview, TabOptionThumbnail },
  data() {
    return {
      tabs: loadTabs(),
      initialSnapshot: null,
      dirty: false,
      saving: false,
      allOptions: ALL_OPTIONS,
      addCats: ADD_CATS,
      // sheet 顶部水平分类
      sheetCat: 'tab',
      // 添加 sheet 状态
      addSheetShow: false,
      addCat: 'app',
      addPicked: [],
      // 拖动排序状态(长按 300ms 后进入 drag,可拖动换位)
      pressId: '',                  // 当前按住的 tab id(按下即记,长按未触发也算)
      pressTimer: null,             // 长按 300ms 定时器
      pressStartClientX: 0,         // touchstart 时的 clientX(用于判断是否算滑动)
      pressStartClientY: 0,
      pressStartIndex: -1,          // 按下时该 tab 在 enabledTabs 里的 index
      isDragging: false,            // 长按触发后置 true
      dragId: '',                   // 当前拖动的 tab id
      dragOffsetPx: 0,              // 拖动偏移量(px)
      dragTargetIndex: -1,          // 拖动中,落点 index(用于显示 ghost 占位)
      // 真实面板预览(从 layoutConfig 读)
      currentLayoutId: '',
      currentLayoutName: '',
      panelWidgets: [],
      previewLayouts: [],
      previewSlots: [],
      previewGridCols: 4,
      previewActiveLayoutId: '',
      previewActivePageId: '',
      connected: false,
      // 主题(皮肤)状态
      themes: [],
      currentThemeId: '',
      initialThemeId: '',
      statusBarHeight: 24,
    }
  },
  computed: {
    enabledTabs() {
      return (this.tabs || [])
        .filter(function (t) { return t && t.enabled !== false })
        .slice()
        .sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
    },
    canUndo() {
      return this.dirty
    },
    currentAddOptions() {
      const self = this
      return this.addOptions.filter(function (o) { return o.group === self.addCat })
    },
    addOptions() {
      const staticOptions = (this.allOptions || []).slice()
      const layoutOptions = (this.previewLayouts || []).filter(function (layout) {
        return layout && !layout.built_in
      }).map(function (layout) {
        return {
          key: 'layout-' + layout.id,
          group: 'other',
          title: layout.name,
          icon: '▣',
          description: '打开指定面板',
          page: 'panel',
          layoutId: layout.id,
          built_in: false,
        }
      })
      return staticOptions.concat(layoutOptions)
    },
    cardSize() {
      return 108
    },
    cardGap() {
      return 12
    },
    currentTheme() {
      const id = this.currentThemeId || DEFAULT_THEME_ID
      return getTheme(id)
    },
    sheetCatName() {
      const map = { tab: '选项卡', theme: '主题', bg: '背景', font: '字体' }
      return map[this.sheetCat] || this.sheetCat
    },
  },
  onLoad() {
    try {
      const systemInfo = uni.getSystemInfoSync()
      this.statusBarHeight = Number(systemInfo.statusBarHeight) || 24
    } catch (e) {
      this.statusBarHeight = 24
    }
  },
  onShow() {
    this._loadPanelState()
    const fresh = syncLayoutTabs(loadTabs(), this.previewLayouts)
    this.tabs = fresh
    saveTabs(fresh)
    this._loadThemeState()
    this.initialSnapshot = JSON.stringify(fresh)
    this.initialThemeId = this.currentThemeId
    this.dirty = false
  },
  methods: {
    _loadPanelState() {
      // 从 layoutConfig 读当前 layout 的 widgets,用于预览
      try {
        const layouts = loadLayouts()
        const curId = getCurrentLayoutId()
        const layout = layouts.find(function (l) { return l.id === curId }) || layouts[0]
        this.previewLayouts = layouts
        if (layout) {
          this.currentLayoutId = layout.id
          this.currentLayoutName = layout.name
          this.panelWidgets = (layout.widgets || []).filter(function (w) { return w && w.visible !== false })
        } else {
          this.panelWidgets = []
        }
      } catch (e) {
        this.panelWidgets = []
        this.previewLayouts = []
      }
      try {
        const cached = uni.getStorageSync('phonekb.last_layouts') || {}
        const keyboardLayouts = Array.isArray(cached.layouts) ? cached.layouts : []
        const activeId = cached.active_layout_id || (keyboardLayouts[0] && keyboardLayouts[0].id) || ''
        const activeLayout = keyboardLayouts.find(function (item) { return item.id === activeId }) || keyboardLayouts[0]
        const activePageId = cached.active_page_id || (activeLayout && activeLayout.pages && activeLayout.pages[0] && activeLayout.pages[0].id) || ''
        const activePage = activeLayout && activeLayout.pages
          ? activeLayout.pages.find(function (item) { return item.id === activePageId }) || activeLayout.pages[0]
          : null
        this.previewSlots = activePage ? (activePage.slots || []) : []
        this.previewGridCols = Number(cached.grid_cols) || 4
        this.previewActiveLayoutId = activeId
        this.previewActivePageId = activePage ? activePage.id : ''
      } catch (e) {
        this.previewSlots = []
        this.previewGridCols = 4
        this.previewActiveLayoutId = ''
        this.previewActivePageId = ''
      }
      // 连接状态(轻量读 globalData)
      try {
        const app = typeof getApp === 'function' ? getApp({ allowDefault: true }) : null
        const gd = (app && app.globalData) || {}
        this.connected = !!(gd.host) // 简化判断
      } catch (e) {
        this.connected = false
      }
    },
    _loadThemeState() {
      try {
        this.themes = listThemes()
        this.currentThemeId = loadThemeId()
      } catch (e) {
        this.themes = []
        this.currentThemeId = DEFAULT_THEME_ID
      }
    },
    onPickTheme(t) {
      if (!t || !t.id) return
      if (this.currentThemeId === t.id) return
      try {
        this.currentThemeId = t.id
        this._markDirty()
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
        uni.showToast({ title: '已应用到预览', icon: 'success', duration: 900 })
      } catch (e) {
        uni.showToast({ title: '切换失败', icon: 'none', duration: 1000 })
      }
    },
    onBack() {
      if (this.dirty) {
        const self = this
        uni.showModal({
          title: '放弃修改?',
          content: '当前修改尚未保存,确定退出?',
          success: function (res) {
            if (!res.confirm) return
            self._restore()
            uni.navigateBack({ delta: 1 })
          },
        })
        return
      }
      uni.navigateBack({ delta: 1 })
    },
    _restore() {
      if (this.initialSnapshot) {
        try { this.tabs = JSON.parse(this.initialSnapshot) } catch (e) {}
        this.currentThemeId = this.initialThemeId || DEFAULT_THEME_ID
        this.dirty = false
      }
    },
    // 右上角 ↺:重置回出厂默认布局(面板/布局/我的),覆盖当前所有 tab 配置
    onResetDefault() {
      const self = this
      uni.showModal({
        title: '重置为默认布局?',
        content: '选项卡和主题将恢复默认设置。继续?',
        success: function (res) {
          if (!res.confirm) return
          self.tabs = DEFAULT_TABS.map(function (t) { return Object.assign({}, t) })
          self.currentThemeId = DEFAULT_THEME_ID
          self._markDirty()
          try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
          uni.showToast({ title: '已重置为默认布局', icon: 'success', duration: 900 })
        },
      })
    },
    onCardTap(t) {
      // 短按:不做额外操作
    },
    onRemoveTab(t) {
      // 内置 Tab(面板/布局/我的)不可删除
      if (t && t.built_in) {
        uni.showToast({ title: '内置 Tab 不能删除', icon: 'none', duration: 900 })
        return
      }
      // 至少保留 1 个
      if (this.enabledTabs.length <= 1) {
        uni.showToast({ title: '至少保留 1 个 Tab', icon: 'none', duration: 900 })
        return
      }
      const next = (this.tabs || []).map(function (x) {
        if (x.id === t.id) return Object.assign({}, x, { enabled: false })
        return x
      })
      this.tabs = next
      this._markDirty()
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    // === 长按拖动排序(自定义 300ms 长按检测,不用 uni-app 的 @longpress) ===
    LONG_PRESS_MS: 300,             // 长按阈值
    PRESS_MOVE_CANCEL_PX: 10,       // 滑动超过这个距离就取消长按(算滚动了)

    onTouchStart(e, id, idx) {
      if (!e || !e.touches || !e.touches[0]) return
      const t = e.touches[0]
      this.pressId = id
      this.pressStartClientX = t.clientX || 0
      this.pressStartClientY = t.clientY || 0
      this.pressStartIndex = typeof idx === 'number' ? idx : -1
      const self = this
      if (this.pressTimer) clearTimeout(this.pressTimer)
      this.pressTimer = setTimeout(function () {
        self.pressTimer = null
        // 长按触发:进入拖动模式
        self.isDragging = true
        self.dragId = id
        self.dragOffsetPx = 0
        self.dragTargetIndex = self.pressStartIndex
        try { uni.vibrateShort({ type: 'medium' }) } catch (err) {}
      }, self.LONG_PRESS_MS)
    },

    onTouchMove(e) {
      if (!e || !e.touches || !e.touches[0]) return
      const t = e.touches[0]
      const cx = t.clientX || 0
      const cy = t.clientY || 0

      // 还没进入 drag:检测是否算滑动 -> 取消长按
      if (!this.isDragging) {
        const dx = Math.abs(cx - this.pressStartClientX)
        const dy = Math.abs(cy - this.pressStartClientY)
        if (dx > this.PRESS_MOVE_CANCEL_PX || dy > this.PRESS_MOVE_CANCEL_PX) {
          if (this.pressTimer) {
            clearTimeout(this.pressTimer)
            this.pressTimer = null
          }
          this.pressId = ''
        }
        return
      }

      // drag 模式:更新偏移(相对手指起点)
      try { e.preventDefault && e.preventDefault() } catch (err) {}
      this.dragOffsetPx = cx - this.pressStartClientX

      // 计算新落点 index
      const stepRpx = this.cardSize + this.cardGap
      const stepPx = typeof uni.upx2px === 'function'
        ? uni.upx2px(stepRpx)
        : stepRpx * ((uni.getSystemInfoSync && uni.getSystemInfoSync().windowWidth) || 375) / 750
      let newTarget = Math.round(this.dragOffsetPx / stepPx) + this.pressStartIndex
      const maxIdx = this.enabledTabs.length - 1
      if (newTarget < 0) newTarget = 0
      if (newTarget > maxIdx) newTarget = maxIdx

      // 实时换位:落点变了就把这个 tab 在数组里挪过去,其它卡片真的让出位置
      if (newTarget !== this.pressStartIndex) {
        const sorted = this.enabledTabs.slice()
        const moved = sorted.splice(this.pressStartIndex, 1)[0]
        sorted.splice(newTarget, 0, moved)
        const orderMap = {}
        sorted.forEach(function (tt, i) { orderMap[tt.id] = i })
        const next = (this.tabs || []).map(function (x) {
          if (orderMap.hasOwnProperty(x.id)) {
            return Object.assign({}, x, { order: orderMap[x.id], enabled: true })
          }
          return x
        })
        this.tabs = next
        // 卡片天然位置已经移动了一个或多个卡位，同步移动触摸锚点。
        // 否则下一帧会重新用旧起点计算，把补偿覆盖掉，卡片会突然跑远。
        const deltaIdx = newTarget - this.pressStartIndex
        this.pressStartClientX = this.pressStartClientX + deltaIdx * stepPx
        this.dragOffsetPx = cx - this.pressStartClientX
        this.pressStartIndex = newTarget
        this.dragTargetIndex = newTarget
        // 每次跨过一道,轻振动
        try { uni.vibrateShort({ type: 'light' }) } catch (err) {}
      }
    },

    onTouchEnd() {
      if (this.pressTimer) {
        clearTimeout(this.pressTimer)
        this.pressTimer = null
      }
      // 换位已在 onTouchMove 实时完成,这里只标记 dirty + 收尾
      if (this.isDragging) {
        this._markDirty()
      }
      // 重置所有状态
      this.pressId = ''
      this.dragId = ''
      this.pressStartIndex = -1
      this.dragTargetIndex = -1
      this.dragOffsetPx = 0
      this.isDragging = false
    },
    // === 添加 sheet ===
    onOpenAddSheet() {
      if (this.enabledTabs.length >= MAX_TABS) {
        uni.showToast({ title: '已达 6 个上限', icon: 'none', duration: 900 })
        return
      }
      this.addPicked = []
      this.addCat = 'app'
      this.addSheetShow = true
    },
    onCloseAddSheet() {
      this.addSheetShow = false
      this.addPicked = []
    },
    isPicked(o) {
      return this.addPicked.indexOf(o.key) >= 0
    },
    isAlreadyOn(o) {
      return (this.tabs || []).some(function (t) { return t.id === o.key && t.enabled !== false })
    },
    onPickAddOption(o) {
      if (this.isAlreadyOn(o)) {
        uni.showToast({ title: '该选项已添加到底部', icon: 'none', duration: 900 })
        return
      }
      const room = MAX_TABS - this.enabledTabs.length
      if (room <= 0) {
        uni.showToast({ title: '已达上限', icon: 'none', duration: 900 })
        return
      }
      const next = this.addPicked.slice()
      const index = next.indexOf(o.key)
      if (index >= 0) next.splice(index, 1)
      else if (next.length < room) next.push(o.key)
      else {
        uni.showToast({ title: '最多还能加 ' + room + ' 个', icon: 'none', duration: 1000 })
        return
      }
      this.addPicked = next
    },
    onConfirmAdd() {
      const pickedSet = {}
      this.addPicked.forEach(function (key) { pickedSet[key] = true })
      const picks = this.addOptions.filter(function (option) { return pickedSet[option.key] })
      if (picks.length === 0) return
      const pickedIds = picks.map(function (x) { return x.key })
      const filtered = (this.tabs || []).filter(function (t) { return pickedIds.indexOf(t.id) < 0 })
      const maxOrder = filtered.reduce(function (m, t) { return Math.max(m, t.order || 0) }, -1)
      const newTabs = picks.map(function (x, i) {
        return {
          id: x.key,
          page: x.page,
          label: x.title,
          icon: x.icon,
          enabled: true,
          order: maxOrder + 1 + i,
          built_in: !!x.built_in,
          widgetType: x.widgetType || '',
          layoutId: x.layoutId || '',
        }
      })
      this.tabs = filtered.concat(newTabs)
      this._markDirty()
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      uni.showToast({ title: '已添加 ' + picks.length + ' 项', icon: 'success', duration: 900 })
      this.onCloseAddSheet()
    },
    _markDirty() {
      this.dirty = JSON.stringify(this.tabs) !== this.initialSnapshot || this.currentThemeId !== this.initialThemeId
    },
    onSave() {
      if (this.saving) return
      if (!this.dirty) {
        // \u6CA1\u4FEE\u6539\u4E5F\u8DF3\u8FDB,\u4E0D\u8BA9\u7528\u6237\u5361\u5728\u8FD9\u91CC
        uni.navigateBack({ delta: 1 })
        return
      }
      this.saving = true
      const self = this
      const ok = saveTabs(this.tabs)
      if (ok) {
        try {
          const theme = getTheme(self.currentThemeId || DEFAULT_THEME_ID)
          saveThemeId(self.currentThemeId || DEFAULT_THEME_ID)
          applyThemeToDocument(theme)
        } catch (e) {}
        self.initialSnapshot = JSON.stringify(self.tabs)
        self.initialThemeId = self.currentThemeId
        self.dirty = false
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
        uni.showToast({ title: '已保存', icon: 'success', duration: 800 })
        // \u4FDD\u5B58\u540E\u7ACB\u5373\u8DF3\u56DE\u4E0A\u4E00\u9875;CustomTabBar \u5DF2\u7ECF\u542C\u5230 TAB_UPDATED_EVENT,\r
        // \u6240\u4EE5\u8DF3\u56DE\u4E4B\u540E\u5E95\u90E8 tab \u5DF2\u7ECF\u662F\u65B0\u7684\u3002
        setTimeout(function () {
          self.saving = false
          uni.navigateBack({ delta: 1 })
        }, 250)
      } else {
        uni.showToast({ title: '保存失败', icon: 'none', duration: 1200 })
        self.saving = false
      }
    },
    tabDisplayIcon(tab) {
      const icons = {
        'p-panel': '⌂',
        'p-layout': '▣',
        'p-devices': '▤',
        'p-profile': '♙',
        'w-key-grid': '⌘',
        'w-text-input': '▦',
        'w-mouse-control': '◉',
        'w-volume': '♪',
      }
      return icons[tab && tab.id] || '◇'
    },
  },
}
</script>
<style scoped>
﻿/* ===== Fluent base v2 (azure+aurora) ===== */
.page, .container {
  min-height: 100vh !important;
  padding: 24rpx 24rpx 64rpx !important;
  box-sizing: border-box;
  position: relative;
  overflow-x: hidden;
  background: var(--fluent-bg-azure) !important;
}
.page::before, .container::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--fluent-bg-aurora);
  pointer-events: none;
  z-index: 0;
}
.page > view, .container > view { position: relative; z-index: 1; }
/* Section / Card (acrylic) */
.section, .card {
  background: var(--fluent-acrylic-strong) !important;
  border: 1rpx solid var(--fluent-hairline) !important;
  border-radius: var(--radius-fluent-lg) !important;
  box-shadow: var(--shadow-fluent-2) !important;
  padding: 22rpx 24rpx !important;
  margin: 0 24rpx 18rpx !important;
  backdrop-filter: blur(32rpx) saturate(140%);
  -webkit-backdrop-filter: blur(32rpx) saturate(140%);
  position: relative;
}
/* Primary button */
.btn-primary {
  background: var(--color-primary) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 14rpx !important;
  font-weight: 600 !important;
  box-shadow: 0 6rpx 14rpx rgba(47,120,246,0.22) !important;
}
.btn-primary[disabled], .btn-disabled { background: var(--color-bg-alt) !important; color: var(--color-text-light) !important; box-shadow: none !important; }
/* Secondary button */
.btn-secondary {
  background: var(--color-bg-alt) !important;
  color: var(--color-text-mid) !important;
  border: 1rpx solid var(--fluent-hairline) !important;
  border-radius: 14rpx !important;
}
/* Input */
.input, .form-input, .modal-input {
  background: var(--color-bg-alt) !important;
  border: 1rpx solid var(--fluent-hairline) !important;
  border-radius: 12rpx !important;
  color: var(--color-text) !important;
}
.input:focus, .form-input:focus, .modal-input:focus { border-color: var(--color-primary) !important; background: #FFFFFF !important; }

/* ===== 页面外壳:浅蓝白外框 + 深色手机外壳 ===== */
.page {
  min-height: 100vh;
  background:
    radial-gradient(85% 32% at 8% 0%, rgba(47,120,246,0.12) 0%, rgba(244,248,253,0) 76%),
    var(--color-bg);
  color: var(--color-text);
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
}

/* ===== 顶部导航(浅色,白字) ===== */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22rpx 24rpx 16rpx;
  flex-shrink: 0;
}
.topbar-back {
  width: 64rpx; height: 64rpx;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  transition: background-color 120ms var(--ease-fluent);
}
.topbar-back-hover { background: var(--color-primary-bg); }
.topbar-back-icon { font-size: 48rpx; color: var(--color-text); line-height: 1; font-weight: 300; }
.topbar-title {
  flex: 1;
  text-align: center;
  font-size: 32rpx;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.4rpx;
}
.topbar-icon {
  width: 64rpx; height: 64rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.6);
  border: 1rpx solid var(--fluent-hairline);
  display: flex; align-items: center; justify-content: center;
  margin-left: 12rpx;
  transition: background-color 120ms var(--ease-fluent), border-color 120ms var(--ease-fluent);
}
.topbar-icon.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 4rpx 10rpx rgba(47,120,246,0.22);
}
.topbar-icon.disabled { opacity: 0.35; }
.topbar-icon-hover { background: var(--color-primary-bg); }
.topbar-icon.active.topbar-icon-hover { background: var(--color-primary-press); }
.topbar-icon-text { font-size: 32rpx; color: var(--color-text-mid); line-height: 1; font-weight: 600; }
.topbar-icon.active .topbar-icon-text { color: #FFFFFF; }

/* ===== 大手机预览区 ===== */
.preview-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16rpx 48rpx 16rpx;
  min-height: 0;
  overflow: hidden;
}
.phone-frame {
  width: 460rpx;
  max-width: 100%;
  background: #1F2937;
  border-radius: 48rpx;
  padding: 12rpx;
  box-shadow: 0 24rpx 60rpx rgba(20,40,70,0.32);
}
.phone-screen {
  background: #FFFFFF;
  border-radius: 36rpx;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 680rpx;
}
.phone-statusbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16rpx 24rpx 6rpx;
  font-size: 20rpx;
  color: #1C1C1C;
}
.phone-body {
  flex: 1;
  padding: 8rpx 16rpx 12rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  background: #F4F8FD;
  overflow: hidden;
}

.mini-status {
  display: flex; align-items: center; gap: 8rpx;
  padding: 8rpx 12rpx;
  background: #FFFFFF;
  border-radius: 12rpx;
  font-size: 20rpx;
  color: #1C1C1C;
  box-shadow: 0 1rpx 2rpx rgba(0,0,0,0.04);
}
.mini-status-dot { width: 12rpx; height: 12rpx; border-radius: 50%; flex-shrink: 0; }
.mini-status-dot.on { background: var(--color-success); }
.mini-status-dot.off { background: #B3B3B3; }
.mini-status-text { font-weight: 500; }
.mini-status-name { margin-left: auto; color: #8A8A8A; font-size: 18rpx; }

.mini-widget {
  background: #FFFFFF;
  border-radius: 14rpx;
  padding: 10rpx 12rpx;
  display: flex; flex-direction: column;
  gap: 6rpx;
  box-shadow: 0 1rpx 2rpx rgba(0,0,0,0.04);
}
.mini-widget-head { display: flex; align-items: center; gap: 6rpx; }
.mini-widget-icon { font-size: 20rpx; }
.mini-widget-title { font-size: 18rpx; font-weight: 600; color: #1C1C1C; }

.mini-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4rpx;
}
.mini-grid-cell {
  height: 32rpx;
  background: #E5E7EB;
  border-radius: 6rpx;
}

.mini-input-row { display: flex; align-items: center; gap: 6rpx; }
.mini-input-box { flex: 1; height: 28rpx; background: #E5E7EB; border-radius: 8rpx; }
.mini-input-btn {
  width: 44rpx; height: 28rpx;
  background: var(--color-primary);
  color: #FFFFFF;
  font-size: 16rpx;
  border-radius: 8rpx;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700;
}

.mini-mouse { display: flex; flex-direction: column; gap: 6rpx; }
.mini-trackpad { height: 56rpx; background: #E5E7EB; border-radius: 8rpx; }
.mini-mouse-btns { display: flex; gap: 4rpx; }
.mini-mouse-btn {
  flex: 1;
  height: 24rpx;
  background: #E5E7EB;
  border-radius: 6rpx;
  font-size: 14rpx;
  color: #1C1C1C;
  display: flex; align-items: center; justify-content: center;
  font-weight: 500;
}

.mini-volume { display: flex; align-items: center; gap: 6rpx; }
.mini-volume-icon { font-size: 18rpx; }
.mini-volume-bar {
  flex: 1;
  height: 8rpx;
  background: #E5E7EB;
  border-radius: 4rpx;
  overflow: hidden;
}
.mini-volume-fill { height: 100%; background: var(--color-primary); border-radius: 4rpx; }
.mini-volume-pct { font-size: 14rpx; color: #616161; min-width: 48rpx; text-align: right; }

.mini-unknown { font-size: 16rpx; color: #8A8A8A; }

.phone-tabs {
  display: flex; align-items: center;
  background: #FFFFFF;
  border-top: 1rpx solid #E5E7EB;
  padding: 12rpx 0 16rpx;
  min-height: 90rpx;
}
.phone-tab {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; gap: 2rpx;
  color: #8A8A8A;
}
.phone-tab-icon { font-size: 28rpx; line-height: 1; }
.phone-tab-label { font-size: 16rpx; }
.phone-tab-empty {
  flex: 1;
  text-align: center;
  color: #8A8A8A;
  font-size: 18rpx;
}

.preview-hint {
  font-size: 24rpx;
  color: var(--color-text-light);
  margin-top: 18rpx;
  text-align: center;
  letter-spacing: 0.2rpx;
}

/* ===== 底部 sheet(白底 Fluent) ===== */
.sheet {
  background: rgba(255,255,255,0.96);
  border: 1rpx solid var(--fluent-hairline);
  border-top-left-radius: 28rpx;
  border-top-right-radius: 28rpx;
  padding: 18rpx 0 calc(18rpx + env(safe-area-inset-bottom));
  flex-shrink: 0;
  box-shadow: 0 -16rpx 40rpx rgba(31,48,70,0.10);
  backdrop-filter: blur(20rpx) saturate(160%);
  -webkit-backdrop-filter: blur(20rpx) saturate(160%);
}
.sheet-cats {
  display: flex;
  gap: 10rpx;
  padding: 10rpx 26rpx 28rpx;
  overflow-x: auto;
}
.sheet-cat {
  padding: 26rpx 28rpx;
  border-radius: 999rpx;
  font-size: 32rpx;
  color: var(--color-text-mid);
  background: var(--color-bg-alt);
  border: 1rpx solid var(--fluent-hairline);
  font-weight: 500;
  white-space: nowrap;
  transition: background-color 120ms var(--ease-fluent), color 120ms var(--ease-fluent), border-color 120ms var(--ease-fluent);
}
.sheet-cat.active {
  background: var(--color-primary);
  color: #FFFFFF;
  border-color: var(--color-primary);
  box-shadow: 0 4rpx 10rpx rgba(47,120,246,0.22);
}
.sheet-cards {
  padding: 8rpx 24rpx 4rpx;
  white-space: nowrap;
}
.sheet-themes { white-space: normal; padding: 8rpx 20rpx 4rpx; }
.sheet-card {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 8rpx;
  margin-right: 16rpx;
  background: rgba(255,255,255,0.92);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: 18rpx;
  position: relative;
  transition: background-color 120ms var(--ease-fluent), border-color 120ms var(--ease-fluent), transform 90ms var(--ease-fluent);
}
.sheet-card-hover { background: var(--color-primary-bg); border-color: var(--color-primary); }
.sheet-card.is-pressing { background: var(--color-primary-bg); border-color: var(--color-primary); transform: scale(0.96); }
.sheet-card.is-dragging {
  box-shadow: 0 10rpx 24rpx rgba(31,48,70,0.20);
  transition: none;
}
.sheet-card.is-builtin { background: rgba(47,120,246,0.06); border-color: rgba(47,120,246,0.18); }
.sheet-card-badge {
  position: absolute;
  top: 6rpx; right: 6rpx;
  width: 36rpx; height: 36rpx;
  border-radius: 50%;
  background: var(--color-danger-bg);
  color: var(--color-danger);
  display: flex; align-items: center; justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
  border: 1rpx solid rgba(209,52,56,0.18);
}
.sheet-card-badge-hover { background: var(--color-danger); color: #FFFFFF; }
.sheet-card-badge-text { line-height: 1; }
.sheet-card-icon {
  width: 80rpx; height: 80rpx;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  border-radius: 22rpx;
  font-size: 44rpx;
  line-height: 1;
}
.sheet-card-label {
  font-size: 22rpx;
  color: var(--color-text);
  font-weight: 500;
  letter-spacing: 0.2rpx;
}
.sheet-card-add {
  background: rgba(255,255,255,0.92);
  border-style: dashed;
  border-color: var(--color-primary);
  color: var(--color-primary);
  justify-content: center;
}
.sheet-card-add-icon { font-size: 56rpx; font-weight: 300; line-height: 1; }

/* ===== Theme Card ===== */
.theme-card {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  padding: 14rpx 18rpx;
  margin-bottom: 12rpx;
  background: rgba(255,255,255,0.94);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: 18rpx;
  transition: border-color 120ms var(--ease-fluent), background-color 120ms var(--ease-fluent), transform 90ms var(--ease-fluent);
}
.theme-card.active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: 0 6rpx 14rpx rgba(47,120,246,0.12);
}
.theme-card-hover { background: var(--color-primary-bg); }
.theme-card-head {
  display: flex; align-items: center; gap: 10rpx;
}
.theme-card-emoji { font-size: 30rpx; line-height: 1; }
.theme-card-name {
  font-size: 27rpx;
  font-weight: 600;
  color: var(--color-text);
  flex: 1;
  letter-spacing: 0.2rpx;
}
.theme-card-check {
  width: 36rpx; height: 36rpx;
  border-radius: 50%;
  background: var(--color-primary);
  color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-size: 24rpx;
  font-weight: 700;
}
.theme-card-check-text { line-height: 1; }
.theme-card-style {
  font-size: 22rpx;
  color: var(--color-text-light);
  line-height: 1.4;
}
.theme-card-swatches {
  display: flex; align-items: center; gap: 8rpx;
  margin-top: 4rpx;
}
.theme-swatch {
  width: 36rpx; height: 36rpx;
  border-radius: 8rpx;
  border: 1rpx solid rgba(0,0,0,0.06);
}
.theme-swatch-accent {
  margin-left: auto;
}
.theme-footer-hint {
  padding: 8rpx 0 4rpx;
  text-align: center;
}
.theme-footer-hint-text {
  font-size: 22rpx;
  color: var(--color-text-light);
}

.sheet-empty {
  padding: 80rpx 32rpx 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240rpx;
}
.sheet-empty-text {
  font-size: 26rpx;
  color: var(--color-text-light);
}

.sheet-hint {
  display: block;
  padding: 12rpx 24rpx 0;
  font-size: 22rpx;
  color: var(--color-text-light);
  text-align: center;
  letter-spacing: 0.2rpx;
}
.sheet-hint-active { color: var(--color-primary); font-weight: 500; }

/* ===== 添加 Tab 浮层 ===== */
.add-mask {
  position: fixed;
  inset: 0;
  background: rgba(31,48,70,0.32);
  backdrop-filter: blur(14rpx);
  -webkit-backdrop-filter: blur(14rpx);
  z-index: 500;
  display: flex;
  align-items: flex-end;
}
.add-sheet {
  width: 100%;
  height: 32vh;
  background: rgba(255,255,255,0.96);
  border: 1rpx solid var(--fluent-hairline);
  border-top-left-radius: 32rpx;
  border-top-right-radius: 32rpx;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-fluent-flyout);
}
.add-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18rpx 24rpx 14rpx;
  border-bottom: 1rpx solid var(--color-divider);
  flex-shrink: 0;
}
.add-topbar-btn {
  padding: 10rpx 18rpx;
  border-radius: 12rpx;
  transition: background-color 120ms var(--ease-fluent);
}
.add-topbar-btn-hover { background: var(--color-primary-bg); }
.add-topbar-btn.disabled { opacity: 0.35; }
.add-topbar-text {
  font-size: 26rpx;
  color: var(--color-text);
  font-weight: 500;
}
.add-topbar-btn:first-child .add-topbar-text { color: var(--color-text-mid); }
.add-topbar-title { font-size: 30rpx; font-weight: 600; color: var(--color-text); }

.add-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.add-cats {
  width: 160rpx;
  flex-shrink: 0;
  background: var(--color-bg-alt);
  padding: 20rpx 0;
  display: flex; flex-direction: column;
  gap: 6rpx;
}
.add-cat {
  padding: 32rpx 0;
  text-align: center;
  border-left: 6rpx solid transparent;
  transition: background-color 120ms var(--ease-fluent);
}
.add-cat-hover { background: rgba(255,255,255,0.6); }
.add-cat.active {
  background: #FFFFFF;
  border-bottom: 4rpx solid var(--color-primary);
}
.add-cat-text {
  font-size: 28rpx;
  color: var(--color-text);
  font-weight: 500;
}
.add-cat.active .add-cat-text { color: var(--color-primary); font-weight: 600; }

.add-grid-scroll { flex: 1; min-height: 0; overflow: hidden; }
.add-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: flex-start;
  gap: 20rpx;
  padding: 16rpx 24rpx 16rpx;
  box-sizing: border-box;
  width: max-content;
}
.add-card {
  width: 160rpx;
  display: inline-flex;
  flex-direction: column; align-items: center;
  gap: 8rpx;
  padding: 6rpx;
  border-radius: 14rpx;
  border: 2rpx solid transparent;
  flex-shrink: 0;
  flex-grow: 0;
  transition: background-color 120ms var(--ease-fluent), border-color 120ms var(--ease-fluent);
}
.add-card-hover { background: var(--color-primary-bg); }
.add-card.selected {
  border-color: var(--color-primary);
  background: rgba(47,120,246,0.08);
}
.add-card.disabled { opacity: 0.5; }
.add-thumb {
  width: 172rpx; height: 380rpx;
  background: linear-gradient(180deg, #E0F2FE 0%, #DBEAFE 100%);
  border-radius: 16rpx;
  padding: 10rpx;
  display: flex; flex-direction: column;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4rpx 10rpx rgba(0,0,0,0.06);
}
.add-thumb-statusbar {
  display: flex; justify-content: flex-end;
  font-size: 14rpx;
  color: #1C1C1C;
  margin-bottom: 4rpx;
}
.add-thumb-body {
  flex: 1;
  display: flex; flex-direction: column;
  gap: 8rpx;
  background: #FFFFFF;
  border-radius: 10rpx;
  padding: 12rpx;
  align-items: center;
  justify-content: center;
}
.add-thumb-icon-wrap {
  width: 56rpx; height: 56rpx;
  background: #EAF6FF;
  border-radius: 12rpx;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 6rpx;
}
.add-thumb-icon { font-size: 32rpx; }
.add-thumb-line { height: 10rpx; background: #E5E7EB; border-radius: 5rpx; width: 80%; }
.add-thumb-line.short { width: 50%; }
.add-card-check {
  position: absolute;
  top: 10rpx; right: 10rpx;
  width: 32rpx; height: 32rpx;
  border-radius: 50%;
  background: var(--color-primary);
  color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
}
.add-card-on {
  position: absolute;
  top: 10rpx; left: 10rpx;
  background: rgba(0,0,0,0.5);
  color: #FFFFFF;
  font-size: 16rpx;
  padding: 4rpx 10rpx;
  border-radius: 999rpx;
}
.add-card-add {
  position: absolute;
  bottom: 10rpx; right: 10rpx;
  width: 36rpx; height: 36rpx;
  border-radius: 50%;
  background: var(--color-primary);
  color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-size: 28rpx;
  font-weight: 300;
  box-shadow: 0 2rpx 4rpx rgba(47,120,246,0.30);
}
.add-card-name {
  font-size: 22rpx;
  color: var(--color-text);
  font-weight: 500;
}
.phone-time { font-size: 22rpx; color: #1C1C1C; font-weight: 600; }
.phone-signal { font-size: 18rpx; color: #1C1C1C; letter-spacing: -1rpx; }
.add-thumb-time { position: absolute; top: 6rpx; right: 6rpx; font-size: 12rpx; color: #1C1C1C; padding: 2rpx 6rpx; border-radius: 4rpx; background: rgba(255,255,255,0.7); }

/* ===== 自定义 App 编辑器重构 ===== */
.page {
  min-height: 100vh !important;
  height: 100vh;
  padding: 0 0 calc(268rpx + env(safe-area-inset-bottom)) !important;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: radial-gradient(90% 40% at 8% 0%, rgba(47,120,246,0.10) 0%, rgba(244,248,253,0) 72%), #F4F8FD !important;
}
.page::before { display: none; }
.topbar {
  min-height: 82rpx;
  padding-left: 22rpx;
  padding-right: 22rpx;
  padding-bottom: 8rpx;
  border-bottom: 1rpx solid rgba(123,148,175,0.10);
  background: rgba(255,255,255,0.78);
  backdrop-filter: blur(24rpx);
  -webkit-backdrop-filter: blur(24rpx);
  box-sizing: border-box;
}
.topbar-back,
.topbar-icon {
  width: 56rpx;
  height: 56rpx;
  border-radius: 15rpx;
  background: transparent;
  border: 1rpx solid transparent;
  box-shadow: none;
}
.topbar-back-hover,
.topbar-icon-hover { background: #EEF5FD; border-color: #DCE6F1; }
.topbar-back-icon { font-size: 42rpx; }
.topbar-title { font-size: 29rpx; font-weight: 700; }
.topbar-icon { margin-left: 6rpx; }
.topbar-icon.active { background: #2F78F6; border-color: #2F78F6; box-shadow: 0 5rpx 13rpx rgba(47,120,246,0.20); }
.topbar-icon-text { font-size: 29rpx; }

.preview-area {
  flex: 1;
  min-height: 0;
  padding: 18rpx 24rpx 12rpx;
  display: flex;
  align-items: stretch;
  justify-content: flex-start;
  overflow: hidden;
}

.page > .sheet {
  position: fixed !important;
  left: 20rpx;
  right: 20rpx;
  bottom: calc(14rpx + env(safe-area-inset-bottom));
  z-index: 120;
  height: 358rpx;
  padding: 16rpx 0;
  margin: 0;
  padding: 16rpx 0 calc(16rpx + env(safe-area-inset-bottom));
  border: 1rpx solid #DCE6F1;
  border-radius: 24rpx;
  background: rgba(255,255,255,0.96);
  box-shadow: 0 12rpx 34rpx rgba(47,78,113,0.09);
  backdrop-filter: blur(22rpx);
  -webkit-backdrop-filter: blur(22rpx);
  overflow: hidden;
  box-sizing: border-box;
}
.sheet-cats {
  padding: 8rpx 22rpx 24rpx;
  display: flex;
  gap: 10rpx;
  overflow: visible;
}
.sheet-cat {
  flex: 1;
  min-width: 0;
  padding: 9rpx 6rpx;
  border-radius: 8rpx;
  background: #EEF3F8;
  border: 1rpx solid transparent;
  color: #607087;
  font-size: 20rpx;
  text-align: center;
}
.sheet-cat.active {
  background: #FFFFFF;
  border-color: #D7E3F0;
  color: #2F78F6;
  box-shadow: 0 3rpx 10rpx rgba(47,78,113,0.08);
}
.sheet-cat.disabled {
  color: #A7B1BE;
  background: #F5F7FA;
}
.sheet-cards { padding: 10rpx 22rpx 8rpx; }
.sheet-card {
  padding: 14rpx 10rpx 12rpx;
  border-radius: 17rpx;
  background: #FBFDFF;
  border-color: #DCE6F1;
  box-shadow: 0 5rpx 15rpx rgba(47,78,113,0.07);
  box-sizing: border-box;
}
.sheet-card-icon {
  width: 56rpx;
  height: 56rpx;
  border-radius: 13rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 24rpx;
}
.sheet-card-label { margin-top: 3rpx; font-size: 18rpx; font-weight: 650; line-height: 1; }
.sheet-card-badge {
  top: -8rpx;
  right: -8rpx;
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  z-index: 4;
  background: #FFFFFF;
  color: #D13438;
  border: 1rpx solid #DCE6F1;
  box-shadow: 0 4rpx 10rpx rgba(47,78,113,0.15);
}
.sheet-card-badge-text { font-size: 22rpx; font-weight: 700; }
.sheet-card-add { border-style: solid; border-color: #DCE6F1; background: #FBFDFF; justify-content: flex-start; }
.sheet-card-add-icon-wrap { background: #F0F5FB; color: #607087; }
.sheet-card-add-icon { font-size: 32rpx; font-weight: 500; line-height: 1; }
.sheet-hint { padding: 12rpx 22rpx 0; font-size: 16rpx; }
.sheet-themes { height: 150rpx; max-height: 150rpx; padding: 4rpx 18rpx; }
.theme-card { padding: 12rpx 15rpx; margin-bottom: 9rpx; border-radius: 15rpx; }
.theme-card-name { font-size: 23rpx; }
.theme-card-style { font-size: 19rpx; }
.theme-swatch { width: 29rpx; height: 29rpx; border-radius: 7rpx; }

.page > .add-mask {
  position: fixed !important;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 500;
  background: rgba(23,32,51,0.38);
}
.add-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: calc(358rpx + env(safe-area-inset-bottom));
  min-height: 0;
  border-top-left-radius: 28rpx;
  border-top-right-radius: 28rpx;
  background: rgba(255,255,255,0.98);
}
.add-topbar {
  min-height: 62rpx;
  padding: 7rpx 18rpx;
  box-sizing: border-box;
}
.add-topbar-btn { min-width: 84rpx; padding: 8rpx 12rpx; }
.add-topbar-title { font-size: 27rpx; font-weight: 700; }
.add-topbar-text { font-size: 22rpx; color: #2F78F6; }
.add-topbar-btn:first-child .add-topbar-text { color: #607087; }
.add-cats {
  width: 104rpx;
  padding: 8rpx 0;
  gap: 20rpx;
  background: #F1F5F9;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.add-cat {
  flex: 1;
  min-height: 70rpx;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-left-width: 5rpx;
}
.add-cat-text { font-size: 21rpx; }
.add-grid-scroll { padding-top: 6rpx; }
.add-grid {
  gap: 10rpx;
  padding: 8rpx 14rpx 10rpx;
}
.add-card {
  width: 180rpx;
  padding: 4rpx;
  position: relative;
  gap: 7rpx;
  border-radius: 16rpx;
  box-sizing: border-box;
}
.add-card.selected { border-color: #2F78F6; background: #F3F8FF; }
.add-card.disabled { opacity: 0.52; }
.add-card-name { font-size: 17rpx; font-weight: 600; }
.add-card-check,
.add-card-add {
  top: 12rpx;
  right: 12rpx;
  bottom: auto;
  width: 34rpx;
  height: 34rpx;
  border: 3rpx solid #FFFFFF;
  box-sizing: border-box;
}
.add-card-on {
  top: 12rpx;
  left: 12rpx;
  padding: 4rpx 8rpx;
  font-size: 15rpx;
}
</style>
