<template>
  <view class="page">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
    <view class="brand">
      <text class="title">悬浮球测试</text>
      <text class="sub">最小验证 · 无功能 · 仅 showFloatingView / hideFloatingView</text>
    </view>

    <view class="section">
      <view class="section-title">控制</view>
      <button class="btn-primary" @tap="onShow">显示悬浮球</button>
      <button class="btn-secondary" @tap="onHide">隐藏悬浮球</button>
      <view class="hint">首次显示时 Android 会弹权限框,请允许显示在其他应用上层。</view>
    </view>

    <view class="section">
      <view class="section-title">日志</view>
      <scroll-view class="log" scroll-y="true">
        <text v-for="(line, i) in logs" :key="i" class="log-line">{{line}}</text>
      </scroll-view>
    </view>
  </view>
</template>

<script>
let HGFloatButton = null
try { HGFloatButton = uni.requireNativePlugin('HG-FloatButton') } catch (e) {}

export default {
  data() {
    return {
      statusBarHeight: 24,
      logs: ['[' + new Date().toLocaleTimeString() + '] 页面加载,HGFloatButton=' + (HGFloatButton ? 'OK' : 'NULL')]
    }
  },
  onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
    onShow() {
      if (!HGFloatButton) {
        this._log('ERR HG-FloatButton 模块未注册,检查 manifest.json nativePlugins')
        return
      }
      this._log('call showFloatingView()...')
      HGFloatButton.showFloatingView({ debug: false, backToMainUI: true }, (res) => {
        this._log('showFloatingView res=' + JSON.stringify(res))
      })
    },
    onHide() {
      if (!HGFloatButton) {
        this._log('ERR HG-FloatButton 模块未注册')
        return
      }
      this._log('call hideFloatingView()...')
      HGFloatButton.hideFloatingView({}, (res) => {
        this._log('hideFloatingView res=' + JSON.stringify(res))
      })
    },
    _log(line) {
      var ts = new Date().toLocaleTimeString()
      this.logs.unshift('[' + ts + '] ' + line)
      if (this.logs.length > 50) this.logs.length = 50
    }
  }
}
</script>

<style>
.page {
  min-height: 100vh;
  padding: 34rpx 24rpx 64rpx;
  background: radial-gradient(84% 38% at 50% 0%, rgba(47,120,246,0.13) 0%, rgba(244,248,253,0) 76%), var(--color-bg);
}
.brand { padding: 28rpx 18rpx 12rpx; text-align: center; }
.title { display: block; color: var(--color-text); font-size: 36rpx; font-weight: 700; }
.sub { display: block; margin-top: 10rpx; color: var(--color-text-mid); font-size: 23rpx; line-height: 1.5; }
.section {
  margin-top: 20rpx;
  padding: 26rpx;
  background: rgba(255,255,255,0.94);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: 26rpx;
  box-shadow: var(--shadow-fluent-2);
}
.section-title { margin-bottom: 18rpx; color: var(--color-text); font-size: 28rpx; font-weight: 650; }
.btn-primary,
.btn-secondary {
  margin-top: 12rpx;
  padding: 20rpx 24rpx;
  border-radius: 15rpx;
  text-align: center;
  font-size: 27rpx;
  font-weight: 600;
}
.btn-primary { color: #FFFFFF; background: var(--color-primary); box-shadow: 0 7rpx 16rpx rgba(47,120,246,0.20); }
.btn-secondary { color: var(--color-text); background: #F1F5FA; border: 1rpx solid #DCE6F1; }
.hint { margin-top: 18rpx; color: var(--color-text-light); font-size: 22rpx; line-height: 1.5; }
.log { height: 360rpx; padding: 18rpx; background: #F4F7FB; border: 1rpx solid #DCE6F1; border-radius: 16rpx; }
.log-line { display: block; padding: 6rpx 0; color: #44536A; font-family: Consolas, monospace; font-size: 21rpx; line-height: 1.5; }

.statusbar-spacer { width: 100%; }
</style>
