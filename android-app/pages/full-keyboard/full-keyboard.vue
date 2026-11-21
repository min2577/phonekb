<template>
  <view :class="['full-keyboard-page', appAppearanceClasses]" :style="appAppearanceStyle">
    <PanelFullKeyboard
      :force-expand="true"
      @fullscreen-change="onFullscreenChange"
    />
  </view>
</template>

<script>
import PanelFullKeyboard from '@/components/PanelFullKeyboard.vue'
import { lockLandscape, lockPortrait } from '@/utils/orientation.js'

export default {
  components: { PanelFullKeyboard },
  data() {
    return { leaving: false }
  },
  onLoad() {
    lockLandscape()
    this.setNativeFullscreen(true)
  },
  onShow() {
    this.leaving = false
    lockLandscape()
    this.setNativeFullscreen(true)
    try { uni.hideTabBar({ animation: false }) } catch (e) {}
  },
  onHide() {
    this.restorePortrait()
  },
  onUnload() {
    this.restorePortrait()
  },
  methods: {
    setNativeFullscreen(enabled) {
      // #ifdef APP-PLUS
      try {
        if (typeof plus !== 'undefined' && plus.navigator && typeof plus.navigator.setFullscreen === 'function') {
          plus.navigator.setFullscreen(!!enabled)
        }
      } catch (e) {}
      // #endif
    },
    restorePortrait() {
      lockPortrait()
      this.setNativeFullscreen(false)
    },
    onFullscreenChange(fullscreen) {
      if (fullscreen || this.leaving) return
      this.leaving = true
      this.restorePortrait()
      uni.navigateBack({
        fail() { uni.reLaunch({ url: '/pages/panel/panel' }) },
      })
    },
  },
}
</script>

<style scoped>
.full-keyboard-page {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #F4F8FD;
}
</style>
