var path = require('path')
var url = require('url')
var register = require('node:module').register

register('./alias-loader.mjs', { parentURL: url.pathToFileURL(__filename).href })

var storage = {}
global.uni = {
  getStorageSync: function(key) { return storage[key] || '' },
  setStorageSync: function(key, value) { storage[key] = value },
  $emit: function() {},
}

;(async function() {
  var file = path.resolve(__dirname, '../utils/codexMicroConfig.js')
  var mod = await import(url.pathToFileURL(file).href)
  var failed = 0

  function assert(condition, message) {
    if (condition) console.log('  PASS', message)
    else { console.log('  FAIL', message); failed++ }
  }

  var controls = mod.CONTROL_GROUPS.reduce(function(all, group) { return all.concat(group.controls) }, [])
  assert(controls.length === 9, 'Codex Micro exposes nine editable control positions')
  assert(mod.DEFAULT_KEYMAP.action_approve === 'approve', 'approve button is editable')
  assert(mod.DEFAULT_KEYMAP.action_reject === 'reject', 'reject button is editable')

  var changed = Object.assign({}, mod.DEFAULT_KEYMAP, { action_approve: 'cancel', action_reject: 'refresh' })
  assert(mod.saveCodexMicroKeyMap(changed), 'custom key map saves')
  var loaded = mod.loadCodexMicroKeyMap()
  assert(loaded.action_approve === 'cancel' && loaded.action_reject === 'refresh', 'approve and reject positions can be remapped')

  if (failed) process.exit(1)
  console.log('\n[test] ALL PASSED')
})().catch(function(error) {
  console.error(error)
  process.exit(1)
})
