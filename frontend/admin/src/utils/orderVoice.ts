export const ORDER_VOICE_POLL_MS = 15_000
export const ORDER_VOICE_SHARED_TTL_MS = 90_000
export const ORDER_VOICE_PAGE_SIZE = 100

export interface OrderVoicePreferences { enabled: boolean; volume: number }
export interface OrderVoiceRow { id: number; order_no: string; parent_id?: number | null }
export interface OrderVoiceCursor { id: number; checkedAt: number }
export interface OrderVoiceStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export function normalizeVoicePreferences(raw: unknown): OrderVoicePreferences {
  const value = raw as Partial<OrderVoicePreferences> | null
  return {
    enabled: value?.enabled === true,
    volume: typeof value?.volume === 'number' && Number.isFinite(value.volume) ? Math.max(0, Math.min(1, value.volume)) : 0.8,
  }
}

export function readVoiceJSON(storage: OrderVoiceStorage, key: string): unknown {
  try { return JSON.parse(storage.getItem(key) || 'null') } catch { return null }
}

export function readVoiceCursor(storage: OrderVoiceStorage, key: string, now: number): OrderVoiceCursor | null {
  const value = readVoiceJSON(storage, key) as OrderVoiceCursor | null
  if (!value || !Number.isSafeInteger(value.id) || value.id < 0 || !Number.isFinite(value.checkedAt)) return null
  const age = now - value.checkedAt
  return age >= 0 && age < ORDER_VOICE_SHARED_TTL_MS ? value : null
}

// Used for UI storage namespacing only. Authorization remains server-side.
export function voiceAdminId(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!.replace(/-/g, '+').replace(/_/g, '/')))
    return Number.isSafeInteger(payload.admin_id) && payload.admin_id > 0 ? String(payload.admin_id) : null
  } catch { return null }
}

export async function scanNewOrders(
  load: (page: number) => Promise<OrderVoiceRow[]>,
  cursor: number | null,
): Promise<{ id: number; orders: OrderVoiceRow[] }> {
  const found = new Map<number, OrderVoiceRow>()
  let newest = cursor ?? 0
  for (let page = 1; page <= 20; page++) {
    const rows = await load(page)
    if (!Array.isArray(rows) || rows.some(row => !Number.isSafeInteger(row.id) || row.id <= 0 || typeof row.order_no !== 'string')) {
      throw new Error('Invalid order response')
    }
    const parents = rows.filter(row => row.parent_id == null || row.parent_id === 0)
    for (const row of parents) newest = Math.max(newest, row.id)
    // A fresh listener establishes a baseline, even when the store is empty.
    if (cursor === null) return { id: newest, orders: [] }
    for (const row of parents) if (row.id > cursor) found.set(row.id, row)
    if (rows.length < ORDER_VOICE_PAGE_SIZE || parents.some(row => row.id <= cursor)) {
      return { id: newest, orders: [...found.values()].sort((a, b) => b.id - a.id) }
    }
  }
  // Never advance the cursor after a truncated/failed scan.
  throw new Error('Order scan limit reached')
}

export async function pollOrderVoice(
  storage: OrderVoiceStorage,
  key: string,
  load: (page: number) => Promise<OrderVoiceRow[]>,
  now: () => number,
  isActive: () => boolean,
): Promise<{ skipped: boolean; id: number; orders: OrderVoiceRow[] }> {
  const cursor = readVoiceCursor(storage, key, now())
  if (cursor && now() - cursor.checkedAt < ORDER_VOICE_POLL_MS - 500) return { skipped: true, id: cursor.id, orders: [] }
  const result = await scanNewOrders(load, cursor?.id ?? null)
  if (!isActive()) return { skipped: true, id: result.id, orders: [] }
  // Re-read before committing for duplicate suppression if Web Locks is absent.
  const concurrent = readVoiceCursor(storage, key, now())
  const threshold = Math.max(cursor?.id ?? 0, concurrent?.id ?? 0)
  const orders = result.orders.filter(order => order.id > threshold)
  storage.setItem(key, JSON.stringify({ id: Math.max(result.id, threshold), checkedAt: now() }))
  return { skipped: false, id: result.id, orders }
}
