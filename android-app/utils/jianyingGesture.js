export const SENSITIVITY_THRESHOLDS = {
  stable: { swipe: 14, pinch: 12 },
  medium: { swipe: 9, pinch: 7 },
  sensitive: { swipe: 6, pinch: 4 },
}

export function clampGestureMultiplier(value, fallback = 1, min = 0.5, max = 3) {
  const parsed = Number(value)
  const normalized = Number.isFinite(parsed) ? parsed : Number(fallback) || 1
  return Math.max(min, Math.min(max, normalized))
}

export function touchCoordinate(touch, axis) {
  const suffix = axis === 'y' ? 'Y' : 'X'
  const keys = ['client' + suffix, 'page' + suffix, axis === 'y' ? 'y' : 'x']
  for (let index = 0; index < keys.length; index++) {
    const value = Number(touch && touch[keys[index]])
    if (Number.isFinite(value)) return value
  }
  return 0
}

export function touchDistance(touches) {
  if (!touches || touches.length < 2) return 0
  const dx = touchCoordinate(touches[1], 'x') - touchCoordinate(touches[0], 'x')
  const dy = touchCoordinate(touches[1], 'y') - touchCoordinate(touches[0], 'y')
  return Math.sqrt(dx * dx + dy * dy)
}

export function thresholdFor(sensitivity, gesture) {
  const values = SENSITIVITY_THRESHOLDS[sensitivity] || SENSITIVITY_THRESHOLDS.medium
  return gesture === 'pinch' ? values.pinch : values.swipe
}

export function swipeMultiplierForScale(rulerScale, baseMultiplier = 1, min = 0.35, max = 3.2) {
  const scale = Math.max(0.1, Number(rulerScale) || 1)
  const base = clampGestureMultiplier(baseMultiplier)
  return Math.max(min, Math.min(max, base / scale))
}

export function consumeGestureSteps(accumulated, threshold, maxSteps = 4) {
  const value = Number(accumulated) || 0
  const size = Math.max(1, Number(threshold) || 1)
  let steps = value > 0 ? Math.floor(value / size) : Math.ceil(value / size)
  const limit = Math.max(1, Number(maxSteps) || 1)
  steps = Math.max(-limit, Math.min(limit, steps))
  return { steps: steps, remaining: value - steps * size }
}

export function scaleForPinch(currentScale, previousDistance, nextDistance, minScale = 0.42, maxScale = 3.2, multiplier = 1) {
  const min = Math.max(0.1, Number(minScale) || 0.42)
  const max = Math.max(min, Number(maxScale) || 3.2)
  const current = Math.max(min, Math.min(max, Number(currentScale) || 1))
  const previous = Number(previousDistance) || 0
  const next = Number(nextDistance) || 0
  if (previous <= 0 || next <= 0) return current
  const amount = clampGestureMultiplier(multiplier)
  return Math.max(min, Math.min(max, current * Math.pow(next / previous, amount)))
}

export function messageForGestureAction(action, stepCount = 1) {
  if (!action || action.type === 'none') return null
  if (action.type === 'mouse_zoom') {
    const steps = Math.max(1, Math.min(8, Math.abs(Number(stepCount) || 1)))
    return { action: 'mouse', op: 'zoom', delta: (Number(action.delta) || 0) * steps }
  }
  if (action.type === 'mouse_wheel') {
    const steps = Math.max(1, Math.min(8, Math.abs(Number(stepCount) || 1)))
    return { action: 'mouse', op: 'wheel', delta: (Number(action.delta) || 0) * steps }
  }
  if (action.type === 'shortcut') {
    return {
      action: 'simulate_key',
      modifiers: Array.isArray(action.modifiers) ? action.modifiers.slice() : [],
      key: String(action.key || ''),
    }
  }
  return null
}
