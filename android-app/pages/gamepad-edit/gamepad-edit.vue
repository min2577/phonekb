<template>
  <view class="editor-page">
    <view class="editor-topbar">
      <button class="icon-button" aria-label="返回操作页面" @tap="onBack"><text>‹</text></button>
      <view class="title-copy"><text class="title">编辑按钮</text><text class="subtitle">{{ draft.label || '未命名按钮' }}</text></view>
      <button class="done-button" @tap="saveAndBack">完成</button>
    </view>

    <view class="preview-section">
      <view class="section-heading"><text>实时预览</text><text class="section-note">按住查看反馈</text></view>
      <view class="preview-stage" @touchstart.stop="previewPressed = true" @touchend.stop="previewPressed = false" @touchcancel.stop="previewPressed = false">
        <view :class="['button-preview', skinClass, shapeClass, pressClass]" :style="previewStyle">
          <text v-if="showLabel" class="preview-label">{{ draft.label || '按钮' }}</text>
          <text v-if="showKey" class="preview-key">{{ bindingText }}</text>
        </view>
      </view>
      <view class="preview-meta"><text>{{ behaviorLabel }}</text><text>{{ Math.round(Number(draft.opacity || 100)) }}% 透明度</text><text>{{ skinName }}</text></view>
    </view>

    <scroll-view class="form-scroll" scroll-y>
      <view class="form-section">
        <view class="section-heading"><text>按钮功能</text><text class="section-note">功能和外观会一起保存</text></view>
        <view class="field-row"><text class="field-label">按钮名称</text><input v-model="draft.label" maxlength="32" class="text-input" placeholder="例如：跳跃" /></view>
        <view class="field-label standalone">功能类型</view>
        <view class="segments two"><button :class="['segment', { active: actionMode === 'key' }]" @tap="setActionMode('key')">键盘按键</button><button :class="['segment', { active: actionMode === 'shortcut' }]" @tap="setActionMode('shortcut')">组合键</button></view>
        <view v-if="actionMode === 'shortcut'" class="modifier-row">
          <button v-for="item in modifiers" :key="item.id" :class="['modifier', { active: activeModifiers.includes(item.id) }]" @tap="toggleModifier(item.id)">{{ item.label }}</button>
        </view>
        <view class="field-row"><text class="field-label">映射键位</text><input v-model="mainKey" maxlength="32" class="key-input" placeholder="Space / A / F1" @blur="sanitizeKey" /></view>
        <view class="field-label standalone">触发方式</view>
        <view class="segments three"><button v-for="item in behaviors" :key="item.id" :class="['segment', { active: draft.behavior === item.id }]" @tap="draft.behavior = item.id">{{ item.label }}</button></view>
      </view>

      <view class="form-section">
        <view class="section-heading"><text>按钮样式</text><text class="section-note">先选模板，再细调</text></view>
        <view class="skin-grid">
          <button v-for="skin in skins" :key="skin.id" :class="['skin-card', { active: draft.appearance.skin === skin.id }]" @tap="setSkin(skin.id)">
            <view :class="['skin-sample', 'skin-' + skin.id]"><text>{{ skin.sample }}</text></view><text class="skin-name">{{ skin.name }}</text>
          </button>
        </view>
        <view class="field-label standalone">按钮形状</view>
        <view class="segments four"><button v-for="shape in shapes" :key="shape.id" :class="['segment', { active: draft.appearance.shape === shape.id }]" @tap="draft.appearance.shape = shape.id">{{ shape.label }}</button></view>
        <view class="field-label standalone">显示内容</view>
        <view class="segments three"><button v-for="mode in labelModes" :key="mode.id" :class="['segment', { active: draft.appearance.labelMode === mode.id }]" @tap="draft.appearance.labelMode = mode.id">{{ mode.label }}</button></view>
        <view class="field-label standalone">自定义颜色</view>
        <view class="color-row"><button v-for="color in colors" :key="color" :class="['color-swatch', { active: draft.appearance.fill === color }]" :style="{ backgroundColor: color }" @tap="setColor(color)"></button><button class="reset-color" @tap="resetColors">使用模板颜色</button></view>
        <view class="slider-row"><text>透明度</text><slider class="slider" :value="draft.opacity" min="20" max="100" step="5" activeColor="#2F78F6" backgroundColor="#D8E4EF" @changing="setOpacity" @change="setOpacity" /><text class="slider-value">{{ Math.round(Number(draft.opacity || 100)) }}%</text></view>
      </view>

      <view class="bottom-actions"><button class="delete-button" @tap="deleteControl">删除按钮</button><button class="preset-button" @tap="saveAsPreset">保存为新预设</button><button class="save-button" @tap="saveDraft">保存按钮</button></view>
    </scroll-view>
  </view>
</template>

<script>
import WS from '@/utils/wsclient.js'
import { lockPortrait } from '@/utils/orientation.js'
import { clone, loadLayouts, saveLayouts, savePreset } from '@/utils/gamepadEditorStore.js'

const SKINS = [
  ['fluent', 'Fluent 键帽', 'Space'], ['matte', '磨砂实体键', 'A'], ['arcade', '街机高光键', 'A'],
  ['glass', '透明触控键', 'A'], ['keycap', '机械键帽', 'Space'], ['hud', '战术 HUD', 'FIRE'],
  ['skill', '技能圆环', 'Q'], ['pixel', '复古像素键', 'A'], ['switch', 'Switch 彩色键', 'B'],
  ['outline', '几何轮廓键', '△'], ['neon', '霓虹街机键', 'ATK'], ['contrast', '高对比大键', '跳'],
].map(function(item) { return { id: item[0], name: item[1], sample: item[2] } })

export default {
  data() {
    return {
      layoutId: '', controlId: '', layoutsData: null, draft: { appearance: {}, bindings: {} },
      actionMode: 'key', mainKey: 'space', activeModifiers: [], previewPressed: false, saved: false,
      skins: SKINS,
      modifiers: [{ id: 'ctrl', label: 'Ctrl' }, { id: 'shift', label: 'Shift' }, { id: 'alt', label: 'Alt' }, { id: 'win', label: 'Win' }],
      behaviors: [{ id: 'hold', label: '按住' }, { id: 'tap', label: '点击' }, { id: 'toggle', label: '切换' }],
      shapes: [{ id: 'round', label: '圆形' }, { id: 'square', label: '方形' }, { id: 'pill', label: '胶囊' }, { id: 'diamond', label: '菱形' }],
      labelModes: [{ id: 'label', label: '名称' }, { id: 'key', label: '键位' }, { id: 'both', label: '名称+键位' }],
      colors: ['#347CF0', '#243449', '#ED5B68', '#2DB77D', '#F0B936', '#7258D6', '#151927'],
    }
  },
  computed: {
    bindingText() {
      const values = this.activeModifiers.map(function(item) { return item.charAt(0).toUpperCase() + item.slice(1) })
      values.push(this.prettyKey(this.mainKey))
      return values.join(' + ')
    },
    behaviorLabel() {
      const item = this.behaviors.find(value => value.id === this.draft.behavior)
      return item ? item.label + '触发' : '按住触发'
    },
    skinName() {
      const item = this.skins.find(value => value.id === this.draft.appearance.skin)
      return item ? item.name : 'Fluent 键帽'
    },
    skinClass() { return 'skin-' + (this.draft.appearance.skin || 'fluent') },
    shapeClass() { return 'shape-' + (this.draft.appearance.shape || 'round') },
    pressClass() { return this.previewPressed ? 'is-pressed' : '' },
    showLabel() { return (this.draft.appearance.labelMode || 'label') !== 'key' },
    showKey() { return ['key', 'both'].includes(this.draft.appearance.labelMode) },
    previewStyle() {
      const appearance = this.draft.appearance || {}
      return {
        opacity: Number(this.draft.opacity || 100) / 100,
        background: appearance.fill || '', borderColor: appearance.border || '', color: appearance.text || '',
      }
    },
  },
  onLoad(options) {
    lockPortrait()
    this.layoutId = String(options && options.layoutId || '')
    this.controlId = String(options && options.controlId || '')
    this.loadDraft()
  },
  onShow() { lockPortrait() },
  methods: {
    loadDraft() {
      this.layoutsData = loadLayouts()
      const layout = this.layoutsData.layouts.find(item => item.id === this.layoutId)
      const control = layout && layout.controls.find(item => item.id === this.controlId)
      if (!control) { uni.showToast({ title: '按钮不存在', icon: 'none' }); return }
      this.draft = clone(control)
      this.draft.appearance = Object.assign({ skin: 'fluent', shape: 'round', labelMode: 'label', pressEffect: 'sink' }, this.draft.appearance || {})
      const current = (this.draft.bindings || {}).press || { type: 'key', key: 'space', modifiers: [] }
      this.mainKey = current.key || 'space'
      this.activeModifiers = (current.modifiers || []).slice()
      this.actionMode = this.activeModifiers.length ? 'shortcut' : 'key'
    },
    prettyKey(key) {
      const value = String(key || 'Space')
      if (value.length === 1) return value.toUpperCase()
      return value.charAt(0).toUpperCase() + value.slice(1)
    },
    setActionMode(mode) { this.actionMode = mode; if (mode === 'key') this.activeModifiers = [] },
    toggleModifier(id) { const index = this.activeModifiers.indexOf(id); if (index >= 0) this.activeModifiers.splice(index, 1); else this.activeModifiers.push(id) },
    sanitizeKey() { this.mainKey = String(this.mainKey || 'space').trim().toLowerCase().slice(0, 32) || 'space' },
    setSkin(id) { this.draft.appearance.skin = id; this.resetColors() },
    setColor(color) { this.draft.appearance.fill = color },
    resetColors() { delete this.draft.appearance.fill; delete this.draft.appearance.border; delete this.draft.appearance.text },
    setOpacity(event) { this.draft.opacity = Number(event && event.detail && event.detail.value || 100) },
    applyDraft() {
      this.sanitizeKey()
      const modifiers = this.actionMode === 'shortcut' ? this.activeModifiers.slice() : []
      this.draft.bindings = Object.assign({}, this.draft.bindings || {}, { press: modifiers.length ? { type: 'shortcut', modifiers: modifiers, key: this.mainKey } : { type: 'key', key: this.mainKey } })
      const layout = this.layoutsData.layouts.find(item => item.id === this.layoutId)
      const index = layout ? layout.controls.findIndex(item => item.id === this.controlId) : -1
      if (index < 0) return false
      layout.controls.splice(index, 1, clone(this.draft))
      this.layoutsData = saveLayouts(this.layoutsData)
      if (WS.isConnected()) WS.saveGamepadLayouts(this.layoutsData)
      this.saved = true
      return true
    },
    saveDraft() { if (this.applyDraft()) uni.showToast({ title: '按钮已保存', icon: 'success' }) },
    saveAsPreset() { if (!this.applyDraft()) return; savePreset(this.draft.label, this.draft); uni.showToast({ title: '已保存到按钮预设', icon: 'success' }) },
    saveAndBack() { if (!this.applyDraft()) return; this.onBack() },
    deleteControl() {
      const self = this
      uni.showModal({ title: '删除按钮', content: '确定从当前布局删除这个按钮吗？', success(res) {
        if (!res.confirm) return
        const layout = self.layoutsData.layouts.find(item => item.id === self.layoutId)
        if (layout) layout.controls = layout.controls.filter(item => item.id !== self.controlId)
        self.layoutsData = saveLayouts(self.layoutsData)
        if (WS.isConnected()) WS.saveGamepadLayouts(self.layoutsData)
        self.onBack()
      } })
    },
    onBack() { uni.navigateBack({ delta: 1, fail() { uni.reLaunch({ url: '/pages/panel/panel' }) } }) },
  },
}
</script>

<style scoped>
.editor-page { min-height: 100vh; background: #F4F8FD; color: #172033; }
.editor-topbar { height: 102rpx; padding: 0 24rpx; display: grid; grid-template-columns: 72rpx 1fr 116rpx; align-items: center; border-bottom: 1rpx solid #D9E5F1; background: rgba(255,255,255,.96); }
button::after { border: 0; }.icon-button,.done-button,.segment,.modifier,.skin-card,.color-swatch,.reset-color,.delete-button,.preset-button,.save-button { margin: 0; padding: 0; }
.icon-button { width: 64rpx; height: 64rpx; display: grid; place-items: center; border: 1rpx solid #D4E1ED; border-radius: 14rpx; background: #FFF; color: #506980; font-size: 48rpx; line-height: 1; }
.title-copy { min-width: 0; display: flex; flex-direction: column; align-items: center; }.title { font-size: 30rpx; font-weight: 800; }.subtitle { max-width: 380rpx; margin-top: 3rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #718399; font-size: 20rpx; }
.done-button { width: 108rpx; height: 60rpx; border-radius: 14rpx; background: #2F78F6; color: #FFF; font-size: 23rpx; font-weight: 800; }
.preview-section { padding: 22rpx 24rpx 20rpx; background: #EDF5FD; border-bottom: 1rpx solid #D7E4F0; }
.section-heading { display: flex; align-items: center; justify-content: space-between; font-size: 25rpx; font-weight: 800; }.section-note { color: #8091A5; font-size: 19rpx; font-weight: 500; }
.preview-stage { height: 300rpx; margin-top: 16rpx; display: grid; place-items: center; border: 1rpx solid #C9DBEB; border-radius: 16rpx; background-color: #F7FBFF; background-image: radial-gradient(#C9DBEB 1.5rpx, transparent 1.5rpx); background-size: 24rpx 24rpx; }
.button-preview { min-width: 160rpx; min-height: 118rpx; padding: 20rpx 28rpx; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 3rpx solid rgba(255,255,255,.9); color: #FFF; box-shadow: inset 0 -10rpx 0 rgba(14,52,104,.17), 0 15rpx 28rpx rgba(39,93,160,.22); transition: transform .12s ease, filter .12s ease; }
.button-preview.is-pressed { transform: translateY(7rpx) scale(.97); filter: brightness(.92); box-shadow: inset 0 -3rpx 0 rgba(14,52,104,.17), 0 6rpx 12rpx rgba(39,93,160,.18); }.preview-label { font-size: 29rpx; font-weight: 850; }.preview-key { margin-top: 5rpx; font-size: 19rpx; font-weight: 700; opacity: .85; }
.shape-round { border-radius: 999rpx; aspect-ratio: 1; }.shape-square { border-radius: 20rpx; }.shape-pill { min-width: 230rpx; min-height: 92rpx; border-radius: 999rpx; }.shape-diamond { border-radius: 20rpx; transform: rotate(45deg); }.shape-diamond > text { transform: rotate(-45deg); }
.skin-fluent { background: linear-gradient(145deg,#68A5FF,#2D72DE); }.skin-matte { background: linear-gradient(145deg,#34465D,#172334); }.skin-arcade { background: radial-gradient(circle at 35% 25%,#FF9AA4,#D93649 70%); border-width: 8rpx; }.skin-glass { background: rgba(83,157,235,.22); border-color: rgba(54,124,203,.55); color: #2865A7; box-shadow: inset 0 0 35rpx rgba(255,255,255,.95),0 12rpx 24rpx rgba(61,108,150,.15); }.skin-keycap { background: linear-gradient(#FFF,#D8E2EC); border-color: #9BA9B6; color: #293B4C; box-shadow: inset 0 -12rpx 0 #8A98A6,0 12rpx 20rpx rgba(46,61,78,.2); }.skin-hud { background: #153942; border-color: #2AD3C7; color: #74FFF2; box-shadow: inset 0 0 25rpx rgba(42,211,199,.3),0 0 18rpx rgba(42,211,199,.38); }.skin-skill { background: radial-gradient(circle,#6758C1,#292454 68%); border-color: #D6BA68; color: #FFE8A0; box-shadow: 0 0 0 7rpx #4B4028,0 11rpx 20rpx rgba(43,34,89,.3); }.skin-pixel { background: #F2D64F; border-color: #243346; color: #243346; border-radius: 0; box-shadow: 10rpx 10rpx 0 #243346; }.skin-switch { background: #E95763; box-shadow: inset 0 -11rpx 0 #B93644,0 12rpx 20rpx rgba(162,43,56,.24); }.skin-outline { background: transparent; border-color: #4B7BAA; color: #4B7BAA; box-shadow: none; }.skin-neon { background: #17142E; border-color: #ED5AFF; color: #72EAFF; box-shadow: 0 0 22rpx rgba(237,90,255,.65),inset 0 0 22rpx rgba(114,234,255,.18); }.skin-contrast { background: #FFEB00; border-color: #111; color: #111; box-shadow: inset 0 -9rpx 0 #D3C000,0 9rpx 0 #111; }
.preview-meta { margin-top: 14rpx; display: flex; justify-content: center; gap: 12rpx; }.preview-meta text { padding: 7rpx 13rpx; border: 1rpx solid #D1DEEA; border-radius: 11rpx; background: #FFF; color: #61768E; font-size: 18rpx; }
.form-scroll { height: calc(100vh - 524rpx); }.form-section { margin: 20rpx 24rpx 0; padding: 22rpx; border: 1rpx solid #D8E4EF; border-radius: 16rpx; background: #FFF; box-shadow: 0 8rpx 22rpx rgba(47,78,113,.06); }
.field-row { min-height: 74rpx; margin-top: 16rpx; display: grid; grid-template-columns: 150rpx 1fr; align-items: center; border-bottom: 1rpx solid #E3EBF3; }.field-label { color: #63788E; font-size: 21rpx; font-weight: 700; }.field-label.standalone { display: block; margin: 20rpx 0 12rpx; }.text-input,.key-input { height: 66rpx; padding: 0 16rpx; border: 1rpx solid #CFDDEB; border-radius: 12rpx; background: #F9FCFF; color: #233E59; font-size: 23rpx; }
.segments { display: grid; gap: 10rpx; }.segments.two { grid-template-columns: repeat(2,1fr); }.segments.three { grid-template-columns: repeat(3,1fr); }.segments.four { grid-template-columns: repeat(4,1fr); }.segment,.modifier { height: 58rpx; border: 1rpx solid #D2DFEC; border-radius: 12rpx; background: #FFF; color: #62778E; font-size: 20rpx; font-weight: 750; }.segment.active,.modifier.active { border-color: #2F78F6; background: #EAF3FF; color: #2F78F6; }
.modifier-row { margin-top: 12rpx; display: grid; grid-template-columns: repeat(4,1fr); gap: 10rpx; }
.skin-grid { margin-top: 16rpx; display: grid; grid-template-columns: repeat(3,1fr); gap: 12rpx; }.skin-card { height: 150rpx; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1rpx solid #D5E1EC; border-radius: 14rpx; background: #F9FBFD; }.skin-card.active { border: 3rpx solid #2F78F6; background: #F2F7FF; }.skin-sample { width: 84rpx; height: 62rpx; display: grid; place-items: center; border: 2rpx solid rgba(255,255,255,.9); border-radius: 15rpx; color: #FFF; font-size: 18rpx; font-weight: 850; }.skin-sample.skin-matte,.skin-sample.skin-arcade,.skin-sample.skin-skill,.skin-sample.skin-switch,.skin-sample.skin-outline { width: 62rpx; border-radius: 50%; }.skin-name { margin-top: 11rpx; color: #536A82; font-size: 17rpx; font-weight: 700; }
.color-row { display: flex; align-items: center; gap: 14rpx; }.color-swatch { width: 48rpx; height: 48rpx; border: 4rpx solid #FFF; border-radius: 50%; box-shadow: 0 0 0 1rpx #BCCBDA; }.color-swatch.active { box-shadow: 0 0 0 4rpx #2F78F6; }.reset-color { margin-left: auto; height: 48rpx; padding: 0 15rpx; border: 1rpx solid #CFDDEB; border-radius: 11rpx; background: #FFF; color: #60758D; font-size: 18rpx; }
.slider-row { margin-top: 22rpx; display: grid; grid-template-columns: 100rpx 1fr 70rpx; align-items: center; color: #61768D; font-size: 20rpx; }.slider { width: 100%; }.slider-value { text-align: right; color: #2E567D; font-weight: 800; }
.bottom-actions { margin: 20rpx 24rpx 40rpx; display: grid; grid-template-columns: .8fr 1.15fr 1.15fr; gap: 12rpx; }.delete-button,.preset-button,.save-button { height: 74rpx; border-radius: 14rpx; font-size: 21rpx; font-weight: 800; }.delete-button { border: 1rpx solid #F0BFC4; background: #FFF; color: #DA4F5D; }.preset-button { border: 1rpx solid #A9C9F8; background: #EAF3FF; color: #2F78F6; }.save-button { background: #2F78F6; color: #FFF; }
</style>
