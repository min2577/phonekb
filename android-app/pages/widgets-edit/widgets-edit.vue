<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="topbar">
    <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">‹ 返回</view>
    <text class="topbar-title">编辑面板</text>
    <view class="topbar-action" hover-class="topbar-action-hover" @tap="onDone">
      <text class="topbar-action-text">完成</text>
    </view>
  </view>

  <view class="hint-section">
    <text class="hint-title">面板: {{ layoutName || "(未命名)" }}</text>
    <text class="hint-body">按住「☰」拖动可调整顺序 · 开关可隐藏组件 · 隐藏后不会在首页显示</text>
  </view>

  <view class="section">
    <view class="section-head">
      <text class="section-title">面板组件 ({{enabledCount}} / {{widgets.length}} 显示)</text>
      <text v-if="dirty" class="section-meta section-meta-dirty">未保存</text>
      <text v-else class="section-meta">已保存</text>
    </view>

    <view class="widget-list">
      <view v-for="(w, idx) in widgets" :key="w.id"
            class="widget-row"
            :class="{ 'is-dragging': dragState && dragState.fromIndex === idx }">
        <view class="widget-row-handle"
              hover-class="widget-row-handle-hover"
              @touchstart="onDragStart($event, idx)"
              @touchmove="onDragMove($event)"
              @touchend="onDragEnd"
              @touchcancel="onDragEnd">
          <text class="widget-row-handle-icon">☰</text>
        </view>
        <text class="widget-row-icon">{{w.icon}}</text>
        <view class="widget-row-info">
          <text class="widget-row-title">{{w.title}}</text>
          <text class="widget-row-type">{{w.type}}</text>
        </view>
        <switch class="widget-row-switch"
                :checked="w.visible !== false"
                :data-id="w.id"
                @change="onToggleVisible($event, w.id)" />
      </view>
    </view>
  </view>

  <view class="bottom-actions">
    <view class="bottom-btn bottom-btn-reset" hover-class="bottom-btn-reset-hover" @tap="onReset">
      <text class="bottom-btn-text">恢复默认</text>
    </view>
  </view>
</view>
</template>

<script>
import {
  loadLayouts,
  getCurrentLayoutId,
  reorderLayoutWidgets,
  setLayoutWidgetVisible,
} from '@/utils/layoutConfig.js'

const ROW_HEIGHT_RPX = 96
const RPX_TO_PX = 2

export default {
  data() {
    const layout = (loadLayouts().find(function (l) { return l.id === getCurrentLayoutId() }) || { widgets: [], id: '', name: '' })
    return {
      layoutId: layout.id,
      layoutName: layout.name,
      widgets: (layout.widgets || []).slice(),
      dragState: null,
    }
  },
  computed: {
    enabledCount() {
      return (this.widgets || []).filter(function (w) { return w && w.visible !== false }).length
    },
    dirty() {
      return !!this.dragState
    },
  },
  onUnload() {
    this.dragState = null
  },
  methods: {
    onBack() {
      uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
    },
    onDone() {
      if (!this.layoutId) {
        uni.showToast({ title: '面板不存在', icon: 'none', duration: 1000 })
        setTimeout(function () { uni.navigateBack({ delta: 1 }) }, 600)
        return
      }
      const ids = (this.widgets || []).map(function (w) { return w.id })
      reorderLayoutWidgets(this.layoutId, ids)
      uni.showToast({ title: '已保存', icon: 'success', duration: 1000 })
      setTimeout(function () {
        uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
      }, 600)
    },
    onReset() {
      const self = this
      if (!self.layoutId) return
      uni.showModal({
        title: '恢复默认',
        content: '将重置当前面板的组件顺序、可见性为初始状态,确定吗?',
        success: function (res) {
          if (!res.confirm) return
          const layouts = loadLayouts()
          const layout = layouts.find(function (l) { return l.id === self.layoutId })
          if (!layout) return
          // 重置顺序和可见性,但保留 type/id/title/icon
          self.widgets = (layout.widgets || []).map(function (w, i) {
            return Object.assign({}, w, { order: i, visible: true, collapsed: false })
          }).sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
          reorderLayoutWidgets(self.layoutId, self.widgets.map(function (w) { return w.id }))
          uni.showToast({ title: '已恢复', icon: 'success', duration: 1000 })
        },
      })
    },
    onToggleVisible(e, id) {
      if (!this.layoutId) return
      const val = !!(e && e.detail && e.detail.value)
      const list = this.widgets.slice()
      const idx = list.findIndex(function (w) { return w.id === id })
      if (idx < 0) return
      list.splice(idx, 1, Object.assign({}, list[idx], { visible: val }))
      this.widgets = list
      setLayoutWidgetVisible(this.layoutId, id, val)
    },
    onDragStart(e, idx) {
      const t = e && e.touches && e.touches[0]
      if (!t) return
      this.dragState = {
        fromIndex: idx,
        startClientY: t.clientY,
      }
      try { e.preventDefault && e.preventDefault() } catch (err) {}
    },
    onDragMove(e) {
      if (!this.dragState) return
      const t = e && e.touches && e.touches[0]
      if (!t) return
      const dy = t.clientY - this.dragState.startClientY
      const itemHeightPx = ROW_HEIGHT_RPX / RPX_TO_PX
      const steps = Math.round(dy / itemHeightPx)
      const target = Math.max(0, Math.min(this.widgets.length - 1, this.dragState.fromIndex + steps))
      if (target !== this.dragState.fromIndex) {
        const list = this.widgets.slice()
        const moved = list.splice(this.dragState.fromIndex, 1)[0]
        list.splice(target, 0, moved)
        this.widgets = list
        this.dragState.fromIndex = target
        this.dragState.startClientY = t.clientY
      }
      try { e.preventDefault && e.preventDefault() } catch (err) {}
    },
    onDragEnd() {
      if (!this.dragState) return
      if (this.layoutId) {
        const ids = this.widgets.map(function (w) { return w.id })
        reorderLayoutWidgets(this.layoutId, ids)
      }
      this.dragState = null
    },
  },
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding-bottom: 48rpx;
  background: #F4F8FD;
  color: #172033;
}
.topbar {
  min-height: 92rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,0.94);
  border-bottom: 1rpx solid #DCE6F1;
}
.topbar-back {
  min-width: 90rpx;
  color: #506177;
  font-size: 25rpx;
  font-weight: 600;
}
.topbar-back-hover {
  color: #2F78F6;
}
.topbar-title {
  color: #172033;
  font-size: 32rpx;
  font-weight: 750;
}
.topbar-action {
  min-width: 90rpx;
  text-align: right;
}
.topbar-action-text {
  color: #2F78F6;
  font-size: 25rpx;
  font-weight: 700;
}
.hint-section {
  margin: 24rpx 32rpx 0;
  padding: 18rpx 22rpx;
  border: 1rpx solid #D5E5FA;
  border-radius: 17rpx;
  background: #EAF3FF;
}
.hint-title {
  display: block;
  color: #315E96;
  font-size: 23rpx;
  font-weight: 700;
}
.hint-body {
  display: block;
  margin-top: 5rpx;
  color: #55708F;
  font-size: 20rpx;
  line-height: 1.45;
}
.section {
  margin: 24rpx;
  padding: 20rpx 22rpx 10rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 28rpx;
  box-shadow: 0 12rpx 30rpx rgba(47, 78, 113, 0.07);
}
.section-head {
  min-height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  color: #53657B;
  font-size: 23rpx;
  font-weight: 700;
}
.section-meta {
  color: #8996A7;
  font-size: 20rpx;
}
.section-meta-dirty {
  color: #D13438;
}
.widget-row {
  min-height: 98rpx;
  display: flex;
  align-items: center;
  border-top: 1rpx solid #E8EEF5;
}
.widget-row.is-dragging {
  opacity: 0.55;
  background: #EAF3FF;
}
.widget-row-handle {
  order: 5;
  width: 54rpx;
  height: 54rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13rpx;
  color: #91A0B2;
}
.widget-row-handle-hover {
  background: #EEF4FA;
  color: #2F78F6;
}
.widget-row-handle-icon {
  font-size: 28rpx;
}
.widget-row-icon {
  width: 50rpx;
  height: 50rpx;
  margin: 0 16rpx 0 4rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 24rpx;
}
.widget-row-info {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.widget-row-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.widget-row-type {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 20rpx;
}
.widget-row-switch {
  margin-right: 10rpx;
  transform: scale(0.82);
}
.bottom-actions {
  margin: 0 24rpx;
}
.bottom-btn {
  height: 70rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 16rpx;
  background: #FFFFFF;
}
.bottom-btn-reset-hover {
  background: #F7FAFE;
}
.bottom-btn-text {
  color: #607087;
  font-size: 24rpx;
  font-weight: 650;
}
</style>
