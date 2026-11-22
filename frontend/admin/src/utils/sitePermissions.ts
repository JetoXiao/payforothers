import type { SiteGrant } from '@/api/sites'

export const siteMenuKeys = ['overview', 'users', 'orders', 'visits'] as const
export type SiteMenuKey = typeof siteMenuKeys[number]
export const siteMenuPresets = [
  { id: 'operations', label: '运营查看', menus: ['overview', 'users', 'orders', 'visits'] },
  { id: 'support', label: '订单客服', menus: ['users', 'orders'] },
  { id: 'finance', label: '财务查看', menus: ['overview', 'orders'] },
  { id: 'users', label: '用户查看', menus: ['users'] },
  { id: 'none', label: '无权限', menus: [] },
] as const

// Presets only copy checkbox values to the selected person's grant. They are
// not shared roles, so editing one person's menus never changes another's.
export function applySiteMenuPreset(grant: SiteGrant, presetID: string): SiteGrant {
  const preset = siteMenuPresets.find(p => p.id === presetID)
  if (!preset) return { ...grant }
  const menus = new Set<string>(preset.menus)
  return { ...grant, ...Object.fromEntries(siteMenuKeys.map(key => [key, menus.has(key)])) }
}

export function matchSiteMenuPreset(grant: SiteGrant): string {
  return siteMenuPresets.find(p => siteMenuKeys.every(key => grant[key] === (p.menus as readonly string[]).includes(key)))?.id || 'custom'
}
