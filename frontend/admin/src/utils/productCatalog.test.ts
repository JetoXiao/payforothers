import { describe, expect, it } from 'vitest'

function visibleControls(isSuper: boolean) { return { sync: isSuper, edit: isSuper, readOnly: !isSuper } }
describe('product catalog access', () => {
  it('regular administrators are read-only', () => expect(visibleControls(false)).toEqual({ sync:false, edit:false, readOnly:true }))
  it('super administrators can synchronize and edit', () => expect(visibleControls(true)).toEqual({ sync:true, edit:true, readOnly:false }))
})
