"""
知乎登录管理
支持 Cookie 导入、扫码登录、登录态检查
"""

import json
import base64
import asyncio
import logging
from typing import Optional

from app.automation.browser_manager import browser_manager
from app.automation.anti_detect import HumanBehavior

logger = logging.getLogger(__name__)


class ZhihuAuth:
    """知乎登录管理器"""

    ZHIHU_HOME_URL = "https://www.zhihu.com"
    ZHIHU_LOGIN_URL = "https://www.zhihu.com/signin"
    ZHIHU_PROFILE_API = "https://www.zhihu.com/api/v4/me"

    async def check_login(self, profile_name: str) -> dict:
        """
        检查知乎登录态

        通过访问个人 API 接口判断是否已登录

        Args:
            profile_name: 浏览器配置文件名

        Returns:
            dict: {
                "is_logged_in": bool,
                "nickname": str | None,
                "message": str
            }
        """
        logger.info(f"检查登录态: {profile_name}")

        page = None
        try:
            context = await browser_manager.get_persistent_context(profile_name)
            page = await browser_manager.new_page(context)

            # 访问知乎首页
            await page.goto(self.ZHIHU_HOME_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(2000, 3000)

            # 尝试调用个人信息 API
            response = await page.evaluate("""
                async () => {
                    try {
                        const res = await fetch('https://www.zhihu.com/api/v4/me', {
                            credentials: 'include'
                        });
                        if (res.ok) {
                            const data = await res.json();
                            return { success: true, name: data.name || '' };
                        }
                        return { success: false, name: '' };
                    } catch (e) {
                        return { success: false, name: '' };
                    }
                }
            """)

            if response and response.get("success"):
                nickname = response.get("name", "")
                logger.info(f"登录态有效: {nickname}")
                return {
                    "is_logged_in": True,
                    "nickname": nickname,
                    "message": f"登录态有效，当前用户: {nickname}",
                }
            else:
                # 通过页面元素判断
                try:
                    avatar = await page.wait_for_selector(
                        'button[aria-label="个人中心"], .AppHeader-profileAvatar',
                        timeout=5000,
                    )
                    if avatar:
                        return {
                            "is_logged_in": True,
                            "nickname": "",
                            "message": "登录态有效（通过页面元素检测）",
                        }
                except Exception:
                    pass

                logger.info("登录态无效")
                return {
                    "is_logged_in": False,
                    "nickname": None,
                    "message": "未登录或登录已过期",
                }

        except Exception as e:
            logger.error(f"检查登录态失败: {e}")
            return {
                "is_logged_in": False,
                "nickname": None,
                "message": f"检查失败: {str(e)}",
            }
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def cookie_login(
        self, profile_name: str, cookie_data: str
    ) -> dict:
        """
        通过导入 Cookie 登录

        支持三种格式：
        1. JSON 数组: [{"name": "...", "value": "...", ...}, ...]
        2. JSON 对象: {"key1": "val1", "key2": "val2", ...}
        3. 分号分隔: "key1=val1; key2=val2; ..."

        Args:
            profile_name: 浏览器配置文件名
            cookie_data: Cookie 数据

        Returns:
            dict: {"success": bool, "message": str}
        """
        logger.info(f"Cookie 导入登录: {profile_name}")

        try:
            context = await browser_manager.get_persistent_context(profile_name)

            # 解析 Cookie
            cookies = self._parse_cookies(cookie_data)
            if not cookies:
                return {"success": False, "message": "无法解析 Cookie 数据，请检查格式"}

            # 添加 Cookie 到浏览器上下文
            await context.add_cookies(cookies)
            logger.info(f"已导入 {len(cookies)} 个 Cookie")

            # 验证登录
            result = await self.check_login(profile_name)
            if result["is_logged_in"]:
                return {"success": True, "message": "Cookie 登录成功"}
            else:
                return {"success": False, "message": "Cookie 无效或已过期"}

        except Exception as e:
            logger.error(f"Cookie 登录失败: {e}")
            return {"success": False, "message": f"登录失败: {str(e)}"}

    async def qrcode_login(self, profile_name: str, account_id: int = 0) -> dict:
        """
        扫码登录
        打开知乎登录页面，截取二维码图片返回 base64

        Args:
            profile_name: 浏览器配置文件名
            account_id: 账号ID，用于扫码成功后更新数据库

        Returns:
            dict: {
                "success": bool,
                "qrcode_base64": str | None,  (base64 编码的二维码图片)
                "message": str
            }
        """
        logger.info(f"扫码登录: {profile_name}")

        page = None
        try:
            context = await browser_manager.get_persistent_context(profile_name)
            page = await browser_manager.new_page(context)

            # 访问知乎登录页
            await page.goto(self.ZHIHU_LOGIN_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(2000, 4000)

            # 点击「扫码登录」 tab（如果存在的话）
            try:
                qr_tab = page.locator(
                    'div[class*="QRCode"], '
                    'button:has-text("扫码登录"), '
                    'div:has-text("扫码登录")'
                )
                if await qr_tab.count() > 0:
                    await qr_tab.first.click()
                    await HumanBehavior.random_delay(1000, 2000)
            except Exception:
                logger.info("未找到扫码登录 tab，可能已经在扫码页")

            # 等待二维码出现
            qr_image = None
            qr_selectors = [
                'img[alt*="二维码"]',
                'img[class*="qrcode"]',
                'img[class*="QRCode"]',
                'div[class*="QRCode"] img',
                'canvas[class*="qrcode"]',
                '.SignFlow-qrcode img',
            ]

            for selector in qr_selectors:
                try:
                    qr_image = await page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if qr_image:
                        break
                except Exception:
                    continue

            if qr_image:
                # 截取二维码图片
                screenshot_bytes = await qr_image.screenshot()
                qrcode_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                logger.info("已获取二维码截图")

                # 启动后台任务等待用户扫码（传入 account_id 以便更新数据库）
                # 注意：page 的所有权转移给后台任务，不在此处关闭
                task = asyncio.create_task(
                    self._wait_for_qr_scan(page, profile_name, account_id)
                )
                task.add_done_callback(self._on_scan_task_done)
                # page 已交给后台任务管理，不在 finally 中关闭
                page = None

                return {
                    "success": True,
                    "qrcode_base64": qrcode_base64,
                    "message": "请使用知乎 APP 扫描二维码",
                }
            else:
                # 如果找不到二维码元素，截取整个页面
                screenshot_bytes = await page.screenshot()
                qrcode_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                # 同样启动后台任务等待扫码（用户可能手动在页面上操作）
                task = asyncio.create_task(
                    self._wait_for_qr_scan(page, profile_name, account_id)
                )
                task.add_done_callback(self._on_scan_task_done)
                # page 已交给后台任务管理
                page = None

                return {
                    "success": True,
                    "qrcode_base64": qrcode_base64,
                    "message": "未找到二维码元素，已返回登录页截图，请查看",
                }

        except Exception as e:
            logger.error(f"扫码登录失败: {type(e).__name__}: {e}")
            return {
                "success": False,
                "qrcode_base64": None,
                "message": f"扫码登录失败: {str(e)}",
            }
        finally:
            # 只有在 page 没有被后台任务接管时才关闭
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _wait_for_qr_scan(self, page, profile_name: str, account_id: int = 0):
        """
        后台等待用户扫码完成
        扫码成功后页面会自动跳转，并更新数据库中的登录状态

        Args:
            page: Playwright Page 对象
            profile_name: 浏览器配置文件名
            account_id: 账号ID，用于更新数据库
        """
        logger.info(f"等待用户扫码: {profile_name}")

        scan_success = False
        try:
            # 等待页面跳转（最多等待 120 秒）
            for _ in range(120):
                await asyncio.sleep(1)
                try:
                    current_url = page.url
                except Exception:
                    logger.warning(f"扫码等待中页面已关闭: {profile_name}")
                    break
                # 如果跳转到了首页或非登录页，说明登录成功
                if "signin" not in current_url and "login" not in current_url:
                    logger.info(f"扫码登录成功: {profile_name}")
                    scan_success = True
                    break
            else:
                logger.warning(f"扫码超时（120秒）: {profile_name}")

        except Exception as e:
            logger.error(f"等待扫码失败: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass

        # 扫码成功后更新数据库中的账号登录状态
        if scan_success and account_id:
            try:
                from app.database.connection import async_session_factory
                from app.models.account import Account

                async with async_session_factory() as session:
                    account = await session.get(Account, account_id)
                    if account:
                        account.login_status = "logged_in"
                        # 尝试获取昵称
                        try:
                            check_result = await self.check_login(profile_name)
                            if check_result.get("nickname"):
                                account.nickname = check_result["nickname"]
                        except Exception:
                            pass
                        await session.commit()
                        logger.info(f"已更新账号登录状态: account_id={account_id}")
            except Exception as e:
                logger.error(f"更新账号登录状态失败: {e}")

    @staticmethod
    def _on_scan_task_done(task: asyncio.Task):
        """记录扫码后台任务中的未处理异常"""
        if task.cancelled():
            logger.info("扫码等待任务已取消")
            return
        exc = task.exception()
        if exc:
            logger.error(f"扫码等待任务异常: {exc}")

    def _parse_cookies(self, cookie_data: str) -> list[dict]:
        """
        解析 Cookie 数据

        支持三种格式：
        1. JSON 数组格式: [{"name": "...", "value": "...", ...}, ...]
        2. JSON 对象格式: {"key1": "val1", "key2": "val2", ...}
        3. 分号分隔格式: "key1=val1; key2=val2; ..."

        Args:
            cookie_data: Cookie 字符串

        Returns:
            list[dict]: Playwright 格式的 Cookie 列表
        """
        cookie_data = cookie_data.strip()
        cookies = []

        # 尝试 JSON 格式
        try:
            parsed = json.loads(cookie_data)

            if isinstance(parsed, list):
                # JSON 数组格式
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name", "")).strip()
                    value = str(item.get("value", "")).strip()
                    if not name:
                        continue
                    cookie = {
                        "name": name,
                        "value": value,
                        "domain": item.get("domain", ".zhihu.com"),
                        "path": item.get("path", "/"),
                    }
                    cookies.append(cookie)
                return cookies

            elif isinstance(parsed, dict):
                # JSON 对象格式: {"key1": "val1", ...}
                for name, value in parsed.items():
                    name = str(name).strip()
                    value = str(value).strip()
                    if not name:
                        continue
                    cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".zhihu.com",
                        "path": "/",
                    })
                return cookies

        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试分号分隔格式: "key1=val1; key2=val2"
        if "=" in cookie_data:
            pairs = cookie_data.split(";")
            for pair in pairs:
                pair = pair.strip()
                if "=" in pair:
                    name, _, value = pair.partition("=")
                    name = name.strip()
                    value = value.strip()
                    if not name:
                        continue
                    cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".zhihu.com",
                        "path": "/",
                    })

        return cookies


# 全局单例
zhihu_auth = ZhihuAuth()
