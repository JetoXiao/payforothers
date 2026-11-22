<template>
  <main class="tutorial-page min-h-screen overflow-x-hidden bg-[#f6f7fb] pb-20 pt-28 dark:bg-[#07080c]">
    <div class="container mx-auto min-w-0 max-w-5xl px-4 sm:px-6">
      <RouterLink to="/" class="mb-8 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition hover:text-foreground"><ArrowLeft class="h-4 w-4" /> {{ t('tutorial.backHome') }}</RouterLink>
      <header class="tutorial-header mb-10 overflow-hidden rounded-3xl bg-[#08090f] px-6 py-10 text-white sm:px-10 sm:py-14">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">CHATGPT · GUIDE</p>
        <h1 class="mt-5 max-w-3xl text-4xl font-semibold leading-tight tracking-[-0.045em] sm:text-5xl">{{ t('tutorial.title') }}</h1>
        <p class="mt-5 max-w-2xl text-base leading-7 text-slate-300">{{ t('tutorial.subtitle') }}</p>
        <div class="mt-8 flex flex-wrap gap-2 text-xs font-medium text-slate-300"><span class="rounded-full border border-white/15 bg-white/5 px-3 py-1.5">{{ t('tutorial.updated') }}</span><span class="rounded-full border border-white/15 bg-white/5 px-3 py-1.5">{{ t('tutorial.readTime') }}</span></div>
      </header>

      <div class="grid gap-5 lg:grid-cols-[0.72fr_1.28fr]">
        <aside class="tutorial-aside h-fit rounded-2xl border bg-card p-5 lg:sticky lg:top-24">
          <p class="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{{ t('tutorial.contents') }}</p>
          <nav class="mt-4 space-y-2 text-sm"><a v-for="item in contents" :key="item.id" :href="`#${item.id}`" class="block rounded-lg px-3 py-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground">{{ item.label }}</a></nav>
          <RouterLink to="/" class="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover">{{ t('tutorial.chooseProduct') }}</RouterLink>
        </aside>

        <article class="tutorial-article min-w-0 rounded-2xl border bg-card p-6 sm:p-10">
          <section id="before" class="tutorial-section"><h2>1. {{ t('tutorial.sections.before.title') }}</h2><p>{{ t('tutorial.sections.before.intro') }}</p><ul><li v-for="item in beforeItems" :key="item">{{ item }}</li></ul></section>
          <section id="choose" class="tutorial-section"><h2>2. {{ t('tutorial.sections.choose.title') }}</h2><p>{{ t('tutorial.sections.choose.intro') }}</p><div class="guide-grid"><div v-for="item in chooseItems" :key="item.title" class="guide-card"><span class="guide-card-dot" :class="item.tone"></span><h3>{{ item.title }}</h3><p>{{ item.text }}</p></div></div></section>
          <section id="purchase" class="tutorial-section"><h2>3. {{ t('tutorial.sections.purchase.title') }}</h2><ol><li v-for="item in purchaseItems" :key="item">{{ item }}</li></ol></section>
          <section id="redeem" class="tutorial-section"><h2>4. {{ t('tutorial.sections.redeem.title') }}</h2><p>{{ t('tutorial.sections.redeem.intro') }}</p><ol><li v-for="item in redeemItems" :key="item">{{ item }}</li></ol><div class="guide-callout"><ShieldCheck class="h-5 w-5 flex-none text-cyan-500" /><p>{{ t('tutorial.sections.redeem.note') }}</p></div></section>
          <section id="troubleshoot" class="tutorial-section"><h2>5. {{ t('tutorial.sections.troubleshoot.title') }}</h2><div class="faq-list"><details v-for="item in faqItems" :key="item.q" class="faq-item"><summary>{{ item.q }}<ChevronDown class="h-4 w-4 flex-none" /></summary><p>{{ item.a }}</p></details></div></section>
          <section id="aftercare" class="tutorial-section"><h2>6. {{ t('tutorial.sections.aftercare.title') }}</h2><p>{{ t('tutorial.sections.aftercare.intro') }}</p><ul><li v-for="item in aftercareItems" :key="item">{{ item }}</li></ul></section>
        </article>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ArrowLeft, ChevronDown, ShieldCheck } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { usePageSeo } from '../composables/usePageSeo'

const { t } = useI18n()
usePageSeo({ canonicalPath: () => '/tutorials/chatgpt-recharge', title: () => t('tutorial.title'), description: () => t('tutorial.subtitle') })

const contents = [
  { id: 'before', label: t('tutorial.contentsItems.before') },
  { id: 'choose', label: t('tutorial.contentsItems.choose') },
  { id: 'purchase', label: t('tutorial.contentsItems.purchase') },
  { id: 'redeem', label: t('tutorial.contentsItems.redeem') },
  { id: 'troubleshoot', label: t('tutorial.contentsItems.troubleshoot') },
  { id: 'aftercare', label: t('tutorial.contentsItems.aftercare') },
]
const beforeItems = [t('tutorial.items.before.account'), t('tutorial.items.before.status'), t('tutorial.items.before.region'), t('tutorial.items.before.noCredentials')]
const chooseItems = [
  { title: t('tutorial.items.choose.goTitle'), text: t('tutorial.items.choose.goText'), tone: 'tone-teal' },
  { title: t('tutorial.items.choose.plusTitle'), text: t('tutorial.items.choose.plusText'), tone: 'tone-blue' },
  { title: t('tutorial.items.choose.proTitle'), text: t('tutorial.items.choose.proText'), tone: 'tone-violet' },
]
const purchaseItems = [t('tutorial.items.purchase.one'), t('tutorial.items.purchase.two'), t('tutorial.items.purchase.three'), t('tutorial.items.purchase.four')]
const redeemItems = [t('tutorial.items.redeem.one'), t('tutorial.items.redeem.two'), t('tutorial.items.redeem.three'), t('tutorial.items.redeem.four')]
const faqItems = [
  { q: t('tutorial.items.faq.failedQ'), a: t('tutorial.items.faq.failedA') },
  { q: t('tutorial.items.faq.pendingQ'), a: t('tutorial.items.faq.pendingA') },
  { q: t('tutorial.items.faq.noPlanQ'), a: t('tutorial.items.faq.noPlanA') },
  { q: t('tutorial.items.faq.wrongRegionQ'), a: t('tutorial.items.faq.wrongRegionA') },
]
const aftercareItems = [t('tutorial.items.aftercare.one'), t('tutorial.items.aftercare.two'), t('tutorial.items.aftercare.three'), t('tutorial.items.aftercare.four')]
</script>

<style scoped>
.tutorial-header { position:relative; width:100%; max-width:100%; min-width:0; isolation:isolate; overflow:hidden; background-image:radial-gradient(circle at 82% 0%,rgba(37,99,235,.38),transparent 34%),radial-gradient(circle at 68% 100%,rgba(124,58,237,.28),transparent 35%); }
.tutorial-header h1, .tutorial-header p { display:block; width:100%; max-width:100%; min-width:0; overflow-wrap:anywhere; word-break:break-all; white-space:normal; }
.tutorial-header::after { content:''; position:absolute; width:240px;height:240px;right:8%;bottom:-150px;border-radius:999px;background:#22c7e8;filter:blur(80px);opacity:.16;z-index:-1; }
.tutorial-article { box-shadow:0 20px 60px -45px rgba(0,0,0,.55); }
.tutorial-section + .tutorial-section { border-top:1px solid var(--ui-border); margin-top:2.25rem; padding-top:2.25rem; }
.tutorial-section h2 { font-size:1.35rem; font-weight:650; letter-spacing:-.025em; }
.tutorial-section > p, .tutorial-section li { margin-top:1rem; color:var(--ui-text-secondary); font-size:.95rem; line-height:1.8; }
.tutorial-section ul, .tutorial-section ol { padding-left:1.25rem; }
.tutorial-section li { padding-left:.35rem; }
.guide-grid { display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin-top:1.25rem; }
.guide-card { border:1px solid var(--ui-border);border-radius:1rem;padding:1rem;background:color-mix(in srgb,var(--ui-bg-soft) 70%,transparent); }
.guide-card h3 { margin-top:.9rem;font-size:.95rem;font-weight:650; }
.guide-card p { margin-top:.45rem;font-size:.82rem;line-height:1.65;color:var(--ui-text-muted); }
.guide-card-dot { display:block;width:10px;height:10px;border-radius:999px;box-shadow:0 0 0 6px color-mix(in srgb,currentColor 15%,transparent); }
.tone-teal { color:#10a37f;background:#10a37f; }.tone-blue { color:#4285f4;background:#4285f4; }.tone-violet { color:#8b5cf6;background:#8b5cf6; }
.guide-callout { display:flex;gap:.75rem;margin-top:1.25rem;padding:1rem;border-radius:1rem;background:rgba(34,199,232,.08);border:1px solid rgba(34,199,232,.2); }
.guide-callout p { margin:0;font-size:.9rem;line-height:1.7;color:var(--ui-text-secondary); }
.faq-list { margin-top:1rem;display:grid;gap:.65rem; }.faq-item { border:1px solid var(--ui-border);border-radius:.9rem;padding:0 1rem; }.faq-item summary { display:flex;align-items:center;justify-content:space-between;gap:1rem;cursor:pointer;padding:1rem 0;font-weight:600;font-size:.9rem;list-style:none; }.faq-item summary::-webkit-details-marker{display:none}.faq-item p { padding:0 0 1rem;margin:0;font-size:.9rem;line-height:1.75;color:var(--ui-text-secondary); }
@media (max-width:700px){ .tutorial-page .container, .tutorial-page .grid, .tutorial-page .tutorial-article, .tutorial-page .tutorial-aside { min-width:0; max-width:100%; }.guide-grid{grid-template-columns:1fr}.tutorial-header{padding:2rem 1.25rem}.tutorial-header h1{width:280px;max-width:100%;font-size:2rem;line-height:1.16;letter-spacing:-.04em;overflow-wrap:anywhere!important;word-break:break-all!important;white-space:normal!important}.tutorial-header p{width:280px;max-width:100%;overflow-wrap:anywhere!important;word-break:break-all!important;white-space:normal!important}.tutorial-article{padding:1.25rem} }
</style>
