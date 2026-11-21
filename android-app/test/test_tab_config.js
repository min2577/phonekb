var path = require('path')
var url = require('url')

var storage = {}

global.uni = {
  getStorageSync: function(key) { return storage[key] },
  setStorageSync: function(key, value) { storage[key] = value },
  $emit: function() {},
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
  console.log('  PASS ' + message)
}

;(async function() {
  var modulePath = path.resolve(__dirname, '../utils/tabConfig.js')
  var config = await import(url.pathToFileURL(modulePath).href)

  var customOption = {
    key: 'layout-work',
    title: '工作面板',
    icon: '▣',
    page: 'panel',
    layoutId: 'work',
  }
  var added = config.pickAddOption(config.DEFAULT_TABS, customOption).tabs
  config.saveTabs(added)
  var loaded = config.loadTabs()
  var customTab = loaded.find(function(tab) { return tab.id === 'layout-work' })
  assert(customTab && customTab.layoutId === 'work', 'custom panel id survives save and load')

  var renamed = config.syncLayoutTabs(loaded, [{ id: 'work', name: '工作台' }])
  customTab = renamed.find(function(tab) { return tab.id === 'layout-work' })
  assert(customTab && customTab.label === '工作台', 'custom panel tab follows layout rename')

  var cleaned = config.syncLayoutTabs(renamed, [])
  assert(!cleaned.some(function(tab) { return tab.id === 'layout-work' }), 'deleted layout removes its stale tab')
})().catch(function(error) {
  console.error('[test] ERROR:', error)
  process.exit(1)
})
