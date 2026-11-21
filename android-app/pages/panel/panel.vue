<template>
<view :class="['page', 'panel-page', appAppearanceClasses, { 'has-fullscreen-widget': !!fullscreenWidgetId }]" :style="appAppearanceStyle">
  <scroll-view :scroll-y="componentScrollEnabled && !fullscreenWidgetId" :bounces="componentScrollEnabled && !fullscreenWidgetId" class="panel-scroll" show-scrollbar="false">
  <view class="panel-scroll-content">
  <!-- 设备状态条(替代 navbar + status-row) -->
  <view class="device-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
    <view class="device-info" hover-class="device-info-hover" @tap="onGoConnect">
      <view class="status-row">
        <view :class="['status-dot', connectionAvailable ? 'on' : 'off']"></view>
        <text class="status-text">
          <text v-if="connectionAvailable">已连接</text>
          <text v-else>未连接</text>
        </text>
      </view>
      <view class="device-name">
        <text class="device-name-text" v-if="connectionAvailable">{{ connectionLabel }}</text>
        <text class="device-name-text" v-else>点击连接</text>
        <text class="status-arrow">›</text>
      </view>
    </view>
    <view class="more-btn" hover-class="more-btn-hover" @tap="onTapMore">
      <text class="more-btn-dot">⋯</text>
    </view>
  </view>
  <view v-if="connectionMode === 'ble' && hidConnected && !connected" class="basic-mode-tip">
    <text>快捷键、键盘、鼠标可用；网址、应用、中文文字和同步需打开电脑端。</text>
  </view>


  <!-- 每个 widget 一个统一卡片,头可收起,体可展开 -->
  <view v-for="w in visibleWidgets"
        :key="w.id"
        class="widget-slot"
        :class="{ 'is-picker-open': w.type === 'key-grid' && keyPickerOpen, 'is-widget-fullscreen': fullscreenWidgetId === w.id }"
        @tap.stop>
    <view class="widget-shell"
          :class="{ 'is-collapsed': !!w.collapsed && fullscreenWidgetId !== w.id, 'is-codex-micro': w.type === 'codex-micro', 'is-jianying-workbench': w.type === 'jianying-workbench', 'is-jianying-landscape': w.type === 'jianying-workbench' && fullscreenWidgetId === w.id && jianyingLandscape, 'is-focus-mode': w.type === 'focus-mode' }"
          :data-wtype="w.type"
          @tap.stop="onWidgetShellTap(w)">
      <view class="widget-head">
        <view class="widget-head-icon">
          <text class="widget-head-icon-text">{{widgetIcon(w.type)}}</text>
        </view>
        <text class="widget-head-title">{{w.type === 'text-input' ? '文字输入' : (w.title || w.type)}}</text>
        <view class="widget-head-actions">
          <view v-if="w.type === 'key-grid'"
                class="widget-head-action widget-head-switch"
                hover-class="widget-head-action-hover"
                @tap.stop="onOpenKeySchemePicker">
            <text class="widget-head-switch-icon">⇄</text>
          </view>
          <view v-if="w.type === 'codex-micro'"
                class="widget-head-action widget-head-edit"
                hover-class="widget-head-action-hover"
                @tap.stop="onEditCodexMicro">
            <text class="widget-head-edit-icon">✎</text>
          </view>
          <view v-if="w.type === 'jianying-workbench'"
                class="widget-head-action widget-head-edit"
                hover-class="widget-head-action-hover"
                @tap.stop="onEditJianying(w)">
            <text class="widget-head-edit-icon">✎</text>
          </view>
          <view v-if="w.type === 'jianying-workbench' && fullscreenWidgetId === w.id"
                class="widget-head-action widget-head-orientation"
                hover-class="widget-head-action-hover"
                role="button"
                :aria-label="jianyingLandscape ? '切换为竖屏' : '切换为横屏'"
                @tap.stop="onToggleJianyingOrientation(w)">
            <text class="widget-head-orientation-icon">{{jianyingLandscape ? '▯' : '▭'}}</text>
          </view>
          <view v-if="w.type === 'mouse-control'"
                class="widget-head-action widget-head-fullscreen"
                hover-class="widget-head-action-hover"
                role="button"
                aria-label="打开全屏触摸板"
                @tap.stop="onOpenFullscreenTrackpad">
            <text class="widget-head-fullscreen-icon">⛶</text>
          </view>
          <view v-else-if="w.type === 'full-keyboard'"
                class="widget-head-action widget-head-fullscreen"
                hover-class="widget-head-action-hover"
                role="button"
                aria-label="打开全屏键盘"
                @tap.stop="onOpenFullscreenKeyboard">
            <text class="widget-head-fullscreen-icon">⛶</text>
          </view>
          <view v-else-if="w.type === 'gamepad'"
                class="widget-head-action widget-head-fullscreen"
                hover-class="widget-head-action-hover"
                role="button"
                aria-label="打开横屏游戏手柄"
                @tap.stop="pgOpenFullscreen">
            <text class="widget-head-fullscreen-icon">⛶</text>
          </view>
          <view v-else
                class="widget-head-action widget-head-fullscreen"
                hover-class="widget-head-action-hover"
                role="button"
                :aria-label="fullscreenWidgetId === w.id ? '关闭弹窗' : '弹窗显示'"
                @tap.stop="onToggleWidgetFullscreen(w)">
            <text class="widget-head-fullscreen-icon">{{fullscreenWidgetId === w.id ? '×' : '⛶'}}</text>
          </view>
          <view v-if="fullscreenWidgetId !== w.id"
                class="widget-head-action widget-head-toggle"
                hover-class="widget-head-action-hover"
                @tap.stop="onToggleWidget(w.id)">
            <text class="widget-head-toggle-icon">{{w.collapsed ? '⌄' : '⌃'}}</text>
          </view>
        </view>
      </view>
      <view v-if="!w.collapsed || fullscreenWidgetId === w.id" class="widget-body">
        <PanelKeyGrid v-if="w.type === 'key-grid'"
                      ref="keyGrid"
                      :slots="slots"
                      :grid-cols="gridCols"
                      :grid-rows="gridRows"
                      :layout-name="activeLayoutName"
                      :page-name="activePageName"
                      :layouts="layouts"
                      :active-layout-id="activeLayoutId"
                      :active-page-id="activePageId"
                      @pick-layout="onPickLayoutEvent"
                      @picker-visible-change="onKeyPickerVisibleChange" />
        <PanelTextInput v-else-if="w.type === 'text-input'" />
        <PanelMouseControl v-else-if="w.type === 'mouse-control'"
                           ref="mouseControl"
                           :force-expand="isFocused" />
        <PanelJianyingWorkbench v-else-if="w.type === 'jianying-workbench'"
                                :storage-scope="currentLayoutId + ':' + w.id"
                                :config-revision="jianyingRevision" />
        <PanelVolumeControl v-else-if="w.type === 'volume-control'" />
        <view v-else-if="w.type === 'focus-mode'" class="focus-card">
          <view class="focus-row focus-row-main">
            <view class="focus-info">
              <text class="focus-mode">{{ focusSnapshot.modeLabel }}</text>
              <text class="focus-duration">{{ focusSnapshot.durationLabel }}</text>
            </view>
            <view class="focus-cta">
              <text class="focus-cta-text">点此开始专注</text>
              <text class="focus-cta-arrow">›</text>
            </view>
          </view>
          <view class="focus-row focus-row-sub">
            <view class="focus-chip">
              <text class="focus-chip-icon">{{ focusSnapshot.strictChipIcon }}</text>
              <text class="focus-chip-text">{{ focusSnapshot.strictChipText }}</text>
            </view>
            <view class="focus-chip">
              <text class="focus-chip-icon">🛡</text>
              <text class="focus-chip-text">白名单 {{ focusSnapshot.whitelistCount }} 个</text>
            </view>
            <view v-if="focusSnapshot.lastHistory" class="focus-chip focus-chip-muted">
              <text class="focus-chip-text">上次 {{ focusSnapshot.lastHistory }}</text>
            </view>
          </view>
        </view>
        <PanelFullKeyboard v-else-if="w.type === 'full-keyboard'" ref="fullKeyboard" :force-expand="false" @open-request="onOpenFullscreenKeyboard" @fullscreen-change="onKeyboardFullscreenChange" />
        <PanelCodexMicro v-else-if="w.type === 'codex-micro'"
                         :connected="connected"
                         :available="codexAvailable"
                         :tasks="codexTasks"
                         :desktop-bindings="codexDesktopBindings"
                         :approval="codexApproval"
                         :initial-reasoning="codexReasoning"
                         @submit-task="onCodexSubmit"
                         @set-reasoning="onCodexSetReasoning"
                         @approve="onCodexApprove"
                         @reject="onCodexReject"
                         @cancel="onCodexCancel"
                          @refresh="onCodexRefresh"
                         @voice-start="onCodexVoiceStart"
                         @test-input="onCodexTestInput"
                         @zhipu-voice-start="onCodexZhipuVoiceStart"
                         @zhipu-voice-end="onCodexZhipuVoiceEnd"
                         @submit-enter="onCodexSubmitEnter"
                          @bind-current-task="onCodexBindCurrentTask"
                          @focus-bound-task="onCodexFocusBoundTask"
                          @open-new-task="onCodexOpenNewTask"
                          @rename-bound-task="onCodexRenameBoundTask"
                         @unbind-bound-task="onCodexUnbindBoundTask"
                         @dictate="onCodexDictate" />
        <view v-else-if="w.type === 'gamepad'"
              class="inline-gamepad-widget"
              :class="{
                'is-disabled': !connected,
                'is-pressed': pgPressed,
                'has-layout': !!pgActiveLayout
              }"
              hover-class="inline-gamepad-widget-hover"
              hover-stay-time="80"
              @tap="pgOpenFullscreen"
              @touchstart="pgPressed = true"
              @touchend="pgPressed = false"
              @touchcancel="pgPressed = false">
          <!-- 紧凑标题条：布局名称和连接状态只展示一次。 -->
          <view class="pg-card-header">
            <view class="pg-card-mark" :class="pgStatusClass">
              <view class="pg-card-mark-dot"></view>
            </view>
            <text class="pg-card-title">{{ pgActiveLayout ? pgActiveLayout.name : '自定义手柄' }}</text>
            <text class="pg-card-sub">{{ pgStatusLabel }}</text>
          </view>
          <view class="inline-gamepad">

          <view v-if="pgActiveLayout" class="pg-stage pg-stage-themed" :class="pgBackgroundStageClass" :style="pgBackgroundStageStyle">
            <view class="pg-grid"></view>
            <view
              v-for="control in pgActiveLayout.controls"
              :key="control.id"
              class="pg-control"
              :class="[
                'pg-control-' + control.type,
                { 'pg-control-wide': control.variant === 'wide' }
              ]"
              :style="pgControlStyle(control)"
            >
              <view v-if="control.type === 'leftStick'" class="pg-stick-zone">
                <view class="pg-stick-ring">
                  <view class="pg-stick-up"    @touchstart.stop="pgOnStickStart(control, 'up')"    @touchend.stop="pgOnStickEnd(control, 'up')"    @touchcancel.stop="pgOnStickEnd(control, 'up')"></view>
                  <view class="pg-stick-right" @touchstart.stop="pgOnStickStart(control, 'right')" @touchend.stop="pgOnStickEnd(control, 'right')" @touchcancel.stop="pgOnStickEnd(control, 'right')"></view>
                  <view class="pg-stick-down"  @touchstart.stop="pgOnStickStart(control, 'down')"  @touchend.stop="pgOnStickEnd(control, 'down')"  @touchcancel.stop="pgOnStickEnd(control, 'down')"></view>
                  <view class="pg-stick-left"  @touchstart.stop="pgOnStickStart(control, 'left')"  @touchend.stop="pgOnStickEnd(control, 'left')"  @touchcancel.stop="pgOnStickEnd(control, 'left')"></view>
                  <view class="pg-stick-center"></view>
                </view>
              </view>

              <view v-else-if="control.type === 'rightStick'" class="pg-stick-zone">
                <view class="pg-stick-ring pg-view-ring"
                      @touchstart.stop="pgOnViewStart(control, $event)"
                      @touchmove.stop="pgOnViewMove(control, $event)"
                      @touchend.stop="pgOnViewEnd(control, $event)"
                      @touchcancel.stop="pgOnViewEnd(control, $event)">
                  <view class="pg-view-reticle"></view>
                </view>
              </view>

              <view v-else-if="control.type === 'dpad'" class="pg-dpad-zone">
                <view class="pg-dpad-up"    @touchstart.stop="pgOnKeyStart(control, 'up')"    @touchend.stop="pgOnKeyEnd(control, 'up')"    @touchcancel.stop="pgOnKeyEnd(control, 'up')">↑</view>
                <view class="pg-dpad-left"  @touchstart.stop="pgOnKeyStart(control, 'left')"  @touchend.stop="pgOnKeyEnd(control, 'left')"  @touchcancel.stop="pgOnKeyEnd(control, 'left')">←</view>
                <view class="pg-dpad-right" @touchstart.stop="pgOnKeyStart(control, 'right')" @touchend.stop="pgOnKeyEnd(control, 'right')" @touchcancel.stop="pgOnKeyEnd(control, 'right')">→</view>
                <view class="pg-dpad-down"  @touchstart.stop="pgOnKeyStart(control, 'down')"  @touchend.stop="pgOnKeyEnd(control, 'down')"  @touchcancel.stop="pgOnKeyEnd(control, 'down')">↓</view>
                <view class="pg-dpad-center"></view>
              </view>

              <view v-else-if="control.type === 'abxy'" class="pg-abxy-zone">
                <view class="pg-abxy-y" @touchstart.stop="pgOnKeyStart(control, 'y')" @touchend.stop="pgOnKeyEnd(control, 'y')" @touchcancel.stop="pgOnKeyEnd(control, 'y')">Y</view>
                <view class="pg-abxy-x" @touchstart.stop="pgOnKeyStart(control, 'x')" @touchend.stop="pgOnKeyEnd(control, 'x')" @touchcancel.stop="pgOnKeyEnd(control, 'x')">X</view>
                <view class="pg-abxy-a" @touchstart.stop="pgOnKeyStart(control, 'a')" @touchend.stop="pgOnKeyEnd(control, 'a')" @touchcancel.stop="pgOnKeyEnd(control, 'a')">A</view>
                <view class="pg-abxy-b" @touchstart.stop="pgOnKeyStart(control, 'b')" @touchend.stop="pgOnKeyEnd(control, 'b')" @touchcancel.stop="pgOnKeyEnd(control, 'b')">B</view>
              </view>

              <view v-else-if="control.type === 'mouse'" class="pg-mouse-zone">
                <view class="pg-mouse-track"
                      @touchstart.stop="pgOnMouseStart(control, $event)"
                      @touchmove.stop="pgOnMouseMove(control, $event)"
                      @touchend.stop="pgOnMouseEnd(control, $event)"
                      @touchcancel.stop="pgOnMouseEnd(control, $event)">
                  <view class="pg-mouse-crosshair"></view>
                </view>
              </view>

              <view v-else class="pg-button-control" :class="{ 'pg-shoulder': control.type === 'shoulder' }">
                <view
                  class="pg-single-button"
                  :class="{
                    'pg-single-wide': control.variant === 'wide' || control.type === 'shoulder',
                    'pg-single-round': control.type === 'key',
                    'pg-shape-square': control.appearance && control.appearance.shape === 'square',
                    'pg-shape-pill': control.appearance && control.appearance.shape === 'pill',
                    'pg-shape-diamond': control.appearance && control.appearance.shape === 'diamond'
                  }"
                  @touchstart.stop="pgOnKeyStart(control, 'press')"
                  @touchend.stop="pgOnKeyEnd(control, 'press')"
                  @touchcancel.stop="pgOnKeyEnd(control, 'press')"
                >
                  <text class="pg-button-label">{{ control.label || 'KEY' }}</text>
                </view>
              </view>
            </view>
          </view>

          <view v-else class="pg-empty-state">
            <text class="pg-empty-text">{{ pgEmptyText }}</text>
          </view>

          <!-- 提示:点卡片进横屏全屏 -->
          <view class="pg-card-foot">
            <text class="pg-card-foot-text">点击卡片进入横屏全屏 ›</text>
          </view>
          </view>
        </view>
        <view v-else class="empty-hint">
          <text class="empty-hint-icon">⚠</text>
          <text class="empty-hint-title">此组件已被移除</text>
          <text class="empty-hint-sub">原类型: {{w.type}} — 旧版本残留</text>
          <view class="empty-hint-action" hover-class="empty-hint-action-hover" @tap.stop="onRemoveWidget(w.id)">
            <text>点此删除</text>
          </view>
        </view>
      </view>
    </view>
  </view>
<!-- 焦点模式:显示「返回面板」入口(回到完整 panel) -->
  <view v-if="isFocused" class="focus-back" hover-class="focus-back-hover" @tap="onExitFocus">
    <text class="focus-back-icon">‹</text>
    <text class="focus-back-label">返回面板</text>
  </view>
<!-- 添加组件占位:仅非焦点模式显示 -->
  <view v-if="!isFocused" class="widget-add" hover-class="widget-add-hover" @tap="onTapAddWidget">
    <text class="widget-add-plus">＋</text>
    <text class="widget-add-label">添加组件</text>
  </view>

  <view class="panel-scroll-bottom"></view>
  </view>

  </scroll-view>
    <CustomTabBar v-if="!keyboardFullscreen && !fullscreenWidgetId" variant="panel" />
  </view>

  <!-- 右上角三个点菜单 -->
  <MoreMenu :show="moreMenuShow" :all-collapsed="false" @select="onMoreMenuSelect" @close="moreMenuShow = false" />
</template>


<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
import Net from '@/utils/net.js'
import PanelTextInput from '@/components/PanelTextInput.vue'
import PanelKeyGrid from '@/components/PanelKeyGrid.vue'
import PanelMouseControl from '@/components/PanelMouseControl.vue'
import PanelVolumeControl from '@/components/PanelVolumeControl.vue'
import { loadConfig as _loadFocusConfig, loadHistory as _loadFocusHistory, getWhitelistEntries as _getWhitelistEntries, getModeMeta as _getModeMeta } from '@/utils/focusConfig.js'
import PanelFullKeyboard from '@/components/PanelFullKeyboard.vue'
import PanelCodexMicro from '@/components/PanelCodexMicro.vue'
import PanelJianyingWorkbench from '@/components/PanelJianyingWorkbench.vue'
import MoreMenu from '@/components/MoreMenu.vue'
import { lockLandscape, lockPortrait } from '@/utils/orientation.js'
import { showTransientToast } from '@/utils/transientToast.js'
import {
  buildApprovalNotification,
  buildInputNotification,
  buildTaskNotification,
  playCodexInputSound,
  playCodexTerminalSound,
  postLocalNotification,
  requestCodexNotificationPermission,
} from '@/utils/codexNotification.js'
import {
  getCurrentLayout,
  setLayoutWidgetCollapsed,
} from '@/utils/layoutConfig.js'
import {
  loadWidgets,
  saveWidgets,
} from '@/utils/widgetConfig.js'

export default {
  components: { PanelTextInput, PanelKeyGrid, PanelMouseControl, PanelVolumeControl, PanelFullKeyboard, PanelCodexMicro, PanelJianyingWorkbench, CustomTabBar, MoreMenu },
  computed: {
    connectionAvailable() {
      return this.connected || (this.connectionMode === 'ble' && this.hidConnected)
    },
    connectionLabel() {
      if (this.connectionMode === 'ble') return this.connected ? '蓝牙完整模式' : '蓝牙基础模式'
      if (this.connectionMode === 'wifi') return 'WiFi连接'
      return 'USB连接'
    },
    // 面板 widget 列表:同时受 visible 与 focusedWidgetType 过滤
    visibleWidgets() {
      const list = (this.widgets || []).filter(function (w) { return w && w.visible !== false })
      if (this.focusedWidgetType) {
        return list.filter(function (w) { return w && w.type === this.focusedWidgetType }.bind(this))
      }
      return list
    },
    // 是否处于「单 widget 焦点模式」:由 tab 决定
    isFocused() {
      return !!this.focusedWidgetType
    },
    focusedTitle() {
      if (!this.focusedWidgetType) return ''
      const t = (this._activeTab && this._activeTab.label) || ''
      return t
    },
    // === 内联的游戏手柄 (从 PanelGamepad.vue 合并) ===
    pgActiveLayout() {
      const d = this.pgLayouts
      if (!d || !Array.isArray(d.layouts)) return null
      return d.layouts.find(l => l.id === d.activeLayoutId) || d.layouts[0] || null
    },
    pgBackgroundStageClass() {
      const background = (this.pgActiveLayout && this.pgActiveLayout.background) || {}
      const id = background.baseId || background.id
      return 'pg-stage-bg-' + (id || 'mobile-light')
    },
    pgBackgroundStageStyle() {
      const background = (this.pgActiveLayout && this.pgActiveLayout.background) || {}
      const theme = background.theme || {}
      const canvas = (this.pgActiveLayout && this.pgActiveLayout.canvas) || {}
      const width = Math.max(1, Number(canvas.width || 2400))
      const height = Math.max(1, Number(canvas.height || 1080))
      const fields = {
        stage_top: '--pg-stage-top', stage_bottom: '--pg-stage-bottom', grid: '--pg-grid',
        button_top: '--pg-button-top', button_bottom: '--pg-button-bottom',
        button_text: '--pg-button-text', button_border: '--pg-button-border',
        control_fill: '--pg-control-fill', control_inner: '--pg-control-inner',
        control_border: '--pg-control-border', accent: '--pg-accent',
      }
      return Object.keys(fields).reduce(function(style, key) {
        if (theme[key]) style[fields[key]] = theme[key]
        return style
      }, { paddingBottom: ((height / width) * 100).toFixed(4) + '%' })
    },
    pgStatusClass() {
      if (!this.connected) return 'is-offline'
      if (!this.pgActiveLayout) return 'is-warning'
      return 'is-on'
    },
    pgStatusLabel() {
      if (!this.connected) return '未连接'
      if (!this.pgActiveLayout) return '电脑未推送布局'
      return '已同步'
    },
    pgEmptyText() {
      if (!this.connected) return '连接电脑后,这里显示游戏手柄控件'
      return '等待电脑端推送布局'
    },
  },
  data() {
    return {
      host: '',
      port: 9876,
      connected: false,
      hidConnected: false,
      connectionMode: 'usb',
      // 第三阶段:从当前 layout 读取 widgets(不再是全局 widgets 数组)
      widgets: [],
      // 标记当前 layout id(用于跨页编辑后重新读 storage)
      currentLayoutId: '',
      jianyingRevision: 0,
      // 右上角菜单
      moreMenuShow: false,
      // === 阶段 3:由 panel_schemes.active_scheme_id 对应方案的 components 驱动 ===

      layouts: [],
      activeLayoutId: '',
      activeLayoutName: '默认',
      activePageId: '',
      activePageName: '—',
      slots: [],
      gridRows: 4,
      gridCols: 4,
      anyTpExpanded: false,
      keyboardFullscreen: false,
      fullscreenWidgetId: '',
      jianyingLandscape: false,
      keyPickerOpen: false,
      // 焦点模式:由底部 tab 决定,只显示一个 widget
      focusedWidgetType: '',
      _activeTab: null,
      // 系统状态栏高度(用于 navbar 适配,iOS notch + Android)
      statusBarHeight: 20,
      codexTasks: [],
      codexDesktopBindings: {},
      codexApproval: { pending: false, ambiguous: false, fingerprint: '', slot: 0, thread_id: '', msg: '' },
      codexAvailable: false,
      codexReasoning: 'high',
      codexWorkspace: '',
      codexVoiceTarget: '',
      codexMessageListener: null,
      layoutsListener: null,
      codexCompletionSeen: {},
      codexApprovalSeen: {},
      codexInputSeen: {},
      netStateListener: null,
      hidStateListener: null,
      codexTestRequestId: '',
      codexTestTimer: null,
      codexApprovalTimer: null,
      codexBindingTimer: null,
      codexBindingReconcileTimer: null,
      codexBindingRequestId: '',
      // === 内联的游戏手柄 (从 PanelGamepad.vue 合并) ===
      pgLayouts: null,
      pgPressedKeys: {},
      pgStickActive: null,
      pgMouseActive: null,
      pgMouseLastPoint: null,
      _pgLayoutListener: null,
      // widget 卡是否被按下(用于按下高亮反馈)
      pgPressed: false,
      componentScrollEnabled: false,
      focusSnapshot: { modeLabel: '倒计时 · 25 分钟', durationLabel: '25 min', strictChipIcon: '🔓', strictChipText: '宽松模式', whitelistCount: 0, lastHistory: '' },
    }
  },
  onShow() {
    const self = this
    self.jianyingRevision += 1
    // 横屏游戏手柄返回后，部分 Android 基座会异步恢复原生 TabBar。
    // 面板使用的是自定义底栏，因此回到页面时再次隐藏原生栏。
    const hideNativeTabBar = function () {
      try { uni.hideTabBar({ animation: false }) } catch (e) {}
    }
    hideNativeTabBar()
    setTimeout(hideNativeTabBar, 80)
    setTimeout(hideNativeTabBar, 320)
    let gd = {}
    try { const _app = getApp({ allowDefault: true }); if (_app) gd = _app.globalData || {} } catch (e) { gd = {} }
    self.host = gd.host || ''
    self.port = gd.port || 9876
    self.connectionMode = Net.getMode()
    self.connected = Net.isConnected()
    var hidStatus = Net.getHidStatus()
    self.hidConnected = !!(hidStatus && hidStatus.connected)
    // 订阅游戏手柄布局(panel 启动时执行一次)
    self._pgSubscribeLayouts()
    // 主动拉一次(即使连上后没收到推送,也能拿到)
    try { WS.getGamepadLayouts() } catch (err) {}
    if (!self.netStateListener) {
      self.netStateListener = function(state) {
        self.connectionMode = Net.getMode()
        self.connected = state === 'connected'
        if (self.connected) {
          self._requestCodexSnapshot(true)
          // 游戏手柄:连接上后请求一次布局
          try { WS.getGamepadLayouts() } catch (err) {}
        }
        else self.codexAvailable = false
      }
      Net.onStateChange(self.netStateListener)
    }
    if (!self.hidStateListener) {
      self.hidStateListener = function(status) {
        self.hidConnected = !!(status && status.connected)
      }
      Net.onHidStateChange(self.hidStateListener)
    }
    try {
      const selection = uni.getStorageSync('phonekb.active_layout_page')
      if (selection && selection.activeLayoutId) {
        self.activeLayoutId = String(selection.activeLayoutId)
        self.activePageId = selection.activePageId ? String(selection.activePageId) : ''
      }
      const cached = uni.getStorageSync('phonekb.last_layouts')
      if (cached) self._apply(cached)
    } catch (e) {}
    if (!self.layoutsListener) {
      self.layoutsListener = function(d) { self._apply(d) }
      Net.onLayouts(self.layoutsListener)
    }
    Net.send({ action: 'reload_layouts' })
    if (!self.codexMessageListener) {
      self.codexMessageListener = function(message) { self.onCodexMessage(message) }
      Net.onMessage(self.codexMessageListener)
    }
    if (self.connected) self._requestCodexSnapshot(true)
    // 第三阶段:从当前 layout 读取 widgets(支持跨页编辑后自动更新)
    self._reloadFromStorage()
    if ((self.widgets || []).some(function(widget) { return widget && widget.visible !== false && widget.type === 'codex-micro' })) {
      requestCodexNotificationPermission()
    }
    // 读取持久化的折叠模式
    // 读取当前激活的 tab id,识别是否进入单 widget 焦点模式
    self._applyActiveTab()
    // 读取系统状态栏高度
    try {
      const sys = uni.getSystemInfoSync()
      self.statusBarHeight = (sys && sys.statusBarHeight) ? sys.statusBarHeight : 20
    } catch (e) { self.statusBarHeight = 20 }
    self._scheduleComponentScrollMeasure()
    self._refreshFocusSnapshot()
  },
  onBackPress() {
    if (this.fullscreenWidgetId) {
      this.closeFullscreenWidget()
      return true
    }
    // The mouse control is a fixed overlay inside the panel page. Consume
    // Android's edge-back gesture here so it closes the overlay instead of
    // navigating away from the panel (or prompting to exit the app).
    const refs = this.$refs && this.$refs.mouseControl
    const targets = Array.isArray(refs) ? refs : (refs ? [refs] : [])
    const target = targets.find(function (item) { return item && item.showTrackpad })
    if (target && target.showTrackpad) {
      target.onCloseTrackpad()
      return true
    }
    return false
  },
  onUnload() {
    this.moreMenuShow = false
    this._exitJianyingLandscape()
    this.fullscreenWidgetId = ''
    this._releaseHeldPanelShortcuts()
      if (this.codexTestTimer) {
        clearTimeout(this.codexTestTimer)
        this.codexTestTimer = null
      }
      if (this.codexApprovalTimer) {
        clearTimeout(this.codexApprovalTimer)
        this.codexApprovalTimer = null
      }
    if (this.codexBindingTimer) {
      clearTimeout(this.codexBindingTimer)
      this.codexBindingTimer = null
    }
    if (this.codexMessageListener) {
      Net.offMessage(this.codexMessageListener)
      this.codexMessageListener = null
    }
    if (this.netStateListener) {
      Net.offStateChange(this.netStateListener)
      this.netStateListener = null
    }
    if (this.hidStateListener) {
      Net.offHidStateChange(this.hidStateListener)
      this.hidStateListener = null
    }
    if (this.layoutsListener) {
      Net.offLayouts(this.layoutsListener)
      this.layoutsListener = null
    }
    // 安全网:防止按住语音键时切换/卸载页面导致 rctrl 卡住。
    // server 端 stop 是幂等的,即使没按下也不会出错。
    try { Net.send({ action: 'codex_zhipu_stop' }) } catch (e) {}
    // 游戏手柄:释放所有按下的键,防止卸载后电脑端一直按下
    this._pgReleaseAll()
    if (this._pgLayoutListener) {
      try { WS.offGamepadLayouts(this._pgLayoutListener) } catch (e) {}
      this._pgLayoutListener = null
    }
  },
  onHide() {
    this._exitJianyingLandscape()
    this.fullscreenWidgetId = ''
    this._releaseHeldPanelShortcuts()
  },

  methods: {
    _releaseHeldPanelShortcuts() {
      const refs = this.$refs && this.$refs.keyGrid
      const targets = Array.isArray(refs) ? refs : (refs ? [refs] : [])
      targets.forEach(function(target) {
        if (target && typeof target.releaseAllShortcuts === 'function') target.releaseAllShortcuts()
      })
    },
    _requestCodexSnapshot(syncStoredDefaults) {
      if (!this.connected) return
      if (syncStoredDefaults) {
        try {
          const saved = uni.getStorageSync('phonekb.codex.reasoning')
          if (['low', 'medium', 'high', 'xhigh'].indexOf(saved) >= 0) {
            this.codexReasoning = saved
            Net.send({ action: 'codex_set_defaults', reasoning_effort: saved })
          }
        } catch (e) {}
      }
      Net.send({ action: 'codex_get_snapshot' })
    },
    _mergeCodexTask(task, notifyTerminal) {
      if (!task || !task.slot) return
      const next = (this.codexTasks || []).slice()
      const index = next.findIndex(function (item) { return Number(item && item.slot) === Number(task.slot) })
      const previous = index >= 0 ? next[index] : null
      let merged = Object.assign({}, previous || {}, task)
      const sameTask = previous && previous.task_id && previous.task_id === task.task_id
      if (sameTask && previous.state === 'running' && task.state === 'starting') {
        merged.state = previous.state
        merged.detail = previous.detail
      }
      if (index >= 0) next.splice(index, 1, merged)
      else next.push(merged)
      this.codexTasks = next

      const terminal = merged.state === 'completed' || merged.state === 'failed' || merged.state === 'cancelled'
      const firstTerminal = !previous || previous.task_id !== merged.task_id || previous.state !== merged.state
      if (notifyTerminal && terminal && firstTerminal && merged.task_id && !this.codexCompletionSeen[merged.task_id]) {
        this.codexCompletionSeen[merged.task_id] = true
        this._notifyCodexTerminal(merged)
      }
    },
    _notifyCodexTerminal(task) {
      const completed = task.state === 'completed'
      const cancelled = task.state === 'cancelled'
      const content = task.name || (completed ? '任务已完成' : (cancelled ? '任务已停止' : '任务执行失败'))
      playCodexTerminalSound(task.state)
      try {
        if (completed) uni.vibrateLong()
        else uni.vibrateShort({ type: 'medium' })
      } catch (e) {}
      try { uni.showToast({ title: content, icon: completed ? 'success' : 'none', duration: 1800 }) } catch (e) {}
      postLocalNotification(buildTaskNotification(task), { silent: true })
    },
    _maybeNotifyCodexApproval(previous, approval) {
      if (!approval || !approval.pending || !approval.fingerprint) return
      if (previous && previous.pending && previous.fingerprint === approval.fingerprint) return
      if (this.codexApprovalSeen[approval.fingerprint]) return
      this.codexApprovalSeen[approval.fingerprint] = true
      const binding = this.codexDesktopBindings[String(approval.slot)] || this.codexDesktopBindings[approval.slot] || null
      const content = binding && binding.title ? binding.title : ('任务槽 ' + approval.slot + ' 等待批准')
      try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
      try { uni.showToast({ title: content, icon: 'none', duration: 1800 }) } catch (e) {}
      postLocalNotification(buildApprovalNotification(approval, binding))
    },
    _maybeNotifyCodexInput(binding) {
      if (!binding || binding.state !== 'waiting_input' || !binding.attention_id) return
      const notificationId = String(binding.thread_id || binding.slot || '') + ':' + String(binding.attention_id)
      if (this.codexInputSeen[notificationId]) return
      this.codexInputSeen[notificationId] = true
      playCodexInputSound()
      try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
      try { uni.showToast({ title: binding.title || 'Codex 等待输入', icon: 'none', duration: 2200 }) } catch (e) {}
      postLocalNotification(buildInputNotification(binding), { silent: true })
    },
    onCodexMessage(message) {
      // Net.onMessage receives replies for every panel widget. Keep Codex
      // dialogs and notifications isolated to the Codex Micro protocol.
      if (!message || typeof message.action !== 'string' || message.action.indexOf('codex_') !== 0) return
      if (message.action === 'codex_snapshot') {
        const previousApproval = this.codexApproval
        this.codexAvailable = !!message.available
        this.codexWorkspace = message.workspace || ''
        this.codexTasks = Array.isArray(message.tasks) ? message.tasks.slice() : []
        this.codexDesktopBindings = message.desktop_bindings && typeof message.desktop_bindings === 'object' ? Object.assign({}, message.desktop_bindings) : {}
        Object.keys(this.codexDesktopBindings).forEach((slot) => this._maybeNotifyCodexInput(this.codexDesktopBindings[slot]))
        this.codexApproval = message.approval && typeof message.approval === 'object'
          ? Object.assign({ pending: false, ambiguous: false, fingerprint: '', slot: 0, thread_id: '', msg: '' }, message.approval)
          : { pending: false, ambiguous: false, fingerprint: '', slot: 0, thread_id: '', msg: '' }
        this._maybeNotifyCodexApproval(previousApproval, this.codexApproval)
        const reasoning = message.defaults && message.defaults.reasoning_effort
        if (['low', 'medium', 'high', 'xhigh'].indexOf(reasoning) >= 0) this.codexReasoning = reasoning
        const pendingBind = String(this.codexBindingRequestId || '').match(/^bind-(\d+)-/)
        if (pendingBind && this.codexDesktopBindings[pendingBind[1]]) this._clearCodexBindingWait()
        return
      }
      if (message.action === 'codex_approval_status') {
        const previousApproval = this.codexApproval
        this.codexApproval = Object.assign(
          { pending: false, ambiguous: false, fingerprint: '', slot: 0, thread_id: '', msg: '' },
          message
        )
        this._maybeNotifyCodexApproval(previousApproval, this.codexApproval)
        const slot = String(message.slot || '')
        if (message.pending && slot && this.codexDesktopBindings[slot]) {
          const next = Object.assign({}, this.codexDesktopBindings)
          next[slot] = Object.assign({}, next[slot], {
            state: 'attention',
            detail: message.msg || 'Codex 正在等待批准终端操作',
            approval: this.codexApproval,
          })
          this.codexDesktopBindings = next
        } else if (!message.pending) {
          this._requestCodexSnapshot(false)
        }
        return
      }
      if (message.action === 'codex_status' || message.action === 'codex_result') {
        this._mergeCodexTask(message.task, true)
        return
      }
      if (message.action === 'codex_binding_status') {
        const slot = String(message.slot || (message.binding && message.binding.slot) || '')
        if (!slot || !message.binding) return
        const previous = this.codexDesktopBindings[slot]
        const next = Object.assign({}, this.codexDesktopBindings)
        next[slot] = message.binding
        this.codexDesktopBindings = next
        const state = message.binding.state || 'idle'
        this._maybeNotifyCodexInput(message.binding)
        if ((state === 'completed' || state === 'failed' || state === 'cancelled') && (!previous || previous.state !== state)) {
          this._notifyCodexTerminal({
            slot: Number(slot),
            task_id: 'desktop-' + (message.binding.thread_id || slot) + '-' + (message.binding.turn_id || message.binding.status_updated_at || Date.now()),
            name: message.binding.title || ('Codex 任务槽 ' + slot),
            state: state,
            detail: message.binding.detail || '',
          })
        }
        return
      }
      if (message.action === 'codex_voice_start_ack') {
        if (message.ok) {
          this.codexVoiceTarget = message.title || '当前窗口'
          if (!message.looks_like_codex) {
            uni.showToast({ title: '当前目标: ' + this.codexVoiceTarget, icon: 'none', duration: 1500 })
          }
        } else {
          uni.showToast({ title: message.msg || '无法锁定 Codex 窗口', icon: 'none' })
        }
        return
      }
      if (message.action === 'codex_dictate_ack') {
        if (!message.ok) uni.showToast({ title: message.msg || '语音文字输入失败', icon: 'none' })
        return
      }
      if (message.action === 'codex_zhipu_start_ack') {
        if (!message.ok) {
          uni.showModal({ title: '智谱语音没有启动', content: message.msg || '无法聚焦 Codex 或按下右 Ctrl', showCancel: false })
        }
        return
      }
      if (message.action === 'codex_zhipu_stop_ack') {
        if (!message.ok) uni.showToast({ title: message.msg || '右 Ctrl 没有正常释放', icon: 'none' })
        return
      }
      if (message.action === 'codex_submit_enter_ack') {
        uni.showToast({
          title: message.ok ? '已发送' : (message.msg || '回车发送失败'),
          icon: message.ok ? 'success' : 'none',
          duration: 1000,
        })
        return
      }
      if (message.action === 'codex_test_input_ack') {
        if (this.codexTestRequestId && message.request_id !== this.codexTestRequestId) return
        if (this.codexTestTimer) clearTimeout(this.codexTestTimer)
        this.codexTestTimer = null
        this.codexTestRequestId = ''
        try { uni.hideLoading() } catch (e) {}
        if (message.ok) {
          uni.showModal({
            title: '测试输入成功',
            content: '4/4 已完成\n电脑已找到 Codex、聚焦输入框并写入固定短语。',
            showCancel: false,
          })
        } else {
          const stages = {
            validate: '电脑收到的内容无效',
            locate_codex: '电脑没有找到或无法聚焦 Codex 输入框',
            inject_text: 'Windows 文字注入失败',
          }
          uni.showModal({
            title: '测试停在电脑端',
            content: (stages[message.stage] || '电脑端执行失败') + '\n\n' + (message.msg || '没有具体原因'),
            showCancel: false,
          })
        }
        return
      }
      if (message.action === 'codex_approve_ack' || message.action === 'codex_reject_ack') {
        if (this.codexApprovalTimer) clearTimeout(this.codexApprovalTimer)
        this.codexApprovalTimer = null
        try { uni.hideLoading() } catch (e) {}
        if (message.approval && typeof message.approval === 'object') {
          this.codexApproval = Object.assign(
            { pending: false, ambiguous: false, fingerprint: '', slot: 0, thread_id: '', msg: '' },
            message.approval
          )
        }
        if (!message.ok) {
          uni.showModal({
            title: message.action === 'codex_approve_ack' ? '没有批准' : '没有拒绝',
            content: message.msg || 'Codex 没有确认这次操作',
            showCancel: false,
          })
        } else {
          uni.showToast({
            title: message.msg || (message.action === 'codex_approve_ack' ? '已允许一次' : '已拒绝'),
            icon: 'success',
            duration: 1400,
          })
        }
        this._requestCodexSnapshot(false)
        return
      }
      if (message.action === 'codex_defaults_ack' && message.ok && message.defaults) {
        this.codexReasoning = message.defaults.reasoning_effort || this.codexReasoning
        return
      }
      if (message.action === 'codex_set_desktop_reasoning_ack') {
        this._clearCodexBindingWait()
        if (!message.ok) {
          uni.showModal({ title: '推理强度没有改变', content: message.msg || 'Codex Desktop 没有确认设置', showCancel: false })
          return
        }
        const next = Object.assign({}, this.codexDesktopBindings)
        next[String(message.slot)] = message.binding
        this.codexDesktopBindings = next
        this.codexReasoning = message.reasoning_effort || this.codexReasoning
        try { uni.setStorageSync('phonekb.codex.reasoning', this.codexReasoning) } catch (e) {}
        const labels = { low: '轻度', medium: '中', high: '高', xhigh: '极高' }
        uni.showToast({ title: '推理强度：' + (labels[this.codexReasoning] || this.codexReasoning), icon: 'success', duration: 1200 })
        return
      }
      if (message.action === 'codex_bind_current_slot_ack') {
        this._clearCodexBindingWait()
        if (!message.ok) {
          uni.showModal({ title: '绑定失败', content: message.msg || '无法识别 Codex 当前任务', showCancel: false })
          return
        }
        const next = Object.assign({}, this.codexDesktopBindings)
        next[String(message.slot)] = message.binding
        this.codexDesktopBindings = next
        uni.showToast({ title: '已绑定任务槽 ' + message.slot, icon: 'success', duration: 1200 })
        return
      }
      if (message.action === 'codex_focus_slot_ack') {
        if (!this._clearCodexBindingWait(message.request_id || '')) return
        if (!message.ok) uni.showModal({ title: '跳转失败', content: message.msg || '无法打开已绑定任务', showCancel: false })
        return
      }
      if (message.action === 'codex_open_new_task_ack') {
        if (!this._clearCodexBindingWait(message.request_id || '')) return
        if (!message.ok) {
          uni.showModal({ title: '新任务没有打开', content: message.msg || '无法打开 Codex 新任务页面', showCancel: false })
          return
        }
        uni.showToast({ title: '已打开 Codex 新任务', icon: 'success', duration: 1200 })
        return
      }
      if (message.action === 'codex_rename_slot_ack') {
        this._clearCodexBindingWait()
        if (!message.ok) {
          uni.showModal({ title: '名称修改失败', content: message.msg || '无法修改任务槽名称', showCancel: false })
          return
        }
        const next = Object.assign({}, this.codexDesktopBindings)
        next[String(message.slot)] = message.binding
        this.codexDesktopBindings = next
        uni.showToast({ title: message.binding.custom_title ? '已使用自定义名称' : '已恢复 Codex 名称', icon: 'success', duration: 1200 })
        return
      }
      if (message.action === 'codex_unbind_slot_ack') {
        this._clearCodexBindingWait()
        if (!message.ok) {
          uni.showModal({ title: '解除绑定失败', content: message.msg || '无法解除任务槽', showCancel: false })
          return
        }
        const next = Object.assign({}, this.codexDesktopBindings)
        delete next[String(message.slot)]
        this.codexDesktopBindings = next
        uni.showToast({ title: '已解除任务槽 ' + message.slot, icon: 'success', duration: 1200 })
        return
      }
      if (/_ack$/.test(message.action)) {
        if (!message.ok) {
          uni.showModal({ title: 'Codex 没有执行', content: message.msg || '电脑端拒绝了这次操作', showCancel: false })
          this._requestCodexSnapshot(false)
        } else if (message.task) {
          this._mergeCodexTask(message.task, false)
        }
        return
      }
      if (message.action === 'codex_error') {
        this._clearCodexBindingWait()
        const rawMessage = message.msg || '未知错误'
        const unsupportedBinding = rawMessage.indexOf('unknown Codex action: codex_bind_current_slot') >= 0
        uni.showModal({
          title: unsupportedBinding ? '电脑端版本不支持绑定' : 'Codex 错误',
          content: unsupportedBinding ? '当前连接的 PhoneKB 电脑端还没有任务槽绑定功能。请在电脑端更新完成后重新连接。' : rawMessage,
          showCancel: false,
        })
      }
    },
    onCodexSubmit(payload) {
      if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      const resume = payload && payload.mode === 'resume'
      const message = {
        action: resume ? 'codex_resume' : 'codex_create',
        slot: payload.slot,
        prompt: payload.prompt,
        reasoning_effort: payload.reasoning_effort,
        workflow_id: payload.workflow_id,
      }
      if (resume) message.session_id = payload.session_id || ''
      const sent = Net.send(message)
      if (!sent) {
        uni.showToast({ title: '发送失败，请检查连接', icon: 'none' })
        return
      }
      this._mergeCodexTask({
        slot: payload.slot,
        task_id: 'pending-' + payload.slot + '-' + Date.now(),
        session_id: resume ? (payload.session_id || '') : '',
        name: String(payload.prompt || '').replace(/\s+/g, ' ').slice(0, 18),
        state: 'starting',
        detail: '正在发送给 Codex',
        result: '',
        reasoning_effort: payload.reasoning_effort,
        workflow_id: payload.workflow_id,
      }, false)
    },
    onCodexBindCurrentTask(payload) {
      const slot = Number(payload && payload.slot)
      if (slot < 1 || slot > 6) return
      const requestId = 'bind-' + slot + '-' + Date.now()
      if (!this.connected || !Net.send({ action: 'codex_bind_current_slot', slot: slot })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('绑定', requestId)
      const self = this
      this.codexBindingReconcileTimer = setTimeout(function() {
        self.codexBindingReconcileTimer = null
        if (self.connected && self.codexBindingRequestId === requestId) self._requestCodexSnapshot(false)
      }, 1200)
    },
    onCodexFocusBoundTask(payload) {
      const slot = Number(payload && payload.slot)
      if (slot < 1 || slot > 6) return
      const requestId = 'focus-' + slot + '-' + Date.now()
      if (!this.connected || !Net.send({ action: 'codex_focus_slot', slot: slot, request_id: requestId })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('跳转', requestId)
    },
    onCodexOpenNewTask() {
      const requestId = 'new-task-' + Date.now()
      if (!this.connected || !Net.send({ action: 'codex_open_new_task', request_id: requestId })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('打开新任务', requestId)
    },
    onCodexRenameBoundTask(payload) {
      const slot = Number(payload && payload.slot)
      if (slot < 1 || slot > 6) return
      if (!this.connected || !Net.send({ action: 'codex_rename_slot', slot: slot, title: String(payload.title || '') })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('修改名称')
    },
    onCodexUnbindBoundTask(payload) {
      const slot = Number(payload && payload.slot)
      if (slot < 1 || slot > 6) return
      if (!this.connected || !Net.send({ action: 'codex_unbind_slot', slot: slot })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('解除绑定')
    },
    _clearCodexBindingWait(requestId) {
      if (requestId && this.codexBindingRequestId && requestId !== this.codexBindingRequestId) return false
      if (this.codexBindingTimer) clearTimeout(this.codexBindingTimer)
      if (this.codexBindingReconcileTimer) clearTimeout(this.codexBindingReconcileTimer)
      this.codexBindingTimer = null
      this.codexBindingReconcileTimer = null
      this.codexBindingRequestId = ''
      try { uni.hideLoading() } catch (e) {}
      return true
    },
    _startCodexBindingWait(label, requestId) {
      this._clearCodexBindingWait()
      this.codexBindingRequestId = requestId || ''
      try { uni.showLoading({ title: '正在' + label, mask: false }) } catch (e) {}
      const self = this
      this.codexBindingTimer = setTimeout(function() {
        self.codexBindingTimer = null
        self.codexBindingRequestId = ''
        try { uni.hideLoading() } catch (e) {}
        uni.showModal({ title: label + '没有回执', content: '请确认电脑端 PhoneKB 已更新并正在运行。', showCancel: false })
      }, 8000)
    },
    onCodexVoiceStart(payload) {
      if (!payload || payload.destination !== 'codex') return
      if (!this.connected || !Net.send({ action: 'codex_voice_start' })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
      }
    },
    onCodexTestInput() {
      if (!this.connected) {
        uni.showModal({ title: '第 1 步失败', content: '手机当前没有连接电脑端 PhoneKB。', showCancel: false })
        return
      }
      if (this.codexTestTimer) clearTimeout(this.codexTestTimer)
      const requestId = 'test-' + Date.now()
      this.codexTestRequestId = requestId
      const sent = Net.send({ action: 'codex_test_input', request_id: requestId })
      if (!sent) {
        this.codexTestRequestId = ''
        uni.showModal({ title: '第 1 步失败', content: '手机没有把测试请求写入连接通道。', showCancel: false })
        return
      }
      uni.showLoading({ title: '正在测试 1/4', mask: false })
      const self = this
      this.codexTestTimer = setTimeout(function() {
        self.codexTestTimer = null
        self.codexTestRequestId = ''
        try { uni.hideLoading() } catch (e) {}
        uni.showModal({
          title: '第 2 步没有回执',
          content: '手机已发出请求，但 6 秒内没有收到电脑回复。最常见原因是电脑仍在运行旧版 PhoneKB.exe。',
          showCancel: false,
        })
      }, 6000)
    },
    onCodexZhipuVoiceStart() {
      if (!this.connected || !Net.send({ action: 'codex_zhipu_start' })) {
        uni.showToast({ title: '没有连接电脑', icon: 'none' })
      }
    },
    onCodexZhipuVoiceEnd() {
      Net.send({ action: 'codex_zhipu_stop' })
    },
    onCodexSubmitEnter() {
      if (!this.connected || !Net.send({ action: 'codex_submit_enter' })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
      }
    },
    onCodexDictate(payload) {
      const text = String(payload && payload.text ? payload.text : '').trim()
      if (!text) return
      const sent = Net.send({ action: 'codex_dictate', text: text, append_space: payload.append_space !== false })
      if (!sent) uni.showToast({ title: '语音文字发送失败', icon: 'none' })
    },
    onCodexSetReasoning(payload) {
      const reasoning = String(payload && payload.reasoning ? payload.reasoning : '')
      const slot = Number(payload && payload.slot)
      if (['low', 'medium', 'high', 'xhigh'].indexOf(reasoning) < 0 || slot < 1 || slot > 6) return
      if (!payload.binding) {
        uni.showToast({ title: '请先长按绑定这个任务槽', icon: 'none' })
        return
      }
      if (!this.connected || !Net.send({ action: 'codex_set_desktop_reasoning', slot: slot, reasoning_effort: reasoning })) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._startCodexBindingWait('设置推理强度')
    },
    onCodexApprove(payload) {
      this._sendCodexApproval('approve', payload)
    },
    onCodexReject(payload) {
      this._sendCodexApproval('reject', payload)
    },
    _sendCodexApproval(decision, payload) {
      const task = payload && payload.task
      const binding = task && task.desktop_binding
      const approval = this.codexApproval || {}
      if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      if (!binding || !approval.pending || Number(approval.slot) !== Number(task.slot)) {
        showTransientToast('当前任务没有待批准请求', 2000)
        return
      }
      const sent = Net.send({
        action: decision === 'approve' ? 'codex_approve' : 'codex_reject',
        slot: Number(task.slot),
        thread_id: String(binding.thread_id || ''),
        fingerprint: String(approval.fingerprint || ''),
      })
      if (!sent) {
        uni.showToast({ title: '审批请求发送失败', icon: 'none' })
        return
      }
      uni.showLoading({ title: decision === 'approve' ? '正在批准' : '正在拒绝', mask: false })
      if (this.codexApprovalTimer) clearTimeout(this.codexApprovalTimer)
      const self = this
      this.codexApprovalTimer = setTimeout(function() {
        self.codexApprovalTimer = null
        try { uni.hideLoading() } catch (e) {}
        uni.showModal({
          title: '审批没有回执',
          content: '手机已发出请求，但电脑端 6 秒内没有返回结果。请确认 PhoneKB 电脑端已经更新并保持连接。',
          showCancel: false,
        })
      }, 6000)
    },
    onCodexCancel(payload) {
      const task = payload && payload.task
      if (!task || !task.task_id) return
      Net.send({ action: 'codex_cancel', task_id: task.task_id, slot: task.slot })
    },
    onCodexRefresh() {
      if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this._requestCodexSnapshot(false)
      uni.showToast({ title: '正在同步 Codex', icon: 'loading', duration: 800 })
    },
    widgetIcon(type) {
      const icons = {
        'key-grid': 'ϟ',
        'text-input': '▦',
        'mouse-control': '◉',
        'volume-control': '♪',
        'codex-micro': '◉',
        'jianying-workbench': '剪',
      }
      return icons[type] || '◇'
    },
    _reloadFromStorage() {
      const layout = getCurrentLayout()
      this.currentLayoutId = layout.id
      this.widgets = (layout.widgets || []).slice()
      this._scheduleComponentScrollMeasure()
    },
    onRemoveWidget(id) {
      if (!id) return
      const self = this
      uni.showModal({
        title: '删除组件',
        content: '确认从面板里移除这个组件?',
        confirmText: '删除',
        confirmColor: '#ef4444',
        success: function (res) {
          if (!res.confirm) return
          const list = loadWidgets().filter(function (w) { return w.id !== id })
          saveWidgets(list)
          self.widgets = list.slice().sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
          uni.showToast({ title: '已删除', icon: 'success', duration: 800 })
        },
      })
    },
    _apply(d) {
      if (!d) return
      const layouts = d.layouts || []
      let lay = null
      if (this.activeLayoutId) lay = layouts.find(l => l.id === this.activeLayoutId) || null
      if (!lay) lay = layouts[0] || null
      let page = null
      if (lay && this.activePageId) page = (lay.pages || []).find(p => p.id === this.activePageId) || null
      if (!page && lay) page = (lay.pages || [])[0] || null
      const rawSlots = page ? (page.slots || []) : []
      const slots = rawSlots.map(function(s) {
        const r = Number(s.r != null ? s.r : s.row) || 0
        const c = Number(s.c != null ? s.c : s.col) || 0
        const rs = Number(s.rowspan) || 1
        const cs = Number(s.colspan != null ? s.colspan : s.span) || 1
        return Object.assign({}, s, { r: r, c: c, rowspan: rs, colspan: cs })
      })
      this.layouts = layouts
      this.activeLayoutId = lay ? lay.id : ''
      this.activeLayoutName = lay ? lay.name : '默认'
      this.pages = lay ? (lay.pages || []) : []
      this.activePageId = page ? page.id : ''
      this.activePageName = page ? page.name : '—'
      this.slots = slots
      this.gridRows = lay && lay.id === 'default' ? 4 : (d.grid_rows || 4)
      this.gridCols = lay && lay.id === 'default' ? 4 : (d.grid_cols || 4)
    },
    onPickLayoutEvent(payload) {
      const self = this
      const layoutId = payload && payload.layoutId
      const pageId = payload && payload.pageId
      if (!layoutId) return
      const lay = (this.layouts || []).find(function(l) { return l.id === layoutId })
      if (!lay) return
      let nextPageId = pageId
      if (!nextPageId) {
        const pages = lay.pages || []
        const pid = pages.length ? pages[0].id : ''
        nextPageId = pid
      }
      const cached = { activeLayoutId: layoutId, activePageId: nextPageId }
      try { uni.setStorageSync('phonekb.active_layout_page', cached) } catch (e) {}
      self.activeLayoutId = layoutId
      self.activePageId = nextPageId
      self._apply({ layouts: self.layouts })
    },
onTpExpandChange(expanded) {
      this.anyTpExpanded = !!expanded
    },
    noop() {},
    _refreshFocusSnapshot() {
      const snap = {
        modeLabel: '倒计时 · 25 分钟',
        durationLabel: '25 min',
        strictChipIcon: '🔓',
        strictChipText: '宽松模式',
        whitelistCount: 0,
        lastHistory: '',
      }
      try {
        const cfg = _loadFocusConfig()
        const meta = _getModeMeta(cfg.mode)
        snap.modeLabel = meta.label + ' · ' + this._fmtFocusDuration(cfg.durationSec)
        snap.durationLabel = this._fmtFocusDurationShort(cfg.durationSec)
        if (cfg.mode === 'strict-lock') {
          snap.strictChipIcon = cfg.strictMode ? '🔒' : '🔓'
          snap.strictChipText = cfg.strictMode ? '严格模式 · 一周 2 次退出' : '宽松模式 · 随时退出'
        } else {
          snap.strictChipIcon = '○'
          snap.strictChipText = '不锁手机'
        }
        snap.whitelistCount = _getWhitelistEntries(cfg).length
        const history = _loadFocusHistory()
        if (history && history.length > 0) {
          const last = history[0]
          snap.lastHistory = this._fmtFocusLast(last)
        }
      } catch (e) {}
      this.focusSnapshot = snap
    },
    _fmtFocusDuration(sec) {
      sec = Math.max(0, Math.round(sec || 0))
      const m = Math.floor(sec / 60)
      const s = sec % 60
      if (m >= 60) {
        const h = Math.floor(m / 60)
        const mm = m % 60
        return h + ' 小时 ' + (mm ? mm + ' 分钟' : '')
      }
      if (s === 0) return m + ' 分钟'
      return m + ' 分 ' + s + ' 秒'
    },
    _fmtFocusDurationShort(sec) {
      sec = Math.max(0, Math.round(sec || 0))
      return Math.floor(sec / 60) + ' min'
    },
    _fmtFocusLast(entry) {
      if (!entry) return ''
      if (entry.outcome === 'completed') return '完成 ' + this._fmtFocusDuration(entry.elapsedSec || 0)
      if (entry.outcome === 'emergency') return '紧急退出 ' + this._fmtFocusDuration(entry.elapsedSec || 0)
      if (entry.outcome === 'cancelled') return '手动取消 ' + this._fmtFocusDuration(entry.elapsedSec || 0)
      return ''
    },
    onGoConnect() {
      uni.navigateTo({ url: '/pages/index/index' })
    },
    // 折叠卡片点击:只有 focus-mode 类型跳到设置页
    onWidgetShellTap(widget) {
      if (!widget) return
      if (widget.type === 'focus-mode') {
        if (this.fullscreenWidgetId) return
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
        uni.navigateTo({ url: '/pages/focus-mode-setup/focus-mode-setup' })
      }
    },
    // 三个点菜单
    onTapMore() {
      this.moreMenuShow = !this.moreMenuShow
    },
    onMoreMenuSelect(key) {
      this.moreMenuShow = false
      if (key === 'edit-layout') {
        uni.navigateTo({ url: '/pages/widgets-edit/widgets-edit' })
      } else if (key === 'switch-layout') {
        uni.navigateTo({ url: '/pages/layouts/layouts' })
      } else if (key === 'manage-layout') {
        uni.navigateTo({ url: '/pages/layouts/layouts?manage=1' })
      } else if (key === 'new-layout') {
        uni.navigateTo({ url: '/pages/layouts/layouts?create=1' })
      }
    },
    onTapAddWidget() {
      uni.navigateTo({ url: '/pages/widgets-manage/widgets-manage' })
    },
    onEditCodexMicro() {
      uni.navigateTo({ url: '/pages/codex-micro-edit/codex-micro-edit' })
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onEditJianying(widget) {
      if (!widget || !widget.id) return
      const scope = this.currentLayoutId + ':' + widget.id
      uni.navigateTo({ url: '/pages/jianying-workbench-edit/jianying-workbench-edit?scope=' + encodeURIComponent(scope) })
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    _scheduleComponentScrollMeasure() {
      const self = this
      this.$nextTick(function () {
        setTimeout(function () { self._updateComponentScrollState() }, 30)
      })
    },
    _updateComponentScrollState() {
      const self = this
      try {
        const query = uni.createSelectorQuery().in(this)
        query.select('.panel-scroll').boundingClientRect()
        query.select('.panel-scroll-content').boundingClientRect()
        query.exec(function (rects) {
          const viewport = rects && rects[0]
          const content = rects && rects[1]
          if (!viewport || !content) return
          self.componentScrollEnabled = content.height > viewport.height + 1
        })
      } catch (e) {
        this.componentScrollEnabled = false
      }
    },
    onToggleWidget(id) {
      const list = this.widgets || []
      const idx = list.findIndex(function (x) { return x && x.id === id })
      if (idx < 0) return
      const nextCollapsed = !list[idx].collapsed
      // 同时更新 this.widgets 与 vue 响应式,确保 body 重新渲染
      try { this.$set(list[idx], 'collapsed', nextCollapsed) } catch (e) {}
      const next = list.slice()
      next[idx] = Object.assign({}, list[idx], { collapsed: nextCollapsed })
      this.widgets = next
      try {
        if (this.currentLayoutId) setLayoutWidgetCollapsed(this.currentLayoutId, id, nextCollapsed)
      } catch (e) {}
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      this._scheduleComponentScrollMeasure()
    },
    onToggleWidgetFullscreen(widget) {
      if (!widget || !widget.id) return
      if (this.fullscreenWidgetId === widget.id) {
        this.closeFullscreenWidget()
        return
      }
      this._exitJianyingLandscape()
      this.fullscreenWidgetId = widget.id
      this.moreMenuShow = false
      this.keyPickerOpen = false
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    closeFullscreenWidget() {
      if (!this.fullscreenWidgetId) return
      this._exitJianyingLandscape()
      this.fullscreenWidgetId = ''
      this.$nextTick(() => this._scheduleComponentScrollMeasure())
    },
    _setSystemFullscreen(enabled) {
      try {
        if (typeof plus !== 'undefined' && plus.navigator && typeof plus.navigator.setFullscreen === 'function') {
          plus.navigator.setFullscreen(!!enabled)
        }
      } catch (e) {}
    },
    _exitJianyingLandscape() {
      if (!this.jianyingLandscape) return
      this.jianyingLandscape = false
      this._setSystemFullscreen(false)
      lockPortrait()
    },
    onToggleJianyingOrientation(widget) {
      if (!widget || widget.type !== 'jianying-workbench' || this.fullscreenWidgetId !== widget.id) return
      this.jianyingLandscape = !this.jianyingLandscape
      if (this.jianyingLandscape) {
        this._setSystemFullscreen(true)
        lockLandscape()
      } else {
        this._setSystemFullscreen(false)
        lockPortrait()
      }
      this.$nextTick(() => this._scheduleComponentScrollMeasure())
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onOpenKeySchemePicker() {
      const refs = this.$refs && this.$refs.keyGrid
      const target = Array.isArray(refs) ? refs[0] : refs
      if (target && typeof target.openPicker === 'function') {
        target.openPicker()
      } else {
        uni.navigateTo({ url: '/pages/layouts/layouts' })
      }
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onKeyPickerVisibleChange(visible) {
      this.keyPickerOpen = !!visible
    },
    onOpenFullscreenTrackpad() {
      const refs = this.$refs && this.$refs.mouseControl
      const target = Array.isArray(refs) ? refs[0] : refs
      if (target && typeof target.onShowTrackpad === 'function') {
        target.onShowTrackpad()
      } else {
        try { uni.$emit('phonekb:showTrackpad') } catch (e) {}
      }
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onOpenFullscreenKeyboard() {
      const refs = this.$refs && this.$refs.fullKeyboard
      const target = Array.isArray(refs) ? refs[0] : refs
      if (target && typeof target.onShow === 'function') target.onShow()
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onKeyboardFullscreenChange(fullscreen) {
      this.keyboardFullscreen = !!fullscreen
      if (this.keyboardFullscreen) this.moreMenuShow = false
    },
    onExitFocus() {
      // 切回面板 tab(p-panel),让 panel 显示全部 widget
      try { uni.setStorageSync('phonekb.activeTabId', 'p-panel') } catch (e) {}
      uni.reLaunch({ url: '/pages/panel/panel' })
    },
    _applyActiveTab() {
      let activeId = ''
      try { activeId = uni.getStorageSync('phonekb.activeTabId') || '' } catch (e) { activeId = '' }
      if (!activeId) {
        this.focusedWidgetType = ''
        this._activeTab = null
        return
      }
      let tabs = []
      try { tabs = uni.getStorageSync('phonekb.tab.config') || [] } catch (e) { tabs = [] }
      const tab = (tabs || []).find(function (t) { return t && t.id === activeId }) || null
      this._activeTab = tab
      this.focusedWidgetType = (tab && tab.widgetType) ? tab.widgetType : ''
    },
    onReloadCustom() {
          Net.send({ action: 'reload_layouts' })
          uni.showToast({ title: '已请求刷新', icon: 'loading', duration: 800 })
        },

        // ===== 内联游戏手柄 (从 PanelGamepad.vue 合并) =====
    pgControlStyle(control) {
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
    pgResolveBinding(control, slot) {
      return (control.bindings || {})[slot] || null
    },
    pgBindingKeys(binding, fallback) {
      if (!binding && fallback) return [String(fallback).toLowerCase()]
      if (!binding) return []
      if (typeof binding === 'string') return this._pgExpandKeyValue(binding.toLowerCase())
      const keys = []
      ;(binding.modifiers || []).forEach(value => {
        const key = String(value || '').trim().toLowerCase()
        if (key && keys.indexOf(key) < 0) keys.push(key)
      })
      const main = String(binding.key || '').trim().toLowerCase()
      if (main && keys.indexOf(main) < 0) keys.push(main)
      return keys
    },
    _pgExpandKeyValue(value) {
      return String(value || '').split(/\s*\+\s*/).map(item => item.trim()).filter(Boolean)
    },
    pgOnStickStart(control, dir) {
      if (!this.connected) return
      const keys = this.pgBindingKeys(this.pgResolveBinding(control, dir), ({up:'w',down:'s',left:'a',right:'d'})[dir])
      const token = control.id + ':' + dir
      keys.forEach(key => this._pgPressKey(key, token))
    },
    pgOnStickEnd(control, dir) {
      if (!this.connected) return
      const keys = this.pgBindingKeys(this.pgResolveBinding(control, dir), ({up:'w',down:'s',left:'a',right:'d'})[dir])
      const token = control.id + ':' + dir
      keys.reverse().forEach(key => this._pgReleaseKey(key, token))
    },
    pgOnKeyStart(control, slot) {
      if (!this.connected) return
      const keys = this.pgBindingKeys(this.pgResolveBinding(control, slot))
      const token = control.id + ':' + slot
      keys.forEach(key => this._pgPressKey(key, token))
    },
    pgOnKeyEnd(control, slot) {
      if (!this.connected) return
      const keys = this.pgBindingKeys(this.pgResolveBinding(control, slot))
      const token = control.id + ':' + slot
      keys.reverse().forEach(key => this._pgReleaseKey(key, token))
    },
    pgOnViewStart(control, e) {
      if (!this.connected) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      this.pgStickActive = {
        controlId: control.id,
        cx: t.clientX || t.pageX || t.x || 0,
        cy: t.clientY || t.pageY || t.y || 0,
        sens: Number(control.sensitivity || 55) / 100,
      }
    },
    pgOnViewMove(control, e) {
      const a = this.pgStickActive
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
      try { WS.gamepadMouseMove(Math.round(dx), Math.round(dy)) } catch (err) {}
      a.cx = x; a.cy = y
    },
    pgOnViewEnd(control) {
      if (this.pgStickActive && this.pgStickActive.controlId === control.id) {
        this.pgStickActive = null
      }
    },
    pgOnMouseStart(control, e) {
      if (!this.connected) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      this.pgMouseActive = { controlId: control.id }
      this.pgMouseLastPoint = { x: t.clientX || t.pageX || t.x || 0, y: t.clientY || t.pageY || t.y || 0 }
    },
    pgOnMouseMove(control, e) {
      if (!this.pgMouseActive || this.pgMouseActive.controlId !== control.id) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      const x = t.clientX || t.pageX || t.x || 0
      const y = t.clientY || t.pageY || t.y || 0
      const sens = Number(control.sensitivity || 55) / 50
      let dx = (x - this.pgMouseLastPoint.x) * sens
      let dy = (y - this.pgMouseLastPoint.y) * sens
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
      dx = Math.max(-150, Math.min(150, dx))
      dy = Math.max(-150, Math.min(150, dy))
      try { WS.gamepadMouseMove(Math.round(dx), Math.round(dy)) } catch (err) {}
      this.pgMouseLastPoint = { x, y }
    },
    pgOnMouseEnd(control) {
      if (this.pgMouseActive && this.pgMouseActive.controlId === control.id) {
        this.pgMouseActive = null
        this.pgMouseLastPoint = null
      }
    },
    _pgPressKey(key, token) {
      if (!this.pgPressedKeys[key]) this.pgPressedKeys[key] = {}
      this.pgPressedKeys[key][token] = true
      if (Object.keys(this.pgPressedKeys[key]).length === 1) {
        try { WS.gamepadKey([key], true) } catch (err) {}
      }
    },
    _pgReleaseKey(key, token) {
      if (!this.pgPressedKeys[key]) return
      delete this.pgPressedKeys[key][token]
      if (Object.keys(this.pgPressedKeys[key]).length === 0) {
        delete this.pgPressedKeys[key]
        try { WS.gamepadKey([key], false) } catch (err) {}
      }
    },
    _pgReleaseAll() {
      const keys = Object.keys(this.pgPressedKeys)
      keys.forEach(k => { try { WS.gamepadKey([k], false) } catch (err) {} })
      this.pgPressedKeys = {}
      this.pgStickActive = null
      this.pgMouseActive = null
      this.pgMouseLastPoint = null
    },
    pgForceRequest() {
      // 手动触发:重新订阅 + 拉一次布局
      try { if (this._pgLayoutListener) WS.offGamepadLayouts(this._pgLayoutListener) } catch (e) {}
      this._pgLayoutListener = null
      this.pgLayouts = null
      this._pgSubscribeLayouts()
      try { WS.getGamepadLayouts() } catch (err) {}
      try { uni.showToast({ title: '已请求电脑布局', icon: 'none' }) } catch (err) {}
    },
    pgOpenFullscreen() {
      // 点击 widget 卡 → 进入横屏全屏游戏手柄页
      // 即使没拿到布局,也会进,游戏手柄页自己会拉取
      try { uni.vibrateShort({ type: 'light' }) } catch (err) {}
      try {
        uni.navigateTo({ url: '/pages/gamepad/gamepad' })
      } catch (err) {
        try { uni.showToast({ title: '打开失败', icon: 'none' }) } catch (e) {}
      }
    },
    _pgSubscribeLayouts() {
      if (this._pgLayoutListener) return
      const self = this
      this._pgLayoutListener = function(data) {
        if (!data || !Array.isArray(data.layouts)) return
        self.pgLayouts = data
      }
      try { WS.onGamepadLayouts(this._pgLayoutListener) } catch (err) {}
      // 读缓存
      try {
        const cached = WS.getCachedGamepadLayouts()
        if (cached && Array.isArray(cached.layouts) && cached.layouts.length) {
          this.pgLayouts = cached
        }
      } catch (err) {}
      // 连上后请求一次
      if (this.connected) { try { WS.getGamepadLayouts() } catch (err) {} }
    },

        // ===== 面板方案 =====

  },
}
</script>


<style>
page {
  background: var(--color-bg);
}

/* ============ 页面级 ============ */
.page {
  min-height: 100vh;
  padding-bottom: 24rpx;
  background: var(--fluent-bg-azure);
  position: relative;
  overflow-x: hidden;
}
.page::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--fluent-bg-aurora);
  pointer-events: none;
  z-index: 0;
}
.page > view { position: relative; z-index: 1; }

/* ============ 自定义顶栏(navigationStyle: custom) ============ */
.device-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28rpx 20rpx;
  background: transparent;
  position: relative;
  z-index: 5;
}
.basic-mode-tip {
  margin: 12rpx 24rpx 0;
  padding: 12rpx 16rpx;
  border: 1rpx solid #D8E5F3;
  border-radius: 12rpx;
  background: #EEF6FF;
  color: #536B86;
  font-size: 20rpx;
  line-height: 1.45;
}
.device-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding: 4rpx 0;
}
.device-info-hover { opacity: 0.7; }
.status-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.status-dot { width: 14rpx; height: 14rpx; border-radius: 50%; flex-shrink: 0; }
.status-dot.on { background: var(--color-success); box-shadow: 0 0 0 4rpx rgba(16,124,16,0.16); }
.status-dot.off { background: var(--color-text-disabled); }
.status-text { font-size: 24rpx; color: var(--color-text-mid); font-weight: 500; }
.device-name { display: flex; align-items: center; gap: 6rpx; }
.device-name-text { font-size: 36rpx; font-weight: 700; color: var(--color-text); letter-spacing: 0.3rpx; line-height: 1.2; }
.status-arrow { font-size: 32rpx; color: var(--color-text-light); line-height: 1; font-weight: 300; }
.more-btn {
  width: 68rpx; height: 68rpx;
  display: flex; align-items: center; justify-content: center;
  border-radius: 20rpx;
  background: var(--fluent-acrylic-strong);
  border: 1rpx solid var(--fluent-hairline);
  box-shadow: var(--shadow-fluent-1);
  backdrop-filter: blur(24rpx);
  -webkit-backdrop-filter: blur(24rpx);
  transition: background-color var(--duration-base) var(--ease-fluent), transform var(--duration-fast) var(--ease-fluent);
  flex-shrink: 0;
}
.more-btn-hover { background: #EAF6FF; transform: scale(0.96); }
.more-btn-dot { font-size: 34rpx; color: #26435E; line-height: 1; letter-spacing: 2rpx; font-weight: 700; }

/* ============ Widget 卡片(亚克力 shell) ============ */
.widget-slot { margin: 0 24rpx 20rpx; }
.widget-shell {
  background: var(--fluent-acrylic-strong);
  backdrop-filter: blur(32rpx) saturate(140%);
  -webkit-backdrop-filter: blur(32rpx) saturate(140%);
  border-radius: 24rpx;
  border: 1rpx solid var(--fluent-hairline);
  padding: 22rpx 24rpx;
  box-shadow: var(--shadow-fluent-2);
  position: relative;
  /* overflow: visible 保证 tap 命中,但 ::before 用绝对定位保持在圆角内 */
}
.widget-shell::before {
  content: '';
  position: absolute;
  top: 0; left: 24rpx; right: 24rpx;
  height: 1rpx;
  background: rgba(255,255,255,0.86);
  pointer-events: none;
}
/* ============ Widget Header(收起 / 展开) ============ */
.widget-head {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 22rpx 24rpx;
  background: rgba(255,255,255,0.45);
  transition: background-color var(--duration-base) var(--ease-fluent);
}
.widget-head-hover { background: rgba(234,246,255,0.65); }
.widget-shell.is-collapsed .widget-head {
  background: rgba(255,255,255,0.55);
}
.widget-head-icon {
  width: 64rpx; height: 64rpx;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-primary-bg);
  border-radius: 18rpx;
  font-size: 36rpx; line-height: 1;
  flex-shrink: 0;
}
.widget-head-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 4rpx;
}
.widget-head-title {
  font-size: 30rpx; font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.3rpx;
}
.widget-head-sub {
  font-size: 22rpx; color: #4C7394;
  font-weight: 400;
  letter-spacing: 0.2rpx;
}
.widget-head-toggle {
  width: 88rpx; height: 88rpx;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-primary-bg);
  border-radius: 50%;
  flex-shrink: 0;
  transition: transform var(--duration-fast) var(--ease-fluent), background-color var(--duration-base) var(--ease-fluent);
}
.widget-shell.is-collapsed .widget-head-toggle {
  background: #F2F5F8;
}
.widget-head-toggle-icon {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;
}
.widget-shell.is-collapsed .widget-head-toggle-icon {
  color: #4C7394;
}
.widget-head-toggle-hover { transform: scale(0.92); background: var(--color-primary) !important; }
.widget-head-toggle-hover .widget-head-toggle-icon { color: #FFFFFF !important; }
/* 鼠标控制 widget 头部「全屏触摸板」按钮 */
.widget-head-fullscreen {
  width: 72rpx; height: 72rpx;
  display: flex; align-items: center; justify-content: center;
  background: #EAF3FB;
  border-radius: 50%;
  flex-shrink: 0;
  margin-right: 8rpx;
  transition: transform var(--duration-fast) var(--ease-fluent), background-color var(--duration-base) var(--ease-fluent);
}
.widget-head-fullscreen-hover { transform: scale(0.92); background: var(--color-primary) !important; }
.widget-head-fullscreen-hover .widget-head-fullscreen-icon { color: #FFFFFF !important; }
.widget-head-fullscreen-icon {
  font-size: 34rpx;
  color: var(--color-primary);
  line-height: 1;
  font-weight: 600;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;
}
/* 收起时,体不再显示 */
.widget-body {
  padding: 6rpx 24rpx 22rpx;
}
/* 子组件内 .section 默认 margin-top:16rpx 与卡片 padding 重复,清零 */
.widget-shell .section:first-child { margin-top: 0; }
/* 子组件 trackpad-launcher 自带 padding,卡内不需要再 padding */
.widget-shell .section-trackpad-launcher { padding: 0; }
/* 子组件内部卡片边距对齐 */
.widget-shell .tp-card,
.widget-shell .vol-display { margin-left: 0; margin-right: 0; }

/* ============ 折叠模式卡片 ============ */
.compact-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 20rpx 24rpx 20rpx 32rpx;
  background: var(--fluent-acrylic-thin);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: var(--radius-fluent-md);
  transition: background-color var(--duration-base) var(--ease-fluent), transform var(--duration-fast) var(--ease-fluent);
  position: relative;
}
.compact-card::before {
  content: '';
  position: absolute;
  left: 0; top: 16rpx; bottom: 16rpx;
  width: 6rpx;
  background: linear-gradient(180deg, var(--color-primary) 0%, rgba(0,120,212,0.4) 100%);
  border-radius: 0 3rpx 3rpx 0;
}
.compact-card-hover {
  background: var(--color-primary-bg);
  transform: scale(0.99);
}
.compact-card-icon {
  font-size: 48rpx;
  line-height: 1;
  width: 64rpx;
  text-align: center;
  flex-shrink: 0;
  margin-left: 4rpx;
}
.compact-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.compact-card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.2rpx;
}
.compact-card-type {
  font-size: 22rpx;
  color: var(--color-text-mid);
  font-family: Consolas, monospace;
}
.compact-card-arrow {
  font-size: 36rpx;
  color: var(--color-text-light);
  line-height: 1;
}

/* ============ 添加组件占位 ============ */
.widget-add {
  margin: 8rpx 24rpx 24rpx;
  height: 88rpx;
  display: flex; align-items: center; justify-content: center;
  gap: 12rpx;
  background: var(--color-card);
  border: 2rpx dashed rgba(0,120,212,0.55);
  border-radius: 16rpx;
  transition: all var(--duration-base) var(--ease-fluent);
}
.widget-add-hover {
  background: var(--color-primary-bg);
  border-style: solid;
  border-color: var(--color-primary);
}
.widget-add-plus { font-size: 32rpx; color: var(--color-primary); line-height: 1; font-weight: 400; }
.widget-add-label { font-size: 28rpx; color: var(--color-primary); font-weight: 600; letter-spacing: 0.3rpx; }

/* ============ 焦点模式返回入口 ============ */
.focus-back {
  margin: 16rpx 24rpx;
  height: 88rpx;
  display: flex; align-items: center; justify-content: center;
  gap: 12rpx;
  background: var(--fluent-mica-deep);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: var(--radius-fluent-md);
  box-shadow: var(--shadow-fluent-2);
  transition: all var(--duration-base) var(--ease-fluent);
}
.focus-back-hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
}
.focus-back-icon { font-size: 44rpx; color: var(--color-primary); line-height: 1; font-weight: 300; }
.focus-back-label { font-size: 28rpx; color: var(--color-primary); font-weight: 600; letter-spacing: 0.3rpx; }

/* ============ Modal(方案选择) ============ */
.modal-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.40);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
  padding: 48rpx;
}
.modal {
  width: 100%;
  max-height: 80vh;
  background: var(--fluent-acrylic-strong);
  backdrop-filter: blur(60rpx) saturate(180%);
  -webkit-backdrop-filter: blur(60rpx) saturate(180%);
  border-radius: var(--radius-fluent-lg);
  border: 1rpx solid var(--fluent-hairline);
  box-shadow: var(--shadow-fluent-flyout);
  display: flex; flex-direction: column;
  overflow: hidden;
  position: relative;
}
.modal::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 1rpx;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.8) 50%, transparent 100%);
  pointer-events: none;
}
.modal-head { padding: 28rpx 28rpx 20rpx; border-bottom: 1rpx solid var(--fluent-hairline); }
.modal-title { font-size: 32rpx; font-weight: 600; color: var(--color-text); letter-spacing: 0.3rpx; }
.modal-body { padding: 12rpx 0; flex: 1; min-height: 200rpx; }
.modal-foot { padding: 16rpx 28rpx 24rpx; display: flex; justify-content: flex-end; }

.empty-hint {
  padding: 32rpx;
  text-align: center;
  color: var(--color-text-mid);
  font-size: 26rpx;
  background: rgba(254, 243, 201, 0.5);
  border-radius: var(--radius-fluent-sm);
}
.empty-hint-icon {
  display: block;
  font-size: 48rpx;
  color: #f59e0b;
  margin-bottom: 8rpx;
}
.empty-hint-title {
  display: block;
  font-size: 28rpx;
  color: #f1f5f9;
  font-weight: 500;
  margin-bottom: 6rpx;
}
.empty-hint-sub {
  display: block;
  font-size: 22rpx;
  color: #94a3b8;
  margin-bottom: 16rpx;
}
.empty-hint-action {
  display: inline-block;
  padding: 12rpx 32rpx;
  background: rgba(56, 189, 248, 0.15);
  border: 1rpx solid rgba(56, 189, 248, 0.3);
  border-radius: 12rpx;
  color: #38bdf8;
  font-size: 24rpx;
}
.empty-hint-action-hover {
  background: rgba(56, 189, 248, 0.3);
}

</style>

<style>
/* 参考图版面：仅约束面板页，避免影响其他页面。 */

/* === 自定义手柄卡片头部(按你截图风格) === */
.pg-card-header {
  display: flex; align-items: center; gap: 12rpx;
  padding: 16rpx 20rpx;
  background: linear-gradient(180deg, #1a2236 0%, #0f1320 100%);
  border-bottom: 1rpx solid rgba(56,189,248,0.12);
}
.pg-card-mark {
  width: 14rpx; height: 14rpx; border-radius: 50%;
  background: #475569;
  display: flex; align-items: center; justify-content: center;
}
.pg-card-mark-dot {
  width: 6rpx; height: 6rpx; border-radius: 50%;
  background: transparent;
}
.pg-card-mark.is-on .pg-card-mark-dot { background: #34d399; box-shadow: 0 0 8rpx #34d399; }
.pg-card-mark.is-warning .pg-card-mark-dot { background: #f59e0b; }
.pg-card-mark.is-offline .pg-card-mark-dot { background: #ef4444; }
.pg-card-title {
  flex: 1;
  font-size: 26rpx;
  color: #f1f5f9;
  font-weight: 500;
  letter-spacing: 0.5rpx;
}
.pg-card-sub {
  font-size: 20rpx;
  color: #64748b;
}

/* === 内联游戏手柄样式 (从 PanelGamepad.vue 合并) === */
.inline-gamepad-widget {
  /* 关键:widget-shell 内部有 padding / blur / overflow 约束,
     嵌套一层强制给 gamepad 一个最小可视高度,让 pg-stage 不会被压扁 */
  display: block;
  width: 100%;
  min-height: 640rpx;
  position: relative;
  /* 隔离层叠上下文,避免父级 backdrop-filter 影响子元素绝对定位 */
  isolation: isolate;
  z-index: 1;
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
}
.inline-gamepad-widget.is-disabled { opacity: 0.55; }
.inline-gamepad-widget.has-layout { cursor: pointer; }
/* 按下时整张卡变亮 6% */
.inline-gamepad-widget.is-pressed,
.inline-gamepad-widget-hover {
  filter: brightness(1.06);
  transform: scale(0.995);
  transition: transform 80ms ease;
}
/* 底部提示文字 */
.pg-card-foot {
  padding: 12rpx 20rpx;
  background: linear-gradient(180deg, transparent 0%, rgba(56,189,248,0.06) 100%);
  border-top: 1rpx solid rgba(56,189,248,0.12);
  text-align: center;
}
.pg-card-foot-text {
  font-size: 22rpx;
  color: #38bdf8;
  letter-spacing: 0.5rpx;
}
.inline-gamepad {
  width: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #131720 0%, #1a1f2c 100%);
  border-radius: 16rpx;
  overflow: hidden;
  color: #f1f5f9;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
  /* widget 卡片内需要最小高度，后续 20:9 预览规则会覆盖这里。 */
  min-height: 600rpx;
}
.inline-gamepad.is-disabled { opacity: 0.55; }
.pg-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12rpx 20rpx; font-size: 22rpx; color: #94a3b8;
  border-bottom: 1rpx solid rgba(255,255,255,0.04);
}
.pg-status { display: flex; align-items: center; gap: 8rpx; }
.pg-status-dot { width: 12rpx; height: 12rpx; border-radius: 50%; background: #475569; }
.pg-status.is-on .pg-status-dot { background: #34d399; box-shadow: 0 0 12rpx #34d399; }
.pg-status.is-warning .pg-status-dot { background: #f59e0b; }
.pg-status.is-offline .pg-status-dot { background: #ef4444; }
.pg-status-text { font-size: 22rpx; }
.pg-layout-name { font-size: 22rpx; color: #cbd5e1; }
.pg-layout-name.pg-empty { color: #64748b; }
.pg-stage {
  position: relative; width: 100%;
  /* widget 卡片里:用固定最小高度,确保控件有足够摆放空间 */
  min-height: 560rpx;
  aspect-ratio: 16 / 9;
  background: radial-gradient(ellipse at center, #1e2536 0%, #0f1320 100%);
  overflow: hidden;
}
.pg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.025) 1rpx, transparent 1rpx),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1rpx, transparent 1rpx);
  background-size: 8.33% 11.11%;
}
.pg-control {
  position: absolute;
  /* widget 卡片里:控件基于 stage 宽度算,且至少 100rpx */
  width: 18%;
  min-width: 100rpx;
  aspect-ratio: 1 / 1;
  pointer-events: auto;
  display: flex; align-items: center; justify-content: center; flex-direction: column;
}
.pg-stick-zone { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; }
.pg-stick-ring {
  position: relative; width: 80%; aspect-ratio: 1 / 1; border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #2a3142 0%, #1a1f2c 70%);
  box-shadow: inset 0 0 16rpx rgba(0,0,0,0.5), 0 0 0 2rpx rgba(148,163,184,0.2);
}
.pg-view-ring { background: radial-gradient(circle at 50% 50%, #1a2236 0%, #0f1320 80%); }
.pg-view-reticle {
  position: absolute; left: 50%; top: 50%;
  width: 16rpx; height: 16rpx; border-radius: 50%; background: #38bdf8;
  transform: translate(-50%, -50%); box-shadow: 0 0 12rpx #38bdf8; pointer-events: none;
}
.pg-stick-up, .pg-stick-right, .pg-stick-down, .pg-stick-left { position: absolute; background: transparent; z-index: 2; }
.pg-stick-up { left: 25%; top: 0; width: 50%; height: 35%; }
.pg-stick-right { right: 0; top: 25%; width: 35%; height: 50%; }
.pg-stick-down { left: 25%; bottom: 0; width: 50%; height: 35%; }
.pg-stick-left { left: 0; top: 25%; width: 35%; height: 50%; }
.pg-stick-center {
  position: absolute; left: 50%; top: 50%; width: 28%; height: 28%;
  border-radius: 50%; background: radial-gradient(circle, #475569 0%, #1e293b 100%);
  transform: translate(-50%, -50%); pointer-events: none; z-index: 1;
}
.pg-dpad-zone { position: relative; width: 100%; height: 100%; }
.pg-dpad-up, .pg-dpad-down, .pg-dpad-left, .pg-dpad-right {
  position: absolute; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, #2a3142, #1a1f2c); color: #cbd5e1; font-size: 28rpx; z-index: 2;
}
.pg-dpad-up { left: 30%; top: 0; width: 40%; height: 32%; border-radius: 12rpx 12rpx 0 0; }
.pg-dpad-down { left: 30%; bottom: 0; width: 40%; height: 32%; border-radius: 0 0 12rpx 12rpx; }
.pg-dpad-left { left: 0; top: 30%; width: 32%; height: 40%; border-radius: 12rpx 0 0 12rpx; }
.pg-dpad-right { right: 0; top: 30%; width: 32%; height: 40%; border-radius: 0 12rpx 12rpx 0; }
.pg-dpad-center { position: absolute; left: 32%; top: 32%; width: 36%; height: 36%; background: #131720; z-index: 1; }
.pg-dpad-up:active, .pg-dpad-down:active, .pg-dpad-left:active, .pg-dpad-right:active {
  background: linear-gradient(145deg, #38bdf8, #0ea5e9); color: #fff;
}
.pg-abxy-zone { position: relative; width: 100%; height: 100%; }
.pg-abxy-y, .pg-abxy-x, .pg-abxy-a, .pg-abxy-b {
  position: absolute; display: flex; align-items: center; justify-content: center;
  width: 38%; height: 38%; border-radius: 50%;
  background: linear-gradient(145deg, #2a3142, #1a1f2c);
  color: #f1f5f9; font-size: 30rpx; font-weight: 600; z-index: 2;
  box-shadow: inset 0 -4rpx 8rpx rgba(0,0,0,0.3);
}
.pg-abxy-y { left: 31%; top: 0; color: #facc15; }
.pg-abxy-x { left: 0; top: 31%; color: #60a5fa; }
.pg-abxy-a { left: 62%; top: 31%; color: #34d399; }
.pg-abxy-b { left: 31%; top: 62%; color: #f87171; }
.pg-abxy-y:active { background: #facc15; color: #131720; }
.pg-abxy-x:active { background: #60a5fa; color: #131720; }
.pg-abxy-a:active { background: #34d399; color: #131720; }
.pg-abxy-b:active { background: #f87171; color: #131720; }
.pg-mouse-zone { position: relative; width: 100%; height: 100%; }
.pg-mouse-track {
  position: relative; width: 100%; height: 100%; border-radius: 16rpx;
  background: linear-gradient(145deg, #1a1f2c, #131720);
  box-shadow: inset 0 0 12rpx rgba(0,0,0,0.5);
  overflow: hidden; z-index: 2;
}
.pg-mouse-crosshair {
  position: absolute; left: 50%; top: 50%;
  width: 16rpx; height: 16rpx; border-radius: 50%; background: #38bdf8;
  transform: translate(-50%, -50%); box-shadow: 0 0 8rpx #38bdf8; pointer-events: none;
}
.pg-button-control { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.pg-single-button {
  display: flex; align-items: center; justify-content: center; padding: 0 16rpx;
  background: linear-gradient(145deg, var(--pg-custom-fill, #2a3142), var(--pg-custom-fill, #1a1f2c));
  color: var(--pg-custom-text, #cbd5e1); font-size: 22rpx; font-weight: 500;
  border: 2rpx solid var(--pg-custom-border, rgba(148,163,184,0.15));
  box-shadow: inset 0 -4rpx 8rpx rgba(0,0,0,0.3);
  min-width: 80rpx; min-height: 80rpx;
}
.pg-single-wide { border-radius: 12rpx; min-width: 100rpx; min-height: 50rpx; }
.pg-single-round { border-radius: 50%; }
.pg-shape-pill { border-radius: 999rpx; }
.pg-shape-square { border-radius: 6rpx; }
.pg-shape-diamond { border-radius: 8rpx; transform: rotate(45deg); }
.pg-shape-diamond .pg-button-label { display: inline-block; transform: rotate(-45deg); }
.pg-shoulder .pg-single-button { min-width: 120rpx; min-height: 40rpx; font-size: 20rpx; }
.pg-single-button:active { background: linear-gradient(145deg, #38bdf8, #0ea5e9); color: #fff; }
.pg-empty-state { padding: 60rpx 24rpx; text-align: center; }
.pg-empty-text { font-size: 24rpx; color: #64748b; }

/* 手柄卡片只做 20:9 预览，横屏页负责完整操作。 */
.inline-gamepad-widget { min-height: 0; }
.inline-gamepad { min-height: 0; }
.inline-gamepad-widget .pg-card-header { padding: 12rpx 16rpx; }
.inline-gamepad-widget .pg-card-title { font-size: 24rpx; }
.inline-gamepad-widget .pg-card-sub { font-size: 18rpx; }
.inline-gamepad .pg-card-foot { padding: 9rpx 16rpx; }
.inline-gamepad .pg-card-foot-text { font-size: 20rpx; }
.inline-gamepad .pg-topbar { padding: 9rpx 16rpx; font-size: 20rpx; }
.inline-gamepad .pg-status-text,
.inline-gamepad .pg-layout-name { font-size: 20rpx; }
.inline-gamepad .pg-stage { min-height: 0; aspect-ratio: 20 / 9; }
.inline-gamepad .pg-control { width: 0; min-width: 0; height: 0; aspect-ratio: auto; }
.inline-gamepad .pg-control-leftStick,
.inline-gamepad .pg-control-rightStick,
.inline-gamepad .pg-control-abxy { width: 13%; height: 29%; }
.inline-gamepad .pg-control-dpad { width: 9%; height: 20%; }
.inline-gamepad .pg-control-mouse { width: 12.5%; height: 18%; }
.inline-gamepad .pg-control-key { width: 5%; height: 11%; }
.inline-gamepad .pg-control-shoulder,
.inline-gamepad .pg-control-wide { width: 10%; height: 9%; }
.inline-gamepad .pg-control-macro { width: 10%; height: 11%; }
.inline-gamepad .pg-single-button {
  width: 100%; height: 100%; min-width: 0; min-height: 0;
  box-sizing: border-box; padding: 0 5rpx;
}
.inline-gamepad .pg-single-wide,
.inline-gamepad .pg-shoulder .pg-single-button { min-width: 0; min-height: 0; }
.inline-gamepad .pg-key-object {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 9.8%;
  aspect-ratio: 1 / 1;
  pointer-events: none;
}
.inline-gamepad .pg-key-token {
  min-width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6rpx;
  border: 1rpx solid rgba(113,181,255,0.9);
  border-radius: 50%;
  color: #f0f9ff;
  background: rgba(18,78,171,0.88);
  font-size: 16rpx;
  font-weight: 800;
  white-space: nowrap;
}
.inline-gamepad .pg-key-token-wide {
  min-width: 160%;
  border-radius: 6rpx;
  font-size: 14rpx;
}
.panel-page {
  --panel-bg: #F6F9FD;
  --panel-card: rgba(255,255,255,0.96);
  --panel-surface: #F8FAFD;
  --panel-surface-strong: #F2F6FB;
  --panel-border: #E2E8F0;
  --panel-border-soft: rgba(103,130,158,0.14);
  --panel-text: #172033;
  --panel-text-mid: #637083;
  --panel-text-light: #99A4B4;
  --panel-accent: var(--color-primary);
  min-height: 100vh;
  padding-bottom: calc(132rpx + env(safe-area-inset-bottom));
  background: radial-gradient(85% 48% at 8% 0%, rgba(77,151,226,0.12) 0%, rgba(246,249,253,0) 72%), var(--panel-bg);
}
.panel-page::before {
  background: radial-gradient(56% 32% at 88% 10%, rgba(118,169,223,0.07) 0%, transparent 72%);
}

.panel-page .device-bar, .custom-app-preview .device-bar {
  padding-left: 32rpx;
  padding-right: 32rpx;
  padding-bottom: 18rpx;
}
.panel-page .device-info, .custom-app-preview .device-info { gap: 2rpx; padding: 2rpx 0; }
.panel-page .status-row, .custom-app-preview .status-row { gap: 10rpx; }
.panel-page .status-dot, .custom-app-preview .status-dot { width: 14rpx; height: 14rpx; }
.panel-page .status-dot.on, .custom-app-preview .status-dot.on {
  background: #22B85A;
  box-shadow: 0 0 0 4rpx rgba(34, 184, 90, 0.18);
}
.panel-page .status-dot.off, .custom-app-preview .status-dot.off {
  background: #E34C4C;
  box-shadow: 0 0 0 4rpx rgba(227, 76, 76, 0.16);
}
.panel-page .status-text, .custom-app-preview .status-text {
  color: #3D4857;
  font-size: 22rpx;
  font-weight: 600;
}
.panel-page .device-name, .custom-app-preview .device-name { gap: 8rpx; }
.panel-page .device-name-text, .custom-app-preview .device-name-text {
  color: var(--panel-text);
  font-size: 32rpx;
  font-weight: 650;
  letter-spacing: -0.2rpx;
}
.panel-page .status-arrow, .custom-app-preview .status-arrow {
  color: #A3ADBA;
  font-size: 28rpx;
}
.panel-page .more-btn, .custom-app-preview .more-btn {
  width: 64rpx;
  height: 64rpx;
  border-radius: 20rpx;
  background: rgba(255,255,255,0.94);
  border: 1rpx solid rgba(112,139,167,0.13);
  box-shadow: 0 8rpx 24rpx rgba(46,79,116,0.10), 0 1rpx 2rpx rgba(46,79,116,0.08);
  backdrop-filter: blur(18rpx);
  -webkit-backdrop-filter: blur(18rpx);
}
.panel-page .more-btn-hover, .custom-app-preview .more-btn-hover { background: #EEF6FF; transform: scale(0.96); }
.panel-page .more-btn-dot, .custom-app-preview .more-btn-dot {
  color: #1E2A3B;
  font-size: 30rpx;
  letter-spacing: 1rpx;
}

.panel-page .widget-slot, .custom-app-preview .widget-slot { margin: 0 24rpx 16rpx; }
.panel-page .widget-slot.is-picker-open, .custom-app-preview .widget-slot.is-picker-open {
  position: relative;
  z-index: 240;
}
.panel-page .widget-shell, .custom-app-preview .widget-shell {
  padding: 0;
  overflow: hidden;
  background: var(--panel-card);
  border: 1rpx solid rgba(121,146,173,0.12);
  border-radius: 22rpx;
  box-shadow: 0 8rpx 24rpx rgba(48,79,114,0.06), 0 2rpx 6rpx rgba(48,79,114,0.04);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
.panel-page .panel-scroll, .custom-app-preview .panel-scroll { width: 100%; min-height: 0; }
.panel-page .panel-scroll, .custom-app-preview .panel-scroll { height: calc(100vh - 112rpx - env(safe-area-inset-bottom)); }
.panel-page .panel-scroll-content, .custom-app-preview .panel-scroll-content { min-height: 100%; }
.panel-page .panel-scroll-bottom, .custom-app-preview .panel-scroll-bottom { height: 32rpx; }
.panel-page .widget-slot.is-picker-open .widget-shell, .custom-app-preview .widget-slot.is-picker-open .widget-shell { overflow: visible; }
.panel-page .widget-shell::before, .custom-app-preview .widget-shell::before { display: none; }
.panel-page .widget-head, .custom-app-preview .widget-head {
  min-height: 76rpx;
  padding: 18rpx 24rpx 14rpx;
  gap: 12rpx;
  background: transparent;
}
.panel-page .widget-shell.is-collapsed .widget-head, .custom-app-preview .widget-shell.is-collapsed .widget-head {
  padding-bottom: 18rpx;
  background: transparent;
}
.panel-page .widget-head-icon, .custom-app-preview .widget-head-icon {
  width: 34rpx;
  height: 34rpx;
  border-radius: 0;
  background: transparent;
}
.panel-page .widget-head-icon-text, .custom-app-preview .widget-head-icon-text {
  color: var(--panel-accent);
  font-size: 29rpx;
  font-weight: 700;
  line-height: 1;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;
}
.panel-page .widget-head-title, .custom-app-preview .widget-head-title {
  flex: 1;
  min-width: 0;
  color: var(--panel-text);
  font-size: 28rpx;
  font-weight: 650;
  line-height: 1.2;
  letter-spacing: 0;
}
.panel-page .widget-head-actions, .custom-app-preview .widget-head-actions {
  display: flex;
  align-items: center;
  gap: 4rpx;
  flex-shrink: 0;
}
.panel-page .widget-head-action, .custom-app-preview .widget-head-action,
.panel-page .widget-head-toggle, .custom-app-preview .widget-head-toggle,
.panel-page .widget-head-fullscreen, .custom-app-preview .widget-head-fullscreen {
  width: 56rpx;
  height: 56rpx;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 14rpx;
  background: rgba(255,255,255,0.55);
  border: 1rpx solid rgba(125,149,174,0.14);
  box-shadow: 0 2rpx 6rpx rgba(48,79,114,0.04);
  transition: background-color 140ms var(--ease-fluent), transform 90ms var(--ease-fluent), border-color 140ms var(--ease-fluent);
}
.panel-page .widget-head-action-hover, .custom-app-preview .widget-head-action-hover {
  background: var(--color-primary) !important;
  border-color: var(--color-primary) !important;
  transform: scale(0.94);
}
.panel-page .widget-head-action-hover, .custom-app-preview .widget-head-action-hover .widget-head-toggle-icon,
.panel-page .widget-head-action-hover, .custom-app-preview .widget-head-action-hover .widget-head-fullscreen-icon,
.panel-page .widget-head-action-hover, .custom-app-preview .widget-head-action-hover .widget-head-switch-icon,
.panel-page .widget-head-action-hover, .custom-app-preview .widget-head-action-hover .widget-head-edit-icon { color: #FFFFFF; }
.panel-page .widget-head-switch, .custom-app-preview .widget-head-switch { background: rgba(255,255,255,0.55); border: 1rpx solid rgba(125,149,174,0.14); }
.panel-page .widget-head-switch-icon, .custom-app-preview .widget-head-switch-icon {
  color: #1E2B3C;
  font-size: 28rpx;
  font-weight: 600;
  line-height: 1;
}
.panel-page .widget-head-edit-icon, .custom-app-preview .widget-head-edit-icon {
  color: #1E2B3C;
  font-size: 29rpx;
  font-weight: 650;
  line-height: 1;
}
.panel-page .widget-head-orientation-icon {
  color: #1E2B3C;
  font-size: 31rpx;
  font-weight: 650;
  line-height: 1;
}
.panel-page .widget-head-switch-label, .custom-app-preview .widget-head-switch-label { display: none; }
.panel-page .widget-head-toggle-icon, .custom-app-preview .widget-head-toggle-icon,
.panel-page .widget-head-fullscreen-icon, .custom-app-preview .widget-head-fullscreen-icon {
  color: #1E2B3C;
  font-size: 30rpx;
  font-weight: 600;
  line-height: 1;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;
}
.panel-page .widget-head-fullscreen-icon, .custom-app-preview .widget-head-fullscreen-icon { color: #1E2B3C; font-size: 28rpx; }
.panel-page .widget-shell.is-collapsed .widget-head-toggle, .custom-app-preview .widget-shell.is-collapsed .widget-head-toggle { background: rgba(255,255,255,0.55); border-color: rgba(125,149,174,0.18); }
.panel-page .widget-shell.is-collapsed .widget-head-toggle-icon, .custom-app-preview .widget-shell.is-collapsed .widget-head-toggle-icon { color: #1E2B3C; }
.panel-page .widget-body, .custom-app-preview .widget-body { padding: 4rpx 24rpx 22rpx; }

/* The active slot becomes an isolated modal layer. The component instance stays
   mounted, so inputs and widget-local state survive opening and closing. */
.panel-page.has-fullscreen-widget .panel-scroll {
  height: 100vh;
  overflow: visible;
}
.panel-page .widget-slot.is-widget-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1400;
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: calc(28rpx + env(safe-area-inset-top)) calc(28rpx + env(safe-area-inset-right)) calc(28rpx + env(safe-area-inset-bottom)) calc(28rpx + env(safe-area-inset-left));
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: hidden;
  background: rgba(226, 235, 244, 0.62);
  backdrop-filter: blur(48px) saturate(45%) brightness(0.92);
  -webkit-backdrop-filter: blur(48px) saturate(45%) brightness(0.92);
  animation: widget-modal-mask-in 160ms ease-out both;
}
.panel-page .widget-slot.is-widget-fullscreen .widget-shell {
  width: calc(100vw - 56rpx - env(safe-area-inset-left) - env(safe-area-inset-right));
  max-width: 920rpx;
  height: auto;
  max-height: calc(100vh - 56rpx - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  border: 1rpx solid rgba(255,255,255,0.76);
  border-radius: 24rpx;
  box-shadow: 0 32rpx 88rpx rgba(24,43,65,0.28), 0 4rpx 18rpx rgba(24,43,65,0.16);
  box-sizing: border-box;
  overflow: hidden;
  background: var(--panel-card);
  animation: widget-modal-panel-in 180ms ease-out both;
}
.panel-page .widget-slot.is-widget-fullscreen .widget-head {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  padding-top: 18rpx;
  padding-right: 24rpx;
  padding-bottom: 18rpx;
  padding-left: 24rpx;
  border-bottom: 1rpx solid rgba(121,146,173,0.14);
  background: var(--panel-card);
}
.panel-page .widget-slot.is-widget-fullscreen .widget-body {
  flex: 0 1 auto;
  min-height: 0;
  max-height: calc(82vh - 96rpx);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 20rpx 24rpx 24rpx;
  box-sizing: border-box;
}
.panel-page .widget-slot.is-widget-fullscreen .widget-head-fullscreen-icon {
  font-size: 40rpx;
  font-weight: 400;
}
@keyframes widget-modal-mask-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes widget-modal-panel-in {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}
@media (orientation: landscape) {
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell {
    width: 72vw;
    max-width: 1040rpx;
    height: auto;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench {
    width: calc(100vw - 56rpx - env(safe-area-inset-left) - env(safe-area-inset-right));
    max-width: none;
    height: calc(100vh - 56rpx - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .widget-body {
    flex: 1;
    max-height: none;
    overflow: hidden;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .jy-console {
    height: 100%;
    display: grid;
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.2fr);
    gap: 18rpx;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .jy-shortcut-grid {
    height: 100%;
    grid-template-rows: repeat(2, minmax(0, 1fr));
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .jy-key {
    min-height: 0;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .jy-timeline-pad {
    height: 100%;
    min-height: 0;
    margin-top: 0;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench .jy-gesture-hints {
    height: calc(100% - 108rpx);
  }

  /* The orientation toggle is authoritative. Android may keep the old CSS
     orientation for a moment while the window lock is changing. */
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) {
    width: calc(100vw - 56rpx - env(safe-area-inset-left) - env(safe-area-inset-right));
    max-width: 920rpx;
    height: auto;
    max-height: calc(82vh - 96rpx);
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .widget-body {
    flex: 0 1 auto;
    max-height: calc(82vh - 96rpx);
    overflow-y: auto;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .jy-console {
    height: auto;
    display: block;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .jy-shortcut-grid {
    height: auto;
    grid-template-rows: repeat(2, 142rpx);
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .jy-key {
    min-height: 142rpx;
  }
  .panel-page .widget-slot.is-widget-fullscreen .widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .jy-timeline-pad {
    height: 292rpx;
    min-height: 292rpx;
    margin-top: 14rpx;
  }
}

.panel-page .section, .custom-app-preview .section { margin-top: 0; }
.panel-page .section-head, .custom-app-preview .section-head { display: none; }
.panel-page .section-trackpad-launcher, .custom-app-preview .section-trackpad-launcher { padding: 0; }

.panel-page .key-grid, .custom-app-preview .key-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-auto-rows: 120rpx;
  gap: 28rpx;
}
.panel-page .key-btn, .custom-app-preview .key-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-width: 0;
  min-height: 120rpx;
  padding: 16rpx 10rpx;
  aspect-ratio: auto;
  background: #FFFFFF;
  border: 1rpx solid #DCE4EE;
  border-radius: 12rpx;
  box-shadow: 0 2rpx 6rpx rgba(48,79,114,0.04);
}
.panel-page .key-btn-hover, .custom-app-preview .key-btn-hover {
  background: #EEF6FF;
  border-color: rgba(0,120,212,0.34);
  box-shadow: 0 5rpx 12rpx rgba(0,120,212,0.11);
  transform: scale(0.97);
}
.panel-page .key-label, .custom-app-preview .key-label {
  margin-top: 0;
  color: #1E2B3C;
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: 0;
}
.panel-page .key-sub, .custom-app-preview .key-sub {
  margin-top: 10rpx;
  color: #8A98AA;
  font-size: 14rpx;
  line-height: 1.1;
  letter-spacing: 0;
  font-family: "Segoe UI", system-ui, sans-serif;
}

.panel-page .text-input, .custom-app-preview .text-input {
  width: 100%;
  height: 80rpx;
  min-height: 80rpx;
  padding: 18rpx 22rpx;
  background: #FFFFFF;
  border: 1rpx solid #DDE4ED;
  border-radius: 14rpx;
  color: var(--panel-text);
  font-size: 25rpx;
  line-height: 1.4;
}
.panel-page .text-input-ph, .custom-app-preview .text-input-ph { color: #ADB6C2; font-size: 22rpx; }
.panel-page .text-actions, .custom-app-preview .text-actions {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 16rpx;
}
.panel-page .btn-secondary, .custom-app-preview .btn-secondary,
.panel-page .btn-primary, .custom-app-preview .btn-primary {
  flex: 0 0 auto;
  height: 60rpx;
  padding: 0 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1;
}
.panel-page .btn-secondary, .custom-app-preview .btn-secondary {
  min-width: 124rpx;
  margin-right: 0;
  color: #5B6776;
  background: #FFFFFF;
  border: 1rpx solid #DDE4ED;
}
.panel-page .btn-primary, .custom-app-preview .btn-primary {
  min-width: 124rpx;
  margin-left: 0;
  color: #FFFFFF;
  background: var(--panel-accent);
  border: 1rpx solid var(--panel-accent);
  box-shadow: 0 6rpx 14rpx rgba(0,120,212,0.20);
}
.panel-page .btn-primary, .custom-app-preview .btn-primary[disabled],
.panel-page .btn-secondary, .custom-app-preview .btn-secondary[disabled],
.panel-page .btn-primary, .custom-app-preview .btn-primary.is-disabled,
.panel-page .btn-secondary, .custom-app-preview .btn-secondary.is-disabled { opacity: 0.58; }

.panel-page .tp-card, .custom-app-preview .tp-card { margin: 0; background: transparent; border: 0; box-shadow: none; }
.panel-page .tp-body, .custom-app-preview .tp-body {
  padding: 0;
  gap: 12rpx;
  background: transparent;
  border: 0;
}
.panel-page .tp-pad, .custom-app-preview .tp-pad {
  width: 100%;
  height: 188rpx;
  background: linear-gradient(145deg, #FFFFFF 0%, #F1F5FA 100%);
  border: 1rpx solid #DFE6EF;
  border-radius: 18rpx;

}
.panel-page .tp-pad::before, .custom-app-preview .tp-pad::before { display: none; }
.panel-page .tp-hint, .custom-app-preview .tp-hint {
  color: #8D99A9;
  font-size: 21rpx;
  font-weight: 400;
}
.panel-page .tp-row, .custom-app-preview .tp-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
}
.panel-page .tp-btn, .custom-app-preview .tp-btn {
  min-width: 0;
  height: 58rpx;
  padding: 0 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #465468;
  background: #FFFFFF;
  border: 1rpx solid #E1E7EF;
  border-radius: 12rpx;
  box-shadow: 0 2rpx 6rpx rgba(43,72,106,0.035);
  font-size: 21rpx;
  font-weight: 550;
}
.panel-page .tp-btn, .custom-app-preview .tp-btn:active {
  background: #EEF6FF;
  border-color: rgba(0,120,212,0.32);
  transform: scale(0.97);
}
.panel-page .tp-btn-icon, .custom-app-preview .tp-btn-icon {
  color: #7C899A;
  background: #F9FAFC;
  font-size: 25rpx;
}

.panel-page .widget-add, .custom-app-preview .widget-add {
  height: 64rpx;
  margin: 18rpx 30rpx 26rpx;
  gap: 8rpx;
  background: rgba(255,255,255,0.42);
  border: 2rpx dashed rgba(62,125,205,0.34);
  border-radius: 14rpx;
}
.panel-page .widget-add-hover, .custom-app-preview .widget-add-hover { background: #EEF6FF; border-color: var(--panel-accent); }
.panel-page .widget-add-plus, .custom-app-preview .widget-add-plus { color: var(--panel-accent); font-size: 26rpx; }
.panel-page .widget-add-label, .custom-app-preview .widget-add-label { color: #4C78B4; font-size: 22rpx; font-weight: 550; }
.panel-page .focus-back, .custom-app-preview .focus-back {
  height: 66rpx;
  margin: 18rpx 30rpx;
  border-radius: 14rpx;
  box-shadow: none;
}
.panel-page .focus-back-label, .custom-app-preview .focus-back-label { font-size: 22rpx; }

.panel-page .empty-hint, .custom-app-preview .empty-hint {
  padding: 28rpx 18rpx;
  color: var(--panel-text-mid);
  background: #F8FAFC;
  border: 1rpx dashed #DDE4ED;
  border-radius: 14rpx;
  font-size: 22rpx;
}

/* 面板内的布局选择与鼠标设置弹层。 */
.panel-page .modal-mask, .custom-app-preview .modal-mask {
  background: rgba(31,48,70,0.28);
  backdrop-filter: blur(12rpx);
  -webkit-backdrop-filter: blur(12rpx);
}
.panel-page .modal, .custom-app-preview .modal {
  max-width: 650rpx;
  background: rgba(255,255,255,0.96);
  border: 1rpx solid rgba(122,145,169,0.18);
  border-radius: 26rpx;
  box-shadow: 0 24rpx 64rpx rgba(40,65,94,0.18);
}
.panel-page .modal-head, .custom-app-preview .modal-head { padding: 26rpx 28rpx 20rpx; }
.panel-page .modal-title, .custom-app-preview .modal-title { color: var(--panel-text); font-size: 29rpx; }
.panel-page .modal-foot, .custom-app-preview .modal-foot { gap: 12rpx; }
.panel-page .btn-cancel, .custom-app-preview .btn-cancel,
.panel-page .btn-save, .custom-app-preview .btn-save {
  min-width: 144rpx;
  padding: 17rpx 24rpx;
  border-radius: 12rpx;
  text-align: center;
  font-size: 24rpx;
  font-weight: 550;
}
.panel-page .btn-cancel, .custom-app-preview .btn-cancel { color: #566579; background: #F2F5F8; }
.panel-page .btn-save, .custom-app-preview .btn-save { color: #FFFFFF; background: var(--panel-accent); }
.panel-page .layout-picker-item, .custom-app-preview .layout-picker-item { padding: 0 20rpx; }
.panel-page .layout-picker-row, .custom-app-preview .layout-picker-row {
  min-height: 78rpx;
  padding: 14rpx 12rpx;
  border-radius: 14rpx;
}
.panel-page .layout-picker-row-hover, .custom-app-preview .layout-picker-row-hover { background: #F0F6FD; }
.panel-page .layout-picker-name, .custom-app-preview .layout-picker-name { display: flex; align-items: center; gap: 12rpx; }
.panel-page .layout-picker-icon, .custom-app-preview .layout-picker-icon { font-size: 28rpx; }
.panel-page .layout-picker-text, .custom-app-preview .layout-picker-text { flex: 1; color: var(--panel-text); font-size: 25rpx; font-weight: 550; }
.panel-page .layout-picker-badge, .custom-app-preview .layout-picker-badge { color: #7C8999; font-size: 20rpx; }
.panel-page .layout-picker-pages, .custom-app-preview .layout-picker-pages { padding: 0 12rpx 12rpx 48rpx; }
.panel-page .layout-picker-page, .custom-app-preview .layout-picker-page { padding: 14rpx 16rpx; color: #69768A; border-radius: 10rpx; font-size: 22rpx; }
.panel-page .layout-picker-page, .custom-app-preview .layout-picker-page.on { color: var(--panel-accent); background: #EDF6FF; }
.panel-page .sens-modal-value, .custom-app-preview .sens-modal-value { padding: 24rpx 0 12rpx; color: var(--panel-accent); font-size: 48rpx; font-weight: 700; text-align: center; }
.panel-page .sens-modal-slider, .custom-app-preview .sens-modal-slider { margin: 12rpx 8rpx 26rpx; }
.panel-page .sens-modal-presets, .custom-app-preview .sens-modal-presets { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8rpx; padding: 0 24rpx; }
.panel-page .sens-preset, .custom-app-preview .sens-preset { padding: 14rpx 4rpx; color: #657286; background: #F5F7FA; border-radius: 10rpx; text-align: center; font-size: 20rpx; }
.panel-page .sens-preset, .custom-app-preview .sens-preset.on { color: var(--panel-accent); background: #EAF5FF; }
.panel-page .sens-modal-input-row, .custom-app-preview .sens-modal-input-row { display: flex; gap: 12rpx; padding: 22rpx 24rpx 10rpx; }
.panel-page .sens-modal-input, .custom-app-preview .sens-modal-input { flex: 1; height: 66rpx; padding: 0 18rpx; background: #F7F9FC; border: 1rpx solid #E1E7EF; border-radius: 12rpx; font-size: 23rpx; }
.panel-page .sens-modal-input-ph, .custom-app-preview .sens-modal-input-ph { color: #A8B1BE; }
.panel-page .sens-modal-input-btn, .custom-app-preview .sens-modal-input-btn { min-width: 112rpx; height: 66rpx; display: flex; align-items: center; justify-content: center; color: #FFFFFF; background: var(--panel-accent); border-radius: 12rpx; font-size: 23rpx; }

.panel-page .trackpad-modal, .custom-app-preview .trackpad-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 260;
  display: flex;
  flex-direction: column;
  padding: calc(64rpx + env(safe-area-inset-top)) 28rpx calc(28rpx + env(safe-area-inset-bottom));
  background: #F5F8FC;
}
.panel-page .trackpad-modal-head, .custom-app-preview .trackpad-modal-head { display: flex; align-items: center; min-height: 72rpx; gap: 12rpx; }
.panel-page .trackpad-modal-title, .custom-app-preview .trackpad-modal-title { flex: 1; color: var(--panel-text); font-size: 30rpx; font-weight: 650; }
.panel-page .trackpad-modal-pos, .custom-app-preview .trackpad-modal-pos { color: #8793A3; font-size: 20rpx; }
.panel-page .trackpad-modal-close, .custom-app-preview .trackpad-modal-close { width: 58rpx; height: 58rpx; display: flex; align-items: center; justify-content: center; color: #526175; background: #FFFFFF; border: 1rpx solid #E0E6EE; border-radius: 16rpx; font-size: 34rpx; }
.panel-page .trackpad-modal-close-hover, .custom-app-preview .trackpad-modal-close-hover { background: #EAF4FF; }
.panel-page .trackpad-modal-pad, .custom-app-preview .trackpad-modal-pad { flex: 1; margin: 20rpx 0; display: flex; align-items: center; justify-content: center; background: linear-gradient(145deg, #FFFFFF 0%, #EEF3F8 100%); border: 1rpx solid #DCE4ED; border-radius: 26rpx; }
.panel-page .trackpad-modal-row, .custom-app-preview .trackpad-modal-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10rpx; }
.panel-page .trackpad-modal-row, .custom-app-preview .trackpad-modal-row .tp-btn { height: 72rpx; }

/* 音量组件与面板卡片保持同一套轻量控件语言。 */
.panel-page .vol-display, .custom-app-preview .vol-display {
  padding: 14rpx 16rpx;
  margin-bottom: 12rpx;
  background: #F6F9FC;
  border: 1rpx solid #E1E8F0;
  border-radius: 14rpx;
}
.panel-page .vol-display-icon, .custom-app-preview .vol-display-icon { font-size: 32rpx; }
.panel-page .vol-display-value, .custom-app-preview .vol-display-value { font-size: 26rpx; }
.panel-page .vol-row, .custom-app-preview .vol-row { gap: 10rpx; }
.panel-page .vol-btn, .custom-app-preview .vol-btn { padding: 16rpx 0; border-radius: 12rpx; }

/* 游戏手柄预览：沿用应用浅色外壳，以实体手柄色彩区分操作区域。 */
.panel-page .inline-gamepad-widget {
  overflow: hidden;
  border-radius: 18rpx;
  background: #F7FBFF;
  border: 1rpx solid rgba(65, 126, 197, 0.16);
}
.panel-page .inline-gamepad-widget.is-disabled { opacity: 1; }
.panel-page .inline-gamepad-widget.is-pressed,
.panel-page .inline-gamepad-widget-hover {
  filter: none;
  transform: scale(0.992);
}
.panel-page .pg-card-header {
  min-height: 58rpx;
  padding: 10rpx 16rpx;
  gap: 10rpx;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1rpx solid rgba(65, 126, 197, 0.13);
}
.panel-page .pg-card-mark {
  width: 18rpx;
  height: 18rpx;
  background: #E8EEF5;
  box-shadow: inset 0 0 0 1rpx rgba(76, 104, 137, 0.12);
}
.panel-page .pg-card-mark-dot { width: 8rpx; height: 8rpx; }
.panel-page .pg-card-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #203A5B;
  font-size: 23rpx;
  font-weight: 650;
  letter-spacing: 0;
}
.panel-page .pg-card-sub {
  flex-shrink: 0;
  padding: 5rpx 10rpx;
  border-radius: 999rpx;
  color: #60758F;
  background: #EDF4FC;
  font-size: 18rpx;
  line-height: 1;
}
.panel-page .inline-gamepad {
  min-height: 0;
  border-radius: 0;
  color: #1C426D;
  background: #EAF4FF;
}
.panel-page .inline-gamepad .pg-stage {
  min-height: 0;
  aspect-ratio: 20 / 9;
  background: radial-gradient(circle at 50% 42%, #FFFFFF 0%, #EDF6FF 60%, #D9EBFF 100%);
}
.panel-page .inline-gamepad .pg-grid {
  background-image:
    linear-gradient(rgba(47, 120, 246, 0.065) 1rpx, transparent 1rpx),
    linear-gradient(90deg, rgba(47, 120, 246, 0.065) 1rpx, transparent 1rpx);
}
.panel-page .inline-gamepad .pg-key-token {
  color: #FFFFFF;
  border-color: rgba(255, 255, 255, 0.9);
  background: linear-gradient(145deg, #55AEFF, #2879E8);
  box-shadow: 0 4rpx 10rpx rgba(38, 105, 205, 0.24), inset 0 0 0 1rpx rgba(255, 255, 255, 0.2);
}
.panel-page .inline-gamepad .pg-key-token-wide {
  background: linear-gradient(145deg, #2EC7D8, #168FC7);
}
.panel-page .inline-gamepad .pg-stick-ring {
  background: rgba(255, 255, 255, 0.72);
  border: 2rpx solid rgba(47, 120, 246, 0.38);
  box-shadow: inset 0 0 0 10rpx rgba(47, 120, 246, 0.07), 0 6rpx 14rpx rgba(47, 120, 246, 0.14);
}
.panel-page .inline-gamepad .pg-stick-center {
  background: radial-gradient(circle at 38% 32%, #FFFFFF 0%, #C8E2FF 68%, #8EBBF1 100%);
  box-shadow: 0 3rpx 8rpx rgba(38, 105, 205, 0.2);
}
.panel-page .inline-gamepad .pg-view-ring {
  background: rgba(35, 193, 172, 0.12);
  border-color: rgba(25, 169, 148, 0.56);
}
.panel-page .inline-gamepad .pg-view-reticle,
.panel-page .inline-gamepad .pg-mouse-crosshair {
  background: #19A994;
  box-shadow: 0 0 0 5rpx rgba(25, 169, 148, 0.13);
}
.panel-page .inline-gamepad .pg-dpad-up,
.panel-page .inline-gamepad .pg-dpad-down,
.panel-page .inline-gamepad .pg-dpad-left,
.panel-page .inline-gamepad .pg-dpad-right {
  color: #FFFFFF;
  background: linear-gradient(145deg, #65ADFF, #3578E4);
  border: 1rpx solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 3rpx 8rpx rgba(36, 111, 229, 0.2);
}
.panel-page .inline-gamepad .pg-dpad-center { background: #2F74DA; }
.panel-page .inline-gamepad .pg-abxy-y { color: #173B61; background: linear-gradient(145deg, #FFE66D, #F6BC27); }
.panel-page .inline-gamepad .pg-abxy-x { color: #FFFFFF; background: linear-gradient(145deg, #75B8FF, #4385EE); }
.panel-page .inline-gamepad .pg-abxy-a { color: #FFFFFF; background: linear-gradient(145deg, #66DFA0, #27BA76); }
.panel-page .inline-gamepad .pg-abxy-b { color: #FFFFFF; background: linear-gradient(145deg, #FF8992, #EA5B70); }
.panel-page .inline-gamepad .pg-abxy-y,
.panel-page .inline-gamepad .pg-abxy-x,
.panel-page .inline-gamepad .pg-abxy-a,
.panel-page .inline-gamepad .pg-abxy-b {
  border: 1rpx solid rgba(255, 255, 255, 0.82);
  box-shadow: 0 4rpx 9rpx rgba(39, 79, 115, 0.18);
}
.panel-page .inline-gamepad .pg-single-button {
  color: var(--pg-custom-text, #245488);
  background: linear-gradient(145deg, var(--pg-custom-fill, #FFFFFF), var(--pg-custom-fill, #DDEEFF));
  border-color: var(--pg-custom-border, rgba(47, 120, 246, 0.45));
  box-shadow: 0 3rpx 8rpx rgba(47, 120, 246, 0.15);
}
.panel-page .inline-gamepad .pg-shoulder .pg-single-button {
  color: var(--pg-custom-text, #FFFFFF);
  background: linear-gradient(145deg, var(--pg-custom-fill, #34C5D8), var(--pg-custom-fill, #168BC8));
  border-color: var(--pg-custom-border, rgba(255, 255, 255, 0.72));
}
.panel-page .pg-card-foot {
  padding: 9rpx 16rpx;
  text-align: center;
  background: rgba(255, 255, 255, 0.94);
  border-top: 1rpx solid rgba(65, 126, 197, 0.13);
}
.panel-page .pg-card-foot-text {
  color: #2F78F6;
  font-size: 19rpx;
  font-weight: 600;
  letter-spacing: 0;
}
.panel-page .inline-gamepad .pg-empty-state {
  min-height: 230rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30rpx 24rpx;
  background: radial-gradient(circle at 50% 35%, #FFFFFF 0%, #E8F4FF 100%);
}
.panel-page .inline-gamepad .pg-empty-text { color: #66809E; font-size: 22rpx; }

/* 与桌面编辑器和横屏页共用的四套主题。 */
.panel-page .inline-gamepad .pg-stage-bg-mobile-light {
  --pg-stage-top: #f9fdff; --pg-stage-bottom: #dff0f8; --pg-grid: rgba(74,130,153,0.10);
  --pg-button-top: #58a8ff; --pg-button-bottom: #286cda; --pg-button-text: #ffffff;
  --pg-button-border: rgba(223,245,255,0.92); --pg-control-fill: rgba(223,247,245,0.72);
  --pg-control-inner: #eef9fc; --pg-control-border: rgba(73,187,178,0.72); --pg-accent: #18a899;
}
.panel-page .inline-gamepad .pg-stage-bg-mobile-dark {
  --pg-stage-top: #1e2536; --pg-stage-bottom: #0f1320; --pg-grid: rgba(255,255,255,0.025);
  --pg-button-top: #2a3142; --pg-button-bottom: #1a1f2c; --pg-button-text: #cbd5e1;
  --pg-button-border: rgba(148,163,184,0.28); --pg-control-fill: #1a1f2c;
  --pg-control-inner: #475569; --pg-control-border: rgba(148,163,184,0.38); --pg-accent: #38bdf8;
}
.panel-page .inline-gamepad .pg-stage-bg-terrain {
  --pg-stage-top: #246381; --pg-stage-bottom: #336b52; --pg-grid: rgba(35,64,76,0.08);
  --pg-button-top: #367efa; --pg-button-bottom: #1c56c8; --pg-button-text: #eff9ff;
  --pg-button-border: rgba(91,164,255,0.8); --pg-control-fill: #10428b;
  --pg-control-inner: #46a1ff; --pg-control-border: rgba(90,166,255,0.8); --pg-accent: #48ded3;
}
.panel-page .inline-gamepad .pg-stage-bg-arcade-neon {
  --pg-stage-top: #20152f; --pg-stage-bottom: #111b2b; --pg-grid: rgba(214,109,255,0.12);
  --pg-button-top: #36234a; --pg-button-bottom: #1c1730; --pg-button-text: #f8e8ff;
  --pg-button-border: rgba(219,115,255,0.74); --pg-control-fill: #2e1b4b;
  --pg-control-inner: #5e2d78; --pg-control-border: rgba(226,119,255,0.76); --pg-accent: #ff6bc7;
}
.panel-page .inline-gamepad .pg-stage-bg-paper-grid {
  --pg-stage-top: #edf3f6; --pg-stage-bottom: #dfe8ed; --pg-grid: rgba(87,113,124,0.22);
  --pg-button-top: #ffffff; --pg-button-bottom: #d9e4ea; --pg-button-text: #20323a;
  --pg-button-border: rgba(77,123,140,0.56); --pg-control-fill: #d5e2e8;
  --pg-control-inner: #9dbdc8; --pg-control-border: rgba(77,123,140,0.7); --pg-accent: #0d9296;
}
.panel-page .inline-gamepad .pg-stage-themed {
  background: radial-gradient(ellipse at center, var(--pg-stage-top) 0%, var(--pg-stage-bottom) 100%);
}
.panel-page .inline-gamepad .pg-stage-themed.pg-stage-bg-terrain {
  background:
    linear-gradient(112deg, transparent 0 43%, rgba(183,174,119,0.88) 43% 55%, transparent 55%),
    linear-gradient(180deg, var(--pg-stage-top) 0 48%, var(--pg-stage-bottom) 48% 100%);
}
.panel-page .inline-gamepad .pg-stage-themed .pg-grid {
  background-image: linear-gradient(var(--pg-grid) 1rpx, transparent 1rpx), linear-gradient(90deg, var(--pg-grid) 1rpx, transparent 1rpx);
}
.panel-page .inline-gamepad .pg-stage-themed .pg-stick-ring,
.panel-page .inline-gamepad .pg-stage-themed .pg-view-ring {
  background: var(--pg-custom-fill, var(--pg-control-fill)); border-color: var(--pg-custom-border, var(--pg-control-border));
  box-shadow: inset 0 0 0 8rpx rgba(255,255,255,0.06), 0 5rpx 14rpx rgba(0,0,0,0.22);
}
.panel-page .inline-gamepad .pg-stage-themed .pg-stick-center { background: var(--pg-control-inner); }
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-up,
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-down,
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-left,
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-right {
  background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom)));
  border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text));
}
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-center { background: var(--pg-stage-bottom); }
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-y,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-x,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-a,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-b {
  background: linear-gradient(145deg, var(--pg-button-top), var(--pg-button-bottom));
  border-color: var(--pg-button-border);
}
.panel-page .inline-gamepad .pg-stage-bg-mobile-light .pg-control-caption { color: #315864; }
.panel-page .inline-gamepad .pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-y { background: linear-gradient(145deg, var(--pg-custom-fill, #ffe66d), var(--pg-custom-fill, #f7bb24)); color: var(--pg-custom-text, #173b61); }
.panel-page .inline-gamepad .pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-x { background: linear-gradient(145deg, var(--pg-custom-fill, #78b6ff), var(--pg-custom-fill, #4a83ef)); color: var(--pg-custom-text, #ffffff); }
.panel-page .inline-gamepad .pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-a { background: linear-gradient(145deg, var(--pg-custom-fill, #69df9b), var(--pg-custom-fill, #2bbd75)); color: var(--pg-custom-text, #ffffff); }
.panel-page .inline-gamepad .pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, #ff8b91), var(--pg-custom-fill, #ed5d71)); color: var(--pg-custom-text, #ffffff); }
.panel-page .inline-gamepad .pg-stage-themed .pg-stick-key,
.panel-page .inline-gamepad .pg-stage-themed .pg-dpad-key { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-button-bottom)); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-y,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-x,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-a,
.panel-page .inline-gamepad .pg-stage-themed .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom))); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
.panel-page .inline-gamepad .pg-stage-themed .pg-view-reticle,
.panel-page .inline-gamepad .pg-stage-themed .pg-mouse-crosshair { background: var(--pg-accent); box-shadow: 0 0 8rpx var(--pg-accent); }
.panel-page .inline-gamepad .pg-stage-themed .pg-mouse-track { background: var(--pg-control-fill); border-color: var(--pg-control-border); }
.panel-page .inline-gamepad .pg-stage-themed .pg-single-button,
.panel-page .inline-gamepad .pg-stage-themed .pg-shoulder .pg-single-button {
  background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom)));
  border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text));
}

.panel-page.app-appearance-active .more-btn,
.panel-page.app-appearance-active .widget-head-action,
.panel-page.app-appearance-active .widget-head-toggle,
.panel-page.app-appearance-active .widget-head-fullscreen,
.panel-page.app-appearance-active .widget-head-switch,
.panel-page.app-appearance-active .widget-shell.is-collapsed .widget-head-toggle {
  background: var(--app-surface-strong) !important;
  border-color: var(--app-color-border) !important;
}
.panel-page.app-appearance-active .more-btn-dot,
.panel-page.app-appearance-active .status-text,
.panel-page.app-appearance-active .widget-head-toggle-icon,
.panel-page.app-appearance-active .widget-head-fullscreen-icon,
.panel-page.app-appearance-active .widget-head-switch-icon,
.panel-page.app-appearance-active .widget-head-edit-icon,
.panel-page.app-appearance-active .widget-shell.is-collapsed .widget-head-toggle-icon {
  color: var(--app-color-text-mid) !important;
}
.panel-page.app-appearance-active .more-btn-hover,
.panel-page.app-appearance-active .widget-head-action-hover {
  background: var(--app-color-primary-bg) !important;
  border-color: var(--app-color-primary) !important;
}
.panel-page.app-appearance-active .widget-add {
  background: var(--app-surface) !important;
  border-color: var(--app-color-primary) !important;
}
.panel-page.app-appearance-active .widget-add-plus,
.panel-page.app-appearance-active .widget-add-label {
  color: var(--app-color-primary) !important;
}

/* ===== 专注模式 内联卡片 ===== */
.focus-card {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  padding: 4rpx 0;
}
.focus-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.focus-row-main {
  justify-content: space-between;
}
.focus-info {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  min-width: 0;
  flex: 1;
}
.focus-mode {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--color-text, #172033);
  line-height: 1.25;
}
.focus-duration {
  font-size: 24rpx;
  color: var(--color-text-light, #7E8B9E);
}
.focus-cta {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: var(--color-primary-bg, #EAF3FF);
  color: var(--color-primary, #2F78F6);
  flex-shrink: 0;
}
.focus-cta-text {
  font-size: 24rpx;
  font-weight: 600;
}
.focus-cta-arrow {
  font-size: 26rpx;
  line-height: 1;
}
.focus-row-sub {
  flex-wrap: wrap;
}
.focus-chip {
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(47, 120, 246, 0.10);
  color: var(--color-primary, #2F78F6);
  font-size: 22rpx;
  font-weight: 600;
}
.focus-chip-icon {
  font-size: 22rpx;
  line-height: 1;
}
.focus-chip-muted {
  background: rgba(0, 0, 0, 0.04);
  color: var(--color-text-light, #7E8B9E);
}
</style>
