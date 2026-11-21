<template>
  <view v-if="visibleItems.length > 0"
        :class="['custom-tabbar', variant === 'panel' ? 'panel-tabbar' : '']">
    <view v-for="(t, idx) in visibleItems" :key="t.id"
          :class="['tab-item', isActive(t) ? 'active' : '']"
          :data-page="t.page"
          @tap="onTap(t)">
      <text class="tab-icon">{{displayIcon(t)}}</text>
      <text class="tab-label">{{displayLabel(t)}}</text>
    </view>
  </view>
</template>

<script>
import Net from '@/utils/net.js'
import { loadLayouts, setCurrentLayoutId } from '@/utils/layoutConfig.js'
// 跟 tab-config.vue 共用同一份读 + 清理逻辑,避免首页显示脏数据
import { loadTabs as loadTabsFromStore, syncLayoutTabs, TAB_UPDATED_EVENT } from '@/utils/tabConfig.js'

export default {
  name: 'CustomTabBar',
  props: {
    variant: { type: String, default: '' },
  },
  data() {
    return {
      // 内置兜底:storage 空时保证至少能看到 Tab 栏。
      // mounted 里会立即用 util.loadTabsFromStore() 覆盖,带 dedup + p-profile 修正。
      tabs: [
        { id: "p-panel",   page: "panel",   label: "面板", icon: "🎛", order: 0, enabled: true },
        { id: "p-layout",  page: "layout",  label: "布局", icon: "📐", order: 1, enabled: true },
        { id: "p-profile", page: "profile", label: "我的", icon: "👤", order: 2, enabled: true },
      ],
      currentPage: '',
      activeTabId: '',
    }
  },
  computed: {
    visibleItems() {
      return (this.tabs || [])
        .filter(function(t) { return t && t.enabled !== false })
        .slice()
        .sort(function(a, b) { return (a.order || 0) - (b.order || 0) })
    },
  },
  mounted() {
    const self = this

    this._reloadTabs()

    // 订阅 tab-config 保存后的全局事件(uni.$on 在 Vue 3 下不一定可靠,只是辅助)
    try {
      uni.$on && uni.$on(TAB_UPDATED_EVENT, function (tabs) {
        if (Array.isArray(tabs) && tabs.length > 0) self.tabs = tabs
      })
    } catch (e) {}

    // 与 PC 端推送的 panel schemes 兼容
    self._unsub = Net.onPanelSchemes(function(d) {
      if (d && Array.isArray(d.tab_config)) {
        try { self.tabs = loadTabsFromStore() } catch (e) { self.tabs = d.tab_config }
      }
    })

    // 计算当前页:从页面栈取最后一个
    try {
      self.activeTabId = uni.getStorageSync('phonekb.activeTabId') || ''
      const pages = getCurrentPages()
      if (pages && pages.length) {
        const cur = pages[pages.length - 1]
        if (cur && cur.route) self.currentPage = cur.route
      }
    } catch (e) {}

    // 原生 tabBar 与自定义 TabBar 不能同时显示。部分 Android 基座在
    // reLaunch/横竖屏切换后会异步恢复原生栏，因此在挂载后的几个时点再确认一次。
    this._hideNativeTabBar()
  },
  beforeUnmount() {
    if (this._unsub) this._unsub()
    try { uni.$off && uni.$off(TAB_UPDATED_EVENT) } catch (e) {}
  },
  // 父页面生命周期:从隐藏切回显示时重新拉数据
  pageLifetimes: {
    show() {
      // 父页面回到前台时(包括 navigateBack 回来),立即刷新 tab 配置
      this._reloadTabs()
      try { this.activeTabId = uni.getStorageSync('phonekb.activeTabId') || '' } catch (e) {}
    },
    hide() {},
  },
  methods: {
    _hideNativeTabBar() {
      const hide = function () {
        try { uni.hideTabBar({ animation: false }) } catch (e) {}
      }
      hide()
      setTimeout(hide, 80)
      setTimeout(hide, 320)
    },
    displayLabel(t) {
      const labels = {
        'p-panel': '控制',
        'p-layout': '布局',
        'p-devices': '设备',
        'p-profile': '我的',
      }
      return labels[t && t.id] || ((t && t.label) || '')
    },
    displayIcon(t) {
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
      return icons[t && t.id] || '◇'
    },
    _reloadTabs() {
      try {
        const next = syncLayoutTabs(loadTabsFromStore(), loadLayouts())
        if (Array.isArray(next) && next.length > 0) {
          this.tabs = next
        }
      } catch (e) {}
    },
    isActive(t) {
      // t.page 形如 "panel",currentPage 形如 "pages/panel/panel"
      if (!t || !t.page) return false
      const samePage = this.currentPage === 'pages/' + t.page + '/' + t.page
        || this.currentPage === 'pages/' + t.page
      if (!samePage) return false
      if (t.page === 'panel' && this.activeTabId) return this.activeTabId === t.id
      return true
    },
    onTap(t) {
      if (!t || !t.page) return
      // 记录当前激活的 tab id,供 panel.vue 等页面识别是哪个 tab 在用
      try { uni.setStorageSync('phonekb.activeTabId', t.id) } catch (e) {}
      this.activeTabId = t.id
      if (t.layoutId) {
        try { setCurrentLayoutId(t.layoutId) } catch (e) {}
      }
      // 总是 reLaunch,确保 onShow 触发(尤其是同页 tab 切换,例如 panel→鼠标控制 都是 page: panel)
      const url = '/pages/' + t.page + '/' + t.page
      uni.reLaunch({ url: url })
    },
  },
}
</script>

<style scoped>
.custom-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  min-height: 104rpx;
  padding: 8rpx 18rpx calc(8rpx + env(safe-area-inset-bottom));
  display: flex;
  flex-wrap: nowrap;
  overflow: hidden;
  background: var(--app-surface-strong, rgba(255,255,255,0.97));
  border-top: 1rpx solid var(--app-color-border, #DFE8F2);
  box-shadow: 0 -8rpx 24rpx rgba(47,78,113,0.05);
  backdrop-filter: blur(30rpx);
  -webkit-backdrop-filter: blur(30rpx);
  z-index: 99;
}
.tab-item {
  min-height: 82rpx;
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border-radius: 14rpx;
  color: var(--app-color-text-light, #8290A3);
  transition: color 120ms cubic-bezier(0.1,0.9,0.2,1), background-color 120ms cubic-bezier(0.1,0.9,0.2,1), transform 90ms cubic-bezier(0.1,0.9,0.2,1);
}
.tab-item:active {
  background: var(--app-color-primary-bg, #F1F6FB);
  transform: scale(0.97);
}
.tab-item.active {
  color: var(--app-color-primary, #2F78F6);
}
.tab-icon {
  min-height: 34rpx;
  color: inherit;
  font-family: "Segoe UI Symbol", "Segoe UI", sans-serif;
  font-size: 29rpx;
  font-weight: 650;
  line-height: 1;
}
.tab-label {
  margin-top: 5rpx;
  color: inherit;
  font-size: 20rpx;
  font-weight: 650;
  line-height: 1;
  white-space: nowrap;
}
.panel-tabbar {
  background: var(--app-surface-strong, rgba(255,255,255,0.98));
}
</style>
