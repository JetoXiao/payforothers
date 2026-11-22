<template>
  <footer class="border-t bg-card text-muted-foreground">
    <div class="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-7 text-xs sm:flex-row sm:px-6">
      <p>&copy; {{ new Date().getFullYear() }} {{ brandName }}. {{ t('footer.rights') }}</p>
      <nav class="flex items-center gap-6" :aria-label="t('legalPage.navigation')">
        <RouterLink to="/privacy" class="py-2 transition hover:text-foreground">{{ t('footer.privacy') }}</RouterLink>
        <RouterLink to="/terms" class="py-2 transition hover:text-foreground">{{ t('footer.terms') }}</RouterLink>
      </nav>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'

const { t } = useI18n()
const appStore = useAppStore()
const brandName = computed(() => String(appStore.config?.brand?.site_name || '').trim() || 'GptPayNow')
</script>
