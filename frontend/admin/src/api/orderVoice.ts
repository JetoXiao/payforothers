import type { OrderVoiceRow } from '@/utils/orderVoice'
import { ORDER_VOICE_PAGE_SIZE } from '@/utils/orderVoice'

export class OrderVoiceRequestError extends Error {
  status: number
  constructor(status: number) { super('Order voice request failed'); this.status = status }
}

// Background polling must not trigger repeating global error toasts or perform
// mutations. HTTP/business auth failures are handled by the listener itself.
export async function getOrderVoicePage(token: string, page: number, signal: AbortSignal): Promise<OrderVoiceRow[]> {
  const query = new URLSearchParams({ page: String(page), page_size: String(ORDER_VOICE_PAGE_SIZE), sort_order: 'desc' })
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/admin/orders?${query}`, {
    headers: { Authorization: `Bearer ${token}` }, signal, cache: 'no-store',
  })
  if (!response.ok) throw new OrderVoiceRequestError(response.status)
  const payload = await response.json()
  if (payload.status_code !== 0) throw new OrderVoiceRequestError(Number(payload.status_code) || 500)
  if (!Array.isArray(payload.data)) throw new OrderVoiceRequestError(500)
  return payload.data.map((row: OrderVoiceRow) => ({ id: row.id, order_no: row.order_no, parent_id: row.parent_id }))
}
