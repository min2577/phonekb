<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="library-card">
    <view class="card-heading"><view class="heading-icon">库</view><view class="heading-copy"><text class="heading-title">预设模板</text><text class="heading-sub">一键导入布局库，按需切换使用</text></view></view>
  </view>

  <view v-if="archivedLayouts.length" class="template-list archived-list">
    <view class="archive-heading">已归档方案</view>
    <view v-for="item in archivedLayouts" :key="item.id" class="template-card">
      <view class="template-copy">
        <text class="template-name">{{ item.name }}</text>
        <text class="template-meta">{{ (item.pages || []).length }} 页 · 可恢复到快捷键方案</text>
      </view>
      <view class="template-btn install" :data-id="item.id" @tap="onRestore">恢复</view>
    </view>
  </view>

  <view class="template-list">
    <view v-for="(item, idx) in presets" :key="idx" class="template-card">
      <view class="template-copy">
        <text class="template-name">{{ item.name }}</text>
        <text class="template-meta">{{ item.summary }}</text>
      </view>
      <view v-if="isInstalled(item.id)" class="template-btn installed">已安装</view>
      <view v-else class="template-btn install" :data-id="item.id" @tap="onInstall">安装</view>
    </view>
  </view>

  <view class="footer-safe"></view>
</view>
</template>

<script>
let app = null
try { app = getApp({ allowDefault: true }) } catch (e) {}
import WS from '@/utils/net.js'
import { installCodeSmithLayout, isCodeSmithInstalled } from '@/utils/layoutConfig.js'

// 内置预设清单（与桌面端 presets/ 对应）
const BUILTIN_PRESETS = [
  { id: 'code-smith', kind: 'panel', name: 'Code Smith', summary: 'Codex Micro 控制台 · 固定布局与可编辑按键', shortcuts: [] },
  { id: 'vscode', name: 'VS Code', summary: '命令面板 Ctrl+Shift+P · 快速打开 Ctrl+P', shortcuts: [['格式化', 'Shift+Alt+F'], ['命令面板', 'Ctrl+Shift+P'], ['快速打开', 'Ctrl+P'], ['保存', 'Ctrl+S']] },
  { id: 'jetbrains', name: 'JetBrains IDE', summary: '查找 Ctrl+F · 重构 Ctrl+Alt+Shift+T', shortcuts: [['查找', 'Ctrl+F'], ['替换', 'Ctrl+R'], ['重构', 'Ctrl+Alt+Shift+T'], ['运行', 'Shift+F10']] },
  { id: 'chrome', name: 'Chrome / Edge', summary: '新标签 Ctrl+T · 关闭标签 Ctrl+W', shortcuts: [['新标签', 'Ctrl+T'], ['关闭标签', 'Ctrl+W'], ['刷新', 'Ctrl+R'], ['地址栏', 'Ctrl+L']] },
  { id: 'office', name: 'Office / WPS', summary: '保存 Ctrl+S · 加粗 Ctrl+B · 打印 Ctrl+P', shortcuts: [['保存', 'Ctrl+S'], ['撤销', 'Ctrl+Z'], ['加粗', 'Ctrl+B'], ['打印', 'Ctrl+P']] },
  { id: 'obs', name: 'OBS Studio', summary: '场景 Ctrl+1-4 · 录制 Ctrl+F9', shortcuts: [['场景 1', 'Ctrl+1'], ['场景 2', 'Ctrl+2'], ['开始录制', 'Ctrl+F9'], ['停止录制', 'Ctrl+F10']] },
  { id: 'vim', name: 'Vim', summary: '移动 h/j/k/l · 搜索 / · 退出 Esc', shortcuts: [['下一词', 'W'], ['上一词', 'B'], ['撤销', 'U'], ['退出', 'Esc']] },
  { id: 'terminal', name: '终端 / Shell', summary: '清屏 Ctrl+L · 终止 Ctrl+C · 补全 Tab', shortcuts: [['清屏', 'Ctrl+L'], ['终止', 'Ctrl+C'], ['挂起', 'Ctrl+Z'], ['补全', 'Tab']] },
  { id: 'windows', name: 'Windows 通用', summary: '分屏 Win+方向键 · 截图 Win+Shift+S', shortcuts: [['显示桌面', 'Win+D'], ['截图', 'Win+Shift+S'], ['锁屏', 'Win+L'], ['分屏左', 'Win+←']] },
]

const LOCAL_PRESET_KEY = 'phonekb.local_preset_ids'

function localPresetIds() {
  try { return uni.getStorageSync(LOCAL_PRESET_KEY) || [] } catch (e) { return [] }
}

function localLayout(preset) {
  return { id: preset.id, name: preset.name, pages: [{ id: 'main', name: '快捷键', slots: preset.shortcuts.map(function(item, index) {
    return { r: Math.floor(index / 4), c: index % 4, span: 1, key: { id: preset.id + '_' + index, label: item[0], sub: item[1], type: 'shortcut' } }
  }) }] }
}

export default {
  data() { return {
      statusBarHeight: 24,
    presets: BUILTIN_PRESETS,
    installedIds: [],
    archivedLayouts: [],
  } },

  onShow() {
    const cached = (() => { try { return uni.getStorageSync("phonekb.last_layouts") } catch (e) { return null } })()
    if (cached) this.applyLayouts(cached)
    if (WS.isConnected()) {
      // 离线安装过的模板在下次连上电脑时补同步，避免桌面布局覆盖手机本机记录。
      localPresetIds().forEach(function(id) {
        WS.send({ action: 'install_preset', preset_id: id })
      })
      WS.send({ action: 'reload_layouts' })
    }
  },

    onLoad() {
      try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {}
      const self = this
      this._onLayouts = function(data) { self.applyLayouts(data) }
      WS.onLayouts(this._onLayouts)
    },
    onUnload() {
      if (this._onLayouts) {
        WS.offLayouts(this._onLayouts)
        this._onLayouts = null
      }
    },
    methods: {
applyLayouts(data) {
    const installed = (data && data.layouts || []).filter(function(l) {
      return BUILTIN_PRESETS.find(function(p) { return p.id === l.id })
    }).map(function(l) { return l.id })
    const panelInstalled = isCodeSmithInstalled() ? ['code-smith'] : []
    this.installedIds = Array.from(new Set(installed.concat(localPresetIds(), panelInstalled)))
    if (data) this.archivedLayouts = (data.archived_layouts || []).slice()
  },
  onRestore(e) {
    const id = e.currentTarget.dataset.id
    const item = this.archivedLayouts.find(function(layout) { return layout.id === id })
    if (!item) return
    if (WS.isConnected()) {
      WS.send({ action: 'restore_layout', layout_id: id })
    } else {
      let cached = null
      try { cached = uni.getStorageSync('phonekb.last_layouts') } catch (error) {}
      cached = cached || { layouts: [], archived_layouts: [], global_pages: [] }
      cached.archived_layouts = (cached.archived_layouts || []).filter(function(layout) { return layout.id !== id })
      cached.layouts = (cached.layouts || []).concat([Object.assign({}, item, { local_only: true })])
      cached.active_layout_id = item.id
      cached.active_page_id = item.pages && item.pages[0] ? item.pages[0].id : null
      try { uni.setStorageSync('phonekb.last_layouts', cached) } catch (error) {}
      this.applyLayouts(cached)
    }
    uni.showToast({ title: '已恢复到快捷键方案', icon: 'success', duration: 900 })
  },
onInstall(e) {
    const id = e.currentTarget.dataset.id
    const self = this
    uni.showModal({
      title: "安装模板",
      content: "将在你的布局库中添加这个预设。",
      success: function(res) {
        if (res.confirm) {
          const preset = BUILTIN_PRESETS.find(function(item) { return item.id === id })
          if (!preset) return
          if (preset.kind === 'panel') {
            installCodeSmithLayout()
            self.applyLayouts(null)
            try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
            uni.showToast({ title: '已安装到面板库', icon: 'success', duration: 900 })
            return
          }
          const ids = localPresetIds()
          if (ids.indexOf(id) < 0) ids.push(id)
          try { uni.setStorageSync(LOCAL_PRESET_KEY, ids) } catch (e) {}
          let cached = null
          try { cached = uni.getStorageSync('phonekb.last_layouts') } catch (e) {}
          cached = cached || { layouts: [], global_pages: [], grid_rows: 4, grid_cols: 4 }
          cached.layouts = (cached.layouts || []).filter(function(layout) { return layout.id !== id }).concat([localLayout(preset)])
          try { uni.setStorageSync('phonekb.last_layouts', cached) } catch (e) {}
          self.applyLayouts(cached)
          if (WS.isConnected()) WS.send({ action: 'install_preset', preset_id: id })
          try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
          uni.showToast({ title: '已安装到本机', icon: 'success', duration: 800 })
        }
      },
    })
  },

  isInstalled(id) {
    return this.installedIds.indexOf(id) >= 0
  }
  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 20rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}
.library-card,
.template-card {
  margin: 0 8rpx 14rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 20rpx;
  box-shadow: 0 7rpx 20rpx rgba(47, 78, 113, 0.055);
}
.library-card {
  padding: 18rpx 20rpx;
}
.card-heading {
  display: flex;
  align-items: center;
}
.heading-icon,
.template-icon {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 19rpx;
  font-weight: 700;
}
.heading-icon {
  margin-right: 16rpx;
}
.heading-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
}
.heading-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.heading-sub {
  margin-top: 5rpx;
  color: #718196;
  font-size: 20rpx;
}
.template-card {
  min-height: 84rpx;
  padding: 14rpx 16rpx;
  display: flex;
  align-items: center;
}
.template-icon {
  margin-right: 12rpx;
}
.template-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.template-name {
  color: #172033;
  font-size: 24rpx;
  font-weight: 700;
}
.template-meta {
  margin-top: 4rpx;
  color: #6F7D91;
  font-size: 19rpx;
}
.template-btn {
  min-width: 78rpx;
  height: 48rpx;
  margin-left: 10rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  font-size: 19rpx;
  font-weight: 650;
}
.template-btn.install {
  background: #2F78F6;
  color: #FFFFFF;
  box-shadow: 0 6rpx 14rpx rgba(47, 120, 246, 0.18);
}
.template-btn.installed {
  border: 1rpx solid #DCE6F1;
  background: #F7FAFE;
  color: #7E8B9E;
}
.footer-safe {
  height: 30rpx;
}
.archived-list { margin-bottom: 24rpx; }
.archive-heading { margin: 0 10rpx 12rpx; color: #52657D; font-size: 22rpx; font-weight: 700; }

.statusbar-spacer { width: 100%; }
</style>
