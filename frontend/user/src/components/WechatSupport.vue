<template>
  <section v-if="accounts.length" data-testid="wechat-support" class="min-w-0" :aria-label="t('wechatSupport.title')">
    <h3 class="flex items-center gap-2 text-sm font-semibold text-foreground">
      <MessageCircle class="h-4 w-4 flex-none text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
      {{ t('wechatSupport.title') }}
    </h3>
    <p class="mt-1 text-xs leading-5 text-muted-foreground">{{ t('wechatSupport.hint') }}</p>
    <div class="mt-3 grid gap-2" :class="compact ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'">
      <button v-for="(account, index) in accounts" :key="account" type="button"
        data-testid="wechat-account" :data-account="account" :aria-label="t('wechatSupport.copyAccount', { account })"
        class="flex min-w-0 items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5 text-left transition hover:border-emerald-500/50 hover:bg-emerald-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        @click="copyAccount(account)">
        <span class="min-w-0 flex-1">
          <span v-if="accounts.length > 1" class="mb-0.5 block text-[11px] text-muted-foreground">{{ t('wechatSupport.agent', { index: index + 1 }) }}</span>
          <span class="block break-all text-sm font-medium text-foreground">{{ account }}</span>
        </span>
        <Copy class="h-3.5 w-3.5 flex-none text-emerald-700 dark:text-emerald-300" aria-hidden="true" />
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Copy, MessageCircle } from 'lucide-vue-next'
import { useWechatSupport } from '../composables/useWechatSupport'
import { copyText } from '../utils/clipboard'
import { toast } from '../composables/useToast'

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
const { t } = useI18n()
const { accounts } = useWechatSupport()
async function copyAccount(account: string) {
  try { await copyText(account); toast.success(t('wechatSupport.copied', { account })) }
  catch { toast.error(t('wechatSupport.copyFailed')) }
}
</script>
