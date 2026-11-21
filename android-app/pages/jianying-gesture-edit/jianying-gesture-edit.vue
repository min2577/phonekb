<template>
<view class="detail-page">
  <view class="statusbar-spacer" :style="{height:statusBarHeight+'px'}"></view>
  <view class="topbar"><view class="back" @tap="goBack">‹ 返回</view><text class="title">{{ isPinch ? '双指缩放' : '单指滑动' }}</text><view class="save" @tap="goBack">保存</view></view>
  <view class="content">
    <view class="section-head"><text>手势预览</text><text>{{ isPinch ? '两指距离变化' : '单指水平移动' }}</text></view>
    <view class="card preview"><view v-if="isPinch" class="pinch-demo"><view class="finger left"></view><view class="finger right"></view><text>←&nbsp;&nbsp;&nbsp;→</text></view><view v-else class="swipe-demo"><text>←·→</text><text>沿时间轴水平滑动</text></view></view>
    <view class="section-head"><text>方向与功能</text><text>点击可更换</text></view>
    <view class="card">
      <view class="direction" @tap="chooseAction(firstProperty)"><view class="direction-head"><text>{{ firstDirection }}</text><text class="tag">连续触发</text></view><view class="action"><view><text>{{ action(firstProperty).label }}</text><text>{{ actionDescription(firstProperty) }}</text></view><text class="binding">{{ actionBinding(firstProperty) }}</text><text class="chev">›</text></view></view>
      <view class="direction" @tap="chooseAction(secondProperty)"><view class="direction-head"><text>{{ secondDirection }}</text><text class="tag">连续触发</text></view><view class="action"><view><text>{{ action(secondProperty).label }}</text><text>{{ actionDescription(secondProperty) }}</text></view><text class="binding">{{ actionBinding(secondProperty) }}</text><text class="chev">›</text></view></view>
    </view>
    <view class="button" @tap="swapDirections">⇄ 交换两个方向的功能</view>
    <text class="footer-note">{{ isPinch ? '时间轴缩放使用 Ctrl + 滚轮复合输入；也可替换为 Ctrl + / - 的轨道高度调整。' : '单指滑动默认模拟普通滚轮，剪映会根据当前时间轴比例决定实际移动幅度。' }}</text>
  </view>
</view>
</template>
<script>
import { PINCH_ACTION_IDS, SWIPE_ACTION_IDS, formatShortcut, getGestureAction, loadWorkbenchConfig, normalizeWorkbenchScope, saveWorkbenchConfig, updateTimeline } from '@/utils/jianyingWorkbenchConfig.js'

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
  data(){return{scope:'default',kind:'swipe',config:loadWorkbenchConfig('default'),statusBarHeight:24}},
  computed:{
    isPinch(){return this.kind==='pinch'}, firstProperty(){return this.isPinch?'pinchOut':'swipeLeft'}, secondProperty(){return this.isPinch?'pinchIn':'swipeRight'},
    firstDirection(){return this.isPinch?'双指张开':'向左滑动'}, secondDirection(){return this.isPinch?'双指合拢':'向右滑动'},
  },
  onLoad(options){this.statusBarHeight=nativeStatusBarHeight();this.scope=normalizeWorkbenchScope(options&&options.scope);this.kind=String((options&&options.kind)||'swipe')==='pinch'?'pinch':'swipe';this.reload()},
  methods:{
    reload(){this.config=loadWorkbenchConfig(this.scope)},goBack(){uni.navigateBack({delta:1})},action(property){return getGestureAction(this.config.timeline[property])},
    actionDescription(property){const item=this.action(property);return item.type==='mouse_zoom'?'修饰键 + 鼠标滚轮':(item.type==='mouse_wheel'?'普通鼠标滚轮':(item.type==='shortcut'?'键盘快捷键':'不发送输入'))},
    actionBinding(property){const item=this.action(property);if(item.type==='mouse_zoom')return 'Ctrl + '+(item.delta>0?'滚轮↑':'滚轮↓');if(item.type==='mouse_wheel')return item.delta>0?'滚轮↑':'滚轮↓';if(item.type==='shortcut')return formatShortcut(item.modifiers,item.key);return '无'},
    chooseAction(property){const self=this;const ids=this.isPinch?PINCH_ACTION_IDS:SWIPE_ACTION_IDS;uni.showActionSheet({itemList:ids.map(id=>getGestureAction(id).label),success(result){const id=ids[result.tapIndex];const updates={};updates[property]=id;const saved=saveWorkbenchConfig(self.scope,updateTimeline(self.config,updates));if(saved)self.config=saved;else uni.showToast({title:'保存失败，请重试',icon:'none'})}})},
    swapDirections(){const first=this.config.timeline[this.firstProperty];const second=this.config.timeline[this.secondProperty];const updates={};updates[this.firstProperty]=second;updates[this.secondProperty]=first;const saved=saveWorkbenchConfig(this.scope,updateTimeline(this.config,updates));if(!saved){uni.showToast({title:'保存失败，请重试',icon:'none'});return}this.config=saved;try{uni.vibrateShort({type:'light'})}catch(e){}},
  },
}
</script>
<style scoped>
.detail-page{min-height:100vh;background:var(--app-color-bg,#EDF4FA);color:var(--app-color-text,#172638)}.topbar{height:92rpx;padding:0 24rpx;display:grid;grid-template-columns:120rpx 1fr 120rpx;align-items:center;border-bottom:1rpx solid var(--app-color-border,#DCE6EF);background:var(--app-surface-strong,#FFF)}.back{color:#5D6E82;font-size:24rpx;font-weight:650}.title{text-align:center;font-size:29rpx;font-weight:750}.save{text-align:right;color:var(--app-color-primary,#2F78F6);font-size:24rpx;font-weight:700}.content{padding:28rpx 24rpx}.section-head{margin:0 4rpx 14rpx;display:flex;justify-content:space-between;color:#596B80;font-size:21rpx;font-weight:700}.section-head:not(:first-child){margin-top:28rpx}.section-head text:last-child{color:#909CAD;font-weight:500}.card{overflow:hidden;border:1rpx solid var(--app-color-border,#DCE6EF);border-radius:14rpx;background:var(--app-surface-strong,#FFF);box-shadow:0 8rpx 24rpx rgba(44,64,87,.06)}.preview{height:194rpx;display:flex;align-items:center;justify-content:center;background:#F8FBFE}.pinch-demo{width:220rpx;height:130rpx;position:relative;display:flex;align-items:flex-end;justify-content:center}.finger{width:48rpx;height:70rpx;position:absolute;top:15rpx;border:4rpx solid #6B8299;border-radius:26rpx;background:#FFF}.finger.left{left:43rpx;transform:rotate(-8deg)}.finger.right{right:43rpx;transform:rotate(8deg)}.pinch-demo text{margin-bottom:4rpx;color:var(--app-color-primary,#2F78F6);font-size:35rpx;font-weight:700}.swipe-demo{display:flex;align-items:center;flex-direction:column}.swipe-demo text:first-child{color:#496782;font-size:47rpx;font-weight:650}.swipe-demo text:last-child{margin-top:14rpx;color:#8291A3;font-size:18rpx}.direction{padding:18rpx;border-top:1rpx solid #E9EEF3}.direction:first-child{border-top:0}.direction-head{display:flex;align-items:center;margin-bottom:12rpx}.direction-head>text:first-child{font-size:23rpx;font-weight:700}.tag{margin-left:10rpx;padding:5rpx 9rpx;border-radius:7rpx;background:#EEF4FB;color:#55739B;font-size:14rpx}.action{min-height:76rpx;padding:12rpx 14rpx;display:flex;align-items:center;border:1rpx solid #D9E3EC;border-radius:11rpx;background:#FBFDFF}.action>view{min-width:0;flex:1;display:flex;flex-direction:column}.action>view text:first-child{font-size:21rpx;font-weight:700}.action>view text:last-child{margin-top:5rpx;color:#8B98A8;font-size:15rpx}.binding{margin:0 10rpx;color:#52667C;font-size:16rpx}.chev{color:#9BA7B4;font-size:28rpx}.button{height:70rpx;margin-top:18rpx;display:flex;align-items:center;justify-content:center;border:1rpx solid rgba(47,120,246,.30);border-radius:12rpx;background:var(--app-color-primary-bg,#EDF5FF);color:var(--app-color-primary,#2F78F6);font-size:21rpx;font-weight:700}.footer-note{display:block;margin-top:22rpx;color:#8290A2;font-size:17rpx;line-height:1.55}
.statusbar-spacer{width:100%;background:var(--app-surface-strong,#FFF)}
</style>
