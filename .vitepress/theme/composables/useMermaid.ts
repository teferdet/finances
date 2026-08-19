import { ref, type Ref } from 'vue'

export interface MermaidState {
  scale: Ref<number>
  translateX: Ref<number>
  translateY: Ref<number>
}

export function useMermaid(
  viewport: Ref<HTMLElement | null>,
  content: Ref<HTMLElement | null>,
) {
  const scale = ref(1)
  const translateX = ref(0)
  const translateY = ref(0)

  function updateTransform() {
    if (!content.value) return
    content.value.style.transform =
      `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`
  }

  function zoom(delta: number, originX?: number, originY?: number) {
    const oldScale = scale.value
    scale.value = Math.min(Math.max(0.4, scale.value + delta), 3.5)
    if (originX !== undefined && originY !== undefined && viewport.value) {
      const rect = viewport.value.getBoundingClientRect()
      const cx = originX - rect.left - rect.width / 2
      const cy = originY - rect.top - rect.height / 2
      translateX.value -= (cx / oldScale) * (scale.value - oldScale)
      translateY.value -= (cy / oldScale) * (scale.value - oldScale)
    }
    updateTransform()
  }

  function reset() {
    scale.value = 1
    translateX.value = 0
    translateY.value = 0
    updateTransform()
  }

  function setScale(s: number) {
    scale.value = Math.min(Math.max(0.4, s), 3.5)
    translateX.value = 0
    translateY.value = 0
    updateTransform()
  }

  function attach() {
    const vp = viewport.value
    if (!vp) return

    // touch-action: none prevents browser scroll hijack
    vp.style.touchAction = 'none'

    let isDragging = false
    let startX = 0
    let startY = 0
    let lastPinchDist: number | null = null

    // ── Mouse ──────────────────────────────────────────────────────────────
    vp.addEventListener('mousedown', (e: MouseEvent) => {
      if (e.button !== 0) return
      isDragging = true
      startX = e.clientX - translateX.value
      startY = e.clientY - translateY.value
      vp.style.cursor = 'grabbing'
    })
    window.addEventListener('mousemove', (e: MouseEvent) => {
      if (!isDragging) return
      translateX.value = e.clientX - startX
      translateY.value = e.clientY - startY
      updateTransform()
    })
    window.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false
        vp.style.cursor = 'grab'
      }
    })
    vp.addEventListener('wheel', (e: WheelEvent) => {
      e.preventDefault()
      zoom(e.deltaY < 0 ? 0.15 : -0.15, e.clientX, e.clientY)
    }, { passive: false })

    // ── Touch ───────────────────────────────────────────────────────────────
    vp.addEventListener('touchstart', (e: TouchEvent) => {
      e.preventDefault()
      if (e.touches.length === 1) {
        isDragging = true
        lastPinchDist = null
        startX = e.touches[0].clientX - translateX.value
        startY = e.touches[0].clientY - translateY.value
      } else if (e.touches.length === 2) {
        isDragging = false
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        lastPinchDist = Math.hypot(dx, dy)
      }
    }, { passive: false })

    vp.addEventListener('touchmove', (e: TouchEvent) => {
      e.preventDefault()
      if (e.touches.length === 1 && isDragging) {
        translateX.value = e.touches[0].clientX - startX
        translateY.value = e.touches[0].clientY - startY
        updateTransform()
      } else if (e.touches.length === 2 && lastPinchDist !== null) {
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        const newDist = Math.hypot(dx, dy)
        const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2
        const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2
        zoom((newDist - lastPinchDist) * 0.008, midX, midY)
        lastPinchDist = newDist
      }
    }, { passive: false })

    vp.addEventListener('touchend', (e: TouchEvent) => {
      if (e.touches.length < 2) lastPinchDist = null
      if (e.touches.length === 0) isDragging = false
    })
  }

  return { scale, translateX, translateY, zoom, reset, setScale, attach }
}
