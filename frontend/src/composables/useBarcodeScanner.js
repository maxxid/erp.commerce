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
  const detectedFlash = ref(false)
  let zxingControls = null
  let zxingReader = null

  // BarcodeDetector (Shape Detection API) solo está en Chrome Android/ChromeOS.
  // En desktop y en iOS Safari no existe nunca: ahí se usa ZXing (JS puro,
  // importado bajo demanda para no pesar el bundle inicial).
  const supportsBarcodeDetector = () => typeof window !== 'undefined' && 'BarcodeDetector' in window

  async function handleDetected(raw) {
    if (!raw || scanCooldown.value || raw === lastScannedCode.value) return
    lastScannedCode.value = raw
    scanCooldown.value = true
    detectedFlash.value = true
    setTimeout(() => { detectedFlash.value = false }, 350)
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

  async function openScanner() {
    scannerError.value = ''
    scannerOpen.value = true
    await nextTick()
    try {
      cameraStream.value = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
          focusMode: 'continuous',
        },
      })
      if (videoEl.value) {
        videoEl.value.srcObject = cameraStream.value
        await videoEl.value.play().catch(() => {})
      }
      if (supportsBarcodeDetector()) {
        barcodeDetector.value = new BarcodeDetector({ formats })
        scanTimer.value = setInterval(detectFromCamera, scanInterval)
      } else {
        const [{ BrowserMultiFormatReader }, { DecodeHintType, BarcodeFormat }] = await Promise.all([
          import('@zxing/browser'),
          import('@zxing/library'),
        ])
        const hints = new Map()
        hints.set(DecodeHintType.POSSIBLE_FORMATS, [
          BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.CODE_128,
          BarcodeFormat.CODE_39, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E, BarcodeFormat.CODABAR,
        ])
        zxingReader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: scanInterval })
        zxingControls = zxingReader.decodeFromStream(cameraStream.value, videoEl.value, (result) => {
          if (result) handleDetected(result.getText().trim())
        })
      }
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
        await handleDetected(codes[0].rawValue.trim())
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
    if (zxingControls) {
      try { zxingControls.stop() } catch { /* ya detenido */ }
      zxingControls = null
    }
    zxingReader = null
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
    detectedFlash,
    supportsBarcodeDetector: supportsBarcodeDetector(),
  }
}
