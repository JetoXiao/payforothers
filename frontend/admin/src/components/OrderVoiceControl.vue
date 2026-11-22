<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { BellRing, Volume2, VolumeX } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useOrderVoice } from '@/composables/useOrderVoice'

const { t } = useI18n()
const router = useRouter()
const open = ref(false)
const { canListen, enabled, volume, ready, status, received, latestId, latestOrderNo, toggle, activate, setVolume, clearReceived } = useOrderVoice()
function viewOrders() {
  clearReceived()
  open.value = false
  router.push({ path: '/orders', query: latestId.value ? { order_id: String(latestId.value) } : {} })
}
</script>

<template>
  <Popover v-if="canListen" v-model:open="open">
    <PopoverTrigger as-child>
      <Button size="sm" variant="outline" class="relative gap-2" data-testid="order-voice-control" :aria-label="t('orderVoice.title')" :title="t('orderVoice.states.' + status)">
        <Volume2 v-if="enabled && ready" class="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        <VolumeX v-else class="h-4 w-4" />
        <span class="hidden xl:inline">{{ t('orderVoice.title') }}</span>
        <span v-if="received" data-testid="order-voice-count" class="absolute -right-1 -top-2 rounded-full bg-primary px-1.5 text-[10px] text-primary-foreground">{{ received > 99 ? '99+' : received }}</span>
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-[340px] max-w-[calc(100vw-24px)] space-y-4 rounded-xl p-4" data-testid="order-voice-panel">
      <div class="flex items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 font-semibold"><BellRing class="h-4 w-4" />{{ t('orderVoice.title') }}</h2>
        <label class="flex cursor-pointer items-center gap-2 text-sm">
          <input type="checkbox" class="h-4 w-4 accent-primary" :checked="enabled" :aria-label="t('orderVoice.enable')" data-testid="order-voice-enabled" @change="toggle(($event.target as HTMLInputElement).checked)" />
          {{ t('orderVoice.enable') }}
        </label>
      </div>
      <p class="text-xs leading-5 text-muted-foreground">{{ t('orderVoice.description') }}</p>
      <p role="status" data-testid="order-voice-status" :data-status="status" class="rounded-lg bg-secondary px-3 py-2 text-xs leading-5">{{ t('orderVoice.states.' + status) }}</p>
      <div class="space-y-2">
        <label for="order-voice-volume" class="flex justify-between text-xs"><span>{{ t('orderVoice.volume') }}</span><span>{{ Math.round(volume * 100) }}%</span></label>
        <input id="order-voice-volume" type="range" min="0" max="100" step="5" :value="Math.round(volume * 100)" class="w-full accent-primary" @input="setVolume(Number(($event.target as HTMLInputElement).value) / 100)" />
      </div>
      <Button :disabled="!enabled" variant="outline" class="w-full" data-testid="order-voice-test" @click="activate">{{ t(ready ? 'orderVoice.test' : 'orderVoice.activate') }}</Button>
      <div v-if="received" class="space-y-1 break-all text-sm" role="status">
        <p>{{ t('orderVoice.received', { count: received }) }}</p>
        <p class="text-xs text-muted-foreground">{{ latestOrderNo }}</p>
      </div>
      <Button class="w-full" data-testid="order-voice-orders" @click="viewOrders">{{ t('orderVoice.viewOrders') }}</Button>
      <p class="text-[11px] leading-5 text-muted-foreground">{{ t('orderVoice.limitations') }}</p>
    </PopoverContent>
  </Popover>
</template>
