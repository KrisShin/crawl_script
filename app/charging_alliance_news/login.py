"""
WeChat Official Account automated login for charging_alliance_news spider.

Launches a Chromium browser (headless by default — works on cloud servers),
saves the QR-code screenshot so the user can scan it, then automatically
extracts cookie, token, fingerprint, and fakeid from the WeChat MP backend.

Called as:  creds = await wechat_login()
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import async_playwright


KNOWN_FAKEID = "MzUyMzAzMjcwNQ=="  # fallback fakeid for 中国充电联盟
APPMSG_BASE_URL = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QR_CODE_PATH = PROJECT_ROOT / "qr_code.png"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _extract_token_from_url(url: str) -> Optional[str]:
    m = re.search(r"token=(\d+)", url)
    return m.group(1) if m else None


def _build_cookie_string(cookies: list[dict]) -> str:
    return "; ".join([f'{c["name"]}={c["value"]}' for c in cookies])


async def _save_qr_code(page) -> None:
    """Take a screenshot of the QR code and save it locally."""
    qr_selectors = [
        "img.qcode_img",
        "img[src*='qrcode']",
        "img[src*='QrCode']",
        ".qrcode img",
        ".login_qrcode_img",
        "#login_qrcode",
        "iframe[src*='qrcode']",
        "iframe[src*='QrCode']",
    ]
    for sel in qr_selectors:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=3000):
                await el.screenshot(path=str(QR_CODE_PATH))
                return
        except Exception:
            continue

    # Fallback: full-page screenshot
    try:
        await page.screenshot(path=str(QR_CODE_PATH), full_page=False)
    except Exception:
        pass


async def _click_hyperlink_button(page) -> bool:
    selectors = [
        '[title="超链接"]',
        'a[title="超链接"]',
        'a:has-text("超链接")',
        '[data-name="link"]',
        '#js_editor_insertlink',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.click()
                logger.info(f"已点击超链接按钮 (selector: {sel})")
                return True
        except Exception:
            continue
    return False


async def _search_charging_alliance(page) -> bool:
    await page.wait_for_timeout(2000)

    # Step A – click "选择其他账号" to reveal the search input
    account_selectors = [
        "text=选择其他账号",
        "text=其他账号",
    ]
    clicked = False
    for sel in account_selectors:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=3000):
                await el.click()
                clicked = True
                logger.info(f"已点击 '{sel}'")
                break
        except Exception:
            continue

    if not clicked:
        logger.warning("未能自动点击'选择其他账号'，请手动操作")
        return False

    await page.wait_for_timeout(2000)

    # Step B – type "充电联盟" via keyboard
    try:
        await page.keyboard.press("Control+A")
        await page.keyboard.type("充电联盟", delay=50)
        logger.info("已通过键盘输入搜索关键词")
    except Exception:
        logger.warning("未能自动填充搜索关键词，请手动输入")
        return False

    await page.wait_for_timeout(500)

    # Step C – Enter to search
    try:
        await page.keyboard.press("Enter")
        logger.info("已按下 Enter 触发搜索")
        return True
    except Exception:
        pass

    # Button fallback
    for sel in ["text=搜索", 'button:has-text("搜索")', 'a:has-text("搜索")', ".icon_search"]:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=2000):
                await el.click()
                logger.info(f"已点击搜索按钮 (selector: {sel})")
                return True
        except Exception:
            continue

    logger.warning("未能自动触发搜索，请手动点击搜索按钮")
    return False


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------
async def wechat_login(timeout_seconds: int = 180) -> dict:
    """
    Launch browser (headless by default), wait for QR scan, extract credentials.

    Set env var  WECHAT_HEADED=1  to use a visible browser window for local dev.

    Returns:  {"cookie": str, "token": str, "fingerprint": str, "fakeid": str}
    """
    headless = not bool(int(os.environ.get("WECHAT_HEADED", "0")))

    print("=" * 60)
    print("  微信公众平台 · 扫码登录")
    print("  目标公众号：中国充电联盟")
    if headless:
        print(f"  QR 二维码将保存到: {QR_CODE_PATH}")
    print("=" * 60)

    fingerprint: Optional[str] = None
    fakeid: Optional[str] = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        captured_requests: list = []

        def _on_request(request):
            captured_requests.append(request)

        page.on("request", _on_request)

        # =================================================================
        # STEP 1 – Login (QR code)
        # =================================================================
        print(f"\n[1/4] 正在打开微信公众平台 (登录超时 {timeout_seconds} 秒)...")
        await page.goto("https://mp.weixin.qq.com/")
        await page.wait_for_timeout(2000)

        if headless:
            await _save_qr_code(page)
            print(f"       QR 二维码已保存至: {QR_CODE_PATH}")
            print("       请使用微信扫描该图片中的二维码登录...")

        print("       等待扫码登录...")

        try:
            await page.wait_for_url(
                lambda url: "/cgi-bin/home" in url and "token=" in url,
                timeout=timeout_seconds * 1000,
            )
        except Exception:
            logger.error("登录超时，请重试")
            await browser.close()
            sys.exit(1)

        token = _extract_token_from_url(page.url)
        if not token:
            logger.error(f"无法从 URL 提取 token: {page.url}")
            await browser.close()
            sys.exit(1)
        print(f"       OK 登录成功  token = {token}")

        # =================================================================
        # STEP 2 – cookies
        # =================================================================
        print("\n[2/4] 正在提取 cookie ...")
        cookies = await context.cookies()
        cookie_str = _build_cookie_string(cookies)
        print(f"       OK 获取到 {len(cookies)} 个 cookie")

        # =================================================================
        # STEP 3 – navigate editor & search
        # =================================================================
        print("\n[3/4] 正在打开文章编辑器，搜索 '充电联盟' ...")
        editor_url = (
            "https://mp.weixin.qq.com/cgi-bin/appmsg"
            "?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77"
            f"&createType=0&token={token}&lang=zh_CN"
        )
        await page.goto(editor_url)
        await page.wait_for_load_state("networkidle")

        auto_ok = await _click_hyperlink_button(page)
        if auto_ok:
            auto_ok = await _search_charging_alliance(page)

        if not auto_ok:
            print("\n   ⚠ 自动操作未能完成，请手动执行以下步骤：")
            print("     1. 点击编辑器工具栏中的 超链接 按钮")
            print('     2. 在弹出的窗口中点击 "选择其他账号"')
            print('     3. 在搜索框输入 "充电联盟" 并搜索')
            input("\n   >>> 完成后按 Enter 继续 ... ")

        await page.wait_for_timeout(3000)

        # =================================================================
        # STEP 4 – extract fingerprint & fakeid
        # =================================================================
        print("\n[4/4] 正在从网络请求中提取 fingerprint 和 fakeid ...")

        for req in reversed(captured_requests):
            url = req.url
            if ("searchbiz" in url.lower() or "search_biz" in url.lower()) and "fingerprint=" in url:
                m = re.search(r"fingerprint=([^&]+)", url)
                if m:
                    fingerprint = m.group(1)
                    break

        if not fingerprint:
            for req in reversed(captured_requests):
                if "fingerprint=" in req.url:
                    m = re.search(r"fingerprint=([^&]+)", req.url)
                    if m:
                        fingerprint = m.group(1)
                        break

        for req in captured_requests:
            if "searchbiz" not in req.url.lower() and "search_biz" not in req.url.lower():
                continue
            try:
                resp = await req.response()
                if resp and resp.ok:
                    body = await resp.json()
                    for biz in body.get("list", []):
                        if "充电联盟" in biz.get("nickname", ""):
                            fakeid = biz.get("fakeid")
                            break
            except Exception:
                continue
            if fakeid:
                break

        if not fakeid:
            fakeid = KNOWN_FAKEID
            logger.info(f"使用已知 fakeid: {fakeid}")
        else:
            print(f"       OK fakeid = {fakeid}")

        if not fingerprint:
            print("\n   ⚠ 未能自动获取 fingerprint")
            fingerprint = input("   请手动输入 fingerprint (从浏览器 Network 面板复制): ").strip()
            if not fingerprint:
                logger.error("fingerprint 不能为空")
                await browser.close()
                sys.exit(1)
        else:
            print(f"       OK fingerprint = {fingerprint}")

        await browser.close()

    print("\n" + "=" * 60)
    print("  OK 登录凭证已获取，开始爬虫...")
    print("=" * 60)

    return {
        "cookie": cookie_str,
        "token": token,
        "fingerprint": fingerprint,
        "fakeid": fakeid,
    }
