import { afterEach, describe, expect, it, vi } from 'vitest'
import { getOrderVoicePage } from './orderVoice'

afterEach(() => vi.unstubAllGlobals())
describe('read-only voice polling API', () => {
  it('uses existing authenticated endpoint and limits returned data', async () => {
    const fetcher = vi.fn().mockResolvedValue({ok:true,json:async()=>({status_code:0,data:[{id:2,order_no:'ORDER2',user_email:'private@example.test',fulfillment:{secret:'private'}}]})})
    vi.stubGlobal('fetch',fetcher)
    const signal = new AbortController().signal
    expect(await getOrderVoicePage('test-token',1,signal)).toEqual([{id:2,order_no:'ORDER2',parent_id:undefined}])
    expect(fetcher.mock.calls[0]![0]).toContain('/api/v1/admin/orders?page=1&page_size=100&sort_order=desc')
    expect(fetcher.mock.calls[0]![1]).toEqual({headers:{Authorization:'Bearer test-token'},signal,cache:'no-store'})
  })
  it('stops for business-level authorization errors even with HTTP 200', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({status_code:401,data:[]})}))
    await expect(getOrderVoicePage('x',1,new AbortController().signal)).rejects.toMatchObject({status:401})
  })
  it('rejects malformed responses rather than resetting the cursor', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({status_code:0,data:null})}))
    await expect(getOrderVoicePage('x',1,new AbortController().signal)).rejects.toMatchObject({status:500})
  })
})
