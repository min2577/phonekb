<template>
  <view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
    <view class="topbar">
      <view class="topbar-back" @tap="onBack">‹ 返回</view>
      <text class="topbar-title">面板方案</text>
      <view class="topbar-save" :class="{ on: dirty }" @tap="onSave">
      <text v-if="saving" class="save-text">保存中…</text>
      <text v-else class="save-text">保存</text>
    </view>
    </view>

    <view class="section schemes-section">
      <view class="section-head">
        <text class="section-title">所有方案 ({{schemes.length}})</text>
        <view class="section-action section-action-primary" @tap="onAddScheme">+ 新建</view>
      </view>
      <view class="scheme-list">
        <view v-for="(s, idx) in schemes" :key="s.id"
              :class="[
        'scheme-item',
        s.id === activeId ? 'scheme-item-on' : '',
        s.id === dirtyActiveId ? 'scheme-item-dirty' : ''
      ]"
              :data-id="s.id"
              @tap="onPickScheme(s.id)">
          <text class="scheme-item-icon">{{s.icon || '📋'}}</text>
          <view class="scheme-item-info">
            <text class="scheme-item-name">{{s.name}}</text>
            <text class="scheme-item-meta">{{(s.components || []).length}} 组件 · {{countEnabled(s)}} 启用</text>
          </view>
          <text v-if="s.built_in" class="scheme-item-badge">内置</text>
          <text v-else class="scheme-item-badge user">我的</text>
          <view class="scheme-item-del" v-if="!s.built_in" :data-id="s.id" @tap.stop="onDeleteScheme(s.id)">×</view>
        </view>
      </view>
    </view>

    <view v-if="activeScheme" class="section components-section">
      <view class="section-head">
        <text class="section-title">{{activeScheme.name}} · 组件</text>
        <view class="section-action section-action-primary" @tap="onAddComponent">+ 添加</view>
      </view>

      <view v-if="!activeScheme.components || activeScheme.components.length === 0" class="empty-hint">
        这个方案还没有任何组件 · 点右上角"+ 添加"
      </view>

      <view class="component-list">
        <view v-for="(c, idx) in activeScheme.components" :key="c.id" class="component-item">
          <text class="component-item-icon">{{componentIcon(c.type)}}</text>
          <view class="component-item-info">
            <text class="component-item-name">{{componentName(c.type)}}</text>
            <text class="component-item-id">{{c.id}}</text>
          </view>
          <switch class="component-item-switch" :checked="c.enabled !== false" :data-idx="idx" @change="onToggleEnabled($event, idx)" />
          <view class="component-item-up" :data-idx="idx" @tap="onMoveUp(idx)">▲</view>
          <view class="component-item-down" :data-idx="idx" @tap="onMoveDown(idx)">▼</view>
          <view class="component-item-del" :data-idx="idx" @tap="onDeleteComponent(idx)">×</view>
        </view>
      </view>
    </view>

    <!-- 新建方案 modal -->
    <view v-if="showAddScheme" class="modal-mask" @tap="showAddScheme = false">
      <view class="modal" @tap.stop="">
        <view class="modal-head"><text class="modal-title">新建方案</text></view>
        <view class="modal-body">
          <view class="form-row">
            <text class="form-label">名称</text>
            <input class="form-input" :value="newScheme.name" @input="onNewSchemeName" placeholder="如:摸鱼模式" />
          </view>
          <view class="form-row">
            <text class="form-label">图标 (emoji)</text>
            <input class="form-input" :value="newScheme.icon" @input="onNewSchemeIcon" placeholder="如:🐟" />
          </view>
        </view>
        <view class="modal-foot">
          <view class="btn-cancel" @tap="showAddScheme = false">取消</view>
          <view class="btn-save" @tap="onConfirmAddScheme">创建</view>
        </view>
      </view>
    </view>

    <!-- 添加组件 modal -->
    <view v-if="showAddComponent" class="modal-mask" @tap="showAddComponent = false">
      <view class="modal" @tap.stop="">
        <view class="modal-head"><text class="modal-title">添加组件</text></view>
        <view class="modal-body">
          <view v-for="t in availableTypes" :key="t.type"
                class="type-btn" @tap="onPickComponentType(t.type)">
            <text class="type-icon">{{t.icon}}</text>
            <view class="type-info">
              <text class="type-name">{{t.name}}</text>
              <text class="type-desc">{{t.description}}</text>
            </view>
          </view>
        </view>
        <view class="modal-foot">
          <view class="btn-cancel" @tap="showAddComponent = false">取消</view>
        </view>
      </view>
    </view>

    <view class="footer-safe"></view>
    <CustomTabBar />
  </view>
</template>

<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
import { listTypes, getMeta } from '@/utils/componentRegistry.js'
import { loadLayouts, saveLayouts, getCurrentLayoutId, setCurrentLayoutId } from '@/utils/layoutConfig.js'
import { loadTabs } from '@/utils/tabConfig.js'

function genId(prefix) {
  return prefix + '_' + Math.random().toString(36).slice(2, 8)
}

function layoutToScheme(layout) {
  return {
    id: layout.id,
    name: layout.name,
    icon: layout.icon || '◇',
    built_in: !!layout.built_in,
    components: (layout.widgets || []).map(function(widget, index) {
      return {
        id: widget.id,
        type: widget.type,
        order: typeof widget.order === 'number' ? widget.order : index,
        enabled: widget.visible !== false,
        config: {
          title: widget.title,
          icon: widget.icon,
          collapsed: !!widget.collapsed,
        },
      }
    }),
  }
}

function schemeToLayout(scheme) {
  return {
    id: scheme.id,
    name: scheme.name,
    icon: scheme.icon || '◇',
    built_in: !!scheme.built_in,
    widgets: (scheme.components || []).map(function(component, index) {
      const meta = getMeta(component.type)
      const config = component.config || {}
      return {
        id: component.id,
        type: component.type,
        title: config.title || meta.name || component.type,
        icon: config.icon || meta.icon || '◇',
        visible: component.enabled !== false,
        collapsed: !!config.collapsed,
        order: typeof component.order === 'number' ? component.order : index,
      }
    }),
  }
}

export default {
  components: { CustomTabBar },
  data() {
    return {
      schemes: [],
      tabConfig: [],
      activeId: '',
      dirty: false,
      dirtyActiveId: '',
      saving: false,
      showAddScheme: false,
      newScheme: { name: '', icon: '✨' },
      showAddComponent: false,
      availableTypes: listTypes().map(function(t) { return Object.assign({ type: t }, getMeta(t)) }),
    }
  },
  computed: {
    activeScheme() {
      return this.schemes.find(function(s) { return s.id === this.activeId }) || null
    },
  },
  onShow() {
    if (this.dirty) return
    const layouts = loadLayouts()
    this.schemes = layouts.map(layoutToScheme)
    this.tabConfig = loadTabs()
    const currentId = getCurrentLayoutId()
    this.activeId = layouts.some(function(layout) { return layout.id === currentId })
      ? currentId
      : ((layouts[0] && layouts[0].id) || '')
  },
  onBack() {
    if (this.dirty) {
      const self = this
      uni.showModal({
        title: '未保存',
        content: '有未保存的修改,确定离开?',
        success: function(r) {
          if (r.confirm) uni.navigateBack()
        }
      })
    } else {
      uni.navigateBack()
    }
  },
  methods: {
    componentIcon(type) { return getMeta(type).icon },
    componentName(type) { return getMeta(type).name },
    countEnabled(s) { return (s.components || []).filter(function(c) { return c.enabled !== false }).length },
    onPickScheme(id) {
      if (this.activeId === id) return
      this.activeId = id
      this.dirty = true
      this.dirtyActiveId = id
    },
    onAddScheme() {
      this.newScheme = { name: '', icon: '✨' }
      this.showAddScheme = true
    },
    onNewSchemeName(e) { this.newScheme.name = String(e.detail.value || '') },
    onNewSchemeIcon(e) { this.newScheme.icon = String(e.detail.value || '✨') },
    onConfirmAddScheme() {
      const name = (this.newScheme.name || '').trim()
      if (!name) {
        uni.showToast({ title: '请输入名称', icon: 'none' })
        return
      }
      const id = genId('scheme')
      const newS = {
        id: id,
        name: name,
        icon: this.newScheme.icon || '✨',
        built_in: false,
        components: [
          { id: genId('kg'), type: 'key-grid', order: 0, enabled: true, config: {} },
        ],
      }
      this.schemes.push(newS)
      this.activeId = id
      this.dirty = true
      this.dirtyActiveId = id
      this.showAddScheme = false
    },
    onDeleteScheme(id) {
      const s = this.schemes.find(function(x) { return x.id === id })
      if (!s || s.built_in) return
      const self = this
      uni.showModal({
        title: '删除方案',
        content: '确定要删除方案「' + s.name + '」?',
        success: function(r) {
          if (!r.confirm) return
          self.schemes = self.schemes.filter(function(x) { return x.id !== id })
          if (self.activeId === id) self.activeId = self.schemes[0] ? self.schemes[0].id : ''
          self.dirty = true
        }
      })
    },
    onAddComponent() {
      this.showAddComponent = true
    },
    onPickComponentType(type) {
      const s = this.activeScheme
      if (!s) return
      if (!s.components) s.components = []
      s.components.push({
        id: genId(type.replace('-', '')),
        type: type,
        order: s.components.length,
        enabled: true,
        config: {},
      })
      this.dirty = true
      this.showAddComponent = false
    },
    onToggleEnabled(e, idx) {
      const s = this.activeScheme
      if (!s || !s.components || !s.components[idx]) return
      s.components[idx].enabled = !!e.detail.value
      this.dirty = true
    },
    onMoveUp(idx) {
      const s = this.activeScheme
      if (!s || idx <= 0) return
      const tmp = s.components[idx]
      s.components.splice(idx, 1)
      s.components.splice(idx - 1, 0, tmp)
      this._renumber(s)
      this.dirty = true
    },
    onMoveDown(idx) {
      const s = this.activeScheme
      if (!s || idx >= s.components.length - 1) return
      const tmp = s.components[idx]
      s.components.splice(idx, 1)
      s.components.splice(idx + 1, 0, tmp)
      this._renumber(s)
      this.dirty = true
    },
    onDeleteComponent(idx) {
      const s = this.activeScheme
      if (!s || !s.components || !s.components[idx]) return
      s.components.splice(idx, 1)
      this._renumber(s)
      this.dirty = true
    },
    _renumber(s) {
      s.components.forEach(function(c, i) { c.order = i })
    },
    onSave() {
      if (this.saving) return
      this.saving = true
      const self = this
      const layouts = this.schemes.map(schemeToLayout)
      const ok = saveLayouts(layouts) && setCurrentLayoutId(this.activeId)
      if (!ok) {
        uni.showToast({ title: '保存失败', icon: 'none' })
        this.saving = false
        return
      }
      self.dirty = false
      self.dirtyActiveId = ''
      self.saving = false
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      uni.showToast({ title: '已保存', icon: 'success', duration: 1000 })
    },
  },
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding-bottom: calc(144rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
}
.topbar {
  min-height: 92rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,0.94);
  border-bottom: 1rpx solid #DCE6F1;
}
.topbar-back {
  min-width: 94rpx;
  color: #506177;
  font-size: 24rpx;
  font-weight: 600;
}
.topbar-title {
  color: #172033;
  font-size: 31rpx;
  font-weight: 750;
}
.topbar-save {
  min-width: 94rpx;
  text-align: right;
  opacity: 0.45;
}
.topbar-save.on {
  opacity: 1;
}
.save-text {
  color: #2F78F6;
  font-size: 24rpx;
  font-weight: 700;
}
.section {
  margin: 24rpx 24rpx 0;
  padding: 20rpx 22rpx 10rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 28rpx;
  box-shadow: 0 12rpx 30rpx rgba(47, 78, 113, 0.07);
}
.section-head,
.scheme-item,
.component-item,
.type-btn,
.modal-head,
.modal-foot {
  display: flex;
  align-items: center;
}
.section-head {
  min-height: 58rpx;
  justify-content: space-between;
}
.section-title {
  color: #53657B;
  font-size: 23rpx;
  font-weight: 700;
}
.section-action {
  min-height: 50rpx;
  padding: 0 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13rpx;
  color: #2F78F6;
  font-size: 21rpx;
  font-weight: 700;
}
.section-action-primary {
  background: #EAF3FF;
}
.scheme-item,
.component-item {
  min-height: 94rpx;
  border-top: 1rpx solid #E8EEF5;
}
.scheme-item-on {
  margin: 8rpx 0;
  padding: 0 12rpx;
  border: 1rpx solid #9FC3FF;
  border-radius: 18rpx;
  background: #F9FCFF;
}
.scheme-item-dirty {
  box-shadow: inset 4rpx 0 0 #2F78F6;
}
.scheme-item-icon,
.component-item-icon {
  width: 50rpx;
  height: 50rpx;
  margin-right: 15rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 23rpx;
}
.scheme-item-info,
.component-item-info,
.type-info {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.scheme-item-name,
.component-item-name,
.type-name {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.scheme-item-meta,
.component-item-id,
.type-desc {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 19rpx;
}
.scheme-item-badge {
  padding: 5rpx 12rpx;
  border-radius: 999rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 18rpx;
  font-weight: 650;
}
.scheme-item-badge.user {
  background: #EEF4FA;
  color: #607087;
}
.scheme-item-del,
.component-item-del,
.component-item-up,
.component-item-down {
  width: 42rpx;
  height: 42rpx;
  margin-left: 7rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  background: #EEF4FA;
  color: #607087;
  font-size: 18rpx;
}
.scheme-item-del,
.component-item-del {
  background: #FDE7E9;
  color: #D13438;
}
.component-item-switch {
  transform: scale(0.8);
}
.empty-hint {
  padding: 42rpx 0;
  border-top: 1rpx solid #E8EEF5;
  color: #8996A7;
  font-size: 22rpx;
  text-align: center;
}
.modal-mask {
  position: fixed;
  inset: 0;
  padding: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(23,32,51,0.34);
  z-index: 300;
}
.modal {
  width: 100%;
  max-height: 76vh;
  overflow: hidden;
  border: 1rpx solid #DCE6F1;
  border-radius: 28rpx;
  background: #FFFFFF;
  box-shadow: 0 28rpx 70rpx rgba(29,55,86,0.22);
}
.modal-head {
  min-height: 90rpx;
  padding: 0 26rpx;
  border-bottom: 1rpx solid #E8EEF5;
}
.modal-title {
  color: #172033;
  font-size: 29rpx;
  font-weight: 750;
}
.modal-body {
  max-height: 56vh;
  padding: 22rpx 26rpx;
  overflow-y: auto;
}
.form-row + .form-row {
  margin-top: 18rpx;
}
.form-label {
  display: block;
  margin-bottom: 9rpx;
  color: #53657B;
  font-size: 22rpx;
  font-weight: 650;
}
.form-input {
  height: 72rpx;
  padding: 0 18rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 14rpx;
  background: #F7FAFE;
  color: #172033;
  font-size: 25rpx;
}
.type-btn {
  min-height: 86rpx;
  border-bottom: 1rpx solid #E8EEF5;
}
.type-icon {
  width: 48rpx;
  height: 48rpx;
  margin-right: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13rpx;
  background: #EAF3FF;
  font-size: 23rpx;
}
.modal-foot {
  min-height: 88rpx;
  padding: 0 26rpx;
  justify-content: flex-end;
  gap: 14rpx;
  border-top: 1rpx solid #E8EEF5;
}
.btn-cancel,
.btn-save {
  min-width: 112rpx;
  height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  font-size: 23rpx;
  font-weight: 700;
}
.btn-cancel {
  background: #EEF4FA;
  color: #506177;
}
.btn-save {
  background: #2F78F6;
  color: #FFFFFF;
}
.footer-safe {
  height: 28rpx;
}
</style>
