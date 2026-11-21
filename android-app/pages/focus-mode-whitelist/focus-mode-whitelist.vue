<template>
  <view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
    <view class="topbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">‹</view>
      <view class="topbar-center">
        <text class="topbar-title">白名单</text>
        <text class="topbar-subtitle">已选 {{ selectedCount }} 个</text>
      </view>
      <view class="topbar-done" hover-class="topbar-done-hover" @tap="onDone">
        <text class="topbar-done-text">完成</text>
      </view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">添加自定义包名</text>
        <text class="section-meta">高级</text>
      </view>
      <view class="custom-input-row">
        <input class="custom-input"
               v-model="customInput"
               placeholder="如 com.example.app"
               placeholder-class="custom-input-ph"
               confirm-type="done"
               @confirm="onAddCustom" />
        <view class="custom-add" hover-class="custom-add-hover" @tap="onAddCustom">
          <text class="custom-add-text">＋ 添加</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">常用应用</text>
        <text class="section-meta">{{ loading ? '加载中...' : '已选 ' + selectedPackageNames.length + ' / ' + installedApps.length }}</text>
      </view>
      <view class="app-list">
        <view v-if="loading" class="loading-row"><text class="loading-text">正在读取你手机上的应用...</text></view>
        <view v-else-if="installedApps.length === 0" class="loading-row"><text class="loading-text">未读取到应用 · 请确认 Android 权限</text></view>
        <view v-for="app in installedApps" :key="app.id"
              class="app-row"
              :class="{ 'is-selected': isSelected(app.id) }"
              hover-class="app-row-hover"
              @tap="onTogglePkg(app.packageName)">
          <view class="app-icon">
            <text class="app-icon-text">{{ app.icon }}</text>
          </view>
          <view class="app-info">
            <text class="app-name">{{ app.name }}</text>
            <text class="app-pkg">{{ app.packageName }}</text>
          </view>
          <view class="app-check">
            <text class="app-check-icon">{{ isPkgSelected(app.packageName) ? '✓' : '＋' }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="customOnly.length > 0" class="section">
      <view class="section-head">
        <text class="section-title">手动添加的包名</text>
        <text class="section-meta">{{ customOnly.length }} 个</text>
      </view>
      <view class="app-list">
        <view v-for="pkg in customOnly" :key="pkg"
              class="app-row is-selected"
              hover-class="app-row-hover"
              @tap="onRemoveCustom(pkg)">
          <view class="app-icon">
            <text class="app-icon-text">📦</text>
          </view>
          <view class="app-info">
            <text class="app-name">{{ pkg }}</text>
            <text class="app-pkg">点此移除</text>
          </view>
          <view class="app-check">
            <text class="app-check-icon">×</text>
          </view>
        </view>
      </view>
    </view>

    <view class="footer-hint">
      <text class="footer-hint-text">勾选的应用在锁机期间可正常使用,其他全部无法操作</text>
    </view>
    <view class="footer-safe"></view>
  </view>
</template>

<script>
import {
  loadConfig,
  saveConfig,
  PRESET_WHITELIST,
} from '@/utils/focusConfig.js'

// 调 5+ API 拿 Android 真实已安装应用列表
// 方案:用 launcher intent 查询"所有有桌面图标的 App"
//
// 为什么不用 getInstalledPackages(0)?
//   Android 11+ (API 30) 引入了 Package Visibility 限制:
//   不加 <queries> 标签或 QUERY_ALL_PACKAGES 权限,getInstalledPackages(0)
//   只会返回"自己 + 系统应用 + 少量被声明可见的应用",拿不到大部分用户 App。
//
// 为什么用 launcher intent?
//   ACTION_MAIN + CATEGORY_LAUNCHER 是 Android 公开的 launcher 查询 API,
//   不需要任何权限,也不需要 <queries> 声明。
//   缺点:拿不到"没有桌面图标的 App"(纯后台服务 / 系统组件),但用户能锁机的就是有桌面图标的 App,正合适。
//
// 返回数组的每一项: { id: 'user:<pkg>', name: '<显示名>', icon: '📦', packageName: '<pkg>' }
function loadInstalledAppsFromAndroid() {
  return new Promise(function (resolve) {
    var list = []
    try {
      if (typeof plus === 'undefined' || !plus.android) { resolve(list); return }
      var main = plus.android.runtimeMainActivity()
      var pm = main.getPackageManager()
      var Intent = plus.android.importClass('android.content.Intent')
      var intent = new Intent(Intent.ACTION_MAIN)
      intent.addCategory(Intent.CATEGORY_LAUNCHER)
      var activities = pm.queryIntentActivities(intent, 0)
      var n = activities.size()
      var myPkg = main.getPackageName()
      for (var i = 0; i < n; i++) {
        try {
          var r = activities.get(i)
          if (!r || !r.activityInfo) continue
          var ai = r.activityInfo.applicationInfo
          if (!ai) continue
          var pkgName = ai.packageName
          if (!pkgName || pkgName === myPkg) continue
          var label = r.loadLabel(pm)
          list.push({
            id: 'user:' + pkgName,
            name: String(label || pkgName),
            icon: '📦',
            packageName: pkgName,
          })
        } catch (e) { continue }
      }
      list.sort(function (a, b) { return a.name.localeCompare(b.name, 'zh-CN') })
    } catch (e) {
      console.warn('[focus-whitelist] loadInstalledApps failed', e)
    }
    resolve(list)
  })
}

export default {
  data() {
    return {
      statusBarHeight: 24,
      installedApps: [],
      loading: true,
      selectedPackageNames: [],
      customInput: '',
    }
  },
  computed: {
    selectedCount() {
      return this.selectedPackageNames.length
    },
    selectedPresetIds() {
      return PRESET_WHITELIST.filter(function (preset) {
        return this.selectedPackageNames.indexOf(preset.packageName) >= 0
      }.bind(this)).map(function (preset) { return preset.id })
    },
    customOnly() {
      var installed = new Set((this.installedApps || []).map(function (a) { return a.packageName }))
      return (this.selectedPackageNames || []).filter(function (p) { return installed.has(p) === false })
    },
  },
  onLoad() {
    const self = this
    try {
      const sys = uni.getSystemInfoSync()
      if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight
    } catch (e) {}
    var cfg = loadConfig()
    // 迁移旧配置:预置 id 与自定义包名统一成包名数组
    var presetNames = []
    var presetIds = Array.isArray(cfg.whitelistIds) ? cfg.whitelistIds : []
    presetIds.forEach(function (id) {
      var preset = PRESET_WHITELIST.find(function (item) { return item.id === id })
      if (preset && preset.packageName && presetNames.indexOf(preset.packageName) < 0) presetNames.push(preset.packageName)
    })
    var customs = Array.isArray(cfg.customPackages) ? cfg.customPackages.slice() : []
    customs.forEach(function (p) { if (presetNames.indexOf(p) < 0) presetNames.push(p) })
    self.selectedPackageNames = presetNames
    self.loading = true
    loadInstalledAppsFromAndroid().then(function (apps) {
      self.installedApps = apps
      self.loading = false
    })
  },
  methods: {
    onBack() {
      uni.navigateBack({ delta: 1 })
    },
    isSelected(id) {
      const preset = PRESET_WHITELIST.find(function (item) { return item.id === id })
      return !!preset && this.isPkgSelected(preset.packageName)
    },
    onTogglePreset(id) {
      const preset = PRESET_WHITELIST.find(function (item) { return item.id === id })
      if (preset) this.onTogglePkg(preset.packageName)
    },
    isPkgSelected(pkg) {
      return this.selectedPackageNames.indexOf(pkg) >= 0
    },
    onTogglePkg(pkg) {
      const i = this.selectedPackageNames.indexOf(pkg)
      if (i >= 0) this.selectedPackageNames.splice(i, 1)
      else this.selectedPackageNames.push(pkg)
      this._persistDraft()
    },
    onAddCustom() {
      const v = (this.customInput || '').trim()
      if (!v) {
        uni.showToast({ title: '包名不能为空', icon: 'none' })
        return
      }
      if (!/^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$/.test(v)) {
        uni.showToast({ title: '包名格式不对(像 com.example.app)', icon: 'none', duration: 1800 })
        return
      }
      if (this.selectedPackageNames.indexOf(v) >= 0) {
        uni.showToast({ title: '已存在', icon: 'none' })
        return
      }
      this.selectedPackageNames.push(v)
      this.customInput = ''
      this._persistDraft()
    },
    onRemoveCustom(pkg) {
      const i = this.selectedPackageNames.indexOf(pkg)
      if (i >= 0) this.selectedPackageNames.splice(i, 1)
      this._persistDraft()
    },
    _persistDraft() {
      // 实时保存草稿,这样即使不点"完成"也保留
      const cfg = loadConfig()
      cfg.whitelistIds = this.selectedPresetIds.slice()
      const presetPackages = PRESET_WHITELIST.map(function (item) { return item.packageName })
      cfg.customPackages = this.selectedPackageNames.filter(function (pkg) { return presetPackages.indexOf(pkg) < 0 })
      saveConfig(cfg)
    },
    onDone() {
      this._persistDraft()
      uni.navigateBack({ delta: 1 })
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
  box-sizing: border-box;
}

.topbar {
  min-height: 92rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,0.94);
  border-bottom: 1rpx solid #DCE6F1;
  position: sticky;
  top: 0;
  z-index: 10;
}
.topbar-back {
  width: 64rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #506177;
  font-size: 48rpx;
}
.topbar-back-hover { color: #2F78F6; }
.topbar-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rpx;
}
.topbar-title { font-size: 32rpx; font-weight: 750; color: #172033; }
.topbar-subtitle { font-size: 20rpx; color: #8996A7; }
.topbar-done {
  padding: 10rpx 24rpx;
  background: #2F78F6;
  border-radius: 999rpx;
}
.topbar-done-hover { background: #1E5BD0; }
.topbar-done-text { font-size: 26rpx; color: #FFFFFF; font-weight: 700; }

.section {
  margin: 24rpx 24rpx 0;
  padding: 22rpx 24rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(47, 78, 113, 0.05);
}
.section-head {
  min-height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}
.section-title { font-size: 24rpx; font-weight: 700; color: #53657B; letter-spacing: 0.5rpx; }
.section-meta {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #EEF4FA;
  color: #718196;
  font-size: 22rpx;
  font-weight: 650;
}

/* ===== custom input ===== */
.custom-input-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.custom-input {
  flex: 1;
  min-height: 80rpx;
  padding: 0 20rpx;
  background: #F1F5F9;
  border-radius: 14rpx;
  font-size: 26rpx;
  font-family: Consolas, monospace;
  color: #172033;
}
.custom-input-ph { color: #95A3B5; }
.custom-add {
  padding: 16rpx 24rpx;
  background: #2F78F6;
  border-radius: 14rpx;
}
.custom-add-hover { background: #1E5BD0; }
.custom-add-text { font-size: 26rpx; color: #FFFFFF; font-weight: 700; }

/* ===== app list ===== */
.app-list { display: flex; flex-direction: column; gap: 4rpx; }
.app-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding: 14rpx 8rpx;
  border-radius: 14rpx;
  border-top: 2rpx solid #E8EEF5;
  margin-top: -2rpx;
}
.app-row:first-child { border-top: none; margin-top: 0; }
.app-row-hover { background: #F7FAFE; }
.app-row.is-selected { background: rgba(47, 120, 246, 0.05); }
.app-icon {
  width: 72rpx; height: 72rpx;
  border-radius: 18rpx;
  background: #EEF4FA;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.app-icon-text { font-size: 36rpx; line-height: 1; }
.app-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2rpx; }
.app-name { font-size: 28rpx; font-weight: 700; color: #172033; }
.app-pkg { font-size: 20rpx; color: #95A3B5; font-family: Consolas, monospace; }
.app-check {
  width: 56rpx; height: 56rpx;
  border-radius: 50%;
  background: #F1F5F9;
  color: #95A3B5;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700;
}
.app-row.is-selected .app-check {
  background: #2F78F6;
  color: #FFFFFF;
}
.app-check-icon { font-size: 30rpx; line-height: 1; }

.footer-hint {
  margin: 28rpx 24rpx 0;
  padding: 14rpx 18rpx;
  background: rgba(245, 158, 11, 0.08);
  border-radius: 14rpx;
  border: 2rpx solid rgba(245, 158, 11, 0.20);
}
.footer-hint-text {
  font-size: 22rpx;
  color: #B95A18;
  line-height: 1.4;
}
.footer-safe { height: 48rpx; }
</style>
