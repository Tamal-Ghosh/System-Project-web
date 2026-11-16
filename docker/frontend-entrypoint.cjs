const fs = require('node:fs')
const crypto = require('node:crypto')
const { spawn, spawnSync } = require('node:child_process')
const digest = crypto.createHash('sha256').update(fs.readFileSync('package-lock.json')).digest('hex')
const stamp = 'node_modules/.dermascope-lock'
if (!fs.existsSync(stamp) || fs.readFileSync(stamp, 'utf8') !== digest) {
  console.log('Dependency lock changed: refreshing container node_modules.')
  const result = spawnSync('npm', ['ci'], { stdio: 'inherit' })
  if (result.status !== 0) process.exit(result.status || 1)
  fs.writeFileSync(stamp, digest)
}
const [command, ...args] = process.argv.slice(2)
if (!command) throw new Error('Missing frontend command')
const child = spawn(command, args, { stdio: 'inherit' })
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal))
child.on('error', error => { console.error(error); process.exit(1) })
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)))
