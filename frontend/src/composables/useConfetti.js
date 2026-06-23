export function useConfetti() {
  function respectsMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function fire() {
    if (respectsMotion()) return
    const canvas = document.createElement('canvas')
    canvas.style.cssText = 'position:fixed;inset:0;z-index:9999;pointer-events:none;'
    document.body.appendChild(canvas)
    const ctx = canvas.getContext('2d')
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight

    const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6']
    const particles = Array.from({ length: 120 }, () => ({
      x: canvas.width / 2 + (Math.random() - 0.5) * 200,
      y: canvas.height / 2,
      vx: (Math.random() - 0.5) * 16,
      vy: Math.random() * -18 - 4,
      w: Math.random() * 8 + 4,
      h: Math.random() * 6 + 2,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      rv: (Math.random() - 0.5) * 12,
      gravity: 0.4 + Math.random() * 0.2
    }))

    let frame = 0
    const maxFrames = 90

    function animate() {
      if (frame >= maxFrames) {
        document.body.removeChild(canvas)
        return
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      for (const p of particles) {
        p.x += p.vx
        p.vy += p.gravity
        p.y += p.vy
        p.rotation += p.rv
        p.vx *= 0.99
        const alpha = Math.max(0, 1 - frame / maxFrames)
        ctx.save()
        ctx.translate(p.x, p.y)
        ctx.rotate((p.rotation * Math.PI) / 180)
        ctx.globalAlpha = alpha
        ctx.fillStyle = p.color
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h)
        ctx.restore()
      }
      frame++
      requestAnimationFrame(animate)
    }
    animate()
  }

  function firstSaleOfDay() {
    const today = new Date().toISOString().slice(0, 10)
    const key = `apex-first-sale-${today}`
    if (localStorage.getItem(key)) return
    localStorage.setItem(key, 'true')
    fire()
  }

  return { fire, firstSaleOfDay }
}
