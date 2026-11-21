<template>
<view class="gesture-page">
  <view class="statusbar-spacer" :style="{height:statusBarHeight+'px'}"></view>
  <view class="topbar"><view class="back" @tap="goBack">‹ 返回</view><text class="title">编辑时间轴手势</text><view class="save" @tap="goBack">保存</view></view>
  <view class="content">
    <view class="card"><view class="enable-row"><view class="row-icon">◇</view><view class="copy"><text>时间轴手势区</text><text>只启用稳定、基础的手势</text></view><switch :checked="config.timeline.enabled" color="#2F78F6" @change="toggleEnabled" /></view></view>
    <view class="section-head"><text>手势含义</text><text>2 组已启用</text></view>
    <view class="card">
      <view class="gesture-row" @tap="editGesture('swipe')"><view class="glyph">←·→</view><view class="copy"><text>单指左右滑动</text><text>按滑动距离连续模拟普通滚轮</text><view class="binding"><text>{{ actionLabel(config.timeline.swipeLeft) }}</text><text>/</text><text>{{ actionLabel(config.timeline.swipeRight) }}</text></view></view><text class="chev">›</text></view>
      <view class="gesture-row" @tap="editGesture('pinch')"><view class="glyph">↔</view><view class="copy"><text>双指张开 / 合拢</text><text>按阶梯连续触发时间轴缩放</text><view class="binding"><text>{{ actionLabel(config.timeline.pinchOut) }}</text><text>/</text><text>{{ actionLabel(config.timeline.pinchIn) }}</text></view></view><text class="chev">›</text></view>
    </view>
    <view class="section-head"><text>触发门槛</text><text>{{ sensitivityLabel }}</text></view>
    <view class="card sensitivity"><view class="segments"><view v-for="item in sensitivityOptions" :key="item.id" :class="['segment',{on:config.timeline.sensitivity===item.id}]" :data-id="item.id" @tap="setSensitivity">{{ item.label }}</view></view><text class="sensitivity-note">{{ sensitivityNote }}</text></view>
    <view class="section-head"><text>手势倍率</text><text>可连续调节</text></view>
    <view class="card multiplier-card">
      <view class="multiplier-row">
        <view class="multiplier-head"><view><text>单指滚轮速度</text><text>数值越大，同样距离触发的滚轮格数越多</text></view><text class="multiplier-value">{{ swipeMultiplierLabel }}</text></view>
        <slider class="multiplier-slider" :value="swipeMultiplierPercent" min="50" max="250" step="10" activeColor="#2F78F6" backgroundColor="#DDE6EF" block-color="#FFFFFF" block-size="22" @changing="previewSwipeMultiplier" @change="saveSwipeMultiplier" />
      </view>
      <view class="multiplier-row">
        <view class="multiplier-head"><view><text>双指缩放程度</text><text>同时调整本地刻度与 Ctrl + 滚轮步数</text></view><text class="multiplier-value">{{ pinchMultiplierLabel }}</text></view>
        <slider class="multiplier-slider" :value="pinchMultiplierPercent" min="50" max="300" step="10" activeColor="#2F78F6" backgroundColor="#DDE6EF" block-color="#FFFFFF" block-size="22" @changing="previewPinchMultiplier" @change="savePinchMultiplier" />
      </view>
    </view>
    <view class="card test-card" @tap="showTest"><view class="row-icon">▶</view><view class="copy"><text>测试手势</text><text>不发送到电脑，只检查识别结果</text></view><text class="chev">›</text></view>
    <text class="footer-note">暂不加入三指、长按、惯性滑动等复杂手势，避免剪辑过程中误触。</text>
  </view>
</view>
</template>
<script>
import { getGestureAction, loadWorkbenchConfig, normalizeWorkbenchScope, saveWorkbenchConfig, updateTimeline } from '@/utils/jianyingWorkbenchConfig.js'

function nativeStatusBarHeight() {
  let height = 24
  try {
    const info = typeof uni.getWindowInfo === 'function' ? uni.getWindowInfo() : null
    height = Math.max(height, Number(info && info.statusBarHeight) || 0, Number(info && info.safeArea && info.safeArea.top) || 0)
  } catch (e) {}
  try {
    const info = uni.getSystemInfoSync()
    height = Math.max(height, Number(info && info.statusBarHeight) || 0, Number(info && info.safeArea && info.safeArea.top) || 0)
  } catch (e) {}
  return height
}

export default {
  data() { return { scope: 'default', config: loadWorkbenchConfig('default'), statusBarHeight: 24, sensitivityOptions: [{id:'stable',label:'更稳定'},{id:'medium',label:'中等'},{id:'sensitive',label:'更灵敏'}] } },
  computed: {
    sensitivityLabel() { const item=this.sensitivityOptions.find(x=>x.id===this.config.timeline.sensitivity); return item ? item.label : '中等' },
    sensitivityNote() { return {stable:'需要更明显的手指移动，误触最少',medium:'操作速度和稳定性的平衡设置',sensitive:'轻微移动即可触发，适合快速操作'}[this.config.timeline.sensitivity] || '' },
    swipeMultiplierPercent() { return Math.round(this.config.timeline.swipeMultiplier * 100) },
    pinchMultiplierPercent() { return Math.round(this.config.timeline.pinchMultiplier * 100) },
    swipeMultiplierLabel() { return this.config.timeline.swipeMultiplier.toFixed(1) + '×' },
    pinchMultiplierLabel() { return this.config.timeline.pinchMultiplier.toFixed(1) + '×' },
  },
  onLoad(options) { this.statusBarHeight=nativeStatusBarHeight(); this.scope=normalizeWorkbenchScope(options&&options.scope); this.reload() }, onShow() { this.reload() },
  methods: {
    reload(){ this.config=loadWorkbenchConfig(this.scope) }, persist(next){ const saved=saveWorkbenchConfig(this.scope,next); if(saved)this.config=saved; else uni.showToast({title:'保存失败，请重试',icon:'none'}) }, goBack(){uni.navigateBack({delta:1})},
    actionLabel(id){return getGestureAction(id).label}, toggleEnabled(event){this.persist(updateTimeline(this.config,{enabled:!!event.detail.value}))},
    setSensitivity(event){this.persist(updateTimeline(this.config,{sensitivity:String(event.currentTarget.dataset.id||'medium')}))},
    previewSwipeMultiplier(event){this.config=updateTimeline(this.config,{swipeMultiplier:Number(event.detail.value)/100})},
    saveSwipeMultiplier(event){this.persist(updateTimeline(this.config,{swipeMultiplier:Number(event.detail.value)/100}))},
    previewPinchMultiplier(event){this.config=updateTimeline(this.config,{pinchMultiplier:Number(event.detail.value)/100})},
    savePinchMultiplier(event){this.persist(updateTimeline(this.config,{pinchMultiplier:Number(event.detail.value)/100}))},
    editGesture(kind){uni.navigateTo({url:'/pages/jianying-gesture-edit/jianying-gesture-edit?scope='+encodeURIComponent(this.scope)+'&kind='+kind})},
    showTest(){uni.showToast({title:'请返回控制页在手势区试用',icon:'none'})},
  },
}
</script>
<style scoped>
.gesture-page{min-height:100vh;background:var(--app-color-bg,#EDF4FA);color:var(--app-color-text,#172638)}.topbar{height:92rpx;padding:0 24rpx;display:grid;grid-template-columns:120rpx 1fr 120rpx;align-items:center;border-bottom:1rpx solid var(--app-color-border,#DCE6EF);background:var(--app-surface-strong,#FFF)}.back{color:#5D6E82;font-size:24rpx;font-weight:650}.title{text-align:center;font-size:29rpx;font-weight:750}.save{text-align:right;color:var(--app-color-primary,#2F78F6);font-size:24rpx;font-weight:700}.content{padding:28rpx 24rpx}.card{overflow:hidden;border:1rpx solid var(--app-color-border,#DCE6EF);border-radius:14rpx;background:var(--app-surface-strong,#FFF);box-shadow:0 8rpx 24rpx rgba(44,64,87,.06)}.enable-row,.test-card{min-height:92rpx;padding:0 18rpx;display:flex;align-items:center}.row-icon{width:48rpx;height:48rpx;margin-right:14rpx;display:flex;align-items:center;justify-content:center;border-radius:10rpx;background:var(--app-color-primary-bg,#EEF4FB);color:#4F75A6;font-size:21rpx}.copy{min-width:0;flex:1;display:flex;flex-direction:column}.copy>text:first-child{font-size:23rpx;font-weight:700}.copy>text:nth-child(2){margin-top:5rpx;color:var(--app-color-text-light,#8B98A8);font-size:16rpx}.section-head{margin:28rpx 4rpx 14rpx;display:flex;justify-content:space-between;color:#596B80;font-size:21rpx;font-weight:700}.section-head text:last-child{color:#909CAD;font-weight:500}.gesture-row{min-height:134rpx;padding:18rpx;display:flex;align-items:center;border-top:1rpx solid var(--app-color-border,#E9EEF3)}.gesture-row:first-child{border-top:0}.glyph{width:72rpx;height:72rpx;margin-right:16rpx;display:flex;align-items:center;justify-content:center;flex:0 0 auto;border:1rpx solid #D8E3ED;border-radius:12rpx;background:#F5F9FD;color:#496782;font-size:29rpx}.binding{margin-top:9rpx;display:flex;gap:8rpx;color:#53677D;font-size:14rpx}.chev{color:#9BA7B4;font-size:30rpx}.sensitivity{padding:14rpx}.segments{padding:5rpx;display:grid;grid-template-columns:repeat(3,1fr);border:1rpx solid #D8E2EB;border-radius:11rpx;background:#F0F4F7}.segment{height:52rpx;display:flex;align-items:center;justify-content:center;border-radius:8rpx;color:#6C7D91;font-size:19rpx;font-weight:650}.segment.on{background:#FFF;color:var(--app-color-primary,#2F78F6);box-shadow:0 2rpx 9rpx rgba(39,57,78,.12)}.sensitivity-note{display:block;margin:15rpx 4rpx 2rpx;color:#8693A4;font-size:16rpx}.test-card{margin-top:26rpx}.footer-note{display:block;margin-top:22rpx;color:#8290A2;font-size:17rpx;line-height:1.55}
.statusbar-spacer{width:100%;background:var(--app-surface-strong,#FFF)}
.multiplier-card{padding:0 18rpx}.multiplier-row{padding:19rpx 0 14rpx;border-top:1rpx solid var(--app-color-border,#E9EEF3)}.multiplier-row:first-child{border-top:0}.multiplier-head{display:flex;align-items:center}.multiplier-head>view{min-width:0;flex:1;display:flex;flex-direction:column}.multiplier-head>view text:first-child{font-size:22rpx;font-weight:700}.multiplier-head>view text:last-child{margin-top:5rpx;color:var(--app-color-text-light,#8B98A8);font-size:15rpx}.multiplier-value{min-width:66rpx;margin-left:14rpx;padding:6rpx 8rpx;border-radius:8rpx;background:var(--app-color-primary-bg,#EEF6FF);color:var(--app-color-primary,#2F78F6);font-size:18rpx;font-weight:750;text-align:center}.multiplier-slider{margin:12rpx -5rpx 0}
</style>
