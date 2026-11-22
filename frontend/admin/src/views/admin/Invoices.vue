<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold">发票处理</h1>
        <p class="mt-1 text-sm text-muted-foreground">人工开具并发送至用户预留邮箱；完成后订单不可重复申请。</p>
      </div>
      <Button variant="outline" @click="load">刷新</Button>
    </div>
    <Card>
      <CardContent class="p-0">
        <Table>
          <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>用户 / 邮箱</TableHead><TableHead>金额</TableHead><TableHead>状态</TableHead><TableHead>创建时间</TableHead><TableHead class="text-right">操作</TableHead></TableRow></TableHeader>
          <TableBody>
            <TableRow v-for="row in rows" :key="row.id">
              <TableCell class="font-mono">#{{ row.id }}</TableCell>
              <TableCell><div class="font-medium">{{ row.profile_snapshot?.name || '-' }}</div><div class="text-xs text-muted-foreground">{{ row.email }}</div></TableCell>
              <TableCell class="font-mono">{{ row.tax_base_amount }} + {{ row.tax_amount }} {{ row.currency }}</TableCell>
              <TableCell>{{ statusLabel(row.status) }}</TableCell>
              <TableCell>{{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}</TableCell>
              <TableCell class="text-right">
                <div v-if="row.status === 'processing'" class="flex flex-wrap justify-end gap-2">
                  <Input v-model="drafts[row.id]" class="h-9 w-40" placeholder="发票号码" />
                  <Button size="sm" :disabled="busyId === row.id || !drafts[row.id]" @click="markIssued(row)">已人工发送</Button>
                </div>
                <span v-else class="text-xs text-muted-foreground">{{ row.invoice_number || '—' }}</span>
              </TableCell>
            </TableRow>
            <TableRow v-if="!loading && rows.length === 0"><TableCell colspan="6" class="py-12 text-center text-muted-foreground">暂无开票申请</TableCell></TableRow>
            <TableRow v-if="loading"><TableCell colspan="6" class="py-12 text-center text-muted-foreground">加载中…</TableCell></TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
    <div class="flex justify-end gap-3 text-sm">
      <Button variant="outline" :disabled="page <= 1" @click="changePage(page - 1)">上一页</Button>
      <span class="self-center text-muted-foreground">第 {{ page }} / {{ totalPage }} 页</span>
      <Button variant="outline" :disabled="page >= totalPage" @click="changePage(page + 1)">下一页</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { adminAPI } from '@/api/admin'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const rows = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const totalPage = ref(1)
const busyId = ref<number | null>(null)
const drafts = reactive<Record<number, string>>({})
const statusLabel = (status: string) => ({ pending_tax_payment: '待补税', processing: '待开票', issued: '已开票', canceled: '已取消', needs_review: '需联系客服' }[status] || status)
const load = async () => {
  loading.value = true
  try {
    const response = await adminAPI.listInvoices({ page: page.value, page_size: 20 })
    rows.value = response.data.data || []
    totalPage.value = response.data.pagination?.total_page || 1
  } finally { loading.value = false }
}
const changePage = (next: number) => { page.value = next; void load() }
const markIssued = async (row: any) => {
  busyId.value = row.id
  try { await adminAPI.markInvoiceIssued(row.id, { invoice_number: drafts[row.id] || '', email_sent: true }); await load() }
  finally { busyId.value = null }
}
onMounted(load)
</script>
