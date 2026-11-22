<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { sitesAPI, type Site, type SiteGrant, type SiteScope, type SiteOverview, type SiteUser, type SiteOrder, type SiteVisit } from '@/api/sites'
import { adminAPI } from '@/api/admin'
import { applySiteMenuPreset, matchSiteMenuPreset, siteMenuPresets } from '@/utils/sitePermissions'

type Tab = 'overview' | 'users' | 'orders' | 'visits' | 'settings'
const scope = ref<SiteScope>({ restricted: true, is_super: false, grants: [], sites: [], base_domain: '' })
const selected = ref('')
const tab = ref<Tab>('overview')
const tabs: { id: Tab; name: string }[] = [{ id: 'overview', name: '经营统计' }, { id: 'users', name: '注册用户' }, { id: 'orders', name: '来源订单' }, { id: 'visits', name: '访问记录' }, { id: 'settings', name: '站点与管理员' }]
const day = (date: Date) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date)
const from = ref(day(new Date(Date.now() - 29 * 86400000)))
const to = ref(day(new Date()))
const keyword = ref('')
const status = ref('')
const page = ref(1)
const total = ref(0)
const overview = ref<SiteOverview | null>(null)
const users = ref<SiteUser[]>([])
const orders = ref<SiteOrder[]>([])
const visits = ref<SiteVisit[]>([])
const detail = ref<SiteOrder | null>(null)
const busy = ref(false)
const message = ref('')
const admins = ref<{ id: number; username: string; is_super: boolean }[]>([])
const adminID = ref('')
const selectedAdmin = computed(() => admins.value.find(admin => String(admin.id) === adminID.value))
const grants = ref<SiteGrant[]>([])
const grantsLoaded = ref(false)
let queryVersion = 0
let grantVersion = 0
let detailVersion = 0
const grantsForAdmin = ref('')
const editing = ref<Partial<Site>>({ name: '', domain: '', enabled: true })
const siteEditorOpen = ref(false)
const params = computed(() => ({ site_id: selected.value === '' ? undefined : Number(selected.value), from: from.value, to: to.value, keyword: keyword.value, status: status.value, page: page.value, page_size: 20 }))
const can = (menu: Tab) => scope.value.is_super || (menu !== 'settings' && scope.value.grants.some(g => g.site_id === Number(selected.value) && g[menu]))
const menus = computed(() => tabs.filter(t => can(t.id)))
const title = (value: Record<string, string>) => value['zh-CN'] || Object.values(value)[0] || ''
const fmt = (value: string) => new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
const clearData = () => { overview.value = null; users.value = []; orders.value = []; visits.value = []; detail.value = null; total.value = 0 }
async function load() {
  const version = ++queryVersion
  ++detailVersion
  clearData(); message.value = ''
  busy.value = false
  if (!can(tab.value)) tab.value = menus.value[0]?.id || 'overview'
  if (!can(tab.value) || tab.value === 'settings') return
  busy.value = true
  try {
    const currentTab = tab.value
    const currentParams = { ...params.value }
    if (currentTab === 'overview') {
      const res = await sitesAPI.overview(currentParams)
      if (version !== queryVersion) return
      overview.value = res.data.data
    } else {
      const res = await sitesAPI[currentTab](currentParams)
      if (version !== queryVersion) return
      total.value = res.data.pagination?.total || 0
      if (tab.value === 'users') users.value = res.data.data
      if (tab.value === 'orders') orders.value = res.data.data
      if (tab.value === 'visits') visits.value = res.data.data
    }
  } catch (e: any) { if (version === queryVersion) message.value = e.message || '加载失败' } finally { if (version === queryVersion) busy.value = false }
}
async function refreshScope() {
  scope.value = (await sitesAPI.scope()).data.data
  if (!scope.value.is_super && !scope.value.sites.some(s => String(s.id) === selected.value)) selected.value = String(scope.value.sites[0]?.id || '')
}
async function changeTab(value: Tab) { tab.value = value; page.value = 1; keyword.value = ''; status.value = ''; await load() }
async function search() { page.value = 1; await load() }
async function showOrder(row: SiteOrder) {
  const version = ++detailVersion
  const query = queryVersion
  message.value = ''; detail.value = null
  try { const res = await sitesAPI.order(row.id, { ...params.value }); if (version === detailVersion && query === queryVersion) detail.value = res.data.data } catch (e: any) { if (version === detailVersion && query === queryVersion) message.value = e.message }
}
async function saveSite() {
  if (busy.value) return
  message.value = ''; busy.value = true
  try { await sitesAPI.saveSite(editing.value); editing.value = { name: '', domain: '', enabled: true }; siteEditorOpen.value = false; await refreshScope(); message.value = '站点已保存；DNS 与证书仍需单独配置。' } catch (e: any) { message.value = e.message } finally { busy.value = false }
}
function openSiteEditor(site?: Site) { editing.value = site ? { ...site } : { name: '', domain: '', enabled: true }; siteEditorOpen.value = true }
function closeSiteEditor() { if (!busy.value) siteEditorOpen.value = false }
async function loadGrants() {
  const version = ++grantVersion
  const id = adminID.value
  grantsForAdmin.value = ''
  grantsLoaded.value = false; grants.value = []; message.value = ''
  if (!adminID.value) return
  try { const res = await sitesAPI.grants(Number(id)); if (version !== grantVersion || id !== adminID.value) return; grants.value = res.data.data.grants; grantsForAdmin.value = id; grantsLoaded.value = true } catch (e: any) { if (version === grantVersion) message.value = e.message }
}
function grant(site: Site): SiteGrant {
  let item = grants.value.find(g => g.site_id === site.id)
  if (!item) { item = { site_id: site.id, overview: false, users: false, orders: false, visits: false }; grants.value.push(item) }
  return item
}
function setMenuPreset(site: Site, event: Event) {
  const current = grant(site)
  Object.assign(current, applySiteMenuPreset(current, (event.target as HTMLSelectElement).value))
}
async function saveGrants() {
  if (!grantsLoaded.value || busy.value || grantsForAdmin.value !== adminID.value) return
  busy.value = true; message.value = ''
  try {
    await sitesAPI.saveGrants(Number(adminID.value), grants.value.filter(g => g.overview || g.users || g.orders || g.visits))
    message.value = `已保存 ${selectedAdmin.value?.username || adminID.value} 的个人菜单授权，立即生效。同一子站其他管理员的权限保持不变。`
  } catch (e: any) { message.value = e.message } finally { busy.value = false }
}
onMounted(async () => {
  try { await refreshScope(); if (scope.value.is_super) admins.value = (await adminAPI.listAuthzAdmins()).data.data.filter((a: any) => !a.is_super); await load() } catch (e: any) { message.value = e.message }
})
</script>

<template>
  <section class="site-console">
    <header class="page-header"><div class="heading-row"><div class="heading-icon">⌁</div><div><h1>子站工作台</h1><p>注册归属与下单归属分别记录，账号全站通用。当前统计和列表均来自主站数据。</p></div></div><div class="scope-badge">{{ scope.is_super ? '总管理员 · 全部来源' : `已授权 ${scope.sites.length} 个子站` }}</div></header>
    <p v-if="!scope.is_super && !scope.sites.length" class="notice">当前账号尚未分配站点或菜单，请联系总管理员。</p>
    <div class="filters filter-card">
      <label>站点<select v-model="selected" @change="search"><option v-if="scope.is_super" value="">全部来源</option><option v-if="scope.is_super" value="0">历史 / 未登记来源</option><option v-for="site in scope.sites" :key="site.id" :value="String(site.id)">{{ site.name }} · {{ site.domain }}{{ site.enabled ? '' : '（停用）' }}</option></select></label>
      <label>起始日期<input v-model="from" type="date" /></label><label>结束日期<input v-model="to" type="date" /></label>
      <button :disabled="busy" @click="search">{{ busy ? '加载中…' : '查询' }}</button>
    </div>
    <nav class="tab-bar"><button v-for="item in menus" :key="item.id" :class="{ active: tab === item.id }" @click="changeTab(item.id)">{{ item.name }}</button></nav>
    <p v-if="message" role="status" class="notice">{{ message }}</p>
    <template v-if="tab === 'overview' && overview">
      <div class="metrics"><article><small>本期注册用户</small><strong>{{ overview.registered_users }}</strong><span>按注册来源归属</span></article><article><small>独立浏览器访问</small><strong>{{ overview.browser_visits }}</strong><span>按站点与日期去重</span></article><article><small>统计币种</small><strong>{{ overview.by_currency.length }}</strong><span>订单金额分币种展示</span></article></div>
      <div class="table-card"><div class="table-caption"><div><h2>来源经营统计</h2><p>仅统计所选站点的主订单，金额按币种拆分。</p></div></div><div class="table-wrap"><table><thead><tr><th>币种</th><th>订单数</th><th>已付款</th><th>销售金额</th><th>退款</th><th>净收入</th><th>成本</th><th>手续费</th><th>估算毛利</th></tr></thead><tbody><tr v-for="row in overview.by_currency" :key="row.currency"><td><strong>{{ row.currency }}</strong></td><td>{{ row.orders }}</td><td>{{ row.paid_orders }}</td><td>{{ row.sales }}</td><td>{{ row.refunds }}</td><td>{{ row.net_revenue }}</td><td>{{ row.cost }}</td><td>{{ row.payment_fees }}</td><td class="profit">{{ row.profit }}</td></tr></tbody></table></div></div>
      <p v-if="!overview.by_currency.length">当前范围没有订单。</p>
      <p v-for="row in overview.by_currency.filter(r => r.missing_cost_orders > 0)" :key="row.currency" class="notice">{{ row.currency }} 中有 {{ row.missing_cost_orders }} 笔已付订单包含零成本商品，毛利可能高估，请核对成本。</p>
      <p class="muted">按订单创建日期统计截至现在的累计金额，仅计主订单，不重复计算拆单。净收入扣除退款及发票税额；成本使用订单项快照，退款不自动冲回成本。支付手续费仅计算商家承担部分并扣已退手续费。毛利不含人工、营销及其他税负，多币种分别统计。日期时区：Asia/Shanghai。</p>
    </template>
    <template v-if="tab === 'users' || tab === 'orders' || tab === 'visits'">
      <div v-if="tab !== 'visits'" class="filters"><input v-model="keyword" :placeholder="tab === 'orders' ? '搜索订单号' : '搜索注册邮箱或昵称'" @keyup.enter="search" /><select v-if="tab === 'orders'" v-model="status"><option value="">全部订单状态</option><option v-for="s in ['pending_payment', 'paid', 'fulfilling', 'delivered', 'completed', 'partially_refunded', 'refunded', 'canceled']" :key="s" :value="s">{{ s }}</option></select><button @click="search">搜索</button></div>
      <div class="table-card"><div class="table-wrap"><table v-if="tab === 'users'"><thead><tr><th>ID</th><th>注册邮箱</th><th>昵称</th><th>注册来源</th><th>注册时间</th></tr></thead><tbody><tr v-for="row in users" :key="row.id"><td>#{{ row.id }}</td><td>{{ row.email }}</td><td>{{ row.display_name || '-' }}</td><td><span class="source-tag">{{ row.registration_domain || '历史来源' }}</span></td><td>{{ fmt(row.created_at) }}</td></tr></tbody></table>
      <table v-if="tab === 'orders'"><thead><tr><th>订单</th><th>来源</th><th>用户类型</th><th>买家</th><th>状态</th><th>金额</th><th>退款</th><th>创建时间</th></tr></thead><tbody><tr v-for="row in orders" :key="row.id"><td><button @click="showOrder(row)">{{ row.order_no }}</button></td><td>{{ row.source_domain || '历史来源' }}</td><td><span class="user-type" :class="row.user_id ? 'registered' : 'guest'">{{ row.user_id ? '平台注册用户' : '游客订单' }}</span></td><td>{{ row.buyer_email || '-' }}</td><td>{{ row.status }}</td><td>{{ row.currency }} {{ row.total_amount }}</td><td>{{ row.refunded_amount }}</td><td>{{ fmt(row.created_at) }}</td></tr></tbody></table>
      <table v-if="tab === 'visits'"><thead><tr><th>站点域名</th><th>日期</th><th>关联用户 ID</th><th>首次访问</th><th>最后访问</th></tr></thead><tbody><tr v-for="row in visits" :key="row.id"><td>{{ row.domain }}</td><td>{{ row.day }}</td><td>{{ row.user_id || '匿名' }}</td><td>{{ fmt(row.first_seen_at) }}</td><td>{{ fmt(row.last_seen_at) }}</td></tr></tbody></table></div></div>
      <p v-if="!busy && total === 0">当前范围没有记录。</p><div class="filters"><button :disabled="page <= 1 || busy" @click="page--; load()">上一页</button><span>第 {{ page }} 页 · 共 {{ total }} 条</span><button :disabled="page * 20 >= total || busy" @click="page++; load()">下一页</button></div>
      <p v-if="tab === 'visits'" class="muted">同一浏览器、同一站点、同一天去重；这不是人数统计。清除 Cookie、换浏览器或设备会产生新的标识。仅记录本站访问，不显示用户在其他站点的记录。</p>
      <div v-if="detail" class="modal-backdrop" @click.self="detailVersion++; detail = null"><section class="modal-card order-modal"><div class="modal-header"><div><span class="eyebrow">来源订单详情</span><h2>{{ detail.order_no }}</h2></div><button class="icon-button" @click="detailVersion++; detail = null">×</button></div><div class="order-summary"><span>{{ detail.source_domain || '历史来源' }}</span><span class="user-type" :class="detail.user_id ? 'registered' : 'guest'">{{ detail.user_id ? '平台注册用户' : '游客订单' }}</span><span>{{ detail.status }}</span><strong>{{ detail.currency }} {{ detail.total_amount }}</strong></div><p class="muted">订单联系邮箱：{{ detail.buyer_email || '未提供' }}</p><div class="modal-items"><div v-for="(item, i) in detail.items" :key="i" class="item-row"><span>{{ title(item.title) }}</span><strong>× {{ item.quantity }}</strong></div><div v-if="!detail.items?.length" class="muted">暂无商品明细</div></div></section></div>
    </template>
    <template v-if="tab === 'settings' && scope.is_super">
      <div class="section-heading"><div><h2>站点与管理员</h2><p class="muted">域名创建后不可更改或复用。停用会保留历史数据，DNS、证书和反向代理需单独配置。</p></div><button class="primary-button" @click="openSiteEditor()">新增站点</button></div>
      <div class="table-card"><div class="table-wrap"><table><thead><tr><th>站点名称</th><th>访问域名</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="site in scope.sites" :key="site.id"><td><strong>{{ site.name }}</strong></td><td class="mono">{{ site.domain }}</td><td><span class="status-tag" :class="site.enabled ? 'enabled' : 'disabled'">{{ site.enabled ? '运行中' : '已停用' }}</span></td><td><button class="secondary-button" @click="openSiteEditor(site)">编辑站点</button></td></tr></tbody></table></div></div>
      <h2 class="subsection-title">管理员个人菜单授权</h2>
      <p class="muted">先在 <RouterLink to="/authz" class="permission-link">权限管理</RouterLink> 创建普通管理员，再选择具体账号配置菜单。同一子站可有多名管理员，每个人使用独立授权。例如 A 只看订单、B 看用户和订单、C 看经营统计。下列组合仅用于快速填写当前个人的勾选项，保存后可以继续自定义。</p>
      <label>管理员账号<select v-model="adminID" :disabled="busy" @change="loadGrants"><option value="">请选择</option><option v-for="admin in admins" :key="admin.id" :value="String(admin.id)">{{ admin.username }}（{{ admin.id }}）</option></select></label>
      <template v-if="grantsLoaded">
        <p>正在配置：<strong>{{ selectedAdmin?.username }}</strong>（ID {{ adminID }}）。仅修改此账号，其他管理员不受影响。</p>
        <div class="table-card"><div class="table-wrap"><table><thead><tr><th>站点</th><th>快速组合</th><th>经营统计</th><th>注册用户</th><th>来源订单</th><th>访问记录</th></tr></thead><tbody><tr v-for="site in scope.sites" :key="site.id"><td><strong>{{ site.name }}</strong><small class="muted mono">{{ site.domain }}</small></td><td><select :aria-label="`${site.domain} 的个人菜单组合`" :value="matchSiteMenuPreset(grant(site))" @change="setMenuPreset(site, $event)"><option value="custom" disabled>自定义</option><option v-for="preset in siteMenuPresets" :key="preset.id" :value="preset.id">{{ preset.label }}</option></select></td><td><input v-model="grant(site).overview" :aria-label="`${site.domain} 经营统计`" type="checkbox" /></td><td><input v-model="grant(site).users" :aria-label="`${site.domain} 注册用户`" type="checkbox" /></td><td><input v-model="grant(site).orders" :aria-label="`${site.domain} 来源订单`" type="checkbox" /></td><td><input v-model="grant(site).visits" :aria-label="`${site.domain} 访问记录`" type="checkbox" /></td></tr></tbody></table><button class="primary-button" :disabled="busy" @click="saveGrants">保存个人授权</button></div></div>
        <p class="muted">撤销某站点全部菜单即撤销该站授权。账号仍保持受限身份，不会自动恢复原有全局权限。</p>
      </template>
      <div v-if="siteEditorOpen" class="modal-backdrop" @click.self="closeSiteEditor"><section class="modal-card site-modal"><div class="modal-header"><div><span class="eyebrow">站点维护</span><h2>{{ editing.id ? '编辑站点' : '新增站点' }}</h2></div><button class="icon-button" @click="closeSiteEditor">×</button></div><div class="modal-form"><label>站点名称<input v-model="editing.name" maxlength="100" placeholder="例如：测试子站" /></label><label>访问域名<input v-model="editing.domain" :disabled="Boolean(editing.id)" :placeholder="`abc.${scope.base_domain}`" /></label><label class="checkbox-line"><input v-model="editing.enabled" type="checkbox" />启用站点</label></div><div class="modal-actions"><button class="secondary-button" :disabled="busy" @click="closeSiteEditor">取消</button><button class="primary-button" :disabled="busy || !editing.name || !editing.domain" @click="saveSite">{{ busy ? '保存中…' : '保存修改' }}</button></div></section></div>
    </template>
  </section>
</template>

<style scoped>
.site-console { display: grid; gap: 18px; max-width: 1500px; margin: 0 auto; min-width: 0; }
.page-header { display:flex; align-items:center; justify-content:space-between; gap:16px; } .heading-row { display:flex; gap:12px; align-items:flex-start; } .heading-icon { display:grid; place-items:center; width:40px; height:40px; border-radius:12px; background:#0f766e; color:white; font-size:24px; } h1 { font-size: 27px; font-weight: 750; letter-spacing:-.02em; } h2 { font-size: 19px; font-weight: 700; } .scope-badge { border:1px solid #99f6e4; background:#f0fdfa; color:#0f766e; border-radius:999px; padding:7px 11px; font-size:12px; white-space:nowrap; }
header p,.muted { color: hsl(var(--muted-foreground)); line-height: 1.7; font-size: 13px; } .filter-card,.table-card { border:1px solid hsl(var(--border)); border-radius:14px; background:hsl(var(--card)); box-shadow:0 8px 24px #0f172a0a; padding:14px; }
.filters,nav { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; } label { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; font-size: 13px; } input:not([type=checkbox]),select,button { border: 1px solid hsl(var(--border)); border-radius: 9px; padding: 8px 11px; background: hsl(var(--background)); color: hsl(var(--foreground)); font: inherit; } button { cursor: pointer; } button:hover:not(:disabled) { background: hsl(var(--secondary)); } button:disabled { cursor: default; opacity: .45; } .tab-bar { border-bottom:1px solid hsl(var(--border)); gap:4px; } .tab-bar button { border-color:transparent; border-radius:9px 9px 0 0; color:hsl(var(--muted-foreground)); } .tab-bar .active { background: #0f766e; color: white; border-color: #0f766e; }
.table-wrap { overflow: auto; min-width: 0; } input:focus-visible,select:focus-visible,button:focus-visible { outline: 2px solid #0f766e; outline-offset: 2px; } table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; } th,td { text-align: left; padding: 12px; border-bottom: 1px solid hsl(var(--border)); } th { font-weight: 650; color:hsl(var(--muted-foreground)); background:hsl(var(--muted)/.28); font-size:11px; text-transform:uppercase; letter-spacing:.03em; } tbody tr:hover { background:hsl(var(--muted)/.18); } tbody tr:last-child td { border-bottom:0; }
.notice { background: #b4530915; border-left: 3px solid #b45309; padding: 12px 16px; line-height: 1.7; }
.permission-link { text-decoration: underline; text-underline-offset: 3px; }
.metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; } .metrics article,.detail { padding: 16px; border: 1px solid hsl(var(--border)); border-radius: 12px; background:hsl(var(--card)); } .metrics small,.metrics span { color:hsl(var(--muted-foreground)); font-size:12px; } .metrics strong { display: block; font-size: 28px; margin-top: 8px; } .metrics span { display:block; margin-top:4px; } .table-caption,.section-heading { padding:4px 4px 12px; } .table-caption h2,.section-heading h2 { margin:0; } .table-caption p { margin:4px 0 0; color:hsl(var(--muted-foreground)); font-size:12px; } .profit { color:#047857; font-weight:650; } .source-tag,.status-tag { display:inline-flex; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:600; } .source-tag { background:#f1f5f9; color:#475569; } .status-tag.enabled { color:#047857; background:#ecfdf5; } .status-tag.disabled { color:#64748b; background:#f1f5f9; } .mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; } .subsection-title { margin-top:8px; }
.secondary-button,.primary-button { border-radius:9px; } .primary-button { background:#0f766e; color:#fff; border-color:#0f766e; } .primary-button:hover:not(:disabled) { background:#115e59; }
.table-card { padding:0; overflow:hidden; } .table-card .table-wrap { padding:0; } .table-card > .table-wrap + .filters { padding:12px; } .table-card > .table-wrap + .pagination { padding:12px; }
.section-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
.user-type { display:inline-flex; align-items:center; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:650; white-space:nowrap; } .user-type.registered { color:#1d4ed8; background:#eff6ff; } .user-type.guest { color:#a16207; background:#fefce8; }
.modal-backdrop { position:fixed; inset:0; z-index:60; display:grid; place-items:center; padding:20px; background:rgb(15 23 42 / .44); backdrop-filter:blur(3px); }
.modal-card { width:min(100%, 640px); max-height:min(86vh, 760px); overflow:auto; border:1px solid hsl(var(--border)); border-radius:18px; background:hsl(var(--card)); box-shadow:0 24px 80px rgb(15 23 42 / .28); padding:22px; }
.modal-header { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; border-bottom:1px solid hsl(var(--border)); padding-bottom:15px; } .modal-header h2 { margin-top:4px; font-size:20px; } .eyebrow { color:#0f766e; font-size:11px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; } .icon-button { width:32px; height:32px; padding:0; border-radius:9px; font-size:22px; line-height:1; color:hsl(var(--muted-foreground)); }
.order-summary { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:16px 0 11px; font-size:13px; color:hsl(var(--muted-foreground)); } .order-summary strong { margin-left:auto; color:hsl(var(--foreground)); font-size:16px; } .modal-items { display:grid; gap:9px; margin-top:16px; border-top:1px solid hsl(var(--border)); padding-top:14px; } .item-row { display:flex; justify-content:space-between; gap:16px; padding:11px 12px; border-radius:10px; background:hsl(var(--muted)/.28); font-size:13px; } .site-modal { width:min(100%, 520px); } .modal-form { display:grid; gap:15px; padding:20px 0; } .modal-form label { display:grid; gap:7px; align-items:stretch; } .modal-form input:not([type=checkbox]) { width:100%; } .checkbox-line { display:flex !important; align-items:center !important; flex-direction:row; } .modal-actions { display:flex; justify-content:flex-end; gap:9px; border-top:1px solid hsl(var(--border)); padding-top:15px; }
@media (max-width:720px) { .page-header { align-items:flex-start; flex-direction:column; } .scope-badge { align-self:flex-start; } .metrics { grid-template-columns:1fr; } }
</style>
