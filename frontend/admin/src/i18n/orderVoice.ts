export const orderVoiceMessages = {
  'zh-CN': {
    title: '订单语音', enable: '开启提醒', volume: '提醒音量', test: '测试语音', activate: '启用声音 / 测试', viewOrders: '查看订单', received: '本次收到 {count} 个新订单',
    description: '每 15 秒检查新建订单（含待付款），不重复播报状态变化。首次启动仅建立基线，不播报历史订单。',
    limitations: '偏好仅保存在当前浏览器，按管理员区分。同一浏览器多标签页去重；刷新后请点击启用声音。关闭后台、休眠或浏览器后台限流可能暂停/延迟提醒。',
    states: { off: '语音提醒已关闭', activate: '请点击“启用声音”授权本页播放', initializing: '正在建立订单监听基线…', listening: '正在监听新订单', blocked: '浏览器阻止播放或音频加载失败，请点击启用声音重试', reconnecting: '网络异常，稍后自动重试', unauthorized: '登录已失效或无订单权限，请重新登录' },
  },
  'zh-TW': {
    title: '訂單語音', enable: '開啟提醒', volume: '提醒音量', test: '測試語音', activate: '啟用聲音 / 測試', viewOrders: '查看訂單', received: '本次收到 {count} 個新訂單',
    description: '每 15 秒檢查新建訂單（含待付款），不重複播報狀態變更。首次啟動只建立基準，不播報歷史訂單。',
    limitations: '偏好僅存於目前瀏覽器，依管理員區分。同一瀏覽器多分頁去重；重新整理後請點擊啟用聲音。關閉後台、休眠或瀏覽器背景限流可能暫停／延遲提醒。',
    states: { off: '語音提醒已關閉', activate: '請點擊「啟用聲音」允許本頁播放', initializing: '正在建立訂單監聽基準…', listening: '正在監聽新訂單', blocked: '瀏覽器阻止播放或音訊載入失敗，請點擊啟用聲音重試', reconnecting: '網路異常，稍後自動重試', unauthorized: '登入已失效或無訂單權限，請重新登入' },
  },
  'en-US': {
    title: 'Order voice', enable: 'Enable alerts', volume: 'Volume', test: 'Test voice', activate: 'Enable sound / Test', viewOrders: 'View orders', received: '{count} new orders this session',
    description: 'Checks new orders every 15 seconds, including unpaid orders. Status changes are not re-announced. The first check establishes a baseline without announcing history.',
    limitations: 'Preferences are per administrator in this browser. Multiple tabs are deduplicated. Enable sound after refreshing. Closing the admin, sleep, and background throttling can pause or delay alerts.',
    states: { off: 'Voice alerts are off', activate: 'Click Enable sound to allow playback', initializing: 'Establishing the order baseline…', listening: 'Listening for new orders', blocked: 'Playback was blocked or audio failed to load. Click Enable sound to retry.', reconnecting: 'Connection lost. Retrying shortly.', unauthorized: 'Session expired or order access denied. Sign in again.' },
  },
}
