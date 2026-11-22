# Autnine / 966qjy 采购适配服务

## 2026-11-11 Pro 自动采购与发货配置

- 本地商品 9（`gptpro100`）、SKU 9 → Autnine 商品 2、埃及区 SKU 2 → `PRO5X` / `EG`。桥接目录的旧智利地区已修正，成本快照更新为 610 CNY，售价保持 690 CNY。
- 本地商品 15（`chatgpt-pro-5x-ios`）、SKU 15 → `https://autnine.com/products/gpt5x-ios` 商品 19、SKU 22 → `PRO5X_IOS` / `US`。新增映射 ID 8，成本快照更新为 605 CNY，售价保持 728 CNY。
- 两者原始履约类型均为 `upstream`，后台/前台展示 `auto`，`local_manual_fulfillment=false`。每单限 1 件；使用现有支付回调、采购队列和卡密轮询交付流程。卡密到账后由买家自行兑换。
- 不启用整个连接的自动售价同步。库存由套餐权限、地区与共享代理余额计算，不能将两个商品的可购数量相加理解为独立库存。
- 修改前数据库及相关记录备份：`/opt/gptpaynow-autnine/backups/pro-auto-20261111/`。不要用全库旧备份覆盖正在接单的商城。
- 运维脚本：`scripts/prepare_pro_auto_catalog.py`、`scripts/enable_pro_auto_fulfillment.py`；属于有前置状态断言的一次性操作，重复执行前先核查当前状态。
- 验证：9 项仿真测试（含两个 Pro 套餐采购路由、自动交付和重试幂等）；两个商品线上映射、库存及原始履约类型；既有订单商品快照和已售数量保持不变；两个不存在订单的采购请求均被拒绝且未生成采购记录；两个商品页均显示自动交付且无 JS 错误。未创建真实订单或进行真实扣款采购。

以下为最初接入记录，商品数量和套餐信息以当前 `catalog.json` 及线上映射为准。

本次替换仅更新线上商品与独立适配服务，不重新部署商城前后台。

## 接入方式

- 公开商品来源：Autnine `GET /api/v1/public/products`，原始信息留存在 `source-snapshot.json`。
- 采购来源：966qjy `https://966qjy.xyz/api/partners/v1`，使用用户提供的代理 API Key。
- 商城连接：`Autnine 卡台 · 966qjy`，连接 ID 1，复用 Dujiao-Next 签名协议。
- 内部地址：`http://autnine-bridge:8080`，无公网端口；仅商城 Docker 网络可达。
- 商品：Go 埃及、Plus 菲、Pro 5x 智利、Pro 20x 菲、Pro 25x 智利。排除买U教程、Credit、Claude。
- 首次售价分别为 35、108、620、1000、3090 CNY，未设置加价。当前 API 采购价与售价相同，不含利润及支付手续费，正式销售前应确认定价。

## 流程和安全边界

用户支付成功 → 现有采购任务 → 本适配服务 → 生成 CDK（上游扣余额）→ 原有轮询交付 → 用户在订单获取 CDK → 自行到 966qjy 兑换。

- 不调用 `/redemptions`，不收集 ChatGPT Session/Token，不替用户完成充值。
- 采购前只读检查商城订单已支付、未退款，商品/SKU/数量与采购 trace 匹配，连接处于 active 状态。
- 上游密钥只保存在 `/opt/gptpaynow-autnine/secrets/upstream_api_key`；不得填写到前端或 Dujiao API Key 字段。商城连接保存的是独立内部桥接凭据。
- 同一个商城子订单使用稳定幂等键、持久化请求体，超时/重启重试不换键或参数。超过 12 小时仍未知的申请转人工核查；这是本地保护阈值，不代表上游保证的幂等保留期限。
- 卡密响应在持久化 SQLite 中用 Fernet 加密。密钥和数据库需一起备份，不能丢弃采购数据库后盲目重试。
- 出现返回数量/套餐/费用异常时保留加密响应并停留人工核查，不把失败响应当成交付。
- 不支持自动退款、取消或卡密更换。请到上游核对后由人工处理，不删除采购状态来“重试”。
- 库存表示当前代理余额下可采购数量，不是复制上游零售库存；按上游套餐权限/地区/余额和商城定时同步刷新。实际采购再次验证。
- 套餐地区变更会将可购库存设为 0，需先更新商品说明并核对 API 套餐。已售商品价格快照不被覆盖，成本上涨会阻止自动采购并提示核查。
- 每单暂限一张卡，自动同步零售价关闭；后续可在商城商品管理调整售价。

## 目录与恢复

服务器 `/opt/gptpaynow-autnine`，Compose 项目 `gptpaynow-autnine`。

```sh
cd /opt/gptpaynow-autnine
docker compose -f compose.yml ps
docker compose -f compose.yml logs --tail 30
```

`backups/shop-before.db` 为修改前在线 SQLite 备份；`backups/products-before.json` 为六个测试商品资料备份。
`migration-result.json` 记录新商品 ID 7–11、上游映射和删除 ID。测试商品无订单引用，已走正常后台软删除。
不要把全库旧备份直接覆盖正在接单的商城；需要恢复商品时应单独恢复商品记录，并先备份当前状态。

备份适配服务时先暂停采购、停桥接服务，再备份 data/ 和 secrets/，重新启动后验证；不得执行 `down -v` 或删除 data/。
原商城、Epay 和其他容器未重建。上游零售文案已经重排、补齐三语，移除外部支付广告及上游客服引流，不把“官方代充”等无法核实的宣传当本站承诺。

## 验证范围

`python -m unittest -v test_bridge.py`：8 项仿真测试，覆盖签名、未付款拒绝、数量/trace/凭据拒绝、涨价拦截、错误响应隔离、幂等和超时重启恢复、地区变化库存关闭。
`python verify.py`：线上商品数量/映射/图片/详情，桌面浅色中文和手机暗色英文，共 12 页，无真实下单；不存在订单的签名采购请求被拒绝。
未进行真实付费采购、充值或支付回调测试，不能宣称真实交易已验收。商城尚未配置支付通道，Epay 需要另行接入商城。
