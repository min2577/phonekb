const fs = require('fs')
const path = require('path')

const source = fs.readFileSync(path.resolve(__dirname, '../pages/panel/panel.vue'), 'utf8')

function assert(condition, message) {
  if (!condition) {
    console.error('  FAIL ' + message)
    process.exitCode = 1
    return
  }
  console.log('  PASS ' + message)
}

assert(
  (source.match(/@tap\.stop="onToggleWidgetFullscreen\(w\)"/g) || []).length === 1,
  'standard widgets use the shared centered modal action'
)
assert(
  source.includes('@tap.stop="onOpenFullscreenTrackpad"') &&
    source.includes('@tap.stop="onOpenFullscreenKeyboard"') &&
    source.includes('@tap.stop="pgOpenFullscreen"'),
  'mouse, keyboard, and gamepad keep their dedicated fullscreen actions'
)
assert(
  source.includes("v-if=\"!w.collapsed || fullscreenWidgetId === w.id\""),
  'opening a collapsed widget reveals its content without changing saved collapse state'
)
assert(
  source.includes("v-if=\"!keyboardFullscreen && !fullscreenWidgetId\""),
  'the custom tab bar is hidden behind a fullscreen widget'
)
assert(
  source.includes("if (this.fullscreenWidgetId) {\n      this.closeFullscreenWidget()\n      return true"),
  'Android back closes the widget before leaving the panel'
)
assert(
  source.includes('.panel-page .widget-slot.is-widget-fullscreen {') &&
    source.includes('position: fixed;') &&
    source.includes('backdrop-filter: blur(48px)') &&
    source.includes('align-items: center;') &&
    source.includes('justify-content: center;'),
  'the modal uses a strongly blurred, centered, full-screen interaction shield'
)
assert(
  source.includes('max-width: 920rpx;') &&
    source.includes('height: auto;') &&
    source.includes('max-height: calc(82vh - 96rpx);'),
  'the centered modal stays content-sized instead of stretching into a tall page'
)
assert(
  source.includes('class="widget-slot"') && source.includes('@tap.stop>') &&
    source.includes('class="widget-shell"') && source.includes('@tap.stop>'),
  'the modal shield and panel stop taps from reaching the background page'
)
assert(
  source.includes('@tap.stop="onToggleJianyingOrientation(w)"') &&
    source.includes('lockLandscape()') && source.includes('lockPortrait()'),
  'the fullscreen Jianying workbench can switch between landscape and portrait'
)
assert(
  source.includes(".widget-shell.is-jianying-workbench .jy-console") &&
    source.includes('grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.2fr);'),
  'the landscape Jianying workbench places shortcuts and timeline side by side'
)
assert(
  source.includes("'is-jianying-landscape': w.type === 'jianying-workbench'") &&
    source.includes('.widget-shell.is-jianying-workbench:not(.is-jianying-landscape) .jy-console') &&
    source.includes('grid-template-rows: repeat(2, 142rpx);'),
  'the portrait Jianying workbench restores a single-column scrollable layout'
)

if (process.exitCode) process.exit(process.exitCode)
console.log('\n[test] ALL PASSED')
