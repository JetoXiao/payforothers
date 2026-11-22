import { describe, expect, it } from 'vitest'
import { applySiteMenuPreset, matchSiteMenuPreset } from './sitePermissions'

describe('personal menu grants on the same site', () => {
  it('applying a preset to one person cannot modify another person or site', () => {
    const alice = { site_id: 1, overview: false, users: false, orders: true, visits: false }
    const bob = { ...alice }
    const otherSite = { ...alice, site_id: 2 }
    const finance = applySiteMenuPreset(alice, 'finance')
    expect(finance).toEqual({ site_id: 1, overview: true, users: false, orders: true, visits: false })
    expect(alice.overview).toBe(false)
    expect(bob.overview).toBe(false)
    expect(otherSite.overview).toBe(false)
    expect(matchSiteMenuPreset(finance)).toBe('finance')
  })
  it('supports independent custom menus and revocation', () => {
    const grant = { site_id: 1, overview: false, users: false, orders: true, visits: true }
    expect(matchSiteMenuPreset(grant)).toBe('custom')
    expect(matchSiteMenuPreset(applySiteMenuPreset(grant, 'support'))).toBe('support')
    expect(applySiteMenuPreset(grant, 'none')).toEqual({ site_id: 1, overview: false, users: false, orders: false, visits: false })
    expect(applySiteMenuPreset(grant, 'unknown')).toEqual(grant)
  })
})
