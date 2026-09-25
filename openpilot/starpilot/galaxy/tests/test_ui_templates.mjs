import assert from 'node:assert/strict'
import { readdir } from 'node:fs/promises'
import { compile } from '../web/vendor/vue/vue.esm-browser.js'

// Compile every exported component, including lazily loaded pages and nested primitives.
globalThis.location = { hash: '#/' }
const directory = new URL('../web/js/', import.meta.url)
const visited = new Set()
let count = 0
function check(component, label) {
  if (!component || typeof component !== 'object' || visited.has(component)) return
  visited.add(component)
  if (component.template) {
    const errors = []
    compile(component.template, { decodeEntities: value => value.replaceAll('&amp;', '&'), onError: error => errors.push(error.message) })
    assert.deepEqual(errors, [], label)
    count++
  }
  for (const [name, child] of Object.entries(component.components || {})) check(child, `${label}/${name}`)
}
for (const file of await readdir(directory)) {
  if (!file.endsWith('.js') || ['app.js', 'boot.js'].includes(file)) continue
  const module = await import(new URL(file, directory))
  for (const [name, component] of Object.entries(module)) check(component, `${file}/${name}`)
}
assert.ok(count >= 40, `Expected the whole component inventory, got ${count}`)
console.log(`Compiled ${count} Galaxy page and shared-component templates.`)
