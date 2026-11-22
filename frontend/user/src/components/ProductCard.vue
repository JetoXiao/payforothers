<template>
  <article
    class="group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border bg-card transition-all duration-200 theme-slide-up"
    :class="[accent || accentForProduct, isSoldOut(product) ? 'opacity-70 grayscale-[0.2]' : 'hover:-translate-y-1 hover:border-hairline-strong hover:shadow-card']"
    :style="{ animationDelay: `${index * animationStep}ms` }"
    @click="$emit('click', product.slug)">
    <div class="flex items-center justify-between px-5 pt-5">
      <div class="grid h-20 w-20 place-items-center overflow-hidden rounded-2xl border bg-white/80 dark:bg-white/10">
      <img v-if="displayImageSrc && !imageErrored" :src="displayImageSrc"
        :alt="getLocalizedText(product.title)" loading="lazy" decoding="async"
        class="h-full w-full object-contain p-2 transition-transform duration-200 group-hover:scale-105"
        @error="handleImageError" />
      <div v-else class="w-full h-full flex items-center justify-center text-muted-foreground" role="img"
        :aria-label="getLocalizedText(product.title)">
        <ImageIcon class="h-7 w-7" :stroke-width="1.5" aria-hidden="true" />
      </div>
      </div>
      <span v-if="!isSoldOut(product)" class="product-accent-dot" aria-hidden="true"></span>
    </div>

    <div class="flex flex-1 flex-col px-5 pb-5 pt-5">
      <div v-if="product.category?.name" class="mb-2 truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {{ getLocalizedText(product.category.name) }}
      </div>
      <h3 class="line-clamp-2 text-[17px] font-semibold leading-tight text-foreground">
        {{ getLocalizedText(product.title) }}
      </h3>
      <p class="mt-3 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
        {{ getLocalizedText(product.description) }}
      </p>

      <div class="mt-auto flex items-end justify-between gap-3 border-t pt-5">
        <div class="flex flex-col">
          <span class="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">{{ t('products.price') }}</span>
          <span
            v-if="hasPromotionPrice(product)"
            class="theme-price-sm theme-price-promotion mt-1"
            :aria-label="t('products.promotionPriceAria', { price: formatPrice(getPromotionPriceAmount(product), siteCurrency) })"
          >
            {{ formatPrice(getPromotionPriceAmount(product), siteCurrency) }}
          </span>
          <span
            v-else
            class="theme-price-sm mt-1"
            :aria-label="t('products.priceAria', { price: formatPrice(product.price_amount, siteCurrency) })"
          >
            {{ formatPrice(product.price_amount, siteCurrency) }}
          </span>
          <div v-if="hasPromotionPrice(product)" class="mt-0.5 flex flex-wrap items-center gap-1.5">
            <span
              class="text-xs text-muted-foreground opacity-80 line-through"
              :aria-label="t('products.originalPriceAria', { price: formatPrice(product.price_amount, siteCurrency) })"
            >{{ formatPrice(product.price_amount, siteCurrency) }}</span>
            <span class="text-[11px] font-medium text-muted-foreground">{{ t('products.promotionTag') }}</span>
          </div>
          <div v-else-if="hasWholesalePrices(product)" class="mt-0.5 flex flex-wrap items-center gap-1.5">
            <span class="text-[11px] font-medium text-muted-foreground">{{ t('products.wholesaleTag') }}</span>
          </div>
          <div v-else-if="hasPromotionRules(product)" class="mt-0.5 flex flex-wrap items-center gap-1.5">
            <span class="text-[11px] font-medium text-muted-foreground">{{ t('products.promotionBadge') }}</span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="grid h-9 w-9 place-items-center rounded-xl border bg-card text-muted-foreground transition hover:border-hairline-strong hover:text-foreground"
            :aria-label="t('products.quickBuyAria')"
            :disabled="isSoldOut(product)"
            @click.stop="$emit('quickBuy', product)"
          >
            <ArrowRight class="h-4 w-4" />
          </button>
          <span class="hidden items-center gap-1 text-xs font-semibold text-muted-foreground transition-colors group-hover:text-foreground md:flex">
            {{ t('common.viewDetails') }} <ArrowRight class="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, ref, watch } from 'vue'
import { ArrowRight, Image as ImageIcon } from 'lucide-vue-next'
import { getFirstImageUrl, getImageUrl } from '../utils/image'
import { useLocalized, useProductLabels } from '../composables/useProduct'

const props = withDefaults(defineProps<{
  product: any
  index?: number
  maxTags?: number
  animationStep?: number
  accent?: string
}>(), {
  index: 0,
  maxTags: 2,
  animationStep: 50,
  accent: '',
})

defineEmits<{
  click: [slug: string]
  quickBuy: [product: any]
}>()

const { t } = useI18n()
const { getLocalizedText, siteCurrency, formatPrice } = useLocalized()
const { isSoldOut, hasPromotionPrice, getPromotionPriceAmount, hasPromotionRules, hasWholesalePrices } = useProductLabels()
const accentForProduct = computed(() => {
  const title = getLocalizedText(props.product?.title).toLowerCase()
  if (title.includes('claude')) return 'accent-warm'
  if (title.includes('gemini')) return 'accent-blue'
  if (title.includes('codex')) return 'accent-violet'
  return ['accent-teal', 'accent-blue', 'accent-violet'][(props.index ?? 0) % 3]
})

const imageErrored = ref(false)
const attemptIdx = ref(0)

const imageCandidates = computed<string[]>(() => {
  const arr: string[] = []
  const primary = getFirstImageUrl(props.product?.images)
  if (primary) arr.push(primary)
  const categoryIcon = props.product?.category?.icon
  if (categoryIcon) {
    const resolved = getImageUrl(categoryIcon)
    if (resolved && resolved !== primary) arr.push(resolved)
  }
  return arr
})

const displayImageSrc = computed(() => imageCandidates.value[attemptIdx.value] ?? '')

watch(imageCandidates, () => {
  attemptIdx.value = 0
  imageErrored.value = false
}, { deep: true })

const handleImageError = () => {
  if (attemptIdx.value < imageCandidates.value.length - 1) {
    attemptIdx.value++
  } else {
    imageErrored.value = true
  }
}
</script>

<style scoped>
.accent-teal, .accent-warm, .accent-blue, .accent-violet { position: relative; isolation: isolate; }
.accent-teal::before, .accent-warm::before, .accent-blue::before, .accent-violet::before { content: ''; position:absolute; width:190px; height:190px; right:-70px; top:-80px; border-radius:999px; filter:blur(38px); opacity:.28; z-index:-1; transition:opacity .25s ease; }
.accent-teal { --product-accent:#10a37f; --product-soft:rgba(16,163,127,.14); }
.accent-warm { --product-accent:#d97757; --product-soft:rgba(217,119,87,.14); }
.accent-blue { --product-accent:#4285f4; --product-soft:rgba(66,133,244,.14); }
.accent-violet { --product-accent:#8b5cf6; --product-soft:rgba(139,92,246,.14); }
.accent-teal::before { background:#10a37f; }
.accent-warm::before { background:#d97757; }
.accent-blue::before { background:#4285f4; }
.accent-violet::before { background:#8b5cf6; }
.accent-teal:hover::before, .accent-warm:hover::before, .accent-blue:hover::before, .accent-violet:hover::before { opacity:.42; }
.product-accent-dot { width:9px; height:9px; border-radius:999px; background:var(--product-accent); box-shadow:0 0 0 5px var(--product-soft); }
</style>
