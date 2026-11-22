import assert from 'node:assert/strict'
import test from 'node:test'
import { shouldPollAutoFulfillment } from '../src/utils/autoFulfillment.ts'

test('auto and upstream orders remain in processing until the fulfillment record is delivered', () => {
  assert.equal(shouldPollAutoFulfillment({
    status: 'fulfilling',
    paid_at: '2026-10-23T05:46:14Z',
    children: [{
      status: 'fulfilling',
      paid_at: '2026-10-23T05:46:14Z',
      items: [{ fulfillment_type: 'upstream' }],
      fulfillment: { status: 'pending' },
    }],
  }), true)

  assert.equal(shouldPollAutoFulfillment({
    status: 'delivered',
    paid_at: '2026-10-23T05:46:14Z',
    children: [{
      status: 'delivered',
      paid_at: '2026-10-23T05:46:14Z',
      items: [{ fulfillment_type: 'auto' }],
      fulfillment: { status: 'delivered' },
    }],
  }), false)
})

test('manual, unpaid, and closed orders are not polled as automatic fulfillment', () => {
  assert.equal(shouldPollAutoFulfillment({ status: 'pending_payment', items: [{ fulfillment_type: 'upstream' }] }), false)
  assert.equal(shouldPollAutoFulfillment({ status: 'fulfilling', paid_at: 'now', items: [{ fulfillment_type: 'manual' }] }), false)
  assert.equal(shouldPollAutoFulfillment({ status: 'canceled', paid_at: 'now', items: [{ fulfillment_type: 'auto' }] }), false)
})
