const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

try {
  const commit = execSync('git rev-parse --short HEAD', { cwd: path.join(__dirname, '..') }).toString().trim()
  fs.writeFileSync(path.join(__dirname, '..', '.env'), `VITE_GIT_COMMIT=${commit}\n`)
  console.log(`Commit: ${commit}`)
} catch (e) {
  fs.writeFileSync(path.join(__dirname, '..', '.env'), 'VITE_GIT_COMMIT=local\n')
}
