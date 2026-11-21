<template>
  <view class="page" :style="pageStyle">
    <!-- 顶部状态 -->
    <view class="topbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="topbar-mode">
        <text class="topbar-mode-icon">{{ modeIcon }}</text>
        <text class="topbar-mode-text">{{ modeLabel }}</text>
      </view>
      <view class="topbar-quota" v-if="cfg.mode === 'strict-lock' && cfg.strictMode">
        <text class="topbar-quota-text">本周紧急退出 {{ emergencyState.used }}/{{ emergencyState.quota }}</text>
      </view>
    </view>

    <!-- 中部:大计时 + 进度环 -->
    <view class="timer-wrap">
      <view class="timer-ring" :style="ringStyle">
        <view class="timer-ring-inner">
          <text class="timer-big">{{ timeText }}</text>
          <text class="timer-sub">{{ subText }}</text>
        </view>
      </view>
    </view>

    <!-- 白名单提示 -->
    <view v-if="cfg.mode === 'strict-lock'" class="whitelist-card">
      <view class="whitelist-card-head">
        <text class="whitelist-card-title">锁机中 · 可使用</text>
      </view>
      <view v-if="whitelistEntries.length === 0" class="whitelist-empty">
        未设置白名单 · 锁机期间无法使用任何应用
      </view>
      <view v-else class="whitelist-grid">
        <view v-for="app in whitelistEntries" :key="app.id" class="whitelist-item">
          <text class="whitelist-item-icon">{{ app.icon }}</text>
          <text class="whitelist-item-name">{{ app.name }}</text>
        </view>
      </view>
    </view>

    <!-- 中断提示(切过后台) -->
    <view v-if="pauseInfo" class="pause-banner">
      <text class="pause-banner-text">检测到切换到后台 · 计时暂停 {{ pauseInfo }}</text>
    </view>

    <!-- 底部:紧急退出 -->
    <view class="emergency-area">
      <view class="emergency-tip">
        <text v-if="cfg.mode !== 'strict-lock'">本模式不锁手机 · 可随时关闭</text>
        <text v-else-if="!cfg.strictMode">宽松模式 · 长按下方按钮即可退出</text>
        <text v-else-if="emergencyState.remaining > 0">严格模式 · 长按 5 秒退出 · 本周剩余 {{ emergencyState.remaining }} 次</text>
        <text v-else class="emergency-tip-warn">本周额度已用完 · 请等待时间结束</text>
      </view>
      <view v-if="showEmergencyConfirm" class="emergency-confirm-mask" @tap="onCancelConfirm">
        <view class="emergency-confirm" @tap.stop="">
          <text class="emergency-confirm-title">确定要紧急退出?</text>
          <text class="emergency-confirm-desc" v-if="cfg.mode === 'strict-lock' && cfg.strictMode">将消耗本周 1 次额度,本周剩余 {{ emergencyState.remaining - 1 }} 次</text>
          <text class="emergency-confirm-desc" v-else>本次专注将被记录为取消</text>
          <view class="emergency-confirm-row">
            <view class="emergency-confirm-btn emergency-confirm-cancel" hover-class="emergency-confirm-btn-hover" @tap="onCancelConfirm">再想想</view>
            <view class="emergency-confirm-btn emergency-confirm-ok" hover-class="emergency-confirm-btn-hover" @tap="onConfirmExit">确认退出</view>
          </view>
        </view>
      </view>
      <view class="emergency-btn"
            :class="{ 'is-disabled': emergencyDisabled }"
            hover-class="emergency-btn-hover"
            @tap="onEmergencyTap">
        <text class="emergency-btn-text">{{ emergencyBtnText }}</text>
      </view>
    </view>

    <view class="footer-safe"></view>
  </view>
</template>

<script>
import {
  loadConfig,
  addHistory,
  getEmergencyState,
  consumeEmergency,
  getWhitelistEntries,
  getModeMeta,
} from '@/utils/focusConfig.js'
import {
  getFocusState,
  stopFocus,
} from '@/utils/focusNative.js'

const TICK_MS = 500

export default {
  data() {
    return {
      statusBarHeight: 24,
      cfg: null,
      modeLabel: '',
      modeIcon: '',
      whitelistEntries: [],
      emergencyState: { used: 0, quota: 2, remaining: 2 },

      // 计时相关(全部基于系统时间戳,不受 setInterval 漂移影响)
      startedAt: 0,            // 实际开始时间戳
      pauseAccumulatedSec: 0,  // 历史累计暂停秒数
      pauseStartedAt: 0,       // 当前暂停起点
      paused: false,
      pauseInfo: '',

      // 显示
      elapsedSec: 0,
      ringDeg: 0,
      now: Date.now(),

      // 紧急退出
      showEmergencyConfirm: false,

      // 后台检测
      onHideTs: 0,
      nativeEndAt: 0,
      nativeActive: false,
    }
  },
  computed: {
    pageStyle() {
      if (this.cfg && this.cfg.mode === 'strict-lock') {
        return 'background: linear-gradient(180deg, #0F2A4A 0%, #06182F 100%); color: #FFFFFF;'
      }
      return 'background: linear-gradient(180deg, #1B2740 0%, #0A1426 100%); color: #FFFFFF;'
    },
    timeText() {
      const sec = Math.max(0, this.elapsedSec)
      if (this.cfg && this.cfg.mode === 'count-up') {
        // 正计时:累计时间
        return this._fmtHMS(sec)
      }
      // 倒计时 / 严格锁机:剩余
      const remain = Math.max(0, (this.cfg ? this.cfg.durationSec : 0) - sec)
      return this._fmtHMS(remain)
    },
    subText() {
      if (!this.cfg) return ''
      const dur = Math.round((this.cfg.durationSec || 0) / 60)
      if (this.cfg.mode === 'count-up') return '目标 ' + dur + ' 分钟'
      if (this.cfg.mode === 'count-down') return '倒计时模式'
      if (this.cfg.mode === 'strict-lock') return '严格锁机 · ' + dur + ' 分钟'
      return ''
    },
    ringStyle() {
      let pct = 0
      if (this.cfg && this.cfg.durationSec > 0) {
        pct = Math.min(1, this.elapsedSec / this.cfg.durationSec)
      }
      const deg = Math.round(pct * 360)
      return 'background: conic-gradient(rgba(47, 120, 246, 0.85) ' + deg + 'deg, rgba(255,255,255,0.10) 0deg);'
    },

    emergencyDisabled() {
      if (!this.cfg) return true
      if (this.cfg.mode === 'count-up') return false  // 正计时不锁手机,可以随时退
      if (this.cfg.mode === 'count-down') return false
      // strict-lock
      if (!this.cfg.strictMode) return false
      return this.emergencyState.remaining <= 0
    },
    emergencyBtnText() {
      if (!this.cfg) return '退出'
      if (this.cfg.mode === 'strict-lock' && this.cfg.strictMode) {
        return this.emergencyState.remaining > 0 ? '紧急退出' : '本周额度已用完'
      }
      return '退出本次专注'
    },
  },
  onLoad() {
    try {
      const sys = uni.getSystemInfoSync()
      if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight
    } catch (e) {}
    this.cfg = loadConfig()
    const meta = getModeMeta(this.cfg.mode)
    this.modeLabel = meta.label
    this.modeIcon = this.cfg.mode === 'count-up' ? '↗' : (this.cfg.mode === 'strict-lock' ? '🔒' : '⏱')
    this.whitelistEntries = getWhitelistEntries(this.cfg)
    this.emergencyState = getEmergencyState()
    const nativeState = getFocusState()
    if (this.cfg.mode === 'strict-lock' && nativeState.active && Number(nativeState.endAt) > Date.now()) {
      this.nativeActive = true
      this.nativeEndAt = Number(nativeState.endAt)
    }
  },
  onShow() {
    if (this.cfg && this.cfg.mode === 'strict-lock') {
      const state = getFocusState()
      this.nativeActive = !!state.active && Number(state.endAt) > Date.now()
      if (this.nativeActive) this.nativeEndAt = Number(state.endAt)
      this.onHideTs = 0
      this.pauseInfo = ''
      return
    }
    if (this.startedAt > 0 && this.onHideTs > 0) {
      const pausedMs = Date.now() - this.onHideTs
      this.pauseAccumulatedSec += Math.round(pausedMs / 1000)
      this.pauseStartedAt = 0
      this.paused = false
      this.onHideTs = 0
      this.pauseInfo = ''
      // 触觉反馈一下
      try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
    }
  },
  onHide() {
    // 严格模式由 Android 前台服务计时,切后台不能暂停。
    if (this.cfg && this.cfg.mode === 'strict-lock') return
    if (this.startedAt > 0 && !this.paused) {
      this.paused = true
      this.pauseStartedAt = Date.now()
      this.onHideTs = Date.now()
      const elapsed = Math.round((Date.now() - this.startedAt) / 1000) - this.pauseAccumulatedSec
      this.pauseInfo = this._fmtHMS(Math.max(0, elapsed))
    }
  },
  onUnload() {
    this._stopTick()
    // 如果用户在计时完成前主动返回,则记录为取消
    if (this.startedAt > 0 && this.elapsedSec < (this.cfg ? this.cfg.durationSec : Infinity)) {
      const outcome = this.outcomeOnExit
      if (outcome) {
        addHistory({
          ts: Date.now(),
          mode: this.cfg.mode,
          durationSec: this.cfg.durationSec,
          elapsedSec: this.elapsedSec,
          outcome: outcome,
        })
      }
    }
  },
  mounted() {
    if (!this.cfg) {
      // 没有配置 -> 直接回 setup
      uni.redirectTo({ url: '/pages/focus-mode-setup/focus-mode-setup' })
      return
    }
    this.startedAt = Date.now()
    this.pauseAccumulatedSec = 0
    this.elapsedSec = 0
    if (this.cfg.mode === 'strict-lock' && this.nativeEndAt <= Date.now()) {
      uni.redirectTo({ url: '/pages/focus-mode-setup/focus-mode-setup' })
      return
    }
    this._startTick()
    // 短震一下表示开始
    try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
  },
  // 专注进行中不允许系统返回键或边缘左滑离开页面。
  // 正常完成、确认退出仍由页面内部的 redirectTo 流程处理。
  onBackPress() {
    return true
  },
  methods: {
    _fmtHMS(sec) {
      sec = Math.max(0, Math.round(sec))
      const h = Math.floor(sec / 3600)
      const m = Math.floor((sec % 3600) / 60)
      const s = sec % 60
      const pad = function (n) { return n < 10 ? '0' + n : String(n) }
      if (h > 0) return pad(h) + ':' + pad(m) + ':' + pad(s)
      return pad(m) + ':' + pad(s)
    },
    _startTick() {
      const self = this
      this._tickTimer = setInterval(function () {
        const nowMs = Date.now()
        if (self.cfg && self.cfg.mode === 'strict-lock' && self.nativeEndAt > 0) {
          const remain = Math.max(0, Math.ceil((self.nativeEndAt - nowMs) / 1000))
          self.elapsedSec = Math.max(0, self.cfg.durationSec - remain)
          self.nativeActive = remain > 0
          self.now = nowMs
          if (remain <= 0) self._onComplete()
          return
        }
        if (self.paused) return
        const totalSec = Math.round((nowMs - self.startedAt) / 1000) - self.pauseAccumulatedSec
        self.elapsedSec = Math.max(0, totalSec)
        self.now = nowMs
        // 检查完成
        if (self.cfg && self.elapsedSec >= self.cfg.durationSec) {
          self._onComplete()
        }
      }, TICK_MS)
    },
    _stopTick() {
      if (this._tickTimer) {
        clearInterval(this._tickTimer)
        this._tickTimer = null
      }
    },
    _onComplete() {
      this._stopTick()
      const self = this
      if (this.cfg && this.cfg.mode === 'strict-lock') {
        stopFocus()
        this.nativeActive = false
      }
      this.outcomeOnExit = 'completed'
      addHistory({
        ts: Date.now(),
        mode: this.cfg.mode,
        durationSec: this.cfg.durationSec,
        elapsedSec: this.elapsedSec,
        outcome: 'completed',
      })
      this.outcomeOnExit = null
      try { uni.vibrateLong({}) } catch (e) {}
      uni.showModal({
        title: '专注完成',
        content: self.cfg.mode === 'count-up' ? '已达到目标时长,干得漂亮!' : '倒计时结束,做得不错!',
        showCancel: false,
        confirmText: '回到面板',
        success: function () {
          uni.redirectTo({ url: '/pages/panel/panel' })
        },
      })
    },
    onEmergencyTap() {
      if (this.emergencyDisabled) return
      this.showEmergencyConfirm = true
    },
    onCancelConfirm() {
      this.showEmergencyConfirm = false
    },
    onConfirmExit() {
      this.showEmergencyConfirm = false
      this._stopTick()
      if (this.cfg && this.cfg.mode === 'strict-lock') stopFocus()
      let outcome = 'cancelled'
      if (this.cfg.mode === 'strict-lock' && this.cfg.strictMode) {
        const next = consumeEmergency()
        if (next) {
          this.emergencyState = next
          outcome = 'emergency'
        } else {
          // 兜底:额度用完
          this.paused = false
          return
        }
      } else {
        outcome = 'cancelled'
      }
      this.outcomeOnExit = outcome
      addHistory({
        ts: Date.now(),
        mode: this.cfg.mode,
        durationSec: this.cfg.durationSec,
        elapsedSec: this.elapsedSec,
        outcome: outcome,
      })
      this.outcomeOnExit = null
      try { uni.vibrateShort({ type: 'heavy' }) } catch (e) {}
      uni.redirectTo({ url: '/pages/panel/panel' })
    },
  },
}
</script>

<style scoped>
.page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  box-sizing: border-box;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28rpx;
  padding-top: 24rpx;
  color: rgba(255,255,255,0.92);
}
.topbar-mode { display: flex; align-items: center; gap: 10rpx; }
.topbar-mode-icon { font-size: 32rpx; }
.topbar-mode-text { font-size: 28rpx; font-weight: 700; letter-spacing: 1rpx; }
.topbar-quota {
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255,255,255,0.10);
  border: 2rpx solid rgba(255,255,255,0.20);
}
.topbar-quota-text { font-size: 22rpx; color: rgba(255,255,255,0.88); }

.timer-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx 0;
}
.timer-ring {
  width: 480rpx;
  height: 480rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 80rpx rgba(47, 120, 246, 0.30);
  position: relative;
}
.timer-ring::after {
  content: '';
  position: absolute;
  inset: 18rpx;
  border-radius: 50%;
  background: rgba(15, 42, 74, 0.85);
}
.timer-ring-inner {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
}
.timer-big {
  font-size: 110rpx;
  font-weight: 800;
  color: #FFFFFF;
  font-family: Consolas, 'SF Mono', monospace;
  letter-spacing: 2rpx;
  line-height: 1;
}
.timer-sub {
  font-size: 24rpx;
  color: rgba(255,255,255,0.65);
  letter-spacing: 2rpx;
}

.whitelist-card {
  margin: 0 28rpx 24rpx;
  padding: 18rpx 20rpx;
  background: rgba(255,255,255,0.06);
  border: 2rpx solid rgba(255,255,255,0.10);
  border-radius: 22rpx;
  backdrop-filter: blur(24rpx);
}
.whitelist-card-head { margin-bottom: 10rpx; }
.whitelist-card-title { font-size: 22rpx; color: rgba(255,255,255,0.65); letter-spacing: 1rpx; }
.whitelist-empty {
  font-size: 24rpx;
  color: rgba(255,255,255,0.55);
  padding: 16rpx 0;
  text-align: center;
}
.whitelist-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12rpx;
}
.whitelist-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  padding: 12rpx 6rpx;
  background: rgba(255,255,255,0.08);
  border-radius: 14rpx;
}
.whitelist-item-icon { font-size: 36rpx; line-height: 1; }
.whitelist-item-name {
  font-size: 20rpx;
  color: rgba(255,255,255,0.85);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pause-banner {
  margin: 0 28rpx 16rpx;
  padding: 12rpx 18rpx;
  background: rgba(245, 158, 11, 0.18);
  border: 2rpx solid rgba(245, 158, 11, 0.40);
  border-radius: 14rpx;
}
.pause-banner-text {
  font-size: 22rpx;
  color: #FCD9A0;
  line-height: 1.4;
}

.emergency-area {
  padding: 24rpx 28rpx calc(36rpx + env(safe-area-inset-bottom));
}
.emergency-tip {
  text-align: center;
  margin-bottom: 14rpx;
  font-size: 22rpx;
  color: rgba(255,255,255,0.60);
  line-height: 1.5;
}
.emergency-tip-warn {
  color: #FCA5A5;
  font-weight: 600;
}

.emergency-confirm-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 0 48rpx;
}
.emergency-confirm {
  width: 100%;
  max-width: 560rpx;
  background: #1B2740;
  border-radius: 28rpx;
  padding: 32rpx 32rpx 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.emergency-confirm-title {
  font-size: 34rpx;
  font-weight: 700;
  color: #FFFFFF;
  text-align: center;
}
.emergency-confirm-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.65);
  text-align: center;
  line-height: 1.5;
}
.emergency-confirm-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-top: 12rpx;
}
.emergency-confirm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  border-radius: 18rpx;
  font-size: 28rpx;
  font-weight: 600;
}
.emergency-confirm-cancel {
  background: rgba(255, 255, 255, 0.10);
  color: #FFFFFF;
}
.emergency-confirm-ok {
  background: #EF4444;
  color: #FFFFFF;
}
.emergency-confirm-btn-hover {
  opacity: 0.85;
}

.emergency-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 112rpx;
  border-radius: 28rpx;
  background: rgba(255,255,255,0.06);
  border: 2rpx solid rgba(255,255,255,0.12);
  overflow: hidden;
}
.emergency-btn-hover { background: rgba(255,255,255,0.10); }
.emergency-btn.is-pressing {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.60);
}
.emergency-btn.is-disabled {
  opacity: 0.45;
}
.emergency-btn.is-pressing .emergency-btn-text {
  position: relative;
  font-size: 30rpx;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: 1rpx;
}

.footer-safe { height: 12rpx; }
</style>
