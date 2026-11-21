<template>
<view class="page">
  <view class="intro-card">
    <view class="intro-icon"><text class="intro-icon-text">＋</text></view>
    <view class="intro-copy">
      <text class="intro-title">添加选项卡</text>
      <text class="intro-sub">选择后会加入底部 Tab 栏，返回上一页仍可继续拖动排序</text>
    </view>
    <text class="intro-count">{{enabledCount + selectedKeys.length}} / {{maxTabs}}</text>
  </view>

  <view class="category-bar">
    <view v-for="cat in categories" :key="cat.key"
          :class="['category-item', activeCategory === cat.key ? 'on' : '']"
          @tap="activeCategory = cat.key">
      <text class="category-text">{{cat.title}}</text>
    </view>
  </view>

  <view class="option-grid">
    <view v-for="option in currentOptions" :key="option.key"
          :class="['option-card', isSelected(option) ? 'selected' : '', isAlreadyOn(option) ? 'disabled' : '']"
          hover-class="option-card-hover"
          @tap="onToggleOption(option)">
      <view class="option-preview">
        <view class="preview-status"><text>9:41</text><text>•••</text></view>
        <view class="preview-body">
          <view class="preview-icon"><text class="preview-icon-text">{{option.icon}}</text></view>
          <view class="preview-line"></view>
          <view class="preview-line preview-line-short"></view>
        </view>
        <view class="preview-tabs">
          <view class="preview-tab"></view><view class="preview-tab active"></view><view class="preview-tab"></view>
        </view>
        <view v-if="isAlreadyOn(option)" class="option-state option-state-on"><text>已添加</text></view>
        <view v-else-if="isSelected(option)" class="option-state option-state-selected"><text>✓</text></view>
        <view v-else class="option-state"><text>＋</text></view>
      </view>
      <text class="option-name">{{option.title}}</text>
      <text class="option-desc">{{option.description}}</text>
    </view>
  </view>

  <view class="bottom-bar">
    <view class="bottom-btn bottom-btn-ghost" @tap="onBack"><text>取消</text></view>
    <view :class="['bottom-btn', 'bottom-btn-primary', selectedKeys.length === 0 ? 'disabled' : '']" @tap="onConfirm">
      <text>添加{{selectedKeys.length ? ' (' + selectedKeys.length + ')' : ''}}</text>
    </view>
  </view>
</view>
</template>

<script>
import {
  ALL_OPTIONS,
  MAX_TABS,
  loadTabs,
  pickAddOption,
  syncBuiltIn,
} from '@/utils/tabConfig.js'

const TAB_DRAFT_KEY = 'phonekb.tab.config.draft'

export default {
  data() {
    return {
      tabs: [],
      selectedKeys: [],
      activeCategory: 'app',
      categories: [
        { key: 'app', title: '组件' },
        { key: 'other', title: '页面' },
      ],
      allOptions: ALL_OPTIONS,
      maxTabs: MAX_TABS,
    }
  },
  computed: {
    currentOptions() {
      const active = this.activeCategory
      return (this.allOptions || []).filter(function(option) { return option.group === active })
    },
    enabledCount() {
      return (this.tabs || []).filter(function(tab) { return tab && tab.enabled !== false }).length
    },
  },
  onLoad() {
    let source = null
    try { source = uni.getStorageSync(TAB_DRAFT_KEY) } catch (e) {}
    this.tabs = syncBuiltIn(Array.isArray(source) && source.length ? source : loadTabs())
  },
  methods: {
    isAlreadyOn(option) {
      return (this.tabs || []).some(function(tab) { return tab && tab.id === option.key && tab.enabled !== false })
    },
    isSelected(option) {
      return this.selectedKeys.indexOf(option.key) >= 0
    },
    onToggleOption(option) {
      if (!option || this.isAlreadyOn(option)) return
      const selected = this.selectedKeys.slice()
      const index = selected.indexOf(option.key)
      if (index >= 0) {
        selected.splice(index, 1)
      } else {
        if (this.enabledCount + selected.length >= this.maxTabs) {
          uni.showToast({ title: '最多只能显示 ' + this.maxTabs + ' 个 Tab', icon: 'none' })
          return
        }
        selected.push(option.key)
      }
      this.selectedKeys = selected
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onConfirm() {
      if (!this.selectedKeys.length) return
      let next = (this.tabs || []).map(function(tab) { return Object.assign({}, tab) })
      let maxOrder = next.reduce(function(max, tab) { return Math.max(max, Number(tab && tab.order) || 0) }, -1)
      const selected = this.selectedKeys.slice()
      for (let i = 0; i < selected.length; i++) {
        const key = selected[i]
        const option = (this.allOptions || []).find(function(item) { return item.key === key })
        if (!option) continue
        const existingIndex = next.findIndex(function(tab) { return tab && tab.id === key })
        if (existingIndex >= 0) {
          maxOrder += 1
          next[existingIndex] = Object.assign({}, next[existingIndex], {
            enabled: true,
            order: maxOrder,
            page: option.page || next[existingIndex].page,
            label: option.title || next[existingIndex].label,
            icon: option.icon || next[existingIndex].icon,
            widgetType: option.widgetType || '',
          })
        } else {
          const result = pickAddOption(next, option)
          next = result.tabs
          maxOrder = next.reduce(function(max, tab) { return Math.max(max, Number(tab && tab.order) || 0) }, maxOrder)
        }
      }
      try { uni.setStorageSync(TAB_DRAFT_KEY, next) } catch (e) {}
      uni.showToast({ title: '已加入编辑列表', icon: 'success', duration: 700 })
      setTimeout(function() { uni.navigateBack({ delta: 1 }) }, 180)
    },
    onBack() {
      uni.navigateBack({ delta: 1 })
    },
  },
}
</script>

<style>
.page {
  min-height: 100vh;
  padding: 24rpx 24rpx calc(150rpx + env(safe-area-inset-bottom));
  background: radial-gradient(82% 34% at 8% 0%, rgba(47,120,246,0.11), transparent 76%), var(--color-bg);
}
.intro-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 24rpx;
  background: rgba(255,255,255,0.94);
  border: 1rpx solid rgba(105,133,162,0.14);
  border-radius: 24rpx;
  box-shadow: var(--shadow-fluent-2);
}
.intro-icon {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 20rpx;
  background: var(--color-primary-bg);
}
.intro-icon-text { color: var(--color-primary); font-size: 40rpx; font-weight: 400; }
.intro-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6rpx; }
.intro-title { color: var(--color-text); font-size: 30rpx; font-weight: 700; }
.intro-sub { color: var(--color-text-mid); font-size: 22rpx; line-height: 1.45; }
.intro-count { color: var(--color-primary); font-size: 24rpx; font-weight: 700; }
.category-bar {
  display: flex;
  gap: 8rpx;
  margin: 22rpx 0 18rpx;
  padding: 6rpx;
  background: rgba(227,235,244,0.82);
  border-radius: 16rpx;
}
.category-item { flex: 1; padding: 14rpx 0; border-radius: 12rpx; text-align: center; }
.category-item.on { background: #FFFFFF; box-shadow: 0 4rpx 12rpx rgba(45,74,108,0.08); }
.category-text { color: var(--color-text-mid); font-size: 25rpx; font-weight: 600; }
.category-item.on .category-text { color: var(--color-primary); }
.option-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16rpx; }
.option-card {
  min-width: 0;
  padding: 14rpx;
  background: rgba(255,255,255,0.94);
  border: 1rpx solid rgba(105,133,162,0.14);
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(45,74,108,0.06);
  transition: transform 90ms var(--ease-fluent), border-color 120ms var(--ease-fluent);
}
.option-card-hover { transform: scale(0.98); }
.option-card.selected { border-color: var(--color-primary); box-shadow: 0 0 0 3rpx rgba(47,120,246,0.10), 0 10rpx 24rpx rgba(45,74,108,0.08); }
.option-card.disabled { opacity: 0.58; }
.option-preview {
  height: 204rpx;
  position: relative;
  overflow: hidden;
  background: #F4F8FD;
  border: 1rpx solid #DCE6F1;
  border-radius: 16rpx;
}
.preview-status { height: 34rpx; display: flex; align-items: center; justify-content: space-between; padding: 0 12rpx; color: #526175; font-size: 16rpx; }
.preview-body { height: 126rpx; margin: 0 10rpx; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #FFFFFF; border-radius: 12rpx; }
.preview-icon { width: 52rpx; height: 52rpx; display: flex; align-items: center; justify-content: center; border-radius: 14rpx; background: var(--color-primary-bg); }
.preview-icon-text { font-size: 28rpx; }
.preview-line { width: 92rpx; height: 9rpx; margin-top: 12rpx; border-radius: 999rpx; background: #DDE5EE; }
.preview-line-short { width: 58rpx; margin-top: 7rpx; }
.preview-tabs { height: 34rpx; display: flex; align-items: center; justify-content: center; gap: 16rpx; }
.preview-tab { width: 28rpx; height: 6rpx; border-radius: 999rpx; background: #D4DCE6; }
.preview-tab.active { background: var(--color-primary); }
.option-state { position: absolute; right: 10rpx; bottom: 10rpx; width: 40rpx; height: 40rpx; display: flex; align-items: center; justify-content: center; border-radius: 12rpx; background: #FFFFFF; color: var(--color-primary); border: 1rpx solid #DCE6F1; font-size: 24rpx; font-weight: 700; }
.option-state-selected { color: #FFFFFF; background: var(--color-primary); border-color: var(--color-primary); }
.option-state-on { width: auto; padding: 0 10rpx; color: var(--color-text-light); background: #EDF2F7; font-size: 18rpx; }
.option-name { display: block; margin-top: 12rpx; color: var(--color-text); font-size: 26rpx; font-weight: 700; }
.option-desc { display: block; margin-top: 4rpx; color: var(--color-text-mid); font-size: 20rpx; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bottom-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: 16rpx;
  padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  background: rgba(255,255,255,0.96);
  border-top: 1rpx solid rgba(105,133,162,0.12);
  box-shadow: 0 -12rpx 32rpx rgba(45,74,108,0.08);
}
.bottom-btn { height: 72rpx; display: flex; align-items: center; justify-content: center; border-radius: 16rpx; font-size: 27rpx; font-weight: 700; }
.bottom-btn-ghost { flex: 1; color: var(--color-text-mid); background: #F2F5F9; }
.bottom-btn-primary { flex: 2; color: #FFFFFF; background: var(--color-primary); box-shadow: 0 8rpx 18rpx rgba(47,120,246,0.20); }
.bottom-btn-primary.disabled { opacity: 0.45; box-shadow: none; }
</style>
