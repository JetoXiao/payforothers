export const storefrontControls = {
  'zh-CN': {
    wechat: { title: '微信客服', description: '每行填写一个微信号，按顺序显示在首页底部与商品详情。最多 20 个，空白或重复账号不会重复展示；全部删除后前台隐藏。', add: '添加微信客服', remove: '删除', account: '客服 {index} 微信号', removeAccount: '删除客服 {index}', placeholder: '填写微信号，例如 think-more-9', empty: '尚未配置微信客服，前台不显示。', invalid: '微信号只允许字母、数字、下划线和短横线，长度不超过 64 个字符。' },
    title: '个人中心菜单', description: '勾选用户个人中心需要展示的菜单，同时适用于桌面和移动端。仅控制入口显示，不改变账户权限与已有订单。',
    overview: '概览', orders: '我的订单', wallet: '我的钱包', affiliate: '推广返利', reseller: '分销中心', giftCard: '礼品卡兑换', security: '安全中心', api: 'API 对接', profile: '资料设置 / 发票信息',
    manual: '由本站手动交付', upstream: '自动采购并交付',
    deliveryHint: '仅影响新订单。手动模式不发起自动采购，也不再同步商品库存与表单；请设置人工库存，付款后在订单后台处理交付。已有订单继续使用下单时的交付方式。',
    skuHint: '保留规格编码与映射；手动模式可维护人工库存，切回自动采购后按渠道库存销售。',
  },
  'zh-TW': {
    wechat: { title: '微信客服', description: '每行填寫一個微信號，依序顯示於首頁底部與商品詳情。最多 20 個，空白或重複帳號不重複顯示；全部刪除後前台隱藏。', add: '新增微信客服', remove: '刪除', account: '客服 {index} 微信號', removeAccount: '刪除客服 {index}', placeholder: '填寫微信號，例如 think-more-9', empty: '尚未設定微信客服，前台不顯示。', invalid: '微信號僅允許字母、數字、底線和短橫線，長度不超過 64 個字元。' },
    title: '個人中心選單', description: '勾選使用者個人中心需要顯示的選單，同時適用於桌面和行動端。僅控制入口顯示，不改變帳戶權限與既有訂單。',
    overview: '概覽', orders: '我的訂單', wallet: '我的錢包', affiliate: '推廣返利', reseller: '分銷中心', giftCard: '禮品卡兌換', security: '安全中心', api: 'API 串接', profile: '資料設定 / 發票資訊',
    manual: '由本站手動交付', upstream: '自動採購並交付',
    deliveryHint: '僅影響新訂單。手動模式不發起自動採購，也不再同步商品庫存與表單；請設定人工庫存，付款後在訂單後台處理交付。既有訂單維持下單時的交付方式。',
    skuHint: '保留規格編碼與映射；手動模式可維護人工庫存，切回自動採購後按渠道庫存銷售。',
  },
  'en-US': {
    wechat: { title: 'WeChat support', description: 'One WeChat ID per row, displayed in order on the homepage footer and product details. Up to 20 IDs. Blank and duplicate IDs are ignored; remove all to hide support.', add: 'Add WeChat support', remove: 'Remove', account: 'Support {index} WeChat ID', removeAccount: 'Remove support {index}', placeholder: 'WeChat ID, e.g. think-more-9', empty: 'No WeChat support configured; hidden on the storefront.', invalid: 'WeChat IDs must be 1–64 letters, numbers, underscores or hyphens.' },
    title: 'Account menus', description: 'Choose account menus shown on desktop and mobile. This controls navigation visibility, not permissions or existing orders.',
    overview: 'Overview', orders: 'My orders', wallet: 'Wallet', affiliate: 'Affiliates', reseller: 'Reseller console', giftCard: 'Gift cards', security: 'Security', api: 'API integration', profile: 'Profile / Invoice details',
    manual: 'Fulfill manually in this store', upstream: 'Automatic procurement and delivery',
    deliveryHint: 'Applies to new orders only. Manual mode disables automatic procurement and stock/form synchronization. Set manual stock and fulfill paid orders in the admin panel. Existing orders retain their original delivery method.',
    skuHint: 'SKU codes and mappings are retained. Manage local stock in manual mode; channel stock applies after switching back to automatic procurement.',
  },
}
