<template>
  <nav
    class="fixed left-0 right-0 top-0 z-50 border-b bg-background/90 backdrop-blur-md transition-all"
    :class="scrolled ? 'py-2' : 'py-3'"
    :style="{ transitionDuration: 'var(--ui-duration-normal)' }">
    <div class="container mx-auto flex max-w-7xl items-center justify-between gap-2 px-4 sm:gap-4 sm:px-6">
      <!-- Logo -->
      <router-link to="/" class="group relative inline-flex min-w-0 items-center gap-3" :title="brandSiteName">
        <img
          :src="brandLogo"
          :alt="brandSiteName"
          class="h-8 max-w-[180px] shrink-0 object-contain"
        />
        <span class="truncate text-[15px] font-semibold tracking-[-0.02em] text-foreground">{{ brandSiteName }}</span>
      </router-link>

      <div class="flex shrink-0 items-center justify-center gap-2 lg:flex-1">
        <router-link to="/tutorials/chatgpt-recharge" class="inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-xl border border-cyan-300 bg-cyan-300 px-3 text-xs font-semibold text-slate-950 shadow-sm transition hover:bg-cyan-200 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-cyan-500 sm:px-5 sm:text-sm">
          <BookOpen class="h-4 w-4 shrink-0" /> {{ t('nav.tutorial') }}
        </router-link>
        <a v-if="redemptionUrl" :href="redemptionUrl" target="_blank" rel="noopener noreferrer" class="inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-xl border border-blue-200 bg-blue-50 px-3 text-xs font-semibold text-blue-700 shadow-sm transition hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-500 dark:border-blue-400/40 dark:bg-blue-400/10 dark:text-blue-200 sm:px-5 sm:text-sm">
          <TicketCheck class="h-4 w-4 shrink-0" /> {{ t('nav.redemption') }}
        </a>
        <router-link v-if="downloadsEnabled" to="/downloads" class="inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-xl border border-violet-200 bg-violet-50 px-3 text-xs font-semibold text-violet-700 shadow-sm transition hover:bg-violet-100 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet-500 dark:border-violet-400/40 dark:bg-violet-400/10 dark:text-violet-200 sm:px-5 sm:text-sm" active-class="!bg-violet-200/70 dark:!bg-violet-400/20">
          <Download class="h-4 w-4 shrink-0" /> {{ t('nav.downloads') }}
        </router-link>
      </div>

      <!-- Right Side Actions -->
      <div class="flex items-center shrink-0 space-x-0 sm:space-x-2 lg:space-x-4">
        <Button v-if="!userAuthStore.isAuthenticated" as-child variant="ghost" size="sm"
          class="hidden lg:inline-flex gap-1.5 text-muted-foreground whitespace-nowrap">
          <router-link to="/guest/orders">
            <ClipboardList class="w-4 h-4 shrink-0 opacity-70" />
            {{ t('navbar.guestOrders') }}
          </router-link>
        </Button>
        <Button v-if="!userAuthStore.isAuthenticated" as-child variant="ghost" size="sm"
          class="hidden lg:inline-flex gap-1.5 text-muted-foreground whitespace-nowrap">
          <router-link to="/auth/login">
            <LogIn class="w-4 h-4 shrink-0 opacity-70" />
            {{ t('navbar.login') }}
          </router-link>
        </Button>
        <Button v-if="userAuthStore.isAuthenticated" as-child variant="ghost" size="sm"
          class="hidden lg:inline-flex gap-1.5 text-muted-foreground whitespace-nowrap">
          <router-link to="/me">
            <User class="w-4 h-4 shrink-0 opacity-70" />
            {{ t('navbar.personalCenter') }}
          </router-link>
        </Button>
        <Button v-if="userAuthStore.isAuthenticated" variant="ghost" size="sm"
          class="hidden lg:inline-flex gap-1.5 whitespace-nowrap text-destructive hover:text-destructive hover:bg-destructive/10"
          @click="userAuthStore.logout()">
          <LogOut class="w-4 h-4 shrink-0 opacity-70" />
          {{ t('navbar.logout') }}
        </Button>
        <!-- Theme Switcher -->
        <Button variant="ghost" size="icon" class="text-muted-foreground" @click="toggleTheme">
          <Sun v-if="theme === 'dark'" class="w-4 h-4" />
          <Moon v-else class="w-4 h-4" />
        </Button>

        <!-- Language Switcher (Desktop) -->
        <Popover v-model:open="langOpen">
          <PopoverTrigger as-child>
            <Button variant="ghost" size="sm" class="hidden lg:inline-flex gap-2 text-muted-foreground">
              <Languages class="w-4 h-4" />
              <span class="text-xs font-medium uppercase tracking-wider">{{ currentLocale }}</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" class="w-40 p-2">
            <div class="px-2 pb-2 mb-2 border-b">
              <span class="text-xs text-muted-foreground font-mono px-2">{{ t('navbar.selectLanguage') }}</span>
            </div>
            <button v-for="lang in languages" :key="lang.code" @click="changeLanguage(lang.code)"
              class="w-full text-left px-3 py-2.5 text-sm rounded-md transition-colors flex items-center justify-between hover:bg-accent hover:text-accent-foreground"
              :class="{ 'text-primary': appStore.locale === lang.code }">
              {{ lang.name }}
              <span v-if="appStore.locale === lang.code" class="w-1.5 h-1.5 rounded-full bg-primary"></span>
            </button>
          </PopoverContent>
        </Popover>

        <!-- Mobile Menu Button (more menu, not main nav) -->
        <Button variant="ghost" size="icon" class="lg:hidden text-muted-foreground [&_svg]:size-5"
          @click="toggleMobileMenu">
          <EllipsisVertical />
        </Button>
      </div>
    </div>

  </nav>

  <!-- Teleport drawer outside nav to avoid backdrop-filter containing block bug -->
  <Teleport to="body">
    <!-- Mobile Drawer Overlay -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0">
      <div v-if="showMobileMenu" class="lg:hidden fixed inset-0 z-[60] bg-black/50" @click="showMobileMenu = false" style="overscroll-behavior: none;"></div>
    </Transition>

    <!-- Mobile Drawer (only items NOT in bottom nav) -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full">
      <div v-if="showMobileMenu"
        class="lg:hidden fixed right-0 top-0 bottom-0 z-[70] w-72 max-w-[80vw] bg-card/95 backdrop-blur-xl border-l overflow-y-auto"
        style="overscroll-behavior: none;">
        <div class="p-5 space-y-1">
          <!-- Header -->
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{{ t('navbar.more') }}</span>
            <Button variant="secondary" size="icon" class="[&_svg]:size-5" @click="showMobileMenu = false">
              <X />
            </Button>
          </div>

          <!-- Recharge guide -->
          <Button as-child variant="ghost"
            class="w-full justify-start gap-3 h-auto py-3 rounded-xl text-sm font-semibold text-cyan-600 hover:bg-cyan-400/10 dark:text-cyan-300 [&_svg]:size-5">
            <router-link to="/tutorials/chatgpt-recharge" @click="showMobileMenu = false" active-class="!bg-cyan-400/15">
              <BookOpen class="shrink-0" />
              {{ t('nav.tutorial') }}
            </router-link>
          </Button>
          <a v-if="redemptionUrl" :href="redemptionUrl" target="_blank" rel="noopener noreferrer" class="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-400/10 dark:text-blue-300" @click="showMobileMenu = false">
            <TicketCheck class="shrink-0" /> {{ t('nav.redemption') }}
          </a>
          <router-link v-if="downloadsEnabled" to="/downloads" class="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-violet-600 transition hover:bg-violet-400/10 dark:text-violet-300" active-class="!bg-violet-400/15" @click="showMobileMenu = false">
            <Download class="shrink-0" /> {{ t('nav.downloads') }}
          </router-link>

          <!-- Guest orders (not in bottom nav) -->
          <Button v-if="!userAuthStore.isAuthenticated" as-child variant="ghost"
            class="w-full justify-start gap-3 h-auto py-3 rounded-xl text-sm text-muted-foreground [&_svg]:size-5">
            <router-link to="/guest/orders" @click="showMobileMenu = false" active-class="!text-primary !bg-primary/10">
              <ClipboardList class="shrink-0 opacity-60" />
              {{ t('navbar.guestOrders') }}
            </router-link>
          </Button>

          <!-- Logout (login/me already in bottom nav) -->
          <Button v-if="userAuthStore.isAuthenticated" variant="ghost"
            class="w-full justify-start gap-3 h-auto py-3 rounded-xl text-sm text-destructive hover:text-destructive hover:bg-destructive/10 [&_svg]:size-5"
            @click="userAuthStore.logout(); showMobileMenu = false">
            <LogOut class="shrink-0 opacity-60" />
            {{ t('navbar.logout') }}
          </Button>

          <!-- Language Switcher -->
          <div class="mt-4 pt-4 border-t">
            <span class="text-xs text-muted-foreground font-semibold uppercase tracking-wider px-4">{{ t('navbar.selectLanguage') }}</span>
            <div class="mt-2 space-y-1">
              <button v-for="lang in languages" :key="lang.code" @click="changeLanguage(lang.code)"
                class="w-full text-left px-4 py-2.5 rounded-xl text-sm transition-colors min-h-[44px] flex items-center justify-between"
                :class="appStore.locale === lang.code
                  ? 'text-primary font-semibold'
                  : 'text-muted-foreground hover:text-foreground'">
                {{ lang.name }}
                <span v-if="appStore.locale === lang.code"
                  class="w-1.5 h-1.5 rounded-full bg-primary"></span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../stores/app'
import { useUserAuthStore } from '../stores/userAuth'
import { useTheme } from '../utils/theme'
import { getImageUrl } from '../utils/image'
import {
  Sun, Moon, ClipboardList, LogIn, User, LogOut, Languages, BookOpen,
  EllipsisVertical, X, TicketCheck, Download,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

const { t } = useI18n()
const appStore = useAppStore()
const userAuthStore = useUserAuthStore()
const { theme, toggleTheme } = useTheme()

const showMobileMenu = ref(false)
const langOpen = ref(false)
const scrolled = ref(false)

const languages = [
  { code: 'zh-CN', name: '简体中文' },
  { code: 'zh-TW', name: '繁體中文' },
  { code: 'en-US', name: 'English' },
]

const currentLocale = computed(() => {
  const lang = languages.find(l => l.code === appStore.locale)
  if (!lang) return 'CN'
  return lang.code === 'en-US' ? 'EN' : (lang.code === 'zh-CN' ? '简' : '繁')
})


const brandSiteName = computed(() => {
  const text = String(appStore.config?.brand?.site_name || '').trim()
  return text !== '' ? text : 'GptPayNow'
})

const brandLogo = computed(() => {
  const raw = String(appStore.config?.brand?.site_logo || '').trim()
  return raw ? getImageUrl(raw) : '/gptpaynow.svg'
})
const redemptionUrl = computed(() => String(appStore.config?.brand?.redemption_url || '').trim())
const downloadsEnabled = computed(() => appStore.config?.downloads?.enabled !== false)

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
}

const changeLanguage = (langCode: string) => {
  appStore.setLocale(langCode)
  langOpen.value = false
}

const handleScroll = () => {
  scrolled.value = window.scrollY > 20
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
