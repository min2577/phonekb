let hideTimer = null

export function showTransientToast(title, duration) {
  const visibleDuration = Math.max(1, Number(duration) || 2000)
  if (hideTimer) clearTimeout(hideTimer)

  uni.showToast({
    title: String(title || ''),
    icon: 'none',
    duration: visibleDuration,
  })

  hideTimer = setTimeout(function () {
    hideTimer = null
    try { uni.hideToast() } catch (e) {}
  }, visibleDuration + 100)
}
