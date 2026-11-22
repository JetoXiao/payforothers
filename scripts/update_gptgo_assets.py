"""Replace the GPT Go artwork with one generated image and restore the redemption link."""
import http.client
import json
import mimetypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy/autnine-bridge"))
from manage import connect, login, api

ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "output/imagegen/gptpaynow-gptgo-20261009/gptgo.png"
REDEEM_URL = "https://966qjy.xyz"


def upload(ssh, token, path: Path) -> str:
    boundary = "----GptPayNowGoAsset" + str(int(time.time() * 1000))
    content = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="scene"\r\n\r\nproducts\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    conn = http.client.HTTPConnection("127.0.0.1", 18003, timeout=90)
    conn.sock = ssh.get_transport().open_channel("direct-tcpip", ("127.0.0.1", 18003), ("127.0.0.1", 0))
    conn.request(
        "POST",
        "/api/v1/admin/upload",
        body,
        {
            "Authorization": "Bearer " + token,
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Content-Length": str(len(body)),
        },
    )
    response = conn.getresponse()
    result = json.loads(response.read())
    conn.close()
    if response.status >= 400 or result.get("status_code") != 0:
        raise RuntimeError("image upload failed")
    return result["data"]["url"]


def append_link(html: str, label: str) -> str:
    if REDEEM_URL in html:
        return html
    return html + f'<p><a href="{REDEEM_URL}" target="_blank" rel="noopener noreferrer">{label}</a></p>'


def main() -> None:
    if not IMAGE.is_file():
        raise RuntimeError(f"generated image missing: {IMAGE}")
    ssh = connect()
    try:
        token = login(ssh)
        product = api(ssh, "GET", "/admin/products/13", token=token)["data"]
        if product.get("slug") != "gptgo-egypt":
            raise RuntimeError("product 13 is not gptgo-egypt; refusing update")
        image_url = upload(ssh, token, IMAGE)
        content = dict(product.get("content") or {})
        content["zh-CN"] = append_link(content.get("zh-CN", ""), "前往卡密兑换服务")
        content["zh-TW"] = append_link(content.get("zh-TW", ""), "前往卡密兌換服務")
        content["en-US"] = append_link(content.get("en-US", ""), "Open redemption service")
        instructions = dict(product.get("instructions") or {})
        instructions["zh-CN"] = f'支付成功后，复制订单中的卡密，前往 {REDEEM_URL} 按指引兑换。请勿公开卡密。'
        instructions["zh-TW"] = f'付款成功後，複製訂單中的卡密，前往 {REDEEM_URL} 按指引兌換。請勿公開卡密。'
        instructions["en-US"] = f'After payment, copy the CDK from your order and open {REDEEM_URL} to redeem it. Keep it private.'
        channels = product.get("payment_channel_ids") or []
        if isinstance(channels, str):
            try:
                channels = json.loads(channels or "[]")
            except json.JSONDecodeError:
                channels = []
        body = {
            "category_id": product["category_id"],
            "slug": product["slug"],
            "seo_meta": product.get("seo_meta") or {},
            "title": product.get("title") or {},
            "description": product.get("description") or {},
            "content": content,
            "instructions": instructions,
            "images": [image_url],
            "tags": product.get("tags") or [],
            "purchase_type": "guest",
            "fulfillment_type": "auto",
            "price_amount": 48.0,
            "cost_price_amount": float(product.get("cost_price_amount") or 0),
            "min_purchase_quantity": 1,
            "max_purchase_quantity": 1,
            "stock_display_mode": product.get("stock_display_mode") or "status",
            "manual_stock_total": 0,
            "payment_channel_ids": channels,
            "is_affiliate_enabled": bool(product.get("is_affiliate_enabled")),
            "is_active": True,
            "sort_order": int(product.get("sort_order") or 10),
            "skus": [
                {
                    "id": sku["id"],
                    "sku_code": sku["sku_code"],
                    "spec_values": sku.get("spec_values") or {},
                    "price_amount": 48.0,
                    "cost_price_amount": float(sku.get("cost_price_amount") or 0),
                    "is_active": True,
                    "manual_stock_total": 0,
                }
                for sku in product.get("skus") or []
            ],
        }
        updated = api(ssh, "PUT", "/admin/products/13", body, token=token)["data"]
        assert len(updated.get("images") or []) == 1
        assert REDEEM_URL in json.dumps(updated.get("content") or {})
        print(json.dumps({"product_id": 13, "image_count": len(updated["images"]), "image": updated["images"][0], "redemption_link": REDEEM_URL}, ensure_ascii=False))
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
