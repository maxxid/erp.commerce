export function useSounds() {
  function isEnabled() {
    return localStorage.getItem('apex-sounds-enabled') === 'true'
  }

  function respectsMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function play(type) {
    if (!isEnabled() || respectsMotion()) return
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)

    const presets = {
      sale: { freq: 880, duration: 0.15, type: 'sine' },
      'cash-open': { freq: 660, duration: 0.12, type: 'triangle' },
      'cash-close': { freq: 440, duration: 0.2, type: 'triangle' }
    }

    const p = presets[type] || presets.sale
    osc.type = p.type
    osc.frequency.setValueAtTime(p.freq, ctx.currentTime)
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + p.duration)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + p.duration)
  }

  function playSale() { play('sale') }
  function playOpenCash() { play('cash-open') }
  function playCloseCash() { play('cash-close') }

  function toggleEnabled() {
    const current = isEnabled()
    localStorage.setItem('apex-sounds-enabled', current ? 'false' : 'true')
    return !current
  }

  return { isEnabled, playSale, playOpenCash, playCloseCash, toggleEnabled }
}
