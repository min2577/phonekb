global.uni = (function() {
  var values = {}
  return {
    getStorageSync: function(key) { return values[key] },
    setStorageSync: function(key, value) { values[key] = JSON.parse(JSON.stringify(value)) },
    removeStorageSync: function(key) { delete values[key] },
  }
})()

;(async function() {
  var Store = await import('../utils/gamepadEditorStore.js')
  var state = Store.normalizeLayouts({ version: 3, activeLayoutId: 'one', layouts: [{ id: 'one', name: '测试', controls: [] }] })
  var builtIns = Store.loadPresets().filter(function(item) { return item.builtIn })
  if (builtIns.length < 20) throw new Error('built-in button library is too small')
  if (new Set(builtIns.map(function(item) { return item.control.appearance.skin })).size < 12) throw new Error('button library does not cover all skins')
  var preset = builtIns[0]
  var control = Store.controlFromPreset(preset, { x: 33, y: 66 })
  state.layouts[0].controls.push(control)
  state = Store.saveLayouts(state)
  if (state.layouts[0].controls[0].x !== 33) throw new Error('control position was not preserved')
  if (!Store.pendingLayouts()) throw new Error('pending layouts were not recorded')

  control.appearance.skin = 'neon'
  control.behavior = 'tap'
  var custom = Store.savePreset('霓虹测试', control)
  if (!custom || Store.loadPresets().filter(function(item) { return !item.builtIn }).length !== 1) throw new Error('custom preset was not saved')

  var next = Store.createLayout(state, '副本', state.layouts[0])
  if (next.layouts.length !== 2 || next.activeLayoutId === 'one') throw new Error('layout copy failed')
  if (next.layouts[1].controls[0].id === state.layouts[0].controls[0].id) throw new Error('copied control id was reused')

  Store.clearPendingLayouts()
  if (Store.pendingLayouts()) throw new Error('pending layouts were not cleared')
  console.log('  PASS gamepad editor store')
})().catch(function(error) {
  console.error('[test] ERROR:', error)
  process.exit(1)
})
