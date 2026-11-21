<template>
  <view class="section section-keys">
    <view v-if="!slots || slots.length === 0" class="empty-hint">这个页面还没有按键 · 去布局页添加</view>
    <view v-else class="key-grid" :class="'cols-' + (gridCols || 4)" :style="gridStyle">
      <view v-for="slot in visibleSlots" :key="slot.key.id"
            class="key-btn"
            :style="slotStyle(slot)"
            :data-id="slot.key.id"
            @touchstart="onSlotPressStart(slot)"
            @touchend="onSlotPressEnd(slot)"
            @touchcancel="onSlotPressEnd(slot)"
            @longpress="onSlotLongPress(slot)"
            @tap="onTriggerSlot" hover-class="key-btn-hover">
        <text class="key-label">{{truncateLabel(slot.key.label)}}</text>
        <text v-if="slot.key.sub" class="key-sub">{{truncateSub(slot.key.sub)}}</text>
      </view>
    </view>

    <!-- 布局/页面选择 modal -->
    <view v-if="showPicker" class="modal-mask" @tap="closePicker">
      <view class="modal layout-picker-modal" @tap.stop="">
        <view class="modal-head">
          <text class="modal-title">切换布局 / 页面</text>
        </view>
        <scroll-view class="modal-body" scroll-y="true">
          <view v-for="lay in layouts" :key="lay.id"
                :class="'layout-picker-item' + (lay.id === activeLayoutId ? ' on' : '')">
            <view class="layout-picker-row" hover-class="layout-picker-row-hover" @tap="onPickLayout(lay.id)">
              <view class="layout-picker-name">
                <text class="layout-picker-icon">{{lay.icon || '📋'}}</text>
                <text class="layout-picker-text">{{lay.name}}</text>
                <text class="layout-picker-badge">{{(lay.pages || []).length}} 页</text>
              </view>
            </view>
            <view v-if="lay.id === activeLayoutId" class="layout-picker-pages">
              <view v-for="page in lay.pages || []" :key="page.id"
                    :class="'layout-picker-page' + (page.id === activePageId ? ' on' : '')"
                    @tap="onPickPage(lay.id, page.id)">
                <text>{{page.icon || ''}} {{page.name}}</text>
              </view>
            </view>
          </view>
        </scroll-view>
        <view class="modal-foot">
          <view class="btn-cancel" @tap="closePicker">关闭</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import Net from "@/utils/net.js"

export default {
  name: "PanelKeyGrid",
  props: {
    slots: { type: Array, default: () => [] },
    gridCols: { type: Number, default: 4 },
    gridRows: { type: Number, default: 4 },
    layoutName: { type: String, default: "默认" },
    pageName: { type: String, default: "—" },
    layouts: { type: Array, default: () => [] },
    activeLayoutId: { type: String, default: "" },
    activePageId: { type: String, default: "" },
    preview: { type: Boolean, default: false },
  },
  emits: ["trigger", "pick-layout", "picker-visible-change"],
  data() {
    return {
      showPicker: false,
      heldShortcutSlots: {},
      suppressedTapIds: {},
    }
  },
  computed: {
    visibleSlots() {
      const rows = Math.max(1, Number(this.gridRows) || 4)
      const cols = Math.max(1, Number(this.gridCols) || 4)
      return (this.slots || []).filter(function(slot) {
        const row = Number(slot.r != null ? slot.r : slot.row) || 0
        const col = Number(slot.c != null ? slot.c : slot.col) || 0
        return row >= 0 && row < rows && col >= 0 && col < cols
      })
    },
    gridStyle() {
      return 'grid-template-rows: repeat(' + Math.max(1, Number(this.gridRows) || 4) + ', minmax(88rpx, 1fr));'
    },
  },
  beforeUnmount() {
    this.releaseAllShortcuts()
  },
  methods: {
    openPicker() {
      this.showPicker = true
      this.$emit("picker-visible-change", true)
    },
    closePicker() {
      this.showPicker = false
      this.$emit("picker-visible-change", false)
    },
    slotStyle(slot) {
      const row = Number(slot.r != null ? slot.r : slot.row) || 0
      const col = Number(slot.c != null ? slot.c : slot.col) || 0
      const rs = slot.rowspan || 1
      const cs = slot.colspan || 1
      return 'grid-column: ' + (col + 1) + ' / span ' + cs + '; grid-row: ' + (row + 1) + ' / span ' + rs
    },
    truncateLabel(s) {
      if (s == null) return ""
      const str = String(s)
      return str.length <= 4 ? str : str.slice(0, 4) + "…"
    },
    truncateSub(s) {
      if (s == null) return ""
      return String(s)
    },
    isShortcutSlot(slot) {
      return !!(slot && slot.key && slot.key.type === "shortcut" && slot.key.id)
    },
    isHoldableMouseSlot(slot) {
      const mouse = slot && slot.key && slot.key.mouse
      return !!(slot && slot.key && slot.key.id && slot.key.type === "mouse" && mouse
        && mouse.op === "click" && ["left", "right", "middle"].indexOf(mouse.button || "left") >= 0)
    },
    canSendShortcut() {
      return Net.getMode() === "ble" ? Net.canSendKeyboard() : Net.isConnected()
    },
    isCodexBindableSlot(slot) {
      const key = slot && slot.key
      const config = key && key.codex
      if (!key || key.type !== "codex" || !key.id || !config || config.action !== "focus_task") return false
      return config.long_press_action !== ""
    },
    onSlotPressStart(slot) {
      if (this.preview || (!this.isShortcutSlot(slot) && !this.isHoldableMouseSlot(slot)) || !this.canSendShortcut()) return
      const id = String(slot.key.id)
      if (this.heldShortcutSlots[id]) return
      const sent = this.isShortcutSlot(slot)
        ? Net.send({ action: "hold_slot", id: id, down: true, slot: slot })
        : Net.send({ action: "hold_mouse", id: id, down: true, button: slot.key.mouse.button })
      if (!sent) return
      this.heldShortcutSlots[id] = slot
      this.suppressedTapIds[id] = true
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
      this.$emit("trigger", slot)
    },
    onSlotPressEnd(slot) {
      if (!this.isShortcutSlot(slot) && !this.isHoldableMouseSlot(slot)) return
      const id = String(slot.key.id)
      if (!this.heldShortcutSlots[id]) return
      if (this.isShortcutSlot(slot)) Net.send({ action: "hold_slot", id: id, down: false, slot: slot })
      else Net.send({ action: "hold_mouse", id: id, down: false, button: slot.key.mouse.button })
      delete this.heldShortcutSlots[id]
      this.suppressedTapIds[id] = true
      const self = this
      setTimeout(function() { delete self.suppressedTapIds[id] }, 500)
    },
    onSlotLongPress(slot) {
      if (this.preview || !this.isCodexBindableSlot(slot)) return
      const id = String(slot.key.id)
      this.suppressedTapIds[id] = true
      const self = this
      setTimeout(function() { delete self.suppressedTapIds[id] }, 1000)
      if (!Net.isConnected()) {
        uni.showToast({ title: "请先连接电脑", icon: "none" })
        return
      }
      if (!Net.send({ action: "trigger_slot_long", id: id })) {
        uni.showToast({ title: "绑定请求发送失败", icon: "none" })
        return
      }
      try { uni.vibrateShort({ type: "medium" }) } catch (e) {}
    },
    releaseAllShortcuts() {
      const held = this.heldShortcutSlots || {}
      Object.keys(held).forEach(function(id) {
        const slot = held[id]
        if (this.isShortcutSlot(slot)) Net.send({ action: "hold_slot", id: id, down: false, slot: slot })
        else if (this.isHoldableMouseSlot(slot)) Net.send({ action: "hold_mouse", id: id, down: false, button: slot.key.mouse.button })
      })
      this.heldShortcutSlots = {}
    },
    onTriggerSlot(e) {
      if (this.preview) return
      const id = (e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id)
        || (e && e.target && e.target.dataset && e.target.dataset.id)
      if (!id) {
        uni.showToast({ title: "按钮数据异常", icon: "none" })
        return
      }
      if (this.suppressedTapIds[id]) {
        delete this.suppressedTapIds[id]
        return
      }
      if (!Net.isConnected()) {
        uni.showToast({ title: "未连接，点顶部状态条重连", icon: "none", duration: 1800 })
        return
      }
      const slot = (this.slots || []).find(function(x) { return x && x.key && x.key.id === id }) || null
      const sent = Net.triggerSlot(slot || id)
      if (sent) {
        try { uni.vibrateShort({ type: "light" }) } catch (e) {}
        this.$emit("trigger", slot)
      } else {
        uni.showToast({ title: "发送失败，请重连", icon: "none", duration: 1500 })
      }
    },
    onPickLayout(layoutId) {
      this.$emit("pick-layout", { layoutId: layoutId, pageId: null })
    },
    onPickPage(layoutId, pageId) {
      this.$emit("pick-layout", { layoutId: layoutId, pageId: pageId })
      this.closePicker()
    },
  },
}
</script>

<style>
/* ==========================================================================
 * PanelKeyGrid 全局样式 (非 scoped)
 *
 * 跟 PanelMouseControl 一样的原因: 原本写在 panel.vue 的 .panel-page 前缀下,
 * 但 panel 的 <style scoped> 选不中子组件内的节点, 导致 layout-picker 弹窗
 * 实际渲染时没有 position: fixed / z-index, 在 widget-slot 内联显示,
 * 其他 widget 卡片透出来看起来"乱七八糟"。
 *
 * 这里提供全局基础样式, z-index 1500 盖过所有 panel 内部元素。
 * ========================================================================== */

/* === Modal 容器 === */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(31,48,70,0.28);
  backdrop-filter: blur(12rpx);
  -webkit-backdrop-filter: blur(12rpx);
  z-index: 1500;
  display: flex; align-items: center; justify-content: center;
  padding: 48rpx;
}
.modal {
  width: 100%; max-width: 650rpx; max-height: 80vh;
  background: rgba(255,255,255,0.96);
  border: 1rpx solid rgba(122,145,169,0.18);
  border-radius: 26rpx;
  box-shadow: 0 24rpx 64rpx rgba(40,65,94,0.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-head { padding: 26rpx 28rpx 20rpx; }
.modal-title { color: #1E2B3C; font-size: 29rpx; font-weight: 600; }
.modal-body { padding: 8rpx 28rpx 20rpx; max-height: 70vh; flex: 1; }
.modal-foot { display: flex; gap: 12rpx; padding: 16rpx 28rpx 22rpx; }
.btn-cancel, .btn-save {
  min-width: 144rpx; padding: 17rpx 24rpx;
  border-radius: 12rpx; text-align: center;
  font-size: 24rpx; font-weight: 550;
}
.btn-cancel { color: #566579; background: #F2F5F8; flex: 1; }
.btn-save { color: #FFFFFF; background: linear-gradient(145deg, #2F78F6 0%, #5C9BFF 100%); flex: 1; }

/* === 布局/页面选择器 === */
.layout-picker-item { padding: 0; }
.layout-picker-item.on { /* no-op */ }
.layout-picker-row {
  display: flex; align-items: center;
  padding: 18rpx 8rpx;
  border-radius: 12rpx;
}
.layout-picker-row-hover { background: #F6FAFF; }
.layout-picker-name { display: flex; align-items: center; gap: 12rpx; flex: 1; }
.layout-picker-icon { font-size: 28rpx; }
.layout-picker-text { color: #1E2B3C; font-size: 26rpx; font-weight: 600; flex: 1; }
.layout-picker-badge { color: #8793A3; font-size: 22rpx; padding: 2rpx 10rpx; background: #F1F5F9; border-radius: 8rpx; }
.layout-picker-pages { padding: 0 0 0 60rpx; display: flex; flex-direction: column; gap: 4rpx; }
.layout-picker-page { padding: 14rpx 16rpx; color: #566579; font-size: 24rpx; border-radius: 10rpx; }
.layout-picker-page.on { background: linear-gradient(145deg, #EEF6FF 0%, #DBE9FB 100%); color: #2F78F6; font-weight: 600; }

/* === key-grid (PanelKeyGrid 主页) === */
.section-keys { padding: 14rpx 16rpx; }
.key-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10rpx;
}
.key-grid.cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.key-grid.cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.key-grid.cols-5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.key-btn {
  min-height: 88rpx;
  padding: 8rpx 6rpx;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #FFFFFF;
  border: 1rpx solid #DFE6EF;
  border-radius: 14rpx;
  color: #1E2B3C;
  box-shadow: 0 2rpx 6rpx rgba(43,72,106,0.05);
  text-align: center;
  box-sizing: border-box;
}
.key-btn-hover { background: #EEF6FF; border-color: rgba(47,120,246,0.45); }
.key-label { font-size: 26rpx; font-weight: 600; line-height: 1.1; }
.key-sub {
  max-width: 100%;
  margin-top: 3rpx;
  color: #8793A3;
  font-size: 18rpx;
  line-height: 1.15;
  text-align: center;
  white-space: normal;
  word-break: break-all;
}
.empty-hint { padding: 40rpx 20rpx; text-align: center; color: #8793A3; font-size: 24rpx; }

.app-appearance-active .layout-picker-modal {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.app-appearance-active .layout-picker-modal .modal-title,
.app-appearance-active .layout-picker-text,
.app-appearance-active .key-btn {
  color: var(--app-color-text);
}
.app-appearance-active .layout-picker-badge,
.app-appearance-active .layout-picker-page,
.app-appearance-active .key-sub,
.app-appearance-active .empty-hint {
  color: var(--app-color-text-mid);
}
.app-appearance-active .layout-picker-badge,
.app-appearance-active .layout-picker-modal .btn-cancel,
.app-appearance-active .key-btn {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
.app-appearance-active .layout-picker-row-hover,
.app-appearance-active .key-btn-hover {
  background: var(--app-color-primary-bg);
}
.app-appearance-active .layout-picker-page.on {
  background: var(--app-color-primary-bg);
  color: var(--app-color-primary);
}
</style>
