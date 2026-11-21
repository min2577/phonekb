<template>
  <view class="gamepad-page">
    <view class="topbar">
      <button class="back-button" aria-label="返回面板" @tap="onBack">
        <text class="back-button-icon">←</text>
      </button>
      <view class="runtime-title">
        <text class="runtime-layout-name">{{ activeLayout ? activeLayout.name : '游戏手柄' }}</text>
        <text class="runtime-mode">{{ toolsOpen ? '布局编辑中' : statusLabel }}</text>
      </view>
      <button class="tools-button" aria-label="打开布局工具" @tap="toggleTools">
        <text class="tools-button-icon">☷</text><text class="tools-button-label">布局</text>
      </button>
    </view>

    <!-- 内联的游戏手柄舞台 (从 PanelGamepad.vue 合并,避免跨页组件引用失败) -->
    <view class="panel-gamepad" :class="{ 'is-disabled': !connected }">
      <view class="pg-topbar">
        <view class="pg-status" :class="statusClass">
          <view class="pg-status-dot"></view>
          <text class="pg-status-text">{{ statusLabel }}</text>
        </view>
        <view v-if="activeLayout" class="pg-layout-name">
          <text>{{ activeLayout.name || '默认布局' }}</text>
        </view>
        <view v-else class="pg-layout-name pg-empty">
          <text>未获取电脑布局</text>
        </view>
      </view>

      <view v-if="activeLayout" class="pg-stage-shell">
      <view class="pg-stage pg-stage-themed" :class="backgroundStageClass" :style="stageDisplayStyle">
        <view class="pg-grid"></view>

        <view
          v-for="control in activeLayout.controls"
          :key="control.id"
          class="pg-control"
          :class="[
            'pg-control-' + control.type,
            { 'pg-control-wide': control.variant === 'wide' }
          ]"
          :style="controlStyle(control)"
          :data-control-id="control.id"
        >
          <view v-if="control.type === 'leftStick'" class="pg-stick-zone">
            <view
              :id="moveStickDomId(control)"
              class="pg-move-stick"
              :class="{ 'is-active': isMoveStickActive(control) }"
              @touchstart.stop.prevent="onMoveStickStart(control, $event)"
              @touchmove.stop.prevent="onMoveStickMove(control, $event)"
              @touchend.stop.prevent="onMoveStickEnd(control, $event)"
              @touchcancel.stop.prevent="onMoveStickEnd(control, $event)"
            >
              <view class="pg-move-ring"></view>
              <view class="pg-move-tick pg-move-tick-up"></view>
              <view class="pg-move-tick pg-move-tick-right"></view>
              <view class="pg-move-tick pg-move-tick-down"></view>
              <view class="pg-move-tick pg-move-tick-left"></view>
              <view class="pg-move-deadzone"></view>
              <view class="pg-move-thumb" :style="moveStickThumbStyle(control)">
                <view class="pg-move-thumb-center"></view>
              </view>
            </view>
            <text v-if="control.label" class="pg-control-caption">{{ control.label }}</text>
          </view>

          <view v-else-if="control.type === 'rightStick'" class="pg-stick-zone">
            <view class="pg-stick-ring pg-view-ring"
                  @touchstart.stop="onViewStart(control, $event)"
                  @touchmove.stop="onViewMove(control, $event)"
                  @touchend.stop="onViewEnd(control, $event)"
                  @touchcancel.stop="onViewEnd(control, $event)">
              <view class="pg-view-reticle"></view>
            </view>
            <text v-if="control.label" class="pg-control-caption">{{ control.label }}</text>
          </view>

          <view v-else-if="control.type === 'dpad'" class="pg-dpad-zone">
            <view class="pg-dpad-key pg-dpad-up"    @touchstart.stop="onKeyStart(control, 'up')"    @touchend.stop="onKeyEnd(control, 'up')"    @touchcancel.stop="onKeyEnd(control, 'up')">
              <text class="pg-dpad-letter">↑</text>
            </view>
            <view class="pg-dpad-key pg-dpad-left"  @touchstart.stop="onKeyStart(control, 'left')"  @touchend.stop="onKeyEnd(control, 'left')"  @touchcancel.stop="onKeyEnd(control, 'left')">
              <text class="pg-dpad-letter">←</text>
            </view>
            <view class="pg-dpad-key pg-dpad-right" @touchstart.stop="onKeyStart(control, 'right')" @touchend.stop="onKeyEnd(control, 'right')" @touchcancel.stop="onKeyEnd(control, 'right')">
              <text class="pg-dpad-letter">→</text>
            </view>
            <view class="pg-dpad-key pg-dpad-down"  @touchstart.stop="onKeyStart(control, 'down')"  @touchend.stop="onKeyEnd(control, 'down')"  @touchcancel.stop="onKeyEnd(control, 'down')">
              <text class="pg-dpad-letter">↓</text>
            </view>
            <view class="pg-dpad-center"></view>
          </view>

          <view v-else-if="control.type === 'abxy'" class="pg-abxy-zone">
            <view class="pg-abxy-key pg-abxy-y" @touchstart.stop="onKeyStart(control, 'y')" @touchend.stop="onKeyEnd(control, 'y')" @touchcancel.stop="onKeyEnd(control, 'y')">
              <text class="pg-abxy-letter">Y</text>
            </view>
            <view class="pg-abxy-key pg-abxy-x" @touchstart.stop="onKeyStart(control, 'x')" @touchend.stop="onKeyEnd(control, 'x')" @touchcancel.stop="onKeyEnd(control, 'x')">
              <text class="pg-abxy-letter">X</text>
            </view>
            <view class="pg-abxy-key pg-abxy-a" @touchstart.stop="onKeyStart(control, 'a')" @touchend.stop="onKeyEnd(control, 'a')" @touchcancel.stop="onKeyEnd(control, 'a')">
              <text class="pg-abxy-letter">A</text>
            </view>
            <view class="pg-abxy-key pg-abxy-b" @touchstart.stop="onKeyStart(control, 'b')" @touchend.stop="onKeyEnd(control, 'b')" @touchcancel.stop="onKeyEnd(control, 'b')">
              <text class="pg-abxy-letter">B</text>
            </view>
          </view>

          <view v-else-if="control.type === 'mouse'" class="pg-mouse-zone">
            <view class="pg-mouse-track"
                  @touchstart.stop="onMouseStart(control, $event)"
                  @touchmove.stop="onMouseMove(control, $event)"
                  @touchend.stop="onMouseEnd(control, $event)"
                  @touchcancel.stop="onMouseEnd(control, $event)">
              <view class="pg-mouse-crosshair"></view>
            </view>
            <text v-if="control.label" class="pg-control-caption">{{ control.label }}</text>
          </view>

          <view v-else class="pg-button-control" :class="{ 'pg-shoulder': control.type === 'shoulder' }">
            <view
              class="pg-single-button"
              :class="buttonClasses(control)"
              @touchstart.stop="onKeyStart(control, 'press')"
              @touchend.stop="onKeyEnd(control, 'press')"
              @touchcancel.stop="onKeyEnd(control, 'press')"
            >
              <text v-if="showControlLabel(control)" class="pg-single-letter pg-button-label">{{ control.label || 'KEY' }}</text>
              <text v-if="showControlKey(control)" class="pg-button-key">{{ controlBindingLabel(control) }}</text>
            </view>
          </view>

          <view
            v-if="toolsOpen"
            :class="['pg-edit-hitbox', { 'is-selected': selectedControlId === control.id }]"
            aria-label="拖动按钮"
            @touchstart.stop.prevent="onEditDragStart(control, $event)"
            @touchmove.stop.prevent="onEditDragMove(control, $event)"
            @touchend.stop.prevent="onEditDragEnd"
            @touchcancel.stop.prevent="onEditDragEnd"
          >
            <text v-if="selectedControlId === control.id" class="pg-edit-grip" aria-hidden="true">⠿</text>
          </view>
        </view>
      </view>
      </view>

      <view v-else class="pg-empty-state">
        <text class="pg-empty-text">{{ emptyText }}</text>
      </view>
    </view>

    <view v-if="toolsOpen" class="layout-tools" :style="toolsPanelStyle" @touchstart.stop>
      <view
        class="tools-heading"
        aria-label="拖动布局工具面板"
        @touchstart.stop.prevent="onToolsDragStart"
        @touchmove.stop.prevent="onToolsDragMove"
        @touchend.stop.prevent="onToolsDragEnd"
        @touchcancel.stop.prevent="onToolsDragEnd"
      >
        <view class="tools-heading-copy">
          <text class="tools-title">布局工具</text>
          <text class="tools-subtitle">画布保持全屏，可直接拖动按钮</text>
        </view>
        <view class="tools-heading-actions">
          <text class="tools-drag-grip" aria-hidden="true">⋮⋮</text>
          <button class="tools-close" aria-label="关闭布局工具" @touchstart.stop @tap.stop="toggleTools">×</button>
        </view>
      </view>

      <scroll-view class="tools-content" scroll-y>
        <text class="tools-section-label">当前布局</text>
        <scroll-view class="layout-strip" scroll-x>
          <button v-for="layout in availableLayouts" :key="layout.id" :class="['layout-chip', { active: activeLayout && activeLayout.id === layout.id }]" @tap="switchLayout(layout.id)">{{ layout.name }}</button>
          <button class="layout-chip layout-new" @tap="createCustomLayout">＋ 新建</button>
        </scroll-view>

        <view class="tool-tabs">
          <button :class="['tool-tab', { active: toolTab === 'add' }]" @tap="toolTab = 'add'">添加按钮</button>
          <button :class="['tool-tab', { active: toolTab === 'selected' }]" @tap="toolTab = 'selected'">选中按钮</button>
        </view>

        <view v-if="toolTab === 'add'" class="preset-grid">
          <button v-for="preset in presets" :key="preset.id" class="preset-item" @tap="addPreset(preset)">
            <view :class="['preset-sample', 'pg-skin-' + ((preset.control.appearance && preset.control.appearance.skin) || 'fluent')]">
              <text>{{ preset.keyLabel || preset.control.label }}</text>
            </view>
            <text class="preset-name">{{ preset.name }}</text>
            <text v-if="!preset.builtIn" class="preset-custom">自定义</text>
          </button>
        </view>

        <view v-else-if="selectedControl" class="selected-tools">
          <view class="selected-summary"><text class="selected-name">{{ selectedControl.label }}</text><text class="selected-key">{{ controlBindingLabel(selectedControl) }}</text></view>
          <view class="size-control">
            <button class="size-step" aria-label="缩小按钮" @tap="resizeSelected(-10)">−</button>
            <slider class="size-slider" :value="selectedControl.size" min="50" max="220" step="5" activeColor="#69A8FF" backgroundColor="rgba(255,255,255,.22)" @changing="resizeSelectedTo" @change="resizeSelectedTo" />
            <button class="size-step" aria-label="放大按钮" @tap="resizeSelected(10)">＋</button>
            <text class="size-value">{{ Math.round(Number(selectedControl.size || 100)) }}%</text>
          </view>
          <view class="selected-actions">
            <button class="selected-action primary" @tap="editSelected">设置</button>
            <button class="selected-action" @tap="copySelected">复制</button>
            <button class="selected-action danger" @tap="deleteSelected">删除</button>
          </view>
        </view>
        <view v-else class="selected-empty"><text>点击画布上的按钮进行选择</text></view>
      </scroll-view>
    </view>

  </view>
</template>

<script>
import WS from '@/utils/wsclient.js'
import Net from '@/utils/net.js'
import { lockLandscape, lockPortrait } from '@/utils/orientation.js'
import { clone, loadLayouts, saveLayouts, loadPresets, controlFromPreset, createLayout } from '@/utils/gamepadEditorStore.js'

// 各控件绑定顺序
const BINDING_ORDER = {
  leftStick: ['up', 'left', 'down', 'right'],
  dpad: ['up', 'left', 'down', 'right'],
  abxy: ['a', 'b', 'x', 'y'],
  shoulder: ['press'],
  key: ['press'],
  macro: ['press'],
}

// 按键方向到 wasd 的常见映射 (binding 缺省时使用)
const DIRECTION_TO_KEY = {
  up: 'w',
  down: 's',
  left: 'a',
  right: 'd',
}

function formatTime(date) {
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return hours + ':' + minutes + ':' + seconds
}

export default {
  data() {
    return {
      layoutsData: null,
      connected: false,
      connectionMode: 'usb',
      syncState: 'idle',
      lastSyncedAt: '',
      pressedKeys: {},
      moveStick: {
        active: false,
        controlId: '',
        touchId: null,
        gestureId: 0,
        ready: false,
        centerX: 0,
        centerY: 0,
        pointX: 0,
        pointY: 0,
        radius: 1,
        thumbX: 0,
        thumbY: 0,
        directions: [],
      },
      _stickActive: null,
      mouseActive: null,
      mouseLastPoint: null,
      stageStyle: {},
      leaving: false,
      toolsOpen: false,
      toolTab: 'add',
      presets: [],
      selectedControlId: '',
      editDrag: null,
      toolsPanelPosition: null,
      toolsPanelDrag: null,
      toggledTokens: {},
    }
  },
  computed: {
    activeLayout() {
      const data = this.layoutsData
      if (!data || !Array.isArray(data.layouts)) return null
      return data.layouts.find(function(layout) { return layout.id === data.activeLayoutId }) || data.layouts[0] || null
    },
    controlCount() {
      return this.activeLayout && Array.isArray(this.activeLayout.controls) ? this.activeLayout.controls.length : 0
    },
    availableLayouts() {
      return this.layoutsData && Array.isArray(this.layoutsData.layouts) ? this.layoutsData.layouts : []
    },
    selectedControl() {
      if (!this.activeLayout || !this.selectedControlId) return null
      return (this.activeLayout.controls || []).find(item => item.id === this.selectedControlId) || null
    },
    toolsPanelStyle() {
      const position = this.toolsPanelPosition
      if (!position) return {}
      return {
        left: position.x + 'px',
        top: position.y + 'px',
        right: 'auto',
      }
    },
    backgroundStageClass() {
      const background = (this.activeLayout && this.activeLayout.background) || {}
      const id = background.baseId || background.id
      return 'pg-stage-bg-' + (id || 'mobile-light')
    },
    stageDisplayStyle() {
      const style = Object.assign({}, this.stageStyle)
      const background = (this.activeLayout && this.activeLayout.background) || {}
      const theme = background.theme || {}
      const fields = {
        stage_top: '--pg-stage-top', stage_bottom: '--pg-stage-bottom', grid: '--pg-grid',
        button_top: '--pg-button-top', button_bottom: '--pg-button-bottom',
        button_text: '--pg-button-text', button_border: '--pg-button-border',
        control_fill: '--pg-control-fill', control_inner: '--pg-control-inner',
        control_border: '--pg-control-border', accent: '--pg-accent',
      }
      Object.keys(fields).forEach(function(key) { if (theme[key]) style[fields[key]] = theme[key] })
      return style
    },
    statusClass() {
      return {
        'is-synced': this.syncState === 'synced',
        'is-syncing': this.syncState === 'syncing',
        'is-cached': this.syncState === 'cached',
        'is-offline': ['offline', 'wrong-mode', 'error'].includes(this.syncState),
      }
    },
    syncLabel() {
      if (this.connectionMode === 'ble') {
        if (!this.activeLayout) return '请先用 WiFi 同步一次布局'
        return this.connected ? '蓝牙 HID · 本地缓存布局' : '等待蓝牙 HID 连接'
      }
      if (this.syncState === 'syncing') return '正在读取电脑布局'
      if (this.syncState === 'synced') return '电脑布局已同步'
      if (this.syncState === 'cached') return '显示上次同步布局'
      if (this.syncState === 'wrong-mode') return '等待 WiFi 连接'
      if (this.syncState === 'error') return '同步超时'
      return '电脑未连接'
    },
    sourceLabel() {
      if (this.connectionMode === 'ble') return '手机本地缓存布局'
      if (this.syncState === 'synced') return '电脑端实时布局'
      if (this.syncState === 'cached') return '手机本地缓存'
      return '电脑端布局副本'
    },
    connectionModeLabel() {
      if (this.connectionMode === 'wifi') return 'WIFI'
      if (this.connectionMode === 'ble') return 'BT'
      return 'USB'
    },
    statusLabel() {
      if (!this.connected) return '未连接'
      if (!this.activeLayout) return '电脑未推送布局'
      if (this.connectionMode === 'ble') return 'HID 已连接'
      return '已同步'
    },
    emptyText() {
      if (this.connectionMode === 'ble' && !this.activeLayout) return '请先用 WiFi 同步一次手柄布局'
      if (!this.connected) return '连接电脑后,这里显示游戏手柄控件'
      return '等待电脑端推送布局'
    },
  },
  onLoad() {
    this.readConnectionMode()
    this.connected = this.isInputConnected()
    const local = loadLayouts()
    const cached = WS.getCachedGamepadLayouts()
    if (local && Array.isArray(local.layouts) && local.layouts.length) {
      this.layoutsData = local
      this.syncState = 'cached'
    } else if (cached && Array.isArray(cached.layouts) && cached.layouts.length) {
      this.layoutsData = saveLayouts(cached, { pending: false })
      this.syncState = 'cached'
    } else {
      this.syncState = this.connectionMode === 'wifi' || this.connectionMode === 'ble' ? 'offline' : 'wrong-mode'
    }
    this.subscribeToSync()
    // === 强制横屏 ===
    this._lockLandscape()
    this._setFullscreen(true)
    this._updateStageMetrics()
    setTimeout(() => this._updateStageMetrics(), 260)
    // === 隐藏 tabBar(横屏全屏) — 多次调用,兼容不同基座 ===
    this._hideTabBar()
  },
  onShow() {
    this.leaving = false
    try { uni.setKeepScreenOn({ keepScreenOn: true }) } catch (e) {}
    const local = loadLayouts()
    if (local.layouts.length) this.layoutsData = local
    this.presets = loadPresets()
    this.readConnectionMode()
    this.connected = this.isInputConnected()
    this.refreshLayouts(false)
    this._lockLandscape()
    this._setFullscreen(true)
    this._updateStageMetrics()
    setTimeout(() => this._updateStageMetrics(), 260)
    this._hideTabBar()
  },
  onResize(event) {
    this._updateStageMetrics(event && event.size)
    if (this.toolsOpen && this.toolsPanelPosition) this.$nextTick(() => this.clampToolsPanel())
  },
  onHide() {
    // 自定义 TabBar 使用同一套页面导航。横屏页不主动显示原生 tabBar，
    // 否则返回 panel 时会与自定义 TabBar 叠成两行。
    this._restorePortrait()
    this._setFullscreen(false)
    this._releaseAll()
  },
  onUnload() {
    if (this._layoutListener) WS.offGamepadLayouts(this._layoutListener)
    if (this._stateListener && typeof WS.offStateChange === 'function') WS.offStateChange(this._stateListener)
    if (this._hidStateListener) Net.offHidStateChange(this._hidStateListener)
    if (this._syncTimer) clearTimeout(this._syncTimer)
    try { uni.setKeepScreenOn({ keepScreenOn: false }) } catch (e) {}
    this._restorePortrait()
    this._setFullscreen(false)
    this._releaseAll()
  },
  methods: {
    _lockLandscape() {
      lockLandscape()
    },
    _restorePortrait() {
      lockPortrait()
    },
    _setFullscreen(enabled) {
      // #ifdef APP-PLUS
      try {
        if (typeof plus !== 'undefined' && plus.navigator && plus.navigator.setFullscreen) {
          plus.navigator.setFullscreen(!!enabled)
        }
      } catch (e) {}
      // #endif
    },
    _updateStageMetrics(size) {
      try {
        const info = size || uni.getSystemInfoSync()
        const width = Math.max(Number(info.windowWidth || 0), Number(info.windowHeight || 0))
        const height = Math.min(Number(info.windowWidth || 0), Number(info.windowHeight || 0))
        if (!width || !height) return
        const canvas = (this.activeLayout && this.activeLayout.canvas) || {}
        const targetRatio = Math.max(0.5, Math.min(4, Number(canvas.width || 2400) / Math.max(1, Number(canvas.height || 1080))))
        const availableHeight = Math.max(160, height)
        let stageWidth = width
        let stageHeight = width / targetRatio
        if (stageHeight > availableHeight) {
          stageHeight = availableHeight
          stageWidth = availableHeight * targetRatio
        }
        this.stageStyle = {
          width: stageWidth + 'px',
          height: stageHeight + 'px',
          '--stage-unit': (stageHeight / 100) + 'px',
        }
      } catch (e) {}
    },
    _hideTabBar() {
      // 多次调用,部分基座首次调用可能失败
      try { uni.hideTabBar({ animation: false }) } catch (e) {}
      setTimeout(function () { try { uni.hideTabBar({ animation: false }) } catch (e) {} }, 50)
      setTimeout(function () { try { uni.hideTabBar({ animation: false }) } catch (e) {} }, 300)
    },
    readConnectionMode() {
      try { this.connectionMode = uni.getStorageSync('phonekb.mode') || 'usb' } catch (e) { this.connectionMode = 'usb' }
    },
    isInputConnected() {
      if (this.connectionMode === 'ble') {
        const status = Net.getHidStatus()
        return !!(status && status.connected)
      }
      return this.connectionMode === 'wifi' && WS.isConnected()
    },
    subscribeToSync() {
      const self = this
      this._layoutListener = function(data) {
        if (!data || !Array.isArray(data.layouts)) return
        if (self._syncTimer) { clearTimeout(self._syncTimer); self._syncTimer = null }
        self.layoutsData = saveLayouts(data, { pending: false })
        self.connected = WS.isConnected()
        self.syncState = 'synced'
        self.lastSyncedAt = formatTime(new Date())
        self.$nextTick(function() { self._updateStageMetrics() })
      }
      this._stateListener = function(state) {
        if (self.connectionMode !== 'wifi') return
        self.connected = state === 'connected'
        if (state === 'connected') {
          self.refreshLayouts(false)
        } else if (self.activeLayout) {
          self.syncState = 'cached'
        } else {
          self.syncState = 'offline'
        }
      }
      this._hidStateListener = function(status) {
        if (self.connectionMode !== 'ble') return
        self.connected = !!(status && status.connected)
        self.syncState = self.activeLayout ? 'cached' : 'offline'
        if (!self.connected) self._releaseAll()
      }
      WS.onGamepadLayouts(this._layoutListener)
      WS.onStateChange(this._stateListener)
      if (this.connectionMode === 'ble') Net.onHidStateChange(this._hidStateListener)
    },
    refreshLayouts(showFeedback) {
      this.readConnectionMode()
      if (this.connectionMode === 'ble') {
        this.connected = this.isInputConnected()
        this.syncState = this.activeLayout ? 'cached' : 'offline'
        if (showFeedback) {
          const title = !this.activeLayout
            ? '请先用 WiFi 同步一次布局'
            : (this.connected ? '蓝牙 HID 已连接' : '等待蓝牙 HID 连接')
          uni.showToast({ title: title, icon: 'none' })
        }
        return
      }
      if (this.connectionMode !== 'wifi') {
        this.connected = false
        this.syncState = this.activeLayout ? 'cached' : 'wrong-mode'
        if (showFeedback) uni.showToast({ title: '第一阶段请使用 WiFi 连接', icon: 'none' })
        return
      }
      this.connected = WS.isConnected()
      if (!this.connected) {
        this.syncState = this.activeLayout ? 'cached' : 'offline'
        if (showFeedback) uni.showToast({ title: '电脑尚未连接', icon: 'none' })
        return
      }
      if (this._syncTimer) clearTimeout(this._syncTimer)
      this.syncState = 'syncing'
      const sent = WS.getGamepadLayouts()
      if (!sent) {
        this.syncState = this.activeLayout ? 'cached' : 'error'
        return
      }
      const self = this
      this._syncTimer = setTimeout(function() {
        self._syncTimer = null
        if (self.syncState === 'syncing') self.syncState = self.activeLayout ? 'cached' : 'error'
      }, 5000)
    },
    onBack() {
      if (this.leaving) return
      this.leaving = true
      this._releaseAll()
      this._restorePortrait()
      this._setFullscreen(false)
      setTimeout(function() {
        uni.navigateBack({ delta: 1, fail: function() { uni.reLaunch({ url: '/pages/panel/panel' }) } })
      }, 280)
    },
    toggleTools() {
      this.toolsOpen = !this.toolsOpen
      this.editDrag = null
      this.toolsPanelDrag = null
      if (this.toolsOpen) {
        this._releaseAll()
        this.presets = loadPresets()
        this.toolTab = 'add'
      } else {
        this.selectedControlId = ''
      }
    },
    onToolsDragStart(event) {
      const touch = this._eventTouch(event, null)
      const point = this._touchPoint(touch)
      if (!point) return
      const query = uni.createSelectorQuery().in(this)
      query.select('.layout-tools').boundingClientRect()
      query.exec(result => {
        const rect = result && result[0]
        if (!rect || !rect.width || !rect.height) return
        const viewport = this.getToolsViewport()
        this.toolsPanelPosition = { x: rect.left, y: rect.top }
        this.toolsPanelDrag = {
          touchId: touch && touch.identifier != null ? touch.identifier : null,
          offsetX: point.x - rect.left,
          offsetY: point.y - rect.top,
          width: rect.width,
          height: rect.height,
          viewportWidth: viewport.width,
          viewportHeight: viewport.height,
        }
      })
    },
    onToolsDragMove(event) {
      const drag = this.toolsPanelDrag
      if (!drag) return
      const point = this._touchPoint(this._eventTouch(event, drag.touchId))
      if (!point) return
      this.toolsPanelPosition = this.constrainToolsPosition(
        point.x - drag.offsetX,
        point.y - drag.offsetY,
        drag.width,
        drag.height,
        drag.viewportWidth,
        drag.viewportHeight
      )
    },
    onToolsDragEnd() {
      this.toolsPanelDrag = null
    },
    getToolsViewport() {
      try {
        const info = uni.getSystemInfoSync()
        return {
          width: Number(info.windowWidth || 0),
          height: Number(info.windowHeight || 0),
        }
      } catch (e) {
        return { width: 0, height: 0 }
      }
    },
    constrainToolsPosition(x, y, width, height, viewportWidth, viewportHeight) {
      const edge = 6
      const maxX = Math.max(edge, Number(viewportWidth || 0) - Number(width || 0) - edge)
      const maxY = Math.max(edge, Number(viewportHeight || 0) - Number(height || 0) - edge)
      return {
        x: Math.round(Math.max(edge, Math.min(maxX, Number(x || 0)))),
        y: Math.round(Math.max(edge, Math.min(maxY, Number(y || 0)))),
      }
    },
    clampToolsPanel() {
      if (!this.toolsPanelPosition) return
      const query = uni.createSelectorQuery().in(this)
      query.select('.layout-tools').boundingClientRect()
      query.exec(result => {
        const rect = result && result[0]
        if (!rect) return
        const viewport = this.getToolsViewport()
        this.toolsPanelPosition = this.constrainToolsPosition(
          this.toolsPanelPosition.x,
          this.toolsPanelPosition.y,
          rect.width,
          rect.height,
          viewport.width,
          viewport.height
        )
      })
    },
    persistLayouts() {
      this.layoutsData = saveLayouts(this.layoutsData)
      if (WS.isConnected()) WS.saveGamepadLayouts(this.layoutsData)
    },
    switchLayout(layoutId) {
      if (!this.layoutsData || !this.availableLayouts.some(item => item.id === layoutId)) return
      this.layoutsData.activeLayoutId = layoutId
      this.selectedControlId = ''
      this.persistLayouts()
      this.$nextTick(() => this._updateStageMetrics())
    },
    createCustomLayout() {
      const self = this
      uni.showModal({
        title: '新建自定义布局',
        editable: true,
        placeholderText: '输入布局名称',
        content: '我的布局',
        success(res) {
          if (!res.confirm) return
          const name = String(res.content || '').trim() || '我的布局'
          self.layoutsData = createLayout(self.layoutsData, name, self.activeLayout)
          self.selectedControlId = ''
          self.persistLayouts()
          self.$nextTick(() => self._updateStageMetrics())
        },
      })
    },
    addPreset(preset) {
      if (!this.activeLayout) return
      const count = (this.activeLayout.controls || []).length
      const offset = (count % 5) * 3
      const control = controlFromPreset(preset, { x: 50 + offset, y: 50 + offset * 0.45 })
      this.activeLayout.controls.push(control)
      this.selectedControlId = control.id
      this.toolTab = 'selected'
      this.persistLayouts()
      uni.showToast({ title: '按钮已添加', icon: 'success' })
    },
    selectControl(control) {
      this.selectedControlId = control.id
      this.toolTab = 'selected'
    },
    onEditDragStart(control, event) {
      this.selectControl(control)
      const point = this._touchPoint(this._eventTouch(event, null))
      if (!point) return
      const touch = this._eventTouch(event, null)
      const query = uni.createSelectorQuery().in(this)
      query.select('.pg-stage').boundingClientRect()
      query.exec(result => {
        const rect = result && result[0]
        if (!rect || !rect.width || !rect.height) return
        this.editDrag = {
          controlId: control.id,
          touchId: touch && touch.identifier != null ? touch.identifier : null,
          rect: rect,
        }
        this.updateDraggedControl(point)
      })
    },
    onEditDragMove(control, event) {
      if (!this.editDrag || this.editDrag.controlId !== control.id) return
      const point = this._touchPoint(this._eventTouch(event, this.editDrag.touchId))
      if (point) this.updateDraggedControl(point)
    },
    updateDraggedControl(point) {
      if (!this.editDrag || !this.activeLayout) return
      const control = this.activeLayout.controls.find(item => item.id === this.editDrag.controlId)
      const rect = this.editDrag.rect
      if (!control || !rect) return
      control.x = Math.round(Math.max(2, Math.min(98, (point.x - rect.left) / rect.width * 100)) * 10) / 10
      control.y = Math.round(Math.max(3, Math.min(97, (point.y - rect.top) / rect.height * 100)) * 10) / 10
    },
    onEditDragEnd() {
      if (!this.editDrag) return
      this.editDrag = null
      this.persistLayouts()
    },
    resizeSelected(delta) {
      if (!this.selectedControl) return
      this.selectedControl.size = Math.max(50, Math.min(220, Number(this.selectedControl.size || 100) + delta))
      this.persistLayouts()
    },
    resizeSelectedTo(event) {
      if (!this.selectedControl) return
      this.selectedControl.size = Math.max(50, Math.min(220, Number(event && event.detail && event.detail.value || 100)))
      if (event && event.type === 'change') this.persistLayouts()
    },
    editSelected() {
      if (!this.selectedControl || !this.activeLayout) return
      this._releaseAll()
      uni.navigateTo({ url: '/pages/gamepad-edit/gamepad-edit?layoutId=' + encodeURIComponent(this.activeLayout.id) + '&controlId=' + encodeURIComponent(this.selectedControl.id) })
    },
    copySelected() {
      if (!this.selectedControl || !this.activeLayout) return
      const copy = clone(this.selectedControl)
      copy.id = 'control-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6)
      copy.label = String(copy.label || '按钮') + ' 副本'
      copy.x = Math.min(98, Number(copy.x || 50) + 4)
      copy.y = Math.min(97, Number(copy.y || 50) + 4)
      this.activeLayout.controls.push(copy)
      this.selectedControlId = copy.id
      this.persistLayouts()
    },
    deleteSelected() {
      if (!this.selectedControl || !this.activeLayout) return
      const self = this
      uni.showModal({ title: '删除按钮', content: '确定从当前布局删除“' + self.selectedControl.label + '”吗？', success(res) {
        if (!res.confirm) return
        self.activeLayout.controls = self.activeLayout.controls.filter(item => item.id !== self.selectedControlId)
        self.selectedControlId = ''
        self.persistLayouts()
      } })
    },
    buttonClasses(control) {
      const appearance = control.appearance || {}
      return {
        'pg-single-wide': control.variant === 'wide' || control.type === 'shoulder',
        'pg-single-round': control.type === 'key',
        'pg-shape-square': appearance.shape === 'square',
        'pg-shape-pill': appearance.shape === 'pill',
        'pg-shape-diamond': appearance.shape === 'diamond',
        ['pg-skin-' + (appearance.skin || 'fluent')]: true,
      }
    },
    showControlLabel(control) {
      return ((control.appearance || {}).labelMode || 'label') !== 'key'
    },
    showControlKey(control) {
      return ['key', 'both'].includes((control.appearance || {}).labelMode)
    },
    controlBindingLabel(control) {
      const binding = this.resolveBinding(control, 'press')
      if (!binding) return control.label || 'KEY'
      const keys = this.bindingKeys(binding)
      return keys.map(key => key.length === 1 ? key.toUpperCase() : key.charAt(0).toUpperCase() + key.slice(1)).join(' + ')
    },
    controlStyle(control) {
      const x = control.x == null ? 50 : Number(control.x)
      const y = control.y == null ? 50 : Number(control.y)
      const size = Number(control.size || 100) / 100
      const opacity = Number(control.opacity == null ? 100 : control.opacity) / 100
      const appearance = control.appearance || {}
      const style = {
        left: String(x) + '%',
        top: String(y) + '%',
        opacity: opacity,
        transform: 'translate(-50%, -50%) scale(' + size + ')',
        display: control.visible === false ? 'none' : 'flex',
      }
      if (appearance.fill) style['--pg-custom-fill'] = appearance.fill
      if (appearance.border) style['--pg-custom-border'] = appearance.border
      if (appearance.text) style['--pg-custom-text'] = appearance.text
      return style
    },
    resolveBinding(control, slot) {
      return (control.bindings || {})[slot] || null
    },
    bindingKeys(binding, fallback) {
      if (!binding && fallback) return [String(fallback).toLowerCase()]
      if (!binding) return []
      if (typeof binding === 'string') return this._expandKeyValue(binding.toLowerCase())
      const keys = []
      ;(binding.modifiers || []).forEach(value => {
        const key = String(value || '').trim().toLowerCase()
        if (key && keys.indexOf(key) < 0) keys.push(key)
      })
      const main = String(binding.key || '').trim().toLowerCase()
      if (main && keys.indexOf(main) < 0) keys.push(main)
      return keys
    },
    _expandKeyValue(value) {
      return String(value || '').split(/\s*\+\s*/).map(item => item.trim()).filter(Boolean)
    },
    moveStickDomId(control) {
      return 'pg-move-stick-' + String(control && control.id || 'default').replace(/[^a-zA-Z0-9_-]/g, '-')
    },
    isMoveStickActive(control) {
      return !!(this.moveStick.active && this.moveStick.controlId === control.id)
    },
    moveStickThumbStyle(control) {
      if (!this.isMoveStickActive(control)) return { transform: 'translate3d(0px, 0px, 0px)' }
      return {
        transform: 'translate3d(' + this.moveStick.thumbX + 'px, ' + this.moveStick.thumbY + 'px, 0px)',
      }
    },
    _eventTouch(e, touchId) {
      const touches = []
      const activeTouches = (e && e.touches) || []
      const changedTouches = (e && e.changedTouches) || []
      for (let i = 0; i < activeTouches.length; i += 1) touches.push(activeTouches[i])
      for (let i = 0; i < changedTouches.length; i += 1) touches.push(changedTouches[i])
      if (touchId != null) {
        const matched = touches.find(touch => touch.identifier === touchId)
        if (matched) return matched
      }
      return touches[0] || null
    },
    _touchPoint(touch) {
      if (!touch) return null
      return {
        x: Number(touch.clientX != null ? touch.clientX : (touch.pageX != null ? touch.pageX : touch.x)) || 0,
        y: Number(touch.clientY != null ? touch.clientY : (touch.pageY != null ? touch.pageY : touch.y)) || 0,
      }
    },
    onMoveStickStart(control, e) {
      if (!this.connected) return
      const touch = this._eventTouch(e, null)
      const point = this._touchPoint(touch)
      if (!point) return

      if (this.moveStick.active) this._endMoveStick()
      this.moveStick.active = true
      this.moveStick.controlId = control.id
      this.moveStick.touchId = touch && touch.identifier != null ? touch.identifier : null
      this.moveStick.gestureId += 1
      const gestureId = this.moveStick.gestureId
      this.moveStick.ready = false
      this.moveStick.centerX = point.x
      this.moveStick.centerY = point.y
      this.moveStick.pointX = point.x
      this.moveStick.pointY = point.y
      this.moveStick.radius = 1
      this.moveStick.thumbX = 0
      this.moveStick.thumbY = 0
      this.moveStick.directions = []

      const selector = '#' + this.moveStickDomId(control)
      const query = uni.createSelectorQuery().in(this)
      query.select(selector).boundingClientRect()
      query.exec(result => {
        if (!this.isMoveStickActive(control) || this.moveStick.gestureId !== gestureId) return
        const rect = result && result[0]
        if (rect && rect.width && rect.height) {
          this.moveStick.centerX = Number(rect.left) + Number(rect.width) / 2
          this.moveStick.centerY = Number(rect.top) + Number(rect.height) / 2
          // 可移动半径扣除摇杆帽半径，避免摇杆帽越出外环。
          this.moveStick.radius = Math.max(18, Math.min(Number(rect.width), Number(rect.height)) * 0.25)
        } else {
          // 少数 Android WebView 首帧取不到布局时，退化为以落点为中心的浮动摇杆。
          this.moveStick.radius = 42
        }
        this.moveStick.ready = true
        this._updateMoveStick(control, { x: this.moveStick.pointX, y: this.moveStick.pointY })
      })
    },
    onMoveStickMove(control, e) {
      if (!this.isMoveStickActive(control)) return
      const point = this._touchPoint(this._eventTouch(e, this.moveStick.touchId))
      if (!point) return
      this.moveStick.pointX = point.x
      this.moveStick.pointY = point.y
      if (this.moveStick.ready) this._updateMoveStick(control, point)
    },
    onMoveStickEnd(control) {
      if (!this.isMoveStickActive(control)) return
      this._endMoveStick(control)
    },
    _updateMoveStick(control, point) {
      if (!this.isMoveStickActive(control)) return
      const dx = point.x - this.moveStick.centerX
      const dy = point.y - this.moveStick.centerY
      const distance = Math.sqrt(dx * dx + dy * dy)
      const radius = Math.max(1, this.moveStick.radius)
      const scale = distance > radius ? radius / distance : 1
      this.moveStick.thumbX = Math.round(dx * scale * 10) / 10
      this.moveStick.thumbY = Math.round(dy * scale * 10) / 10

      const nextDirections = []
      if (distance >= radius * 0.2) {
        // 22.5 度分界形成八方向；斜向会同时保持两个绑定键。
        const axisThreshold = 0.3826834324
        const nx = dx / distance
        const ny = dy / distance
        if (ny < -axisThreshold) nextDirections.push('up')
        if (nx > axisThreshold) nextDirections.push('right')
        if (ny > axisThreshold) nextDirections.push('down')
        if (nx < -axisThreshold) nextDirections.push('left')
      }
      this._setMoveDirections(control, nextDirections)
    },
    _setMoveDirections(control, nextDirections) {
      const previous = this.moveStick.directions.slice()
      const removed = previous.filter(dir => nextDirections.indexOf(dir) < 0)
      const added = nextDirections.filter(dir => previous.indexOf(dir) < 0)
      if (!removed.length && !added.length) return

      removed.forEach(dir => {
        const keys = this.bindingKeys(this.resolveBinding(control, dir), DIRECTION_TO_KEY[dir])
        const token = control.id + ':move:' + dir
        keys.slice().reverse().forEach(key => this._releaseKey(key, token))
      })
      added.forEach(dir => {
        const keys = this.bindingKeys(this.resolveBinding(control, dir), DIRECTION_TO_KEY[dir])
        const token = control.id + ':move:' + dir
        keys.forEach(key => this._pressKey(key, token))
      })
      this.moveStick.directions = nextDirections.slice()
    },
    _endMoveStick(control) {
      const activeControl = control || (this.activeLayout && this.activeLayout.controls || []).find(item => item.id === this.moveStick.controlId)
      if (activeControl) this._setMoveDirections(activeControl, [])
      this.moveStick.active = false
      this.moveStick.controlId = ''
      this.moveStick.touchId = null
      this.moveStick.ready = false
      this.moveStick.thumbX = 0
      this.moveStick.thumbY = 0
      this.moveStick.directions = []
    },
    onKeyStart(control, slot) {
      if (!this.connected || this.toolsOpen) return
      const keys = this.bindingKeys(this.resolveBinding(control, slot))
      const token = control.id + ':' + slot
      const behavior = control.behavior || 'hold'
      if (behavior === 'tap') {
        keys.forEach(key => this._pressKey(key, token))
        keys.slice().reverse().forEach(key => this._releaseKey(key, token))
        return
      }
      if (behavior === 'toggle') {
        if (this.toggledTokens[token]) {
          keys.slice().reverse().forEach(key => this._releaseKey(key, token))
          delete this.toggledTokens[token]
        } else {
          keys.forEach(key => this._pressKey(key, token))
          this.toggledTokens[token] = true
        }
        return
      }
      keys.forEach(key => this._pressKey(key, token))
    },
    onKeyEnd(control, slot) {
      if (!this.connected || this.toolsOpen || ['tap', 'toggle'].includes(control.behavior)) return
      const keys = this.bindingKeys(this.resolveBinding(control, slot))
      const token = control.id + ':' + slot
      keys.reverse().forEach(key => this._releaseKey(key, token))
    },
    onViewStart(control, e) {
      if (!this.connected) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      this._stickActive = {
        controlId: control.id,
        cx: t.clientX || t.pageX || t.x || 0,
        cy: t.clientY || t.pageY || t.y || 0,
        sens: Number(control.sensitivity || 55) / 100,
      }
    },
    onViewMove(control, e) {
      const a = this._stickActive
      if (!a || a.controlId !== control.id) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      const x = t.clientX || t.pageX || t.x || 0
      const y = t.clientY || t.pageY || t.y || 0
      let dx = (x - a.cx) * a.sens
      let dy = (y - a.cy) * a.sens
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
      dx = Math.max(-120, Math.min(120, dx))
      dy = Math.max(-120, Math.min(120, dy))
      this._sendMouseMove(Math.round(dx), Math.round(dy))
      a.cx = x
      a.cy = y
    },
    onViewEnd(control, e) {
      if (this._stickActive && this._stickActive.controlId === control.id) {
        this._stickActive = null
        this._flushMouseMove()
      }
    },
    onMouseStart(control, e) {
      if (!this.connected) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      this.mouseActive = { controlId: control.id }
      this.mouseLastPoint = { x: t.clientX || t.pageX || t.x || 0, y: t.clientY || t.pageY || t.y || 0 }
    },
    onMouseMove(control, e) {
      if (!this.mouseActive || this.mouseActive.controlId !== control.id) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      const x = t.clientX || t.pageX || t.x || 0
      const y = t.clientY || t.pageY || t.y || 0
      const sens = Number(control.sensitivity || 55) / 50
      let dx = (x - this.mouseLastPoint.x) * sens
      let dy = (y - this.mouseLastPoint.y) * sens
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
      dx = Math.max(-150, Math.min(150, dx))
      dy = Math.max(-150, Math.min(150, dy))
      this._sendMouseMove(Math.round(dx), Math.round(dy))
      this.mouseLastPoint = { x, y }
    },
    onMouseEnd(control, e) {
      if (this.mouseActive && this.mouseActive.controlId === control.id) {
        this.mouseActive = null
        this.mouseLastPoint = null
        this._flushMouseMove()
      }
    },
    _sendMouseMove(dx, dy) {
      try {
        return this.connectionMode === 'ble'
          ? Net.mouseMove(dx, dy)
          : WS.gamepadMouseMove(dx, dy)
      } catch (err) { return false }
    },
    _flushMouseMove() {
      if (this.connectionMode !== 'ble') return
      try { Net.flushMouseMove() } catch (err) {}
    },
    _sendKey(key, down) {
      try {
        return this.connectionMode === 'ble'
          ? Net.send({ action: 'keyboard_key', key: key, down: !!down })
          : WS.gamepadKey([key], !!down)
      } catch (err) { return false }
    },
    _pressKey(key, token) {
      if (!this.pressedKeys[key]) this.pressedKeys[key] = {}
      this.pressedKeys[key][token] = true
      if (Object.keys(this.pressedKeys[key]).length === 1) {
        this._sendKey(key, true)
      }
    },
    _releaseKey(key, token) {
      if (!this.pressedKeys[key]) return
      delete this.pressedKeys[key][token]
      if (Object.keys(this.pressedKeys[key]).length === 0) {
        delete this.pressedKeys[key]
        this._sendKey(key, false)
      }
    },
    _releaseAll() {
      const keys = Object.keys(this.pressedKeys)
      keys.forEach(k => {
        this._sendKey(k, false)
      })
      this.pressedKeys = {}
      this.toggledTokens = {}
      this.moveStick.active = false
      this.moveStick.controlId = ''
      this.moveStick.touchId = null
      this.moveStick.ready = false
      this.moveStick.thumbX = 0
      this.moveStick.thumbY = 0
      this.moveStick.directions = []
      this._stickActive = null
      this.mouseActive = null
      this.mouseLastPoint = null
      this._flushMouseMove()
    },
  },
}
</script>

<style scoped>
.gamepad-page {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 100dvh;
  background: linear-gradient(160deg, #0d1018 0%, #131720 100%);
  color: #f1f5f9;
  position: fixed;
  inset: 0;
  z-index: 999;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  min-height: 52px;
  padding: 10px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.layout-identity { display: flex; align-items: center; gap: 10px; min-width: 0; }
.connection-mark {
  width: 9px; height: 9px; border-radius: 50%;
  background: #475569;
  position: relative;
}
.connection-mark.is-synced .connection-core { background: #34d399; box-shadow: 0 0 7px #34d399; }
.connection-mark.is-syncing .connection-core { background: #f59e0b; }
.connection-mark.is-cached .connection-core { background: #38bdf8; }
.connection-mark.is-offline .connection-core { background: #ef4444; }
.connection-core {
  position: absolute; inset: 0; border-radius: 50%;
}
.identity-copy { display: flex; flex-direction: column; }
.identity-kicker { font-size: 10px; color: #64748b; letter-spacing: 1px; }
.identity-title { max-width: 32vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 16px; font-weight: 600; color: #f1f5f9; }

.sync-summary { display: flex; flex-direction: column; align-items: center; }
.sync-label { font-size: 13px; color: #94a3b8; }
.sync-time { font-size: 11px; color: #64748b; }

.topbar-actions { display: flex; gap: 8px; }
.icon-button {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(148,163,184,0.15);
  border-radius: 8px;
  color: #f1f5f9;
  font-size: 22px;
  width: 42px; height: 42px;
  display: flex; align-items: center; justify-content: center;
  padding: 0;
}
.icon-button:active { background: rgba(56,189,248,0.2); }
.icon-button-disabled { opacity: 0.4; }
.refresh-icon.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

.layout-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  min-height: 34px;
  padding: 6px 20px;
  font-size: 12px;
  color: #94a3b8;
  border-top: 1px solid rgba(255,255,255,0.05);
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 8;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(13,16,24,0), rgba(13,16,24,0.82));
}
.footer-source { display: flex; align-items: center; gap: 7px; }
.source-pulse { width: 7px; height: 7px; border-radius: 50%; background: #475569; }
.source-pulse.is-synced { background: #34d399; }
.source-pulse.is-syncing { background: #f59e0b; }
.source-pulse.is-cached { background: #38bdf8; }
.source-pulse.is-offline { background: #ef4444; }
.footer-stats { display: flex; align-items: center; gap: 10px; }
.footer-divider { width: 1px; height: 14px; background: rgba(255,255,255,0.1); }

/* === 以下为内联的 PanelGamepad 样式 (从 PanelGamepad.vue 合并) === */
.panel-gamepad {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #131720 0%, #1a1f2c 100%);
  border-radius: 0;
  overflow: hidden;
  color: #f1f5f9;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}
.panel-gamepad.is-disabled { opacity: 0.55; }

.pg-topbar {
  display: none;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  min-height: 30px;
  padding: 5px 14px;
  font-size: 12px;
  color: #94a3b8;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.pg-status { display: flex; align-items: center; gap: 6px; }
.pg-status-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #475569;
}
.pg-status.is-synced .pg-status-dot { background: #34d399; box-shadow: 0 0 7px #34d399; }
.pg-status.is-syncing .pg-status-dot { background: #f59e0b; }
.pg-status.is-cached .pg-status-dot { background: #38bdf8; }
.pg-status.is-warning .pg-status-dot { background: #f59e0b; }
.pg-status.is-offline .pg-status-dot { background: #ef4444; }
.pg-status-text { font-size: 12px; }
.pg-layout-name { max-width: 42vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #cbd5e1; }
.pg-layout-name.pg-empty { color: #64748b; }

.pg-stage-shell {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
}
.runtime-title {
  position: absolute;
  left: 50%;
  top: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translateX(-50%);
  color: #21476f;
}
.runtime-layout-name { max-width: 38vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 800; }
.runtime-mode { margin-top: 1px; color: #6d88a3; font-size: 9px; font-weight: 650; }
.tools-button {
  width: 68px;
  height: 32px;
  margin: 0;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  pointer-events: auto;
  border: 1px solid rgba(47,128,237,.24);
  border-radius: 8px;
  color: #245488;
  background: rgba(255,255,255,.92);
  box-shadow: 0 3px 10px rgba(47,128,237,.14);
}
.tools-button::after { border: 0; }
.tools-button-icon { font-size: 15px; line-height: 1; }
.tools-button-label { font-size: 11px; font-weight: 800; }
.pg-stage {
  position: relative;
  flex: 0 0 auto;
  max-width: 100%;
  max-height: 100%;
  /* 用 flex 撑满,不再用 padding-bottom 56.25%(那是小组件用的高度自适应) */
  background: radial-gradient(ellipse at center, #1e2536 0%, #0f1320 100%);
  overflow: hidden;
  aspect-ratio: 20 / 9;
}
.pg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 8.33% 11.11%;
}

.pg-control {
  position: absolute;
  height: 0;
  width: 0;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  z-index: 4;
}
.pg-control-leftStick,
.pg-control-rightStick,
.pg-control-abxy { width: 13%; height: 29%; }
.pg-control-dpad { width: 9%; height: 20%; }
.pg-control-mouse { width: 12.5%; height: 18%; }
.pg-control-key { width: 5%; height: 11%; }
.pg-control-shoulder,
.pg-control-wide { width: 10%; height: 9%; }
.pg-control-macro { width: 10%; height: 11%; }
.pg-key-object {
  position: absolute;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  height: calc(var(--stage-unit, 4px) * 9.8);
  aspect-ratio: 1 / 1;
  pointer-events: none;
}
.pg-key-token {
  min-width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 7px;
  border: 1px solid rgba(113,181,255,0.9);
  border-radius: 50%;
  color: #f0f9ff;
  background: rgba(18,78,171,0.88);
  box-shadow: 0 4px 10px rgba(2,17,48,0.36), inset 0 0 0 1px rgba(177,221,255,0.12);
  font-size: clamp(10px, calc(var(--stage-unit, 4px) * 3), 18px);
  font-weight: 800;
  text-shadow: 0 1px 2px #061932;
  white-space: nowrap;
}
.pg-key-token-wide {
  min-width: 160%;
  border-radius: 6px;
  font-size: clamp(9px, calc(var(--stage-unit, 4px) * 2.5), 15px);
}
.pg-control-caption {
  position: absolute;
  bottom: -17px;
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
}

.pg-stick-zone { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; }

/* === 移动摇杆:固定底盘、跟手摇杆帽和八方向状态 === */
.pg-move-stick {
  position: relative;
  width: min(94%, 100%);
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  touch-action: none;
  -webkit-user-select: none;
  user-select: none;
}
.pg-move-ring {
  position: absolute;
  inset: 4%;
  border: 2px solid var(--pg-custom-border, var(--pg-control-border, rgba(56,189,248,0.38)));
  border-radius: 50%;
  background:
    radial-gradient(circle at 50% 48%, rgba(255,255,255,0.13) 0 38%, transparent 39%),
    var(--pg-custom-fill, var(--pg-control-fill, rgba(30,41,59,0.72)));
  box-shadow:
    inset 0 0 0 7px rgba(255,255,255,0.045),
    inset 0 -7px 18px rgba(7,24,46,0.18),
    0 7px 17px rgba(15,38,67,0.2);
  transition: border-color 100ms ease, box-shadow 100ms ease;
}
.pg-move-stick.is-active .pg-move-ring {
  border-color: var(--pg-accent, #38bdf8);
  box-shadow:
    inset 0 0 0 7px rgba(255,255,255,0.07),
    inset 0 -7px 18px rgba(7,24,46,0.16),
    0 0 0 4px rgba(56,189,248,0.1),
    0 8px 19px rgba(15,38,67,0.22);
}
.pg-move-tick {
  position: absolute;
  z-index: 2;
  width: 8%;
  height: 3%;
  border-radius: 999px;
  background: var(--pg-accent, #38bdf8);
  opacity: 0.42;
  pointer-events: none;
}
.pg-move-tick-up { left: 46%; top: 11%; }
.pg-move-tick-right { right: 11%; top: 48.5%; transform: rotate(90deg); }
.pg-move-tick-down { left: 46%; bottom: 11%; }
.pg-move-tick-left { left: 11%; top: 48.5%; transform: rotate(90deg); }
.pg-move-deadzone {
  position: absolute;
  z-index: 1;
  left: 50%;
  top: 50%;
  width: 22%;
  height: 22%;
  border: 1px solid var(--pg-control-border, rgba(148,163,184,0.28));
  border-radius: 50%;
  opacity: 0.42;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.pg-move-thumb {
  position: absolute;
  z-index: 4;
  left: 29%;
  top: 29%;
  width: 42%;
  height: 42%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pg-button-border, rgba(255,255,255,0.72));
  border-radius: 50%;
  background: linear-gradient(145deg, var(--pg-button-top, #4ba4ff), var(--pg-button-bottom, #246fe5));
  box-shadow:
    inset 0 3px 5px rgba(255,255,255,0.2),
    inset 0 -5px 8px rgba(10,40,82,0.2),
    0 6px 13px rgba(15,45,86,0.32);
  pointer-events: none;
  will-change: transform;
  transition: transform 90ms ease-out, box-shadow 90ms ease-out;
}
.pg-move-stick.is-active .pg-move-thumb {
  box-shadow:
    inset 0 3px 5px rgba(255,255,255,0.24),
    inset 0 -5px 8px rgba(10,40,82,0.18),
    0 4px 10px rgba(15,45,86,0.3),
    0 0 0 4px rgba(56,189,248,0.12);
  transition: none;
}
.pg-move-thumb-center {
  width: 28%;
  height: 28%;
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 50%;
  background: rgba(255,255,255,0.14);
  box-shadow: inset 0 1px 2px rgba(255,255,255,0.18);
}

/* 右侧视角摇杆仍使用独立的触控环。 */
.pg-stick-ring {
  position: relative;
  width: min(92%, 100%);
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(56,189,248,0.06) 0%, rgba(15,19,32,0) 70%);
}

/* === 视角摇杆(右) === */
.pg-view-ring {
  width: 92%;
  background: radial-gradient(circle at 50% 50%, rgba(15,19,32,0.4) 0%, rgba(15,19,32,0) 70%);
  border: 1px solid rgba(56,189,248,0.18);
}
.pg-view-reticle {
  position: absolute; left: 50%; top: 50%;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid rgba(56,189,248,0.8);
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 3;
}

/* === 十字键 dpad:四个独立的圆角矩形键 === */
.pg-dpad-zone { position: relative; width: 100%; height: 100%; }
.pg-dpad-key {
  position: absolute;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, #2a3142, #1a1f2c);
  border: 1px solid rgba(148,163,184,0.2);
  z-index: 2;
}
.pg-dpad-letter {
  color: #cbd5e1;
  font-size: clamp(11px, 2.2vh, 18px);
  font-weight: 600;
}
.pg-dpad-up    { left: 32%; top: 0;    width: 36%; height: 32%; border-radius: 7px 7px 0 0; }
.pg-dpad-down  { left: 32%; bottom: 0; width: 36%; height: 32%; border-radius: 0 0 7px 7px; }
.pg-dpad-left  { left: 0;   top: 32%;  width: 32%; height: 36%; border-radius: 7px 0 0 7px; }
.pg-dpad-right { right: 0;  top: 32%;  width: 32%; height: 36%; border-radius: 0 7px 7px 0; }
.pg-dpad-center {
  position: absolute; left: 32%; top: 32%;
  width: 36%; height: 36%;
  background: #131720;
  z-index: 1;
}
.pg-dpad-key:active {
  background: linear-gradient(145deg, #38bdf8, #0ea5e9);
  border-color: rgba(56,189,248,0.6);
}
.pg-dpad-key:active .pg-dpad-letter { color: #fff; }

/* === ABXY:四个独立的大圆形彩色键 === */
.pg-abxy-zone { position: relative; width: 100%; height: 100%; }
.pg-abxy-key {
  position: absolute;
  display: flex; align-items: center; justify-content: center;
  width: 42%; height: 42%;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.12);
  z-index: 2;
  box-shadow: inset 0 -3px 7px rgba(0,0,0,0.3), 0 0 0 1px rgba(0,0,0,0.5);
}
.pg-abxy-letter {
  font-size: clamp(14px, 2.8vh, 22px);
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0;
}
.pg-abxy-y { left: 29%; top: 0;    background: linear-gradient(145deg, #fde047, #facc15); }
.pg-abxy-x { left: 0;   top: 29%;  background: linear-gradient(145deg, #60a5fa, #2563eb); }
.pg-abxy-a { left: 58%; top: 29%;  background: linear-gradient(145deg, #4ade80, #22c55e); }
.pg-abxy-b { left: 29%; top: 58%;  background: linear-gradient(145deg, #fb7185, #e11d48); }
.pg-abxy-key:active {
  transform: scale(0.94);
  filter: brightness(1.2);
  box-shadow: 0 0 12px currentColor;
}
.pg-abxy-y:active { color: #facc15; }
.pg-abxy-x:active { color: #60a5fa; }
.pg-abxy-a:active { color: #4ade80; }
.pg-abxy-b:active { color: #fb7185; }

.pg-mouse-zone { position: relative; width: 100%; height: 100%; }
.pg-mouse-track {
  position: relative;
  width: 100%; height: 100%;
  border-radius: 8px;
  background: linear-gradient(145deg, #1a1f2c, #131720);
  box-shadow: inset 0 0 7px rgba(0,0,0,0.5);
  overflow: hidden;
  z-index: 2;
}
.pg-mouse-crosshair {
  position: absolute; left: 50%; top: 50%;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #38bdf8;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 5px #38bdf8;
  pointer-events: none;
}

/* === 单键 / 肩键:圆角矩形 + 字母 === */
.pg-button-control { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.pg-single-button {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  overflow: hidden;
  padding: 4px 6px;
  background: linear-gradient(145deg, var(--pg-custom-fill, rgba(56,189,248,0.15)), var(--pg-custom-fill, rgba(15,19,32,0.6)));
  color: var(--pg-custom-text, #e0f2fe);
  font-weight: 600;
  border: 1px solid var(--pg-custom-border, rgba(56,189,248,0.35));
  box-shadow: inset 0 -2px 5px rgba(0,0,0,0.3);
  min-width: 34px; min-height: 28px;
}
.pg-single-letter {
  font-size: clamp(10px, 1.8vh, 15px);
  letter-spacing: 0;
}
.pg-button-label {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: keep-all;
  line-height: 1.1;
}
.pg-single-wide { border-radius: 7px; min-width: 48px; min-height: 24px; }
.pg-single-round { border-radius: 50%; min-width: 30px; min-height: 30px; }
.pg-shape-pill { border-radius: 999px; }
.pg-shape-square { border-radius: 4px; }
.pg-shape-diamond { border-radius: 5px; transform: rotate(45deg); }
.pg-shape-diamond .pg-button-label,
.pg-shape-diamond .pg-button-key { display: inline-block; transform: rotate(-45deg); }
.pg-shoulder .pg-single-button {
  min-width: 48px; min-height: 24px;
  font-size: 12px;
  border-radius: 7px;
  background: linear-gradient(180deg, rgba(56,189,248,0.25), rgba(15,19,32,0.7));
}
.pg-single-button:active {
  background: linear-gradient(145deg, #38bdf8, #0ea5e9);
  border-color: rgba(56,189,248,0.8);
  color: #fff;
}

.pg-empty-state { padding: 30px 14px; text-align: center; }
.pg-empty-text { font-size: 14px; color: #64748b; }

@media (orientation: landscape) {
  .gamepad-page { padding: 0; }
}

/* 游戏手柄主题：沿用应用的浅蓝底色，用高饱和按键作为操作焦点。 */
.gamepad-page {
  background: #eaf4ff;
  color: #183b63;
}
.topbar {
  position: absolute;
  top: 0;
  left: env(safe-area-inset-left);
  right: env(safe-area-inset-right);
  z-index: 20;
  min-height: 0;
  padding: 9px 11px;
  border: 0;
  justify-content: space-between;
  pointer-events: none;
}
.back-button {
  width: 30px;
  height: 30px;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  pointer-events: auto;
  border: 1px solid rgba(47,128,237,0.22);
  border-radius: 50%;
  color: #245488;
  background: rgba(255,255,255,0.9);
  box-shadow: 0 3px 10px rgba(47,128,237,0.16);
}
.back-button::after { border: 0; }
.back-button-icon {
  font-size: 17px;
  line-height: 1;
  font-weight: 650;
}
.panel-gamepad {
  background: #eaf4ff;
}
.panel-gamepad.is-disabled { opacity: 1; }
.pg-stage {
  background:
    radial-gradient(circle at 50% 42%, #ffffff 0%, #edf6ff 58%, #d9ebff 100%);
  border: 0;
  box-shadow: none;
}
.pg-grid {
  background-image:
    linear-gradient(rgba(47,128,237,0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(47,128,237,0.07) 1px, transparent 1px);
}
.pg-key-token {
  border-color: rgba(255,255,255,0.92);
  color: #fff;
  background: linear-gradient(145deg, #4ba4ff, #246fe5);
  box-shadow: 0 5px 12px rgba(36,111,229,0.26), inset 0 0 0 1px rgba(255,255,255,0.2);
  text-shadow: 0 1px 2px rgba(19,65,128,0.6);
}
.pg-key-token-wide {
  background: linear-gradient(145deg, #24b8d5, #1686c8);
}
.pg-stick-ring {
  background: rgba(255,255,255,0.68);
  border: 2px solid rgba(47,128,237,0.42);
  box-shadow: inset 0 0 0 12px rgba(47,128,237,0.08), 0 8px 18px rgba(47,128,237,0.15);
}
.pg-view-ring {
  background: rgba(48,198,180,0.16);
  border-color: rgba(28,166,151,0.58);
}
.pg-view-reticle { border-color: #19a994; box-shadow: 0 0 0 5px rgba(25,169,148,0.12); }
.pg-dpad-key {
  background: linear-gradient(145deg, #5c9dff, #2f70df);
  border-color: rgba(255,255,255,0.82);
  color: #fff;
  box-shadow: 0 3px 8px rgba(36,111,229,0.2);
}
.pg-dpad-key:active { background: linear-gradient(145deg, #1fbdcf, #1587c4); }
.pg-abxy-key { border-color: rgba(255,255,255,0.8); box-shadow: 0 5px 10px rgba(39,79,115,0.18); }
.pg-abxy-y { background: linear-gradient(145deg, #ffe66d, #f7bb24); }
.pg-abxy-x { background: linear-gradient(145deg, #78b6ff, #4a83ef); }
.pg-abxy-a { background: linear-gradient(145deg, #69df9b, #2bbd75); }
.pg-abxy-b { background: linear-gradient(145deg, #ff8b91, #ed5d71); }
.pg-abxy-letter { color: #173b61; text-shadow: none; }
.pg-mouse-track {
  background: rgba(255,255,255,0.62);
  border: 2px dashed rgba(28,166,151,0.58);
  box-shadow: inset 0 0 14px rgba(28,166,151,0.08);
}
.pg-mouse-crosshair { background: #19a994; box-shadow: 0 0 8px rgba(25,169,148,0.55); }
.pg-single-button {
  background: linear-gradient(145deg, var(--pg-custom-fill, #ffffff), var(--pg-custom-fill, #dcecff));
  border-color: var(--pg-custom-border, rgba(47,128,237,0.5));
  color: var(--pg-custom-text, #245488);
  box-shadow: 0 4px 10px rgba(47,128,237,0.16), inset 0 -3px 5px rgba(47,128,237,0.08);
}
.pg-shoulder .pg-single-button { background: linear-gradient(145deg, var(--pg-custom-fill, #42c7db), var(--pg-custom-fill, #168bc8)); color: var(--pg-custom-text, #fff); border-color: var(--pg-custom-border, rgba(255,255,255,0.72)); }
.pg-single-button:active { background: linear-gradient(145deg, #2f80ed, #1f5fc4); color: #fff; }
.pg-control-caption { color: #52759a; }

.pg-button-key {
  display: block;
  max-width: 88%;
  overflow: hidden;
  color: currentColor;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  word-break: keep-all;
  font-size: clamp(7px, 1.05vh, 9px);
  font-weight: 800;
  line-height: 1;
  opacity: .72;
}
.pg-edit-hitbox {
  position: absolute;
  inset: -7px;
  z-index: 40;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  border: 1px dashed rgba(38,112,205,.5);
  border-radius: 8px;
  background: rgba(74,145,235,.06);
  touch-action: none;
}
.pg-edit-hitbox.is-selected { border: 2px solid #2778e8; background: rgba(67,139,234,.13); box-shadow: 0 0 0 3px rgba(39,120,232,.14); }
.pg-edit-grip {
  width: 22px;
  height: 14px;
  margin-top: -11px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255,255,255,.82);
  border-radius: 5px;
  color: #fff;
  background: #2778e8;
  box-shadow: 0 2px 5px rgba(30,91,174,.22);
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
}

/* 按钮库的视觉模板，和竖屏按钮设置页保持同一套命名。 */
.pg-stage-themed .pg-single-button.pg-skin-fluent { background: linear-gradient(145deg,var(--pg-custom-fill,#68A5FF),var(--pg-custom-fill,#2D72DE)); color: var(--pg-custom-text,#fff); }
.pg-stage-themed .pg-single-button.pg-skin-matte { background: linear-gradient(145deg,var(--pg-custom-fill,#34465D),var(--pg-custom-fill,#172334)); color: var(--pg-custom-text,#fff); border-color: var(--pg-custom-border,#52657a); }
.pg-stage-themed .pg-single-button.pg-skin-arcade { background: radial-gradient(circle at 35% 25%,var(--pg-custom-fill,#FF9AA4),var(--pg-custom-fill,#D93649) 70%); color: var(--pg-custom-text,#fff); border-width: 3px; }
.pg-stage-themed .pg-single-button.pg-skin-glass { background: var(--pg-custom-fill,rgba(83,157,235,.22)); border-color: var(--pg-custom-border,rgba(54,124,203,.55)); color: var(--pg-custom-text,#2865A7); box-shadow: inset 0 0 14px rgba(255,255,255,.9),0 5px 10px rgba(61,108,150,.14); }
.pg-stage-themed .pg-single-button.pg-skin-keycap { background: linear-gradient(var(--pg-custom-fill,#fff),var(--pg-custom-fill,#D8E2EC)); border-color: var(--pg-custom-border,#9BA9B6); color: var(--pg-custom-text,#293B4C); box-shadow: inset 0 -5px 0 #8A98A6,0 5px 8px rgba(46,61,78,.2); }
.pg-stage-themed .pg-single-button.pg-skin-hud { background: var(--pg-custom-fill,#153942); border-color: var(--pg-custom-border,#2AD3C7); color: var(--pg-custom-text,#74FFF2); box-shadow: inset 0 0 10px rgba(42,211,199,.3),0 0 8px rgba(42,211,199,.38); }
.pg-stage-themed .pg-single-button.pg-skin-skill { background: radial-gradient(circle,var(--pg-custom-fill,#6758C1),var(--pg-custom-fill,#292454) 68%); border-color: var(--pg-custom-border,#D6BA68); color: var(--pg-custom-text,#FFE8A0); box-shadow: 0 0 0 3px #4B4028,0 5px 9px rgba(43,34,89,.3); }
.pg-stage-themed .pg-single-button.pg-skin-pixel { background: var(--pg-custom-fill,#F2D64F); border-color: var(--pg-custom-border,#243346); border-radius: 0; color: var(--pg-custom-text,#243346); box-shadow: 4px 4px 0 #243346; }
.pg-stage-themed .pg-single-button.pg-skin-switch { background: var(--pg-custom-fill,#E95763); color: var(--pg-custom-text,#fff); box-shadow: inset 0 -5px 0 #B93644,0 5px 9px rgba(162,43,56,.24); }
.pg-stage-themed .pg-single-button.pg-skin-outline { background: var(--pg-custom-fill,transparent); border-color: var(--pg-custom-border,#4B7BAA); color: var(--pg-custom-text,#4B7BAA); box-shadow: none; }
.pg-stage-themed .pg-single-button.pg-skin-neon { background: var(--pg-custom-fill,#17142E); border-color: var(--pg-custom-border,#ED5AFF); color: var(--pg-custom-text,#72EAFF); box-shadow: 0 0 9px rgba(237,90,255,.65),inset 0 0 9px rgba(114,234,255,.18); }
.pg-stage-themed .pg-single-button.pg-skin-contrast { background: var(--pg-custom-fill,#FFEB00); border-color: var(--pg-custom-border,#111); color: var(--pg-custom-text,#111); box-shadow: inset 0 -4px 0 #D3C000,0 4px 0 #111; }

.layout-tools {
  position: fixed;
  z-index: 80;
  top: calc(8px + env(safe-area-inset-top));
  right: calc(9px + env(safe-area-inset-right));
  width: min(286px, 40vw);
  max-height: calc(84vh - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.38);
  border-radius: 8px;
  color: #f7fbff;
  background: rgba(18,34,54,.64);
  box-shadow: 0 8px 24px rgba(10,30,52,.2);
  backdrop-filter: blur(8px);
  touch-action: none;
}
.layout-tools button { margin: 0; padding: 0; }
.layout-tools button::after { border: 0; }
.tools-heading { flex: 0 0 auto; padding: 9px 10px 8px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,.12); background: rgba(12,28,46,.2); cursor: move; }
.tools-heading-copy { min-width: 0; }
.tools-heading-actions { flex: 0 0 auto; margin-left: 8px; display: flex; align-items: center; gap: 5px; }
.tools-drag-grip { color: rgba(220,236,255,.72); font-size: 15px; font-weight: 800; line-height: 1; letter-spacing: 0; }
.tools-title,.tools-subtitle { display: block; }.tools-title { font-size: 14px; font-weight: 850; }.tools-subtitle { margin-top: 2px; color: #afc7dc; font-size: 9px; }
.tools-close { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 6px; color: #dcecff; background: rgba(255,255,255,.09); font-size: 19px; line-height: 1; }
.tools-content { flex: 1 1 auto; min-height: 0; padding: 10px 12px 13px; box-sizing: border-box; }
.tools-section-label { display: block; margin-bottom: 7px; color: #b9cee0; font-size: 9px; font-weight: 750; }
.layout-strip { width: 100%; white-space: nowrap; }
.layout-chip { height: 30px; margin-right: 6px !important; padding: 0 10px !important; display: inline-flex; align-items: center; border: 1px solid rgba(255,255,255,.17); border-radius: 6px; color: #d8e8f5; background: rgba(255,255,255,.07); font-size: 10px; font-weight: 700; }
.layout-chip.active { border-color: #6bb0ff; color: #fff; background: rgba(55,134,228,.48); }.layout-chip.layout-new { border-style: dashed; color: #8dc4ff; }
.tool-tabs { margin-top: 11px; padding: 3px; display: grid; grid-template-columns: repeat(2,1fr); gap: 3px; border-radius: 7px; background: rgba(4,18,34,.32); }
.tool-tab { height: 30px; border-radius: 5px; color: #abc1d5; background: transparent; font-size: 10px; font-weight: 750; }.tool-tab.active { color: #153b65; background: #eaf5ff; }
.preset-grid { margin-top: 10px; display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 7px; }
.preset-item { position: relative; min-width: 0; height: 78px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,.13); border-radius: 7px; color: #eaf5ff; background: rgba(255,255,255,.06); }
.preset-sample { width: 34px; height: 30px; display: grid; place-items: center; border: 1px solid rgba(255,255,255,.76); border-radius: 9px; color: #fff; background: linear-gradient(145deg,#68A5FF,#2D72DE); font-size: 8px; font-weight: 850; box-shadow: inset 0 -3px rgba(5,33,69,.2); }
.preset-sample.pg-skin-matte { background: linear-gradient(145deg,#34465D,#172334); }
.preset-sample.pg-skin-arcade { border-radius: 50%; background: radial-gradient(circle at 35% 25%,#FF9AA4,#D93649 70%); }
.preset-sample.pg-skin-glass { border-color: rgba(112,184,255,.7); background: rgba(83,157,235,.24); color: #d7efff; }
.preset-sample.pg-skin-keycap { border-color: #9BA9B6; background: linear-gradient(#fff,#D8E2EC); color: #293B4C; }
.preset-sample.pg-skin-hud { border-color: #2AD3C7; background: #153942; color: #74FFF2; }
.preset-sample.pg-skin-skill { border-radius: 50%; border-color: #D6BA68; background: radial-gradient(circle,#6758C1,#292454 68%); color: #FFE8A0; }
.preset-sample.pg-skin-pixel { border-radius: 0; border-color: #243346; background: #F2D64F; color: #243346; box-shadow: 3px 3px #243346; }
.preset-sample.pg-skin-switch { border-radius: 50%; background: #E95763; }
.preset-sample.pg-skin-outline { border-color: #76b8fa; background: transparent; color: #9aceff; box-shadow: none; }
.preset-sample.pg-skin-neon { border-color: #ED5AFF; background: #17142E; color: #72EAFF; box-shadow: 0 0 7px rgba(237,90,255,.65); }
.preset-sample.pg-skin-contrast { border-color: #111; background: #FFEB00; color: #111; }
.preset-name { max-width: 90%; margin-top: 7px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 9px; font-weight: 700; }.preset-custom { position: absolute; top: 3px; right: 4px; color: #87c6ff; font-size: 6px; }
.selected-tools { margin-top: 10px; }.selected-summary { padding: 8px 9px; display: flex; justify-content: space-between; border: 1px solid rgba(255,255,255,.13); border-radius: 7px; background: rgba(255,255,255,.05); }.selected-name { font-size: 11px; font-weight: 800; }.selected-key { max-width: 55%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #8dc4ff; font-size: 9px; }
.size-control { margin-top: 9px; display: grid; grid-template-columns: 30px 1fr 30px 34px; align-items: center; gap: 5px; }.size-step { width: 30px; height: 30px; border-radius: 6px; color: #fff; background: rgba(255,255,255,.1); font-size: 16px; }.size-slider { width: 100%; }.size-value { text-align: right; color: #c8dcf0; font-size: 9px; font-weight: 800; }
.selected-actions { margin-top: 9px; display: grid; grid-template-columns: repeat(3,1fr); gap: 6px; }.selected-action { height: 32px; border: 1px solid rgba(255,255,255,.15); border-radius: 6px; color: #dbeafa; background: rgba(255,255,255,.07); font-size: 10px; font-weight: 800; }.selected-action.primary { border-color: #72b3ff; background: #327ed8; color: #fff; }.selected-action.danger { border-color: rgba(255,137,148,.45); color: #ffabb4; }
.selected-empty { height: 88px; display: grid; place-items: center; color: #a9c0d4; font-size: 10px; }

/* 与桌面编辑器共用的五套背景/按钮变量。 */
.pg-stage-bg-mobile-light {
  --pg-stage-top: #f9fdff; --pg-stage-bottom: #dff0f8; --pg-grid: rgba(74,130,153,0.10);
  --pg-button-top: #58a8ff; --pg-button-bottom: #286cda; --pg-button-text: #ffffff;
  --pg-button-border: rgba(223,245,255,0.92); --pg-control-fill: rgba(223,247,245,0.72);
  --pg-control-inner: #eef9fc; --pg-control-border: rgba(73,187,178,0.72); --pg-accent: #18a899;
}
.pg-stage-bg-mobile-dark {
  --pg-stage-top: #1e2536; --pg-stage-bottom: #0f1320; --pg-grid: rgba(255,255,255,0.025);
  --pg-button-top: #2a3142; --pg-button-bottom: #1a1f2c; --pg-button-text: #cbd5e1;
  --pg-button-border: rgba(148,163,184,0.28); --pg-control-fill: #1a1f2c;
  --pg-control-inner: #475569; --pg-control-border: rgba(148,163,184,0.38); --pg-accent: #38bdf8;
}
.pg-stage-bg-terrain {
  --pg-stage-top: #246381; --pg-stage-bottom: #336b52; --pg-grid: rgba(35,64,76,0.08);
  --pg-button-top: #367efa; --pg-button-bottom: #1c56c8; --pg-button-text: #eff9ff;
  --pg-button-border: rgba(91,164,255,0.8); --pg-control-fill: #10428b;
  --pg-control-inner: #46a1ff; --pg-control-border: rgba(90,166,255,0.8); --pg-accent: #48ded3;
}
.pg-stage-bg-arcade-neon {
  --pg-stage-top: #20152f; --pg-stage-bottom: #111b2b; --pg-grid: rgba(214,109,255,0.12);
  --pg-button-top: #36234a; --pg-button-bottom: #1c1730; --pg-button-text: #f8e8ff;
  --pg-button-border: rgba(219,115,255,0.74); --pg-control-fill: #2e1b4b;
  --pg-control-inner: #5e2d78; --pg-control-border: rgba(226,119,255,0.76); --pg-accent: #ff6bc7;
}
.pg-stage-bg-paper-grid {
  --pg-stage-top: #edf3f6; --pg-stage-bottom: #dfe8ed; --pg-grid: rgba(87,113,124,0.22);
  --pg-button-top: #ffffff; --pg-button-bottom: #d9e4ea; --pg-button-text: #20323a;
  --pg-button-border: rgba(77,123,140,0.56); --pg-control-fill: #d5e2e8;
  --pg-control-inner: #9dbdc8; --pg-control-border: rgba(77,123,140,0.7); --pg-accent: #0d9296;
}
.pg-stage-themed {
  background: radial-gradient(ellipse at center, var(--pg-stage-top) 0%, var(--pg-stage-bottom) 100%);
}
.pg-stage-themed.pg-stage-bg-terrain {
  background:
    linear-gradient(112deg, transparent 0 43%, rgba(183,174,119,0.88) 43% 55%, transparent 55%),
    linear-gradient(180deg, var(--pg-stage-top) 0 48%, var(--pg-stage-bottom) 48% 100%);
}
.pg-stage-themed .pg-grid {
  background-image: linear-gradient(var(--pg-grid) 1px, transparent 1px), linear-gradient(90deg, var(--pg-grid) 1px, transparent 1px);
}
.pg-stage-themed .pg-stick-ring,
.pg-stage-themed .pg-view-ring {
  background: var(--pg-custom-fill, var(--pg-control-fill)); border-color: var(--pg-custom-border, var(--pg-control-border));
  box-shadow: inset 0 0 0 8px rgba(255,255,255,0.06), 0 5px 14px rgba(0,0,0,0.22);
}
.pg-stage-themed .pg-dpad-key { background: linear-gradient(145deg, var(--pg-button-top), var(--pg-button-bottom)); border-color: var(--pg-button-border); color: var(--pg-button-text); }
.pg-stage-themed .pg-view-reticle,
.pg-stage-themed .pg-mouse-crosshair { border-color: var(--pg-accent); background: var(--pg-accent); box-shadow: 0 0 8px var(--pg-accent); }
.pg-stage-themed .pg-dpad-center { background: var(--pg-stage-bottom); }
.pg-stage-themed .pg-abxy-key { background: linear-gradient(145deg, var(--pg-button-top), var(--pg-button-bottom)); border-color: var(--pg-button-border); }
.pg-stage-themed .pg-mouse-track { background: var(--pg-control-fill); border-color: var(--pg-control-border); }
.pg-stage-themed .pg-single-button {
  background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom)));
  border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text));
}
.pg-stage-themed .pg-control-caption { color: var(--pg-button-text); }
.pg-stage-bg-mobile-light .pg-control-caption { color: #315864; }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-y { background: linear-gradient(145deg, var(--pg-custom-fill, #ffe66d), var(--pg-custom-fill, #f7bb24)); color: var(--pg-custom-text, #173b61); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-x { background: linear-gradient(145deg, var(--pg-custom-fill, #78b6ff), var(--pg-custom-fill, #4a83ef)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-a { background: linear-gradient(145deg, var(--pg-custom-fill, #69df9b), var(--pg-custom-fill, #2bbd75)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, #ff8b91), var(--pg-custom-fill, #ed5d71)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed .pg-dpad-key { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-button-bottom)); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
.pg-stage-themed .pg-abxy-y,
.pg-stage-themed .pg-abxy-x,
.pg-stage-themed .pg-abxy-a,
.pg-stage-themed .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom))); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
</style>
