<template>
<view :class="['page', 'key-editor-page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="editor-safe-top" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="editor-header">
    <view>
      <text class="editor-eyebrow">{{jianyingScope ? '剪映控制' : '按键设置'}}</text>
      <text class="editor-title">{{jianyingScope ? '编辑剪映快捷键' : (id ? '编辑自定义按键' : '新建自定义按键')}}</text>
    </view>
    <view class="editor-status"><text>{{id ? '编辑中' : '未保存'}}</text></view>
  </view>

  <view class="section identity-section">
    <view class="section-heading">
      <text class="section-title">显示</text>
      <text class="section-description">面板中的按键名称</text>
    </view>
    <view class="row">
      <text class="label">名称</text>
      <input class="input" placeholder="例如 格式化" placeholder-class="input-placeholder" placeholder-style="font-size:24rpx;color:#9CA3AF" maxlength="16" :value="label" @input="onLabelInput" />
    </view>
  </view>
  <view v-if="!jianyingScope" class="section action-section">
    <view class="section-heading">
      <text class="section-title">动作</text>
      <text class="section-description">选择按下这个键时在电脑上执行的操作</text>
    </view>
    <view class="row action-type-row">
      <view class="seg action-type-seg">
        <view :class="type === 'shortcut' ? 'seg-btn on' : 'seg-btn'" data-t="shortcut" @tap="onTypeChange"><text class="seg-icon">⌘</text><text>快捷键</text></view>
        <view :class="type === 'mouse' ? 'seg-btn on' : 'seg-btn'" data-t="mouse" @tap="onTypeChange"><text class="seg-icon">🖱</text><text>鼠标</text></view>
        <view :class="type === 'text' ? 'seg-btn on' : 'seg-btn'" data-t="text" @tap="onTypeChange"><text class="seg-icon">T</text><text>文本</text></view>
        <view :class="type === 'combo' ? 'seg-btn on' : 'seg-btn'" data-t="combo" @tap="onTypeChange"><text class="seg-icon">≡</text><text>多步操作</text></view>
        <view :class="type === 'link' ? 'seg-btn on' : 'seg-btn'" data-t="link" @tap="onTypeChange"><text class="seg-icon">↗</text><text>打开网站</text></view>
        <view :class="type === 'app' ? 'seg-btn on' : 'seg-btn'" data-t="app" @tap="onTypeChange"><text class="seg-icon">▣</text><text>打开软件</text></view>
        <view :class="type === 'codex' ? 'seg-btn on' : 'seg-btn'" data-t="codex" @tap="onTypeChange"><text class="seg-icon">C</text><text>Codex 功能</text></view>
      </view>
    </view>
  </view>

  <!-- shortcut 配置 -->
  <block v-if="type === 'shortcut'">
    <view class="section">
      <view class="preview-row">
        <view class="shortcut-preview">{{shortcutPreview || '（尚未设置）'}}</view>
        <view class="collapse-btn shortcut-collapse-btn"
              :aria-label="shortcutExpanded ? '收起快捷键编辑' : '展开快捷键编辑'"
              @tap="onToggleShortcutExpanded">{{shortcutExpanded ? '⌃' : '⌄'}}</view>
        <view class="clear-btn" hover-class="clear-btn-hover" @tap="onClearShortcut">清除</view>
      </view>
      <block v-if="shortcutExpanded">
      <view class="sub-title">常用快捷键 <text class="sub-meta">({{allPresets.length}})</text></view>
      <view class="preset-row">
        <view v-for="p in allPresets" :key="p.id"
              :class="isPresetActive(p) ? 'preset-chip on' : 'preset-chip'"
              :data-id="p.id"
              @tap="onPickPreset"
              @longpress="onLongPressPreset"
              hover-class="preset-chip-hover">
          <text class="preset-chip-label">{{p.label}}</text>
          <text class="preset-chip-sub">{{p.short}}</text>
        </view>
        <view :class="showAddPreset ? 'preset-chip-add on' : 'preset-chip-add'"
              @tap="onToggleAddPreset"
              hover-class="preset-chip-add-hover">
          <text>{{showAddPreset ? '×' : '+'}}</text>
        </view>
      </view>
      <block v-if="showAddPreset">
        <view class="add-preset-panel">
          <view class="row">
            <text class="label">名称</text>
            <input class="input" placeholder="例如：注释代码" placeholder-class="input-placeholder" placeholder-style="font-size:24rpx;color:#9CA3AF" maxlength="8" :value="newPresetLabel" @input="onNewPresetLabelInput" />
          </view>
          <view class="sub-title">修饰键</view>
          <view class="mod-row">
            <view v-for="m in MOD_LIST" :key="m.name"
                  :class="hasMod(newPresetMods, m.name) ? 'mod-chip on' : 'mod-chip'"
                  :data-mod="m.name"
                  hover-class="mod-chip-hover"
                  @tap="onToggleNewPresetMod">{{m.label}}</view>
          </view>
          <view class="sub-title">主键 - 字母</view>
          <view class="key-row">
            <view :class="!newPresetKey ? 'key-chip modifier-only-chip on' : 'key-chip modifier-only-chip'" data-key="" @tap="onPickNewPresetKey">仅修饰键</view>
            <view v-for="k in KEY_LETTERS" :key="k"
                  :class="newPresetKey === k ? 'key-chip on' : 'key-chip'" :data-key="k" @tap="onPickNewPresetKey">{{k}}</view>
          </view>
          <view class="sub-title">主键 - 数字 / 符号</view>
          <view class="key-row">
            <view v-for="k in KEY_DIGITS" :key="k"
                  :class="newPresetKey === k ? 'key-chip on' : 'key-chip'" :data-key="k" @tap="onPickNewPresetKey">{{k}}</view>
          </view>
          <view class="sub-title">主键 - 功能 / 导航</view>
          <view class="key-row">
            <view v-for="k in KEY_SPECIAL" :key="k.name"
                  :class="newPresetKey === k.name ? 'key-chip wide on' : 'key-chip wide'" :data-key="k.name" @tap="onPickNewPresetKey">{{k.label}}</view>
          </view>
          <view class="add-preset-actions">
            <view class="btn-secondary" @tap="onCancelAddPreset">取消</view>
            <view :class="canSaveNewPreset ? 'btn-primary' : 'btn-primary btn-disabled'" @tap="onConfirmAddPreset">保存模板</view>
          </view>
        </view>
      </block>      <view class="sub-title">修饰键（点 = 选/取消；可分左右）</view>
       <view class="mod-row">
        <view v-for="m in MOD_LIST" :key="m.name"
              :class="hasMod(modifiers, m.name) ? 'mod-chip on' : 'mod-chip'"
              :data-mod="m.name"
              hover-class="mod-chip-hover"
               @tap="onToggleMod">{{m.label}}</view>
       </view>
      </block>
    </view>
    <view v-if="shortcutExpanded" class="section">
      <view class="sub-title">主键 - 字母</view>
      <view class="key-row">
        <view :class="!key ? 'key-chip modifier-only-chip on' : 'key-chip modifier-only-chip'" data-key="" @tap="onPickKey">仅修饰键</view>
        <view v-for="k in KEY_LETTERS" :key="k"
              :class="key === k ? 'key-chip on' : 'key-chip'" :data-key="k" @tap="onPickKey">{{k}}</view>
      </view>
      <view class="sub-title">主键 - 数字 / 符号</view>
      <view class="key-row">
        <view v-for="k in KEY_DIGITS" :key="k"
              :class="key === k ? 'key-chip on' : 'key-chip'" :data-key="k" @tap="onPickKey">{{k}}</view>
      </view>
      <view class="sub-title">主键 - 功能 / 导航</view>
      <view class="key-row">
        <view v-for="k in KEY_SPECIAL" :key="k.name"
              :class="key === k.name ? 'key-chip wide on' : 'key-chip wide'" :data-key="k.name" @tap="onPickKey">{{k.label}}</view>
      </view>
    </view>
  </block>

  <block v-if="type === 'mouse'">
    <view class="section">
      <view class="sub-title">鼠标动作</view>
      <view class="mouse-action-row">
        <view :class="mouseOp === 'click' ? 'mouse-action-btn on' : 'mouse-action-btn'" data-op="click" @tap="onMouseOpChange">点击</view>
        <view :class="mouseOp === 'down' ? 'mouse-action-btn on' : 'mouse-action-btn'" data-op="down" @tap="onMouseOpChange">按下</view>
        <view :class="mouseOp === 'up' ? 'mouse-action-btn on' : 'mouse-action-btn'" data-op="up" @tap="onMouseOpChange">松开</view>
        <view :class="mouseOp === 'wheel' ? 'mouse-action-btn on' : 'mouse-action-btn'" data-op="wheel" @tap="onMouseOpChange">滚轮</view>
      </view>
      <view v-if="mouseOp !== 'wheel'" class="mouse-action-row">
        <view v-for="button in MOUSE_BUTTONS" :key="button.value"
              :class="mouseButton === button.value ? 'mouse-action-btn on' : 'mouse-action-btn'"
              :data-button="button.value" @tap="onMouseButtonChange">{{button.label}}</view>
      </view>
      <view v-else class="mouse-action-row">
        <view :class="mouseDelta > 0 ? 'mouse-action-btn on' : 'mouse-action-btn'" data-delta="120" @tap="onMouseDeltaChange">向上</view>
        <view :class="mouseDelta < 0 ? 'mouse-action-btn on' : 'mouse-action-btn'" data-delta="-120" @tap="onMouseDeltaChange">向下</view>
      </view>
    </view>
  </block>

  <!-- text 配置 -->
  <block v-if="type === 'text'">
    <view class="section">
      <view class="sub-title">注入文本</view>
      <textarea class="text-input" placeholder="点发送时注入到电脑" placeholder-class="text-input-ph" placeholder-style="font-size:24rpx;color:#9CA3AF" :value="textValue" @input="onTextInput" auto-height="true" maxlength="2000" />
      <view class="hint">支持中文 + 表情；发送时一次性注入</view>
    </view>
  </block>

  <block v-if="type === 'link'">
    <view class="section">
      <view class="sub-title">网站地址</view>
      <input class="input action-input" placeholder="https://example.com" placeholder-class="input-placeholder" :value="linkUrl" @input="onLinkUrlInput" maxlength="2048" />
      <view :class="readingClipboard ? 'btn-primary btn-disabled action-read-btn' : 'btn-primary action-read-btn'" @tap="onReadDesktopLink">{{readingClipboard && clipboardPurpose === 'link' ? '正在读取...' : '读取电脑复制的网址'}}</view>
      <view class="hint">也可以直接粘贴网站地址；保存后会由电脑的默认浏览器打开。</view>
    </view>
  </block>

  <block v-if="type === 'app'">
    <view class="section">
      <view class="sub-title">已选择的软件</view>
      <view class="app-selection">
        <text :class="selectedApp && selectedApp.name ? 'app-selection-name' : 'app-selection-empty'">{{selectedApp && selectedApp.name ? selectedApp.name : '尚未选择'}}</text>
        <text v-if="selectedApp && selectedApp.id" class="app-selection-status">已授权</text>
      </view>
      <view :class="readingClipboard ? 'btn-primary btn-disabled action-read-btn' : 'btn-primary action-read-btn'" @tap="onReadDesktopClipboard">{{readingClipboard ? '正在读取...' : (selectedApp && selectedApp.id ? '重新读取电脑复制的路径' : '读取电脑复制的路径')}}</view>
      <view class="hint">先在电脑中对软件的 .exe 文件使用“复制为路径”，再点击上方按钮自动填入。只会启动本次确认过的软件。</view>
    </view>
  </block>

  <block v-if="type === 'codex'">
    <view class="section codex-config-section">
      <view class="sub-title">Codex 动作</view>
      <view class="codex-action-row">
        <view :class="codexAction === 'focus_task' ? 'codex-action-btn on' : 'codex-action-btn'" data-a="focus_task" @tap="onCodexActionChange">
          <text class="codex-action-name">切换</text>
          <text class="codex-action-desc">打开绑定任务</text>
        </view>
        <view :class="codexAction === 'approve' ? 'codex-action-btn on' : 'codex-action-btn'" data-a="approve" @tap="onCodexActionChange">
          <text class="codex-action-name">批准</text>
          <text class="codex-action-desc">同意待确认操作</text>
        </view>
        <view :class="codexAction === 'reject' ? 'codex-action-btn on' : 'codex-action-btn'" data-a="reject" @tap="onCodexActionChange">
          <text class="codex-action-name">拒绝</text>
          <text class="codex-action-desc">拒绝待确认操作</text>
        </view>
      </view>
      <view class="sub-title codex-slot-title">目标任务槽</view>
      <view class="codex-slot-row">
        <view v-for="slot in CODEX_SLOTS" :key="slot"
              :class="codexSlot === slot ? 'codex-slot-btn on' : 'codex-slot-btn'"
              :data-slot="slot" @tap="onCodexSlotChange">{{slot}}</view>
      </view>
      <view v-if="codexAction === 'focus_task'" class="row codex-long-row">
        <view class="codex-long-copy">
          <text class="codex-long-title">长按绑定当前任务</text>
          <text class="codex-long-desc">短按切换，长按把电脑当前 Codex 任务绑定到该槽</text>
        </view>
        <switch :checked="codexLongPressBind" @change="onCodexLongPressChange" color="#2F78F6" />
      </view>
      <view class="hint">“切换”会打开该槽绑定的 Codex 任务；批准和拒绝仅在任务等待确认时生效。</view>
    </view>
  </block>

  <!-- combo 配置 (可视化步骤列表) -->
  <block v-if="type === 'combo'">
    <view class="section">
      <view class="macro-interval-row">
        <view class="macro-interval-copy">
          <text class="macro-interval-title">统一步骤间隔</text>
          <text class="macro-interval-desc">单独的等待步骤会替代该位置的统一间隔</text>
        </view>
        <view class="macro-interval-input-wrap">
          <input class="macro-interval-input" type="number" maxlength="4" :value="comboIntervalMs" @input="onComboIntervalInput" />
          <text class="macro-interval-unit">毫秒</text>
        </view>
      </view>
      <view class="macro-record-row">
        <view class="macro-record-copy">
          <text class="macro-record-title">录制电脑操作</text>
          <text class="macro-record-desc">只记录键盘、鼠标按钮和滚轮，不记录鼠标移动</text>
        </view>
        <view v-if="!recording" :class="recordingBusy ? 'btn-secondary btn-disabled' : 'btn-primary'" @tap="onStartRecording">录制</view>
        <view v-else class="btn-danger macro-stop-btn" @tap="onStopRecording">停止</view>
        <view v-if="comboSteps.length && !recording" class="btn-secondary macro-test-btn" @tap="onTestMacro">测试</view>
      </view>
      <view class="sub-title">步骤列表 <text class="sub-meta">({{comboSteps.length}} 步)</text></view>

      <view v-if="comboSteps.length === 0" class="empty-hint">
        还没有步骤 · 点下方按钮添加
      </view>

      <view v-for="(step, idx) in comboSteps" :key="idx"
            :class="stepDrag && stepDrag.index === idx ? 'step-row is-step-dragging' : 'step-row'"
            :data-idx="idx">
        <view class="step-head">
          <text class="step-num">{{idx + 1}}</text>
          <text v-if="stepCollapsed[idx]" class="step-type-summary">{{_stepTypeLabel(step.type)}}</text>
          <view v-else class="step-type-tabs">
            <view :class="step.type === 'key' ? 'step-type-tab on' : 'step-type-tab'" :data-idx="idx" data-t="key" @touchstart.stop @tap="onChangeStepType">快捷键</view>
            <view :class="step.type === 'text' ? 'step-type-tab on' : 'step-type-tab'" :data-idx="idx" data-t="text" @touchstart.stop @tap="onChangeStepType">文本</view>
            <view :class="step.type === 'wait_ms' ? 'step-type-tab on' : 'step-type-tab'" :data-idx="idx" data-t="wait_ms" @touchstart.stop @tap="onChangeStepType">等待</view>
            <view :class="step.type === 'enter' ? 'step-type-tab on' : 'step-type-tab'" :data-idx="idx" data-t="enter" @touchstart.stop @tap="onChangeStepType">回车</view>
            <view :class="step.type === 'mouse' ? 'step-type-tab on' : 'step-type-tab'" :data-idx="idx" data-t="mouse" @touchstart.stop @tap="onChangeStepType">鼠标</view>
          </view>
          <view class="step-insert-btn"
                :data-idx="idx"
                aria-label="在此步骤后添加"
                @touchstart.stop @tap="onInsertStepAfter">+</view>
          <view class="collapse-btn step-collapse-btn"
                :data-idx="idx"
                :aria-label="stepCollapsed[idx] ? '展开步骤' : '收起步骤'"
                @touchstart.stop @tap="onToggleStepCollapsed">{{stepCollapsed[idx] ? '⌄' : '⌃'}}</view>
          <text class="step-drag-handle"
                :data-idx="idx"
                aria-label="长按拖动步骤"
                @touchstart.stop="onStepDragStart"
                @touchmove.stop="onStepDragMove"
                @touchend.stop="onStepDragEnd"
                @touchcancel.stop="onStepDragEnd">⠿</text>
          <view class="step-del" :data-idx="idx" @touchstart.stop @tap="onRemoveStep">✕</view>
        </view>

        <view :class="stepCollapsed[idx] ? 'step-preview is-collapsed' : 'step-preview'">{{formatStepLabel(step) || '（尚未设置）'}}</view>

        <block v-if="!stepCollapsed[idx]">
        <block v-if="step.type === 'key'">
          <view class="step-mode-row">
            <text class="step-mode-label">执行</text>
            <view v-for="mode in STEP_MODES" :key="mode.value"
                  :class="(step.mode || 'tap') === mode.value ? 'step-mode-btn on' : 'step-mode-btn'"
                  :data-idx="idx" :data-mode="mode.value" @touchstart.stop @tap="onStepModeChange">{{mode.label}}</view>
          </view>
          <view class="mod-row">
            <view v-for="m in MOD_LIST" :key="m.name"
                  :class="stepHasMod(step, m.name) ? 'mod-chip on' : 'mod-chip'"
                  :data-idx="idx" :data-mod="m.name"
                  @touchstart.stop
                  hover-class="mod-chip-hover"
                  @tap="onStepToggleMod">{{m.label}}</view>
          </view>
          <view class="key-row">
            <view :class="!step.key ? 'key-chip modifier-only-chip on' : 'key-chip modifier-only-chip'" :data-idx="idx" data-key="" @touchstart.stop @tap="onStepPickKey">仅修饰键</view>
            <view v-for="k in KEY_LETTERS" :key="k"
                  :class="step.key === k ? 'key-chip on' : 'key-chip'" :data-idx="idx" :data-key="k" @touchstart.stop @tap="onStepPickKey">{{k}}</view>
          </view>
          <view class="sub-title step-key-subtitle">数字 / 符号</view>
          <view class="key-row">
            <view v-for="k in KEY_DIGITS" :key="k"
                  :class="step.key === k ? 'key-chip on' : 'key-chip'" :data-idx="idx" :data-key="k" @touchstart.stop @tap="onStepPickKey">{{k}}</view>
          </view>
          <view class="sub-title step-key-subtitle">功能 / 导航</view>
          <view class="key-row">
            <view v-for="k in KEY_SPECIAL" :key="k.name"
                  :class="step.key === k.name ? 'key-chip wide on' : 'key-chip wide'" :data-idx="idx" :data-key="k.name" @touchstart.stop @tap="onStepPickKey">{{k.label}}</view>
          </view>
        </block>

        <block v-if="step.type === 'mouse'">
          <view class="mouse-action-row step-mouse-row">
            <view :class="step.op === 'click' ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-op="click" @touchstart.stop @tap="onStepMouseOpChange">点击</view>
            <view :class="step.op === 'down' ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-op="down" @touchstart.stop @tap="onStepMouseOpChange">按下</view>
            <view :class="step.op === 'up' ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-op="up" @touchstart.stop @tap="onStepMouseOpChange">松开</view>
            <view :class="step.op === 'wheel' ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-op="wheel" @touchstart.stop @tap="onStepMouseOpChange">滚轮</view>
          </view>
          <view v-if="step.op === 'wheel'" class="mouse-action-row">
            <view :class="step.delta > 0 ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-delta="120" @touchstart.stop @tap="onStepMouseDeltaChange">向上</view>
            <view :class="step.delta < 0 ? 'mouse-action-btn on' : 'mouse-action-btn'" :data-idx="idx" data-delta="-120" @touchstart.stop @tap="onStepMouseDeltaChange">向下</view>
          </view>
          <view v-else class="mouse-action-row">
            <view v-for="button in MOUSE_BUTTONS" :key="button.value"
                  :class="step.button === button.value ? 'mouse-action-btn on' : 'mouse-action-btn'"
                  :data-idx="idx" :data-button="button.value" @touchstart.stop @tap="onStepMouseButtonChange">{{button.label}}</view>
          </view>
        </block>

        <block v-if="step.type === 'text'">
          <textarea class="text-input" placeholder="文本内容" placeholder-class="text-input-ph" placeholder-style="font-size:24rpx;color:#9CA3AF" :value="step.value" :data-idx="idx" @touchstart.stop @input="onStepTextInput" auto-height="true" maxlength="500" />
        </block>

        <block v-if="step.type === 'wait_ms'">
          <view class="wait-row">
            <input class="input wait-input" type="number" :value="step.value" :data-idx="idx" @touchstart.stop @input="onStepWaitInput" />
            <text class="wait-unit">毫秒</text>
          </view>
        </block>

        <block v-if="step.type === 'enter'">
          <view class="hint">触发一次回车键</view>
        </block>
        </block>
      </view>

      <view v-if="stepDrag" class="step-drag-ghost" :style="stepDragGhostStyle">
        <view class="step-head step-drag-ghost-head">
          <text class="step-num">{{stepDrag.index + 1}}</text>
          <text class="step-drag-ghost-type">{{_stepTypeLabel(stepDrag.step.type)}}</text>
          <text class="step-drag-handle">⠿</text>
        </view>
        <view class="step-preview step-drag-ghost-preview">{{formatStepLabel(stepDrag.step) || '未设置内容'}}</view>
      </view>

      <view class="add-step-row">
        <view class="add-step-btn" data-t="key" @tap="onAddStep">+ 快捷键</view>
        <view class="add-step-btn" data-t="text" @tap="onAddStep">+ 文本</view>
        <view class="add-step-btn" data-t="wait_ms" @tap="onAddStep">+ 等待</view>
        <view class="add-step-btn" data-t="enter" @tap="onAddStep">+ 回车</view>
        <view class="add-step-btn" data-t="mouse" @tap="onAddStep">+ 鼠标</view>
      </view>
    </view>
  </block>
  <view class="section">
    <view class="sub-title">触发反馈</view>
    <view class="row">
      <text class="label">震动</text>
      <switch :checked="feedback.vibrate" data-k="vibrate" @change="onToggleFeedback" color="#2F78F6" />
    </view>
    <view class="row">
      <text class="label">音效</text>
      <switch :checked="feedback.sound" data-k="sound" @change="onToggleFeedback" color="#2F78F6" />
    </view>
    <view class="row">
      <text class="label">屏幕提示</text>
      <switch :checked="feedback.toast" data-k="toast" @change="onToggleFeedback" color="#2F78F6" />
    </view>
  </view>

  <view class="footer-actions">
    <view v-if="id && !jianyingScope" class="btn-danger" @tap="onDelete">删除</view>
    <view :class="saving ? 'btn-primary btn-disabled' : 'btn-primary'" @tap="onSave">{{saving ? '保存中...' : '保存'}}</view>
  </view>
  <view class="footer-safe"></view>
</view>
<!-- 设为常用模板弹窗 -->
<view v-if="showSaveAsTemplate" class="modal-mask" @tap="onSaveTemplateCancel">
  <view class="modal-card" @tap.stop="">
    <view class="modal-title">设为常用模板？</view>
    <view class="modal-preview">{{shortcutPreview}}</view>
    <view class="row">
      <text class="label">名称</text>
      <input class="input" placeholder="例如：全选" placeholder-class="input-placeholder" placeholder-style="font-size:24rpx;color:#9CA3AF" maxlength="8" :value="saveTemplateLabel" @input="onSaveTemplateLabelInput" />
    </view>
    <view class="modal-actions">
      <view class="btn-secondary" @tap="onSaveTemplateCancel">下次再说</view>
      <view :class="saveTemplateLabel && saveTemplateLabel.length > 0 ? 'btn-primary' : 'btn-primary btn-disabled'" @tap="onSaveTemplateConfirm">保存</view>
    </view>
  </view>
</view></template>

<script>
let appE = null
try { appE = getApp({ allowDefault: true }) } catch (e) {}
import WS from '@/utils/net.js'
import { JIANYING_SHORTCUT_PRESETS, loadWorkbenchConfig, normalizeWorkbenchScope, saveWorkbenchConfig, updateShortcut, updateTimelineButton } from '@/utils/jianyingWorkbenchConfig.js'

const KEY_LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('')
const KEY_DIGITS = ["0","1","2","3","4","5","6","7","8","9","/","-","=",";",",",".","'","[","]","`","\\"]
const KEY_SPECIAL = [
  { name: 'f1', label: 'F1' }, { name: 'f2', label: 'F2' }, { name: 'f3', label: 'F3' }, { name: 'f4', label: 'F4' },
  { name: 'f5', label: 'F5' }, { name: 'f6', label: 'F6' }, { name: 'f7', label: 'F7' }, { name: 'f8', label: 'F8' },
  { name: 'f9', label: 'F9' }, { name: 'f10', label: 'F10' }, { name: 'f11', label: 'F11' }, { name: 'f12', label: 'F12' },
  { name: 'enter', label: 'Enter' }, { name: 'tab', label: 'Tab' }, { name: 'space', label: 'Space' },
  { name: 'backspace', label: '退格' }, { name: 'delete', label: '删除' }, { name: 'escape', label: 'Esc' },
  { name: 'home', label: 'Home' }, { name: 'end', label: 'End' },
  { name: 'pageup', label: 'PgUp' }, { name: 'pagedown', label: 'PgDn' },
  { name: 'left', label: '←' }, { name: 'right', label: '→' }, { name: 'up', label: '↑' }, { name: 'down', label: '↓' },
]
const STEP_MODES = [
  { value: 'tap', label: '点按' },
  { value: 'down', label: '按下' },
  { value: 'up', label: '松开' },
]
const MOUSE_BUTTONS = [
  { value: 'left', label: '左键' },
  { value: 'right', label: '右键' },
  { value: 'middle', label: '中键' },
]

const KEY_LABELS = {
  enter:'Enter', tab:'Tab', space:'Space', backspace:'退格', delete:'删除',
  escape:'Esc', home:'Home', end:'End', pageup:'PgUp', pagedown:'PgDn',
  left:'←', right:'→', up:'↑', down:'↓',
}

// ===== 修饰键列表（左右区分）=====
const MOD_LIST = [
  { name: 'lctrl',  label: 'LCtrl' },
  { name: 'rctrl', label: 'RCtrl' },
  { name: 'lshift',  label: 'LShift' },
  { name: 'rshift', label: 'RShift' },
  { name: 'lalt',  label: 'LAlt' },
  { name: 'ralt', label: 'RAlt' },
  { name: 'lwin',  label: 'LWin' },
  { name: 'rwin', label: 'RWin' },
]
const MOD_LABEL_MAP = {}
MOD_LIST.forEach(function(m) { MOD_LABEL_MAP[m.name] = m.label })
// 兼容旧单边名（万一旧数据用了 ctrl/shift/alt/win）
MOD_LABEL_MAP.ctrl = 'Ctrl'
MOD_LABEL_MAP.shift = 'Shift'
MOD_LABEL_MAP.alt = 'Alt'
MOD_LABEL_MAP.win = 'Win'

// 构造显示用的简短文本（用于预设方格副标题）
function formatShortcutShort(mods, key) {
  const mm = (mods || []).map(function(m) { return MOD_LABEL_MAP[m] || m })
  let kLabel = (key || '').toUpperCase()
  if (KEY_LABELS[key]) kLabel = KEY_LABELS[key]
  return mm.concat([kLabel]).filter(Boolean).join(' + ')
}


// ===== 内置快捷键预设（10 个最常用）=====
const KEY_PRESETS_BUILTIN = [
  { id: 'b1',  label: '全选', mods: ['lctrl'], key: 'a' },
  { id: 'b2',  label: '复制', mods: ['lctrl'], key: 'c' },
  { id: 'b3',  label: '粘贴', mods: ['lctrl'], key: 'v' },
  { id: 'b4',  label: '剪切', mods: ['lctrl'], key: 'x' },
  { id: 'b5',  label: '撤销', mods: ['lctrl'], key: 'z' },
  { id: 'b6',  label: '重做', mods: ['lctrl'], key: 'y' },
  { id: 'b7',  label: '保存', mods: ['lctrl'], key: 's' },
  { id: 'b8',  label: '查找', mods: ['lctrl'], key: 'f' },
  { id: 'b9',  label: '新建', mods: ['lctrl'], key: 'n' },
  { id: 'b10', label: '关闭', mods: ['lctrl'], key: 'w' },
]

// ===== 用户自定义模板（持久化到 storage）=====
const USER_PRESETS_KEY = 'phonekb.key_presets_user'
function loadUserPresets() {
  try {
    const raw = uni.getStorageSync(USER_PRESETS_KEY)
    return Array.isArray(raw) ? raw : []
  } catch (e) { return [] }
}
function saveUserPresets(list) {
  try { uni.setStorageSync(USER_PRESETS_KEY, list || []) } catch (e) {}
}

export default {
  data() { return {
    layoutId: '',
    pageId: '',
    slotR: -1,
    slotC: -1,
    id: '',
    label: '',
    icon: '',
    type: 'shortcut',
    modifiers: [],
    key: '',
    shortcutExpanded: false,
    mouseOp: 'click',
    mouseButton: 'left',
    mouseDelta: 120,
    span: 1,
    textValue: '',
    linkUrl: '',
    selectedApp: null,
    codexAction: 'focus_task',
    codexSlot: 1,
    codexLongPressBind: true,
    readingClipboard: false,
    clipboardPurpose: '',
    saving: false,
    _desktopMessageListener: null,
    _clipboardTimeoutId: null,
    _saveTimeoutId: null,
    _pendingSaveAck: '',
    comboSteps: [],
    comboIntervalMs: 50,
    recording: false,
    recordingBusy: false,
    recordingElapsedTimer: null,
    recordingElapsedMs: 0,
    recordingTimeoutId: null,
    stepCollapsed: [],
    stepPress: null,
    stepDrag: null,
    stepRects: [],
    stepLongPressTimer: null,
    feedback: { vibrate: true, sound: false, toast: true },
    userPresets: [],
    showAddPreset: false,
    newPresetLabel: '',
    newPresetMods: [],
    newPresetKey: '',
    showSaveAsTemplate: false,
    saveTemplateLabel: '',
    _pendingSave: false,
    statusBarHeight: 24,
    jianyingScope: '',
    jianyingSlotIndex: -1,
    jianyingArea: 'shortcuts',

    KEY_LETTERS: KEY_LETTERS,
    KEY_DIGITS: KEY_DIGITS,
    KEY_SPECIAL: KEY_SPECIAL,
    MOD_LIST: MOD_LIST,
    STEP_MODES: STEP_MODES,
    MOUSE_BUTTONS: MOUSE_BUTTONS,
    CODEX_SLOTS: [1, 2, 3, 4, 5, 6],
  } },

  onLoad(opts) {
    try {
      const info = uni.getSystemInfoSync()
      if (info && info.statusBarHeight) this.statusBarHeight = info.statusBarHeight
    } catch (e) {}
    this.userPresets = loadUserPresets()
    if (String(opts.source || '') === 'jianying') {
      this.jianyingScope = normalizeWorkbenchScope(opts.scope)
      this.jianyingSlotIndex = parseInt(opts.slot || '0', 10)
      this.jianyingArea = String(opts.area || '') === 'timeline' ? 'timeline' : 'shortcuts'
      const config = loadWorkbenchConfig(this.jianyingScope)
      const items = this.jianyingArea === 'timeline' ? config.timelineButtons : config.shortcuts
      const item = items[this.jianyingSlotIndex]
      if (item) {
        this.id = item.id || ''
        this._fillFromKey(item, 1)
      }
      this.type = 'shortcut'
      return
    }
    this.layoutId = opts.layout_id || ''
    this.pageId = opts.page_id || ''
    this.slotR = parseInt(opts.r || '-1', 10)
    this.slotC = parseInt(opts.c || '-1', 10)
    this.id = opts.id || ''
    const requestedType = String(opts.type || '')
    if (!this.id && ['shortcut', 'mouse', 'text', 'combo', 'link', 'app', 'codex'].indexOf(requestedType) >= 0) {
      this.type = requestedType
    }
    this._desktopMessageListener = (msg) => this.onDesktopMessage(msg)
    if (typeof WS.onMessage === 'function') WS.onMessage(this._desktopMessageListener)
    const cached = (function() { try { return uni.getStorageSync('phonekb.last_layouts') } catch (e) { return null } })()
    if (cached && this.id) {
      for (const lay of cached.layouts || []) {
        if (lay.id !== this.layoutId) continue
        for (const page of lay.pages || []) {
          if (page.id !== this.pageId) continue
          for (const s of page.slots || []) {
            if (s.key && s.key.id === this.id) {
              this._fillFromKey(s.key, s.span || 1)
              return
            }
          }
        }
      }
    }
  },

  onUnload() {
    if (this._desktopMessageListener && typeof WS.offMessage === 'function') {
      WS.offMessage(this._desktopMessageListener)
    }
    if (this._clipboardTimeoutId) clearTimeout(this._clipboardTimeoutId)
    if (this._saveTimeoutId) clearTimeout(this._saveTimeoutId)
    if (this.recordingElapsedTimer) clearInterval(this.recordingElapsedTimer)
    if (this.recordingTimeoutId) clearTimeout(this.recordingTimeoutId)
    if (this.recording) {
      try { WS.send({ action: 'record_stop' }) } catch (e) {}
    }
    this._clearStepPress()
    this.stepDrag = null
  },

  computed: {
    shortcutPreview() {
      if (this.type !== 'shortcut') return ''
      const parts = []
      const me = this
      ;(me.modifiers || []).forEach(function(m) { parts.push(MOD_LABEL_MAP[m] || m) })
      let keyLabel = (me.key || '').toUpperCase()
      if (KEY_LABELS[me.key]) keyLabel = KEY_LABELS[me.key]
      if (keyLabel) parts.push(keyLabel)
      return parts.join(' + ')
    },
    allPresets() {
      const me = this
      const sig = me._presetSig
      const short = formatShortcutShort
      const builtins = KEY_PRESETS_BUILTIN.map(function(p) {
        return Object.assign({}, p, { sig: sig(p.mods, p.key), short: short(p.mods, p.key), isBuiltin: true })
      })
      const jianying = me.jianyingScope ? JIANYING_SHORTCUT_PRESETS.map(function(p) {
        return Object.assign({}, p, { id: 'jy-' + p.id, sig: sig(p.mods, p.key), short: short(p.mods, p.key), isBuiltin: true })
      }) : []
      const users = (me.userPresets || []).map(function(p) {
        return Object.assign({}, p, { sig: sig(p.mods, p.key), short: short(p.mods, p.key), isBuiltin: false })
      })
      return jianying.concat(builtins, users)
    },
    canSaveNewPreset() {
      const me = this
      return !!(me.newPresetLabel && me.newPresetLabel.length > 0 && (me.newPresetKey || (me.newPresetMods || []).length > 0))
    },
    stepDragGhostStyle() {
      const drag = this.stepDrag
      if (!drag) return 'display:none;'
      return 'left:' + (drag.x - drag.offsetX) + 'px;top:' + (drag.y - drag.offsetY) + 'px;width:' + drag.width + 'px;'
    },
  },

  methods: {
    _fillFromKey(key, span) {
      const type = key.type || 'shortcut'
      const fb = key.feedback || { vibrate: true, sound: false, toast: true }
      const sc = key.shortcut || { modifiers: [], key: '' }
      let textValue = ''
      let comboSteps = []
      let comboIntervalMs = 50
      let linkUrl = ''
      let selectedApp = null
      let mouseOp = 'click'
      let mouseButton = 'left'
      let mouseDelta = 120
      let codexAction = 'focus_task'
      let codexSlot = 1
      let codexLongPressBind = true
      if (type === 'text') textValue = (key.text && key.text.value) || ''
      if (type === 'mouse') {
        mouseOp = (key.mouse && key.mouse.op) || 'click'
        mouseButton = (key.mouse && key.mouse.button) || 'left'
        mouseDelta = Number(key.mouse && key.mouse.delta) || 120
      }
      if (type === 'macro') {
        const savedSteps = ((key.macro && key.macro.steps) || []).filter(function(s) { return s && typeof s === 'object' })
        comboSteps = this._normalizeRecordedSteps(savedSteps)
        const savedInterval = parseInt(key.macro && key.macro.interval_ms, 10)
        comboIntervalMs = Number.isFinite(savedInterval) ? Math.max(0, Math.min(1000, savedInterval)) : 50
      }
      if (type === 'link') linkUrl = (key.link && key.link.url) || ''
      if (type === 'app' && key.app && key.app.id) selectedApp = { id: key.app.id, name: key.app.name || key.label || '已选择的软件' }
      if (type === 'codex' && key.codex) {
        codexAction = ['focus_task', 'approve', 'reject'].indexOf(key.codex.action) >= 0 ? key.codex.action : 'focus_task'
        const savedSlot = parseInt(key.codex.slot, 10)
        codexSlot = savedSlot >= 1 && savedSlot <= 6 ? savedSlot : 1
        codexLongPressBind = key.codex.long_press_action !== ''
      }
      this.label = key.label || ''
      this.icon = key.icon || ''
      this.type = (type === 'macro' ? 'combo' : type)
      this.modifiers = sc.modifiers || []
      this.key = sc.key || ''
      this.mouseOp = mouseOp
      this.mouseButton = mouseButton
      this.mouseDelta = mouseDelta
      this.span = span
      this.textValue = textValue
      this.linkUrl = linkUrl
      this.selectedApp = selectedApp
      this.codexAction = codexAction
      this.codexSlot = codexSlot
      this.codexLongPressBind = codexLongPressBind
      this.comboSteps = comboSteps
      this.comboIntervalMs = comboIntervalMs
      this.stepCollapsed = comboSteps.map(function() { return true })
      this.feedback = fb
    },

    onTypeChange(e) {
      const self = this
      const t = e.currentTarget.dataset.t
      self.type = t
    },
    onLabelInput(e) { this.label = e.detail.value },
    onSpanChange(e) { this.span = parseInt(e.currentTarget.dataset.s, 10) || 1 },
    onTextInput(e) { this.textValue = e.detail.value },
    onMouseOpChange(e) { this.mouseOp = e.currentTarget.dataset.op || 'click' },
    onMouseButtonChange(e) { this.mouseButton = e.currentTarget.dataset.button || 'left' },
    onMouseDeltaChange(e) { this.mouseDelta = parseInt(e.currentTarget.dataset.delta, 10) || 120 },
    onLinkUrlInput(e) { this.linkUrl = e.detail.value },
    onCodexActionChange(e) { this.codexAction = e.currentTarget.dataset.a || 'focus_task' },
    onCodexSlotChange(e) {
      const slot = parseInt(e.currentTarget.dataset.slot, 10)
      if (slot >= 1 && slot <= 6) this.codexSlot = slot
    },
    onCodexLongPressChange(e) { this.codexLongPressBind = !!e.detail.value },
    onReadDesktopClipboard() {
      this._requestDesktopClipboard('app')
    },
    onReadDesktopLink() {
      this._requestDesktopClipboard('link')
    },
    _requestDesktopClipboard(purpose) {
      if (this.readingClipboard) return
      if (!WS.isConnected || !WS.isConnected()) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this.readingClipboard = true
      this.clipboardPurpose = purpose
      const action = purpose === 'link' ? 'read_desktop_clipboard_url' : 'read_desktop_clipboard'
      if (!WS.send({ action: action })) {
        this.readingClipboard = false
        this.clipboardPurpose = ''
        uni.showToast({ title: '读取请求发送失败', icon: 'none' })
        return
      }
      this._clipboardTimeoutId = setTimeout(() => {
        if (!this.readingClipboard) return
        this.readingClipboard = false
        this.clipboardPurpose = ''
        uni.showToast({ title: '电脑端没有回应，请更新并重启桌面端', icon: 'none' })
      }, 6000)
    },
    onDesktopMessage(msg) {
      if (!msg) return
      if (msg.action === 'record_started') {
        if (this.recordingTimeoutId) clearTimeout(this.recordingTimeoutId)
        this.recordingTimeoutId = null
        this.recordingBusy = false
        if (msg.ok) {
          this.recording = true
          this.recordingElapsedMs = 0
          if (this.recordingElapsedTimer) clearInterval(this.recordingElapsedTimer)
          this.recordingElapsedTimer = setInterval(() => { this.recordingElapsedMs += 100 }, 100)
        } else {
          this.recording = false
          uni.showToast({ title: msg.msg || '录制启动失败', icon: 'none' })
        }
        return
      }
      if (msg.action === 'record_stopped') {
        if (this.recordingTimeoutId) clearTimeout(this.recordingTimeoutId)
        this.recordingTimeoutId = null
        this.recordingBusy = false
        this.recording = false
        if (this.recordingElapsedTimer) clearInterval(this.recordingElapsedTimer)
        this.recordingElapsedTimer = null
        if (msg.ok && msg.macro) {
          const recordedSteps = Array.isArray(msg.macro.steps) ? msg.macro.steps : []
          this.comboSteps = this._normalizeRecordedSteps(recordedSteps)
          this.comboIntervalMs = Number.isFinite(Number(msg.macro.interval_ms)) ? Number(msg.macro.interval_ms) : 0
          this.stepCollapsed = this.comboSteps.map(function() { return true })
          uni.showToast({ title: '录制完成，已载入步骤', icon: 'success' })
        } else if (!msg.ok) {
          uni.showToast({ title: msg.msg || '录制停止失败', icon: 'none' })
        }
        return
      }
      if (msg.action === 'error' && this.recordingBusy) {
        if (this.recordingTimeoutId) clearTimeout(this.recordingTimeoutId)
        this.recordingTimeoutId = null
        this.recordingBusy = false
        this.recording = false
        uni.showToast({ title: msg.msg || '电脑端没有响应，请重启桌面端', icon: 'none' })
        return
      }
      if (msg.action === 'test_macro_ack') {
        if (!msg.ok) uni.showToast({ title: msg.msg || '测试失败', icon: 'none' })
        return
      }
      const clipboardReply = this.clipboardPurpose === 'link' ? 'clipboard_url' : 'clipboard_app'
      if (this.readingClipboard && (msg.action === clipboardReply || msg.action === 'error')) {
        const purpose = this.clipboardPurpose
        this.readingClipboard = false
        this.clipboardPurpose = ''
        if (this._clipboardTimeoutId) clearTimeout(this._clipboardTimeoutId)
        this._clipboardTimeoutId = null
        if (purpose === 'link' && msg.ok && msg.url) {
          this.linkUrl = String(msg.url).trim()
          uni.showToast({ title: '网址已填入', icon: 'success' })
        } else if (purpose === 'app' && msg.ok && msg.app && msg.app.id) {
          this.selectedApp = { id: msg.app.id, name: msg.app.name || '已选择的软件' }
          if (!this.label) this.label = this.selectedApp.name
          uni.showToast({ title: '已选择 ' + this.selectedApp.name, icon: 'success' })
        } else {
          uni.showToast({ title: msg.msg || '无法读取电脑复制的路径', icon: 'none' })
        }
      }
      if (!this.saving) return
      if (msg.action === this._pendingSaveAck) {
        this._finishSave(!!msg.ok, msg.msg)
      } else if (msg.action === 'error') {
        this._finishSave(false, msg.msg || '电脑端拒绝保存')
      }
    },
    onToggleMod(e) {
      const mod = e.currentTarget.dataset.mod
      const mods = (this.modifiers || []).slice()
      const idx = mods.indexOf(mod)
      if (idx >= 0) mods.splice(idx, 1); else mods.push(mod)
      this.modifiers = mods
    },
    onClearShortcut() {
      this.modifiers = []
      this.key = ''
    },
    onToggleShortcutExpanded() {
      this.shortcutExpanded = !this.shortcutExpanded
    },
    _presetSig(mods, key) {
      const ms = ((mods || []).slice()).sort().join('+')
      return ms + '|' + (key || '')
    },
    isPresetActive(p) {
      return this._presetSig(this.modifiers, this.key) === (p && p.sig)
    },
    onPickPreset(e) {
      const id = e.currentTarget.dataset.id
      const all = this.allPresets || []
      const p = all.find(function(x) { return x.id === id })
      if (!p) return
      this.modifiers = (p.mods || []).slice()
      this.key = p.key
      this.label = p.label || this.label
    },
    onLongPressPreset(e) {
      const id = e.currentTarget.dataset.id
      const all = this.allPresets || []
      const p = all.find(function(x) { return x.id === id })
      if (!p || p.isBuiltin) return
      const me = this
      uni.showModal({
        title: '删除模板？',
        content: '确认删除 "' + p.label + '"？',
        success: function(res) {
          if (!res.confirm) return
          me.userPresets = (me.userPresets || []).filter(function(x) { return x.id !== id })
          saveUserPresets(me.userPresets)
        }
      })
    },
    onToggleAddPreset() {
      this.showAddPreset = !this.showAddPreset
      if (this.showAddPreset) {
        this.newPresetLabel = ''
        this.newPresetMods = []
        this.newPresetKey = ''
      }
    },
    onNewPresetLabelInput(e) { this.newPresetLabel = e.detail.value },
    onToggleNewPresetMod(e) {
      const mod = e.currentTarget.dataset.mod
      const mods = (this.newPresetMods || []).slice()
      const idx = mods.indexOf(mod)
      if (idx >= 0) mods.splice(idx, 1); else mods.push(mod)
      this.newPresetMods = mods
    },
    onPickNewPresetKey(e) {
      const value = e.currentTarget.dataset.key
      this.newPresetKey = typeof value === 'string' ? value : ''
    },
    onCancelAddPreset() {
      this.showAddPreset = false
      this.newPresetLabel = ''
      this.newPresetMods = []
      this.newPresetKey = ''
    },
    onConfirmAddPreset() {
      if (!this.canSaveNewPreset) return
      const sig = this._presetSig(this.newPresetMods, this.newPresetKey)
      const all = this.allPresets || []
      const exists = all.some(function(x) { return x.sig === sig })
      if (exists) {
        uni.showToast({ title: '已有相同模板', icon: 'none' })
        return
      }
      const p = {
        id: 'u' + Date.now(),
        label: this.newPresetLabel,
        mods: (this.newPresetMods || []).slice(),
        key: this.newPresetKey,
      }
      const list = (this.userPresets || []).concat([p])
      this.userPresets = list
      saveUserPresets(list)
      this.modifiers = p.mods.slice()
      this.key = p.key
      this.label = p.label || this.label
      this.showAddPreset = false
      this.newPresetLabel = ''
      this.newPresetMods = []
      this.newPresetKey = ''
      uni.showToast({ title: '已保存模板', icon: 'success' })
    },
    onSaveTemplateLabelInput(e) { this.saveTemplateLabel = e.detail.value },
    onSaveTemplateCancel() {
      this.showSaveAsTemplate = false
      if (this._pendingSave) { this._pendingSave = false; this._actuallySave() }
    },
    onSaveTemplateConfirm() {
      const label = (this.saveTemplateLabel || '').trim()
      if (!label) { uni.showToast({ title: '请填名称', icon: 'none' }); return }
      const sig = this._presetSig(this.modifiers, this.key)
      const all = this.allPresets || []
      const exists = all.some(function(x) { return x.sig === sig })
      if (exists) {
        this.showSaveAsTemplate = false
        if (this._pendingSave) { this._pendingSave = false; this._actuallySave() }
        return
      }
      const p = {
        id: 'u' + Date.now(),
        label: label,
        mods: (this.modifiers || []).slice(),
        key: this.key,
      }
      const list = (this.userPresets || []).concat([p])
      this.userPresets = list
      saveUserPresets(list)
      this.showSaveAsTemplate = false
      uni.showToast({ title: '已保存模板', icon: 'success' })
      if (this._pendingSave) { this._pendingSave = false; this._actuallySave() }
    },
    onPickKey(e) {
      const value = e.currentTarget.dataset.key
      this.key = typeof value === 'string' ? value : ''
    },

    _stepTypeLabel(t) {
      return ({ key: '快捷键', mouse: '鼠标', text: '文本', wait_ms: '等待', enter: '回车' })[t] || t
    },
    _makeStep(type) {
      if (type === 'key') return { type: 'key', mode: 'tap', modifiers: [], key: 'a' }
      if (type === 'mouse') return { type: 'mouse', op: 'click', button: 'left' }
      if (type === 'text') return { type: 'text', value: '' }
      if (type === 'wait_ms') return { type: 'wait_ms', value: 100 }
      if (type === 'enter') return { type: 'enter' }
      return null
    },
    onAddStep(e) {
      const t = e.currentTarget.dataset.t
      const step = this._makeStep(t)
      if (!step) return
      const steps = (this.comboSteps || []).slice()
      steps.push(step)
      this.comboSteps = steps
      const collapsed = (this.stepCollapsed || []).slice()
      collapsed.push(false)
      this.stepCollapsed = collapsed
    },
    _normalizeRecordedSteps(input) {
      const source = Array.isArray(input) ? input : []
      const output = []
      const tapLimit = 250
      for (let i = 0; i < source.length; i++) {
        const current = source[i]
        const wait = source[i + 1]
        const release = source[i + 2]
        const isKeyDown = current && current.type === 'key' && current.mode === 'down'
        const isMouseDown = current && current.type === 'mouse' && current.op === 'down'
        const waitMs = wait && wait.type === 'wait_ms' ? Math.max(0, Number(wait.value) || 0) : null
        const sameKey = isKeyDown && release && release.type === 'key' && release.mode === 'up'
          && release.key === current.key
          && JSON.stringify(release.modifiers || []) === JSON.stringify(current.modifiers || [])
        const sameMouse = isMouseDown && release && release.type === 'mouse' && release.op === 'up'
          && release.button === current.button
        if ((sameKey || sameMouse) && waitMs !== null && waitMs <= tapLimit) {
          const tap = Object.assign({}, current)
          if (sameKey) tap.mode = 'tap'
          else tap.op = 'click'
          tap.duration_ms = Math.round(waitMs)
          output.push(tap)
          i += 2
          continue
        }
        output.push(current)
      }
      return output
    },
    onInsertStepAfter(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      if (idx < 0 || idx >= this.comboSteps.length) return
      const steps = (this.comboSteps || []).slice()
      steps.splice(idx + 1, 0, this._makeStep('key'))
      this.comboSteps = steps
      const collapsed = (this.stepCollapsed || []).slice()
      collapsed.splice(idx + 1, 0, false)
      this.stepCollapsed = collapsed
    },
    _clearStepPress() {
      if (this.stepLongPressTimer) clearTimeout(this.stepLongPressTimer)
      this.stepLongPressTimer = null
      this.stepPress = null
    },
    _refreshStepRects(done) {
      const self = this
      try {
        uni.createSelectorQuery().in(this).selectAll('.step-row').boundingClientRect(function(rects) {
          self.stepRects = Array.isArray(rects) ? rects : []
          if (typeof done === 'function') done()
        }).exec()
      } catch (e) {
        self.stepRects = []
        if (typeof done === 'function') done()
      }
    },
    onStepDragStart(e) {
      if (this.comboSteps.length < 2) return
      const touch = e && e.touches && e.touches[0]
      const index = parseInt(e.currentTarget.dataset.idx, 10)
      if (!touch || index < 0 || index >= this.comboSteps.length) return
      this._clearStepPress()
      this.stepPress = { index: index, x: touch.clientX, y: touch.clientY }
      this._refreshStepRects()
      const self = this
      this.stepLongPressTimer = setTimeout(function() {
        self.stepLongPressTimer = null
        const press = self.stepPress
        if (!press || press.index !== index) return
        const rect = self.stepRects[index]
        if (!rect) return
        self.stepDrag = {
          index: index,
          step: self.comboSteps[index],
          x: press.x,
          y: press.y,
          offsetX: Math.max(0, Math.min(rect.width, press.x - rect.left)),
          offsetY: Math.max(0, Math.min(rect.height, press.y - rect.top)),
          width: rect.width,
        }
        try { uni.vibrateShort({ type: 'medium' }) } catch (err) {}
      }, 360)
    },
    onStepDragMove(e) {
      const touch = e && e.touches && e.touches[0]
      if (!touch || !this.stepPress) return
      if (!this.stepDrag) {
        const dx = touch.clientX - this.stepPress.x
        const dy = touch.clientY - this.stepPress.y
        if (Math.sqrt(dx * dx + dy * dy) > 10) this._clearStepPress()
        return
      }
      try { e.preventDefault && e.preventDefault() } catch (err) {}
      this.stepDrag = Object.assign({}, this.stepDrag, { x: touch.clientX, y: touch.clientY })
      const rects = this.stepRects || []
      if (!rects.length) return
      let target = rects.length - 1
      for (let i = 0; i < rects.length; i += 1) {
        if (touch.clientY < rects[i].top + rects[i].height / 2) {
          target = i
          break
        }
      }
      const from = this.stepDrag.index
      if (target === from || target < 0 || target >= this.comboSteps.length) return
      const steps = this.comboSteps.slice()
      const moved = steps.splice(from, 1)[0]
      steps.splice(target, 0, moved)
      this.comboSteps = steps
      const collapsed = (this.stepCollapsed || []).slice()
      const movedCollapsed = collapsed.splice(from, 1)[0]
      collapsed.splice(target, 0, !!movedCollapsed)
      this.stepCollapsed = collapsed
      this.stepDrag = Object.assign({}, this.stepDrag, { index: target })
      this.$nextTick(() => this._refreshStepRects())
    },
    onStepDragEnd() {
      this._clearStepPress()
      this.stepDrag = null
      this.stepRects = []
    },
    onRemoveStep(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const steps = (this.comboSteps || []).slice()
      if (idx >= 0 && idx < steps.length) {
        steps.splice(idx, 1)
        this.comboSteps = steps
        const collapsed = (this.stepCollapsed || []).slice()
        collapsed.splice(idx, 1)
        this.stepCollapsed = collapsed
      }
    },
    onToggleStepCollapsed(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      if (idx < 0 || idx >= this.comboSteps.length) return
      const collapsed = (this.stepCollapsed || []).slice()
      collapsed[idx] = !collapsed[idx]
      this.stepCollapsed = collapsed
    },
    onChangeStepType(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const t = e.currentTarget.dataset.t
      const steps = (this.comboSteps || []).slice()
      if (idx >= 0 && idx < steps.length) {
        steps[idx] = this._makeStep(t)
        this.comboSteps = steps
        const collapsed = (this.stepCollapsed || []).slice()
        collapsed[idx] = false
        this.stepCollapsed = collapsed
      }
    },
    onStepToggleMod(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const mod = e.currentTarget.dataset.mod
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'key') return
      const mods = (step.modifiers || []).slice()
      const i = mods.indexOf(mod)
      if (i >= 0) mods.splice(i, 1); else mods.push(mod)
      steps[idx] = Object.assign({}, step, { modifiers: mods })
      this.comboSteps = steps
    },
    onStepPickKey(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const value = e.currentTarget.dataset.key
      const k = typeof value === 'string' ? value : ''
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'key') return
      steps[idx] = Object.assign({}, step, { key: k })
      this.comboSteps = steps
    },
    onStepModeChange(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const mode = e.currentTarget.dataset.mode || 'tap'
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'key' || ['tap', 'down', 'up'].indexOf(mode) < 0) return
      steps[idx] = Object.assign({}, step, { mode: mode })
      this.comboSteps = steps
    },
    onStepMouseOpChange(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const op = e.currentTarget.dataset.op || 'click'
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'mouse') return
      steps[idx] = Object.assign({}, step, { op: op })
      this.comboSteps = steps
    },
    onStepMouseButtonChange(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const button = e.currentTarget.dataset.button || 'left'
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'mouse') return
      steps[idx] = Object.assign({}, step, { button: button })
      this.comboSteps = steps
    },
    onStepMouseDeltaChange(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const delta = parseInt(e.currentTarget.dataset.delta, 10) || 120
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'mouse') return
      steps[idx] = Object.assign({}, step, { delta: delta })
      this.comboSteps = steps
    },
    onStepTextInput(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'text') return
      steps[idx] = Object.assign({}, step, { value: e.detail.value })
      this.comboSteps = steps
    },
    onStepWaitInput(e) {
      const idx = parseInt(e.currentTarget.dataset.idx, 10)
      const steps = (this.comboSteps || []).slice()
      const step = steps[idx]
      if (!step || step.type !== 'wait_ms') return
      const v = Math.max(0, Math.min(60000, parseInt(e.detail.value || '0', 10) || 0))
      steps[idx] = Object.assign({}, step, { value: v })
      this.comboSteps = steps
    },
    onComboIntervalInput(e) {
      const value = parseInt(e.detail.value || '0', 10) || 0
      this.comboIntervalMs = Math.max(0, Math.min(1000, value))
    },
    stepHasMod(step, mod) {
      return !!(step && step.modifiers && step.modifiers.indexOf(mod) >= 0)
    },
    formatStepLabel(step) {
      if (!step) return ''
      if (step.type === 'key') {
        const parts = (step.modifiers || []).map(function(m) { return MOD_LABEL_MAP[m] || m })
        let keyLabel = (step.key || '').toUpperCase()
        if (KEY_LABELS[step.key]) keyLabel = KEY_LABELS[step.key]
        if (keyLabel) parts.push(keyLabel)
        const mode = ({ tap: '点击', down: '按下', up: '松开' })[step.mode || 'tap'] || '点击'
        let duration = ''
        if (step.mode === 'tap' && step.duration_ms !== undefined && step.duration_ms !== null) {
          const ms = Math.max(0, Number(step.duration_ms) || 0)
          duration = '（' + Math.round(ms) + '毫秒）'
        }
        return parts.join('+') + (parts.length ? ' · ' : '') + mode + duration
      }
      if (step.type === 'mouse') {
        if (step.op === 'wheel') return (step.delta || 120) > 0 ? '滚轮向上' : '滚轮向下'
        const label = ({ left: '左键', right: '右键', middle: '中键' })[step.button || 'left'] || '左键'
        const op = ({ click: '点击', down: '按下', up: '松开' })[step.op || 'click']
        const duration = step.op === 'click' && step.duration_ms !== undefined && step.duration_ms !== null ? '（' + Math.round(Math.max(0, Number(step.duration_ms) || 0)) + '毫秒）' : ''
        return label + ' · ' + op + duration
      }
      if (step.type === 'text') return (step.value || '').slice(0, 12)
      if (step.type === 'wait_ms') return (step.value || 0) + 'ms'
      if (step.type === 'enter') return 'Enter'
      return ''
    },
    onToggleFeedback(e) {
      const k = e.currentTarget.dataset.k
      const fb = Object.assign({}, this.feedback)
      fb[k] = !fb[k]
      this.feedback = fb
    },
    onStartRecording() {
      if (this.recording || this.recordingBusy) return
      if (WS.getMode && WS.getMode() === 'ble') {
        uni.showToast({ title: '蓝牙模式不能录制电脑按键，请切换 USB 或 Wi-Fi', icon: 'none' })
        return
      }
      if (!WS.isConnected || !WS.isConnected()) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      this.recordingBusy = true
      if (!WS.send({ action: 'record_start' })) {
        this.recordingBusy = false
        uni.showToast({ title: '录制请求发送失败', icon: 'none' })
        return
      }
      // 先进入录制状态，避免桌面端回执延迟时没有“停止”按钮可点。
      this.recording = true
      this.recordingBusy = false
      this.recordingElapsedMs = 0
      this.recordingTimeoutId = setTimeout(() => {
        if (this.recordingElapsedTimer) return
        this.recordingBusy = false
        this.recording = false
        this.recordingTimeoutId = null
        uni.showToast({ title: '电脑端没有确认开始录制，请重启桌面端', icon: 'none' })
      }, 5000)
    },
    onStopRecording() {
      if (!this.recording || this.recordingBusy) return
      if (this.recordingTimeoutId) { clearTimeout(this.recordingTimeoutId); this.recordingTimeoutId = null }
      this.recordingBusy = true
      if (!WS.send({ action: 'record_stop' })) {
        this.recordingBusy = false
        uni.showToast({ title: '停止录制请求发送失败', icon: 'none' })
        return
      }
      this.recordingTimeoutId = setTimeout(() => {
        if (!this.recordingBusy) return
        this.recordingBusy = false
        this.recording = false
        this.recordingTimeoutId = null
        uni.showToast({ title: '电脑端没有返回录制结果，请重启桌面端', icon: 'none' })
      }, 8000)
    },
    onTestMacro() {
      if (this.recording || !this.comboSteps.length) return
      if (!WS.isConnected || !WS.isConnected()) {
        uni.showToast({ title: '请先连接电脑', icon: 'none' })
        return
      }
      if (!WS.send({ action: 'test_macro', macro: { interval_ms: this.comboIntervalMs, steps: this.comboSteps } })) {
        uni.showToast({ title: '测试请求发送失败', icon: 'none' })
      }
    },

    onSave() {
      if (this.saving) return
      if (!this.label) { uni.showToast({ title: '请填名称', icon: 'none' }); return }
      if (!this.jianyingScope && (!this.layoutId || !this.pageId)) { uni.showToast({ title: '页面信息丢失', icon: 'none' }); return }
      // shortcut 类型：检查是否要保存为模板
      if (this.type === 'shortcut') {
        if (!this.key && (!this.modifiers || this.modifiers.length === 0)) {
          uni.showToast({ title: '请至少设置修饰键或主键', icon: 'none' }); return
        }
        const sig = this._presetSig(this.modifiers, this.key)
        const all = this.allPresets || []
        const exists = all.some(function(x) { return x.sig === sig })
        if (!exists) {
          this.saveTemplateLabel = this.shortcutPreview || ''
          this.showSaveAsTemplate = true
          this._pendingSave = true
          return
        }
      }
      if (this.type === 'mouse' && ['click', 'down', 'up', 'wheel'].indexOf(this.mouseOp) < 0) {
        uni.showToast({ title: '请选择鼠标动作', icon: 'none' }); return
      }
      if (this.type === 'link' && !/^https?:\/\/[^\s/]+/i.test((this.linkUrl || '').trim())) {
        uni.showToast({ title: '请输入 http 或 https 网站地址', icon: 'none' }); return
      }
      if (this.type === 'app' && !(this.selectedApp && this.selectedApp.id)) {
        uni.showToast({ title: '请先读取电脑复制的软件路径', icon: 'none' }); return
      }
      this._actuallySave()
    },
    _actuallySave() {
      if (this.saving) return
      let key
      if (this.type === 'shortcut') {
        if (!this.key && (!this.modifiers || this.modifiers.length === 0)) {
          uni.showToast({ title: '请至少设置修饰键或主键', icon: 'none' }); return
        }
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: this._shortcutLabel(), icon: this.icon,
          type: 'shortcut', feedback: this.feedback,
          shortcut: { modifiers: this.modifiers, key: this.key || '' },
        }
      } else if (this.type === 'text') {
        if (!this.textValue) { uni.showToast({ title: '请输入文本', icon: 'none' }); return }
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: this.textValue.slice(0, 16), icon: this.icon,
          type: 'text', feedback: this.feedback,
          text: { value: this.textValue },
        }
      } else if (this.type === 'mouse') {
        const isWheel = this.mouseOp === 'wheel'
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label,
          sub: isWheel ? (this.mouseDelta > 0 ? '滚轮向上' : '滚轮向下') : (({ left: '左键', right: '右键', middle: '中键' })[this.mouseButton] || '左键') + ' · ' + ({ click: '点击', down: '按下', up: '松开' })[this.mouseOp],
          icon: this.icon,
          type: 'mouse', feedback: this.feedback,
          mouse: isWheel ? { op: 'wheel', delta: this.mouseDelta } : { op: this.mouseOp, button: this.mouseButton, count: 1 },
        }
      } else if (this.type === 'combo') {
        const steps = (this.comboSteps || []).filter(function(s) { return s && typeof s === 'object' })
        if (steps.length === 0) { uni.showToast({ title: '请添加至少一个步骤', icon: 'none' }); return }
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: steps.length + ' 步', icon: this.icon,
          type: 'macro', feedback: this.feedback,
          macro: { interval_ms: this.comboIntervalMs, steps: steps },
        }
      } else if (this.type === 'link') {
        const url = (this.linkUrl || '').trim()
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: this._linkSub(url), icon: this.icon,
          type: 'link', feedback: this.feedback,
          link: { url: url },
        }
      } else if (this.type === 'app') {
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: '已授权软件', icon: this.icon,
          type: 'app', feedback: this.feedback,
          app: { id: this.selectedApp.id, name: this.selectedApp.name || this.label },
        }
      } else if (this.type === 'codex') {
        const actionLabels = { focus_task: '切换任务', approve: '批准操作', reject: '拒绝操作' }
        key = {
          id: this.id || ('key_' + Date.now()),
          label: this.label, sub: 'Codex · ' + (actionLabels[this.codexAction] || '任务操作') + ' ' + this.codexSlot, icon: this.icon,
          type: 'codex', feedback: this.feedback,
          codex: {
            action: this.codexAction,
            slot: this.codexSlot,
            long_press_action: this.codexAction === 'focus_task' && this.codexLongPressBind ? 'bind_current_task' : '',
          },
        }
      } else {
        uni.showToast({ title: '该类型暂未支持', icon: 'none' }); return
      }

      if (this.jianyingScope) {
        this.saving = true
        const config = loadWorkbenchConfig(this.jianyingScope)
        const items = this.jianyingArea === 'timeline' ? config.timelineButtons : config.shortcuts
        const stableKey = Object.assign({}, key, { id: (items[this.jianyingSlotIndex] || {}).id || key.id })
        const nextConfig = this.jianyingArea === 'timeline'
          ? updateTimelineButton(config, this.jianyingSlotIndex, stableKey)
          : updateShortcut(config, this.jianyingSlotIndex, stableKey)
        const savedConfig = saveWorkbenchConfig(this.jianyingScope, nextConfig)
        const savedItems = savedConfig && (this.jianyingArea === 'timeline' ? savedConfig.timelineButtons : savedConfig.shortcuts)
        const savedItem = savedItems && savedItems[this.jianyingSlotIndex]
        const shortcutMatches = savedItem
          && savedItem.label === stableKey.label
          && savedItem.sub === stableKey.sub
          && savedItem.shortcut
          && savedItem.shortcut.key === stableKey.shortcut.key
          && JSON.stringify(savedItem.shortcut.modifiers || []) === JSON.stringify(stableKey.shortcut.modifiers || [])
        if (!shortcutMatches) {
          this.saving = false
          uni.showToast({ title: '保存失败，请重试', icon: 'none' })
          return
        }
        try {
          const channel = typeof this.getOpenerEventChannel === 'function' ? this.getOpenerEventChannel() : null
          if (channel && typeof channel.emit === 'function') channel.emit('saved', { scope: this.jianyingScope, config: savedConfig })
        } catch (e) {}
        try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
        uni.showToast({ title: '已保存', icon: 'success', duration: 450 })
        setTimeout(function() { uni.navigateBack({ delta: 1 }) }, 450)
        return
      }

      if (!WS.isConnected || !WS.isConnected()) {
        uni.showToast({ title: '请先连接电脑再保存', icon: 'none' })
        return
      }
      const isUpdate = !!this.id
      const action = isUpdate ? 'update_slot' : 'add_slot'
      const payload = isUpdate ? {
        action: action,
        layout_id: this.layoutId,
        page_id: this.pageId,
        r: this.slotR, c: this.slotC,
        updates: { key: key, span: this.span },
      } : {
        action: action,
        layout_id: this.layoutId,
        page_id: this.pageId,
        slot: { r: this.slotR, c: this.slotC, span: this.span || 1, key: key },
      }
      this.saving = true
      this._pendingSaveAck = action + '_ack'
      if (!WS.send(payload)) {
        this._finishSave(false, '保存请求发送失败，请检查连接')
        return
      }
      this._saveTimeoutId = setTimeout(() => {
        if (this.saving) this._finishSave(false, '电脑端没有确认保存，请更新并重启桌面端')
      }, 6000)
    },
    _finishSave(ok, message) {
      if (this._saveTimeoutId) clearTimeout(this._saveTimeoutId)
      this._saveTimeoutId = null
      this.saving = false
      this._pendingSaveAck = ''
      if (!ok) {
        uni.showToast({ title: message || '保存失败', icon: 'none' })
        return
      }
      try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
      uni.showToast({ title: '已保存', icon: 'success', duration: 800 })
      setTimeout(function() {
        try {
          if (typeof WS.reloadLayouts === 'function') WS.reloadLayouts()
          else WS.send({ action: 'reload_layouts' })
        } catch (e) {}
      }, 100)
      setTimeout(function() { uni.navigateBack() }, 800)
    },
    onDelete() {
      if (!this.id) { uni.navigateBack(); return }
      const self = this
      uni.showModal({
        title: '删除键位', content: '确认删除？',
        success: function(res) {
          if (res.confirm) {
            WS.send({
              action: 'delete_slot',
              layout_id: self.layoutId,
              page_id: self.pageId,
              r: self.slotR, c: self.slotC,
            })
            try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
            uni.navigateBack()
          }
        },
      })
    },

    _shortcutLabel() {
      const parts = []
      const me = this
      ;(me.modifiers || []).forEach(function(m) { parts.push(MOD_LABEL_MAP[m] || m) })
      let keyLabel = (me.key || '').toUpperCase()
      if (KEY_LABELS[me.key]) keyLabel = KEY_LABELS[me.key]
      if (keyLabel) parts.push(keyLabel)
      return parts.join(' + ')
    },

    _linkSub(url) {
      return url.replace(/^https?:\/\//i, '').replace(/\/$/, '').slice(0, 24)
    },

    hasMod(mods, target) {
      if (!mods) return false
      return mods.indexOf(target) >= 0
    },
    isType(t) { return this.type === t },
    formatKeyLabel(k) {
      if (KEY_LABELS[k]) return KEY_LABELS[k]
      return (k || '').toUpperCase()
    },
  },
}
</script>

<style>
page {
  --bg: #F9FAFB; --primary: #3B82F6; --primary-soft: #DBEAFE;
  --accent: #8B5CF6; --danger: #EF4444;
  --text: #1F2937; --text-mid: #6B7280; --text-light: #9CA3AF; --border: #E5E7EB;
  --radius-md: 12rpx;
  background: var(--bg);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
}
.page { min-height: 100vh; padding: 24rpx; box-sizing: border-box; }
.section { background: white; border-radius: 16rpx; padding: 24rpx; margin-bottom: 20rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.05); }
.row { display: flex; align-items: center; padding: 12rpx 0; border-bottom: 2rpx solid var(--bg); }
.row:last-child { border-bottom: none; }
.label { width: 160rpx; font-size: 30rpx; color: var(--text); font-weight: 500; }
.input {
  flex: 1;
  min-width: 0;
  height: 76rpx;
  padding: 0 16rpx;
  line-height: 76rpx;
  background: var(--bg);
  border-radius: 8rpx;
  font-size: 28rpx;
  color: var(--text);
}
.input-placeholder { color: var(--text-light); font-size: 26rpx; }
.sub-title { font-size: 24rpx; color: var(--text-light); margin-bottom: 12rpx; font-weight: 500; }
.sub-meta { font-size: 22rpx; color: var(--text-light); font-weight: 400; margin-left: 8rpx; }

.seg { display: flex; gap: 8rpx; flex-wrap: wrap; }
.action-type-seg {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
  gap: 8rpx;
}
.seg-btn {
  padding: 12rpx 24rpx; background: var(--bg); color: var(--text-mid);
  border-radius: 999rpx; font-size: 26rpx; border: 2rpx solid transparent;
}
.action-type-seg .seg-btn {
  min-width: 0;
  padding: 12rpx 6rpx;
  text-align: center;
}
.seg-btn.on { background: var(--primary); color: white; }

/* ===== 实时快捷键预览（顶部 + 清除按钮同行） ===== */
.preview-row {
  display: flex; align-items: stretch; gap: 12rpx;
  margin-bottom: 16rpx;
}
.shortcut-preview {
  flex: 1;
  font-family: Consolas, 'SF Mono', monospace;
  font-size: 32rpx; font-weight: 700;
  color: var(--text);
  background: var(--bg);
  padding: 18rpx 20rpx;
  border-radius: var(--radius-md);
  text-align: center;
  letter-spacing: 1rpx;
  min-height: 44rpx;
}
.clear-btn {
  flex: 0 0 auto;
  padding: 0 24rpx;
  background: #FEE2E2;
  color: var(--danger);
  border-radius: var(--radius-md);
  font-size: 26rpx;
  font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.clear-btn-hover { background: #FCA5A5; color: white; }
.collapse-btn {
  flex: 0 0 auto;
  display: flex; align-items: center; justify-content: center;
  border: 2rpx solid var(--border);
  background: var(--bg); color: var(--text-mid);
  font-weight: 700;
}
.shortcut-collapse-btn {
  width: 72rpx;
  border-radius: var(--radius-md);
  font-size: 30rpx;
}

.mod-row { display: flex; gap: 10rpx; flex-wrap: wrap; }
.mod-chip {
  padding: 12rpx 20rpx; background: var(--bg); color: var(--text-mid);
  border-radius: 10rpx; font-size: 24rpx; font-weight: 600;
  border: 2rpx solid var(--border); min-width: 88rpx; text-align: center;
  transition: transform 0.1s, background-color 0.15s;
}
.mod-chip.on { background: var(--primary); color: white; border-color: var(--primary); }
.mod-chip-hover { background: var(--primary-soft); transform: scale(0.95); }
.mod-chip.on.mod-chip-hover { background: var(--primary); }

.key-row { display: flex; flex-wrap: wrap; gap: 10rpx; margin-bottom: 16rpx; }
.key-chip {
  min-width: 72rpx; height: 72rpx; padding: 0 14rpx;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg); border-radius: 10rpx; font-size: 26rpx;
  font-weight: 600; color: var(--text);
  border: 2rpx solid var(--border);
}
.key-chip.wide { min-width: 96rpx; padding: 0 18rpx; font-size: 24rpx; }
.key-chip.modifier-only-chip { min-width: 154rpx; }
.key-chip.on { background: var(--primary); color: white; border-color: var(--primary); }

.text-input {
  width: 100%; min-height: 160rpx; padding: 16rpx; box-sizing: border-box;
  background: var(--bg); border-radius: 8rpx; font-size: 26rpx;
  font-family: -apple-system, 'PingFang SC', sans-serif;
}
.action-input {
  width: 100%;
  box-sizing: border-box;
}
.app-selection {
  min-height: 72rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  background: var(--bg);
  border-radius: 8rpx;
  box-sizing: border-box;
}
.app-selection-name,
.app-selection-empty {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 26rpx;
}
.app-selection-name { color: var(--text); }
.app-selection-empty { color: var(--text-light); }
.app-selection-status {
  margin-left: 12rpx;
  color: #1E8E5A;
  font-size: 21rpx;
  font-weight: 600;
}
.action-read-btn {
  width: 100%;
  margin-top: 16rpx;
  box-sizing: border-box;
}
.text-input.mono { font-family: Consolas, 'SF Mono', monospace; font-size: 22rpx; }
.text-input-ph { color: var(--text-light); font-size: 28rpx; }
.hint { font-size: 22rpx; color: var(--text-light); margin-top: 8rpx; }

.empty-hint {
  font-size: 22rpx; color: var(--text-light);
  background: #FEF3C7; padding: 8rpx 16rpx; border-radius: 8rpx;
  margin: 12rpx 0; text-align: center;
}

/* ===== 组合键步骤列表 ===== */
.step-row {
  position: relative;
  background: linear-gradient(135deg, #FAFBFC 0%, #F4F6FA 100%);
  border: 2rpx solid var(--border);
  border-radius: var(--radius-md);
  padding: 12rpx 16rpx;
  margin-bottom: 12rpx;
}
.macro-interval-row {
  min-height: 84rpx;
  margin-bottom: 18rpx;
  padding: 14rpx 16rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  border: 2rpx solid var(--border);
  border-radius: 12rpx;
  background: var(--bg);
  box-sizing: border-box;
}
.macro-interval-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.macro-interval-title { color: var(--text); font-size: 24rpx; font-weight: 700; }
.macro-interval-desc { color: var(--text-light); font-size: 19rpx; line-height: 1.35; }
.macro-interval-input-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.macro-interval-input {
  width: 104rpx;
  height: 58rpx;
  border: 2rpx solid var(--border);
  border-radius: 10rpx;
  background: white;
  color: var(--text);
  font-size: 24rpx;
  font-weight: 700;
  text-align: center;
}
.macro-interval-unit { color: var(--text-mid); font-size: 21rpx; }
.macro-record-row {
  min-height: 82rpx;
  margin-bottom: 18rpx;
  padding: 14rpx 16rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  border: 2rpx solid var(--border);
  border-radius: 12rpx;
  background: white;
}
.macro-record-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.macro-record-title { color: var(--text); font-size: 24rpx; font-weight: 700; }
.macro-record-desc { color: var(--text-light); font-size: 19rpx; line-height: 1.35; }
.macro-stop-btn, .macro-test-btn { flex-shrink: 0; min-height: 58rpx; padding: 0 16rpx; display: flex; align-items: center; justify-content: center; border-radius: 10rpx; font-size: 21rpx; }
.macro-test-btn { border: 2rpx solid var(--border); background: var(--bg); color: var(--text-mid); }
.step-row.is-step-dragging {
  opacity: 0.28;
  border-color: var(--primary);
}
.step-head {
  display: flex; align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}
.step-num {
  width: 36rpx; height: 36rpx;
  background: var(--primary); color: white;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 22rpx; font-weight: 700;
  flex-shrink: 0;
}
.step-type-tabs {
  display: flex; gap: 6rpx;
  flex: 1; flex-wrap: wrap;
}
.step-type-tab {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: white;
  border: 2rpx solid var(--border);
  color: var(--text-mid);
  font-size: 22rpx;
}
.step-type-tab.on {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
  font-weight: 600;
}
.step-del {
  width: 44rpx; height: 44rpx;
  display: flex; align-items: center; justify-content: center;
  background: #FEE2E2; color: #DC2626;
  border-radius: 50%;
  font-size: 26rpx;
  flex-shrink: 0;
}
.step-type-summary {
  flex: 1;
  color: var(--primary);
  font-size: 22rpx;
  font-weight: 700;
}
.step-collapse-btn {
  width: 44rpx; height: 44rpx;
  border-radius: 10rpx;
  font-size: 25rpx;
}
.step-insert-btn {
  width: 44rpx; height: 44rpx;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 2rpx solid var(--primary);
  border-radius: 10rpx;
  background: var(--primary-soft); color: var(--primary);
  font-size: 28rpx; font-weight: 700;
}
.step-mode-row,
.mouse-action-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10rpx;
  margin: 10rpx 0;
}
.step-mode-label {
  color: var(--text-light);
  font-size: 22rpx;
}
.step-mode-btn,
.mouse-action-btn {
  min-width: 92rpx;
  padding: 10rpx 16rpx;
  border: 2rpx solid var(--border);
  border-radius: 10rpx;
  background: white;
  color: var(--text-mid);
  font-size: 23rpx;
  text-align: center;
}
.step-mode-btn.on,
.mouse-action-btn.on {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}
.step-key-subtitle { margin-top: 12rpx; }
.step-mouse-row { margin-top: 0; }
.step-drag-handle {
  width: 44rpx;
  height: 44rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-light);
  font-size: 28rpx;
  line-height: 1;
  text-align: center;
  touch-action: none;
}
.step-drag-ghost {
  position: fixed;
  box-sizing: border-box;
  padding: 12rpx 16rpx;
  border: 2rpx solid var(--primary);
  border-radius: var(--radius-md);
  background: #FFFFFF;
  box-shadow: 0 18rpx 40rpx rgba(31, 48, 70, 0.22);
  opacity: 0.76;
  pointer-events: none;
  z-index: 1001;
}
.step-drag-ghost-head { margin-bottom: 8rpx; }
.step-drag-ghost-type {
  flex: 1;
  color: var(--primary);
  font-size: 23rpx;
  font-weight: 700;
}
.step-drag-ghost-preview { margin-bottom: 0; }
.step-preview {
  font-family: Consolas, 'SF Mono', monospace;
  font-size: 26rpx; font-weight: 600;
  color: var(--text);
  background: white;
  padding: 10rpx 16rpx;
  border-radius: 8rpx;
  margin-bottom: 10rpx;
}
.wait-row {
  display: flex; align-items: center;
  gap: 12rpx;
}
.wait-input {
  flex: 0 0 200rpx;
  text-align: center;
  font-weight: 600;
}
.wait-unit {
  font-size: 24rpx; color: var(--text-mid);
}
.add-step-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12rpx;
  margin-top: 16rpx;
}
.add-step-btn {
  padding: 18rpx 0;
  background: white;
  border: 2rpx dashed var(--primary);
  border-radius: var(--radius-md);
  color: var(--primary);
  font-size: 26rpx;
  font-weight: 600;
  text-align: center;
}
.add-step-btn:active { background: var(--primary-soft); }
/* ===== 常用快捷键预设 ===== */
.preset-row { display: flex; flex-wrap: wrap; gap: 10rpx; margin-bottom: 16rpx; align-items: center; }
.preset-chip {
  min-width: 140rpx;
  padding: 14rpx 18rpx;
  display: flex; flex-direction: column;
  align-items: center; gap: 4rpx;
  background: var(--primary-soft);
  color: var(--primary);
  border-radius: 12rpx;
  border: 2rpx solid var(--primary-soft);
}
.preset-chip-label { font-size: 26rpx; font-weight: 700; line-height: 1.2; }
.preset-chip-sub { font-size: 20rpx; opacity: 0.85; font-family: Consolas, monospace; line-height: 1.2; }
.preset-chip.on .preset-chip-sub { color: rgba(255,255,255,0.85); opacity: 1; }
.preset-chip.on { background: var(--primary); color: white; border-color: var(--primary); }
.preset-chip-hover { background: var(--primary); color: white; border-color: var(--primary); transform: scale(0.95); }
.preset-chip-add {
  width: 56rpx; height: 56rpx;
  display: flex; align-items: center; justify-content: center;
  background: white;
  color: var(--primary);
  border: 2rpx dashed var(--primary);
  border-radius: 10rpx;
  font-size: 36rpx; font-weight: 700;
  line-height: 1;
}
.preset-chip-add.on { background: #FEE2E2; color: var(--danger); border-color: var(--danger); border-style: solid; }
.preset-chip-add-hover { background: var(--primary-soft); transform: scale(0.95); }
.add-preset-panel {
  background: #FFFFFF;
  border: 2rpx solid var(--border);
  border-radius: var(--radius-md);
  padding: 16rpx;
  margin-top: 16rpx;
  margin-bottom: 16rpx;
  position: relative;
  z-index: 2;
}
.add-preset-actions { display: flex; gap: 12rpx; margin-top: 16rpx; }
.btn-secondary {
  flex: 1; padding: 18rpx 0; text-align: center;
  background: var(--bg); color: var(--text-mid);
  border-radius: 10rpx; font-size: 26rpx; font-weight: 600;
  border: 2rpx solid var(--border);
}
.btn-primary.btn-disabled { background: var(--text-light); opacity: 0.5; }

/* ===== 保存为模板弹窗 ===== */
.modal-mask {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 999;
}
.modal-card {
  width: 80%; max-width: 600rpx;
  background: white; border-radius: 16rpx;
  padding: 32rpx 28rpx;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.15);
}
.modal-title {
  font-size: 32rpx; font-weight: 700;
  color: var(--text); text-align: center;
  margin-bottom: 20rpx;
}
.modal-preview {
  font-family: Consolas, 'SF Mono', monospace;
  font-size: 28rpx; font-weight: 600;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 16rpx 20rpx;
  border-radius: 10rpx;
  text-align: center;
  margin-bottom: 16rpx;
}
.modal-actions { display: flex; gap: 16rpx; margin-top: 24rpx; }
.modal-actions .btn-secondary { flex: 1; }
.modal-actions .btn-primary { flex: 2; }

.footer-actions { display: flex; gap: 16rpx; padding: 16rpx 0; }
.btn-danger {
  flex: 1; padding: 24rpx 0; text-align: center;
  background: #FEE2E2; color: var(--danger);
  border-radius: 12rpx; font-size: 30rpx; font-weight: 600;
}
.btn-primary {
  flex: 2; padding: 24rpx 0; text-align: center;
  background: var(--primary); color: white;
  border-radius: 12rpx; font-size: 30rpx; font-weight: 600;
}
.footer-safe { height: 60rpx; }

/* Fluent editor refresh. These rules are scoped to the key editor so shared
   controls elsewhere keep their established appearance. */
.key-editor-page {
  min-height: 100vh;
  padding: 0 24rpx calc(148rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
  font-family: Roboto, 'Noto Sans CJK SC', 'Microsoft YaHei UI', sans-serif;
}
.step-preview.is-collapsed { margin-bottom: 0; }
.key-editor-page .editor-safe-top { width: 100%; flex-shrink: 0; }
.key-editor-page .editor-header {
  min-height: 86rpx;
  margin: 12rpx 8rpx 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.key-editor-page .editor-eyebrow {
  display: block;
  color: #7890AC;
  font-size: 19rpx;
  font-weight: 650;
  line-height: 1.25;
}
.key-editor-page .editor-title {
  display: block;
  margin-top: 5rpx;
  color: #172033;
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.2;
}
.key-editor-page .editor-status {
  min-width: 76rpx;
  min-height: 38rpx;
  padding: 0 13rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #D8E6F5;
  border-radius: 999rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 18rpx;
  font-weight: 650;
}
.key-editor-page .section {
  margin: 0 8rpx 16rpx;
  padding: 22rpx 24rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 18rpx;
  background: #FFFFFF;
  box-shadow: 0 7rpx 20rpx rgba(47, 78, 113, 0.055);
}
.key-editor-page .section-heading {
  margin-bottom: 12rpx;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16rpx;
}
.key-editor-page .section-title {
  color: #172033;
  font-size: 25rpx;
  font-weight: 700;
  line-height: 1.25;
}
.key-editor-page .section-description {
  color: #8291A3;
  font-size: 18rpx;
  line-height: 1.35;
  text-align: right;
}
.key-editor-page .row {
  min-height: 78rpx;
  padding: 10rpx 0;
  border-bottom: 1rpx solid #EAF0F6;
}
.key-editor-page .row:last-child { border-bottom: 0; }
.key-editor-page .label {
  flex: 0 0 104rpx;
  width: auto;
  color: #53657B;
  font-size: 23rpx;
  font-weight: 650;
}
.key-editor-page .input {
  min-width: 0;
  height: 68rpx;
  padding: 0 17rpx;
  border: 1rpx solid #E0E8F1;
  border-radius: 12rpx;
  background: #F7FAFE;
  color: #172033;
  font-size: 24rpx;
  line-height: 68rpx;
}
.key-editor-page .input-placeholder {
  color: #A4B0BF;
  font-size: 22rpx;
}
.key-editor-page .action-type-row {
  min-height: 0;
  padding: 0;
  border: 0;
}
.key-editor-page .action-type-seg {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10rpx;
}
.key-editor-page .seg-btn {
  min-height: 66rpx;
  padding: 0 14rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  border: 1rpx solid #E0E8F1;
  border-radius: 12rpx;
  background: #F8FAFD;
  color: #52657C;
  font-size: 22rpx;
  font-weight: 650;
  text-align: left;
}
.key-editor-page .action-type-seg .seg-btn {
  min-width: 0;
  padding: 0 14rpx;
  text-align: left;
}
.key-editor-page .seg-icon {
  width: 30rpx;
  height: 30rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 700;
  line-height: 1;
}
.key-editor-page .seg-btn.on {
  border-color: #2F78F6;
  background: #2F78F6;
  color: #FFFFFF;
  box-shadow: 0 5rpx 12rpx rgba(47, 120, 246, 0.2);
}
.key-editor-page .seg-btn.on .seg-icon {
  background: rgba(255, 255, 255, 0.2);
  color: #FFFFFF;
}
.key-editor-page .codex-config-section {
  border: 1rpx solid #DCE8F6;
}
.key-editor-page .codex-action-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9rpx;
  margin-bottom: 20rpx;
}
.key-editor-page .codex-action-btn {
  min-width: 0;
  min-height: 88rpx;
  padding: 12rpx 8rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  border: 1rpx solid #DCE8F6;
  border-radius: 11rpx;
  background: #F6F9FD;
  color: #52657C;
}
.key-editor-page .codex-action-btn.on {
  border-color: #2F78F6;
  background: #2F78F6;
  color: #FFFFFF;
}
.key-editor-page .codex-action-name { font-size: 22rpx; font-weight: 700; }
.key-editor-page .codex-action-desc { font-size: 16rpx; color: #8798AB; }
.key-editor-page .codex-action-btn.on .codex-action-desc { color: rgba(255,255,255,0.78); }
.key-editor-page .codex-slot-title { margin-top: 2rpx; }
.key-editor-page .codex-slot-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 7rpx;
  margin-bottom: 14rpx;
}
.key-editor-page .codex-slot-btn {
  min-width: 0;
  height: 54rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE8F6;
  border-radius: 10rpx;
  background: #F6F9FD;
  color: #52657C;
  font-size: 21rpx;
  font-weight: 700;
}
.key-editor-page .codex-slot-btn.on {
  border-color: #2F78F6;
  background: #EAF3FF;
  color: #2468B5;
}
.key-editor-page .codex-long-row {
  min-height: 78rpx;
  margin: 2rpx 0 12rpx;
  padding: 11rpx 0;
  border-top: 1rpx solid #E8EEF5;
  border-bottom: 1rpx solid #E8EEF5;
}
.key-editor-page .codex-long-copy {
  min-width: 0;
  flex: 1;
  padding-right: 14rpx;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.key-editor-page .codex-long-title { color: #334A63; font-size: 21rpx; font-weight: 700; }
.key-editor-page .codex-long-desc { color: #8798AB; font-size: 17rpx; line-height: 1.35; }
.key-editor-page .sub-title {
  margin: 0 0 11rpx;
  color: #5B6D83;
  font-size: 21rpx;
  font-weight: 650;
  line-height: 1.35;
}
.key-editor-page .sub-meta {
  color: #91A0B2;
  font-size: 18rpx;
}
.key-editor-page .preview-row {
  min-height: 74rpx;
  margin-bottom: 18rpx;
  gap: 10rpx;
}
.key-editor-page .shortcut-preview {
  min-height: 74rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE8F6;
  border-radius: 13rpx;
  background: #F2F7FD;
  color: #2B4C70;
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 23rpx;
  font-weight: 650;
  letter-spacing: 0;
}
.key-editor-page .clear-btn {
  min-width: 78rpx;
  padding: 0 14rpx;
  border: 1rpx solid #F1D6D8;
  border-radius: 12rpx;
  background: #FDEFF0;
  color: #C4474D;
  font-size: 20rpx;
  font-weight: 650;
}
.key-editor-page .clear-btn-hover { background: #FBE1E3; color: #B43C43; }
.key-editor-page .shortcut-collapse-btn {
  width: 64rpx;
  border: 1rpx solid #DCE8F6;
  border-radius: 12rpx;
  background: #F2F7FD;
  color: #47729F;
  font-size: 26rpx;
}
.key-editor-page .preset-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8rpx;
  margin: 0 0 17rpx;
}
.key-editor-page .preset-chip {
  min-width: 0;
  min-height: 74rpx;
  padding: 10rpx 6rpx;
  gap: 3rpx;
  border: 1rpx solid #DCE8F6;
  border-radius: 11rpx;
  background: #F2F7FD;
  color: #3773B5;
}
.key-editor-page .preset-chip-label { font-size: 21rpx; font-weight: 650; }
.key-editor-page .preset-chip-sub { font-size: 16rpx; color: #6D94C0; }
.key-editor-page .preset-chip.on { border-color: #2F78F6; background: #2F78F6; color: #FFFFFF; }
.key-editor-page .preset-chip.on .preset-chip-sub { color: rgba(255,255,255,0.8); }
.key-editor-page .preset-chip-hover { background: #EAF3FF; color: #2F78F6; transform: none; }
.key-editor-page .preset-chip-add {
  width: auto;
  min-height: 74rpx;
  border: 1rpx dashed #73A5E5;
  border-radius: 11rpx;
  background: #FBFDFF;
  color: #2F78F6;
  font-size: 30rpx;
}
.key-editor-page .preset-chip-add.on { border-color: #D96B70; background: #FDEFF0; color: #C4474D; }
.key-editor-page .add-preset-panel {
  margin: 0 0 18rpx;
  padding: 16rpx;
  border: 1rpx solid #DDE7F2;
  border-radius: 14rpx;
  background: #F8FBFE;
}
.key-editor-page .mod-row,
.key-editor-page .key-row { gap: 8rpx; }
.key-editor-page .mod-row { margin-bottom: 16rpx; }
.key-editor-page .mod-chip {
  min-width: 0;
  min-height: 52rpx;
  padding: 0 15rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #E0E7EF;
  border-radius: 10rpx;
  background: #F9FBFD;
  color: #5A6879;
  font-size: 20rpx;
  font-weight: 600;
}
.key-editor-page .mod-chip.on { border-color: #2F78F6; background: #EAF3FF; color: #2F78F6; }
.key-editor-page .mod-chip-hover { background: #F1F6FC; transform: none; }
.key-editor-page .mod-chip.on.mod-chip-hover { background: #EAF3FF; }
.key-editor-page .key-row { margin-bottom: 18rpx; }
.key-editor-page .key-chip {
  min-width: 58rpx;
  height: 58rpx;
  padding: 0 10rpx;
  border: 1rpx solid #E0E7EF;
  border-radius: 9rpx;
  background: #FBFCFE;
  color: #344456;
  font-size: 22rpx;
  font-weight: 600;
}
.key-editor-page .key-chip.wide { min-width: 80rpx; padding: 0 12rpx; font-size: 19rpx; }
.key-editor-page .key-chip.modifier-only-chip { min-width: 126rpx; }
.key-editor-page .key-chip.on { border-color: #2F78F6; background: #2F78F6; color: #FFFFFF; }
.key-editor-page .text-input {
  min-height: 142rpx;
  padding: 16rpx;
  border: 1rpx solid #E0E8F1;
  border-radius: 12rpx;
  background: #F7FAFE;
  color: #172033;
  font-size: 23rpx;
  line-height: 1.5;
}
.key-editor-page .text-input-ph { color: #A4B0BF; font-size: 22rpx; }
.key-editor-page .hint { margin-top: 9rpx; color: #8291A3; font-size: 19rpx; line-height: 1.45; }
.key-editor-page .action-input { width: 100%; }
.key-editor-page .app-selection {
  min-height: 68rpx;
  border: 1rpx solid #E0E8F1;
  border-radius: 12rpx;
  background: #F7FAFE;
}
.key-editor-page .app-selection-name,
.key-editor-page .app-selection-empty { font-size: 23rpx; }
.key-editor-page .app-selection-status {
  padding: 4rpx 8rpx;
  border-radius: 7rpx;
  background: #EAF8EF;
  color: #248954;
  font-size: 17rpx;
}
.key-editor-page .action-read-btn { min-height: 64rpx; margin-top: 12rpx; }
.key-editor-page .empty-hint {
  margin: 0 0 14rpx;
  padding: 20rpx 16rpx;
  border: 1rpx dashed #C9D8E8;
  border-radius: 12rpx;
  background: #F8FBFE;
  color: #8291A3;
  font-size: 20rpx;
}
.key-editor-page .macro-interval-row {
  min-height: 78rpx;
  margin-bottom: 17rpx;
  padding: 13rpx 14rpx;
  border: 1rpx solid #DCE8F6;
  border-radius: 12rpx;
  background: #F2F7FD;
}
.key-editor-page .macro-interval-title { color: #2B4C70; font-size: 21rpx; }
.key-editor-page .macro-interval-desc { color: #8291A3; font-size: 17rpx; }
.key-editor-page .macro-interval-input {
  width: 92rpx;
  height: 54rpx;
  border: 1rpx solid #C9D8E8;
  border-radius: 9rpx;
  background: #FFFFFF;
  color: #2F78F6;
  font-size: 22rpx;
}
.key-editor-page .macro-interval-unit { color: #687B91; font-size: 18rpx; }
.key-editor-page .macro-record-row {
  min-height: 76rpx;
  margin-bottom: 17rpx;
  padding: 12rpx 14rpx;
  border: 1rpx solid #DCE8F6;
  border-radius: 12rpx;
  background: #FFFFFF;
}
.key-editor-page .macro-record-title { color: #2B4C70; font-size: 20rpx; }
.key-editor-page .macro-record-desc { color: #8291A3; font-size: 16rpx; }
.key-editor-page .macro-stop-btn,
.key-editor-page .macro-test-btn {
  min-height: 52rpx;
  padding: 0 13rpx;
  border-radius: 9rpx;
  font-size: 19rpx;
}
.key-editor-page .macro-test-btn { border: 1rpx solid #DCE6F1; background: #F4F7FB; color: #5B6D83; }
.key-editor-page .step-row {
  margin-bottom: 12rpx;
  padding: 15rpx;
  border: 1rpx solid #DDE7F2;
  border-radius: 14rpx;
  background: #F9FBFE;
}
.key-editor-page .step-head { gap: 10rpx; margin-bottom: 10rpx; }
.key-editor-page .step-num {
  width: 34rpx;
  height: 34rpx;
  border-radius: 9rpx;
  background: #2F78F6;
  font-size: 18rpx;
}
.key-editor-page .step-type-tabs { gap: 6rpx; }
.key-editor-page .step-type-tab {
  padding: 7rpx 10rpx;
  border: 1rpx solid #DDE6F0;
  border-radius: 8rpx;
  background: #FFFFFF;
  color: #63758C;
  font-size: 18rpx;
}
.key-editor-page .step-type-tab.on { border-color: #2F78F6; background: #EAF3FF; color: #2F78F6; }
.key-editor-page .step-type-summary { color: #2F78F6; font-size: 19rpx; }
.key-editor-page .step-collapse-btn {
  width: 38rpx;
  height: 38rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 10rpx;
  background: #F2F7FD;
  color: #47729F;
  font-size: 21rpx;
}
.key-editor-page .step-insert-btn {
  width: 38rpx;
  height: 38rpx;
  border: 1rpx solid #8BB5EA;
  border-radius: 10rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 24rpx;
}
.key-editor-page .step-drag-handle {
  width: 38rpx;
  height: 38rpx;
}
.key-editor-page .step-del {
  width: 38rpx;
  height: 38rpx;
  border-radius: 10rpx;
  background: #FDEFF0;
  color: #C4474D;
  font-size: 20rpx;
}
.key-editor-page .step-preview {
  padding: 11rpx 13rpx;
  border: 1rpx solid #E0E8F1;
  border-radius: 10rpx;
  background: #FFFFFF;
  color: #37506D;
  font-size: 21rpx;
}
.key-editor-page .wait-row { gap: 10rpx; }
.key-editor-page .wait-input { flex-basis: 160rpx; text-align: center; }
.key-editor-page .wait-unit { color: #74869B; font-size: 20rpx; }
.key-editor-page .add-step-row { gap: 8rpx; margin-top: 12rpx; }
.key-editor-page .add-step-btn {
  padding: 15rpx 4rpx;
  border: 1rpx dashed #76A7E4;
  border-radius: 10rpx;
  background: #FBFDFF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 650;
}
.key-editor-page .add-step-btn:active { background: #EAF3FF; }
.key-editor-page .add-preset-actions { gap: 10rpx; margin-top: 14rpx; }
.key-editor-page .btn-secondary,
.key-editor-page .btn-primary {
  min-height: 62rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  font-size: 22rpx;
  font-weight: 650;
}
.key-editor-page .btn-secondary {
  border: 1rpx solid #DCE6F1;
  background: #F4F7FB;
  color: #5B6D83;
}
.key-editor-page .btn-primary {
  border: 1rpx solid #2F78F6;
  background: #2F78F6;
  color: #FFFFFF;
}
.key-editor-page .btn-primary.btn-disabled { border-color: #B7C7D9; background: #B7C7D9; opacity: 1; }
.key-editor-page .footer-actions {
  position: sticky;
  bottom: 0;
  z-index: 10;
  margin: 0 -24rpx;
  padding: 16rpx 32rpx calc(16rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid rgba(220,230,241,0.9);
  background: rgba(244,248,253,0.96);
  backdrop-filter: blur(16rpx);
  -webkit-backdrop-filter: blur(16rpx);
}
.key-editor-page .footer-actions .btn-primary,
.key-editor-page .footer-actions .btn-danger { min-height: 78rpx; }
.key-editor-page .footer-safe { height: 0; }
.key-editor-page .btn-danger {
  border: 1rpx solid #F2D4D6;
  border-radius: 13rpx;
  background: #FFF5F5;
  color: #C4474D;
  font-size: 23rpx;
  font-weight: 650;
}

.modal-mask { background: rgba(31, 48, 70, 0.28); backdrop-filter: blur(10rpx); -webkit-backdrop-filter: blur(10rpx); }
.modal-card {
  width: calc(100% - 72rpx);
  max-width: 630rpx;
  padding: 26rpx 24rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 20rpx;
  background: #FFFFFF;
  box-shadow: 0 24rpx 64rpx rgba(36, 59, 88, 0.2);
}
.modal-title { color: #172033; font-size: 27rpx; line-height: 1.3; }
.modal-preview { border: 1rpx solid #DCE8F6; border-radius: 12rpx; background: #F2F7FD; color: #2F78F6; font-size: 22rpx; }
.modal-card .row { min-height: 76rpx; border-bottom: 0; }
.modal-card .label { flex: 0 0 90rpx; color: #53657B; font-size: 22rpx; font-weight: 650; }
.modal-card .input { height: 66rpx; border: 1rpx solid #E0E8F1; border-radius: 12rpx; background: #F7FAFE; font-size: 23rpx; line-height: 66rpx; }
.modal-actions { gap: 10rpx; margin-top: 20rpx; }
.modal-actions .btn-secondary,
.modal-actions .btn-primary { min-height: 62rpx; border-radius: 12rpx; font-size: 22rpx; font-weight: 650; }
.modal-actions .btn-secondary { border: 1rpx solid #DCE6F1; background: #F4F7FB; color: #5B6D83; }
.modal-actions .btn-primary { border: 1rpx solid #2F78F6; background: #2F78F6; color: #FFFFFF; }
</style>
