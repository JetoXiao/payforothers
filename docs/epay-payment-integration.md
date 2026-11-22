# GptPayNow → Epay 支付接入

配置时间：2026-10-08。只通过后台配置新增支付渠道，未重建商城/Epay 程序镜像，也未发布此前暂存的页面修改。

| 项目 | 配置 |
| --- | --- |
| 商城渠道 ID / 名称 | 1 / 支付宝 |
| 网关 | https://pay.gptpaynow.com |
| Epay 商户号 | 1000 |
| 协议 | 易支付 V1，MD5 |
| 展示方式 | QR 二维码 |
| 适用 | 商品订单、开票补款订单；不开放钱包充值 |
| 金额范围 | 0.01–10000.00 CNY，与当前 Epay 上限一致 |
| 额外支付手续费 | 0（未擅自增加收费） |
| 异步通知 | https://www.gptpaynow.com/api/v1/payments/callback |
| 同步返回 | https://www.gptpaynow.com/pay （商城自动附加原订单定位参数） |

商户 1000 当前 keytype=0；提供的 MD5 密钥经数据库比对与只读商户接口验证匹配。此模式无需 RSA 私钥，未保存或使用聊天中提供的 RSA 私钥。密钥配置不在此文档中，管理员接口脱敏、公开配置不返回密钥。

## 已验证

- HTTPS 商户查询成功，商户有效且已允许支付。
- 以 CNY 0.01 生成一笔明确标为“支付接口联调（请勿付款）”的未支付测试单，`/mapi.php` 返回 code=1 和 qrcode。
- 测试单上游编号 `2026100803402767330`，本地引用 `GPNVERIFY20261008034026d53c9d`；没有对应商城商品订单，不会触发上游 CDK 采购。**不要支付此联调单**。
- 检查时该 Epay 测试单状态仍为 0，尚未支付。未调用任何付款、代付、退款或结算接口。
- 回调接口可访问，伪造签名且无关联订单的通知返回 fail。
- 易支付签名/回调适配器/HTTP 回调单元测试通过。
- 原“未配置默认账户”没有在本次扫码下单中复现，但不代表覆盖其他商户、支付模式和通道。

## 回调重试

Epay 仍封锁公共 `/cron.php`。通过主机 `epay-notify-retry.timer` 每分钟以 CLI 调用 `do=notify`，只重试已经进入支付通知重试队列的订单。
不启用 settle、transfer、profitsharing、order 清理任务，不执行自动结算或资金转移。

```sh
systemctl status epay-notify-retry.timer
systemctl status epay-notify-retry.service
journalctl -u epay-notify-retry.service --no-pager -n 30
```

## 验收边界

尚未完成真实扫码付款 → 汇付通知 Epay → Epay 通知商城 → 商城扣上游余额采购卡密的端到端测试。
后续使用真实商品测试前先确认售价、上游余额和收款通道费用。真实付款会触发已接入的自动采购，不要为验证回调手工伪造成功状态。

聊天中已出现密钥和私钥，建议后续在可控窗口轮换，再同步更新服务端配置。修改 Epay 密钥会影响旧单签名核验，应先确认未完成订单及通知状态。
