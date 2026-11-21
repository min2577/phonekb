const TAP_MAX_MS = 260
const DOUBLE_TAP_MS = 340
const TAP_SLOP_PX = 12
const SWIPE_MIN_PX = 52
const SCROLL_START_PX = 7
const PINCH_START_PX = 9
const SCROLL_STEP_PX = 14
const PINCH_STEP = 0.055

export const DEFAULT_TOUCHPAD_OPTIONS = {
  sensitivity: 1.5,
  scrollSensitivity: 1,
  tapToClick: true,
  tapDrag: true,
  naturalScroll: true,
  inertia: true,
}

function point(touch) {
  return {
    x: Number(touch && (touch.clientX != null ? touch.clientX : touch.pageX)) || 0,
    y: Number(touch && (touch.clientY != null ? touch.clientY : touch.pageY)) || 0,
  }
}

function points(touches) {
  return Array.prototype.map.call(touches || [], point)
}

function center(items) {
  let x = 0
  let y = 0
  for (const item of items) { x += item.x; y += item.y }
  const count = Math.max(1, items.length)
  return { x: x / count, y: y / count }
}

function distance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y)
}

function consume(distancePx, stepPx) {
  const steps = distancePx < 0 ? Math.ceil(distancePx / stepPx) : Math.floor(distancePx / stepPx)
  return { steps, remaining: distancePx - steps * stepPx }
}

export function systemGestureFor(fingers, dx, dy, isTap) {
  if (isTap) {
    if (fingers === 3) return { action: 'simulate_key', modifiers: ['win'], key: 's' }
    if (fingers === 4) return { action: 'simulate_key', modifiers: ['win'], key: 'n' }
    return null
  }
  const horizontal = Math.abs(dx) > Math.abs(dy)
  if (fingers === 3) {
    if (!horizontal && dy < 0) return { action: 'simulate_key', modifiers: ['win'], key: 'tab' }
    if (!horizontal && dy > 0) return { action: 'simulate_key', modifiers: ['win'], key: 'd' }
    if (horizontal && dx < 0) return { action: 'simulate_key', modifiers: ['alt'], key: 'tab' }
    if (horizontal && dx > 0) return { action: 'simulate_key', modifiers: ['alt', 'shift'], key: 'tab' }
  }
  if (fingers === 4) {
    if (horizontal) return { action: 'simulate_key', modifiers: ['win', 'ctrl'], key: dx < 0 ? 'right' : 'left' }
    if (dy < 0) return { action: 'simulate_key', modifiers: ['win'], key: 'tab' }
    if (dy > 0) return { action: 'simulate_key', modifiers: ['win'], key: 'd' }
  }
  return null
}

export function createTouchpadController(config = {}) {
  const emit = typeof config.emit === 'function' ? config.emit : function() {}
  const schedule = typeof config.setTimeout === 'function' ? config.setTimeout : setTimeout
  const unschedule = typeof config.clearTimeout === 'function' ? config.clearTimeout : clearTimeout
  let options = Object.assign({}, DEFAULT_TOUCHPAD_OPTIONS, config.options || {})
  let state = null
  let pendingTapAt = 0
  let pendingTapTimer = null
  let externalDragArmed = false
  let inertiaTimer = null

  function sendMouse(op, extra) {
    emit(Object.assign({ action: 'mouse', op }, extra || {}))
  }

  function sendNotches(op, steps) {
    const delta = steps < 0 ? -120 : 120
    for (let count = Math.abs(steps); count > 0; count--) sendMouse(op, { delta })
  }

  function cancelInertia() {
    if (inertiaTimer != null) unschedule(inertiaTimer)
    inertiaTimer = null
  }

  function cancelPendingTap() {
    if (pendingTapTimer != null) unschedule(pendingTapTimer)
    pendingTapTimer = null
    pendingTapAt = 0
  }

  function queueSingleTap(now) {
    cancelPendingTap()
    pendingTapAt = now
    pendingTapTimer = schedule(function() {
      pendingTapTimer = null
      pendingTapAt = 0
      sendMouse('click', { button: 'left' })
    }, DOUBLE_TAP_MS)
  }

  function startInertia(axis, velocity) {
    cancelInertia()
    if (!options.inertia || Math.abs(velocity) < 0.12) return
    let speed = Math.max(-1.8, Math.min(1.8, velocity))
    let remainder = 0
    const tick = function() {
      remainder += speed * 16
      const step = SCROLL_STEP_PX / Math.max(0.25, Number(options.scrollSensitivity) || 1)
      const result = consume(remainder, step)
      remainder = result.remaining
      if (result.steps) {
        const direction = options.naturalScroll === false ? -result.steps : result.steps
        sendNotches(axis === 'x' ? 'hwheel' : 'wheel', direction)
      }
      speed *= 0.88
      if (Math.abs(speed) >= 0.035) inertiaTimer = schedule(tick, 16)
      else inertiaTimer = null
    }
    inertiaTimer = schedule(tick, 16)
  }

  function begin(rawTouches, now = Date.now()) {
    const items = points(rawTouches)
    if (!items.length) return
    cancelInertia()
    if (state && items.length <= state.fingers) return
    if (state && state.dragging) sendMouse('up', { button: 'left' })

    const fingers = Math.min(4, items.length)
    const origin = center(items)
    if (fingers === 1) {
      const secondTap = pendingTapAt > 0 && now - pendingTapAt <= DOUBLE_TAP_MS
      if (secondTap) cancelPendingTap()
      const dragging = externalDragArmed
      externalDragArmed = false
      state = { fingers, startedAt: now, start: origin, last: origin, moved: false, dragging, secondTap, tapDragAllowed: options.tapDrag !== false, lastMoveAt: now }
      return
    }

    cancelPendingTap()
    state = {
      fingers, startedAt: now, start: origin, last: origin, moved: false,
      startDistance: fingers === 2 ? distance(items[0], items[1]) : 0,
      lastDistance: fingers === 2 ? distance(items[0], items[1]) : 0,
      mode: null, axis: null, scrollRemainder: 0, pinchRemainder: 0,
      lastMoveAt: now, velocityX: 0, velocityY: 0,
    }
  }

  function move(rawTouches, now = Date.now()) {
    const items = points(rawTouches)
    if (!state || !items.length) return
    const current = center(items)
    const dx = current.x - state.last.x
    const dy = current.y - state.last.y
    const totalX = current.x - state.start.x
    const totalY = current.y - state.start.y
    const elapsed = Math.max(1, now - state.lastMoveAt)
    state.velocityX = dx / elapsed
    state.velocityY = dy / elapsed
    state.lastMoveAt = now

    if (state.fingers === 1) {
      const travel = Math.hypot(totalX, totalY)
      if (state.secondTap && !state.dragging) {
        if (travel <= TAP_SLOP_PX) {
          state.last = current
          return
        }
        if (!state.tapDragAllowed) {
          sendMouse('click', { button: 'left' })
          state.secondTap = false
          state.moved = true
          sendMouse('move', {
            dx: totalX * (Number(options.sensitivity) || 1),
            dy: totalY * (Number(options.sensitivity) || 1),
          })
          state.last = current
          return
        }
        sendMouse('down', { button: 'left' })
        state.dragging = true
        state.moved = true
        sendMouse('move', {
          dx: totalX * (Number(options.sensitivity) || 1),
          dy: totalY * (Number(options.sensitivity) || 1),
        })
        state.last = current
        return
      }
      if (travel > TAP_SLOP_PX) state.moved = true
      if (dx || dy) sendMouse('move', {
        dx: dx * (Number(options.sensitivity) || 1),
        dy: dy * (Number(options.sensitivity) || 1),
      })
      state.last = current
      return
    }

    if (state.fingers === 2 && items.length >= 2) {
      const currentDistance = distance(items[0], items[1])
      const pinchTotal = currentDistance - state.startDistance
      const panDistance = Math.hypot(totalX, totalY)
      if (!state.mode) {
        if (Math.abs(pinchTotal) >= PINCH_START_PX && Math.abs(pinchTotal) > panDistance * 0.75) state.mode = 'pinch'
        else if (panDistance >= SCROLL_START_PX) {
          state.mode = 'scroll'
          state.axis = Math.abs(totalX) > Math.abs(totalY) ? 'x' : 'y'
        }
      }
      if (state.mode === 'pinch') {
        const ratio = state.lastDistance > 0 ? currentDistance / state.lastDistance : 1
        state.pinchRemainder += Math.log(Math.max(0.1, ratio))
        const result = consume(state.pinchRemainder, PINCH_STEP)
        state.pinchRemainder = result.remaining
        if (result.steps) sendNotches('zoom', result.steps)
      } else if (state.mode === 'scroll') {
        const axisDelta = state.axis === 'x' ? dx : dy
        state.scrollRemainder += axisDelta
        const step = SCROLL_STEP_PX / Math.max(0.25, Number(options.scrollSensitivity) || 1)
        const result = consume(state.scrollRemainder, step)
        state.scrollRemainder = result.remaining
        if (result.steps) {
          const direction = options.naturalScroll === false ? -result.steps : result.steps
          sendNotches(state.axis === 'x' ? 'hwheel' : 'wheel', direction)
        }
      }
      state.lastDistance = currentDistance
      if (state.mode) state.moved = true
    } else if (Math.hypot(totalX, totalY) > TAP_SLOP_PX) {
      state.moved = true
    }
    state.last = current
  }

  function end(rawTouches, now = Date.now()) {
    if (!state || points(rawTouches).length) return
    const finished = state
    state = null
    if (finished.fingers === 1) {
      if (finished.dragging) {
        sendMouse('up', { button: 'left' })
        cancelPendingTap()
      } else if (finished.secondTap && !finished.moved && now - finished.startedAt <= TAP_MAX_MS) {
        sendMouse('click', { button: 'left', count: 2 })
      } else if (!finished.moved && now - finished.startedAt <= TAP_MAX_MS && options.tapToClick !== false) {
        queueSingleTap(now)
      } else cancelPendingTap()
      return
    }
    if (finished.fingers === 2) {
      if (!finished.moved && now - finished.startedAt <= TAP_MAX_MS) sendMouse('click', { button: 'right' })
      else if (finished.mode === 'scroll') startInertia(finished.axis, finished.axis === 'x' ? finished.velocityX : finished.velocityY)
      return
    }
    const dx = finished.last.x - finished.start.x
    const dy = finished.last.y - finished.start.y
    const travel = Math.hypot(dx, dy)
    const isTap = travel <= TAP_SLOP_PX && now - finished.startedAt <= TAP_MAX_MS
    if (isTap || travel >= SWIPE_MIN_PX) {
      const action = systemGestureFor(finished.fingers, dx, dy, isTap)
      if (action) emit(action)
    }
  }

  function cancel() {
    cancelInertia()
    if (state && state.dragging) sendMouse('up', { button: 'left' })
    if (externalDragArmed) sendMouse('up', { button: 'left' })
    state = null
    externalDragArmed = false
    cancelPendingTap()
  }

  return {
    start: begin,
    move,
    end,
    cancel,
    updateOptions(next) { options = Object.assign({}, options, next || {}) },
    armExternalDrag() {
      cancel()
      sendMouse('down', { button: 'left' })
      externalDragArmed = true
    },
  }
}
