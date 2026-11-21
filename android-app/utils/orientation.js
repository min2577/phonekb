let desiredOrientation = 'portrait-primary'
let requestGeneration = 0

function lock(orientation) {
  desiredOrientation = orientation
  const generation = ++requestGeneration
  // #ifdef APP-PLUS
  const apply = function() {
    if (generation !== requestGeneration || desiredOrientation !== orientation) return
    try {
      if (typeof plus !== 'undefined' && plus.screen && typeof plus.screen.lockOrientation === 'function') {
        plus.screen.lockOrientation(orientation)
      }
    } catch (e) {}
  }
  apply()
  setTimeout(apply, 80)
  setTimeout(apply, 260)
  setTimeout(apply, 600)
  // #endif
}

export function lockPortrait() {
  lock('portrait-primary')
}

export function lockLandscape() {
  lock('landscape-primary')
}
