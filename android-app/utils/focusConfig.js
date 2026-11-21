/**
 * focusConfig.js - 专注模式配置管理
 *
 * 数据存储(全部 uni storage):
 *   phonekb.focus.config            - 上次使用的配置(模式/时长/白名单/严格模式)
 *   phonekb.focus.history           - 历史记录数组(最多 50 条)
 *   phonekb.focus.emergency_count   - 本周已用紧急退出次数
 *   phonekb.focus.week_id           - 当前周编号(YYYY-Www)
 *
 * 模式:
 *   count-up        正计时(到目标时长自动结束,不强制锁手机)
 *   count-down      倒计时(到 0 自动结束,不强制锁手机)
 *   strict-lock     倒计时 + 强制锁手机 + 白名单拦截(严格模式)
 *
 * 紧急退出:
 *   严格模式:本周 2 次额度,用完即不可中途退出
 *   宽松模式:不计入额度,随时退出
 *
 * 注意:严格模式下的"强制锁手机"目前仅前端层面(MVP);
 *      真正的系统级拦截需要后续接入 Android AccessibilityService 原生插件
 */

const CONFIG_KEY    = 'phonekb.focus.config'
const HISTORY_KEY   = 'phonekb.focus.history'
const EMERGENCY_KEY = 'phonekb.focus.emergency_count'
const WEEK_KEY      = 'phonekb.focus.week_id'
const MAX_HISTORY   = 50
const WEEKLY_QUOTA  = 2

// 预置白名单 App 列表(MVP 用,等原生插件接入后改为"已安装应用")
// icon 用 emoji,后续可换成 PNG
export const PRESET_WHITELIST = [
  { id: 'wechat',     name: '微信',     icon: '💬', packageName: 'com.tencent.mm' },
  { id: 'qq',         name: 'QQ',       icon: '🐧', packageName: 'com.tencent.mobileqq' },
  { id: 'tel',        name: '电话',     icon: '📞', packageName: 'com.android.contacts' },
  { id: 'sms',        name: '短信',     icon: '✉️', packageName: 'com.android.mms' },
  { id: 'camera',     name: '相机',     icon: '📷', packageName: 'com.android.camera' },
  { id: 'alarm',      name: '闹钟',     icon: '⏰', packageName: 'com.android.deskclock' },
  { id: 'calendar',   name: '日历',     icon: '📅', packageName: 'com.android.calendar' },
  { id: 'maps',       name: '地图',     icon: '🗺',  packageName: 'com.google.android.apps.maps' },
  { id: 'calculator', name: '计算器',   icon: '🧮', packageName: 'com.android.calculator2' },
  { id: 'chrome',     name: '浏览器',   icon: '🌐', packageName: 'com.android.chrome' },
]

// ===== ISO 周编号 =====
//   ISO 周定义:
//     1) 一周从周一开始,周日是一周的最后一天
//     2) 一年的第一周(W01)是包含该年第一个星期四的那一周
//        (等价说法:W01 一定包含 1 月 4 日)
//     3) 一个日期所属的 ISO 周年份 = 该日期所在 ISO 周的星期四所在的日历年
//
//   算法:
//     - 把任意日期推到"本周的周四",周四所在年份 = ISO 周年份
//     - W01 的周四 = 包含 1 月 4 日的那一周的周四
//       周一 = 1 月 4 日 - (6 - jan4DayNr) 天
//       周四 = 周一 + 3 = 1 月 4 日 + jan4DayNr - 3 天
export function getCurrentWeekId(now) {
  const d = now || new Date()
  const date = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const dayNr = (date.getDay() + 6) % 7  // 周一=0 ... 周日=6
  // 把 date 推到本周的周四
  date.setDate(date.getDate() - dayNr + 3)
  const thursdayYear = date.getFullYear()
  // W01 的周四
  const jan4 = new Date(thursdayYear, 0, 4)
  const jan4DayNr = (jan4.getDay() + 6) % 7
  // 包含 1 月 4 日的 ISO 周的周四 = 1 月 4 日 - jan4DayNr + 3
  // (先把 jan4 推到它所在 ISO 周的周一,再加 3 天到周四)
  jan4.setDate(jan4.getDate() - jan4DayNr + 3)
  const diffWeeks = (date.valueOf() - jan4.valueOf()) / 604800000
  // 用 Math.round 避免浮点边界;理论上 diffWeeks 永远是整数
  const week = 1 + Math.round(diffWeeks)
  return thursdayYear + '-W' + String(week).padStart(2, '0')
}

// ===== 默认配置 =====
export function getDefaultConfig() {
  return {
    mode: 'strict-lock',          // 'count-up' | 'count-down' | 'strict-lock'
    durationSec: 25 * 60,         // 默认 25 分钟
    strictMode: true,             // 仅 strict-lock 下有效:紧急退出额度
    whitelistIds: ['wechat', 'tel'], // 默认白名单(预置 id 列表,自定义项走 customPackages)
    customPackages: [],           // 用户手动输入的包名
  }
}

// ===== storage 辅助 =====
function readJSON(key, fallback) {
  try {
    const v = uni.getStorageSync(key)
    if (v === '' || v === null || v === undefined) return fallback
    return v
  } catch (e) {
    return fallback
  }
}

function writeJSON(key, val) {
  try {
    uni.setStorageSync(key, val)
    return true
  } catch (e) {
    console.warn('[focusConfig] write failed:', key, e)
    return false
  }
}

export function loadConfig() {
  const stored = readJSON(CONFIG_KEY, null)
  if (!stored || typeof stored !== 'object') return getDefaultConfig()
  const def = getDefaultConfig()
  return Object.assign({}, def, stored, {
    whitelistIds: Array.isArray(stored.whitelistIds) ? stored.whitelistIds : def.whitelistIds,
    customPackages: Array.isArray(stored.customPackages) ? stored.customPackages : [],
  })
}

export function saveConfig(cfg) {
  return writeJSON(CONFIG_KEY, cfg || getDefaultConfig())
}

// ===== history =====
export function loadHistory() {
  const v = readJSON(HISTORY_KEY, [])
  return Array.isArray(v) ? v : []
}

export function addHistory(entry) {
  const list = loadHistory()
  list.unshift(entry)
  if (list.length > MAX_HISTORY) list.length = MAX_HISTORY
  writeJSON(HISTORY_KEY, list)
  return list
}

export function clearHistory() {
  return writeJSON(HISTORY_KEY, [])
}

// ===== 紧急退出额度(按周重置) =====
export function getEmergencyState() {
  const currentWeek = getCurrentWeekId()
  const storedWeek = readJSON(WEEK_KEY, '')
  let count = 0
  if (storedWeek === currentWeek) {
    count = Number(readJSON(EMERGENCY_KEY, 0)) || 0
  } else {
    writeJSON(WEEK_KEY, currentWeek)
    writeJSON(EMERGENCY_KEY, 0)
  }
  return {
    weekId: currentWeek,
    used: count,
    quota: WEEKLY_QUOTA,
    remaining: Math.max(0, WEEKLY_QUOTA - count),
  }
}

export function consumeEmergency() {
  const st = getEmergencyState()
  if (st.remaining <= 0) return null
  const next = st.used + 1
  writeJSON(EMERGENCY_KEY, next)
  return {
    weekId: st.weekId,
    used: next,
    quota: WEEKLY_QUOTA,
    remaining: Math.max(0, WEEKLY_QUOTA - next),
  }
}

// ===== 工具:合并预置 + 自定义,得到运行时白名单包名数组 =====
export function getWhitelistPackageNames(cfg) {
  if (!cfg) return []
  const out = []
  const ids = Array.isArray(cfg.whitelistIds) ? cfg.whitelistIds : []
  ids.forEach(function (id) {
    const preset = PRESET_WHITELIST.find(function (p) { return p.id === id })
    if (preset && preset.packageName) out.push(preset.packageName)
  })
  const customs = Array.isArray(cfg.customPackages) ? cfg.customPackages : []
  customs.forEach(function (pkg) {
    if (pkg && out.indexOf(pkg) < 0) out.push(pkg)
  })
  return out
}

export function getWhitelistEntries(cfg) {
  if (!cfg) return []
  const out = []
  const ids = Array.isArray(cfg.whitelistIds) ? cfg.whitelistIds : []
  ids.forEach(function (id) {
    const preset = PRESET_WHITELIST.find(function (p) { return p.id === id })
    if (preset) out.push(Object.assign({}, preset))
  })
  const customs = Array.isArray(cfg.customPackages) ? cfg.customPackages : []
  customs.forEach(function (pkg) {
    out.push({ id: 'custom:' + pkg, name: pkg, icon: '📦', packageName: pkg })
  })
  return out
}

// ===== 模式描述 =====
export const MODE_OPTIONS = [
  { key: 'count-up',    label: '正计时', desc: '从 0 开始累计,达到目标自动结束', strictApplicable: false },
  { key: 'count-down',  label: '倒计时', desc: '到 0 自动结束,不限制手机使用',     strictApplicable: false },
  { key: 'strict-lock', label: '严格锁机', desc: '倒计时 + 强制锁手机 + 白名单',     strictApplicable: true  },
]

export function getModeMeta(key) {
  return MODE_OPTIONS.find(function (m) { return m.key === key }) || MODE_OPTIONS[2]
}
