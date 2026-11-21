<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="topbar">
    <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">‹</view>
    <view class="topbar-center">
      <text class="topbar-title">组件管理</text>
      <text class="topbar-subtitle">点按编辑，长按调整顺序</text>
    </view>
    <view class="topbar-gear" hover-class="topbar-gear-hover" @tap="onTapGear">
      <text class="topbar-gear-icon">⚙</text>
    </view>
  </view>

  <!-- 已开启组件 -->
  <view class="section">
    <view class="section-head">
      <text class="section-title">已开启组件</text>
      <text class="section-meta">{{enabledWidgets.length}} 项</text>
    </view>
    <view class="widget-list">
      <view v-for="w in enabledWidgets" :key="w.id"
            class="widget-row"
            hover-class="widget-row-hover"
            @longpress="onLongPress(w.id, w.title)"
            @tap="onRowTap(w.id)">
        <view class="widget-toggle widget-toggle-on"
              hover-class="widget-toggle-hover"
              @tap.stop="onDisable(w.id, w.title)">
          <text class="widget-toggle-icon">−</text>
        </view>
        <text class="widget-icon">{{w.icon}}</text>
        <view class="widget-info">
          <text class="widget-title">{{w.title}}</text>
          <text class="widget-type">{{w.type}}</text>
        </view>
        <text class="widget-chevron">⌄</text>
      </view>
      <view v-if="enabledWidgets.length === 0" class="empty-row">
        <text class="empty-text">当前面板没有任何组件</text>
      </view>
    </view>
  </view>

  <!-- 已关闭组件 -->
  <view class="section">
    <view class="section-head">
      <text class="section-title">已关闭组件</text>
      <text class="section-meta">{{disabledMetas.length}} 项</text>
    </view>
    <view class="widget-list">
      <view v-for="m in disabledMetas" :key="m.type"
            class="widget-row"
            hover-class="widget-row-hover"
            @tap="onEnable(m)">
        <view class="widget-toggle widget-toggle-off"
              hover-class="widget-toggle-hover"
              @tap.stop="onEnable(m)">
          <text class="widget-toggle-icon">＋</text>
        </view>
        <text class="widget-icon">{{m.icon}}</text>
        <view class="widget-info">
          <text class="widget-title">{{m.title}}</text>
          <text class="widget-type">{{m.type}}</text>
        </view>
        <text class="widget-chevron">⌄</text>
      </view>
      <view v-if="disabledMetas.length === 0" class="empty-row">
        <text class="empty-text">所有组件都已启用 🎉</text>
      </view>
    </view>
  </view>
</view>
</template>


<script>
import {
  loadLayouts,
  getCurrentLayoutId,
  addWidgetToLayout,
  removeWidgetFromLayout,
} from '@/utils/layoutConfig.js'
import { widgetMeta, newWidgetInstance } from '@/utils/widgetRegistry.js'

export default {
  data() {
    return {
      layouts: [],
      currentLayoutId: '',
      widgetMeta: widgetMeta,
    }
  },
  computed: {
    currentLayout() {
      const self = this
      return (self.layouts || []).find(function (l) { return l.id === self.currentLayoutId }) || { id: '', name: '', widgets: [] }
    },
    layoutName() {
      return this.currentLayout.name
    },
    enabledWidgets() {
      return (this.currentLayout.widgets || []).slice().sort(function (a, b) {
        return (a.order || 0) - (b.order || 0)
      })
    },
    disabledMetas() {
      const enabledTypes = (this.enabledWidgets || []).map(function (w) { return w.type })
      return (this.widgetMeta || []).filter(function (m) {
        return enabledTypes.indexOf(m.type) < 0
      })
    },
  },
  onShow() {
    this.layouts = loadLayouts()
    this.currentLayoutId = getCurrentLayoutId()
  },
  methods: {
    onBack() {
      uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
    },
    onTapGear() {
      uni.navigateTo({ url: '/pages/widgets-edit/widgets-edit' })
    },
    onRowTap(id) {
      uni.navigateTo({ url: '/pages/widgets-edit/widgets-edit' })
    },
    onLongPress(id, title) {
      uni.showModal({
        title: '调整顺序',
        content: '去「编辑面板」拖动排序?',
        confirmText: '去编辑',
        success: function (res) {
          if (res.confirm) uni.navigateTo({ url: '/pages/widgets-edit/widgets-edit' })
        },
      })
    },
    onEnable(m) {
      if (!this.currentLayoutId) {
        uni.showToast({ title: '面板不存在', icon: 'none' })
        return
      }
      const inst = newWidgetInstance(m.type)
      if (!inst) {
        uni.showToast({ title: '组件不存在', icon: 'none' })
        return
      }
      const ok = addWidgetToLayout(this.currentLayoutId, inst)
      if (ok) {
        this.layouts = loadLayouts()
        uni.showToast({ title: '已启用 ' + m.title, icon: 'success', duration: 800 })
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        uni.showToast({ title: '已存在', icon: 'none' })
      }
    },
    onDisable(id, title) {
      const self = this
      if (!this.currentLayoutId) return
      uni.showModal({
        title: '关闭组件',
        content: '从「' + (this.layoutName || '当前面板') + '」关闭「' + (title || '组件') + '」?',
        confirmText: '关闭',
        success: function (res) {
          if (!res.confirm) return
          removeWidgetFromLayout(self.currentLayoutId, id)
          self.layouts = loadLayouts()
          uni.showToast({ title: '已关闭', icon: 'success', duration: 600 })
        },
      })
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
.topbar-back,
.topbar-gear {
  width: 64rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #506177;
  font-size: 36rpx;
}
.topbar-back-hover,
.topbar-gear-hover {
  color: #2F78F6;
}
.topbar-center {
  display: flex;
  align-items: center;
  flex-direction: column;
}
.topbar-title {
  color: #172033;
  font-size: 31rpx;
  font-weight: 750;
}
.topbar-subtitle {
  margin-top: 2rpx;
  color: #8996A7;
  font-size: 18rpx;
}
.topbar-gear-icon {
  font-size: 27rpx;
}
.section {
  margin: 24rpx 24rpx 0;
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
  padding: 4rpx 11rpx;
  border-radius: 999rpx;
  background: #EEF4FA;
  color: #718196;
  font-size: 19rpx;
  font-weight: 650;
}
.widget-row {
  min-height: 96rpx;
  display: flex;
  align-items: center;
  border-top: 1rpx solid #E8EEF5;
}
.widget-row-hover {
  background: #F7FAFE;
}
.widget-toggle {
  width: 42rpx;
  height: 42rpx;
  margin-right: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}
.widget-toggle-on {
  background: #FDE7E9;
  color: #D13438;
}
.widget-toggle-off {
  background: #EAF8EF;
  color: #159447;
}
.widget-toggle-hover {
  transform: scale(0.94);
}
.widget-toggle-icon {
  font-size: 25rpx;
  font-weight: 750;
}
.widget-icon {
  width: 50rpx;
  height: 50rpx;
  margin-right: 15rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 23rpx;
}
.widget-info {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.widget-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.widget-type {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 20rpx;
}
.widget-chevron {
  color: #91A0B2;
  font-size: 26rpx;
}
.empty-row {
  padding: 40rpx 0;
  border-top: 1rpx solid #E8EEF5;
  text-align: center;
}
.empty-text {
  color: #8996A7;
  font-size: 22rpx;
}
</style>
