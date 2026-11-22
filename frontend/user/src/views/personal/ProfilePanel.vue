<template>
  <div class="rounded-2xl border bg-card p-7 shadow-sm">
    <PanelHeading :title="t('personalCenter.profile.title')" :description="t('personalCenter.profile.subtitle')" :icon="UserCircle">
      <template #actions>
        <Badge variant="accent" size="sm">{{ t('personalCenter.tabs.profile') }}</Badge>
      </template>
    </PanelHeading>

    <Alert v-if="profileAlert" class="mb-5" :variant="pageAlertVariant(profileAlert.level)" :class="pageAlertToneClass(profileAlert.level)">
      <AlertDescription>{{ profileAlert.message }}</AlertDescription>
    </Alert>

    <form class="space-y-6" @submit.prevent="handleSaveProfile">
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div class="md:col-span-2">
          <Label class="mb-2 block">{{ t('personalCenter.profile.emailLabel') }}</Label>
          <Input :model-value="userProfileStore.profile?.email || ''" disabled class="h-11" />
        </div>

        <div>
          <Label class="mb-2 block">{{ t('personalCenter.profile.nicknameLabel') }}</Label>
          <Input
            v-model="profileForm.nickname"
            :placeholder="t('personalCenter.profile.nicknamePlaceholder')"
            class="h-11"
          />
        </div>

        <div>
          <Label class="mb-2 block">{{ t('personalCenter.profile.localeLabel') }}</Label>
          <Select v-model="profileForm.locale">
            <SelectTrigger class="h-11 w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zh-CN">简体中文</SelectItem>
              <SelectItem value="zh-TW">繁體中文</SelectItem>
              <SelectItem value="en-US">English</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div class="flex flex-col gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p class="text-xs text-muted-foreground">{{ t('personalCenter.profile.subtitle') }}</p>
        <Button type="submit" :disabled="userProfileStore.savingProfile" class="h-11 font-bold">
          {{ userProfileStore.savingProfile ? t('personalCenter.profile.saving') : t('personalCenter.profile.save') }}
        </Button>
      </div>
    </form>

    <section class="mt-8 border-t pt-7">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-foreground">{{ t('personalCenter.invoice.title') }}</h2>
          <p class="mt-1 text-sm text-muted-foreground">{{ t('personalCenter.invoice.subtitle') }}</p>
        </div>
        <Button type="button" variant="secondary" @click="startNewInvoiceProfile">{{ t('personalCenter.invoice.add') }}</Button>
      </div>
      <p v-if="invoiceError" role="alert" class="mt-4 text-sm text-danger">{{ invoiceError }}</p>
      <div class="mt-4 space-y-3">
        <div v-if="invoiceProfiles.length === 0" class="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">{{ t('personalCenter.invoice.empty') }}</div>
        <div v-for="profile in invoiceProfiles" :key="profile.id" class="rounded-xl border p-4">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div><p class="font-semibold">{{ profile.name }} <span v-if="profile.is_default" class="text-xs text-primary">{{ t('personalCenter.invoice.default') }}</span></p><p class="mt-1 text-xs text-muted-foreground">{{ profile.taxpayer_id }} · {{ profile.email }}</p></div>
            <div class="flex gap-2"><Button size="sm" variant="outline" @click="editInvoiceProfile(profile)">{{ t('invoice.edit') }}</Button><Button size="sm" variant="ghost" @click="removeInvoiceProfile(profile.id)">{{ t('invoice.remove') }}</Button></div>
          </div>
        </div>
      </div>
      <p class="mt-4 text-xs text-muted-foreground">{{ t('invoice.specialFields') }}</p>
      <form v-if="invoiceFormVisible" class="mt-5 grid gap-3 rounded-xl border bg-secondary p-4 md:grid-cols-2" @submit.prevent="saveInvoiceProfile">
        <Input v-model="invoiceForm.name" :aria-label="t('personalCenter.invoice.name')" :placeholder="t('personalCenter.invoice.name')" required />
        <Input v-model="invoiceForm.taxpayer_id" :aria-label="t('personalCenter.invoice.taxpayerId')" :placeholder="t('personalCenter.invoice.taxpayerId')" required />
        <Input v-model="invoiceForm.address" :aria-label="t('personalCenter.invoice.address')" :placeholder="t('personalCenter.invoice.address')" />
        <Input v-model="invoiceForm.phone" :aria-label="t('personalCenter.invoice.phone')" :placeholder="t('personalCenter.invoice.phone')" />
        <Input v-model="invoiceForm.bank_name" :aria-label="t('personalCenter.invoice.bankName')" :placeholder="t('personalCenter.invoice.bankName')" />
        <Input v-model="invoiceForm.bank_account" :aria-label="t('personalCenter.invoice.bankAccount')" :placeholder="t('personalCenter.invoice.bankAccount')" />
        <Input v-model="invoiceForm.email" type="email" :placeholder="t('personalCenter.invoice.email')" required />
        <label class="flex items-center gap-2 text-sm"><input v-model="invoiceForm.is_default" type="checkbox" class="accent-primary" />{{ t('personalCenter.invoice.default') }}</label>
        <div class="flex gap-2 md:col-span-2"><Button type="submit" :disabled="invoiceBusy">{{ t('personalCenter.invoice.save') }}</Button><Button type="button" variant="secondary" @click="invoiceFormVisible=false">{{ t('common.cancel') }}</Button></div>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { UserCircle } from 'lucide-vue-next'
import { pageAlertVariant, pageAlertToneClass, type PageAlert } from '../../utils/alerts'
import { useUserProfileStore } from '../../stores/userProfile'
import { userOrderAPI } from '../../api'
import PanelHeading from '../../components/shared/PanelHeading.vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const { t } = useI18n()
const userProfileStore = useUserProfileStore()

const profileForm = reactive({
  nickname: '',
  locale: 'zh-CN',
})

const profileAlert = ref<PageAlert | null>(null)
const invoiceProfiles = ref<any[]>([])
const invoiceError = ref('')
const invoiceBusy = ref(false)
const invoiceFormVisible = ref(false)
const editingInvoiceId = ref<number | null>(null)
const invoiceForm = reactive({name:'',taxpayer_id:'',address:'',phone:'',bank_name:'',bank_account:'',email:'',is_default:false})
const loadInvoiceProfiles = async () => { try { invoiceProfiles.value = (await userOrderAPI.invoiceProfiles()).data.data || [] } catch (err:any) { invoiceError.value=err.message || t('invoice.loadFailed') } }
const startNewInvoiceProfile = () => { editingInvoiceId.value=null; Object.assign(invoiceForm,{name:'',taxpayer_id:'',address:'',phone:'',bank_name:'',bank_account:'',email:userProfileStore.profile?.email || '',is_default:false}); invoiceFormVisible.value=true }
const editInvoiceProfile = (profile:any) => { editingInvoiceId.value=profile.id; Object.assign(invoiceForm,profile); invoiceFormVisible.value=true }
const saveInvoiceProfile = async () => {
  if (invoiceBusy.value) return
  invoiceBusy.value=true;invoiceError.value=''
  try {
    const payload={...invoiceForm}
    if(editingInvoiceId.value) await userOrderAPI.updateInvoiceProfile(editingInvoiceId.value,payload)
    else await userOrderAPI.createInvoiceProfile(payload)
    invoiceFormVisible.value=false;await loadInvoiceProfiles()
  } catch(err:any){invoiceError.value=err.message || t('invoice.saveFailed')}
  finally{invoiceBusy.value=false}
}
const removeInvoiceProfile = async (id:number) => {
  if(invoiceBusy.value || !confirm(t('invoice.deleteConfirm'))) return
  invoiceBusy.value=true;invoiceError.value=''
  try{await userOrderAPI.deleteInvoiceProfile(id);await loadInvoiceProfiles()}
  catch(err:any){invoiceError.value=err.message || t('invoice.saveFailed')}
  finally{invoiceBusy.value=false}
}

const handleSaveProfile = async () => {
  profileAlert.value = null
  const payload = { nickname: profileForm.nickname.trim(), locale: profileForm.locale }
  const ok = await userProfileStore.saveProfile(payload)
  profileAlert.value = ok
    ? { level: 'success', message: t('personalCenter.profile.saveSuccess') }
    : { level: 'error', message: userProfileStore.profileError || t('personalCenter.common.saveFailed') }
}

watch(
  () => userProfileStore.profile,
  (profile) => {
    if (!profile) return
    profileForm.nickname = profile.nickname || ''
    profileForm.locale = profile.locale || 'zh-CN'
  },
  { immediate: true },
)

onMounted(loadInvoiceProfiles)
</script>
