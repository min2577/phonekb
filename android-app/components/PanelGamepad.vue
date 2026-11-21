<template>
  <view class="panel-gamepad" :class="{ 'is-disabled': !connected }">
    <!-- 顶部迷你状态条 -->
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

    <!-- 控件舞台 -->
    <view v-if="activeLayout" class="pg-stage pg-stage-themed" :class="backgroundStageClass" :style="backgroundStageStyle">
      <view class="pg-grid"></view>

      <view
        v-for="control in activeLayout.controls"
        :key="control.id"
        class="pg-control"
        :style="controlStyle(control)"
        :data-control-id="control.id"
      >
        <!-- 左摇杆:四方向 + 中心回正 -->
        <view v-if="control.type === 'leftStick'" class="pg-stick-zone">
          <view class="pg-stick-ring">
            <view class="pg-stick-up"    @touchstart.stop="onStickStart(control, 'up')"    @touchend.stop="onStickEnd(control, 'up')"    @touchcancel.stop="onStickEnd(control, 'up')"></view>
            <view class="pg-stick-right" @touchstart.stop="onStickStart(control, 'right')" @touchend.stop="onStickEnd(control, 'right')" @touchcancel.stop="onStickEnd(control, 'right')"></view>
            <view class="pg-stick-down"  @touchstart.stop="onStickStart(control, 'down')"  @touchend.stop="onStickEnd(control, 'down')"  @touchcancel.stop="onStickEnd(control, 'down')"></view>
            <view class="pg-stick-left"  @touchstart.stop="onStickStart(control, 'left')"  @touchend.stop="onStickEnd(control, 'left')"  @touchcancel.stop="onStickEnd(control, 'left')"></view>
            <view class="pg-stick-center"></view>
          </view>
          <text v-if="control.label" class="pg-control-caption">{{ control.label }}</text>
        </view>

        <!-- 右摇杆:鼠标视角 -->
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

        <!-- 方向键 dpad -->
        <view v-else-if="control.type === 'dpad'" class="pg-dpad-zone">
          <view class="pg-dpad-up"    @touchstart.stop="onKeyStart(control, 'up')"    @touchend.stop="onKeyEnd(control, 'up')"    @touchcancel.stop="onKeyEnd(control, 'up')">↑</view>
          <view class="pg-dpad-left"  @touchstart.stop="onKeyStart(control, 'left')"  @touchend.stop="onKeyEnd(control, 'left')"  @touchcancel.stop="onKeyEnd(control, 'left')">←</view>
          <view class="pg-dpad-right" @touchstart.stop="onKeyStart(control, 'right')" @touchend.stop="onKeyEnd(control, 'right')" @touchcancel.stop="onKeyEnd(control, 'right')">→</view>
          <view class="pg-dpad-down"  @touchstart.stop="onKeyStart(control, 'down')"  @touchend.stop="onKeyEnd(control, 'down')"  @touchcancel.stop="onKeyEnd(control, 'down')">↓</view>
          <view class="pg-dpad-center"></view>
        </view>

        <!-- ABXY -->
        <view v-else-if="control.type === 'abxy'" class="pg-abxy-zone">
          <view class="pg-abxy-y" @touchstart.stop="onKeyStart(control, 'y')" @touchend.stop="onKeyEnd(control, 'y')" @touchcancel.stop="onKeyEnd(control, 'y')">Y</view>
          <view class="pg-abxy-x" @touchstart.stop="onKeyStart(control, 'x')" @touchend.stop="onKeyEnd(control, 'x')" @touchcancel.stop="onKeyEnd(control, 'x')">X</view>
          <view class="pg-abxy-a" @touchstart.stop="onKeyStart(control, 'a')" @touchend.stop="onKeyEnd(control, 'a')" @touchcancel.stop="onKeyEnd(control, 'a')">A</view>
          <view class="pg-abxy-b" @touchstart.stop="onKeyStart(control, 'b')" @touchend.stop="onKeyEnd(control, 'b')" @touchcancel.stop="onKeyEnd(control, 'b')">B</view>
        </view>

        <!-- 鼠标区域:触摸移动控制鼠标 -->
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

        <!-- 单键 / 肩键 -->
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
            @touchstart.stop="onKeyStart(control, 'press')"
            @touchend.stop="onKeyEnd(control, 'press')"
            @touchcancel.stop="onKeyEnd(control, 'press')"
          >
            <text class="pg-button-label">{{ control.label || 'KEY' }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else class="pg-empty-state">
      <text class="pg-empty-text">{{ emptyText }}</text>
    </view>
  </view>
</template>

<script>
/**
 * PanelGamepad.vue - 游戏手柄小组件
 *
 * 设计目标:
 *   1. 可作为 widget 嵌入 panel,与快捷键/文字输入等并列
 *   2. 接收电脑端通过 WS 推送的游戏手柄布局 (action: gamepad_layouts)
 *   3. 每个控件带触摸事件,按下/松开调用 WS.gamepadKey()
 *   4. 摇杆/鼠标区域通过 touchmove 持续发 WS.gamepadMouseMove()
 *
 * 与原 gamepad.vue 的差异:
 *   - 没有顶栏/底部统计(由 widget 外壳统一处理)
 *   - CSS 单位用 rpx + scale,缩放进 widget 卡片仍清晰
 *   - 不用全屏页面的横屏强制,父容器决定显示尺寸
 */
import WS from '@/utils/wsclient.js'

// 按键方向到 wasd / arrow / 单字符 的常见映射
const DIRECTION_TO_KEY = {
  up: 'w',
  down: 's',
  left: 'a',
  right: 'd',
}

export default {
  name: 'PanelGamepad',
  props: {
    // 可选:外部传入连接状态(panel.vue 已经传了 connected 给其他 widget)
    connected: { type: Boolean, default: false },
    // 可选:外部传入布局数据(没传就从 WS.getCachedGamepadLayouts() 读)
    layoutsData: { type: Object, default: null },
    // 缩放模式:
    //   'auto'  - 默认,根据容器宽高自动缩放
    //   'fixed' - 按 20:9 固定尺寸
    aspect: { type: String, default: 'auto' },
  },
  data() {
    return {
      internalLayouts: null,
      internalConnected: false,
      lastError: '',
      // 防误触:正在按的键集合(用于 ABXY / dpad / shoulder)
      pressedKeys: {},
      // 摇杆跟踪
      stickHeld: {},
      // 鼠标区域跟踪
      mouseActive: null,
      // 鼠标区域累计位移,防止 touchmove 丢帧
      mouseLastPoint: null,
    }
  },
  computed: {
    layoutsDataMerged() {
      return this.layoutsData || this.internalLayouts
    },
    connectedMerged() {
      return this.connected || this.internalConnected
    },
    activeLayout() {
      const data = this.layoutsDataMerged
      if (!data || !Array.isArray(data.layouts)) return null
      return data.layouts.find(l => l.id === data.activeLayoutId) || data.layouts[0] || null
    },
    statusLabel() {
      if (!this.connectedMerged) return '未连接'
      if (!this.activeLayout) return '电脑未推送布局'
      return '已同步'
    },
    statusClass() {
      if (!this.connectedMerged) return 'is-offline'
      if (!this.activeLayout) return 'is-warning'
      return 'is-on'
    },
    emptyText() {
      if (!this.connectedMerged) return '连接电脑后,这里显示游戏手柄控件'
      return '等待电脑端推送布局'
    },
    backgroundStageClass() {
      const background = (this.activeLayout && this.activeLayout.background) || {}
      const id = background.baseId || background.id
      return 'pg-stage-bg-' + (id || 'mobile-light')
    },
    backgroundStageStyle() {
      const background = (this.activeLayout && this.activeLayout.background) || {}
      const theme = background.theme || {}
      const canvas = (this.activeLayout && this.activeLayout.canvas) || {}
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
  },
  mounted() {
    // 读本地缓存
    try {
      const cached = WS.getCachedGamepadLayouts()
      if (cached && Array.isArray(cached.layouts) && cached.layouts.length) {
        this.internalLayouts = cached
      }
    } catch (e) {}

    this.internalConnected = WS.isConnected()

    // 订阅布局推送
    this._layoutListener = (data) => {
      if (!data || !Array.isArray(data.layouts)) return
      this.internalLayouts = data
      this.lastError = ''
    }
    WS.onGamepadLayouts(this._layoutListener)

    // 订阅连接状态
    this._stateListener = (state) => {
      this.internalConnected = state === 'connected'
      if (this.internalConnected) {
        // 重新拉一次
        try { WS.getGamepadLayouts() } catch (e) {}
      }
    }
    if (typeof WS.onStateChange === 'function') WS.onStateChange(this._stateListener)
  },
  beforeUnmount() {
    if (this._layoutListener) WS.offGamepadLayouts(this._layoutListener)
    if (this._stateListener && typeof WS.offStateChange === 'function') WS.offStateChange(this._stateListener)
    // 释放所有按下的键,防止 widget 卸载后电脑端一直按下
    this._releaseAll()
  },
  methods: {
    /**
     * 控件定位样式 - 跟原 gamepad.vue 一致: x/y 是百分比,大小由 size 缩放
     */
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

    /**
     * 单层布局直接读取组件槽位。结构化 shortcut 会展开成有序按键数组。
     */
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

    /**
     * 左摇杆某方向按下
     * 优先用 binding 里配置的 key,否则按方向映射到 wasd / arrows
     */
    onStickStart(control, dir) {
      if (!this.connectedMerged) return
      const keys = this.bindingKeys(this.resolveBinding(control, dir), DIRECTION_TO_KEY[dir])
      const token = control.id + ':' + dir
      keys.forEach(key => this._pressKey(key, token))
    },
    onStickEnd(control, dir) {
      if (!this.connectedMerged) return
      const keys = this.bindingKeys(this.resolveBinding(control, dir), DIRECTION_TO_KEY[dir])
      const token = control.id + ':' + dir
      keys.reverse().forEach(key => this._releaseKey(key, token))
    },

    /**
     * 普通按键 (dpad / abxy / shoulder / 单键)
     */
    onKeyStart(control, slot) {
      if (!this.connectedMerged) return
      const keys = this.bindingKeys(this.resolveBinding(control, slot))
      const token = control.id + ':' + slot
      keys.forEach(key => this._pressKey(key, token))
    },
    onKeyEnd(control, slot) {
      if (!this.connectedMerged) return
      const keys = this.bindingKeys(this.resolveBinding(control, slot))
      const token = control.id + ':' + slot
      keys.reverse().forEach(key => this._releaseKey(key, token))
    },

    /**
     * 组合键沿用现有 gamepad_key 协议：每个键共享同一个触摸 token，
     * 因此重复命中同一键时仍由 _pressKey/_releaseKey 做引用计数。
     */
    _expandKeyValue(value) {
      return String(value || '')
        .split(/\s*\+\s*/)
        .map(item => item.trim())
        .filter(Boolean)
    },

    /**
     * 右摇杆 - 鼠标视角移动
     * 以 touchstart 为圆心,dx/dy = 当前点 - 中心点,乘以 sensitivity
     */
    onViewStart(control, e) {
      if (!this.connectedMerged) return
      const t = (e && e.touches && e.touches[0]) || (e && e.changedTouches && e.changedTouches[0])
      if (!t) return
      this._stickActive = {
        controlId: control.id,
        cx: t.clientX || t.pageX || t.x || 0,
        cy: t.clientY || t.pageY || t.y || 0,
        sens: Number(control.sensitivity || 55) / 100, // 0.55
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
      // 节流:距离太小不发送
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
      // 截断极端值
      dx = Math.max(-120, Math.min(120, dx))
      dy = Math.max(-120, Math.min(120, dy))
      try { WS.gamepadMouseMove(Math.round(dx), Math.round(dy)) } catch (err) {}
      // 重置基准点,避免累计漂移
      a.cx = x
      a.cy = y
    },
    onViewEnd(control, e) {
      if (this._stickActive && this._stickActive.controlId === control.id) {
        this._stickActive = null
      }
    },

    /**
     * 鼠标区域 - 拖动 = 鼠标移动
     */
    onMouseStart(control, e) {
      if (!this.connectedMerged) return
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
      const sens = Number(control.sensitivity || 55) / 50 // 比摇杆稍高
      let dx = (x - this.mouseLastPoint.x) * sens
      let dy = (y - this.mouseLastPoint.y) * sens
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
      dx = Math.max(-150, Math.min(150, dx))
      dy = Math.max(-150, Math.min(150, dy))
      try { WS.gamepadMouseMove(Math.round(dx), Math.round(dy)) } catch (err) {}
      this.mouseLastPoint = { x, y }
    },
    onMouseEnd(control, e) {
      if (this.mouseActive && this.mouseActive.controlId === control.id) {
        this.mouseActive = null
        this.mouseLastPoint = null
      }
    },

    /**
     * 底层 - 引用计数式 press / release
     * 同一个 key 可能来自多个 slot(如 dpad.up 和 leftStick.up 都用 'w'),
     * 用 token 区分,直到所有 token release 才真正 release
     */
    _pressKey(key, token) {
      if (!this.pressedKeys[key]) this.pressedKeys[key] = {}
      this.pressedKeys[key][token] = true
      // 只有从 0 个 token -> 1 个 token 的瞬间才发 gamepad_key(down=true)
      if (Object.keys(this.pressedKeys[key]).length === 1) {
        try { WS.gamepadKey([key], true) } catch (err) {}
      }
    },
    _releaseKey(key, token) {
      if (!this.pressedKeys[key]) return
      delete this.pressedKeys[key][token]
      if (Object.keys(this.pressedKeys[key]).length === 0) {
        delete this.pressedKeys[key]
        try { WS.gamepadKey([key], false) } catch (err) {}
      }
    },
    _releaseAll() {
      const keys = Object.keys(this.pressedKeys)
      keys.forEach(k => {
        try { WS.gamepadKey([k], false) } catch (err) {}
      })
      this.pressedKeys = {}
      this._stickActive = null
      this.mouseActive = null
      this.mouseLastPoint = null
    },
  },
}
</script>

<style scoped>
/* 容器 */
.panel-gamepad {
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
}
.panel-gamepad.is-disabled { opacity: 0.55; }

/* 顶部状态条 */
.pg-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 20rpx;
  font-size: 22rpx;
  color: #94a3b8;
  border-bottom: 1rpx solid rgba(255,255,255,0.04);
}
.pg-status {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.pg-status-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #475569;
}
.pg-status.is-on .pg-status-dot { background: #34d399; box-shadow: 0 0 12rpx #34d399; }
.pg-status.is-warning .pg-status-dot { background: #f59e0b; }
.pg-status.is-offline .pg-status-dot { background: #ef4444; }
.pg-status-text { font-size: 22rpx; }
.pg-layout-name { font-size: 22rpx; color: #cbd5e1; }
.pg-layout-name.pg-empty { color: #64748b; }

/* 控件舞台 - 与桌面编辑画布一致使用 20:9。 */
.pg-stage {
  position: relative;
  width: 100%;
  padding-bottom: 45%;
  --pg-stage-top: #1e2536;
  --pg-stage-bottom: #0f1320;
  --pg-grid: rgba(255,255,255,0.025);
  --pg-button-top: #2a3142;
  --pg-button-bottom: #1a1f2c;
  --pg-button-text: #cbd5e1;
  --pg-button-border: rgba(148,163,184,0.15);
  --pg-control-fill: #1a1f2c;
  --pg-control-inner: #475569;
  --pg-control-border: rgba(148,163,184,0.2);
  --pg-accent: #38bdf8;
  --pg-accent-dark: #0ea5e9;
  background: radial-gradient(ellipse at center, var(--pg-stage-top) 0%, var(--pg-stage-bottom) 100%);
  overflow: hidden;
}
.pg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(var(--pg-grid) 1rpx, transparent 1rpx),
    linear-gradient(90deg, var(--pg-grid) 1rpx, transparent 1rpx);
  background-size: 8.33% 11.11%;
}

/* 控件通用 */
.pg-control {
  position: absolute;
  width: 0;
  height: 0;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
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
.pg-control-caption {
  position: absolute;
  bottom: -28rpx;
  font-size: 18rpx;
  color: #64748b;
  white-space: nowrap;
}

/* 左/右摇杆 */
.pg-stick-zone {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  flex-direction: column;
}
.pg-stick-ring {
  position: relative;
  width: 80%;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, var(--pg-button-top) 0%, var(--pg-button-bottom) 70%);
  box-shadow: inset 0 0 16rpx rgba(0,0,0,0.5), 0 0 0 2rpx var(--pg-control-border);
}
.pg-view-ring { background: radial-gradient(circle at 50% 50%, var(--pg-control-fill) 0%, var(--pg-stage-bottom) 80%); }
.pg-view-reticle {
  position: absolute; left: 50%; top: 50%;
  width: 16rpx; height: 16rpx;
  border-radius: 50%;
  background: var(--pg-accent);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 12rpx var(--pg-accent);
}
.pg-stick-up, .pg-stick-right, .pg-stick-down, .pg-stick-left {
  position: absolute;
  background: transparent;
  z-index: 2;
}
.pg-stick-up    { left: 25%; top: 0;    width: 50%; height: 35%; }
.pg-stick-right { right: 0;  top: 25%;  width: 35%; height: 50%; }
.pg-stick-down  { left: 25%; bottom: 0; width: 50%; height: 35%; }
.pg-stick-left  { left: 0;   top: 25%;  width: 35%; height: 50%; }
.pg-stick-center {
  position: absolute; left: 50%; top: 50%;
  width: 28%; height: 28%;
  border-radius: 50%;
  background: radial-gradient(circle, var(--pg-control-inner) 0%, var(--pg-stage-bottom) 100%);
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 1;
}

/* 摇杆四个方向触摸反馈 */
.pg-stick-up:active,    .pg-stick-up.is-pressed    { background: radial-gradient(circle at 50% 100%, rgba(56,189,248,0.4), transparent); }
.pg-stick-down:active,  .pg-stick-down.is-pressed  { background: radial-gradient(circle at 50% 0%,   rgba(56,189,248,0.4), transparent); }
.pg-stick-left:active,  .pg-stick-left.is-pressed  { background: radial-gradient(circle at 100% 50%, rgba(56,189,248,0.4), transparent); }
.pg-stick-right:active, .pg-stick-right.is-pressed { background: radial-gradient(circle at 0% 50%,   rgba(56,189,248,0.4), transparent); }

/* dpad */
.pg-dpad-zone {
  position: relative;
  width: 100%; height: 100%;
}
.pg-dpad-up, .pg-dpad-down, .pg-dpad-left, .pg-dpad-right {
  position: absolute;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, var(--pg-button-top), var(--pg-button-bottom));
  color: var(--pg-button-text);
  font-size: 28rpx;
  z-index: 2;
}
.pg-dpad-up    { left: 30%; top: 0;    width: 40%; height: 32%; border-radius: 12rpx 12rpx 0 0; }
.pg-dpad-down  { left: 30%; bottom: 0; width: 40%; height: 32%; border-radius: 0 0 12rpx 12rpx; }
.pg-dpad-left  { left: 0;   top: 30%;  width: 32%; height: 40%; border-radius: 12rpx 0 0 12rpx; }
.pg-dpad-right { right: 0;  top: 30%;  width: 32%; height: 40%; border-radius: 0 12rpx 12rpx 0; }
.pg-dpad-center {
  position: absolute; left: 32%; top: 32%;
  width: 36%; height: 36%;
  background: var(--pg-stage-bottom);
  z-index: 1;
}
.pg-dpad-up:active, .pg-dpad-down:active, .pg-dpad-left:active, .pg-dpad-right:active {
  background: linear-gradient(145deg, var(--pg-accent), var(--pg-accent-dark));
  color: #fff;
}

/* ABXY */
.pg-abxy-zone {
  position: relative;
  width: 100%; height: 100%;
}
.pg-abxy-y, .pg-abxy-x, .pg-abxy-a, .pg-abxy-b {
  position: absolute;
  display: flex; align-items: center; justify-content: center;
  width: 38%; height: 38%;
  border-radius: 50%;
  background: linear-gradient(145deg, var(--pg-button-top), var(--pg-button-bottom));
  color: #f1f5f9;
  font-size: 30rpx;
  font-weight: 600;
  z-index: 2;
  box-shadow: inset 0 -4rpx 8rpx rgba(0,0,0,0.3);
}
.pg-abxy-y { left: 31%; top: 0;    color: #facc15; }
.pg-abxy-x { left: 0;   top: 31%;  color: #60a5fa; }
.pg-abxy-a { left: 62%; top: 31%;  color: #34d399; }
.pg-abxy-b { left: 31%; top: 62%;  color: #f87171; }
.pg-abxy-y:active { background: #facc15; color: #131720; }
.pg-abxy-x:active { background: #60a5fa; color: #131720; }
.pg-abxy-a:active { background: #34d399; color: #131720; }
.pg-abxy-b:active { background: #f87171; color: #131720; }

/* 鼠标区 */
.pg-mouse-zone {
  position: relative;
  width: 100%; height: 100%;
}
.pg-mouse-track {
  position: relative;
  width: 100%; height: 100%;
  border-radius: 16rpx;
  background: linear-gradient(145deg, var(--pg-button-bottom), var(--pg-stage-bottom));
  box-shadow: inset 0 0 12rpx rgba(0,0,0,0.5);
  overflow: hidden;
  z-index: 2;
}
.pg-mouse-crosshair {
  position: absolute; left: 50%; top: 50%;
  width: 16rpx; height: 16rpx;
  border-radius: 50%;
  background: var(--pg-accent);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 8rpx var(--pg-accent);
  pointer-events: none;
}

/* 单键 / 肩键 */
.pg-button-control {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
}
.pg-single-button {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; box-sizing: border-box;
  padding: 0 6rpx;
  background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom)));
  color: var(--pg-custom-text, var(--pg-button-text));
  font-size: 22rpx;
  font-weight: 500;
  border: 2rpx solid var(--pg-custom-border, var(--pg-button-border));
  box-shadow: inset 0 -4rpx 8rpx rgba(0,0,0,0.3);
  min-width: 0; min-height: 0;
}
.pg-single-wide { border-radius: 12rpx; min-width: 0; min-height: 0; }
.pg-single-round { border-radius: 50%; }
.pg-shape-pill { border-radius: 999rpx; }
.pg-shape-square { border-radius: 6rpx; }
.pg-shape-diamond { border-radius: 8rpx; transform: rotate(45deg); }
.pg-shape-diamond .pg-button-label { display: inline-block; transform: rotate(-45deg); }
.pg-shoulder .pg-single-button { min-width: 0; min-height: 0; font-size: 20rpx; }
.pg-single-button:active { background: linear-gradient(145deg, var(--pg-accent), var(--pg-accent-dark)); color: #fff; }

/* 内置主题。布局只保存主题 id，控件仍使用同一套响应式尺寸。 */
.pg-stage-bg-mobile-light {
  --pg-stage-top: #f9fdff;
  --pg-stage-bottom: #dff0f8;
  --pg-grid: rgba(74, 130, 153, 0.10);
  --pg-button-top: #58a8ff;
  --pg-button-bottom: #286cda;
  --pg-button-text: #ffffff;
  --pg-button-border: rgba(223, 245, 255, 0.92);
  --pg-control-fill: rgba(223, 247, 245, 0.72);
  --pg-control-inner: #eef9fc;
  --pg-control-border: rgba(73, 187, 178, 0.72);
  --pg-accent: #18a899;
  --pg-accent-dark: #0d8278;
}
.pg-stage-bg-mobile-dark {
  --pg-stage-top: #1e2536;
  --pg-stage-bottom: #0f1320;
  --pg-grid: rgba(255,255,255,0.025);
  --pg-button-top: #2a3142;
  --pg-button-bottom: #1a1f2c;
  --pg-button-text: #cbd5e1;
  --pg-button-border: rgba(148,163,184,0.15);
  --pg-control-fill: #1a1f2c;
  --pg-control-inner: #475569;
  --pg-control-border: rgba(148,163,184,0.2);
  --pg-accent: #38bdf8;
  --pg-accent-dark: #0ea5e9;
}
.pg-stage-bg-terrain {
  --pg-stage-top: #246381;
  --pg-stage-bottom: #336b52;
  --pg-grid: rgba(35,64,76,0.02);
  --pg-button-top: #367efa;
  --pg-button-bottom: #1c56c8;
  --pg-button-text: #eff9ff;
  --pg-button-border: rgba(91,164,255,0.72);
  --pg-control-fill: #10428b;
  --pg-control-inner: #46a1ff;
  --pg-control-border: rgba(90,166,255,0.72);
  --pg-accent: #48ded3;
  --pg-accent-dark: #1c56c8;
}
.pg-stage-bg-arcade-neon {
  --pg-stage-top: #20152f;
  --pg-stage-bottom: #111b2b;
  --pg-grid: rgba(214,109,255,0.12);
  --pg-button-top: #36234a;
  --pg-button-bottom: #1c1730;
  --pg-button-text: #f8e8ff;
  --pg-button-border: rgba(219,115,255,0.7);
  --pg-control-fill: #2e1b4b;
  --pg-control-inner: #5e2d78;
  --pg-control-border: rgba(226,119,255,0.72);
  --pg-accent: #ff6bc7;
  --pg-accent-dark: #9f42d7;
}
.pg-stage-bg-paper-grid {
  --pg-stage-top: #edf3f6;
  --pg-stage-bottom: #dfe8ed;
  --pg-grid: rgba(87,113,124,0.22);
  --pg-button-top: #ffffff;
  --pg-button-bottom: #d9e4ea;
  --pg-button-text: #20323a;
  --pg-button-border: rgba(77,123,140,0.52);
  --pg-control-fill: #d5e2e8;
  --pg-control-inner: #9dbdc8;
  --pg-control-border: rgba(77,123,140,0.68);
  --pg-accent: #0d9296;
  --pg-accent-dark: #087276;
}
.pg-stage-bg-paper-grid .pg-control-caption { color: #45616c; }
.pg-stage-bg-paper-grid .pg-dpad-center { background: rgba(255,255,255,0.55); }
.pg-stage-bg-paper-grid .pg-mouse-track { box-shadow: inset 0 0 12rpx rgba(55,80,90,0.22); }

.pg-stage-themed {
  background: radial-gradient(ellipse at center, var(--pg-stage-top) 0%, var(--pg-stage-bottom) 100%);
}
.pg-stage-themed.pg-stage-bg-terrain {
  background:
    linear-gradient(112deg, transparent 0 43%, rgba(183,174,119,0.88) 43% 55%, transparent 55%),
    linear-gradient(180deg, var(--pg-stage-top) 0 48%, var(--pg-stage-bottom) 48% 100%);
}
.pg-stage-themed .pg-grid {
  background-image: linear-gradient(var(--pg-grid) 1rpx, transparent 1rpx), linear-gradient(90deg, var(--pg-grid) 1rpx, transparent 1rpx);
}
.pg-stage-themed .pg-stick-ring,
.pg-stage-themed .pg-view-ring { background: var(--pg-custom-fill, var(--pg-control-fill)); border-color: var(--pg-custom-border, var(--pg-control-border)); }
.pg-stage-themed .pg-stick-center { background: radial-gradient(circle, var(--pg-control-inner), var(--pg-stage-bottom)); }
.pg-stage-themed .pg-dpad-up,
.pg-stage-themed .pg-dpad-down,
.pg-stage-themed .pg-dpad-left,
.pg-stage-themed .pg-dpad-right {
  background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom)));
  border: 1rpx solid var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text));
}
.pg-stage-themed .pg-dpad-center { background: var(--pg-stage-bottom); }
.pg-stage-themed .pg-view-reticle,
.pg-stage-themed .pg-mouse-crosshair { background: var(--pg-accent); box-shadow: 0 0 8rpx var(--pg-accent); }
.pg-stage-themed .pg-mouse-track { background: var(--pg-control-fill); border: 2rpx dashed var(--pg-control-border); }
.pg-stage-themed .pg-control-caption { color: var(--pg-button-text); }
.pg-stage-bg-mobile-light .pg-control-caption { color: #315864; }
.pg-stage-bg-mobile-light .pg-abxy-y { background: linear-gradient(145deg, var(--pg-custom-fill, #ffe66d), var(--pg-custom-fill, #f7bb24)); color: var(--pg-custom-text, #173b61); }
.pg-stage-bg-mobile-light .pg-abxy-x { background: linear-gradient(145deg, var(--pg-custom-fill, #78b6ff), var(--pg-custom-fill, #4a83ef)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-bg-mobile-light .pg-abxy-a { background: linear-gradient(145deg, var(--pg-custom-fill, #69df9b), var(--pg-custom-fill, #2bbd75)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-bg-mobile-light .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, #ff8b91), var(--pg-custom-fill, #ed5d71)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed .pg-stick-key,
.pg-stage-themed .pg-dpad-key { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-button-bottom)); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
.pg-stage-themed .pg-abxy-y,
.pg-stage-themed .pg-abxy-x,
.pg-stage-themed .pg-abxy-a,
.pg-stage-themed .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, var(--pg-button-top)), var(--pg-custom-fill, var(--pg-button-bottom))); border-color: var(--pg-custom-border, var(--pg-button-border)); color: var(--pg-custom-text, var(--pg-button-text)); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-y { background: linear-gradient(145deg, var(--pg-custom-fill, #ffe66d), var(--pg-custom-fill, #f7bb24)); color: var(--pg-custom-text, #173b61); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-x { background: linear-gradient(145deg, var(--pg-custom-fill, #78b6ff), var(--pg-custom-fill, #4a83ef)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-a { background: linear-gradient(145deg, var(--pg-custom-fill, #69df9b), var(--pg-custom-fill, #2bbd75)); color: var(--pg-custom-text, #ffffff); }
.pg-stage-themed.pg-stage-bg-mobile-light .pg-abxy-b { background: linear-gradient(145deg, var(--pg-custom-fill, #ff8b91), var(--pg-custom-fill, #ed5d71)); color: var(--pg-custom-text, #ffffff); }

/* 空状态 */
.pg-empty-state {
  padding: 60rpx 24rpx;
  text-align: center;
}
.pg-empty-text { font-size: 24rpx; color: #64748b; }
</style>
