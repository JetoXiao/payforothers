# 代充商城部署与渠道接入手册

本仓库基于 Dujiao-Next，已经具备商品、SKU、支付、订单、卡密、上游采购、回调交付、退款、对账、邮件通知、工单式人工处理和后台 RBAC。这里将 Autnine 作为正式的 Dujiao-Next 上游，将 SpaceXCard 作为独立的采购结算工具。

## 安全边界

- 不收集 ChatGPT 密码、Cookie、Session Token、`/api/auth/session` 内容、短信验证码或 2FA 恢复码。
- 只销售来源可证明且允许转售的卡密、兑换链接或人工服务。
- SpaceXCard 的卡号、有效期、CVV、API 密钥只允许进入独立的财务/采购系统，不写入顾客订单、商品描述、交付内容或日志。
- 不要把 ChatGPT Plus 与 OpenAI API 余额混为一谈；它们是不同产品。

## 1. 本地或服务器启动

1. 安装 Docker 和 Docker Compose。
2. 复制 `.env.production.example` 为 `.env`。
3. 分别生成三个不同的随机密钥，替换 `.env` 中的占位值。
4. 设置管理员账号、强密码、不可猜测的 `WEB_ADMIN_PATH`，并把 `CORS_ALLOWED_ORIGINS` 改成商城的准确 HTTPS Origin（不要使用 `*`）。
5. 启动：

   ```powershell
   docker compose -f docker-compose.production.yml up -d --build
   ```

6. 验证：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/production-smoke.ps1
   ```

生产环境应在前面放置 Nginx/Caddy/Cloudflare，启用 HTTPS、备份卷、访问日志脱敏和监控。不要把 SQLite 数据库、`.env` 或后台端口公开下载。

## 2. 申请 Autnine API

Autnine 公开前端显示它使用 Dujiao-Next，并在用户中心提供“API 对接”申请。操作顺序：

1. 在 `https://autnine.com/` 注册并完成其要求的账户审核。
2. 在个人中心打开“API 对接”，申请 API 权限。
3. 审核通过后立即保存 API Key 和 Secret；Secret 不应通过聊天工具转发。
4. 确认账户余额、币种、退款政策、卡密有效期和商品转售权限。
5. 不要抓取 Autnine 网页或模拟用户登录，使用它提供的正式 API 凭据。

## 3. 在本系统连接 Autnine

进入后台的“连接管理”，创建连接：

| 字段 | 值 |
| --- | --- |
| 名称 | Autnine |
| Base URL | `https://autnine.com` |
| API Key | Autnine 审核后提供 |
| API Secret | Autnine 审核后提供 |
| 协议 | `dujiao-next` |
| 回调 URL | 你的商城公网 HTTPS 地址加后台显示的上游回调路径 |
| 汇率 | 同币种填 `1`，否则填实际结算汇率 |
| 加价百分比 | 按退款率、支付手续费、售后和税费核算 |
| 自动同步价格 | 初期关闭，核对价格后再打开 |

保存后执行 Ping。Ping 成功会返回上游站点、协议版本、用户 ID、余额和币种，并把连接从“待激活”转为“已激活”。

## 4. 导入商品并测试采购

1. 打开“商品映射”并选择 Autnine。
2. 拉取上游分类和商品，只导入明确允许销售的 ChatGPT 卡密商品。
3. 先保持商品下架，检查：标题、地区、有效期、是否允许覆盖订阅、交付类型、SKU、成本价和库存。
4. 系统会保留上游商品及 SKU 映射；上游商品要求的普通表单字段会同步到结算页。
5. 删除任何要求 ChatGPT 密码、Cookie、Session Token、验证码或恢复码的商品；不要上架这种 SKU。
6. 设置售价、购买数量上限、退款说明和客户可见的兑换教程。
7. 使用测试支付或最小金额完成一笔端到端订单，确认：
   - 支付回调只处理一次；
   - 本地订单生成采购单；
   - 上游接单后状态可轮询或回调；
   - 卡密/兑换链接只对该订单的顾客展示；
   - 失败时进入重试或退款队列；
   - 邮件和后台审计日志不泄露敏感内容。

## 5. 支付配置

系统内置支付宝、微信支付、Stripe、PayPal、易支付、USDT 等适配器。只启用你拥有合法商户资质的渠道：

- 在后台“支付渠道”填写官方商户配置；
- 回调必须使用 HTTPS；
- 密钥只保存于后台加密字段或服务器密钥管理系统；
- 不把任何支付私钥放进前端、Git 或商品说明；
- 开启金额、订单号、币种和签名校验；
- 对退款和拒付保留人工复核。

## 6. SpaceXCard 的定位

`https://spacexcard.org/` 是独立的虚拟卡系统，公开页面显示 API/CDK 文档需要登录授权。当前没有账户密钥和正式文档时，不应猜测或逆向它的私有接口。

建议流程：

1. 单独注册商户账户并完成 KYC/企业审核。
2. 在其开发者中心下载当前 OpenAPI 文档，确认开卡、充值、交易查询、冻结和 webhook 权限。
3. 为采购设置单卡/单日限额、商户锁、余额告警和审批。
4. SpaceXCard 只用于你向合规供应商付款；商城仍通过 Autnine API 自动采购。
5. 每日导出 SpaceXCard 交易，与本系统“采购单管理/对账中心”核对。
6. 没有书面许可前，不要用虚拟卡批量替客户登录 ChatGPT 官网付款，也不要用它规避地区、身份或平台风控。

如果以后确实要做 SpaceXCard API 适配器，应先取得其正式 Markdown/OpenAPI 文档和测试环境凭据，再实现服务端专用连接；密钥加密存储，webhook 验签，并且不能把 PAN/CVV 返回前端。

## 7. 上线检查清单

- [ ] Autnine API 申请已批准，Ping 成功。
- [ ] 供应合同、卡源、退款和转售权已经核实。
- [ ] 商品不要求任何 ChatGPT 登录凭据。
- [ ] 完成至少一笔成功、失败、退款的全流程演练。
- [ ] HTTPS、后台隐藏路径、2FA、Turnstile、登录限流已开启。
- [ ] 数据库、上传目录和 Redis 有自动备份与恢复演练。
- [ ] 支付 webhook、上游回调、邮件和队列有监控告警。
- [ ] 隐私政策、服务条款、虚拟商品退款规则和客服渠道已发布。
- [ ] 管理员账号不再使用 bootstrap 初始密码。
- [ ] 日志中没有卡密、API Secret、支付私钥、卡号/CVV 或用户登录凭据。

## 8. 日常运营

- 每天检查采购失败、上游余额、退款、低库存和对账差异。
- 上游规则或价格变化时先下架，再复测后恢复。
- 卡密只在成功支付订单中展示，不通过公共链接或客服群发送。
- 定期轮换 Autnine、支付渠道和 SpaceXCard API 密钥。
- 发现凭据泄露时立即吊销密钥、冻结采购、保全审计记录并通知受影响方。
