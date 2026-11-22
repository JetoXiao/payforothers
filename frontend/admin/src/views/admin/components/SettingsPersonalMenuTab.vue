<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminAPI } from '@/api/admin'
import { notifyError, notifySuccess } from '@/utils/notify'

const { t } = useI18n()
const emit = defineEmits<{ saved: [] }>()
const keys = ['overview', 'orders', 'wallet', 'affiliate', 'reseller', 'giftCard', 'security', 'api', 'profile']
const selected = ref(['overview', 'orders', 'security', 'profile'])
const submitting = ref(false)
const loaded = ref(false)
onMounted(async () => {
  try {
    const response = await adminAPI.getSettings({ key: 'personal_menu_config' })
    const value = response.data?.data?.enabled_sections
    if (Array.isArray(value)) selected.value = keys.filter(key => value.includes(key))
    loaded.value = true
  } catch {
    notifyError(t('admin.settings.alerts.saveFailed'))
  }
})
async function save() {
  if (!loaded.value || submitting.value) return
  submitting.value = true
  try {
    await adminAPI.updateSettings({ key: 'personal_menu_config', value: { enabled_sections: selected.value } })
    notifySuccess(t('admin.settings.alerts.saveSuccess'))
    emit('saved')
  } catch {
    notifyError(t('admin.settings.alerts.saveFailed'))
  } finally { submitting.value = false }
}
defineExpose({ save, submitting })
</script>

<template>
  <section class="rounded-xl border border-border bg-card p-6">
    <h2 class="text-lg font-semibold">{{ t('storefrontControls.title') }}</h2>
    <p class="mt-2 text-sm leading-6 text-muted-foreground">{{ t('storefrontControls.description') }}</p>
    <div class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <label v-for="key in keys" :key="key" class="flex cursor-pointer items-center gap-3 rounded-xl border border-border p-4 text-sm hover:bg-muted/40">
        <input v-model="selected" :value="key" :disabled="!loaded || submitting" type="checkbox" class="size-4 accent-primary" />
        {{ t('storefrontControls.' + key) }}
      </label>
    </div>
  </section>
</template>
