import { ref, onUnmounted, nextTick } from 'vue'
import { useToastStore } from '@/stores/toasts'

const toast = useToastStore()

export function useBarcodeScanner(options = {}) {
  const {
    onDetect,
    formats = ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'codabar'],
    scanInterval = 350,
    facingMode = 'environment',
    continuous = true,
    cooldownMs = 1500,
  } = options

  const scannerOpen = ref(false)
  const scannerError = ref('')
  const videoEl = ref(null)
  const barcodeDetector = ref(null)
  const scanTimer = ref(null)
  const cameraStream = ref(null)
  const lastScannedCode = ref('')
  const scanCooldown = ref(false)

  const supportsBarcodeDetector = () => typeof window !== 'undefined' && 'BarcodeDetector' in window

  async function openScanner() {
    if (!supportsBarcodeDetector()) {
      toast.warning('Tu navegador no soporta escaneo por cámara (requiere iOS 15.4+ / Chrome 88+). Usá el campo manual.')
      return false
    }
    scannerError.value = ''
    scannerOpen.value = true
    await nextTick()
    try {
      barcodeDetector.value = new BarcodeDetector({ formats })
      cameraStream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode } })
      if (videoEl.value) {
        videoEl.value.srcObject = cameraStream.value
        await videoEl.value.play().catch(() => {})
      }
      scanTimer.value = setInterval(detectFromCamera, scanInterval)
      return true
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        scannerError.value = 'Permiso de cámara denegado. Habilitalo en la configuración del navegador.'
      } else if (err.name === 'NotFoundError' || err.name === 'OverconstrainedError') {
        scannerError.value = 'No se encontró cámara trasera. Probá con la frontal.'
      } else {
        scannerError.value = 'No se pudo acceder a la cámara. Permití el acceso e intentá de nuevo.'
      }
      closeCamera()
      return false
    }
  }

  async function detectFromCamera() {
    if (!barcodeDetector.value || !videoEl.value || !cameraStream.value) return
    if (scanCooldown.value) return
    try {
      const codes = await barcodeDetector.value.detect(videoEl.value)
      if (codes && codes.length && codes[0].rawValue) {
        const raw = codes[0].rawValue.trim()
        if (raw === lastScannedCode.value) return
        lastScannedCode.value = raw
        scanCooldown.value = true
        if (onDetect) await onDetect(raw)
        if (!continuous) {
          closeCamera()
        } else {
          setTimeout(() => {
            scanCooldown.value = false
            lastScannedCode.value = ''
          }, cooldownMs)
        }
      }
    } catch {
      // ignorar frames sin detección
    }
  }

  function closeCamera() {
    if (scanTimer.value) {
      clearInterval(scanTimer.value)
      scanTimer.value = null
    }
    if (cameraStream.value) {
      cameraStream.value.getTracks().forEach(t => t.stop())
      cameraStream.value = null
    }
    barcodeDetector.value = null
    scannerOpen.value = false
    scanCooldown.value = false
    lastScannedCode.value = ''
  }

  onUnmounted(() => {
    closeCamera()
  })

  return {
    scannerOpen,
    scannerError,
    videoEl,
    openScanner,
    closeCamera,
    supportsBarcodeDetector: supportsBarcodeDetector(),
  }
}