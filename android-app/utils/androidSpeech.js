// Android system SpeechRecognizer adapter. This bypasses the DCloud cloud ASR
// credentials used by plus.speech and delegates recognition to the phone OS.

let recognizer = null
let listener = null
let callbacks = null
let latestPartial = ''
let finished = false
let stopTimer = null

const RESULTS_KEY = 'results_recognition'
const ERROR_MESSAGES = {
  1: '网络超时',
  2: '网络错误',
  3: '录音错误',
  4: '语音服务端错误',
  5: '语音识别客户端错误',
  6: '没有检测到语音',
  7: '没有识别到匹配文字',
  8: '语音识别器正忙',
  9: '语音识别权限不足',
  10: '请求过多',
  11: '语音服务繁忙',
  12: '手机不支持当前语言',
  13: '当前语言暂不可用',
}

function clearStopTimer() {
  if (stopTimer) {
    clearTimeout(stopTimer)
    stopTimer = null
  }
}

function destroyRecognizer() {
  clearStopTimer()
  if (recognizer) {
    try { plus.android.invoke(recognizer, 'destroy') } catch (e) {}
  }
  recognizer = null
  listener = null
  callbacks = null
  latestPartial = ''
}

function firstResult(bundle) {
  if (!bundle) return ''
  try {
    const matches = plus.android.invoke(bundle, 'getStringArrayList', RESULTS_KEY)
    if (!matches) return ''
    const size = Number(plus.android.invoke(matches, 'size') || 0)
    if (size < 1) return ''
    return String(plus.android.invoke(matches, 'get', 0) || '').trim()
  } catch (e) {
    return ''
  }
}

function finishWithText(text) {
  if (finished) return
  const value = String(text || '').trim()
  if (!value) return
  finished = true
  const done = callbacks && callbacks.onResult
  destroyRecognizer()
  if (done) done(value)
}

function finishWithError(code, message) {
  if (finished) return
  finished = true
  const failed = callbacks && callbacks.onError
  destroyRecognizer()
  if (failed) failed({
    code: 'ANDROID_ASR_' + String(code),
    message: message || ERROR_MESSAGES[code] || ('Android 语音识别错误 ' + String(code)),
  })
}

function start(options) {
  options = options || {}
  if (typeof plus === 'undefined' || !plus.android) {
    throw new Error('当前环境不是 Android App')
  }

  destroyRecognizer()
  callbacks = options
  latestPartial = ''
  finished = false

  const activity = plus.android.runtimeMainActivity()
  const SpeechRecognizer = plus.android.importClass('android.speech.SpeechRecognizer')
  const available = !!plus.android.invoke(SpeechRecognizer, 'isRecognitionAvailable', activity)
  if (!available) {
    callbacks = null
    throw new Error('手机没有启用系统语音识别服务')
  }

  listener = plus.android.implements('android.speech.RecognitionListener', {
    onReadyForSpeech: function() {
      if (callbacks && callbacks.onReady) callbacks.onReady()
    },
    onBeginningOfSpeech: function() {},
    onRmsChanged: function() {},
    onBufferReceived: function() {},
    onEndOfSpeech: function() {},
    onError: function(code) {
      const numericCode = Number(code)
      if (latestPartial && (numericCode === 6 || numericCode === 7)) {
        finishWithText(latestPartial)
        return
      }
      finishWithError(numericCode, ERROR_MESSAGES[numericCode])
    },
    onResults: function(bundle) {
      const value = firstResult(bundle) || latestPartial
      if (value) finishWithText(value)
      else finishWithError(7, ERROR_MESSAGES[7])
    },
    onPartialResults: function(bundle) {
      const value = firstResult(bundle)
      if (value) latestPartial = value
    },
    onEvent: function() {},
  })

  recognizer = plus.android.invoke(SpeechRecognizer, 'createSpeechRecognizer', activity)
  if (!recognizer) {
    destroyRecognizer()
    throw new Error('无法创建 Android 系统语音识别器')
  }
  plus.android.invoke(recognizer, 'setRecognitionListener', listener)

  const Intent = plus.android.importClass('android.content.Intent')
  const intent = new Intent('android.speech.action.RECOGNIZE_SPEECH')
  plus.android.invoke(intent, 'putExtra', 'android.speech.extra.LANGUAGE_MODEL', 'free_form')
  plus.android.invoke(intent, 'putExtra', 'android.speech.extra.LANGUAGE', options.lang || 'zh-CN')
  plus.android.invoke(intent, 'putExtra', 'android.speech.extra.PARTIAL_RESULTS', true)
  plus.android.invoke(intent, 'putExtra', 'android.speech.extra.MAX_RESULTS', 3)
  plus.android.invoke(recognizer, 'startListening', intent)
}

function stop() {
  if (!recognizer || finished) return
  try { plus.android.invoke(recognizer, 'stopListening') } catch (e) {
    finishWithError('STOP_FAILED', String(e && e.message ? e.message : e))
    return
  }
  clearStopTimer()
  stopTimer = setTimeout(function() {
    if (latestPartial) finishWithText(latestPartial)
    else finishWithError('NO_RESULT', '松开按键后，手机没有返回识别文字')
  }, 1800)
}

function cancel() {
  if (recognizer) {
    try { plus.android.invoke(recognizer, 'cancel') } catch (e) {}
  }
  finished = true
  destroyRecognizer()
}

export default { start, stop, cancel }
