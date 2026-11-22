import { api } from './client'
export interface ProductCatalogItem { id:number; product_id:number; sku_id:number; product_slug:string; title:Record<string,string>; sku_code:string; spec_values:Record<string,unknown>; product_active:boolean; sku_active:boolean; product_price:string|number; cost_price:string|number; sale_price:string|number; follow_product_price:boolean; manual_stock:number; manual_locked:number; manual_sold:number; auto_stock:number; effective_sale_price:string|number; profit_amount:string|number; profit_rate:number; inventory:number }
export const productCatalogAPI={
 list:(params?:Record<string,unknown>)=>api.get('/admin/product-catalog',{params}),
 sync:(includeInactive:boolean)=>api.post('/admin/product-catalog/sync',{include_inactive:includeInactive}),
 update:(id:number,data:Record<string,unknown>)=>api.put(`/admin/product-catalog/${id}`,data),
}
