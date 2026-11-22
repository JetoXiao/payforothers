import { api } from './client'

export interface Site { id: number; name: string; domain: string; enabled: boolean; certificate_status?: string; certificate_expires_at?: string; certificate_error?: string; certificate_requested_at?: string }
export interface SiteGrant { site_id: number; overview: boolean; users: boolean; orders: boolean; visits: boolean }
export interface SiteScope { restricted: boolean; is_super: boolean; grants: SiteGrant[]; sites: Site[]; base_domain: string }
export interface SiteUser { id: number; email: string; display_name: string; registration_domain: string; created_at: string }
export interface SiteOrder { id: number; order_no: string; source_domain: string; user_id: number; buyer_email: string; currency: string; total_amount: string; refunded_amount: string; status: string; created_at: string; items?: { title: Record<string, string>; quantity: number }[] }
export interface SiteVisit { id: number; domain: string; day: string; user_id: number; first_seen_at: string; last_seen_at: string }
export interface SiteOverview { registered_users: number; browser_visits: number; by_currency: { currency: string; orders: number; paid_orders: number; missing_cost_orders: number; sales: string; refunds: string; net_revenue: string; cost: string; payment_fees: string; profit: string }[] }
export const sitesAPI = {
  scope: () => api.get('/admin/site-console/scope'),
  sites: () => api.get('/admin/sites'),
  saveSite: (data: Partial<Site>) => data.id ? api.put(`/admin/sites/${data.id}`, data) : api.post('/admin/sites', data),
  requestCertificate: (id: number) => api.post(`/admin/sites/${id}/certificate`),
  certificate: (id: number) => api.get(`/admin/sites/${id}/certificate`),
  grants: (id: number) => api.get(`/admin/sites/admins/${id}/grants`),
  saveGrants: (id: number, grants: SiteGrant[]) => api.put(`/admin/sites/admins/${id}/grants`, { grants }),
  overview: (params: Record<string, unknown>) => api.get('/admin/site-console/overview', { params }),
  users: (params: Record<string, unknown>) => api.get('/admin/site-console/users', { params }),
  orders: (params: Record<string, unknown>) => api.get('/admin/site-console/orders', { params }),
  order: (id: number, params: Record<string, unknown>) => api.get(`/admin/site-console/orders/${id}`, { params }),
  visits: (params: Record<string, unknown>) => api.get('/admin/site-console/visits', { params }),
}
