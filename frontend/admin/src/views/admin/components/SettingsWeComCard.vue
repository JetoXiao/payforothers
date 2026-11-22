<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MessageCircle } from 'lucide-vue-next'
import { adminAPI } from '@/api/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { notifyError, notifySuccess } from '@/utils/notify'

const { t } = useI18n()
const emit = defineEmits<{ tested: [] }>()
const enabled = ref(false)
const savedEnabled = ref(false)
const hasWebhook = ref(false)
const webhook = ref('')
const busy = ref(false)
const loaded = ref(false)
const dirty = computed(() => webhook.value.trim() !== '' || enabled.value !== savedEnabled.value)
function accept(data: any) {
  const config = data?.channels?.wecom
  enabled.value = !!config?.enabled
  savedEnabled.value = enabled.value
  hasWebhook.value = !!config?.has_webhook
  webhook.value = ''
  loaded.value = true
}
async function save(clear = false) {
  if (clear && !window.confirm(t('wecom.clearConfirm'))) return
  if (!clear && enabled.value && !hasWebhook.value && !webhook.value.trim()) {
    notifyError(t('wecom.required')); return
  }
  busy.value = true
  try {
    const response = await adminAPI.updateNotificationCenterSettings({ channels: { wecom: {
      enabled: clear ? false : enabled.value, webhook: webhook.value.trim(), clear_webhook: clear,
    } } })
    accept(response.data?.data)
    notifySuccess(t('wecom.saved'))
  } catch { notifyError(t('wecom.failed')) } finally { busy.value = false }
}
async function test() {
  if (dirty.value) { notifyError(t('wecom.unsaved')); return }
  busy.value = true
  try {
    await adminAPI.testNotificationCenterSettings({ channel: 'wecom', target: 'configured-group', scene: 'order_created', locale: 'zh-CN' })
    notifySuccess(t('wecom.sent'))
    emit('tested')
  } catch { notifyError(t('wecom.failed')) } finally { busy.value = false }
}
onMounted(async () => {
  try { accept((await adminAPI.getNotificationCenterSettings()).data?.data) }
  catch { notifyError(t('wecom.failed')) }
})
</script>

<template>
  <section class="rounded-xl border border-border bg-card p-6" data-testid="wecom-settings">
    <div class="flex items-center gap-2"><MessageCircle class="h-5 w-5 text-emerald-600 dark:text-emerald-400" /><h2 class="text-lg font-semibold">{{ t('wecom.title') }}</h2></div>
    <p class="mt-2 max-w-4xl text-sm leading-relaxed text-muted-foreground">{{ t('wecom.description') }}</p>
    <p v-if="!loaded" class="mt-4 text-sm text-muted-foreground">{{ t('wecom.loading') }}</p>
    <fieldset :disabled="busy || !loaded" class="mt-5 space-y-4">
      <label class="flex items-center gap-2 text-sm font-medium"><input v-model="enabled" type="checkbox" class="h-4 w-4 accent-primary" />{{ t('wecom.enabled') }}</label>
      <div class="space-y-2">
        <label for="wecom-webhook" class="text-sm font-medium">{{ t('wecom.webhook') }}</label>
        <Input id="wecom-webhook" v-model="webhook" type="password" autocomplete="new-password" :spellcheck="false" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=…" />
        <p class="text-xs text-muted-foreground">{{ t(hasWebhook ? 'wecom.savedHook' : 'wecom.emptyHook') }}</p>
      </div>
      <div class="flex flex-wrap gap-3">
        <Button type="button" :disabled="busy || !loaded" @click="save()">{{ t('wecom.save') }}</Button>
        <Button type="button" variant="outline" :disabled="busy || !hasWebhook || dirty" @click="test">{{ t('wecom.test') }}</Button>
        <Button v-if="hasWebhook" type="button" variant="ghost" :disabled="busy" @click="save(true)">{{ t('wecom.clear') }}</Button>
      </div>
    </fieldset>
    <p class="mt-4 text-xs leading-relaxed text-muted-foreground">{{ t('wecom.privacy') }}</p>
  </section>
</template>
