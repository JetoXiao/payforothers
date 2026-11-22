import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAdminAuthStore } from './auth'
import { adminAPI } from '@/api/admin'

vi.mock('@/api/admin', () => ({ adminAPI: { getAuthzMe: vi.fn() } }))

describe('site administrator scope', () => {
  beforeEach(() => { localStorage.clear(); setActivePinia(createPinia()) })
  it('global wildcard policies cannot restore restricted menus', async () => {
    const store = useAdminAuthStore()
    store.token = 'test-token'
    vi.mocked(adminAPI.getAuthzMe).mockResolvedValue({ data: { data: { is_super: false, site_scope: { restricted: true, grants: [] }, policies: [{ action: '*', object: '/admin/*' }], roles: ['admin'] } } } as any)
    await store.loadAuthz()
    expect(store.siteRestricted).toBe(true)
    expect(store.hasPermission('GET:/admin/orders')).toBe(false)
    expect(store.hasPermission('GET:/admin/users')).toBe(false)
    expect(store.hasPermission('PUT:/admin/authz/admins/1')).toBe(false)
    expect(store.hasPermission('GET:/admin/site-console/scope')).toBe(true)
    expect(store.hasPermission('GET:/admin/2fa/status')).toBe(true)
  })
  it('the super administrator keeps all permissions and scope clears on logout', async () => {
    const store = useAdminAuthStore()
    store.token = 'test-token'
    vi.mocked(adminAPI.getAuthzMe).mockResolvedValue({ data: { data: { is_super: true, site_scope: { restricted: true }, policies: [], roles: [] } } } as any)
    await store.loadAuthz()
    expect(store.siteRestricted).toBe(false)
    expect(store.hasPermission('GET:/admin/orders')).toBe(true)
    store.clearAuthzCache()
    expect(store.hasPermission('GET:/admin/orders')).toBe(false)
  })
})
