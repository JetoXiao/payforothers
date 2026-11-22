import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAdminAuthStore } from '@/stores/auth'
import { ADMIN_BASE } from '@/utils/adminBase'
import { getOrderVoicePage, OrderVoiceRequestError } from '@/api/orderVoice'
import { normalizeVoicePreferences, readVoiceJSON, pollOrderVoice, voiceAdminId, ORDER_VOICE_POLL_MS } from '@/utils/orderVoice'
import type { OrderVoiceStorage } from '@/utils/orderVoice'
import newOrderZh from '@/assets/audio/new-order-zh.wav?url'
import enabledZh from '@/assets/audio/order-voice-enabled-zh.wav?url'
import newOrderEn from '@/assets/audio/new-order-en.wav?url'
import enabledEn from '@/assets/audio/order-voice-enabled-en.wav?url'

export function useOrderVoice() {
  const auth = useAdminAuthStore()
  const { locale } = useI18n()
  const adminId = computed(() => voiceAdminId(auth.token))
  const canListen = computed(() => !!adminId.value && auth.permissionsLoaded && auth.hasPermission('GET:/admin/orders'))
  const enabled = ref(false)
  const volume = ref(0.8)
  const ready = ref(false)
  const issue = ref('')
  const received = ref(0)
  const latestId = ref(0)
  const latestOrderNo = ref('')
  const lastChecked = ref<number | null>(null)
  const initializing = ref(false)
  const audioBlocked = ref(false)
  let audio: HTMLAudioElement | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined
  let mounted = false
  let generation = 0
  let playGeneration = 0
  let key = ''
  // Storage can be disabled by browser policy; still work for this tab.
  const memory = new Map<string, string>()
  const storage: OrderVoiceStorage = {
    getItem: k => { try { return localStorage.getItem(k) } catch { return memory.get(k) ?? null } },
    setItem: (k,v) => { try { localStorage.setItem(k,v) } catch { memory.set(k,v) } },
  }
  const status = computed(() => !enabled.value ? 'off' : issue.value || (audioBlocked.value ? 'blocked' : !ready.value ? 'activate' : initializing.value ? 'initializing' : 'listening'))

  function persist() { if (key) storage.setItem(key, JSON.stringify({ enabled: enabled.value, volume: volume.value })) }
  function stop() {
    generation++
    clearTimeout(timer)
    timer = undefined
    controller?.abort()
    controller = undefined
    playGeneration++
    if (audio) { audio.pause(); audio.currentTime = 0 }
    ready.value = false
    initializing.value = false
  }
  async function play(test: boolean): Promise<boolean> {
    if (!audio) return false
    const id = ++playGeneration
    audio.pause()
    audio.src = locale.value.startsWith('en') ? (test ? enabledEn : newOrderEn) : (test ? enabledZh : newOrderZh)
    audio.volume = volume.value
    audio.currentTime = 0
    try {
      await audio.play()
      if (id !== playGeneration) return false
      audioBlocked.value = false
      return true
    } catch {
      if (id === playGeneration) audioBlocked.value = true
      return false
    }
  }
  async function tick(run: number) {
    if (!mounted || run !== generation || !canListen.value || !enabled.value || !ready.value) return
    let delay = ORDER_VOICE_POLL_MS
    const work = async () => {
      if (!mounted || run !== generation || !canListen.value || !enabled.value || !ready.value) return
      controller = new AbortController()
      const requestController = controller
      const timeout = setTimeout(() => requestController.abort(), 25_000)
      try {
        const result = await pollOrderVoice(storage, key + ':cursor', page => getOrderVoicePage(auth.token, page, requestController.signal), Date.now,
          () => mounted && run === generation && canListen.value && enabled.value && ready.value)
        if (run !== generation) return
        lastChecked.value = Date.now()
        issue.value = ''
        initializing.value = false
        if (result.orders.length) {
          received.value += result.orders.length
          latestId.value = result.orders[0]!.id
          latestOrderNo.value = result.orders[0]!.order_no
          await play(false)
        }
      } finally { clearTimeout(timeout); if (controller === requestController) controller = undefined }
    }
    try {
      if (navigator.locks) await navigator.locks.request(key + ':lock', { ifAvailable: true }, async lock => { if (lock) await work() })
      else await work()
    } catch (error) {
      if (run !== generation) return
      initializing.value = false
      if (error instanceof OrderVoiceRequestError && [401,403].includes(error.status)) {
        issue.value = 'unauthorized'
        stop()
        return
      }
      issue.value = 'reconnecting'
      delay = 30_000
    } finally {
      if (mounted && run === generation && enabled.value && ready.value) timer = setTimeout(() => void tick(run), delay)
    }
  }
  async function activate() {
    if (!canListen.value) return
    // Call play directly from the button gesture; no await/API before it.
    const activeToken = auth.token
    const played = await play(true)
    if (!mounted || activeToken !== auth.token || !enabled.value || !played) return
    if (ready.value) return
    ready.value = true
    issue.value = ''
    initializing.value = true
    const run = ++generation
    void tick(run)
  }
  function toggle(value: boolean) {
    enabled.value = value
    persist()
    issue.value = ''
    audioBlocked.value = false
    if (value) void activate()
    else stop()
  }
  function setVolume(value: number) {
    volume.value = normalizeVoicePreferences({ volume: value }).volume
    if (audio) audio.volume = volume.value
    persist()
  }
  function loadPreferences() {
    stop()
    key = adminId.value ? `gptpaynow:order-voice:v1:${ADMIN_BASE}:${adminId.value}` : ''
    const prefs = normalizeVoicePreferences(readVoiceJSON(storage, key))
    enabled.value = prefs.enabled
    volume.value = prefs.volume
    received.value = 0
    latestId.value = 0
    latestOrderNo.value = ''
    lastChecked.value = null
    audioBlocked.value = false
    issue.value = ''
  }
  function onStorage(event: StorageEvent) {
    if (event.key === key) {
      const prefs = normalizeVoicePreferences(readVoiceJSON(storage, key))
      volume.value = prefs.volume
      if (audio) audio.volume = prefs.volume
      if (enabled.value && !prefs.enabled) stop()
      enabled.value = prefs.enabled
    }
  }
  function resume() {
    if (document.visibilityState === 'visible' && ready.value && enabled.value && !controller) {
      clearTimeout(timer)
      void tick(generation)
    }
  }
  watch(() => auth.token, () => { if (mounted) loadPreferences() })
  watch(canListen, allowed => { if (!allowed) stop() })
  onMounted(() => {
    mounted = true
    audio = new Audio()
    audio.preload = 'auto'
    audio.src = locale.value.startsWith('en') ? newOrderEn : newOrderZh
    loadPreferences()
    window.addEventListener('storage', onStorage)
    document.addEventListener('visibilitychange', resume)
    window.addEventListener('online', resume)
  })
  onBeforeUnmount(() => {
    mounted = false
    stop()
    if (audio) { audio.removeAttribute('src'); audio.load(); audio = null }
    window.removeEventListener('storage', onStorage)
    document.removeEventListener('visibilitychange', resume)
    window.removeEventListener('online', resume)
  })
  return { canListen, enabled, volume, ready, status, received, latestId, latestOrderNo, lastChecked, toggle, activate, setVolume, clearReceived: () => { received.value = 0 } }
}
