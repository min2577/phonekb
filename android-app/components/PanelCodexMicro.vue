<template>
  <view class="micro-surface">
    <view class="micro-console">
      <view class="console-status">
        <view :class="['micro-connection', { 'is-connected': connected && available }]">
          <view class="connection-dot"></view>
          <text>{{ connectionLabel }}</text>
        </view>
        <text>{{ runningCount }} 运行 / {{ completedCount }} 完成</text>
      </view>

      <view class="micro-grid">
        <view :class="['dial-control', { 'is-recording': isRecordingControl('reasoning_dial') }]"
              hover-class="dial-control-hover"
              @tap="onControlTap('reasoning_dial')"
              @touchstart.stop="onControlTouchStart('reasoning_dial')"
              @touchend.stop="onControlTouchEnd('reasoning_dial')"
              @touchcancel.stop="onControlTouchEnd('reasoning_dial')">
          <view class="dial-disc">
            <view class="dial-notch"></view>
            <text>{{ controlDiscText('reasoning_dial') }}</text>
          </view>
          <text class="dial-label">{{ controlMeta('reasoning_dial').label }}</text>
        </view>

        <view v-for="task in displayTasks"
              :key="task.slot"
              :class="['agent-key', 'agent-' + task.slot, 'state-' + task.state, { 'is-selected': task.slot === selectedSlot, 'is-empty': isTrulyEmptyTask(task) }]"
              hover-class="agent-key-hover"
              @longpress.stop="bindTaskSlot(task)"
              @tap="selectTask(task)">
          <text class="agent-number">{{ task.slot }}</text>
          <view class="agent-led"></view>
          <text v-if="isTrulyEmptyTask(task)" class="agent-empty-plus">+</text>
          <text class="agent-name">{{ task.name }}</text>
          <text class="agent-state">{{ taskStateLabel(task) }}</text>
        </view>

        <view :class="['joystick-control', { 'is-recording': isRecordingControl('workflow_dial') }]"
              hover-class="joystick-control-hover"
              @tap="onControlTap('workflow_dial')"
              @touchstart.stop="onControlTouchStart('workflow_dial')"
              @touchend.stop="onControlTouchEnd('workflow_dial')"
              @touchcancel.stop="onControlTouchEnd('workflow_dial')">
          <view class="joystick-disc">
            <view class="joystick-notch"></view>
            <text class="joystick-symbol">{{ controlDiscText('workflow_dial') }}</text>
          </view>
          <text class="joystick-label">{{ controlMeta('workflow_dial').label }}</text>
        </view>

        <view :class="['action-key', 'action-skill', { 'is-disabled': isControlDisabled('action_skill'), 'is-recording': isRecordingControl('action_skill') }]"
              hover-class="action-key-hover"
              @tap="onControlTap('action_skill')"
              @touchstart.stop="onControlTouchStart('action_skill')"
              @touchend.stop="onControlTouchEnd('action_skill')"
              @touchcancel.stop="onControlTouchEnd('action_skill')">
          <text class="action-symbol">{{ controlMeta('action_skill').symbol }}</text>
          <text>{{ controlLabel('action_skill') }}</text>
        </view>
        <view :class="['action-key', 'action-approve', { 'is-disabled': isControlDisabled('action_approve'), 'is-recording': isRecordingControl('action_approve') }]"
              hover-class="action-key-hover"
              @tap="onControlTap('action_approve')"
              @touchstart.stop="onControlTouchStart('action_approve')"
              @touchend.stop="onControlTouchEnd('action_approve')"
              @touchcancel.stop="onControlTouchEnd('action_approve')">
          <text class="action-symbol">{{ controlMeta('action_approve').symbol }}</text>
          <text>{{ controlLabel('action_approve') }}</text>
        </view>
        <view :class="['action-key', 'action-reject', { 'is-disabled': isControlDisabled('action_reject'), 'is-recording': isRecordingControl('action_reject') }]"
              hover-class="action-key-hover"
              @tap="onControlTap('action_reject')"
              @touchstart.stop="onControlTouchStart('action_reject')"
              @touchend.stop="onControlTouchEnd('action_reject')"
              @touchcancel.stop="onControlTouchEnd('action_reject')">
          <text class="action-symbol">{{ controlMeta('action_reject').symbol }}</text>
          <text>{{ controlLabel('action_reject') }}</text>
        </view>
        <view :class="['action-key', 'action-switch', { 'is-disabled': isControlDisabled('action_switch'), 'is-recording': isRecordingControl('action_switch') }]"
              hover-class="action-key-hover"
              @tap="onControlTap('action_switch')"
              @touchstart.stop="onControlTouchStart('action_switch')"
              @touchend.stop="onControlTouchEnd('action_switch')"
              @touchcancel.stop="onControlTouchEnd('action_switch')">
          <text class="action-symbol">{{ controlMeta('action_switch').symbol }}</text>
          <text>{{ controlLabel('action_switch') }}</text>
        </view>

        <view :class="['wake-control', { 'is-disabled': isControlDisabled('action_refresh'), 'is-recording': isRecordingControl('action_refresh') }]"
              hover-class="wake-control-hover"
              @tap="onControlTap('action_refresh')"
              @touchstart.stop="onControlTouchStart('action_refresh')"
              @touchend.stop="onControlTouchEnd('action_refresh')"
              @touchcancel.stop="onControlTouchEnd('action_refresh')">
          <view class="wake-disc">
            <view v-if="controlActionId('action_refresh') === 'refresh'" class="wake-ring"></view>
            <text v-else class="wake-symbol">{{ controlMeta('action_refresh').symbol }}</text>
          </view>
          <text>{{ controlLabel('action_refresh') }}</text>
        </view>
        <view :class="['voice-key', { 'is-disabled': isControlDisabled('action_voice'), 'is-recording': isRecordingControl('action_voice') }]"
              hover-class="voice-key-hover"
              @tap="onControlTap('action_voice')"
              @touchstart.stop="onControlTouchStart('action_voice')"
              @touchend.stop="onControlTouchEnd('action_voice')"
              @touchcancel.stop="onControlTouchEnd('action_voice')">
          <view v-if="controlActionId('action_voice') === 'voice'" class="mic-glyph"><view></view></view>
          <view v-else class="voice-action-symbol">{{ controlMeta('action_voice').symbol }}</view>
          <text>{{ controlLabel('action_voice') }}</text>
          <text class="voice-sub">{{ controlSubLabel('action_voice') }}</text>
        </view>
        <view :class="['action-key', 'action-new', { 'is-disabled': isControlDisabled('action_new'), 'is-recording': isRecordingControl('action_new') }]"
              hover-class="action-key-hover"
              @tap="onControlTap('action_new')"
              @touchstart.stop="onControlTouchStart('action_new')"
              @touchend.stop="onControlTouchEnd('action_new')"
              @touchcancel.stop="onControlTouchEnd('action_new')">
          <text class="action-symbol">{{ controlMeta('action_new').symbol }}</text>
          <text>{{ controlLabel('action_new') }}</text>
        </view>
      </view>

      <view class="task-summary" hover-class="task-summary-hover" @tap="openSelectedTask">
        <view :class="['summary-bar', 'state-' + selectedTask.state]"></view>
        <view class="summary-copy">
          <text class="summary-title">{{ selectedTask.name }}</text>
          <text class="summary-detail">{{ selectedTask.detail }}</text>
        </view>
        <text v-if="isActiveTaskState(selectedTask.state)"
              class="summary-stop"
              @tap.stop="emitAction('cancel')">■</text>
        <text v-else class="summary-open">↗</text>
      </view>

      <view v-if="composerOpen" class="prompt-panel">
        <view class="panel-title-row">
          <text class="panel-title">{{ composerMode === 'resume' ? '继续任务 ' : '新任务 ' }}{{ selectedSlot }}</text>
          <text class="panel-close" @tap="closeComposer">×</text>
        </view>
        <view v-if="selectedTask.session_id" class="composer-mode">
          <view :class="{ active: composerMode === 'create' }" @tap="composerMode = 'create'">新任务</view>
          <view :class="{ active: composerMode === 'resume' }" @tap="composerMode = 'resume'">继续任务</view>
        </view>
        <textarea v-model="promptText"
                  class="prompt-input"
                  :maxlength="8000"
                  auto-height
                  placeholder="输入要交给 Codex 的任务" />
        <view class="prompt-actions">
          <view :class="['prompt-voice', { active: voicePressed }]"
                @touchstart="onVoiceStart('composer')"
                @touchend="onVoiceEnd"
                @touchcancel="onVoiceEnd">
            <text>{{ voicePressed ? '正在听' : '按住说话' }}</text>
          </view>
          <view class="prompt-send" @tap="submitPrompt">发送给 Codex</view>
        </view>
      </view>

      <view v-if="resultOpen" class="result-panel">
        <view class="panel-title-row">
          <text class="panel-title">{{ selectedTask.name }}</text>
          <text class="panel-close" @tap="resultOpen = false">×</text>
        </view>
        <scroll-view scroll-y class="result-scroll">
          <text class="result-text" selectable>{{ selectedTask.result || selectedTask.detail }}</text>
        </scroll-view>
        <view v-if="selectedTask.session_id && !isActiveTaskState(selectedTask.state)"
              class="result-continue"
              @tap="openComposer('resume')">继续这个任务</view>
      </view>
    </view>

    <view class="micro-footer">
      <view class="workflow-chip" hover-class="workflow-chip-hover" @tap="cycleWorkflow">
        <text>当前工作流</text>
        <text class="workflow-name">{{ workflowLabel }}</text>
      </view>
      <view class="state-legend">
        <view v-for="item in legend" :key="item.state" class="legend-item">
          <view :class="['legend-dot', 'state-' + item.state]"></view>
          <text>{{ item.label }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import AndroidSpeech from '@/utils/androidSpeech.js'
import { getCodexActionMeta, loadCodexMicroKeyMap } from '@/utils/codexMicroConfig.js'
import { showTransientToast } from '@/utils/transientToast.js'

export default {
  name: 'PanelCodexMicro',
  props: {
    tasks: { type: Array, default: function () { return [] } },
    connected: { type: Boolean, default: false },
    available: { type: Boolean, default: false },
    desktopBindings: { type: Object, default: function () { return {} } },
    approval: { type: Object, default: function () { return {} } },
    initialReasoning: { type: String, default: 'high' },
  },
  data() {
    return {
      selectedSlot: 1,
      keyMap: loadCodexMicroKeyMap(),
      reasoning: this.initialReasoning,
      workflowIndex: 0,
      voicePressed: false,
      voiceDestination: 'codex',
      voiceHadResult: false,
      voiceSessionStartedAt: 0,
      speechErrorShown: false,
      suppressVoiceTap: false,
      composerOpen: false,
      composerMode: 'create',
      promptText: '',
      resultOpen: false,
      suppressTaskTap: false,
      workflows: [
        { id: 'review', label: '代码审查' },
        { id: 'debug', label: '修复问题' },
        { id: 'test', label: '运行测试' },
        { id: 'refactor', label: '重构优化' },
      ],
      reasoningLevels: ['low', 'medium', 'high', 'xhigh'],
      legend: [
        { state: 'running', label: '运行' },
        { state: 'waiting_input', label: '待输入' },
        { state: 'completed', label: '完成' },
        { state: 'attention', label: '待确认' },
        { state: 'failed', label: '错误' },
        { state: 'cancelled', label: '停止' },
        { state: 'idle', label: '空闲' },
      ],
    }
  },
  computed: {
    displayTasks() {
      const incoming = Array.isArray(this.tasks) ? this.tasks : []
      const slots = []
      for (let slot = 1; slot <= 6; slot++) {
        const task = incoming.find(function (item) { return Number(item && item.slot) === slot })
        const item = Object.assign({ slot: slot, name: '空任务槽', state: 'idle', detail: '长按绑定当前 Codex 任务', result: '', session_id: '' }, task || {})
        const binding = this.desktopBindings ? (this.desktopBindings[String(slot)] || this.desktopBindings[slot]) : null
        if (binding) {
          Object.assign(item, {
            name: binding.title || '已绑定任务',
            state: binding.state || 'idle',
            detail: binding.detail || '点击跳转到 Codex Desktop',
            desktop_binding: binding,
          })
          const approval = this.approval || {}
          if (approval.pending && Number(approval.slot) === slot && String(approval.thread_id || '') === String(binding.thread_id || '')) {
            item.state = 'attention'
            item.detail = approval.msg || 'Codex 正在等待批准终端操作'
            item.approval = approval
          }
        }
        slots.push(item)
      }
      return slots
    },
    selectedTask() {
      return this.displayTasks.find(function (task) { return task.slot === this.selectedSlot }.bind(this)) || this.displayTasks[0]
    },
    runningCount() {
      return this.displayTasks.filter(function (task) {
        return task.state === 'running' || task.state === 'starting' || task.state === 'waiting_input'
      }).length
    },
    completedCount() {
      return this.displayTasks.filter(function (task) { return task.state === 'completed' }).length
    },
    workflow() {
      return this.workflows[this.workflowIndex] || this.workflows[0]
    },
    workflowLabel() {
      return this.workflow.label
    },
    activeReasoning() {
      const binding = this.selectedTask && this.selectedTask.desktop_binding
      const value = binding && binding.reasoning_effort
      return this.reasoningLevels.indexOf(value) >= 0 ? value : this.reasoning
    },
    reasoningLabel() {
      const labels = { low: '轻度', medium: '中', high: '高', xhigh: '极高' }
      return labels[this.activeReasoning] || '高'
    },
    connectionLabel() {
      if (!this.connected) return '已断开'
      return this.available ? 'Codex 可用' : 'Codex 未就绪'
    },
    canResolveApproval() {
      const approval = this.approval || {}
      const binding = this.selectedTask && this.selectedTask.desktop_binding
      return !!(
        this.connected && this.available && binding && approval.pending &&
        Number(approval.slot) === Number(this.selectedSlot) &&
        String(approval.thread_id || '') === String(binding.thread_id || '') &&
        approval.fingerprint
      )
    },
  },
  watch: {
    initialReasoning(value) {
      if (this.reasoningLevels.indexOf(value) >= 0) this.reasoning = value
    },
  },
  created() {
    try {
      const saved = uni.getStorageSync('phonekb.codex.workflow')
      const index = this.workflows.findIndex(function (item) { return item.id === saved })
      if (index >= 0) this.workflowIndex = index
    } catch (e) {}
    const self = this
    this._keyMapListener = function() { self.keyMap = loadCodexMicroKeyMap() }
    try { uni.$on('phonekb:codex-micro-keymap-updated', this._keyMapListener) } catch (e) {}
  },
  beforeUnmount() {
    try { AndroidSpeech.cancel() } catch (e) {}
    try { uni.$off('phonekb:codex-micro-keymap-updated', this._keyMapListener) } catch (e) {}
  },
  methods: {
    controlActionId(controlId) {
      return this.keyMap[controlId]
    },
    controlMeta(controlId) {
      return getCodexActionMeta(this.controlActionId(controlId))
    },
    controlDiscText(controlId) {
      return this.controlActionId(controlId) === 'reasoning' ? this.reasoningLabel : this.controlMeta(controlId).symbol
    },
    controlLabel(controlId) {
      if (this.controlActionId(controlId) === 'voice' && this.voicePressed) return '智谱正在听'
      return this.controlMeta(controlId).label
    },
    controlSubLabel(controlId) {
      if (this.controlActionId(controlId) === 'voice') return this.voicePressed ? '松开结束' : '电脑端智谱语音'
      return this.controlMeta(controlId).hint
    },
    isRecordingControl(controlId) {
      return this.voicePressed && this.controlActionId(controlId) === 'voice'
    },
    isControlDisabled(controlId) {
      return this.isControlDisabledForAction(this.controlActionId(controlId))
    },
    onControlTouchStart(controlId) {
      if (this.controlActionId(controlId) === 'voice') this.onZhipuVoiceStart()
    },
    onControlTouchEnd(controlId) {
      if (this.controlActionId(controlId) === 'voice') this.onZhipuVoiceEnd()
    },
    onControlTap(controlId) {
      const action = this.controlActionId(controlId)
      if (action === 'voice') return
      this.executeControlAction(action)
    },
    executeControlAction(action) {
      if (action === 'reasoning') return this.cycleReasoning()
      if (action === 'workflow') return this.cycleWorkflow()
      if (action === 'skill') return this.openWorkflow()
      if (action === 'approve' || action === 'reject') return this.requestApproval(action)
      if (action === 'switch_task') return this.openSelectedTask()
      if (action === 'refresh') return this.refreshCodexStatus()
      if (action === 'new_task') {
        this.$emit('open-new-task')
        this.vibrate('medium')
        return
      }
      if (action === 'submit_enter') return this.emitAction('submit-enter')
      if (action === 'test_input') return this.sendCodexTestPhrase()
      if (action === 'bind_current') {
        this.$emit('bind-current-task', { slot: this.selectedSlot })
        this.vibrate('medium')
        return
      }
      if (action === 'cancel') {
        if (this.isControlDisabledForAction(action)) {
          uni.showToast({ title: '当前任务没有运行', icon: 'none' })
          return
        }
        return this.emitAction('cancel')
      }
    },
    isControlDisabledForAction(action) {
      if (action === 'approve' || action === 'reject') return !this.canResolveApproval
      if (action === 'cancel') return !this.isActiveTaskState(this.selectedTask.state)
      return false
    },
    isActiveTaskState(state) {
      return state === 'running' || state === 'starting' || state === 'waiting_input'
    },
    stateLabel(state) {
      const labels = { starting: '启动中', running: '运行中', waiting_input: '待输入', completed: '已完成', attention: '待确认', failed: '错误', idle: '可开始', cancelled: '已停止' }
      return labels[state] || '可开始'
    },
    taskStateLabel(task) {
      if (task && task.desktop_binding) return task.state === 'idle' ? '已绑定' : this.stateLabel(task.state)
      if (task && task.state === 'idle') return '长按绑定'
      return this.stateLabel(task && task.state)
    },
    isTrulyEmptyTask(task) {
      return !!(
        task && task.state === 'idle' &&
        !task.desktop_binding &&
        !task.session_id
      )
    },
    bindTaskSlot(task) {
      if (!task || task.slot < 1 || task.slot > 6) return
      this.suppressTaskTap = true
      const self = this
      setTimeout(function() { self.suppressTaskTap = false }, 600)
      this.selectedSlot = task.slot
      if (!task.desktop_binding) {
        this.$emit('bind-current-task', { slot: task.slot })
        this.vibrate('medium')
        return
      }
      try {
        uni.showActionSheet({
          itemList: ['重新绑定当前任务', '自定义名称', '解除绑定'],
          success: function(result) {
            if (result.tapIndex === 0) self.$emit('bind-current-task', { slot: task.slot })
            else if (result.tapIndex === 1) self.renameTaskSlot(task)
            else if (result.tapIndex === 2) self.unbindTaskSlot(task)
          },
        })
      } catch (e) {
        this.$emit('bind-current-task', { slot: task.slot })
      }
      this.vibrate('medium')
    },
    renameTaskSlot(task) {
      const self = this
      uni.showModal({
        title: '任务槽 ' + task.slot + ' 自定义名称',
        content: '留空并确定可恢复 Codex 左侧栏名称',
        editable: true,
        placeholderText: (task.desktop_binding && task.desktop_binding.title) || '输入名称',
        success: function(result) {
          if (!result.confirm) return
          self.$emit('rename-bound-task', { slot: task.slot, title: String(result.content || '').trim() })
        },
      })
    },
    unbindTaskSlot(task) {
      const self = this
      uni.showModal({
        title: '解除任务槽 ' + task.slot,
        content: '只会删除手机键盘的绑定，不会删除 Codex 任务。',
        success: function(result) {
          if (result.confirm) self.$emit('unbind-bound-task', { slot: task.slot })
        },
      })
    },
    selectTask(task) {
      if (this.suppressTaskTap) {
        this.suppressTaskTap = false
        return
      }
      this.selectedSlot = task.slot
      this.resultOpen = false
      this.$emit('select-task', task)
      if (task.desktop_binding) {
        this.$emit('focus-bound-task', { slot: task.slot, binding: task.desktop_binding })
      }
      this.vibrate('light')
    },
    cycleReasoning() {
      const index = this.reasoningLevels.indexOf(this.activeReasoning)
      const next = this.reasoningLevels[(index + 1) % this.reasoningLevels.length]
      this.$emit('set-reasoning', {
        slot: this.selectedSlot,
        reasoning: next,
        previous: this.activeReasoning,
        binding: this.selectedTask.desktop_binding || null,
      })
      this.vibrate('light')
    },
    cycleWorkflow() {
      this.workflowIndex = (this.workflowIndex + 1) % this.workflows.length
      this.persistWorkflow()
      this.$emit('set-workflow', this.workflow)
      uni.showToast({ title: '工作流：' + this.workflow.label, icon: 'none', duration: 1000 })
      this.vibrate('light')
    },
    openWorkflow() {
      const self = this
      try {
        uni.showActionSheet({
          itemList: this.workflows.map(function (item) { return item.label }),
          success: function (result) {
            self.workflowIndex = result.tapIndex
            self.persistWorkflow()
            self.$emit('set-workflow', self.workflow)
            uni.showToast({ title: '工作流：' + self.workflow.label, icon: 'none', duration: 1000 })
          },
        })
      } catch (e) {
        this.cycleWorkflow()
      }
    },
    persistWorkflow() {
      try { uni.setStorageSync('phonekb.codex.workflow', this.workflow.id) } catch (e) {}
    },
    emitAction(action) {
      this.$emit(action, { task: this.selectedTask, workflow: this.workflow, reasoning: this.reasoning })
      this.vibrate(action === 'approve' || action === 'reject' ? 'medium' : 'light')
    },
    requestApproval(action) {
      if (!this.connected || !this.available) {
        uni.showToast({ title: this.connected ? '电脑端没有找到 Codex' : '请先连接电脑', icon: 'none' })
        return
      }
      if (!this.canResolveApproval) {
        showTransientToast('当前任务没有待批准请求', 2000)
        return
      }
      this.emitAction(action)
    },
    refreshCodexStatus() {
      this.emitAction('refresh')
    },
    openComposer(mode) {
      if (this.isActiveTaskState(this.selectedTask.state)) {
        uni.showToast({ title: '该任务正在运行，请先停止或选择其他槽位', icon: 'none' })
        return
      }
      this.composerMode = mode === 'resume' && this.selectedTask.session_id ? 'resume' : 'create'
      this.resultOpen = false
      this.composerOpen = true
    },
    closeComposer() {
      if (this.voicePressed) this.onVoiceEnd()
      this.composerOpen = false
    },
    submitPrompt() {
      const prompt = String(this.promptText || '').trim()
      if (!prompt) {
        uni.showToast({ title: '请输入任务内容', icon: 'none' })
        return
      }
      if (!this.connected || !this.available) {
        uni.showToast({ title: this.connected ? '电脑端没有找到 Codex' : '请先连接电脑', icon: 'none' })
        return
      }
      this.$emit('submit-task', {
        slot: this.selectedSlot,
        prompt: prompt,
        mode: this.composerMode,
        session_id: this.selectedTask.session_id || '',
        workflow_id: this.workflow.id,
        reasoning_effort: this.reasoning,
      })
      this.promptText = ''
      this.composerOpen = false
      this.vibrate('medium')
    },
    openSelectedTask() {
      if (this.selectedTask.desktop_binding) {
        this.$emit('focus-bound-task', { slot: this.selectedTask.slot, binding: this.selectedTask.desktop_binding })
        this.vibrate('light')
        return
      }
      if (this.selectedTask.state === 'idle') {
        this.openComposer('create')
        return
      }
      this.composerOpen = false
      this.resultOpen = true
      this.vibrate('light')
    },
    sendCodexTestPhrase() {
      if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this.$emit('test-input')
      this.vibrate('medium')
    },
    onZhipuVoiceStart() {
      if (this.voicePressed) return
      if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this.voicePressed = true
      this.$emit('zhipu-voice-start')
      this.vibrate('medium')
    },
    onZhipuVoiceEnd() {
      if (!this.voicePressed) return
      this.voicePressed = false
      this.$emit('zhipu-voice-end')
      this.vibrate('light')
    },
    onVoiceStart(destination) {
      if (this.voicePressed) return
      this.voiceDestination = destination === 'composer' ? 'composer' : 'codex'
      if (this.voiceDestination === 'composer') {
        this.openComposer(this.selectedTask.session_id ? 'resume' : 'create')
        if (!this.composerOpen) return
      } else if (!this.connected) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this.voicePressed = true
      this.voiceHadResult = false
      this.voiceSessionStartedAt = Date.now()
      this.speechErrorShown = false
      this.$emit('voice-start', { destination: this.voiceDestination })
      this.vibrate('medium')
      if (typeof plus === 'undefined' || !plus.android) {
        this.voicePressed = false
        this.$emit('voice-end')
        uni.showToast({ title: 'Android 系统语音接口不可用', icon: 'none' })
        return
      }
      this.requestSpeechPermission()
    },
    requestSpeechPermission() {
      const self = this
      if (typeof plus === 'undefined' || !plus.android || typeof plus.android.requestPermissions !== 'function') {
        this.beginSpeechRecognition()
        return
      }
      try {
        plus.android.requestPermissions(['android.permission.RECORD_AUDIO'], function (result) {
          const denied = (result && result.deniedPresent ? result.deniedPresent : []).concat(result && result.deniedAlways ? result.deniedAlways : [])
          if (denied.length) {
            self.showSpeechError({ code: 'RECORD_AUDIO_DENIED', message: '麦克风权限未授予，请在系统设置中允许麦克风权限' })
            return
          }
          if (self.voicePressed) self.beginSpeechRecognition()
          else uni.showToast({ title: '权限已授予，请重新按住说话', icon: 'none' })
        }, function (error) {
          self.showSpeechError(error || { message: '请求麦克风权限失败' })
        })
      } catch (error) {
        this.showSpeechError(error)
      }
    },
    beginSpeechRecognition() {
      const self = this
      try {
        AndroidSpeech.start({
          lang: 'zh-CN',
          onResult: function (text) {
            const value = String(text || '').trim()
            if (!value) return
            self.voiceHadResult = true
            self.voicePressed = false
            if (self.voiceDestination === 'codex') {
              self.$emit('dictate', { text: value, append_space: true })
            } else {
              self.promptText = self.promptText ? (self.promptText + ' ' + value) : value
            }
            self.$emit('voice-end')
          },
          onError: function (error) {
            self.showSpeechError(error)
          },
        })
      } catch (e) {
        this.showSpeechError({ code: 'ANDROID_ASR_START_FAILED', message: String(e && e.message ? e.message : e) })
      }
    },
    showSpeechError(error) {
      if (this.speechErrorShown) return
      this.speechErrorShown = true
      this.voicePressed = false
      let detail = ''
      try { detail = typeof error === 'string' ? error : JSON.stringify(error || {}) } catch (e) { detail = String(error || '') }
      const code = error && error.code != null ? String(error.code) : ''
      const message = error && error.message ? String(error.message) : ''
      const content = [code ? '错误码: ' + code : '', message, detail && detail !== message ? detail : ''].filter(Boolean).join('\n').slice(0, 500)
      uni.showModal({
        title: '语音识别失败',
        content: content || '手机没有返回具体原因，请检查麦克风权限和系统语音识别服务',
        showCancel: false,
      })
    },
    onVoiceEnd() {
      if (!this.voicePressed) return
      this.voicePressed = false
      this.suppressVoiceTap = true
      const self = this
      setTimeout(function () { self.suppressVoiceTap = false }, 300)
      try { AndroidSpeech.stop() } catch (e) {}
      this.$emit('voice-end')
    },
    onVoiceTap() {
      if (this.suppressVoiceTap) return
      if (!this.voicePressed) uni.showToast({ title: '请按住语音键说话', icon: 'none' })
    },
    vibrate(type) {
      try { uni.vibrateShort({ type: type }) } catch (e) {}
    },
  },
}
</script>

<style scoped>
  .micro-surface { --micro-ink:var(--app-color-text,#213347); --micro-muted:var(--app-color-text-mid,#718399); --micro-line:var(--app-color-border,#D3DFE9); --micro-blue:#2878D4; --micro-green:#12945A; --micro-input:#C57B00; --micro-attention:#7657A8; --micro-red:#C7444B; --micro-stopped:#6B7280; --micro-idle:var(--app-color-disabled,#B1BBC5); color:var(--micro-ink); }
.micro-connection { display:flex; align-items:center; gap:8rpx; color:var(--micro-muted); font-size:18rpx; font-weight:750; letter-spacing:0; white-space:nowrap; }.connection-dot { width:12rpx; height:12rpx; border-radius:50%; background:var(--micro-idle); box-shadow:0 0 0 5rpx rgba(177,187,197,0.15); }.micro-connection.is-connected .connection-dot { background:var(--micro-green); box-shadow:0 0 0 5rpx rgba(18,148,90,0.13); }
.micro-console { padding:18rpx; border:1rpx solid var(--micro-line); border-radius:26rpx; background:var(--app-surface,rgba(255,255,255,0.76)); box-shadow:0 10rpx 24rpx rgba(20,39,52,0.10); }.console-status { min-height:32rpx; display:flex; align-items:flex-start; justify-content:space-between; gap:12rpx; color:var(--micro-muted); font-size:18rpx; font-weight:750; letter-spacing:1rpx; }.console-status text:last-child { color:var(--app-color-text-light,#8393A3); font-size:17rpx; letter-spacing:0; white-space:nowrap; }
.micro-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); grid-template-rows:132rpx 132rpx 110rpx 128rpx; gap:12rpx; margin-top:12rpx; }.agent-key,.action-key,.voice-key,.joystick-control { position:relative; overflow:hidden; display:flex; align-items:center; justify-content:center; flex-direction:column; border:1rpx solid var(--micro-line); border-radius:18rpx; background:var(--app-surface-strong,rgba(250,252,253,0.96)); box-shadow:0 5rpx 11rpx rgba(20,39,52,0.11); box-sizing:border-box; }.agent-key-hover,.action-key-hover,.voice-key-hover,.joystick-control-hover { transform:scale(0.975); }.agent-key.is-selected { border-color:var(--app-color-primary,#75A8DF); box-shadow:0 0 0 3rpx rgba(40,120,212,0.18),0 5rpx 11rpx rgba(20,39,52,0.11); }.agent-number { position:absolute; top:13rpx; left:14rpx; color:var(--app-color-text-light,#8797A7); font-size:19rpx; font-weight:800; letter-spacing:0.6rpx; }.agent-led { width:17rpx; height:17rpx; position:absolute; top:15rpx; right:14rpx; border-radius:50%; background:var(--micro-idle); box-shadow:0 0 0 5rpx rgba(177,187,197,0.15); }.agent-name { max-width:84%; margin-top:30rpx; overflow:hidden; color:var(--micro-ink); font-size:21rpx; font-weight:750; line-height:1.15; text-overflow:ellipsis; white-space:nowrap; }.agent-state { margin-top:7rpx; color:var(--micro-muted); font-size:17rpx; font-weight:650; }.agent-1{grid-column:2;grid-row:1}.agent-2{grid-column:3;grid-row:1}.agent-3{grid-column:1;grid-row:2}.agent-4{grid-column:2;grid-row:2}.agent-5{grid-column:3;grid-row:2}.agent-6{grid-column:4;grid-row:2}
.agent-key.is-empty { border:2rpx dashed var(--micro-muted); background:var(--app-surface,rgba(255,255,255,0.78)); box-shadow:none; }.agent-key.is-empty .agent-led { display:none; }.agent-empty-plus { margin-top:4rpx; color:var(--micro-ink); font-size:34rpx; font-weight:500; line-height:0.8; }.agent-key.is-empty .agent-name { margin-top:7rpx; font-size:18rpx; }.agent-key.is-empty .agent-state { margin-top:4rpx; }
.agent-key.state-running,
.agent-key.state-starting { background:var(--app-color-primary-bg,#EAF4FF); }
.agent-key.state-waiting_input { background:#FFF5D9; }
.agent-key.state-completed { background:var(--app-success-surface,#EFFAF5); }
.agent-key.state-attention { background:#F5F0FC; }
.agent-key.state-failed { background:var(--app-danger-surface,#FFF0F1); }
.agent-key.state-cancelled { background:var(--app-color-bg-alt,#F2F4F7); }

.agent-key.state-running .agent-led,
.summary-bar.state-running,
.legend-dot.state-running { background:var(--micro-blue); box-shadow:0 0 0 5rpx rgba(40,120,212,0.13); }
.agent-key.state-starting .agent-led,
.summary-bar.state-starting { background:var(--micro-blue); }
.agent-key.state-waiting_input .agent-led,
.summary-bar.state-waiting_input,
.legend-dot.state-waiting_input { background:var(--micro-input); box-shadow:0 0 0 5rpx rgba(197,123,0,0.16); }
.agent-key.state-completed .agent-led,
.summary-bar.state-completed,
.legend-dot.state-completed { background:var(--micro-green); box-shadow:0 0 0 5rpx rgba(18,148,90,0.13); }
.agent-key.state-attention .agent-led,
.summary-bar.state-attention,
.legend-dot.state-attention { background:var(--micro-attention); box-shadow:0 0 0 5rpx rgba(118,87,168,0.13); }
.agent-key.state-failed .agent-led,
.summary-bar.state-failed,
.legend-dot.state-failed { background:var(--micro-red); box-shadow:0 0 0 5rpx rgba(199,68,75,0.13); }
.agent-key.state-cancelled .agent-led,
.summary-bar.state-cancelled,
.legend-dot.state-cancelled { background:var(--micro-stopped); box-shadow:0 0 0 5rpx rgba(107,114,128,0.13); }
.legend-dot.state-idle { background:var(--micro-idle); box-shadow:none; }
.agent-key.state-running .agent-led,
.agent-key.state-waiting_input .agent-led { animation:micro-led-pulse 1.35s ease-in-out infinite; }
@keyframes micro-led-pulse { 0%,100% { opacity:0.58; } 50% { opacity:1; } }
.dial-control { grid-column:1; grid-row:1; display:flex; align-items:center; justify-content:center; flex-direction:column; }.dial-control-hover,.wake-control-hover { transform:scale(0.98); }.dial-disc { width:98rpx; height:98rpx; position:relative; display:flex; align-items:flex-end; justify-content:center; padding-bottom:15rpx; border:1rpx solid #C8D5DF; border-radius:50%; background:#F8FAFB; box-shadow:inset 6rpx 6rpx 11rpx rgba(255,255,255,0.98),inset -6rpx -6rpx 9rpx rgba(146,163,177,0.16),0 5rpx 11rpx rgba(46,79,112,0.13); color:#52677B; font-size:18rpx; font-weight:800; }.dial-notch { width:4rpx; height:28rpx; position:absolute; top:11rpx; border-radius:4rpx; background:#52677B; transform:rotate(37deg); transform-origin:50% 38rpx; }.dial-label { margin-top:8rpx; color:#667D91; font-size:17rpx; font-weight:750; }
.joystick-control { grid-column:4; grid-row:1; border-style:dashed; border-color:#8395A6; background:#EFF4F8; }.joystick-disc { width:74rpx; height:74rpx; position:relative; display:flex; align-items:center; justify-content:center; border:6rpx solid #25323F; border-radius:50%; background:#3D4B59; box-shadow:inset 0 3rpx 6rpx rgba(0,0,0,0.36),0 5rpx 6rpx rgba(35,49,63,0.16); }.joystick-notch { width:27rpx; height:3rpx; position:absolute; top:13rpx; left:17rpx; border-radius:3rpx; background:#182530; transform:rotate(-35deg); }.joystick-symbol { color:#F0F5F8; font-size:22rpx; font-weight:800; }.joystick-label { max-width:92%; margin-top:9rpx; overflow:hidden; color:#52677B; font-size:17rpx; font-weight:800; text-overflow:ellipsis; white-space:nowrap; }
.action-key { grid-row:3; background:var(--app-surface-strong,rgba(255,255,255,0.96)); }.action-skill{grid-column:1}.action-approve{grid-column:2}.action-reject{grid-column:3}.action-switch{grid-column:4}.action-symbol { color:var(--micro-ink); font-size:42rpx; font-weight:600; line-height:1; }.action-key text:last-child { margin-top:9rpx; color:var(--micro-muted); font-size:17rpx; font-weight:750; }.action-check{font-size:37rpx}.action-cross{font-size:44rpx}
.action-key.is-disabled,.voice-key.is-disabled,.wake-control.is-disabled { opacity:0.42; box-shadow:inset 0 1rpx 0 #FFFFFF; }
.wake-control { grid-column:1; grid-row:4; display:flex; align-items:center; justify-content:center; flex-direction:column; }.wake-disc { width:72rpx; height:72rpx; display:flex; align-items:center; justify-content:center; border:7rpx solid #E7EEF4; border-radius:50%; background:#111920; box-shadow:0 0 0 1rpx #9AABB9,inset 0 2rpx 5rpx rgba(0,0,0,0.80); }.wake-ring { width:20rpx; height:20rpx; border:2rpx solid #D7E4ED; border-radius:50%; }.wake-symbol { color:#D7E4ED; font-size:28rpx; font-weight:800; }.wake-control>text { max-width:92%; margin-top:10rpx; overflow:hidden; color:#667D91; font-size:17rpx; font-weight:750; text-overflow:ellipsis; white-space:nowrap; }.voice-key { grid-column:2 / span 2; grid-row:4; gap:7rpx; border-radius:20rpx; background:#F9FBFC; }.voice-key.is-recording,.action-key.is-recording,.wake-control.is-recording,.dial-control.is-recording,.joystick-control.is-recording { border-color:#D99839; background:#FFF2DF; }.mic-glyph { width:30rpx; height:38rpx; position:relative; border:3rpx solid #2E4559; border-radius:16rpx; }.mic-glyph view { width:3rpx; height:10rpx; position:absolute; bottom:-13rpx; left:11rpx; border-radius:3rpx; background:#2E4559; }.mic-glyph::after { content:''; width:24rpx; height:14rpx; position:absolute; left:0rpx; bottom:-6rpx; border:3rpx solid #2E4559; border-top:0; border-radius:0 0 16rpx 16rpx; }.voice-action-symbol { color:#2E4559; font-size:38rpx; font-weight:750; line-height:1; }.voice-key>text:nth-of-type(1) { margin-top:14rpx; color:#496378; font-size:22rpx; font-weight:800; }.voice-key>.voice-action-symbol+text { margin-top:0; }.voice-sub { max-width:90%; overflow:hidden; color:#8796A5; font-size:16rpx !important; font-weight:650 !important; text-overflow:ellipsis; white-space:nowrap; }.voice-key.is-recording .mic-glyph { border-color:#AD6900; }.voice-key.is-recording .mic-glyph::after { border-color:#AD6900; }.voice-key.is-recording .mic-glyph view { background:#AD6900; }.voice-key.is-recording>text:nth-of-type(1) { color:#98600B; }.action-new{grid-column:4;grid-row:4}.action-new .action-symbol { color:#3972A5; font-size:44rpx; }.action-new text:last-child { color:#5D7994; }
.task-summary { min-height:86rpx; margin-top:15rpx; padding:14rpx 15rpx; display:flex; align-items:center; gap:13rpx; border:1rpx solid var(--micro-line); border-radius:16rpx; background:var(--app-surface-strong,#F7FAFC); box-sizing:border-box; }.task-summary-hover { transform:scale(0.99); }.summary-bar { width:7rpx; height:42rpx; flex-shrink:0; border-radius:7rpx; background:var(--micro-idle); }.summary-copy { display:flex; min-width:0; flex:1; flex-direction:column; }.summary-title,.summary-detail { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.summary-title { color:var(--micro-ink); font-size:21rpx; font-weight:800; }.summary-detail { margin-top:5rpx; color:var(--micro-muted); font-size:18rpx; }.summary-open { color:var(--app-color-primary,#3B7CBB); font-size:31rpx; font-weight:600; }
.summary-stop { width:48rpx; height:48rpx; display:flex; align-items:center; justify-content:center; color:var(--micro-red); font-size:22rpx; }
.prompt-panel,.result-panel { margin-top:14rpx; padding:16rpx; border:1rpx solid var(--micro-line); border-radius:16rpx; background:var(--app-surface-strong,#FFFFFF); box-sizing:border-box; }.panel-title-row { min-height:44rpx; display:flex; align-items:center; justify-content:space-between; gap:12rpx; }.panel-title { min-width:0; overflow:hidden; color:var(--micro-ink); font-size:22rpx; font-weight:800; text-overflow:ellipsis; white-space:nowrap; }.panel-close { width:44rpx; height:44rpx; display:flex; align-items:center; justify-content:center; color:var(--micro-muted); font-size:34rpx; }.composer-mode { width:100%; height:56rpx; margin-top:10rpx; padding:4rpx; display:flex; border:1rpx solid var(--micro-line); border-radius:12rpx; background:var(--app-color-bg-alt,#EDF3F7); box-sizing:border-box; }.composer-mode view { display:flex; flex:1; align-items:center; justify-content:center; border-radius:9rpx; color:var(--micro-muted); font-size:18rpx; font-weight:750; }.composer-mode view.active { background:var(--app-surface-strong,#FFFFFF); color:var(--app-color-primary,#285D8D); }.prompt-input { width:100%; min-height:150rpx; max-height:300rpx; margin-top:12rpx; padding:15rpx; border:1rpx solid var(--micro-line); border-radius:12rpx; background:var(--app-surface-strong,#F8FAFC); box-sizing:border-box; color:var(--micro-ink); font-size:22rpx; line-height:1.45; }.prompt-actions { margin-top:12rpx; display:flex; gap:10rpx; }.prompt-voice,.prompt-send,.result-continue { min-height:64rpx; display:flex; align-items:center; justify-content:center; border-radius:12rpx; font-size:19rpx; font-weight:800; }.prompt-voice { width:160rpx; border:1rpx solid var(--micro-line); background:var(--app-color-bg-alt,#EFF4F8); color:var(--micro-muted); }.prompt-voice.active { border-color:#D99839; background:#FFF2DF; color:#98600B; }.prompt-send { flex:1; background:var(--app-color-primary,#245F94); color:#FFFFFF; }.result-scroll { width:100%; height:320rpx; margin-top:10rpx; padding:14rpx; border:1rpx solid var(--micro-line); border-radius:12rpx; background:var(--app-surface-strong,#F8FAFC); box-sizing:border-box; }.result-text { color:var(--micro-ink); font-size:20rpx; line-height:1.55; white-space:pre-wrap; }.result-continue { margin-top:12rpx; background:var(--app-color-primary,#245F94); color:#FFFFFF; }
.micro-footer { margin-top:16rpx; }.workflow-chip { min-height:58rpx; padding:0 16rpx; display:flex; align-items:center; justify-content:space-between; gap:12rpx; border:1rpx solid #D6E2EB; border-radius:15rpx; background:#F4F8FB; color:#738497; font-size:17rpx; font-weight:750; }.workflow-chip-hover { background:#EBF3FA; }.workflow-name { color:#35516A; font-size:20rpx; }.state-legend { margin-top:15rpx; display:flex; flex-wrap:wrap; justify-content:center; gap:11rpx 16rpx; }.legend-item { display:flex; align-items:center; gap:6rpx; color:#738497; font-size:16rpx; font-weight:700; }.legend-dot { width:10rpx; height:10rpx; border-radius:50%; }
.dial-disc { border-color:var(--micro-line); background:var(--app-surface-strong,#F8FAFB); color:var(--micro-muted); }.dial-notch { background:var(--micro-muted); }.dial-label,.joystick-label,.wake-control>text,.voice-key>text:nth-of-type(1),.voice-sub { color:var(--micro-muted); }
.joystick-control { border-color:var(--micro-muted); background:var(--app-surface,#EFF4F8); }.voice-key { background:var(--app-surface-strong,#F9FBFC); }.mic-glyph { border-color:var(--micro-ink); }.mic-glyph::after { border-color:var(--micro-ink); }.mic-glyph view { background:var(--micro-ink); }
.workflow-chip { border-color:var(--micro-line); background:var(--app-surface,#F4F8FB); color:var(--micro-muted); }.workflow-chip-hover { background:var(--app-color-primary-bg,#EBF3FA); }.workflow-name { color:var(--micro-ink); }.legend-item { color:var(--micro-muted); }
</style>
