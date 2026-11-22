<template>
  <div class="legal-page min-h-screen bg-background pb-20 pt-28 text-foreground">
    <div class="mx-auto w-full min-w-0 max-w-6xl px-4 sm:px-6">
      <RouterLink to="/" class="mb-7 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft class="size-4" aria-hidden="true" /> {{ t('legalPage.back') }}
      </RouterLink>
      <header class="legal-hero rounded-3xl px-6 py-10 sm:px-10 sm:py-14">
        <p class="text-xs font-semibold tracking-[0.2em] text-cyan-300">{{ t('legalPage.eyebrow') }}</p>
        <h1 class="mt-5 text-4xl font-semibold tracking-tight text-white sm:text-5xl">{{ title }}</h1>
        <p class="mt-5 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">{{ brandText(t(type === 'terms' ? 'legalPage.termsSummary' : 'legalPage.privacySummary')) }}</p>
        <div class="mt-7 flex flex-wrap items-center gap-4 text-xs text-slate-300">
          <span v-if="!content">{{ t('legalPage.updated') }} <time datetime="2026-10-07">2026-10-07</time></span>
        </div>
      </header>

      <div v-if="loading" class="grid place-items-center py-20" role="status">
        <Loader2 class="size-8 animate-spin" /><span class="sr-only">{{ t('common.loading') }}</span>
      </div>
      <div v-else class="mt-8 grid min-w-0 grid-cols-1 items-start gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside class="legal-sidebar space-y-6 lg:sticky lg:top-24">
          <nav class="space-y-2" :aria-label="t('legalPage.navigation')">
            <RouterLink v-for="page in legalPages" :key="page.path" :to="page.path" class="flex items-center gap-3 rounded-xl border px-4 py-3 text-sm transition" :class="type === page.type ? 'border-cyan-500/30 bg-cyan-500/10 text-foreground' : 'border-transparent text-muted-foreground hover:bg-muted'">
              <component :is="page.icon" class="size-4" aria-hidden="true" /> {{ t(page.label) }}
            </RouterLink>
          </nav>
          <nav v-if="!content" :aria-label="t('legalPage.contents')" class="hidden lg:block">
            <h2 class="mb-3 px-4 text-xs font-semibold tracking-wide text-muted-foreground">{{ t('legalPage.contents') }}</h2>
            <a v-for="(section, index) in sections" :key="index" :href="'#legal-' + index" class="block rounded-lg px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">{{ rt(section.title) }}</a>
          </nav>
          <RouterLink to="/tutorials/chatgpt-recharge" class="inline-flex items-center gap-2 px-4 text-sm text-cyan-700 hover:underline dark:text-cyan-300"><BookOpen class="size-4" />{{ t('legalPage.tutorial') }}</RouterLink>
        </aside>

        <article class="legal-article min-w-0 rounded-2xl border bg-card p-6 sm:p-9">
          <template v-if="!content">
            <div class="mb-8 border-b pb-8">
              <h2 class="text-base font-semibold">{{ t('legalPage.noticeTitle') }}</h2>
              <p class="mt-3 text-sm leading-7 text-muted-foreground">{{ brandText(t('legalPage.noticeText')) }}</p>
            </div>
            <section v-for="(section, index) in sections" :id="'legal-' + index" :key="index" class="legal-section scroll-mt-24">
              <h2 class="text-lg font-semibold tracking-tight">{{ String(index + 1).padStart(2, '0') }} · {{ rt(section.title) }}</h2>
              <p v-for="(paragraph, paragraphIndex) in section.paragraphs" :key="paragraphIndex" class="mt-4 text-sm leading-7 text-muted-foreground">{{ brandText(rt(paragraph)) }}</p>
            </section>
          </template>
          <div v-else class="prose prose-sm max-w-none dark:prose-invert theme-prose" v-html="safeContent"></div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, BookOpen, FileText, Loader2, ShieldCheck } from 'lucide-vue-next'
import DOMPurify from 'dompurify'
import { useLegal } from '../composables/useLegal'

const props = defineProps<{ type: 'terms' | 'privacy' }>()
const { t, tm, rt } = useI18n()
const { loading, title, content } = useLegal(() => props.type)
const legalPages = [
  { path: '/privacy', type: 'privacy', label: 'footer.privacy', icon: ShieldCheck },
  { path: '/terms', type: 'terms', label: 'footer.terms', icon: FileText },
]
type Message = Parameters<typeof rt>[0]
const sections = computed(() => tm('legalPage.' + props.type + '.sections') as Array<{ id: Message; title: Message; paragraphs: Message[] }>)
const safeContent = computed(() => DOMPurify.sanitize(brandText(content.value), { USE_PROFILES: { html: true } }))
const brandText = (value: unknown) => String(value ?? '').replace(/gptpaynow/gi, 'GptPayNow')
</script>

<style scoped>
.legal-hero { background: radial-gradient(ellipse at 90% 0%,rgba(66,133,244,.24),transparent 60%),radial-gradient(ellipse at 90% 100%,rgba(124,92,252,.18),transparent 50%),#08090f; }
.legal-page { overflow-wrap: anywhere; }
.legal-section + .legal-section { border-top: 1px solid var(--ui-border); padding-top: 2rem; margin-top: 2rem; }
</style>
