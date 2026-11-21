﻿<template>
  <view class="fkb" :class="{ 'is-fullscreen': isFullscreen, 'is-typing-compact': typingCompact }" @tap="onContainerTap">
    <view v-if="!isFullscreen" class="fkb-tap-hint">
      <text class="fkb-tap-hint-text">点击展开大键盘</text>
    </view>

    <!-- 全屏头部（无标题，只保留收起/关闭按钮，避免和大键盘重叠） -->
    <view v-if="isFullscreen" class="fkb-fs-head">
      <view class="fkb-fs-actions">
        <view v-if="!typingCompact" class="fkb-fs-toggle" hover-class="fkb-fs-toggle-hover"
              aria-label="展开或收起快捷键行" @tap.stop="toggleCustomRow">
          <text class="fkb-fs-toggle-icon">{{ customRowIcon }}</text>
        </view>
        <view class="fkb-fs-toggle fkb-layout-toggle" hover-class="fkb-fs-toggle-hover"
              :aria-label="typingCompact ? '展开完整键盘' : '收起为打字键盘'"
              @tap.stop="toggleTypingLayout">
          <text class="fkb-fs-toggle-icon">{{ typingLayoutIcon }}</text>
        </view>
        <view class="fkb-close" hover-class="fkb-close-hover" @tap.stop="onCollapse">
          <text class="fkb-close-icon">×</text>
        </view>
      </view>
    </view>

    <!-- 快捷键行（F 行上方，跟着大键盘一起旋转） -->
    <view class="fkb-board">
      <view v-if="isFullscreen && customRowExpanded && !typingCompact" class="fkb-custom-row">
        <view v-for="ck in customKeys" :key="ck.id"
              class="fkb-custom-btn"
              :class="{ 'is-pressed': !!heldCustomKeys[ck.id] }"
              hover-class="fkb-custom-btn-hover"
              @touchstart="onCustomKeyDown(ck)"
              @touchend="onCustomKeyUp(ck)"
              @touchcancel="onCustomKeyUp(ck)"
              @tap.stop="onCustomKeyTap(ck)">
          <text class="fkb-custom-btn-label">{{ ck.label }}</text>
        </view>
      </view>
      <view v-for="(row, ri) in visibleRows" :key="ri" class="fkb-row">
        <view v-for="key in row" :key="key.id"
              class="fkb-key"
              :class="[keyClass(key), { 'is-pressed': !!heldKeys[key.id] }]"
              :style="keyStyle(key)"
              :data-id="key.id"
              hover-class="fkb-key-hover"
              @touchstart="onKeyDown(key)"
              @touchend="onKeyUp(key)"
              @touchcancel="onKeyUp(key)"
              @tap.stop="onKeyTap(key)">
          <text class="fkb-key-label">{{ key.label }}</text>
        </view>
      </view>
    </view>

  </view>
</template>


<script>
import Net from '@/utils/net.js'
import { lockLandscape, lockPortrait } from '@/utils/orientation.js'

// 标准 104 键 PC 键盘布局
const PC_KEYBOARD = [
  [
    { id: 'esc', label: 'Esc', w: 1 },
    { id: 'f1', label: 'F1', w: 1 }, { id: 'f2', label: 'F2', w: 1 }, { id: 'f3', label: 'F3', w: 1 }, { id: 'f4', label: 'F4', w: 1 },
    { id: 'f5', label: 'F5', w: 1 }, { id: 'f6', label: 'F6', w: 1 }, { id: 'f7', label: 'F7', w: 1 }, { id: 'f8', label: 'F8', w: 1 },
    { id: 'f9', label: 'F9', w: 1 }, { id: 'f10', label: 'F10', w: 1 }, { id: 'f11', label: 'F11', w: 1 }, { id: 'f12', label: 'F12', w: 1 },
  ],
  [
    { id: '`', label: '`', w: 1 }, { id: '1', label: '1', w: 1 }, { id: '2', label: '2', w: 1 }, { id: '3', label: '3', w: 1 },
    { id: '4', label: '4', w: 1 }, { id: '5', label: '5', w: 1 }, { id: '6', label: '6', w: 1 }, { id: '7', label: '7', w: 1 },
    { id: '8', label: '8', w: 1 }, { id: '9', label: '9', w: 1 }, { id: '0', label: '0', w: 1 },
    { id: '-', label: '-', w: 1 }, { id: '=', label: '=', w: 1 },
    { id: 'bksp', label: '⌫', w: 1, sub: 'Backspace' },
  ],
  [
    { id: 'tab', label: 'Tab', w: 1 },
    { id: 'q', label: 'Q', w: 1 }, { id: 'w', label: 'W', w: 1 }, { id: 'e', label: 'E', w: 1 }, { id: 'r', label: 'R', w: 1 },
    { id: 't', label: 'T', w: 1 }, { id: 'y', label: 'Y', w: 1 }, { id: 'u', label: 'U', w: 1 }, { id: 'i', label: 'I', w: 1 },
    { id: 'o', label: 'O', w: 1 }, { id: 'p', label: 'P', w: 1 },
    { id: '[', label: '[', w: 1 }, { id: ']', label: ']', w: 1 },
    { id: '\\', label: '\\', w: 1 },
  ],
  [
    { id: 'caps', label: 'Caps', w: 1 },
    { id: 'a', label: 'A', w: 1 }, { id: 's', label: 'S', w: 1 }, { id: 'd', label: 'D', w: 1 }, { id: 'f', label: 'F', w: 1 },
    { id: 'g', label: 'G', w: 1 }, { id: 'h', label: 'H', w: 1 }, { id: 'j', label: 'J', w: 1 }, { id: 'k', label: 'K', w: 1 },
    { id: 'l', label: 'L', w: 1 },
    { id: ';', label: ';', w: 1 }, { id: "'", label: "'", w: 1 },
    { id: 'enter', label: 'Enter', w: 2 },
  ],
  [
    { id: 'lshift', label: 'Shift', w: 2 },
    { id: 'z', label: 'Z', w: 1 }, { id: 'x', label: 'X', w: 1 }, { id: 'c', label: 'C', w: 1 }, { id: 'v', label: 'V', w: 1 },
    { id: 'b', label: 'B', w: 1 }, { id: 'n', label: 'N', w: 1 }, { id: 'm', label: 'M', w: 1 },
    { id: ',', label: ',', w: 1 }, { id: '.', label: '.', w: 1 }, { id: '/', label: '/', w: 1 },
    { id: 'rshift', label: 'Shift', w: 2 },
  ],
  [
    { id: 'lctrl', label: 'Ctrl', w: 1 },
    { id: 'lwin', label: 'Win', w: 1 },
    { id: 'lalt', label: 'Alt', w: 1 },
    { id: 'space', label: 'Space', w: 6 },
    { id: 'ralt', label: 'Alt', w: 1 },
    { id: 'rwin', label: 'Win', w: 1 },
    { id: 'menu', label: 'Menu', w: 1 },
    { id: 'rctrl', label: 'Ctrl', w: 1 },
  ],
]

// 横向收起后的手机输入法式布局，只保留文字输入所需按键。
const TYPING_KEYBOARD = [
  [
    { id: 'q', label: 'Q' }, { id: 'w', label: 'W' }, { id: 'e', label: 'E' }, { id: 'r', label: 'R' }, { id: 't', label: 'T' },
    { id: 'y', label: 'Y' }, { id: 'u', label: 'U' }, { id: 'i', label: 'I' }, { id: 'o', label: 'O' }, { id: 'p', label: 'P' },
  ],
  [
    { id: 'a', label: 'A' }, { id: 's', label: 'S' }, { id: 'd', label: 'D' }, { id: 'f', label: 'F' }, { id: 'g', label: 'G' },
    { id: 'h', label: 'H' }, { id: 'j', label: 'J' }, { id: 'k', label: 'K' }, { id: 'l', label: 'L' },
  ],
  [
    { id: 'lshift', label: 'Shift', w: 1.35 },
    { id: 'z', label: 'Z' }, { id: 'x', label: 'X' }, { id: 'c', label: 'C' }, { id: 'v', label: 'V' },
    { id: 'b', label: 'B' }, { id: 'n', label: 'N' }, { id: 'm', label: 'M' },
    { id: 'bksp', label: '⌫', w: 1.35 },
  ],
  [
    { id: 'caps', label: '大小写', w: 1.4 },
    { id: ',', label: ',', w: 1 },
    { id: 'space', label: '空格', w: 4.2 },
    { id: '.', label: '.', w: 1 },
    { id: 'enter', label: 'Enter', w: 1.6 },
  ],
]

export default {
  name: 'PanelFullKeyboard',
  emits: ['fullscreen-change', 'open-request'],
  props: {
    forceExpand: { type: Boolean, default: false },
    preview: { type: Boolean, default: false },
  },
  data() {
    return {
      expanded: false,
      customRowExpanded: true,
      typingCompact: false,
      heldKeys: {},
      heldCustomKeys: {},
      rows: PC_KEYBOARD,
      customKeys: [
        { id: 'volup', label: '音量+', kind: 'consumer', key: 'volume_up' },
        { id: 'voldn', label: '音量-', kind: 'consumer', key: 'volume_down' },
        { id: 'mute', label: '静音', kind: 'consumer', key: 'mute' },
        { id: 'copy', label: '复制', modifiers: ['ctrl'], key: 'c' },
        { id: 'paste', label: '粘贴', modifiers: ['ctrl'], key: 'v' },
        { id: 'undo', label: '撤销', modifiers: ['ctrl'], key: 'z' },
        { id: 'screenshot', label: '截图', modifiers: ['win', 'shift'], key: 's' },
        { id: 'lock', label: '锁屏', modifiers: ['win'], key: 'l' },
      ],
    }
  },
  computed: {
    isFullscreen() {
      return this.expanded || this.forceExpand
    },
    customRowIcon() {
      return this.customRowExpanded ? '⌄' : '⌃'
    },
    typingLayoutIcon() {
      return this.typingCompact ? '⇥' : '⇤'
    },
    visibleRows() {
      return this.typingCompact ? TYPING_KEYBOARD : this.rows
    },
  },
  beforeUnmount() {
    this.releaseAllKeys()
    if (this.expanded) {
      lockPortrait()
      this._setFullscreen(false)
    }
  },
  methods: {
    _setFullscreen(on) {
      try {
        if (typeof plus !== 'undefined' && plus.navigator && typeof plus.navigator.setFullscreen === 'function') {
          plus.navigator.setFullscreen(!!on)
        }
      } catch (e) {}
      this.$emit('fullscreen-change', !!on)
    },
    keyClass(key) {
      const cls = []
      if ((key.w || 1) === 2) cls.push('fkb-key-wide')
      if ((key.w || 1) >= 4) cls.push('fkb-key-xwide')
      if (key.id === 'space') cls.push('fkb-key-space')
      return cls.join(' ')
    },
    keyStyle(key) {
      const width = key.w || 1
      if (this.typingCompact) {
        return { flexGrow: width, flexBasis: 0 }
      }
      return { gridColumn: 'span ' + width }
    },
    onShow() {
      if (this.preview) return
      lockLandscape()
      this.expanded = true
      this._setFullscreen(true)
    },
    onContainerTap() {
      if (this.preview) return
      if (this.isFullscreen) return
      lockLandscape()
      this.expanded = true
      this._setFullscreen(true)
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onCollapse() {
      this.releaseAllKeys()
      lockPortrait()
      this.expanded = false
      this._setFullscreen(false)
    },
    toggleCustomRow() {
      this.customRowExpanded = !this.customRowExpanded
    },
    toggleTypingLayout() {
      this.releaseAllKeys()
      this.typingCompact = !this.typingCompact
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    customKeyMessage(ck, down) {
      if (ck.kind === 'consumer') {
        return { action: 'consumer_key', key: ck.key, name: ck.id, down: down }
      }
      return {
        action: 'keyboard_shortcut',
        modifiers: ck.modifiers || [],
        key: ck.key || '',
        name: ck.id,
        down: down,
      }
    },
    onCustomKeyDown(ck) {
      if (this.preview || Net.getMode() !== 'ble') return
      const id = (ck && ck.id) || ''
      if (!id || this.heldCustomKeys[id]) return
      const ok = Net.canSendKeyboard() ? Net.send(this.customKeyMessage(ck, true)) : false
      if (ok) {
        this.heldCustomKeys = Object.assign({}, this.heldCustomKeys, { [id]: ck })
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        try { uni.showToast({ title: '未连接', icon: 'none', duration: 1000 }) } catch (e) {}
      }
    },
    onCustomKeyUp(ck) {
      const id = (ck && ck.id) || ''
      if (!id || !this.heldCustomKeys[id]) return
      Net.send(this.customKeyMessage(ck, false))
      const next = Object.assign({}, this.heldCustomKeys)
      delete next[id]
      this.heldCustomKeys = next
    },
    onCustomKeyTap(ck) {
      if (this.preview || Net.getMode() === 'ble') return
      const id = (ck && ck.id) || ''
      if (!id) return
      const ok = Net.isConnected() ? Net.send({ action: 'shortcut', name: id }) : false
      if (ok) {
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        try { uni.showToast({ title: '未连接', icon: 'none', duration: 1000 }) } catch (e) {}
      }
    },
    onKeyDown(key) {
      if (this.preview || Net.getMode() !== 'ble') return
      const id = (key && key.id) || ''
      if (!id || this.heldKeys[id]) return
      const keyName = id === 'bksp' ? 'backspace' : id
      const ok = Net.canSendKeyboard()
        ? Net.send({ action: 'keyboard_key', key: keyName, down: true })
        : false
      if (ok) {
        this.heldKeys = Object.assign({}, this.heldKeys, { [id]: keyName })
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        try { uni.showToast({ title: '未连接', icon: 'none', duration: 1000 }) } catch (e) {}
      }
    },
    onKeyUp(key) {
      const id = (key && key.id) || ''
      if (!id || !this.heldKeys[id]) return
      Net.send({ action: 'keyboard_key', key: this.heldKeys[id], down: false })
      const next = Object.assign({}, this.heldKeys)
      delete next[id]
      this.heldKeys = next
    },
    onKeyTap(key) {
      if (this.preview || Net.getMode() === 'ble') return
      const id = (key && key.id) || ''
      if (!id) return
      const keyName = id === 'bksp' ? 'backspace' : id
      const ok = Net.send({ action: 'simulate_key', modifiers: [], key: keyName })
      if (ok) {
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        try { uni.showToast({ title: '未连接', icon: 'none', duration: 1000 }) } catch (e) {}
      }
    },
    releaseAllKeys() {
      const heldKeys = this.heldKeys || {}
      Object.keys(heldKeys).forEach(function(id) {
        Net.send({ action: 'keyboard_key', key: heldKeys[id], down: false })
      })
      const self = this
      const heldCustomKeys = this.heldCustomKeys || {}
      Object.keys(heldCustomKeys).forEach(function(id) {
        Net.send(self.customKeyMessage(heldCustomKeys[id], false))
      })
      this.heldKeys = {}
      this.heldCustomKeys = {}
    },
  },
}

</script>

<style scoped>
.fkb {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  padding: 6rpx;
  box-sizing: border-box;
  overflow: hidden;
  background: #F4F8FD;
  position: relative;
}
.fkb.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #F4F8FD;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.fkb-tap-hint {
  padding: 6rpx 12rpx 0;
  color: #8793A3;
  font-size: 20rpx;
  text-align: center;
}
.fkb-board {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  flex: 1;
  min-height: 0;
}
.fkb.is-fullscreen .fkb-board {
  gap: 8rpx;
  position: fixed;
  inset: 0;
  width: auto;
  height: auto;
  padding: 88rpx 24rpx 24rpx;
  box-sizing: border-box;
}

@media (orientation: portrait) {
  .fkb.is-fullscreen .fkb-board {
    inset: auto;
    top: 50%;
    left: 50%;
    width: 100vh;
    height: 100vw;
    padding: 24rpx 24rpx 24rpx 96rpx;
    transform: translate(-50%, -50%) rotate(90deg);
    transform-origin: center center;
  }
}

.fkb-row {
  display: grid;
  grid-template-columns: repeat(14, minmax(0, 1fr));
  gap: 4rpx;
  flex: 1;
  min-height: 0;
}
.fkb.is-fullscreen .fkb-row { gap: 6rpx; }
.fkb.is-fullscreen.is-typing-compact .fkb-board {
  gap: 10rpx;
  padding-left: 40rpx;
  padding-right: 40rpx;
}
.fkb.is-typing-compact .fkb-row {
  display: flex;
  gap: 8rpx;
}
.fkb.is-typing-compact .fkb-row:nth-child(2) {
  padding-left: 5%;
  padding-right: 5%;
}
.fkb.is-typing-compact .fkb-key {
  box-shadow: 0 3rpx 0 rgba(39, 55, 74, 0.1);
}
.fkb.is-typing-compact .fkb-key-wide .fkb-key-label,
.fkb.is-typing-compact .fkb-key-space .fkb-key-label {
  font-size: 22rpx;
}
.fkb-key {
  min-width: 0;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #FFFFFF;
  border: 1rpx solid #DCE4EE;
  border-radius: 6rpx;
  color: #1E2B3C;
  font-weight: 500;
  user-select: none;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fkb.is-fullscreen .fkb-key { border-radius: 10rpx; }
.fkb-key-hover {
  background: #EEF6FF;
  border-color: rgba(47, 120, 246, 0.45);
}
.fkb-key.is-pressed,
.fkb-custom-btn.is-pressed {
  background: #DDEBFC;
  border-color: rgba(47, 120, 246, 0.7);
}
.fkb-key-label {
  font-size: 16rpx;
  line-height: 1.1;
}
.fkb.is-fullscreen .fkb-key-label { font-size: 22rpx; }
.fkb-key-wide .fkb-key-label { font-size: 14rpx; }
.fkb.is-fullscreen .fkb-key-wide .fkb-key-label { font-size: 20rpx; }
.fkb-key-space .fkb-key-label { color: #8793A3; font-size: 14rpx; }
.fkb.is-fullscreen .fkb-key-space .fkb-key-label { font-size: 20rpx; }

.fkb-close {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid #DCE6F1;
  border-radius: 18rpx;
  z-index: 1;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
}
.fkb-fs-head {
  position: absolute;
  top: 24rpx;
  left: 24rpx;
  right: 24rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  z-index: 3;
  pointer-events: none;
}
.fkb-fs-actions { display: flex; gap: 8rpx; pointer-events: auto; }
.fkb-fs-toggle {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid #DCE6F1;
  border-radius: 18rpx;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
}
.fkb-fs-toggle-hover { background: #EEF5FD; }
.fkb-fs-toggle-icon { font-size: 24rpx; color: #526175; line-height: 1; }
.fkb-custom-row {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 6rpx;
  padding: 0 4rpx;
}
.fkb-custom-btn {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid #DCE6F1;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.06);
}
.fkb-close-icon { font-size: 36rpx; color: #526175; line-height: 1; }
.fkb-custom-btn-hover { background: #EEF6FF; border-color: rgba(47, 120, 246, 0.45); }
.fkb-custom-btn-label { color: #1E2B3C; font-size: 24rpx; font-weight: 500; }

/* In landscape, rpx follows the long edge. Use the short edge to preserve the original proportions. */
@media (orientation: landscape) {
  .fkb.is-fullscreen .fkb-board {
    gap: 1.067vh;
    padding: 11.733vh 3.2vh 3.2vh;
  }
  .fkb.is-fullscreen .fkb-row { gap: 0.8vh; }
  .fkb.is-fullscreen.is-typing-compact .fkb-board {
    gap: 1.333vh;
    padding-left: 5.333vh;
    padding-right: 5.333vh;
  }
  .fkb.is-fullscreen.is-typing-compact .fkb-row { gap: 1.067vh; }
  .fkb.is-fullscreen.is-typing-compact .fkb-key-label,
  .fkb.is-fullscreen.is-typing-compact .fkb-key-wide .fkb-key-label,
  .fkb.is-fullscreen.is-typing-compact .fkb-key-space .fkb-key-label {
    font-size: 3.2vh;
  }
  .fkb.is-fullscreen .fkb-key {
    border-width: 0.133vh;
    border-radius: 1.333vh;
  }
  .fkb.is-fullscreen .fkb-key-label { font-size: 2.933vh; }
  .fkb.is-fullscreen .fkb-key-wide .fkb-key-label,
  .fkb.is-fullscreen .fkb-key-space .fkb-key-label { font-size: 2.667vh; }
  .fkb.is-fullscreen .fkb-fs-head {
    top: 3.2vh;
    left: 3.2vh;
    right: 3.2vh;
    height: 7.467vh;
  }
  .fkb.is-fullscreen .fkb-fs-actions { gap: 1.067vh; }
  .fkb.is-fullscreen .fkb-close,
  .fkb.is-fullscreen .fkb-fs-toggle {
    width: 7.467vh;
    height: 7.467vh;
    border-width: 0.133vh;
    border-radius: 2.4vh;
    box-shadow: 0 0.533vh 1.6vh rgba(0, 0, 0, 0.08);
  }
  .fkb.is-fullscreen .fkb-close-icon { font-size: 4.8vh; }
  .fkb.is-fullscreen .fkb-fs-toggle-icon { font-size: 3.2vh; }
  .fkb.is-fullscreen .fkb-custom-row {
    gap: 0.8vh;
    padding: 0 0.533vh;
  }
  .fkb.is-fullscreen .fkb-custom-btn {
    border-width: 0.133vh;
    border-radius: 1.6vh;
    box-shadow: 0 0.533vh 1.6vh rgba(0, 0, 0, 0.06);
  }
  .fkb.is-fullscreen .fkb-custom-btn-label { font-size: 3.2vh; }
}

</style>

<style>
.app-appearance-active .fkb,
.app-appearance-active .fkb.is-fullscreen {
  background: var(--app-surface) !important;
}
.app-appearance-active .fkb-key,
.app-appearance-active .fkb-close,
.app-appearance-active .fkb-fs-toggle,
.app-appearance-active .fkb-custom-btn {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.app-appearance-active .fkb-key,
.app-appearance-active .fkb-custom-btn-label {
  color: var(--app-color-text);
}
.app-appearance-active .fkb-tap-hint,
.app-appearance-active .fkb-key-space .fkb-key-label,
.app-appearance-active .fkb-close-icon,
.app-appearance-active .fkb-fs-toggle-icon {
  color: var(--app-color-text-mid);
}
.app-appearance-active .fkb-key-hover,
.app-appearance-active .fkb-fs-toggle-hover,
.app-appearance-active .fkb-custom-btn-hover {
  background: var(--app-color-primary-bg);
  border-color: var(--app-color-primary);
}
</style>
