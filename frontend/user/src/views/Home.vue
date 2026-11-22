<template>
  <div class="home-page min-h-screen overflow-hidden bg-background text-foreground">
    <section class="relative overflow-hidden bg-[#08090f] text-white">
      <div class="hero-orb hero-orb-blue" aria-hidden="true"></div>
      <div class="hero-orb hero-orb-violet" aria-hidden="true"></div>
      <div class="container relative mx-auto grid min-w-0 max-w-7xl grid-cols-1 items-center gap-12 px-4 pb-20 pt-32 sm:px-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)] lg:gap-16 lg:pb-24 lg:pt-40">
        <div class="relative z-10 min-w-0 max-w-2xl">
          <p class="mb-6 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">{{ t('home.hero.badge') }}</p>
          <h1 class="max-w-2xl text-5xl font-semibold leading-[1.04] tracking-[-0.06em] sm:text-6xl lg:text-[5.25rem]">{{ t('home.hero.title') }}</h1>
          <p class="mt-7 max-w-xl text-base leading-7 text-slate-300 sm:text-lg">{{ t('home.hero.subtitle') }}</p>
          <a href="#products" class="mt-9 inline-flex h-12 items-center gap-2 rounded-xl bg-[#ffffff] px-5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100">
            {{ t('home.hero.cta') }} <ArrowDown class="h-4 w-4" />
          </a>
        </div>

        <div class="relative mx-auto w-full min-w-0 max-w-[480px]">
          <div class="grid grid-cols-2 gap-3 sm:gap-4">
            <div v-for="(ability, index) in gptAbilities" :key="ability.title" class="hero-product" :class="[`hero-product-${index}`, ability.tone]">
              <div class="hero-product-logo"><component :is="ability.icon" class="h-7 w-7" aria-hidden="true" /></div>
              <h2 class="mt-4 text-base font-semibold text-white/90">{{ t(ability.title) }}</h2>
              <p class="mt-2 text-xs leading-5 text-slate-300 sm:text-sm">{{ t(ability.text) }}</p>
            </div>
          </div>
          <p class="mt-5 text-xs leading-5 text-slate-400">{{ t('home.hero.abilities.note') }}</p>
        </div>
      </div>
    </section>

    <section id="products" class="relative bg-[#f6f7fb] py-20 dark:bg-[#07080c] sm:py-24">
      <div class="container mx-auto max-w-7xl px-4 sm:px-6">
        <div class="mb-10 flex items-end justify-between gap-6">
          <div>
            <p class="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-primary">{{ t('home.featured.eyebrow') }}</p>
            <h2 class="text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">{{ t('home.featured.title') }}</h2>
            <p class="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">{{ t('home.featured.description') }}</p>
          </div>
          <span class="hidden text-sm font-medium text-muted-foreground sm:block">{{ products.length }} {{ t('home.featured.countLabel') }}</span>
        </div>

        <div v-if="products.length" class="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          <ProductCard v-for="(product, idx) in products" :key="product.id" :product="product" :index="idx" :animation-step="35" :accent="accentClass(product, idx)" @click="goToProduct" @quick-buy="openQuickBuy" />
        </div>
        <div v-else class="rounded-3xl border border-dashed bg-card py-20 text-center text-muted-foreground"><PackageOpen class="mx-auto mb-4 h-12 w-12 opacity-50" />{{ t('home.featured.empty') }}</div>
      </div>
    </section>

    <section class="border-y bg-card">
      <div class="container mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:px-6" :class="hasWechatSupport ? 'sm:grid-cols-2 lg:grid-cols-4' : 'sm:grid-cols-3'">
        <div class="flex gap-3"><ShieldCheck class="mt-0.5 h-5 w-5 flex-none text-cyan-500" /><div><h3 class="text-sm font-semibold">{{ t('home.trust.selectionTitle') }}</h3><p class="mt-1 text-sm leading-6 text-muted-foreground">{{ t('home.trust.selectionDescription') }}</p></div></div>
        <div class="flex gap-3"><ReceiptText class="mt-0.5 h-5 w-5 flex-none text-violet-500" /><div><h3 class="text-sm font-semibold">{{ t('home.trust.orderTitle') }}</h3><p class="mt-1 text-sm leading-6 text-muted-foreground">{{ t('home.trust.orderDescription') }}</p></div></div>
        <div class="flex gap-3"><LifeBuoy class="mt-0.5 h-5 w-5 flex-none text-emerald-500" /><div><h3 class="text-sm font-semibold">{{ t('home.trust.supportTitle') }}</h3><p class="mt-1 text-sm leading-6 text-muted-foreground">{{ t('home.trust.supportDescription') }}</p></div></div>
        <WechatSupport compact />
      </div>
    </section>

    <section class="bg-[#f6f7fb] py-12 dark:bg-[#07080c] sm:py-16" aria-labelledby="service-intro-title">
      <div class="container mx-auto max-w-7xl px-4 sm:px-6">
        <div class="max-w-3xl rounded-2xl border bg-card px-6 py-6 sm:px-8">
          <h2 id="service-intro-title" class="text-lg font-semibold tracking-[-0.02em]">{{ t('home.seoIntro.title') }}</h2>
          <p class="mt-3 text-sm leading-7 text-muted-foreground">{{ t('home.seoIntro.description') }}</p>
          <p class="mt-2 text-sm leading-7 text-muted-foreground">{{ t('home.seoIntro.scope') }}</p>
        </div>
      </div>
    </section>

    <ProductQuickBuy v-if="quickBuyProduct" :product="quickBuyProduct" :visible="quickBuyVisible" @update:visible="quickBuyVisible = $event" />
    <AnnouncementModal v-if="activeAnnouncement" :announcement="activeAnnouncement" :visible="announcementVisible" @update:visible="announcementVisible = $event" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useHead } from '@unhead/vue'
import { ArrowDown, BrainCircuit, Image, LifeBuoy, PackageOpen, ReceiptText, ShieldCheck, Sparkles, TerminalSquare } from 'lucide-vue-next'
import { productAPI } from '../api'
import { useLocalized } from '../composables/useProduct'
import { usePageSeo } from '../composables/usePageSeo'
import { useAppStore } from '../stores/app'
import ProductCard from '../components/ProductCard.vue'
import WechatSupport from '../components/WechatSupport.vue'
import { useWechatSupport } from '../composables/useWechatSupport'
import ProductQuickBuy from '../components/ProductQuickBuy.vue'
import AnnouncementModal from '../components/AnnouncementModal.vue'
import { useAnnouncement, type HomeAnnouncement } from '../composables/useAnnouncement'

const router = useRouter()
const { t } = useI18n()
const { getLocalizedText } = useLocalized()
const appStore = useAppStore()
const { hasWechatSupport } = useWechatSupport()
const products = ref<any[]>([])
const quickBuyProduct = ref<any>(null)
const quickBuyVisible = ref(false)
const activeAnnouncement = ref<HomeAnnouncement | null>(null)
const announcementVisible = ref(false)
const { shouldShow } = useAnnouncement()

useHead({
  script: [{
    key: 'gptpaynow-home-jsonld',
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: 'GptPayNow',
      url: 'https://www.gptpaynow.com/',
      description: 'ChatGPT 与 GPT 订阅充值服务，提供商品详情、在线下单、订单查询和充值教程。',
      areaServed: 'Worldwide',
      knowsAbout: ['ChatGPT', 'GPT Plus', 'GPT Pro', 'Claude subscription'],
    }),
  }],
})

usePageSeo({
  canonicalPath: () => '/',
  title: () => t('home.hero.title'),
  description: () => t('home.seoIntro.description'),
  keywords: () => t('home.seoIntro.keywords'),
})

const openQuickBuy = (product: any) => { quickBuyProduct.value = product; quickBuyVisible.value = true }
const goToProduct = (slug: string) => router.push(`/products/${slug}`)
const gptAbilities = [
  { title: 'home.hero.abilities.reasoningTitle', text: 'home.hero.abilities.reasoningText', tone: 'accent-blue', icon: BrainCircuit },
  { title: 'home.hero.abilities.latestTitle', text: 'home.hero.abilities.latestText', tone: 'accent-violet', icon: Sparkles },
  { title: 'home.hero.abilities.imagesTitle', text: 'home.hero.abilities.imagesText', tone: 'accent-warm', icon: Image },
  { title: 'home.hero.abilities.codeTitle', text: 'home.hero.abilities.codeText', tone: 'accent-teal', icon: TerminalSquare },
]
const accentClass = (product: any, index: number) => {
  const title = getLocalizedText(product?.title).toLowerCase()
  if (title.includes('claude')) return 'accent-warm'
  if (title.includes('gemini')) return 'accent-blue'
  if (title.includes('codex')) return 'accent-violet'
  return ['accent-teal', 'accent-blue', 'accent-violet'][index % 3]
}

onMounted(async () => {
  await appStore.loadConfig()
  try { products.value = (await productAPI.list({ page: 1, page_size: 50 })).data.data || [] } catch (error) { console.error('Failed to load products:', error) }
  const announcement = appStore.config?.announcement as HomeAnnouncement | undefined
  if (announcement && shouldShow(announcement)) { activeAnnouncement.value = announcement; announcementVisible.value = true }
})
</script>

<style scoped>
.hero-orb { position:absolute; border-radius:999px; filter:blur(70px); opacity:.32; pointer-events:none; animation: drift 16s ease-in-out infinite alternate; }
.hero-orb-blue { width:360px; height:360px; background:#2563eb; right:18%; top:-120px; }
.hero-orb-violet { width:300px; height:300px; background:#7c3aed; right:-40px; bottom:-140px; animation-delay:-6s; }
.hero-product { position:relative; min-width:0; min-height:190px; display:flex; flex-direction:column; justify-content:flex-start; padding:20px; border:1px solid rgba(255,255,255,.12); border-radius:22px; background:rgba(255,255,255,.07); backdrop-filter:blur(18px); box-shadow:0 20px 60px rgba(0,0,0,.22); transform:translateY(0); transition:transform .25s ease, border-color .25s ease; }
.hero-product:hover { transform:translateY(-4px); border-color:rgba(255,255,255,.28); }
.hero-product-1 { margin-top:26px; }
.hero-product-2 { margin-top:-18px; }
.hero-product-logo { display:grid; width:58px; height:58px; flex-shrink:0; place-items:center; border-radius:18px; color:var(--accent); background:color-mix(in srgb, var(--accent) 15%, transparent); border:1px solid color-mix(in srgb, var(--accent) 30%, transparent); }
.hero-product-placeholder { min-height:230px; align-items:center; justify-content:center; gap:12px; grid-column:span 2; }
.accent-teal { --accent:#10a37f; }
.accent-warm { --accent:#d97757; }
.accent-blue { --accent:#4285f4; }
.accent-violet { --accent:#8b5cf6; }
@keyframes drift { from { transform:translate3d(-8px, 4px, 0) scale(1); } to { transform:translate3d(15px, -10px, 0) scale(1.08); } }
@media (prefers-reduced-motion:reduce) { .hero-orb { animation:none; } }
@media (max-width:639px) { .hero-product { padding:16px; } }
</style>
