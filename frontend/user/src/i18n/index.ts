import { createI18n } from 'vue-i18n'
// 默认语言（兜底语言）静态打包，其余语言按需动态加载
import zhCN from './locales/zh-CN.json'
import legalZhCN from './locales/legal-zh-CN.json'
import invoiceZhCN from './locales/invoice-zh-CN.json'
import wechatZhCN from './locales/wechat-zh-CN.json'

const supportedLocales = ['zh-CN', 'zh-TW', 'en-US']

// 非默认语言的懒加载器：切换语言时才下载对应语言包 chunk
const localeLoaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
    'zh-TW': async () => {
        const [main, legal] = await Promise.all([import('./locales/zh-TW.json'), import('./locales/legal-zh-TW.json')])
        const invoice = await import('./locales/invoice-zh-TW.json')
        const wechat = await import('./locales/wechat-zh-TW.json')
        return { default: { ...main.default, ...legal.default, ...invoice.default, ...wechat.default } }
    },
    'en-US': async () => {
        const [main, legal] = await Promise.all([import('./locales/en-US.json'), import('./locales/legal-en-US.json')])
        const invoice = await import('./locales/invoice-en-US.json')
        const wechat = await import('./locales/wechat-en-US.json')
        return { default: { ...main.default, ...legal.default, ...invoice.default, ...wechat.default } }
    },
}

const loadedLocales = new Set(['zh-CN'])

export function detectLocale(): string {
    const saved = localStorage.getItem('locale')
    if (saved && supportedLocales.includes(saved)) return saved

    const browserLang = navigator.language || ''
    if (supportedLocales.includes(browserLang)) return browserLang

    const langPrefix = browserLang.split('-')[0]
    if (langPrefix === 'zh') {
        if (browserLang.includes('TW') || browserLang.includes('HK') || browserLang.includes('Hant')) {
            return 'zh-TW'
        }
        return 'zh-CN'
    }
    if (langPrefix === 'en') return 'en-US'

    return 'zh-CN'
}

const i18n = createI18n({
    legacy: false,
    locale: 'zh-CN',
    fallbackLocale: 'zh-CN',
    // 键断言为 string，避免 locale 类型被收窄为 "zh-CN" 字面量（其余语言在运行时动态注入）
    messages: { 'zh-CN': { ...zhCN, ...legalZhCN, ...invoiceZhCN, ...wechatZhCN } } as Record<string, typeof zhCN & typeof legalZhCN & typeof invoiceZhCN & typeof wechatZhCN>,
})

async function loadLocaleMessages(locale: string): Promise<void> {
    if (loadedLocales.has(locale)) return
    const loader = localeLoaders[locale]
    if (!loader) return
    const messages = await loader()
    i18n.global.setLocaleMessage(locale, (messages.default ?? messages) as any)
    loadedLocales.add(locale)
}

// 记录最新一次切换请求，防止快速连续切换时慢加载的旧请求覆盖新选择
let pendingLocale = ''

// 切换语言：先确保语言包加载完成再更新 locale，避免闪现缺失文案。
// 语言包加载失败时保持当前语言不变，避免整页文案退化为 key。
export async function setI18nLocale(locale: string): Promise<void> {
    if (!supportedLocales.includes(locale)) return
    pendingLocale = locale
    try {
        await loadLocaleMessages(locale)
    } catch (error) {
        console.error(`Failed to load locale messages: ${locale}`, error)
        return
    }
    if (pendingLocale !== locale) return
    i18n.global.locale.value = locale
}

// 空闲时预取其余语言包：让语言切换即时生效，也避免部署更新后旧页面
// 再切语言时请求已失效的旧 chunk（预取时已进入浏览器缓存）
export function warmupLocaleMessages(): void {
    if (typeof window === 'undefined') return

    const prefetch = () => {
        for (const locale of Object.keys(localeLoaders)) {
            void loadLocaleMessages(locale).catch(() => {
                // 预取失败静默忽略，实际切换时会重试并走 setI18nLocale 的错误处理
            })
        }
    }

    if ('requestIdleCallback' in window && typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(prefetch, { timeout: 3000 })
        return
    }
    window.setTimeout(prefetch, 1000)
}

export default i18n
