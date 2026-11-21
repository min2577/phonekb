<script>
import BT from '@/utils/btclient.js'
import Net from '@/utils/net.js'
import { applyCurrentPageAppearance, installAppearanceRuntime } from '@/utils/appearanceConfig.js'
import { lockLandscape, lockPortrait } from '@/utils/orientation.js'
import { installFeedbackRuntime, loadSettings } from '@/utils/appSettings.js'
import { getFocusState } from '@/utils/focusNative.js'

export default {
  globalData: {
    appVersion: '0.3.3',
    host: '',
    port: 9876,
    code: '',
    token: null,
    settings: null,
  },
  onLaunch() {
    lockPortrait()
    installAppearanceRuntime()
    installFeedbackRuntime()
    try { BT.init() } catch (e) { console.error('[phonekb] BLE.init fail', e) }
    try {
      this.globalData.settings = loadSettings()
    } catch (e) {}
    try {
      const last = uni.getStorageSync('phonekb.last_host')
      if (last) this.globalData.host = last
      const lastCode = uni.getStorageSync('phonekb.last_code')
      if (lastCode) this.globalData.code = lastCode
    } catch (e) {}
    const self = this
    setTimeout(function() {
      try {
        if (loadSettings().autoReconnect === false) return
        if (Net.isConnected()) return
        const mode = Net.getMode()
        if (mode === 'ble') {
          BT.restoreConnection({
            onConnected: function() { console.log('[phonekb] restored Bluetooth connection') },
            onError: function(error) { console.warn('[phonekb] Bluetooth restore failed', error) },
            onDisconnected: function() { console.warn('[phonekb] Bluetooth disconnected; reconnect scheduled') },
          }).catch(function(error) { console.warn('[phonekb] no Bluetooth connection restored', error) })
          return
        }
        const options = {
          host: mode === 'usb' ? '127.0.0.1' : self.globalData.host,
          port: mode === 'usb' ? 9877 : (self.globalData.port || 9876),
          code: mode === 'usb' ? 'USB_LOCAL_TRUST' : self.globalData.code,
          token: mode === 'usb' ? null : (self.globalData.token || null),
          onConnected: function() { console.log('[phonekb] restored ' + mode + ' connection') },
          onError: function(error) { console.warn('[phonekb] restore connection failed', error) },
          onDisconnected: function() { console.warn('[phonekb] restored connection disconnected') },
        }
        if (mode === 'usb' || (options.host && options.code)) Net.connect(options)
      } catch (e) {
        console.error('[phonekb] auto connect failed', e)
      }
    }, 350)
    console.log('[phonekb] app launched, settings=', this.globalData.settings)
  },
  onShow() {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages.length ? String(pages[pages.length - 1].route || '') : ''
    // 最近任务被划掉后,系统可能从默认入口重新创建应用;锁定仍有效时必须回到锁定页。
    if (current !== 'pages/focus-mode-running/focus-mode-running') {
      try {
        const focus = getFocusState()
        if (focus && focus.active && Number(focus.endAt) > Date.now()) {
          uni.redirectTo({ url: '/pages/focus-mode-running/focus-mode-running' })
          return
        }
      } catch (e) {}
    }
    if (current === 'pages/gamepad/gamepad' || current === 'pages/full-keyboard/full-keyboard') {
      lockLandscape()
    } else {
      lockPortrait()
    }
    setTimeout(function() { applyCurrentPageAppearance() }, 0)
  }
}
</script>

<style>
/* 全局样式 */
page {
  background-color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 14px;
  color: #222;
  height: 100%;
}
view, text, button, input { box-sizing: border-box; }

.app-appearance-active .section,
.app-appearance-active .widget-shell,
.app-appearance-active .user-card,
.app-appearance-active .quick-card,
.app-appearance-active .list-card,
.app-appearance-active .account-card,
.app-appearance-active .layout-card,
.app-appearance-active .template-item,
.app-appearance-active .template-card,
.app-appearance-active .device-row,
.app-appearance-active .mode-item,
.app-appearance-active .task-summary,
.app-appearance-active .settings-card,
.app-appearance-active .panel-card,
.app-appearance-active .editor-card,
.app-appearance-active .input-card,
.app-appearance-active .form-card,
.app-appearance-active .sheet-card,
.app-appearance-active .add-card,
.app-appearance-active .type-btn,
.app-appearance-active .preset-chip,
.app-appearance-active .key-chip,
.app-appearance-active .key-btn,
.app-appearance-active .tp-pad,
.app-appearance-active .tp-btn,
.app-appearance-active .step-btn,
.app-appearance-active .more-btn,
.app-appearance-active .widget-head,
.app-appearance-active .widget-head-action,
.app-appearance-active .widget-head-toggle,
.app-appearance-active .widget-head-fullscreen,
.app-appearance-active .widget-head-switch,
.app-appearance-active .preview-section,
.app-appearance-active .templates-section,
.app-appearance-active .custom-tabbar,
.app-appearance-active .config-bar,
.app-appearance-active .topbar {
  background-color: var(--app-surface) !important;
  border-color: var(--app-color-border) !important;
}

.app-appearance-active .modal,
.app-appearance-active .prompt-panel,
.app-appearance-active .result-panel,
.app-appearance-active input,
.app-appearance-active textarea,
.app-appearance-active .input,
.app-appearance-active .form-input {
  background-color: var(--app-surface-strong) !important;
  border-color: var(--app-color-border) !important;
  color: var(--app-color-text) !important;
}

.app-appearance-active .section-title,
.app-appearance-active .label,
.app-appearance-active .account-name,
.app-appearance-active .user-name,
.app-appearance-active .list-label,
.app-appearance-active .quick-label,
.app-appearance-active .template-name,
.app-appearance-active .modal-title,
.app-appearance-active .topbar-title {
  color: var(--app-color-text) !important;
}

.app-appearance-active .widget-head-title,
.app-appearance-active .key-label,
.app-appearance-active .card-title,
.app-appearance-active .heading-title,
.app-appearance-active .panel-title {
  color: var(--app-color-text) !important;
}

.app-appearance-active .account-sub,
.app-appearance-active .user-sub,
.app-appearance-active .quick-sub,
.app-appearance-active .template-meta,
.app-appearance-active .hint,
.app-appearance-active .subtitle {
  color: var(--app-color-text-mid) !important;
}

.app-appearance-active .key-sub,
.app-appearance-active .widget-head-sub,
.app-appearance-active .card-sub,
.app-appearance-active .heading-sub {
  color: var(--app-color-text-mid) !important;
}

.app-appearance-active .tp-hint,
.app-appearance-active .tp-btn,
.app-appearance-active .tp-btn-icon {
  color: var(--app-color-text-mid) !important;
}

.app-appearance-active.panel-page {
  --panel-card: var(--app-surface);
  --panel-surface: var(--app-surface);
  --panel-surface-strong: var(--app-surface-strong);
  --panel-text: var(--app-color-text);
  --panel-text-mid: var(--app-color-text-mid);
  --panel-text-light: var(--app-color-text-light);
}

.app-appearance-active.page {
  color: var(--app-color-text);
  background-color: var(--app-page-bg-color) !important;
  background-image: var(--app-page-bg-image) !important;
  background-repeat: no-repeat !important;
  background-position: var(--app-page-bg-position) !important;
  background-size: var(--app-page-bg-size) !important;
}
.app-has-custom-background.page::before {
  display: none !important;
}
.app-dark .row,
.app-dark .account-row,
.app-dark .list-divider,
.app-dark .quick-divider {
  border-color: var(--app-color-divider) !important;
}
.app-dark .row-hover,
.app-dark .list-item-hover,
.app-dark .quick-item-hover,
.app-dark .widget-head-hover {
  background-color: rgba(255,255,255,0.06) !important;
}
</style>
