<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="topbar">
    <view class="icon-btn" hover-class="icon-btn-hover" @tap="onBack">‹</view>
    <view class="topbar-copy">
      <text class="topbar-title">Codex Micro</text>
      <text class="topbar-sub">按键功能</text>
    </view>
    <view class="reset-btn" hover-class="reset-btn-hover" @tap="onReset">恢复默认</view>
  </view>

  <view class="console-strip">
    <view class="console-mark">CM</view>
    <view class="console-copy">
      <text class="console-name">Code Smith</text>
      <text class="console-meta">固定布局 · {{controlCount}} 个可编辑控制位</text>
    </view>
    <view class="console-state">本机</view>
  </view>

  <view v-for="group in controlGroups" :key="group.id" class="control-section">
    <view class="section-head">
      <text class="section-title">{{group.label}}</text>
      <text class="section-count">{{group.controls.length}}</text>
    </view>
    <view class="control-list">
      <view v-for="control in group.controls" :key="control.id"
            class="control-row" hover-class="control-row-hover" @tap="onPickAction(control)">
        <view class="control-position">{{control.position}}</view>
        <view class="control-copy">
          <text class="control-name">{{control.label}}</text>
          <text class="control-hint">{{actionMeta(keyMap[control.id]).hint}}</text>
        </view>
        <view class="action-value">
          <view class="action-symbol">{{actionMeta(keyMap[control.id]).symbol}}</view>
          <text class="action-name">{{actionMeta(keyMap[control.id]).label}}</text>
        </view>
        <text class="row-chevron">›</text>
      </view>
    </view>
  </view>

  <view class="footer-safe"></view>
</view>
</template>

<script>
import {
  ACTION_OPTIONS,
  CONTROL_GROUPS,
  getCodexActionMeta,
  loadCodexMicroKeyMap,
  resetCodexMicroKeyMap,
  saveCodexMicroKeyMap,
} from '@/utils/codexMicroConfig.js'

export default {
  data() {
    return {
      statusBarHeight: 24,
      actionOptions: ACTION_OPTIONS,
      controlGroups: CONTROL_GROUPS,
      keyMap: loadCodexMicroKeyMap(),
    }
  },
  computed: {
    controlCount() {
      return this.controlGroups.reduce(function(total, group) { return total + group.controls.length }, 0)
    },
  },
  onLoad() {
    try {
      const system = uni.getSystemInfoSync()
      if (system && system.statusBarHeight) this.statusBarHeight = system.statusBarHeight
    } catch (e) {}
  },
  onShow() {
    this.keyMap = loadCodexMicroKeyMap()
  },
  methods: {
    actionMeta(actionId) { return getCodexActionMeta(actionId) },
    onBack() { uni.navigateBack() },
    onPickAction(control) {
      const self = this
      uni.showActionSheet({
        itemList: this.actionOptions.map(function(item) { return item.label }),
        success: function(result) {
          const action = self.actionOptions[result.tapIndex]
          if (!action) return
          const next = Object.assign({}, self.keyMap)
          next[control.id] = action.id
          if (!saveCodexMicroKeyMap(next)) {
            uni.showToast({ title: '保存失败', icon: 'none' })
            return
          }
          self.keyMap = next
          try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
        },
      })
    },
    onReset() {
      const self = this
      uni.showModal({
        title: '恢复默认按键',
        content: '将恢复 Code Smith 的初始功能映射。',
        confirmText: '恢复',
        success: function(result) {
          if (!result.confirm) return
          resetCodexMicroKeyMap()
          self.keyMap = loadCodexMicroKeyMap()
          uni.showToast({ title: '已恢复默认', icon: 'success', duration: 900 })
        },
      })
    },
  },
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 0 24rpx calc(36rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background: #F3F7FB;
  color: #172033;
}
.statusbar-spacer { width: 100%; }
.topbar {
  min-height: 82rpx;
  display: flex;
  align-items: center;
  gap: 14rpx;
}
.icon-btn {
  width: 54rpx;
  height: 54rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #D8E2EC;
  border-radius: 12rpx;
  background: #FFFFFF;
  color: #33485D;
  font-size: 38rpx;
}
.icon-btn-hover { background: #EAF3FF; }
.topbar-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.topbar-title { color: #18283A; font-size: 27rpx; font-weight: 750; }
.topbar-sub { margin-top: 2rpx; color: #7C8B9D; font-size: 18rpx; }
.reset-btn {
  min-height: 50rpx;
  padding: 0 16rpx;
  display: flex;
  align-items: center;
  border: 1rpx solid #D7E2ED;
  border-radius: 11rpx;
  background: #FFFFFF;
  color: #566B80;
  font-size: 19rpx;
  font-weight: 650;
}
.reset-btn-hover { border-color: #9CBFE4; color: #286AA7; }
.console-strip {
  min-height: 92rpx;
  margin: 8rpx 0 20rpx;
  padding: 15rpx 17rpx;
  display: flex;
  align-items: center;
  gap: 14rpx;
  border: 1rpx solid #C8D7E4;
  border-radius: 15rpx;
  background: #E9F0F6;
  box-sizing: border-box;
}
.console-mark {
  width: 50rpx;
  height: 50rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10rpx;
  background: #26394B;
  color: #FFFFFF;
  font-size: 17rpx;
  font-weight: 800;
}
.console-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.console-name { color: #263A4E; font-size: 23rpx; font-weight: 750; }
.console-meta { margin-top: 4rpx; color: #718397; font-size: 17rpx; }
.console-state { color: #376B98; font-size: 18rpx; font-weight: 700; }
.control-section { margin-top: 18rpx; }
.section-head {
  min-height: 46rpx;
  padding: 0 5rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title { color: #54687D; font-size: 20rpx; font-weight: 750; }
.section-count { color: #91A0AF; font-size: 18rpx; }
.control-list {
  overflow: hidden;
  border: 1rpx solid #D9E3EC;
  border-radius: 15rpx;
  background: #FFFFFF;
}
.control-row {
  min-height: 92rpx;
  padding: 13rpx 14rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  border-bottom: 1rpx solid #E7EDF3;
  box-sizing: border-box;
}
.control-row:last-child { border-bottom: 0; }
.control-row-hover { background: #F3F8FD; }
.control-position {
  width: 70rpx;
  color: #8493A3;
  font-size: 17rpx;
  text-align: center;
}
.control-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.control-name { color: #26394D; font-size: 22rpx; font-weight: 700; }
.control-hint { margin-top: 4rpx; overflow: hidden; color: #8594A4; font-size: 16rpx; text-overflow: ellipsis; white-space: nowrap; }
.action-value { display: flex; align-items: center; gap: 7rpx; }
.action-symbol {
  width: 38rpx;
  height: 38rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9rpx;
  background: #EAF3FC;
  color: #2F6FA9;
  font-size: 18rpx;
  font-weight: 800;
}
.action-name { max-width: 116rpx; color: #446079; font-size: 18rpx; font-weight: 650; }
.row-chevron { color: #A0ADBA; font-size: 28rpx; }
.footer-safe { height: 20rpx; }
</style>
