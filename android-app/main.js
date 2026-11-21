import { createSSRApp } from 'vue'
import App from './App.vue'
import { applyCurrentPageAppearance } from './utils/appearanceConfig.js'

export function createApp() {
  const app = createSSRApp(App)
  app.mixin({
    data() {
      return {
        appAppearanceClasses: {},
        appAppearanceStyle: {},
      }
    },
    onShow() {
      const self = this
      setTimeout(function () { self.$refreshAppAppearance() }, 0)
    },
    methods: {
      $refreshAppAppearance() {
        const state = applyCurrentPageAppearance()
        this.appAppearanceClasses = {
          'app-appearance-root': true,
          'app-appearance-active': state.mode === 'dark' || state.hasOverride,
          'app-has-custom-background': state.hasCustomBackground,
          'app-dark': state.mode === 'dark',
          'app-light': state.mode !== 'dark',
        }
        this.appAppearanceStyle = state.variables
        return state
      },
    },
  })
  return { app }
}
