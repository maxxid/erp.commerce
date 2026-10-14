const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

// Vite copia public/sw.js a dist/ tal cual; acá le inyectamos el commit
// para que cada deploy cambie los bytes del SW y el browser lo instale.
let commit = 'local'
try {
  commit = execSync('git rev-parse --short HEAD', { cwd: path.join(__dirname, '..') }).toString().trim()
} catch { /* fuera de git: queda 'local' */ }

const swPath = path.join(__dirname, '..', 'dist', 'sw.js')
if (fs.existsSync(swPath)) {
  const sw = fs.readFileSync(swPath, 'utf8')
  fs.writeFileSync(swPath, sw.replace('__BUILD_ID__', `apex-erp-${commit}`))
  console.log(`sw.js stamp: apex-erp-${commit}`)
}
