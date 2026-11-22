import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { normalizeWechatAccounts, replaceLegacyWechatContact } from '../src/utils/wechatSupport.ts'

test('empty, one and multiple WeChat IDs, preserving order and clearing explicitly', () => {
  assert.deepEqual(normalizeWechatAccounts(undefined), [])
  assert.deepEqual(normalizeWechatAccounts('one'), [])
  assert.deepEqual(normalizeWechatAccounts([]), [])
  assert.deepEqual(normalizeWechatAccounts([' think-more-9 ']), ['think-more-9'])
  assert.deepEqual(normalizeWechatAccounts(['one', 'two', '', 'ONE', null, 'https://x.test', '<script>']), ['one', 'two'])
  assert.equal(normalizeWechatAccounts(Array.from({ length: 30 }, (_, i) => 'wx_' + i)).length, 20)
})

test('legacy imported contact is dynamic without changing surrounding warranty text', () => {
  const old = '<p>兑换失败，请联系 GptPayNow 微信客服 think-more-9。本平台为独立服务。</p>'
  assert.equal(replaceLegacyWechatContact(old, '本页微信客服'), '<p>兑换失败，请联系 本页微信客服。本平台为独立服务。</p>')
  assert.equal(replaceLegacyWechatContact('WeChat: another-support-id', 'Contact'), 'WeChat: another-support-id')
  assert.equal(replaceLegacyWechatContact('GptPayNow WeChat support: think-more-9.', '<b>Contact</b>'), '&lt;b&gt;Contact&lt;/b&gt;.')
  assert.ok(!replaceLegacyWechatContact(old, '订单页售后支持').includes('think-more-9'))
})

test('support translations have consistent nonempty keys in every locale', () => {
  const messages = ['zh-CN', 'zh-TW', 'en-US'].map(locale => JSON.parse(readFileSync(new URL('../src/i18n/locales/wechat-' + locale + '.json', import.meta.url), 'utf8')).wechatSupport)
  for (const message of messages) {
    assert.deepEqual(Object.keys(message), Object.keys(messages[0]))
    assert.ok(Object.values(message).every(value => typeof value === 'string' && value.length > 0))
  }
})
