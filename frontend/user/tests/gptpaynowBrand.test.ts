import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = (path: string) => readFileSync(new URL('../src/' + path, import.meta.url), 'utf8')
test('legal fallback has matching sections in all supported languages', () => {
  const locales = ['zh-CN', 'en-US', 'zh-TW']
  const documents = locales.map(locale => JSON.parse(source('i18n/locales/legal-' + locale + '.json')).legalPage)
  for (const type of ['privacy', 'terms']) {
    const expected = documents[0][type].sections.map((section: any) => section.id)
    for (const doc of documents) {
      assert.deepEqual(doc[type].sections.map((section: any) => section.id), expected)
      assert.ok(doc.statusText && doc.noticeText)
      for (const section of doc[type].sections) {
        assert.ok(section.title.length > 0)
        assert.ok(section.paragraphs.length >= 2)
        assert.ok(section.paragraphs.every((paragraph: string) => paragraph.length > 0))
      }
    }
  }
})
test('dark primary buttons use a contrasting foreground', () => {
  const css = source('style.css')
  const dark = css.match(/\.dark\s*\{([^}]+)\}/)?.[1] || ''
  const foreground = dark.match(/--ui-text-on-accent:\s*(#[0-9a-f]+)/)?.[1]
  const background = dark.match(/--ui-accent:\s*(#[0-9a-f]+)/)?.[1]
  const luminance = (color: string) => {
    const linear = [1, 3, 5].map(index => parseInt(color.slice(index, index + 2), 16) / 255).map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4)
    return linear[0]! * 0.2126 + linear[1]! * 0.7152 + linear[2]! * 0.0722
  }
  assert.ok(foreground && background)
  const ratio = (luminance(background) + 0.05) / (luminance(foreground) + 0.05)
  assert.ok(ratio >= 4.5, 'Primary button contrast must reach 4.5:1')
})
test('the classic storefront does not render the template footer region', () => {
  const app = source('App.vue')
  assert.ok(!app.match(/<Footer\s/))
  assert.ok(!app.includes('import Footer'))
})
