<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="topbar">
    <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">‹</view>
    <text class="topbar-title">{{ manageMode ? '面板管理' : '切换面板' }}</text>
    <view class="topbar-action" hover-class="topbar-action-hover" @tap="onCreate"><text class="topbar-action-text">＋ 新建</text></view>
  </view>

  <view class="hint-section">
      <text class="hint-body">{{ manageMode ? '点更多可复制、重命名或删除面板。' : '点击卡片切换面板，点更多可管理面板。' }}</text>
  </view>

  <view class="section">
    <view class="section-heading">
      <view class="section-heading-left"><view class="heading-icon">面</view><text class="section-title">全部面板</text><text class="count-badge">{{ layouts.length }}</text></view>
      <text class="current-copy">当前：{{ currentName }}</text>
    </view>
    <view class="layout-grid">
      <view v-for="l in layouts" :key="l.id" :class="['layout-card', l.id === currentId ? 'layout-card-active' : '']" @tap="onPick(l.id)">
        <view class="layout-card-top">
          <view class="layout-card-copy"><text class="layout-card-name">{{ l.name }}</text><text class="layout-card-meta">{{ l.widgets.length }} 个组件</text></view>
          <view class="layout-more" :class="{ 'layout-more-active': l.id === currentId }" @tap.stop="onMore(l)">•••</view>
        </view>
        <view class="mini-components">
          <view v-for="(w, widx) in l.widgets.slice(0, 3)" :key="widx" class="mini-component">{{ w.icon || '◇' }}</view>
        </view>
        <text v-if="l.id === currentId" class="current-badge">当前</text>
      </view>
    </view>
  </view>
</view>
</template>

<script>
import {
  loadLayouts,
  getCurrentLayoutId,
  setCurrentLayoutId,
  createLayout,
  deleteLayout,
  renameLayout,
} from '@/utils/layoutConfig.js'

export default {
  data() {
    return {
      layouts: [],
      currentId: 'default',
      createOnShow: false,
      manageMode: false,
    }
  },
  computed: {
    currentName() {
      const currentId = this.currentId
      const l = this.layouts.find(function (x) { return x.id === currentId })
      return l ? l.name : ''
    },
  },
  onLoad(options) {
    this.createOnShow = !!(options && options.create === '1')
    this.manageMode = !!(options && options.manage === '1')
  },
  onShow() {
    this.layouts = loadLayouts()
    this.currentId = getCurrentLayoutId()
    if (this.createOnShow) {
      this.createOnShow = false
      const self = this
      setTimeout(function() { self.onCreate() }, 120)
    }
  },
  methods: {
    countEnabled(l) {
      return (l.widgets || []).filter(function (w) { return w && w.visible !== false }).length
    },
    onBack() {
      uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
    },
    onPick(id) {
      if (id === this.currentId) return
      setCurrentLayoutId(id)
      this.currentId = id
      uni.showToast({ title: '已切换', icon: 'success', duration: 600 })
      setTimeout(function () {
        uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
      }, 400)
    },
    onCreate() {
      const self = this
      uni.showModal({
        title: '新建面板',
        content: '从当前面板复制组件,新建一个独立面板',
        editable: true,
        placeholderText: '面板名称(留空用默认)',
        success: function (res) {
          if (!res.confirm) return
          const name = (res.content || '').trim() || ('面板 ' + (self.layouts.length + 1))
          const created = createLayout(name, self.currentId)
          self.layouts = loadLayouts()
          setCurrentLayoutId(created.id)
          self.currentId = created.id
          uni.showToast({ title: '已创建', icon: 'success', duration: 800 })
        },
      })
    },
    onMore(l) {
      const self = this
      const actions = []
      actions.push({ text: '复制', value: 'copy' })
      if (!l.built_in) actions.push({ text: '重命名', value: 'rename' })
      if (!l.built_in && l.id !== this.currentId) {
        actions.push({ text: '删除', value: 'delete', style: 'danger' })
      }
      uni.showActionSheet({
        itemList: actions.map(function (a) { return a.text }),
        success: function (res) {
          const act = actions[res.tapIndex]
          if (!act) return
          if (act.value === 'copy') {
            const created = createLayout(l.name + ' 副本', l.id)
            self.layouts = loadLayouts()
            uni.showToast({ title: '已复制为「' + created.name + '」', icon: 'none', duration: 1200 })
          } else if (act.value === 'rename') {
            self.promptRename(l)
          } else if (act.value === 'delete') {
            self.confirmDelete(l)
          }
        },
      })
    },
    promptRename(l) {
      const self = this
      uni.showModal({
        title: '重命名',
        content: '请输入新名称',
        editable: true,
        placeholderText: l.name,
        success: function (res) {
          if (!res.confirm) return
          const name = (res.content || '').trim()
          if (!name) return
          renameLayout(l.id, name)
          self.layouts = loadLayouts()
          uni.showToast({ title: '已重命名', icon: 'success', duration: 600 })
        },
      })
    },
    confirmDelete(l) {
      const self = this
      uni.showModal({
        title: '删除面板',
        content: '确定要删除「' + l.name + '」吗?此操作不可恢复',
        success: function (res) {
          if (!res.confirm) return
          deleteLayout(l.id)
          self.layouts = loadLayouts()
          self.currentId = getCurrentLayoutId()
          uni.showToast({ title: '已删除', icon: 'success', duration: 800 })
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
  min-height: 80rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,0.92);
  border-bottom: 1rpx solid #DCE6F1;
}
.topbar-back {
  width: 56rpx;
  height: 52rpx;
  display: flex;
  align-items: center;
  color: #506177;
  font-size: 38rpx;
}
.topbar-back-hover {
  color: #2F78F6;
}
.topbar-title {
  color: #172033;
  font-size: 29rpx;
  font-weight: 750;
}
.topbar-action {
  min-width: 96rpx;
  height: 46rpx;
  padding: 0 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  background: #EAF3FF;
  color: #2F78F6;
}
.topbar-action-hover {
  background: #DCEBFF;
}
.topbar-action-text {
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 700;
}
.hint-section {
  margin: 18rpx 32rpx 16rpx;
  padding: 14rpx 18rpx;
  border-radius: 13rpx;
  background: #EAF3FF;
  border: 1rpx solid #D5E5FA;
}
.hint-body {
  color: #55708F;
  font-size: 20rpx;
  line-height: 1.45;
}
.section {
  margin: 0 24rpx;
  padding: 18rpx 14rpx 20rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(47, 78, 113, 0.06);
}
.section-heading {
  min-height: 58rpx;
  padding: 0 10rpx 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-heading-left {
  display: flex;
  align-items: center;
}
.heading-icon {
  width: 46rpx;
  height: 46rpx;
  margin-right: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 19rpx;
  font-weight: 700;
}
.section-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.count-badge {
  margin-left: 12rpx;
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 700;
}
.current-copy {
  max-width: 42%;
  color: #7E8B9E;
  font-size: 20rpx;
  text-align: right;
}
.layout-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
}
.layout-card {
  width: calc(50% - 8rpx);
  min-height: 148rpx;
  margin-top: 12rpx;
  padding: 16rpx 14rpx;
  position: relative;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 17rpx;
  box-sizing: border-box;
}
.layout-card-active {
  border: 2rpx solid #2F78F6;
  background: #F9FCFF;
  box-shadow: 0 8rpx 20rpx rgba(47, 120, 246, 0.12);
}
.layout-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.layout-card-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.layout-card-name {
  color: #172033;
  font-size: 23rpx;
  font-weight: 700;
  line-height: 1.25;
}
.layout-card-meta {
  margin-top: 5rpx;
  color: #7E8B9E;
  font-size: 19rpx;
}
.layout-more {
  width: 36rpx;
  height: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #607087;
  font-size: 21rpx;
  letter-spacing: 2rpx;
}
.layout-more-active {
  color: #506177;
}
.mini-components {
  display: flex;
  gap: 8rpx;
  margin-top: 20rpx;
}
.mini-component {
  width: 42rpx;
  height: 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 9rpx;
  background: #F4F8FD;
  color: #506177;
  font-size: 18rpx;
}
.current-badge {
  position: absolute;
  right: 14rpx;
  bottom: 12rpx;
  padding: 3rpx 9rpx;
  border-radius: 9rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 17rpx;
  font-weight: 700;
}
</style>
