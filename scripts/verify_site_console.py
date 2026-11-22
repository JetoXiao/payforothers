"""Local browser contract checks with synthetic API responses; no live access."""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5186")
    parser.add_argument("--output", default="tmp/site-console-qa")
    args = parser.parse_args()
    assert urlsplit(args.url).hostname in ("localhost", "127.0.0.1")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    sites = [
        {"id": 1, "name": "广州校园", "domain": "abc.gptpaynow.com", "enabled": True},
        {"id": 2, "name": "深圳校园", "domain": "xyz.gptpaynow.com", "enabled": True},
    ]
    grants = [
        {"site_id": 1, "overview": False, "users": False, "orders": True, "visits": False},
        {"site_id": 2, "overview": False, "users": True, "orders": False, "visits": False},
    ]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        for super_admin in (False, True):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.add_init_script("localStorage.setItem('admin_token','local-qa');localStorage.setItem('admin_locale','zh-CN');")
            page = context.new_page()
            errors = []
            writes = []
            saved_grants = {"8": [], "9": []}
            page.on("pageerror", lambda error: errors.append(str(error)))

            def api(route):
                request = route.request
                path = urlsplit(request.url).path.removeprefix("/api/v1")
                query = parse_qs(urlsplit(request.url).query)
                data = {}
                pagination = None
                if path == "/admin/authz/me":
                    data = {"is_super": super_admin, "roles": [], "policies": [{"action": "*", "object": "/admin/*"}], "site_scope": {"restricted": not super_admin, "grants": grants}}
                elif path == "/admin/site-console/scope":
                    data = {"is_super": super_admin, "restricted": not super_admin, "sites": sites, "grants": grants, "base_domain": "gptpaynow.com"}
                elif path == "/public/config":
                    data = {"brand": {}, "app_version": "local-qa"}
                elif path == "/admin/site-console/overview":
                    data = {"registered_users": 28, "browser_visits": 105, "by_currency": [{"currency": "CNY", "orders": 19, "paid_orders": 16, "missing_cost_orders": 1, "sales": "2000.00", "refunds": "100.00", "net_revenue": "1900.00", "cost": "1400.00", "payment_fees": "20.00", "profit": "480.00"}]}
                elif path == "/admin/product-catalog":
                    assert super_admin or request.method == "GET"
                    data = [{"item": {"id": 1, "product_id": 9, "sku_id": 12, "product_slug": "demo", "title": {"zh-CN": "演示商品"}, "sku_code": "DEFAULT", "product_active": True, "sku_active": True, "product_price": "20.00", "cost_price": "8.00", "sale_price": "20.00", "follow_product_price": True, "inventory": 13}, "effective_sale_price": "20.00", "profit_amount": "12.00", "profit_rate": 60, "inventory": 13}]
                    pagination = {"total": 1}
                elif path == "/admin/product-catalog/sync":
                    assert super_admin
                    data = {"synced": 1}
                elif path == "/admin/site-console/orders":
                    assert super_admin or query.get("site_id") == ["1"]
                    data = [{"id": 42, "order_no": "ABC-ORDER-42", "source_domain": "abc.gptpaynow.com", "buyer_email": "buyer@example.test", "currency": "CNY", "total_amount": "99.00", "refunded_amount": "0.00", "status": "completed", "created_at": "2026-11-23T01:00:00+08:00"}]
                    pagination = {"total": 1}
                elif path == "/admin/site-console/orders/42":
                    data = {"id": 42, "order_no": "ABC-ORDER-42", "source_domain": "abc.gptpaynow.com", "buyer_email": "buyer@example.test", "currency": "CNY", "total_amount": "99.00", "status": "completed", "items": [{"title": {"zh-CN": "演示商品"}, "quantity": 1}]}
                elif path == "/admin/site-console/users":
                    assert super_admin or query.get("site_id") == ["2"]
                    data = [{"id": 8, "email": "xyz@example.test", "display_name": "深圳用户", "registration_domain": "xyz.gptpaynow.com", "created_at": "2026-11-23T01:00:00+08:00"}]
                    pagination = {"total": 1}
                elif path == "/admin/authz/admins":
                    assert super_admin
                    data = [{"id": 8, "username": "campus", "is_super": False}, {"id": 9, "username": "campus-finance", "is_super": False}]
                elif path in ("/admin/sites/admins/8/grants", "/admin/sites/admins/9/grants"):
                    assert super_admin
                    administrator = path.split("/")[-2]
                    if request.method == "PUT":
                        writes.append({"admin_id": administrator, **request.post_data_json})
                        saved_grants[administrator] = request.post_data_json["grants"]
                    data = {"restricted": True, "grants": saved_grants[administrator]}
                else:
                    # Global order polling, dashboards and directories are never
                    # needed for a restricted administrator.
                    if not super_admin and path.startswith("/admin/"):
                        raise AssertionError("Unexpected global request: " + path)
                    data = []
                payload = {"status_code": 0, "msg": "success", "data": data}
                if pagination:
                    payload["pagination"] = pagination
                route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

            page.route("**/api/v1/**", api)
            page.goto(args.url + "/site-console", wait_until="networkidle")
            page.get_by_role("heading", name="子站管理", exact=True).wait_for()
            if not super_admin:
                page.get_by_role("button", name="ABC-ORDER-42", exact=True).click()
                page.get_by_text("演示商品 × 1").wait_for()
                assert page.get_by_role("button", name="经营统计", exact=True).count() == 0
                assert page.get_by_role("button", name="站点与管理员", exact=True).count() == 0
                page.locator(".site-console select").first.select_option("2")
                page.get_by_text("xyz@example.test", exact=True).wait_for()
                assert page.get_by_text("buyer@example.test", exact=True).count() == 0
                assert page.get_by_role("button", name="来源订单", exact=True).count() == 0
                page.goto(args.url + "/orders", wait_until="networkidle")
                assert urlsplit(page.url).path == "/site-console"
                page.screenshot(path=str(output / "scoped-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(output / "scoped-mobile.png"), full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            else:
                page.get_by_text("480.00", exact=True).wait_for()
                page.get_by_role("button", name="站点与管理员", exact=True).click()
                admin_select = page.get_by_label("管理员账号", exact=False)
                admin_select.select_option("8")
                page.get_by_role("button", name="保存个人授权", exact=True).wait_for()
                page.get_by_label("abc.gptpaynow.com 来源订单", exact=True).check()
                page.get_by_role("button", name="保存个人授权", exact=True).click()
                page.get_by_text("已保存 campus 的个人菜单授权", exact=False).wait_for()
                assert writes[-1]["admin_id"] == "8"
                assert writes[-1]["grants"] == [{"site_id": 1, "overview": False, "users": False, "orders": True, "visits": False}]
                admin_select.select_option("9")
                page.get_by_role("button", name="保存个人授权", exact=True).wait_for()
                assert not page.get_by_label("abc.gptpaynow.com 来源订单", exact=True).is_checked()
                page.get_by_label("abc.gptpaynow.com 的个人菜单组合", exact=True).select_option("finance")
                assert page.get_by_label("abc.gptpaynow.com 经营统计", exact=True).is_checked()
                assert page.get_by_label("abc.gptpaynow.com 来源订单", exact=True).is_checked()
                assert not page.get_by_label("abc.gptpaynow.com 注册用户", exact=True).is_checked()
                page.get_by_role("button", name="保存个人授权", exact=True).click()
                page.get_by_text("已保存 campus-finance 的个人菜单授权", exact=False).wait_for()
                assert writes[-1]["admin_id"] == "9"
                assert writes[-1]["grants"][0]["overview"] is True
                admin_select.select_option("8")
                page.get_by_role("button", name="保存个人授权", exact=True).wait_for()
                assert not page.get_by_label("abc.gptpaynow.com 经营统计", exact=True).is_checked()
                assert page.get_by_label("abc.gptpaynow.com 来源订单", exact=True).is_checked()
                assert saved_grants["9"][0]["overview"] is True
                page.screenshot(path=str(output / "super-grants-desktop.png"), full_page=True)
                page.evaluate("document.documentElement.classList.add('dark')")
                page.screenshot(path=str(output / "super-grants-dark.png"), full_page=True)
                colors = page.locator('.site-console select').first.evaluate("el => { const c = getComputedStyle(el); return [c.backgroundColor, c.color] }")
                assert colors[0] != colors[1], colors
            assert not errors, errors
            context.close()
        browser.close()
    print("PASS: scoped menus, site switching, order detail, route guard, grant saving, desktop/mobile; no live API requests.")


if __name__ == "__main__":
    main()
