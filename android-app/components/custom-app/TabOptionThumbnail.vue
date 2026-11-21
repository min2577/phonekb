<template>
  <view class="option-thumb">
    <view class="option-status"><text>9:41</text><text>•••</text></view>
    <view class="option-body">
      <view v-if="option.key === 'w-key-grid'" class="thumb-widget">
        <view class="thumb-title"><text>⌘</text><text>快捷键</text></view>
        <view class="thumb-key-grid"><view v-for="i in 12" :key="i" class="thumb-key"></view></view>
      </view>
      <view v-else-if="option.key === 'w-text-input'" class="thumb-widget">
        <view class="thumb-title"><text>▦</text><text>文字输入</text></view>
        <view class="thumb-input"></view>
        <view class="thumb-actions"><view></view><view class="primary"></view></view>
      </view>
      <view v-else-if="option.key === 'w-mouse-control'" class="thumb-widget">
        <view class="thumb-title"><text>◉</text><text>鼠标控制</text></view>
        <view class="thumb-trackpad"></view>
        <view class="thumb-mouse-row"><view v-for="i in 4" :key="i"></view></view>
      </view>
      <view v-else-if="option.key === 'w-volume'" class="thumb-widget">
        <view class="thumb-title"><text>♪</text><text>音量控制</text></view>
        <view class="thumb-volume"><view class="thumb-volume-icon">♪</view><view class="thumb-volume-copy"><view></view><view class="short"></view></view></view>
        <view class="thumb-volume-row"><view></view><view class="primary"></view><view></view></view>
      </view>
      <view v-else-if="option.key === 'p-layout'" class="thumb-page">
        <view class="thumb-page-title">布局</view>
        <view class="thumb-layout-grid"><view v-for="i in 16" :key="i"></view></view>
        <view class="thumb-list-row" v-for="i in 2" :key="'layout-' + i"><view></view><text></text></view>
      </view>
      <view v-else-if="option.key === 'p-profile'" class="thumb-page">
        <view class="thumb-page-title">我的</view>
        <view class="thumb-profile"><view class="avatar">♙</view><view><text></text><text class="short"></text></view></view>
        <view class="thumb-list-row" v-for="i in 3" :key="'profile-' + i"><view></view><text></text></view>
      </view>
      <view v-else-if="option.key === 'p-devices'" class="thumb-page">
        <view class="thumb-page-title">设备</view>
        <view class="thumb-device-card"><view class="device-dot"></view><view><text></text><text class="short"></text></view></view>
        <view class="thumb-list-row" v-for="i in 2" :key="'device-' + i"><view></view><text></text></view>
      </view>
      <view v-else class="thumb-page thumb-panel-page">
        <view class="thumb-panel-head"><view><text></text><text class="short"></text></view><view class="more">•••</view></view>
        <view class="thumb-panel-card" v-for="i in 3" :key="'panel-' + i"><view class="thumb-title"><text>{{ i === 1 ? '⌘' : (i === 2 ? '▦' : '◉') }}</text><text></text></view><view class="thumb-panel-fill"></view></view>
      </view>
    </view>
    <view class="option-tabbar"><view v-for="i in 4" :key="i"></view></view>
  </view>
</template>

<script>
export default {
  name: 'TabOptionThumbnail',
  props: {
    option: { type: Object, required: true },
  },
}
</script>

<style scoped>
.option-thumb { width: 132rpx; height: 145rpx; display: flex; flex-direction: column; overflow: hidden; border: 1rpx solid #DCE6F1; border-radius: 13rpx; background: #F4F8FD; box-shadow: 0 4rpx 10rpx rgba(47,78,113,0.07); }
.option-status { height: 25rpx; padding: 4rpx 10rpx 0; display: flex; align-items: center; justify-content: space-between; color: #506177; font-size: 9rpx; box-sizing: border-box; }
.option-body { flex: 1; min-height: 0; padding: 5rpx; box-sizing: border-box; overflow: hidden; }
.option-tabbar { height: 25rpx; padding: 4rpx 12rpx; display: flex; align-items: center; justify-content: space-between; border-top: 1rpx solid #E5ECF4; background: #FFFFFF; box-sizing: border-box; }
.option-tabbar view { width: 15rpx; height: 15rpx; border-radius: 5rpx; background: #DCE6F1; }
.thumb-widget, .thumb-page { height: 100%; padding: 6rpx; border-radius: 9rpx; background: #FFFFFF; box-sizing: border-box; overflow: hidden; }
.thumb-title { height: 19rpx; display: flex; align-items: center; gap: 5rpx; color: #2F78F6; font-size: 10rpx; font-weight: 700; }
.thumb-title text:last-child { color: #172033; }
.thumb-key-grid { margin-top: 7rpx; display: grid; grid-template-columns: repeat(4, 1fr); gap: 4rpx; }
.thumb-key { height: 15rpx; border: 1rpx solid #DCE6F1; border-radius: 4rpx; background: #FBFDFF; }
.thumb-input { height: 31rpx; margin-top: 7rpx; border: 1rpx solid #DCE6F1; border-radius: 6rpx; background: #F7FAFE; }
.thumb-actions, .thumb-volume-row { margin-top: 9rpx; display: flex; justify-content: space-between; gap: 7rpx; }
.thumb-actions view { width: 42rpx; height: 20rpx; border-radius: 6rpx; background: #EEF4FA; }
.thumb-actions .primary { background: #2F78F6; }
.thumb-trackpad { height: 42rpx; margin-top: 6rpx; border: 1rpx solid #DCE6F1; border-radius: 7rpx; background: #F3F7FC; }
.thumb-mouse-row { margin-top: 7rpx; display: grid; grid-template-columns: repeat(4, 1fr); gap: 4rpx; }
.thumb-mouse-row view { height: 20rpx; border-radius: 5rpx; background: #EEF4FA; }
.thumb-volume { margin-top: 10rpx; padding: 9rpx; display: flex; align-items: center; gap: 8rpx; border-radius: 8rpx; background: #F4F8FD; }
.thumb-volume-icon { width: 28rpx; height: 28rpx; display: flex; align-items: center; justify-content: center; border-radius: 8rpx; background: #EAF3FF; color: #2F78F6; font-size: 15rpx; }
.thumb-volume-copy { flex: 1; }
.thumb-volume-copy view { height: 7rpx; border-radius: 4rpx; background: #C9D7E7; }
.thumb-volume-copy .short { width: 58%; margin-top: 5rpx; }
.thumb-volume-row view { flex: 1; height: 28rpx; border-radius: 7rpx; background: #EEF4FA; }
.thumb-volume-row .primary { background: #2F78F6; }
.thumb-page-title { margin-bottom: 8rpx; color: #172033; font-size: 12rpx; font-weight: 700; text-align: center; }
.thumb-layout-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3rpx; }
.thumb-layout-grid view { height: 19rpx; border: 1rpx solid #DCE6F1; border-radius: 4rpx; }
.thumb-list-row { height: 28rpx; margin-top: 6rpx; padding: 0 6rpx; display: flex; align-items: center; gap: 6rpx; border: 1rpx solid #E5ECF4; border-radius: 7rpx; }
.thumb-list-row view { width: 15rpx; height: 15rpx; border-radius: 5rpx; background: #EAF3FF; }
.thumb-list-row text { flex: 1; height: 6rpx; border-radius: 4rpx; background: #D7E2EE; }
.thumb-profile { padding: 9rpx; display: flex; align-items: center; gap: 8rpx; border-radius: 9rpx; background: #F7FAFE; }
.thumb-profile .avatar { width: 30rpx; height: 30rpx; display: flex; align-items: center; justify-content: center; border-radius: 9rpx; background: #EAF3FF; color: #2F78F6; }
.thumb-profile > view:last-child, .thumb-device-card > view:last-child { flex: 1; }
.thumb-profile text, .thumb-device-card text { display: block; height: 6rpx; border-radius: 4rpx; background: #C9D7E7; }
.thumb-profile .short, .thumb-device-card .short { width: 58%; margin-top: 5rpx; }
.thumb-device-card { padding: 10rpx; display: flex; align-items: center; gap: 8rpx; border-radius: 9rpx; background: #F7FAFE; }
.device-dot { width: 12rpx; height: 12rpx; border-radius: 50%; background: #22B85A; }
.thumb-panel-page { padding: 7rpx; background: #F4F8FD; }
.thumb-panel-head { height: 28rpx; display: flex; align-items: center; justify-content: space-between; }
.thumb-panel-head > view:first-child { flex: 1; }
.thumb-panel-head text { display: block; width: 54rpx; height: 6rpx; border-radius: 4rpx; background: #BFCEDF; }
.thumb-panel-head .short { width: 36rpx; margin-top: 4rpx; }
.thumb-panel-head .more { color: #607087; font-size: 10rpx; }
.thumb-panel-card { margin-top: 5rpx; padding: 6rpx; border: 1rpx solid #E1E8F0; border-radius: 8rpx; background: #FFFFFF; }
.thumb-panel-fill { height: 21rpx; margin-top: 4rpx; border-radius: 5rpx; background: #EFF4F9; }
</style>
