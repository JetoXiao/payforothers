const terminalOrderStatuses = new Set(['delivered', 'completed', 'canceled', 'refunded'])

export const shouldPollAutoFulfillment = (order: any): boolean => {
  if (!order?.paid_at) return false

  const hasPendingFulfillment = (current: any): boolean => {
    if (!current || terminalOrderStatuses.has(String(current.status || ''))) return false

    const children = Array.isArray(current.children) ? current.children : []
    if (children.length > 0) return children.some(hasPendingFulfillment)

    const hasAutoItems = Array.isArray(current.items)
      && current.items.some((item: any) => ['auto', 'upstream'].includes(String(item?.fulfillment_type || '')))
    return hasAutoItems && current.fulfillment?.status !== 'delivered'
  }

  return hasPendingFulfillment(order)
}
