import { describe, expect, it } from 'vitest'
import { normalizeVoicePreferences, pollOrderVoice, scanNewOrders, readVoiceCursor, voiceAdminId, ORDER_VOICE_POLL_MS } from './orderVoice'

function storage() {
  const map = new Map<string,string>()
  return { getItem: (key: string) => map.get(key) ?? null, setItem: (key: string, value: string) => { map.set(key,value) } }
}
const row = (id: number) => ({ id, order_no: `ORDER${id}` })

describe('admin order voice', () => {
  it('normalizes settings and namespaces by administrator, not token text', () => {
    expect(normalizeVoicePreferences(null)).toEqual({ enabled:false, volume:0.8 })
    expect(normalizeVoicePreferences({enabled:true,volume:2})).toEqual({enabled:true,volume:1})
    expect(voiceAdminId('a.'+btoa('{"admin_id":42}')+'.c')).toBe('42')
    expect(voiceAdminId('invalid')).toBeNull()
  })
  it('first response creates a baseline without replaying history', async () => {
    expect(await scanNewOrders(async()=>[row(9),row(8)],null)).toEqual({id:9,orders:[]})
    expect(await scanNewOrders(async()=>[],null)).toEqual({id:0,orders:[]})
    expect(await scanNewOrders(async()=>[row(1)],0)).toEqual({id:1,orders:[row(1)]})
  })
  it('counts new parent orders only and does not replay status changes', async () => {
    expect(await scanNewOrders(async()=>[row(12),row(11),{...row(10),parent_id:9},row(9)],9)).toEqual({id:12,orders:[row(12),row(11)]})
    expect(await scanNewOrders(async()=>[row(12),row(11)],12)).toEqual({id:12,orders:[]})
  })
  it('does not miss a burst crossing pagination', async () => {
    const rows = Array.from({length:220}, (_, i)=>row(220-i))
    const result = await scanNewOrders(async page=>rows.slice((page-1)*100,page*100),7)
    expect(result.id).toBe(220)
    expect(result.orders).toHaveLength(213)
  })
  it('shared cursor suppresses duplicates across tabs', async () => {
    const s=storage(); let now=100000
    await pollOrderVoice(s,'cursor',async()=>[row(1)],()=>now,()=>true)
    now+=ORDER_VOICE_POLL_MS
    expect((await pollOrderVoice(s,'cursor',async()=>[row(2),row(1)],()=>now,()=>true)).orders).toEqual([row(2)])
    expect((await pollOrderVoice(s,'cursor',async()=>[row(2),row(1)],()=>now,()=>true)).skipped).toBe(true)
  })
  it('request failure and canceled listeners never advance cursor', async () => {
    const s=storage(); let now=100000
    await pollOrderVoice(s,'cursor',async()=>[row(1)],()=>now,()=>true)
    const before=s.getItem('cursor'); now+=ORDER_VOICE_POLL_MS
    await expect(pollOrderVoice(s,'cursor',async()=>{throw new Error('offline')},()=>now,()=>true)).rejects.toThrow('offline')
    expect(s.getItem('cursor')).toBe(before)
    await pollOrderVoice(s,'cursor',async()=>[row(2)],()=>now,()=>false)
    expect(s.getItem('cursor')).toBe(before)
  })
  it('ignores stale shared cursor after closing the browser or prolonged sleep', async () => {
    const s=storage(); s.setItem('cursor',JSON.stringify({id:10,checkedAt:1}))
    expect(readVoiceCursor(s,'cursor',100000)).toBeNull()
    expect((await pollOrderVoice(s,'cursor',async()=>[row(20)],()=>100000,()=>true)).orders).toEqual([])
  })
})
