export function normalizeWechatAccounts(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const seen = new Set<string>()
  const result: string[] = []
  for (const item of value) {
    if (typeof item !== 'string') continue
    const account = item.trim()
    const key = account.toLowerCase()
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(account) || seen.has(key)) continue
    seen.add(key)
    result.push(account)
    if (result.length === 20) break
  }
  return result
}

// Existing imported descriptions had this fixed contact. Render a pointer to
// the configured contact block instead, without changing the stored product.
export function replaceLegacyWechatContact(html: string, label: string): string {
  const safeLabel = label.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
  return html.replace(/GptPayNow\s+(?:微信客服\s+|WeChat support:\s*)think-more-9/gi, () => safeLabel)
}
