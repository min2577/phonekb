const fs = require('fs')
const path = require('path')

const editor = fs.readFileSync(path.resolve(__dirname, '../pages/layout/edit-key.vue'), 'utf8')
const workbench = fs.readFileSync(path.resolve(__dirname, '../pages/jianying-workbench-edit/jianying-workbench-edit.vue'), 'utf8')
const panelWorkbench = fs.readFileSync(path.resolve(__dirname, '../components/PanelJianyingWorkbench.vue'), 'utf8')
const gestureEditor = fs.readFileSync(path.resolve(__dirname, '../pages/jianying-gestures-edit/jianying-gestures-edit.vue'), 'utf8')
const panel = fs.readFileSync(path.resolve(__dirname, '../pages/panel/panel.vue'), 'utf8')

function assert(condition, message) {
  if (!condition) {
    console.error('  FAIL ' + message)
    process.exitCode = 1
    return
  }
  console.log('  PASS ' + message)
}

assert(
  editor.includes('class="editor-safe-top"') && editor.includes('statusBarHeight'),
  'shortcut editor reserves the native status-bar safe area'
)
assert(
  !editor.includes('class="input icon-input"') && !editor.includes('onIconInput'),
  'shortcut editor no longer exposes icon editing'
)
assert(
  (editor.match(/this\.label = p\.label \|\| this\.label/g) || []).length >= 2,
  'choosing built-in or newly created presets updates the button name'
)
assert(
  editor.includes("channel.emit('saved'") && workbench.includes('events: {') && workbench.includes('saved(payload)'),
  'Jianying shortcut saves refresh the workbench before navigation returns'
)
assert(
  editor.includes('const shortcutMatches = savedItem') && editor.includes('保存失败，请重试'),
  'shortcut editor verifies the persisted slot before navigating back'
)
assert(
  workbench.includes('class="jy-statusbar-spacer"') && workbench.includes('nativeStatusBarHeight()') && !workbench.includes('height: calc(100vh - 92rpx)'),
  'workbench editor reserves the real status bar and lets the content flex'
)
assert(
  workbench.includes('WORKBENCH_CONFIG_CHANGED_EVENT') && panelWorkbench.includes('WORKBENCH_CONFIG_CHANGED_EVENT'),
  'editor and control widget subscribe to verified config changes'
)
assert(
  editor.includes('normalizeWorkbenchScope(opts.scope)') && workbench.includes('normalizeWorkbenchScope(options && options.scope)'),
  'nested editor routes share one canonical widget scope'
)
assert(
  panelWorkbench.includes('sendDirectionalActions') && !panelWorkbench.includes('pendingActions'),
  'timeline gestures send immediately instead of waiting for a render frame'
)
assert(
  panelWorkbench.includes('this.config.timeline.swipeMultiplier') && gestureEditor.includes('saveSwipeMultiplier') && gestureEditor.includes('savePinchMultiplier'),
  'timeline speed and pinch response have persisted continuous controls'
)
assert(
  gestureEditor.includes('getWindowInfo') && gestureEditor.includes('statusbar-spacer'),
  'gesture editor reserves the native status-bar safe area'
)
assert(
  editor.includes('updateTimelineButton') && editor.includes("this.jianyingArea === 'timeline'") && workbench.includes('editTimelineButton(index)'),
  'all four timeline shortcut buttons reuse the verified Jianying shortcut editor'
)
assert(
  panelWorkbench.includes('config.timelineButtons[0]') && panelWorkbench.includes('config.timelineButtons[3]'),
  'control widget renders all four editable timeline shortcut buttons'
)
assert(
  editor.includes('comboIntervalMs: 50') && editor.includes('macro: { interval_ms: this.comboIntervalMs, steps: steps }'),
  'multi-step editor saves a default uniform interval'
)
assert(
  panel.includes("uni.getStorageSync('phonekb.active_layout_page')") && panel.includes('self.activeLayoutId = String(selection.activeLayoutId)'),
  'panel restores the selected shortcut layout when shown again'
)

if (process.exitCode) process.exit(process.exitCode)
console.log('\n[test] ALL PASSED')
