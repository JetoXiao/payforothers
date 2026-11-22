import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'
import { normalizeWechatAccounts, replaceLegacyWechatContact } from '../utils/wechatSupport'

export function useWechatSupport() {
  const appStore = useAppStore()
  const { t } = useI18n()
  const accounts = computed(() => normalizeWechatAccounts(appStore.config?.contact?.wechat))
  const hasWechatSupport = computed(() => accounts.value.length > 0)
  const productSupportHtml = (html: string) => replaceLegacyWechatContact(html, t(hasWechatSupport.value ? 'wechatSupport.productContact' : 'wechatSupport.orderContact'))
  return { accounts, hasWechatSupport, productSupportHtml }
}
