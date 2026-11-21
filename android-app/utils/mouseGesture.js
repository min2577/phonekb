export const WHEEL_LONG_PRESS_MS = 320
export const WHEEL_MOVE_SLOP_PX = 10
export const WHEEL_STEP_PX = 18
export const WHEEL_DELTA = 120

export function consumeWheelMovement(accumulatedY, stepPx = WHEEL_STEP_PX) {
  const distance = Number(accumulatedY) || 0
  const size = Math.max(1, Number(stepPx) || WHEEL_STEP_PX)
  const steps = distance < 0 ? Math.ceil(distance / size) : Math.floor(distance / size)
  return {
    delta: steps === 0 ? 0 : -steps * WHEEL_DELTA,
    remainingY: distance - steps * size,
  }
}
