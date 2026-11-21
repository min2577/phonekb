<template>
  <view class="custom-app-preview">
    <view class="preview-device">
      <view class="preview-screen">
        <view class="preview-stage" :style="themeStyle">
          <view class="preview-panel">
            <view class="preview-device-bar">
              <view class="preview-device-info">
                <view class="preview-status-row">
                  <view :class="['preview-status-dot', connected ? 'on' : 'off']"></view>
                  <text>{{ connected ? '已连接' : '未连接' }}</text>
                </view>
                <view class="preview-device-name">
                  <text>{{ connected ? '连接方式' : '点击连接' }}</text>
                  <text class="preview-arrow">›</text>
                </view>
              </view>
              <view class="preview-more">•••</view>
            </view>

            <view class="preview-panel-body">
              <view v-for="widget in orderedWidgets" :key="widget.id" class="preview-widget-slot">
                <view class="preview-widget-shell" :class="{ 'is-collapsed': !!widget.collapsed }">
                  <view class="preview-widget-head">
                    <text class="preview-widget-icon">{{ widgetIcon(widget.type) }}</text>
                    <text class="preview-widget-title">{{ widgetTitle(widget) }}</text>
                    <view class="preview-widget-actions">
                      <view v-if="widget.type === 'key-grid'" class="preview-action">⇄</view>
                      <view v-if="widget.type === 'mouse-control'" class="preview-action">⛶</view>
                      <view class="preview-action">{{ widget.collapsed ? '⌄' : '⌃' }}</view>
                    </view>
                  </view>
                  <view v-if="!widget.collapsed" class="preview-widget-body">
                    <PanelKeyGrid
                      v-if="widget.type === 'key-grid'"
                      :slots="slots"
                      :grid-cols="gridCols"
                      :layouts="layouts"
                      :active-layout-id="activeLayoutId"
                      :active-page-id="activePageId"
                      :preview="true" />
                    <PanelTextInput v-else-if="widget.type === 'text-input'" :preview="true" />
                    <PanelMouseControl v-else-if="widget.type === 'mouse-control'" :preview="true" />
                    <PanelVolumeControl v-else-if="widget.type === 'volume-control'" :preview="true" />
                    <PanelFullKeyboard v-else-if="widget.type === 'full-keyboard'" :force-expand="false" :preview="true" />
                    <PanelCodexMicro v-else-if="widget.type === 'codex-micro'" />
                    <PanelJianyingWorkbench v-else-if="widget.type === 'jianying-workbench'" :preview="true" :storage-scope="layoutName + ':' + widget.id" />
                    <view v-else class="preview-empty">未知组件</view>
                  </view>
                </view>
              </view>
              <view v-if="orderedWidgets.length === 0" class="preview-empty preview-empty-panel">当前面板暂无组件</view>
              <view class="preview-add">＋ 添加组件</view>
            </view>

          </view>
        </view>
        <view class="preview-tabbar">
          <view v-for="tab in visibleTabs" :key="tab.id" class="preview-tab-item" :class="{ active: tab.id === 'p-panel' }">
            <text class="preview-tab-icon">{{ tabIcon(tab) }}</text>
            <text class="preview-tab-label">{{ tabLabel(tab) }}</text>
          </view>
        </view>
      </view>
    </view>
    <text class="preview-caption">主页实时预览</text>
  </view>
</template>

<script>
import PanelKeyGrid from '@/components/PanelKeyGrid.vue'
import PanelTextInput from '@/components/PanelTextInput.vue'
import PanelMouseControl from '@/components/PanelMouseControl.vue'
import PanelVolumeControl from '@/components/PanelVolumeControl.vue'
import PanelFullKeyboard from '@/components/PanelFullKeyboard.vue'
import PanelCodexMicro from '@/components/PanelCodexMicro.vue'
import PanelJianyingWorkbench from '@/components/PanelJianyingWorkbench.vue'

export default {
  name: 'CustomAppPreview',
  components: { PanelKeyGrid, PanelTextInput, PanelMouseControl, PanelVolumeControl, PanelFullKeyboard, PanelCodexMicro, PanelJianyingWorkbench },
  props: {
    widgets: { type: Array, default: () => [] },
    tabs: { type: Array, default: () => [] },
    connected: { type: Boolean, default: false },
    slots: { type: Array, default: () => [] },
    gridCols: { type: Number, default: 4 },
    layouts: { type: Array, default: () => [] },
    activeLayoutId: { type: String, default: '' },
    activePageId: { type: String, default: '' },
    layoutName: { type: String, default: '默认面板' },
    theme: { type: Object, default: () => ({}) },
  },
  computed: {
    orderedWidgets() {
      return (this.widgets || [])
        .filter(function (widget) { return widget && widget.visible !== false })
        .slice()
        .sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
    },
    visibleTabs() {
      return (this.tabs || [])
        .filter(function (tab) { return tab && tab.enabled !== false })
        .slice()
        .sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
    },
    themeStyle() {
      const vars = (this.theme && this.theme.vars) || {}
      const style = {}
      Object.keys(vars).forEach(function (key) { style[key] = vars[key] })
      return style
    },
  },
  methods: {
    widgetTitle(widget) {
      if (widget.type === 'text-input') return '文字输入'
      return widget.title || widget.type || '组件'
    },
    widgetIcon(type) {
      const icons = {
        'key-grid': '⌘',
        'text-input': '▦',
        'mouse-control': '◉',
        'volume-control': '♪',
        'codex-micro': '◉',
      }
      return icons[type] || '◇'
    },
    tabIcon(tab) {
      const icons = {
        'p-panel': '⌂',
        'p-layout': '▣',
        'p-devices': '▤',
        'p-profile': '♙',
        'w-key-grid': '⌘',
        'w-text-input': '▦',
        'w-mouse-control': '◉',
        'w-volume': '♪',
      }
      return icons[tab && tab.id] || '◇'
    },
    tabLabel(tab) {
      const labels = { 'p-panel': '控制', 'p-layout': '布局', 'p-devices': '设备', 'p-profile': '我的' }
      return labels[tab && tab.id] || (tab && tab.label) || ''
    },
  },
}
</script>

<style>
.custom-app-preview {
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  flex-direction: column;
}
.preview-device {
  width: 520rpx;
  height: 1056rpx;
  max-height: 1056rpx;
  flex: none;
  min-height: 0;
  padding: 6rpx;
  border-radius: 42rpx;
  background: #1C2A3B;
  box-shadow: 0 22rpx 52rpx rgba(28,58,92,0.22), 0 2rpx 5rpx rgba(28,58,92,0.12);
  box-sizing: border-box;
}
.preview-screen {
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 32rpx;
  background: #F4F8FD;
}
.preview-stage {
  width: 750rpx;
  min-height: 1280rpx;
  margin-left: 30rpx;
  transform: scale(0.6);
  transform-origin: top left;
  margin-bottom: -172rpx;
  background: #F4F8FD;
}
.preview-panel {
  min-height: 1080rpx;
  padding-bottom: 30rpx;
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}
.preview-device-bar {
  padding: 26rpx 32rpx 18rpx;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.preview-device-info { display: flex; flex-direction: column; }
.preview-status-row { display: flex; align-items: center; gap: 10rpx; color: #637083; font-size: 22rpx; }
.preview-status-dot { width: 14rpx; height: 14rpx; border-radius: 50%; background: #AEB8C6; }
.preview-status-dot.on { background: #22B85A; }
.preview-status-dot.off { background: #E34C4C; }
.preview-device-name { display: flex; align-items: center; gap: 8rpx; margin-top: 4rpx; color: #172033; font-size: 32rpx; font-weight: 650; }
.preview-arrow { color: #A3ADBA; font-size: 28rpx; }
.preview-more { width: 64rpx; height: 64rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid #DCE6F1; border-radius: 20rpx; background: rgba(255,255,255,0.94); color: #1E2A3B; font-size: 28rpx; }
.preview-panel-body { padding: 0 24rpx 26rpx; }
.preview-widget-slot { margin-bottom: 16rpx; }
.preview-widget-shell { overflow: hidden; border: 1rpx solid #E2E8F0; border-radius: 22rpx; background: rgba(255,255,255,0.96); box-shadow: 0 8rpx 24rpx rgba(48,79,114,0.06); }
.preview-widget-head { min-height: 76rpx; padding: 18rpx 24rpx 14rpx; display: flex; align-items: center; gap: 12rpx; box-sizing: border-box; }
.preview-widget-icon { color: #2F78F6; font-size: 29rpx; font-weight: 700; }
.preview-widget-title { flex: 1; color: #172033; font-size: 28rpx; font-weight: 650; }
.preview-widget-actions { display: flex; align-items: center; gap: 4rpx; }
.preview-action { width: 56rpx; height: 56rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid #E1E7EF; border-radius: 14rpx; color: #1E2B3C; font-size: 28rpx; }
.preview-widget-body { padding: 4rpx 24rpx 22rpx; }
.preview-widget-body .section { margin-top: 0; padding: 0; background: transparent; border: 0; box-shadow: none; }
.preview-widget-body .section-head { display: none; }
.preview-widget-body .key-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-auto-rows: 96rpx; gap: 16rpx; }
.preview-widget-body .key-btn { min-width: 0; min-height: 96rpx; padding: 8rpx 6rpx; background: #FFFFFF; border: 1rpx solid #DCE4EE; border-radius: 12rpx; box-shadow: 0 2rpx 6rpx rgba(48,79,114,0.04); }
.preview-widget-body .key-label { color: #1E2B3C; font-size: 22rpx; }
.preview-widget-body .key-sub { margin-top: 6rpx; color: #6B7888; font-size: 18rpx; }
.preview-widget-body .text-input { height: 80rpx; min-height: 80rpx; padding: 18rpx 22rpx; border: 1rpx solid #DDE4ED; border-radius: 14rpx; background: #FFFFFF; font-size: 25rpx; }
.preview-widget-body .text-actions { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 16rpx; margin-top: 16rpx; }
.preview-widget-body .btn-secondary, .preview-widget-body .btn-primary { height: 60rpx; min-width: 124rpx; padding: 0 28rpx; border-radius: 14rpx; font-size: 24rpx; }
.preview-widget-body .tp-body { padding: 0; gap: 12rpx; }
.preview-widget-body .tp-pad { width: 100%; height: 188rpx; border: 1rpx solid #DFE6EF; border-radius: 18rpx; background: #F4F7FB; }
.preview-widget-body .tp-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12rpx; }
.preview-widget-body .tp-btn { height: 58rpx; padding: 0 8rpx; border: 1rpx solid #E1E7EF; border-radius: 12rpx; background: #FFFFFF; color: #465468; font-size: 21rpx; }
.preview-empty { padding: 30rpx; text-align: center; color: #8996A7; font-size: 22rpx; }
.preview-add { height: 64rpx; margin: 18rpx 30rpx 0; display: flex; align-items: center; justify-content: center; border: 2rpx dashed rgba(62,125,205,0.34); border-radius: 14rpx; color: #4C78B4; font-size: 22rpx; }
.preview-tabbar { position: absolute; left: 0; right: 0; bottom: 0; min-height: 86rpx; padding: 7rpx 10rpx 8rpx; display: flex; border-top: 1rpx solid #DFE8F2; background: rgba(255,255,255,0.98); box-shadow: 0 -7rpx 18rpx rgba(47,78,113,0.05); box-sizing: border-box; z-index: 4; }
.preview-tab-item { flex: 1; min-height: 68rpx; display: flex; align-items: center; justify-content: center; flex-direction: column; border-radius: 12rpx; color: #8290A3; }
.preview-tab-item.active { color: #2F78F6; }
.preview-tab-icon { min-height: 28rpx; font-size: 24rpx; font-weight: 650; line-height: 1; }
.preview-tab-label { margin-top: 4rpx; font-size: 17rpx; font-weight: 650; line-height: 1; }
.preview-caption { margin-top: 14rpx; color: #7E8B9E; font-size: 20rpx; }
</style>
