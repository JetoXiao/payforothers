import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../src/composables/usePayment.ts', import.meta.url), 'utf8')

test('payment page bridges a subdomain order to the configured main origin once', () => {
  assert.match(source, /payment_origin/)
  assert.match(source, /appStore\.config\?\.tenant\?\.mode !== 'site'/)
  assert.match(source, /query\.set\('context',context\)/)
  assert.match(source, /window\.location\.assign\(`\$\{mainPaymentOrigin\.value\}\/pay\?\$\{query\.toString\(\)\}`\)/)
  assert.match(source, /payment_context/)
})
