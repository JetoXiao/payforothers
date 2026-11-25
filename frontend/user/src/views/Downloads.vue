<template>
  <div class="downloads-page min-h-screen bg-background text-foreground">
    <section class="relative overflow-hidden bg-[#0b1020] text-white">
      <div class="downloads-orb downloads-orb-one" aria-hidden="true"></div>
      <div class="downloads-orb downloads-orb-two" aria-hidden="true"></div>
      <div class="relative mx-auto max-w-7xl px-4 pb-14 pt-28 sm:px-6 sm:pb-16 sm:pt-36">
        <div class="max-w-3xl">
          <div class="mb-5 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">
            <HardDriveDownload class="h-4 w-4" aria-hidden="true" />
            <span>R2 Object Storage</span>
          </div>
          <h1 class="text-4xl font-semibold tracking-[-0.055em] sm:text-6xl">{{ t('downloads.title') }}</h1>
          <p class="mt-5 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">{{ t('downloads.subtitle') }}</p>
          <div class="mt-8 flex flex-wrap gap-3 text-sm">
            <span class="downloads-hero-pill"><PackageOpen class="h-4 w-4 text-cyan-300" />{{ t('downloads.stats.resources', { count: filteredResources.length }) }}</span>
            <span class="downloads-hero-pill"><Sparkles class="h-4 w-4 text-violet-300" />{{ t('downloads.stats.categories', { count: Math.max(categories.length - 1, 0) }) }}</span>
            <span class="downloads-hero-pill"><CheckCircle2 class="h-4 w-4 text-emerald-300" />{{ t('downloads.stats.delivery') }}</span>
          </div>
        </div>
      </div>
    </section>

    <main class="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14">
      <div class="mb-7 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{{ t('downloads.libraryEyebrow') }}</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">{{ t('downloads.libraryTitle') }}</h2>
        </div>
        <button v-if="loadError" type="button" class="inline-flex h-10 items-center gap-2 self-start rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition hover:bg-muted lg:self-auto" @click="loadManifest">
          <RefreshCw class="h-4 w-4" /> {{ t('downloads.retry') }}
        </button>
      </div>

      <div class="mb-8 rounded-2xl border border-border/80 bg-card p-3 shadow-sm sm:p-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
          <label class="relative min-w-0 flex-1">
            <span class="sr-only">{{ t('downloads.searchPlaceholder') }}</span>
            <Search class="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input v-model.trim="searchTerm" type="search" class="h-11 w-full rounded-xl border border-border bg-background pl-11 pr-4 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-4 focus:ring-primary/10" :placeholder="t('downloads.searchPlaceholder')" />
          </label>
          <label class="relative shrink-0">
            <span class="sr-only">{{ t('downloads.sortLabel') }}</span>
            <select v-model="sortBy" class="h-11 w-full appearance-none rounded-xl border border-border bg-background py-2 pl-4 pr-10 text-sm font-medium outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 sm:w-48">
              <option value="featured">{{ t('downloads.sortFeatured') }}</option>
              <option value="newest">{{ t('downloads.sortNewest') }}</option>
              <option value="name">{{ t('downloads.sortName') }}</option>
            </select>
            <ChevronDown class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          </label>
        </div>
        <div class="mt-3 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          <button v-for="category in categories" :key="category" type="button" class="shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition" :class="activeCategory === category ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-foreground'" @click="activeCategory = category">
            {{ category === ALL_CATEGORY ? t('downloads.allCategories') : category }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        <div v-for="index in 6" :key="index" class="h-64 animate-pulse rounded-3xl border border-border bg-card/70"></div>
      </div>
      <div v-else-if="filteredResources.length" class="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        <article v-for="resource in filteredResources" :key="resource.id" class="downloads-card group flex min-h-64 flex-col overflow-hidden rounded-3xl border border-border bg-card shadow-sm transition duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-xl">
          <div class="flex items-start justify-between gap-4 p-6 pb-4">
            <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl" :class="resourceTone(resource)">
              <component :is="resourceIcon(resource)" class="h-6 w-6" aria-hidden="true" />
            </div>
            <span v-if="resource.featured" class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-700 dark:bg-amber-400/15 dark:text-amber-300"><Sparkles class="h-3 w-3" />{{ t('downloads.featured') }}</span>
          </div>
          <div class="flex flex-1 flex-col px-6 pb-6">
            <div class="flex items-center gap-2 text-xs font-semibold text-primary">
              <span>{{ resource.category || t('downloads.uncategorized') }}</span>
              <span class="h-1 w-1 rounded-full bg-border"></span>
              <span class="text-muted-foreground">{{ resource.version || t('downloads.latest') }}</span>
            </div>
            <h3 class="mt-2 text-lg font-semibold tracking-[-0.025em]">{{ localized(resource.title) }}</h3>
            <p class="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">{{ localized(resource.description) }}</p>
            <div class="mt-5 flex items-center justify-between gap-3 text-xs text-muted-foreground">
              <span>{{ resource.size || t('downloads.sizeUnknown') }}</span>
              <span>{{ formatDate(resource.updated_at) }}</span>
            </div>
            <div class="mt-5 flex items-center gap-3">
              <a v-if="resolveUrl(resource)" :href="resolveUrl(resource)" target="_blank" rel="noopener noreferrer" class="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                <Download class="h-4 w-4" />{{ t('downloads.download') }}
              </a>
              <button v-else type="button" disabled class="inline-flex h-10 flex-1 cursor-not-allowed items-center justify-center gap-2 rounded-xl bg-muted px-4 text-sm font-semibold text-muted-foreground">
                <ExternalLink class="h-4 w-4" />{{ t('downloads.comingSoon') }}
              </button>
              <a v-if="resource.url && resource.url.startsWith('http')" :href="resource.url" target="_blank" rel="noopener noreferrer" class="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-border text-muted-foreground transition hover:border-primary/40 hover:bg-primary/10 hover:text-primary" :aria-label="t('downloads.openResource')"><ArrowUpRight class="h-4 w-4" /></a>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="rounded-3xl border border-dashed border-border bg-card px-6 py-20 text-center">
        <PackageOpen class="mx-auto h-12 w-12 text-muted-foreground/60" aria-hidden="true" />
        <h3 class="mt-5 text-lg font-semibold">{{ t('downloads.emptyTitle') }}</h3>
        <p class="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">{{ t('downloads.emptyDescription') }}</p>
      </div>

      <aside v-if="usingDemoData" class="mt-8 flex gap-3 rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900 dark:border-cyan-400/20 dark:bg-cyan-400/10 dark:text-cyan-100">
        <HardDriveDownload class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <p class="leading-6">{{ t('downloads.demoHint') }} <code class="rounded bg-white/70 px-1.5 py-0.5 text-xs dark:bg-black/20">VITE_R2_MANIFEST_URL</code> {{ t('downloads.demoHintSuffix') }}</p>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHead } from '@unhead/vue'
import { ArrowUpRight, CheckCircle2, ChevronDown, Download, ExternalLink, FileArchive, FileCode2, FileText, HardDriveDownload, PackageOpen, RefreshCw, Search, Sparkles } from 'lucide-vue-next'
import { usePageSeo } from '../composables/usePageSeo'
import { useAppStore } from '../stores/app'

type LocalizedText = string | Record<string, string> | undefined
interface DownloadResource {
  id: string
  title: LocalizedText
  description: LocalizedText
  category?: string
  version?: string
  size?: string
  updated_at?: string
  url?: string
  file_key?: string
  icon?: string
  featured?: boolean
}

const ALL_CATEGORY = '__all__'
const DEMO_RESOURCES: DownloadResource[] = [
  { id: 'starter-kit', title: { 'zh-CN': 'AI 使用入门包', 'zh-TW': 'AI 使用入門包', 'en-US': 'AI Starter Kit' }, description: { 'zh-CN': '整理好的使用指南、快捷指令与常用检查清单。', 'zh-TW': '整理好的使用指南、快捷指令與常用檢查清單。', 'en-US': 'Guides, prompts, and practical checklists for getting started.' }, category: '工具包', version: 'v1.0', size: '—', featured: true, icon: 'archive' },
  { id: 'prompt-library', title: { 'zh-CN': '提示词模板库', 'zh-TW': '提示詞模板庫', 'en-US': 'Prompt Library' }, description: { 'zh-CN': '适合写作、学习、编程与日常工作的可复制模板。', 'zh-TW': '適合寫作、學習、編程與日常工作的可複製模板。', 'en-US': 'Reusable templates for writing, learning, coding, and everyday work.' }, category: '模板', version: 'v1.0', size: '—', icon: 'code' },
  { id: 'quick-guide', title: { 'zh-CN': '快速上手指南', 'zh-TW': '快速上手指南', 'en-US': 'Quick Start Guide' }, description: { 'zh-CN': '从账号准备到兑换确认，一页看懂完整流程。', 'zh-TW': '從帳號準備到兌換確認，一頁看懂完整流程。', 'en-US': 'A concise walkthrough from account setup to redemption.' }, category: '教程', version: 'v1.0', size: '—', icon: 'text' },
]

const { t, locale } = useI18n()
const appStore = useAppStore()
const resources = ref<DownloadResource[]>([])
const loading = ref(true)
const loadError = ref(false)
const usingDemoData = ref(false)
const searchTerm = ref('')
const activeCategory = ref(ALL_CATEGORY)
const sortBy = ref<'featured' | 'newest' | 'name'>('featured')

const configuredDownloads = computed(() => (appStore.config?.downloads || {}) as { enabled?: boolean; manifest_url?: string; public_url?: string })
const isDownloadsEnabled = computed(() => configuredDownloads.value.enabled !== false)
const manifestUrl = computed(() => String(configuredDownloads.value.manifest_url || import.meta.env.VITE_R2_MANIFEST_URL || '/downloads/manifest.json').trim())
const r2PublicUrl = computed(() => String(configuredDownloads.value.public_url || import.meta.env.VITE_R2_PUBLIC_URL || '').trim().replace(/\/$/, ''))

const localized = (value: LocalizedText) => {
  if (typeof value === 'string') return value
  if (!value || typeof value !== 'object') return ''
  return value[locale.value] || value['zh-CN'] || value['en-US'] || Object.values(value)[0] || ''
}

const normaliseResources = (payload: unknown): DownloadResource[] => {
  const list = Array.isArray(payload) ? payload : (payload && typeof payload === 'object' && Array.isArray((payload as { resources?: unknown }).resources) ? (payload as { resources: unknown[] }).resources : [])
  return list.map((item, index) => {
    const raw = (item && typeof item === 'object' ? item : {}) as Record<string, unknown>
    return {
      id: String(raw.id || raw.slug || `resource-${index + 1}`),
      title: raw.title as LocalizedText,
      description: raw.description as LocalizedText,
      category: String(raw.category || '').trim(),
      version: String(raw.version || '').trim(),
      size: String(raw.size || '').trim(),
      updated_at: String(raw.updated_at || raw.updatedAt || '').trim(),
      url: String(raw.url || '').trim(),
      file_key: String(raw.file_key || raw.fileKey || '').trim(),
      icon: String(raw.icon || '').trim(),
      featured: raw.featured === true,
    }
  }).filter((item) => localized(item.title))
}

const loadManifest = async () => {
  loading.value = true
  loadError.value = false
  try {
    const response = await fetch(manifestUrl.value, { cache: 'no-store' })
    if (!response.ok) throw new Error(`manifest request failed: ${response.status}`)
    const next = normaliseResources(await response.json())
    resources.value = next
    usingDemoData.value = false
  } catch (error) {
    console.warn('Downloads manifest unavailable; showing setup preview.', error)
    resources.value = DEMO_RESOURCES
    usingDemoData.value = true
    loadError.value = true
  } finally {
    loading.value = false
  }
}

const categories = computed<string[]>(() => {
  const values = Array.from(new Set(resources.value.map((item) => item.category).filter((value): value is string => Boolean(value))))
  values.sort((a: string, b: string) => a.localeCompare(b, locale.value))
  return [ALL_CATEGORY, ...values]
})
const filteredResources = computed(() => {
  const query = searchTerm.value.toLowerCase()
  const result = resources.value.filter((item) => {
    const matchesCategory = activeCategory.value === ALL_CATEGORY || item.category === activeCategory.value
    const haystack = `${localized(item.title)} ${localized(item.description)} ${item.category || ''}`.toLowerCase()
    return matchesCategory && (!query || haystack.includes(query))
  })
  return result.sort((a, b) => {
    if (sortBy.value === 'name') return localized(a.title).localeCompare(localized(b.title), locale.value)
    if (sortBy.value === 'newest') return String(b.updated_at || '').localeCompare(String(a.updated_at || ''))
    return Number(b.featured) - Number(a.featured) || localized(a.title).localeCompare(localized(b.title), locale.value)
  })
})

const resolveUrl = (resource: DownloadResource) => {
  if (resource.url) return resource.url
  if (!resource.file_key || !r2PublicUrl.value) return ''
  return `${r2PublicUrl.value}/${resource.file_key.replace(/^\/+/, '')}`
}

const formatDate = (value?: string) => {
  if (!value) return t('downloads.dateUnknown')
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale.value, { year: 'numeric', month: 'short', day: 'numeric' }).format(date)
}

const resourceIcon = (resource: DownloadResource) => {
  if (resource.icon === 'code') return FileCode2
  if (resource.icon === 'text') return FileText
  return FileArchive
}

const resourceTone = (resource: DownloadResource) => {
  if (resource.icon === 'code') return 'bg-violet-100 text-violet-700 dark:bg-violet-400/15 dark:text-violet-300'
  if (resource.icon === 'text') return 'bg-amber-100 text-amber-700 dark:bg-amber-400/15 dark:text-amber-300'
  return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-400/15 dark:text-cyan-300'
}

const manifestOrigin = (() => {
  if (!manifestUrl.value.startsWith('http')) return ''
  try { return new URL(manifestUrl.value).origin } catch { return '' }
})()
useHead({ link: manifestOrigin ? [{ rel: 'preconnect', href: manifestOrigin }] : [] })
usePageSeo({ canonicalPath: () => '/downloads', title: () => t('downloads.title'), description: () => t('downloads.subtitle'), noindex: () => false })

onMounted(async () => {
  await appStore.loadConfig()
  if (isDownloadsEnabled.value) await loadManifest()
  else loading.value = false
})
</script>

<style scoped>
.downloads-orb { position: absolute; border-radius: 999px; filter: blur(72px); pointer-events: none; opacity: .35; }
.downloads-orb-one { width: 360px; height: 360px; right: 8%; top: -180px; background: #2563eb; }
.downloads-orb-two { width: 280px; height: 280px; left: 28%; bottom: -220px; background: #7c3aed; }
.downloads-hero-pill { display: inline-flex; align-items: center; gap: .5rem; border: 1px solid rgba(255,255,255,.14); border-radius: 999px; padding: .55rem .8rem; color: #dbeafe; background: rgba(255,255,255,.07); backdrop-filter: blur(12px); }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
.scrollbar-hide::-webkit-scrollbar { display: none; }
</style>
