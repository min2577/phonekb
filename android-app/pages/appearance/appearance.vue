<template>
  <view :class="['page', 'appearance-page', appAppearanceClasses]" :style="appAppearanceStyle">
    <view class="appearance-topbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="back-btn" hover-class="back-btn-hover" @tap="onBack">‹</view>
      <view class="title-copy">
        <text class="topbar-title">页面外观</text>
        <text class="topbar-sub">{{ batchMode ? '选择页面后，一次性应用当前设置' : '未修改的页面保持当前样式' }}</text>
      </view>
      <view :class="['batch-toggle', batchMode ? 'active' : '']" @tap="onToggleBatchMode">{{ batchMode ? '完成' : '批量' }}</view>
    </view>

    <scroll-view class="page-tabs" scroll-x :show-scrollbar="false">
      <view class="page-tabs-inner">
        <view v-for="item in pages"
              :key="item.id"
              :class="['page-tab', currentPageId === item.id ? 'active' : '']"
              :data-id="item.id"
              @tap="onSelectPage">{{ item.label }}</view>
      </view>
    </scroll-view>

    <view v-if="batchMode" class="batch-picker">
      <view class="batch-picker-head">
        <text>已选 {{ selectedPageIds.length }} 个页面</text>
        <view class="batch-select-all" @tap="onToggleSelectAll">{{ allPagesSelected ? '取消全选' : '全选' }}</view>
      </view>
      <view class="batch-page-grid">
        <view v-for="item in pages"
              :key="item.id"
              :class="['batch-page-option', isPageSelected(item.id) ? 'selected' : '']"
              :data-id="item.id"
              @tap="onTogglePageSelection">
          <view class="batch-check">{{ isPageSelected(item.id) ? '✓' : '' }}</view>
          <text>{{ item.label }}</text>
        </view>
      </view>
    </view>

    <view class="preview" :style="previewStyle">
      <view class="preview-top">
        <text>{{ batchMode ? '批量应用预览' : currentPageLabel }}</text>
        <text>{{ batchMode ? ('将应用到 ' + selectedPageIds.length + ' 页') : (hasOverride ? '已自定义' : '默认') }}</text>
      </view>
      <view class="preview-surface" :style="previewSurfaceStyle">
        <view class="preview-icon">◉</view>
        <view class="preview-copy">
          <text class="preview-title">组件表面</text>
          <text class="preview-sub">文字和状态保持清晰</text>
        </view>
        <view class="preview-state"></view>
      </view>
    </view>

    <view class="section">
      <view class="section-title">背景类型</view>
      <view class="type-grid">
        <view v-for="item in backgroundTypes"
              :key="item.id"
              :class="['type-option', draft.background.type === item.id ? 'active' : '']"
              :data-type="item.id"
              @tap="onBackgroundType">{{ item.label }}</view>
      </view>

      <view v-if="draft.background.type === 'color'" class="sub-editor">
        <view class="swatches">
          <view v-for="color in colors"
                :key="color"
                :class="['swatch', draft.background.color === color ? 'active' : '']"
                :style="{ backgroundColor: color }"
                :data-color="color"
                @tap="onPickColor"></view>
        </view>
        <view class="color-input-row">
          <input v-model="colorText" class="color-input" maxlength="7" placeholder="#F4F8FD" @confirm="onApplyColor" />
          <view class="apply-btn" @tap="onApplyColor">应用</view>
        </view>
      </view>

      <view v-if="draft.background.type === 'builtin'" class="builtin-grid">
        <view v-for="item in builtins"
              :key="item.id"
              :class="['builtin-item', draft.background.builtinId === item.id ? 'active' : '']"
              :data-id="item.id"
              @tap="onPickBuiltin">
          <view class="builtin-thumb" :style="{ backgroundImage: item.background }"></view>
          <text>{{ item.label }}</text>
        </view>
      </view>

      <view v-if="draft.background.type === 'image'" class="image-editor">
        <view class="image-action" :class="{ disabled: choosingImage }" @tap="onChooseImage">
          {{ choosingImage ? '正在保存…' : (draft.background.source ? '更换相册图片' : '从相册选择') }}
        </view>
        <text v-if="!draft.background.source" class="image-hint">图片将复制到 App 本地目录</text>
      </view>
    </view>

    <view v-if="draft.background.type === 'image'" class="section">
      <view class="section-title">图片显示</view>
      <view class="segmented">
        <view :class="{ active: draft.background.fit === 'cover' }" data-fit="cover" @tap="onFit">填充</view>
        <view :class="{ active: draft.background.fit === 'contain' }" data-fit="contain" @tap="onFit">完整显示</view>
      </view>
      <view class="segmented position-segmented">
        <view :class="{ active: draft.background.position === 'top' }" data-position="top" @tap="onPosition">顶部</view>
        <view :class="{ active: draft.background.position === 'center' }" data-position="center" @tap="onPosition">居中</view>
        <view :class="{ active: draft.background.position === 'bottom' }" data-position="bottom" @tap="onPosition">底部</view>
      </view>
      <view class="slider-row">
        <view class="slider-copy"><text>背景暗度</text><text>{{ Math.round(draft.background.dim * 100) }}%</text></view>
        <slider :value="Math.round(draft.background.dim * 100)" min="0" max="60" step="5" activeColor="#2F78F6" backgroundColor="#CDD8E2" @change="onDimChange" />
      </view>
    </view>

    <view class="section">
      <view class="section-title">组件表面</view>
      <view class="slider-row">
        <view class="slider-copy"><text>不透明度</text><text>{{ Math.round(draft.surfaceOpacity * 100) }}%</text></view>
        <slider :value="Math.round(draft.surfaceOpacity * 100)" min="65" max="100" step="5" activeColor="#2F78F6" backgroundColor="#CDD8E2" @change="onOpacityChange" />
      </view>
      <text class="section-note">只调整卡片和按键底色，文字、图标和状态灯不会变淡。</text>
    </view>

    <view class="footer-actions">
      <view v-if="batchMode" class="reset-page" @tap="onResetSelected">恢复已选页面</view>
      <view v-else class="reset-page" @tap="onResetPage">恢复本页默认</view>
      <view v-if="batchMode" :class="['apply-batch', selectedPageIds.length ? '' : 'disabled']" @tap="onApplyBatch">应用到 {{ selectedPageIds.length }} 页</view>
      <view v-else class="reset-all" @tap="onResetAll">恢复全部页面</view>
    </view>
    <view class="footer-safe"></view>
  </view>
</template>

<script>
import {
  BUILTIN_BACKGROUNDS,
  COLOR_BACKGROUNDS,
  PAGE_OPTIONS,
  applyAppearance,
  buildAppearanceState,
  loadAppearance,
  persistBackgroundImage,
  removePersistedBackground,
  resetAllPageAppearances,
  resetPageAppearance,
  resetPageAppearances,
  sanitizePageAppearance,
  updatePageAppearances,
  updatePageAppearance,
} from '@/utils/appearanceConfig.js'

function defaultPageAppearance() {
  return sanitizePageAppearance({
    surfaceOpacity: 1,
    background: { type: 'default', fit: 'cover', position: 'center', dim: 0 },
  })
}

export default {
  data() {
    return {
      statusBarHeight: 24,
      pages: PAGE_OPTIONS,
      builtins: BUILTIN_BACKGROUNDS,
      colors: COLOR_BACKGROUNDS,
      backgroundTypes: [
        { id: 'default', label: '默认' },
        { id: 'color', label: '纯色' },
        { id: 'builtin', label: '内置' },
        { id: 'image', label: '相册' },
      ],
      currentPageId: 'panel',
      config: loadAppearance(),
      draft: defaultPageAppearance(),
      colorText: '#F4F8FD',
      choosingImage: false,
      batchMode: false,
      selectedPageIds: [],
      pendingBatchImageSources: [],
    }
  },
  computed: {
    currentPageLabel() {
      const page = this.pages.find(function (item) { return item.id === this.currentPageId }.bind(this))
      return page ? page.label : '页面'
    },
    hasOverride() {
      return !!(this.config.pages && this.config.pages[this.currentPageId])
    },
    allPagesSelected() {
      return this.selectedPageIds.length === this.pages.length
    },
    previewState() {
      const config = { mode: this.config.mode, pages: {} }
      config.pages[this.currentPageId] = this.draft
      return buildAppearanceState(config, this.currentPageId, 'light')
    },
    previewStyle() {
      const vars = this.previewState.variables
      return {
        backgroundColor: vars['--app-page-bg-color'],
        backgroundImage: vars['--app-page-bg-image'],
        backgroundSize: vars['--app-page-bg-size'],
        backgroundPosition: vars['--app-page-bg-position'],
        color: vars['--app-color-text'],
      }
    },
    previewSurfaceStyle() {
      const vars = this.previewState.variables
      return {
        backgroundColor: vars['--app-surface'],
        borderColor: vars['--app-color-border'],
        color: vars['--app-color-text'],
      }
    },
  },
  onLoad() {
    try {
      const info = uni.getSystemInfoSync()
      if (info && info.statusBarHeight) this.statusBarHeight = info.statusBarHeight
    } catch (error) {}
    this.loadDraft()
  },
  methods: {
    loadDraft() {
      this.config = loadAppearance()
      const saved = this.config.pages && this.config.pages[this.currentPageId]
      this.draft = saved ? sanitizePageAppearance(saved) : defaultPageAppearance()
      this.colorText = this.draft.background.color || '#F4F8FD'
    },
    saveDraft() {
      if (this.batchMode) return
      const previousConfig = this.config
      this.config = updatePageAppearance(this.currentPageId, this.draft)
      this.removeOrphanedBackgrounds(previousConfig, this.config)
      applyAppearance('settings', this.config)
      this.$refreshAppAppearance()
    },
    onBack() { uni.navigateBack() },
    onToggleBatchMode() {
      if (this.batchMode) this.discardPendingBatchImages()
      this.batchMode = !this.batchMode
      this.selectedPageIds = this.batchMode ? [this.currentPageId] : []
      if (!this.batchMode) this.loadDraft()
    },
    onSelectPage(e) {
      this.currentPageId = e.currentTarget.dataset.id
      if (!this.batchMode) this.loadDraft()
    },
    isPageSelected(pageId) {
      return this.selectedPageIds.indexOf(pageId) >= 0
    },
    onTogglePageSelection(e) {
      const pageId = e.currentTarget.dataset.id
      const ids = this.selectedPageIds.slice()
      const index = ids.indexOf(pageId)
      if (index >= 0) ids.splice(index, 1)
      else ids.push(pageId)
      this.selectedPageIds = ids
    },
    onToggleSelectAll() {
      this.selectedPageIds = this.allPagesSelected ? [] : this.pages.map(function (page) { return page.id })
    },
    onBackgroundType(e) {
      const type = e.currentTarget.dataset.type
      const background = Object.assign({}, this.draft.background, { type: type })
      if (type === 'color' && !background.color) background.color = '#F4F8FD'
      if (type === 'builtin' && !background.builtinId) background.builtinId = BUILTIN_BACKGROUNDS[0].id
      if (type === 'image' && !background.source) background.source = ''
      this.draft = sanitizePageAppearance({ surfaceOpacity: this.draft.surfaceOpacity, background: background })
      this.saveDraft()
    },
    onPickColor(e) {
      this.colorText = e.currentTarget.dataset.color
      this.draft.background.color = this.colorText
      this.saveDraft()
    },
    onApplyColor() {
      const color = String(this.colorText || '').trim().toUpperCase()
      if (!/^#[0-9A-F]{6}$/.test(color)) {
        uni.showToast({ title: '请输入 6 位十六进制颜色', icon: 'none' })
        return
      }
      this.draft.background.color = color
      this.colorText = color
      this.saveDraft()
    },
    onPickBuiltin(e) {
      this.draft.background.builtinId = e.currentTarget.dataset.id
      this.saveDraft()
    },
    onChooseImage() {
      if (this.choosingImage) return
      const self = this
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album'],
        success: function (result) {
          const path = result && result.tempFilePaths && result.tempFilePaths[0]
          if (!path) return
          self.choosingImage = true
          persistBackgroundImage(path).then(function (savedPath) {
            self.draft.background.source = savedPath
            if (self.batchMode && self.pendingBatchImageSources.indexOf(savedPath) < 0) {
              self.pendingBatchImageSources.push(savedPath)
            }
            self.saveDraft()
          }).catch(function (error) {
            uni.showToast({ title: (error && error.errMsg) || '背景图保存失败', icon: 'none' })
          }).finally(function () { self.choosingImage = false })
        },
      })
    },
    onFit(e) {
      this.draft.background.fit = e.currentTarget.dataset.fit
      this.saveDraft()
    },
    onPosition(e) {
      this.draft.background.position = e.currentTarget.dataset.position
      this.saveDraft()
    },
    onDimChange(e) {
      this.draft.background.dim = Number(e.detail.value) / 100
      this.saveDraft()
    },
    onOpacityChange(e) {
      this.draft.surfaceOpacity = Number(e.detail.value) / 100
      this.saveDraft()
    },
    onResetPage() {
      const previousConfig = this.config
      this.config = resetPageAppearance(this.currentPageId)
      this.removeOrphanedBackgrounds(previousConfig, this.config)
      this.loadDraft()
      applyAppearance('settings', this.config)
      this.$refreshAppAppearance()
    },
    onApplyBatch() {
      if (!this.selectedPageIds.length) {
        uni.showToast({ title: '请至少选择一个页面', icon: 'none' })
        return
      }
      const previousConfig = this.config
      this.config = updatePageAppearances(this.selectedPageIds, this.draft)
      this.removeOrphanedBackgrounds(previousConfig, this.config)
      this.discardPendingBatchImages(this.draft.background.type === 'image' ? this.draft.background.source : '')
      applyAppearance('settings', this.config)
      this.$refreshAppAppearance()
      uni.showToast({ title: '已应用到 ' + this.selectedPageIds.length + ' 个页面', icon: 'success' })
    },
    onResetSelected() {
      if (!this.selectedPageIds.length) {
        uni.showToast({ title: '请至少选择一个页面', icon: 'none' })
        return
      }
      const self = this
      uni.showModal({
        title: '恢复已选页面',
        content: '恢复这 ' + this.selectedPageIds.length + ' 个页面的默认外观？',
        success: function (result) {
          if (!result.confirm) return
          const previousConfig = self.config
          self.config = resetPageAppearances(self.selectedPageIds)
          self.removeOrphanedBackgrounds(previousConfig, self.config)
          self.loadDraft()
          applyAppearance('settings', self.config)
          self.$refreshAppAppearance()
        },
      })
    },
    onResetAll() {
      const self = this
      uni.showModal({
        title: '恢复全部页面',
        content: '删除所有页面背景和透明度设置？',
        success: function (result) {
          if (!result.confirm) return
          const previousConfig = loadAppearance()
          self.config = resetAllPageAppearances()
          self.removeOrphanedBackgrounds(previousConfig, self.config)
          self.loadDraft()
          applyAppearance('settings', self.config)
          self.$refreshAppAppearance()
        },
      })
    },
    removeOrphanedBackgrounds(previousConfig, nextConfig) {
      const remaining = {}
      Object.keys((nextConfig && nextConfig.pages) || {}).forEach(function (pageId) {
        const background = nextConfig.pages[pageId] && nextConfig.pages[pageId].background
        if (background && background.type === 'image' && background.source) remaining[background.source] = true
      })
      const removed = {}
      Object.keys((previousConfig && previousConfig.pages) || {}).forEach(function (pageId) {
        const background = previousConfig.pages[pageId] && previousConfig.pages[pageId].background
        const source = background && background.type === 'image' ? background.source : ''
        if (source && !remaining[source] && !removed[source]) {
          removed[source] = true
          removePersistedBackground(source)
        }
      })
    },
    discardPendingBatchImages(keepSource) {
      const keep = String(keepSource || '')
      this.pendingBatchImageSources.forEach(function (source) {
        if (source && source !== keep) removePersistedBackground(source)
      })
      this.pendingBatchImageSources = []
    },
  },
}
</script>

<style scoped>
.appearance-page {
  min-height: 100vh;
  padding: 0 22rpx 42rpx;
  color: var(--color-text);
}
.appearance-topbar { min-height: 104rpx; display: flex; align-items: center; gap: 16rpx; }
.back-btn { width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid var(--color-border); border-radius: 18rpx; background: var(--app-surface-strong, #FFFFFF); color: var(--color-text); font-size: 44rpx; }
.back-btn-hover { transform: scale(0.96); }
.title-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 3rpx; }
.topbar-title { color: var(--color-text); font-size: 32rpx; font-weight: 750; }
.topbar-sub { color: var(--color-text-mid); font-size: 19rpx; }
.batch-toggle { min-width: 72rpx; height: 52rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid var(--color-border); border-radius: 14rpx; background: var(--app-surface, #FFFFFF); color: var(--color-primary); font-size: 20rpx; font-weight: 700; }
.batch-toggle.active { border-color: var(--color-primary); background: var(--color-primary-bg); }
.page-tabs { margin: 6rpx 0 16rpx; white-space: nowrap; }
.page-tabs-inner { display: inline-flex; gap: 10rpx; padding: 2rpx; }
.page-tab { min-height: 58rpx; padding: 0 19rpx; display: flex; align-items: center; border: 1rpx solid var(--color-border); border-radius: 15rpx; background: var(--app-surface, #FFFFFF); color: var(--color-text-mid); font-size: 21rpx; }
.page-tab.active { border-color: var(--color-primary); background: var(--color-primary-bg); color: var(--color-primary); font-weight: 700; }
.batch-picker { margin: 0 0 16rpx; padding: 16rpx; border: 1rpx solid var(--color-border); border-radius: 18rpx; background: var(--app-surface, #FFFFFF); }
.batch-picker-head { margin-bottom: 14rpx; display: flex; align-items: center; justify-content: space-between; color: var(--color-text-mid); font-size: 20rpx; }
.batch-select-all { padding: 5rpx 8rpx; color: var(--color-primary); font-weight: 700; }
.batch-page-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9rpx; }
.batch-page-option { min-width: 0; min-height: 58rpx; padding: 0 12rpx; display: flex; align-items: center; gap: 9rpx; border: 1rpx solid var(--color-border); border-radius: 12rpx; background: var(--color-bg-alt); color: var(--color-text-mid); font-size: 19rpx; }
.batch-page-option.selected { border-color: var(--color-primary); background: var(--color-primary-bg); color: var(--color-primary); font-weight: 700; }
.batch-check { width: 26rpx; height: 26rpx; box-sizing: border-box; display: flex; flex: 0 0 26rpx; align-items: center; justify-content: center; border: 1rpx solid var(--color-border); border-radius: 8rpx; background: var(--app-surface-strong, #FFFFFF); color: #FFFFFF; font-size: 18rpx; }
.batch-page-option.selected .batch-check { border-color: var(--color-primary); background: var(--color-primary); }
.preview { min-height: 250rpx; padding: 18rpx; border-radius: 24rpx; background-repeat: no-repeat; overflow: hidden; }
.preview-top { display: flex; align-items: center; justify-content: space-between; color: inherit; font-size: 20rpx; font-weight: 700; }
.preview-surface { min-height: 120rpx; margin-top: 46rpx; padding: 18rpx; display: flex; align-items: center; gap: 15rpx; border: 1rpx solid; border-radius: 18rpx; box-shadow: 0 9rpx 24rpx rgba(17,35,46,0.16); }
.preview-icon { width: 56rpx; height: 56rpx; display: flex; align-items: center; justify-content: center; border-radius: 15rpx; background: var(--color-primary-bg); color: var(--color-primary); font-size: 28rpx; }
.preview-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 5rpx; }
.preview-title { color: inherit; font-size: 24rpx; font-weight: 750; }
.preview-sub { color: var(--color-text-mid); font-size: 18rpx; }
.preview-state { width: 14rpx; height: 14rpx; border-radius: 50%; background: var(--color-success); box-shadow: 0 0 0 5rpx rgba(16,124,16,0.16); }
.section { margin-top: 16rpx; padding: 20rpx; border: 1rpx solid var(--color-border); border-radius: 22rpx; background: var(--app-surface, #FFFFFF); }
.section-title { margin-bottom: 15rpx; color: var(--color-text); font-size: 24rpx; font-weight: 750; }
.type-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9rpx; }
.type-option { min-height: 62rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid var(--color-border); border-radius: 14rpx; background: var(--color-bg-alt); color: var(--color-text-mid); font-size: 21rpx; }
.type-option.active { border-color: var(--color-primary); background: var(--color-primary-bg); color: var(--color-primary); font-weight: 700; }
.sub-editor, .image-editor { margin-top: 17rpx; }
.swatches { display: flex; flex-wrap: wrap; gap: 14rpx; }
.swatch { width: 54rpx; height: 54rpx; border: 4rpx solid transparent; border-radius: 14rpx; box-shadow: inset 0 0 0 1rpx rgba(20,35,45,0.12); }
.swatch.active { border-color: var(--color-primary); }
.color-input-row { margin-top: 14rpx; display: flex; gap: 10rpx; }
.color-input { height: 64rpx; min-width: 0; padding: 0 16rpx; flex: 1; border: 1rpx solid var(--color-border); border-radius: 14rpx; background: var(--app-surface-strong, #FFFFFF); color: var(--color-text); font-size: 23rpx; }
.apply-btn, .image-action { min-height: 64rpx; padding: 0 20rpx; display: flex; align-items: center; justify-content: center; border-radius: 14rpx; background: var(--color-primary); color: #FFFFFF; font-size: 22rpx; font-weight: 700; }
.builtin-grid { margin-top: 17rpx; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }
.builtin-item { padding: 7rpx; border: 2rpx solid transparent; border-radius: 16rpx; color: var(--color-text-mid); font-size: 19rpx; }
.builtin-item.active { border-color: var(--color-primary); color: var(--color-primary); }
.builtin-thumb { height: 82rpx; margin-bottom: 7rpx; border-radius: 11rpx; background-size: cover; }
.image-action.disabled { opacity: 0.5; }
.image-hint { display: block; margin-top: 10rpx; color: var(--color-text-mid); font-size: 19rpx; }
.segmented { height: 62rpx; padding: 4rpx; display: flex; gap: 4rpx; border: 1rpx solid var(--color-border); border-radius: 15rpx; background: var(--color-bg-alt); }
.segmented view { min-width: 0; flex: 1; display: flex; align-items: center; justify-content: center; border-radius: 10rpx; color: var(--color-text-mid); font-size: 21rpx; }
.segmented view.active { background: var(--app-surface-strong, #FFFFFF); color: var(--color-primary); font-weight: 700; }
.position-segmented { margin-top: 10rpx; }
.slider-row { margin-top: 13rpx; }
.slider-copy { display: flex; align-items: center; justify-content: space-between; color: var(--color-text); font-size: 22rpx; }
.slider-copy text:last-child { color: var(--color-primary); font-weight: 750; }
.section-note { display: block; color: var(--color-text-mid); font-size: 19rpx; line-height: 1.5; }
.footer-actions { margin-top: 18rpx; display: flex; gap: 10rpx; }
.reset-page, .reset-all, .apply-batch { min-height: 70rpx; display: flex; flex: 1; align-items: center; justify-content: center; border: 1rpx solid var(--color-border); border-radius: 16rpx; background: var(--app-surface, #FFFFFF); color: var(--color-text-mid); font-size: 21rpx; }
.reset-all { color: var(--color-danger); }
.apply-batch { border-color: var(--color-primary); background: var(--color-primary); color: #FFFFFF; font-weight: 700; }
.apply-batch.disabled { opacity: 0.45; }
.footer-safe { height: env(safe-area-inset-bottom); }
</style>
