var path = require('path')
var url = require('url')

;(async function() {
  var mod = await import(url.pathToFileURL(path.resolve(__dirname, '../utils/appearanceConfig.js')).href)
  var failed = 0
  function assert(condition, message) {
    if (condition) console.log('  PASS', message)
    else { console.error('  FAIL', message); failed++ }
  }

  var normalized = mod.normalizeAppearance({
    mode: 'invalid',
    pages: {
      panel: { surfaceOpacity: 0.2, background: { type: 'color', color: '#123456', dim: 2 } },
      unknown: { surfaceOpacity: 0.8 },
    },
  })
  assert(normalized.mode === 'light', 'invalid mode falls back to light')
  assert(normalized.pages.panel.surfaceOpacity === 0.65, 'surface opacity clamps to readable minimum')
  assert(normalized.pages.panel.background.dim === 0.6, 'background dim clamps to maximum')
  assert(!normalized.pages.unknown, 'unknown page ids are discarded')

  assert(mod.resolveEffectiveMode('system', 'dark') === 'dark', 'system dark resolves to dark')
  assert(mod.resolveEffectiveMode('system', 'light') === 'light', 'system light resolves to light')
  assert(mod.routeToPageId('/pages/panel/panel') === 'panel', 'route maps to stable page id')
  assert(mod.routeToPageId('pages/appearance/appearance') === 'settings', 'appearance editor inherits settings page')

  var untouched = mod.buildAppearanceState(mod.DEFAULT_APPEARANCE, 'panel', 'dark')
  assert(untouched.mode === 'light', 'default appearance remains current light mode')
  assert(!untouched.hasOverride && !untouched.hasCustomBackground, 'untouched page has no visual override')

  var configured = mod.buildAppearanceState({
    mode: 'dark',
    pages: {
      panel: {
        surfaceOpacity: 0.75,
        background: { type: 'builtin', builtinId: 'forest', fit: 'cover', position: 'center', dim: 0 },
      },
    },
  }, 'panel', 'light')
  assert(configured.mode === 'dark', 'explicit dark mode wins over system')
  assert(configured.hasCustomBackground, 'built-in background activates custom page background')
  assert(configured.variables['--app-surface'] === 'rgba(29,38,43,0.75)', 'dark surface keeps content opacity separate')
  assert(configured.variables['--color-text'] === '#ECF2F4', 'legacy component text token follows dark mode')

  var memory = {}
  var storage = {
    get: function(key) { return memory[key] },
    set: function(key, value) { memory[key] = value },
  }
  mod.updatePageAppearance('panel', { surfaceOpacity: 0.8, background: { type: 'default' } }, storage)
  assert(mod.loadAppearance(storage).pages.panel.surfaceOpacity === 0.8, 'page override persists')
  mod.resetPageAppearance('panel', storage)
  assert(!mod.loadAppearance(storage).pages.panel, 'page reset removes override instead of writing defaults')

  mod.updatePageAppearances(['panel', 'layout', 'unknown'], { surfaceOpacity: 0.7, background: { type: 'color', color: '#654321' } }, storage)
  var batchConfig = mod.loadAppearance(storage)
  assert(batchConfig.pages.panel.surfaceOpacity === 0.7 && batchConfig.pages.layout.surfaceOpacity === 0.7, 'batch update applies one appearance to every valid page')
  assert(!batchConfig.pages.unknown, 'batch update ignores unknown page ids')
  mod.resetPageAppearances(['panel', 'layout'], storage)
  assert(!mod.loadAppearance(storage).pages.panel && !mod.loadAppearance(storage).pages.layout, 'batch reset removes every selected page override')

  process.exit(failed ? 1 : 0)
})().catch(function(error) { console.error(error); process.exit(1) })
