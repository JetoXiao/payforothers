<template>
  <section class="downloads-admin">
    <header class="hero">
      <div><span class="eyebrow">DOWNLOAD DELIVERY</span><h1>资源下载管理</h1><p>配置 Cloudflare R2、上传公开资源并查看下载统计。</p></div>
      <button class="primary" @click="resourceOpen = true">＋ 添加资源</button>
    </header>

    <div class="metrics">
      <article><small>资源总数</small><strong>{{ resources.length }}</strong></article>
      <article><small>已发布</small><strong>{{ publishedCount }}</strong></article>
      <article><small>累计下载</small><strong>{{ totalDownloads }}</strong></article>
      <article><small>存储状态</small><strong class="ok">{{ r2Configured ? '已配置' : '未配置' }}</strong></article>
    </div>

    <section class="panel">
      <div class="panel-head"><div><h2>R2 下载存储</h2><p>凭据仅保存在服务器设置中；Secret 保存后不会回显，但测试连接会自动复用。</p></div><span class="badge" :class="r2Configured ? 'good' : 'warn'">{{ r2Configured ? '已配置' : '未配置' }}</span></div>
      <div class="grid">
        <label>S3 API 端点<input v-model="r2.endpoint" placeholder="https://account.r2.cloudflarestorage.com" /></label>
        <label>存储桶<input v-model="r2.bucket" placeholder="downloads" /></label>
        <label>Access Key ID<input v-model="r2.access_key_id" autocomplete="off" /></label>
        <label>Secret Access Key<input v-model="r2.secret_access_key" type="password" :placeholder="r2.secret_saved ? '已保存，留空保持不变' : '必须填写 Secret Access Key'" autocomplete="new-password" /></label>
        <label>区域<input v-model="r2.region" placeholder="auto" /></label>
        <label class="check-field"><input v-model="r2.use_path_style" type="checkbox" /> 使用 Path-style S3 地址</label>
        <label class="wide">浏览器上传 CORS 配置<textarea v-model="r2.cors" rows="7" placeholder='[{"AllowedOrigins":["https://www.gptpaynow.com"],"AllowedMethods":["GET","PUT"],"AllowedHeaders":["*"]}]' /></label>
      </div>
      <div v-if="missingFields.length" class="missing"><strong>还缺少：</strong><span v-for="field in missingFields" :key="field">{{ field }}</span></div>
      <p v-if="message" class="message" :class="messageKind">{{ message }}</p>
      <div class="actions"><button class="secondary" :disabled="saving" @click="testR2">测试连接</button><button class="primary" :disabled="saving" @click="saveR2">{{ saving ? '保存中…' : '保存配置' }}</button></div>
    </section>

    <section class="panel"><div class="panel-head"><div><h2>下载资源</h2><p>发布后的资源会在前台资源下载页展示。</p></div><button class="secondary" @click="load">刷新</button></div>
      <div class="table-wrap"><table><thead><tr><th>资源</th><th>平台</th><th>大小</th><th>更新时间</th><th>下载次数</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="row in resources" :key="row.id"><td><strong>{{ row.title?.['zh-CN'] || row.slug }}</strong><small>{{ row.version }} · {{ row.file_key }}</small></td><td>{{ row.platform || '通用' }}</td><td>{{ row.size || '-' }}</td><td>{{ formatDate(row.updated_at) }}</td><td>{{ row.download_count }}</td><td><span class="badge good" v-if="row.published">已发布</span><span class="badge warn" v-else>草稿</span></td><td><button class="icon" @click="edit(row)">编辑</button><button class="icon danger" @click="remove(row)">删除</button></td></tr><tr v-if="!resources.length"><td colspan="7" class="empty">暂无资源，点击右上角添加。</td></tr></tbody></table></div>
    </section>

    <div v-if="resourceOpen" class="backdrop" @click.self="resourceOpen=false"><section class="modal"><div class="modal-head"><div><h2>{{ editing.id ? '编辑资源' : '添加资源' }}</h2><p>上传文件后填写展示信息；文件会保存到 R2 对象前缀。</p></div><button class="icon" @click="resourceOpen=false">×</button></div><div class="upload-box"><label>安装包文件<input type="file" @change="onFile" /></label><small>选择文件后会自动读取文件名和大小；上传动作在保存资源时执行。</small></div><div class="grid"><label>唯一标识<input v-model="editing.slug" placeholder="ai-starter-kit" /></label><label>版本<input v-model="editing.version" placeholder="v1.0.0" /></label><label>中文名称<input v-model="editing.title.zhCN" placeholder="资源名称" /></label><label>英文名称<input v-model="editing.title.enUS" placeholder="Resource name" /></label><label>平台<input v-model="editing.platform" placeholder="Windows / macOS / Linux" /></label><label>排序权重<input v-model.number="editing.sort_order" type="number" /></label><label class="wide">中文简介<textarea v-model="editing.description.zhCN" rows="2" /></label><label class="wide">英文简介<textarea v-model="editing.description.enUS" rows="2" /></label><label class="wide">R2 对象键<input v-model="editing.file_key" placeholder="downloads/file.zip" /></label><label>下载文件名<input v-model="editing.download_name" placeholder="file.zip" /></label><label>内容类型<input v-model="editing.content_type" placeholder="application/octet-stream" /></label><label>SHA-256<input v-model="editing.sha256" /></label></div><label class="check"><input v-model="editing.published" type="checkbox" /> 已发布</label><div class="modal-actions"><button class="secondary" @click="resourceOpen=false">取消</button><button class="primary" :disabled="saving" @click="saveResource">保存</button></div></section></div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { adminAPI } from '@/api/admin'

type Resource = { id?: number; slug: string; title: Record<string, string>; description: Record<string, string>; platform?: string; version?: string; file_key?: string; download_name?: string; content_type?: string; sha256?: string; size?: string; updated_at?: string; download_count: number; published: boolean; sort_order?: number }
const resources = ref<Resource[]>([])
const resourceOpen = ref(false); const saving = ref(false)
const r2 = reactive({ endpoint: '', bucket: '', access_key_id: '', secret_access_key: '', secret_saved: false, region: 'auto', use_path_style: true, cors: '' })
const message = ref(''); const messageKind = ref<'ok' | 'error'>('ok')
const editing = reactive<any>({ id: 0, slug: '', title: { zhCN: '', enUS: '' }, description: { zhCN: '', enUS: '' }, platform: '', version: '', file_key: '', download_name: '', content_type: 'application/octet-stream', sha256: '', published: true, sort_order: 0, file: null })
const missingFields = computed(() => [
  !r2.endpoint ? 'S3 API 端点' : '', !r2.bucket ? '存储桶' : '', !r2.access_key_id ? 'Access Key ID' : '', !(r2.secret_access_key || r2.secret_saved) ? 'Secret Access Key' : '', !r2.cors ? 'CORS 配置' : '',
].filter(Boolean))
const r2Configured = computed(() => missingFields.value.length === 0)
const publishedCount = computed(() => resources.value.filter(item => item.published).length)
const totalDownloads = computed(() => resources.value.reduce((sum, item) => sum + Number(item.download_count || 0), 0))
const load = async () => { const [settings, list] = await Promise.all([adminAPI.getDownloadConfig(), adminAPI.getDownloadResources()]); Object.assign(r2, settings.data.data?.r2 || {}); resources.value = list.data.data || [] }
const saveR2 = async () => { message.value = ''; if (missingFields.value.length) { messageKind.value = 'error'; message.value = `请先填写：${missingFields.value.join('、')}`; return } saving.value = true; try { await adminAPI.updateDownloadConfig({ r2: { ...r2 } }); messageKind.value = 'ok'; message.value = 'R2 配置已保存。'; await load() } catch (error: any) { messageKind.value = 'error'; message.value = error?.message || '保存失败' } finally { saving.value = false } }
const testR2 = async () => { message.value = ''; if (missingFields.value.length) { messageKind.value = 'error'; message.value = `请先填写：${missingFields.value.join('、')}`; return } saving.value = true; try { await adminAPI.testDownloadStorage({ ...r2 }); messageKind.value = 'ok'; message.value = '连接测试成功。' } catch (error: any) { messageKind.value = 'error'; message.value = error?.message || '连接测试失败，请检查端点、存储桶、密钥和权限。' } finally { saving.value = false } }
const resetEditing = () => Object.assign(editing, { id: 0, slug: '', title: { zhCN: '', enUS: '' }, description: { zhCN: '', enUS: '' }, platform: '', version: '', file_key: '', download_name: '', content_type: 'application/octet-stream', sha256: '', published: true, sort_order: 0, file: null })
const edit = (row: Resource) => { Object.assign(editing, { ...row, title: { zhCN: row.title?.['zh-CN'] || '', enUS: row.title?.['en-US'] || '' }, description: { zhCN: row.description?.['zh-CN'] || '', enUS: row.description?.['en-US'] || '' } }); resourceOpen.value = true }
const onFile = (event: Event) => { editing.file = (event.target as HTMLInputElement).files?.[0] || null; if (editing.file && !editing.file_key) editing.file_key = `downloads/${editing.file.name}` }
const saveResource = async () => { saving.value = true; try { const data = { ...editing, title: { 'zh-CN': editing.title.zhCN, 'en-US': editing.title.enUS }, description: { 'zh-CN': editing.description.zhCN, 'en-US': editing.description.enUS } }; delete data.file; await adminAPI.saveDownloadResource(data, editing.file); resourceOpen.value = false; resetEditing(); await load() } finally { saving.value = false } }
const remove = async (row: Resource) => { if (row.id && window.confirm(`确认删除资源 ${row.slug}？`)) { await adminAPI.deleteDownloadResource(row.id); await load() } }
const formatDate = (value?: string) => value ? new Date(value).toLocaleDateString('zh-CN') : '-'
onMounted(load)
</script>

<style scoped>
.missing{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:14px;padding:11px 13px;border:1px solid #fde68a;border-radius:10px;background:#fffbeb;color:#92400e;font-size:12px}.missing span{padding:3px 7px;border-radius:999px;background:#fef3c7;font-weight:650}.message{margin:12px 0 0;padding:10px 12px;border-radius:9px;font-size:12px}.message.ok{color:#047857;background:#ecfdf5}.message.error{color:#b91c1c;background:#fef2f2}
.downloads-admin{display:grid;gap:18px;max-width:1480px;margin:0 auto}.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;padding:4px 2px}.eyebrow{color:#0f766e;font-size:11px;font-weight:700;letter-spacing:.12em}.hero h1{margin:6px 0 3px;font-size:28px}.hero p,.panel-head p{margin:0;color:hsl(var(--muted-foreground));font-size:13px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.metrics article{padding:18px;border:1px solid hsl(var(--border));border-radius:14px;background:hsl(var(--card));box-shadow:0 10px 28px rgb(15 23 42 / .06)}.metrics small{display:block;color:hsl(var(--muted-foreground));font-size:12px}.metrics strong{display:block;margin-top:8px;font-size:28px}.metrics .ok{color:#059669}.panel{border:1px solid hsl(var(--border));border-radius:16px;background:hsl(var(--card));box-shadow:0 10px 28px rgb(15 23 42 / .05);padding:20px}.panel-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:16px}.panel h2{margin:0 0 5px;font-size:19px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.grid label{display:grid;gap:6px;font-size:12px;color:hsl(var(--muted-foreground))}.grid input,.grid textarea{width:100%;box-sizing:border-box;border:1px solid hsl(var(--border));border-radius:9px;padding:9px 10px;background:hsl(var(--background));color:inherit;font:inherit}.wide{grid-column:span 3}.actions,.modal-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:16px}.primary,.secondary,.icon{border:1px solid hsl(var(--border));border-radius:9px;padding:9px 13px;background:hsl(var(--background));color:inherit;cursor:pointer}.primary{background:#0f766e;color:white;border-color:#0f766e}.badge{display:inline-flex;border-radius:999px;padding:4px 8px;font-size:11px;font-weight:650}.badge.good{color:#047857;background:#ecfdf5}.badge.warn{color:#a16207;background:#fffbeb}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px;font-size:13px}th,td{padding:12px;border-bottom:1px solid hsl(var(--border));text-align:left}th{font-size:11px;color:hsl(var(--muted-foreground));background:hsl(var(--muted)/.25)}td small{display:block;margin-top:3px;color:hsl(var(--muted-foreground));font-size:11px}.danger{color:#dc2626}.empty{text-align:center;padding:40px;color:hsl(var(--muted-foreground))}.backdrop{position:fixed;inset:0;z-index:60;display:grid;place-items:center;padding:20px;background:rgb(15 23 42 / .45)}.modal{width:min(100%,900px);max-height:90vh;overflow:auto;border-radius:18px;background:hsl(var(--card));padding:22px}.modal-head{display:flex;justify-content:space-between;gap:16px;margin-bottom:16px}.modal-head h2{margin:0 0 4px}.upload-box{border:1px dashed #5eead4;border-radius:12px;padding:14px;margin-bottom:16px;background:#f0fdfa}.upload-box label{display:flex;justify-content:space-between;align-items:center;font-weight:650;color:#0f766e}.upload-box small{display:block;margin-top:7px;color:hsl(var(--muted-foreground));font-size:12px}.check{display:flex;align-items:center;gap:7px;margin-top:14px;font-size:13px}@media(max-width:900px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.wide{grid-column:span 2}}@media(max-width:560px){.metrics,.grid{grid-template-columns:1fr}.wide{grid-column:span 1}.hero{align-items:flex-start;flex-direction:column}}
</style>
