var storage = {}
var emitted = []
var path = require('path')
var url = require('url')
var register = require('node:module').register

register('./alias-loader.mjs', { parentURL: url.pathToFileURL(__filename).href })

global.uni = {
  getStorageSync: function(key) { return storage[key] || '' },
  setStorageSync: function(key, value) { storage[key] = value },
  $emit: function(name, payload) { emitted.push({ name: name, payload: payload }) },
}

;(async function() {
  var file = path.resolve(__dirname, '../utils/jianyingWorkbenchConfig.js')
  var mod = await import(url.pathToFileURL(file).href)
  var failed = 0
  function assert(condition, message) {
    if (condition) console.log('  PASS', message)
    else { console.log('  FAIL', message); failed++ }
  }

  var base = mod.defaultConfig()
  assert(base.version === 3, 'default config uses version 3')
  assert(base.revision === 0, 'default config starts with revision zero')
  assert(base.shortcuts.length === 8, 'default config contains a 2x4 shortcut grid')
  assert(base.shortcuts[0].label === '分割', 'default first shortcut is split')
  assert(base.timeline.swipeLeft === 'timeline_scroll_forward', 'swipe left uses normal timeline wheel scrolling by default')
  assert(base.timeline.pinchOut === 'timeline_zoom_in', 'pinch out zooms timeline by default')
  assert(base.timeline.swipeMultiplier === 1.4, 'one-finger wheel movement starts at a useful speed')
  assert(base.timeline.pinchMultiplier === 1, 'pinch zoom starts at one-times speed')
  assert(base.timelineButtons.length === 4, 'timeline has four independent shortcut buttons')
  assert(base.timelineButtons[0].label === '上一帧' && base.timelineButtons[3].label === '定位尾帧', 'timeline buttons use navigation defaults')

  var changed = mod.updateShortcut(base, 2, {
    id: 'custom', label: '自定义', type: 'shortcut', shortcut: { modifiers: ['ctrl'], key: 'k' },
  })
  assert(changed.shortcuts[2].label === '自定义', 'one shortcut can be updated')
  assert(changed.shortcuts[2].sub === 'Ctrl + K', 'shortcut subtitle is normalized')

  var timelineButtonChanged = mod.updateTimelineButton(changed, 2, {
    id: 'jy-timeline-3', label: '添加标记', type: 'shortcut', shortcut: { modifiers: [], key: 'm' },
  })
  assert(timelineButtonChanged.timelineButtons[2].label === '添加标记', 'timeline shortcut buttons are editable')
  assert(timelineButtonChanged.timelineButtons[2].sub === 'M', 'timeline shortcut button binding is normalized')

  var moved = mod.moveShortcut(timelineButtonChanged, 2, 0)
  assert(moved.shortcuts[0].label === '自定义', 'shortcuts can be reordered')
  assert(moved.shortcuts.length === 8, 'reordering preserves shortcut count')

  var timeline = mod.updateTimeline(moved, { sensitivity: 'sensitive', swipeMultiplier: 1.8, pinchMultiplier: 2.2, pinchOut: 'track_zoom_in' })
  assert(timeline.timeline.sensitivity === 'sensitive', 'gesture sensitivity is editable')
  assert(timeline.timeline.swipeMultiplier === 1.8, 'one-finger movement multiplier is editable')
  assert(timeline.timeline.pinchMultiplier === 2.2, 'pinch zoom multiplier is editable')
  assert(timeline.timeline.pinchOut === 'track_zoom_in', 'gesture meaning is editable')

  var malformed = mod.normalizeConfig({ shortcuts: [{}], timeline: { sensitivity: 'invalid', swipeLeft: 'invalid' } })
  assert(malformed.shortcuts.length === 8, 'malformed shortcut arrays are repaired')
  assert(malformed.timeline.sensitivity === 'medium', 'invalid sensitivity falls back to medium')
  assert(malformed.timeline.swipeMultiplier === 1.4, 'missing movement multiplier falls back safely')
  assert(malformed.timeline.swipeLeft === 'timeline_scroll_forward', 'invalid gesture action falls back safely')

  var saved = mod.saveWorkbenchConfig('layout:widget', timeline)
  var loaded = mod.loadWorkbenchConfig('layout:widget')
  assert(saved && saved.revision > 0, 'verified saves receive a new revision')
  assert(loaded.revision === saved.revision, 'saved revision is read back from storage')
  assert(loaded.shortcuts[0].label === '自定义', 'config persists by widget scope')
  assert(loaded.timeline.pinchOut === 'track_zoom_in', 'gesture config persists by widget scope')
  assert(emitted.length === 1 && emitted[0].name === mod.WORKBENCH_CONFIG_CHANGED_EVENT, 'verified save broadcasts a config change')
  assert(emitted[0].payload.scope === 'layout:widget', 'config change keeps the widget scope')

  var rawScope = 'layout:encoded-widget'
  var doubleEncodedScope = encodeURIComponent(encodeURIComponent(rawScope))
  var misplaced = mod.updateShortcut(base, 0, {
    id: 'jy-shortcut-1', label: '已迁移', type: 'shortcut', shortcut: { modifiers: ['ctrl'], key: 'c' },
  })
  misplaced.revision = 10
  storage[mod.STORAGE_PREFIX + doubleEncodedScope] = misplaced
  var migrated = mod.loadWorkbenchConfig(encodeURIComponent(rawScope))
  assert(mod.normalizeWorkbenchScope(doubleEncodedScope) === rawScope, 'encoded widget scopes normalize to one canonical value')
  assert(migrated.shortcuts[0].label === '已迁移', 'config saved under a double-encoded scope is recovered')
  assert(storage[mod.STORAGE_PREFIX + rawScope].shortcuts[0].label === '已迁移', 'recovered config migrates to the canonical storage key')
  var resaved = mod.saveWorkbenchConfig(doubleEncodedScope, migrated)
  assert(resaved && storage[mod.STORAGE_PREFIX + rawScope].revision === resaved.revision, 'future saves always use the canonical scope')
  assert(emitted[emitted.length - 1].payload.scope === rawScope, 'config events publish the canonical scope')

  storage[mod.LEGACY_STORAGE_PREFIX + 'legacy'] = { version: 1, rows: 6, cols: 6, controls: [] }
  var migrated = mod.loadWorkbenchConfig('legacy')
  assert(migrated.version === 3 && migrated.shortcuts.length === 8, 'legacy workbench config migrates to version 3')

  var versionTwo = mod.normalizeConfig({ version: 2, timeline: { swipeLeft: 'next_frame', swipeRight: 'previous_frame', swipeMultiplier: 1 } })
  assert(versionTwo.timeline.swipeLeft === 'timeline_scroll_forward', 'version 2 frame swipe migrates to normal wheel scrolling')
  assert(versionTwo.timeline.swipeMultiplier === 1.4, 'version 2 swipe speed migrates to the new wheel default')

  if (failed) process.exit(1)
  console.log('\n[test] ALL PASSED')
})().catch(function(error) {
  console.error(error)
  process.exit(1)
})
