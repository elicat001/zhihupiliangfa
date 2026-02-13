"""
知乎自动发文
使用 Playwright 自动化操作知乎专栏发文页面
"""

import os
import random
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.automation.browser_manager import browser_manager
from app.automation.anti_detect import HumanBehavior

logger = logging.getLogger(__name__)


class ZhihuPublisher:
    """
    知乎文章发布器
    自动化操作知乎专栏写文章页面，完成文章发布
    """

    WRITE_URL = "https://zhuanlan.zhihu.com/write"

    async def publish_article(
        self,
        profile_name: str,
        title: str,
        content: str,
        tags: Optional[list[str]] = None,
        images: Optional[dict] = None,
    ) -> dict:
        """
        发布文章到知乎专栏

        流程：
        1. 打开知乎专栏写作页面
        2. 填入标题
        3. 通过剪贴板粘贴内容
        4. 添加话题标签
        5. 点击发布
        6. 截图存档
        7. 获取发布后的文章 URL

        Args:
            profile_name: 浏览器配置文件名
            title: 文章标题
            content: 文章内容（Markdown / HTML）
            tags: 话题标签列表

        Returns:
            dict: {
                "success": bool,
                "article_url": str | None,
                "screenshot_path": str | None,
                "message": str
            }
        """
        logger.info(f"开始发布文章: {title[:30]}... (使用账号: {profile_name})")

        page = None
        try:
            context = await browser_manager.get_persistent_context(profile_name)
            page = await browser_manager.new_page(context)

            # ========== Step 1: 打开写作页面 ==========
            logger.info("Step 1/7: 打开知乎写作页面...")
            await page.goto(self.WRITE_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(3000, 5000)

            # 检查是否被重定向到登录页
            if "signin" in page.url or "login" in page.url:
                screenshot_path = await self._take_screenshot(
                    page, f"not_logged_in_{profile_name}"
                )
                return {
                    "success": False,
                    "article_url": None,
                    "screenshot_path": screenshot_path,
                    "message": "账号未登录或登录已过期，请重新登录",
                }

            # ========== Step 2: 填入标题 ==========
            logger.info("Step 2/7: 填入文章标题...")
            title_selector = (
                'textarea[placeholder*="请输入标题"], '
                'textarea.WriteIndex-titleInput, '
                'input[placeholder*="标题"]'
            )
            try:
                await page.wait_for_selector(title_selector, timeout=10000)
                await HumanBehavior.random_delay(500, 1000)

                # 清除已有内容
                title_element = page.locator(title_selector).first
                await title_element.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await HumanBehavior.random_delay(300, 500)

                # 逐字输入标题，模拟人类打字
                for char in title:
                    delay = 50 + int(30 * random.random())
                    await page.keyboard.type(char, delay=delay)
                    if random.random() < 0.03:
                        await HumanBehavior.random_delay(200, 600)

            except Exception as e:
                logger.error(f"标题输入失败: {e}")
                screenshot_path = await self._take_screenshot(
                    page, f"error_title_{profile_name}"
                )
                return {
                    "success": False,
                    "article_url": None,
                    "screenshot_path": screenshot_path,
                    "message": f"标题输入失败: {str(e)}",
                }

            await HumanBehavior.random_delay(1000, 2000)

            # ========== Step 3: 填入正文内容 ==========
            logger.info("Step 3/7: 填入文章正文...")
            content_selector = (
                '.public-DraftEditor-content, '
                'div[contenteditable="true"], '
                '.WriteIndex-contentInput'
            )
            try:
                await page.wait_for_selector(content_selector, timeout=10000)
                content_element = page.locator(content_selector).first
                await content_element.click()
                await HumanBehavior.random_delay(500, 1000)

                # 将 Markdown 内容转换为 HTML 并通过剪贴板粘贴
                html_content = self._markdown_to_html(content)
                await self._paste_content(page, html_content)

            except Exception as e:
                logger.error(f"正文输入失败: {e}")
                screenshot_path = await self._take_screenshot(
                    page, f"error_content_{profile_name}"
                )
                return {
                    "success": False,
                    "article_url": None,
                    "screenshot_path": screenshot_path,
                    "message": f"正文输入失败: {str(e)}",
                }

            await HumanBehavior.random_delay(2000, 3000)
            await HumanBehavior.random_scroll(page, times=2)

            # ========== Step 4: 添加话题标签 ==========
            if tags:
                logger.info(f"Step 4/7: 添加话题标签: {tags}")
                await self._add_tags(page, tags)
                await HumanBehavior.random_delay(1000, 2000)
            else:
                logger.info("Step 4/7: 无话题标签，跳过")

            # ========== Step 5: 点击发布 ==========
            logger.info("Step 5/7: 点击发布按钮...")
            publish_success = await self._click_publish(page)

            if not publish_success:
                # 截图保存失败现场
                error_screenshot = await self._take_screenshot(
                    page, f"error_publish_{profile_name}"
                )
                return {
                    "success": False,
                    "article_url": None,
                    "screenshot_path": error_screenshot,
                    "message": "发布失败，未能找到或点击发布按钮",
                }

            await HumanBehavior.random_delay(3000, 5000)

            # ========== Step 6: 截图存档 ==========
            logger.info("Step 6/7: 发布完成，截图存档...")
            screenshot_path = await self._take_screenshot(
                page, f"published_{profile_name}"
            )

            # ========== Step 7: 获取文章 URL ==========
            logger.info("Step 7/7: 获取文章 URL...")
            article_url = page.url
            if "zhuanlan.zhihu.com/p/" in article_url:
                logger.info(f"文章发布成功: {article_url}")
            else:
                # 尝试从页面中提取链接
                article_url = await self._get_article_url(page)

            return {
                "success": True,
                "article_url": article_url,
                "screenshot_path": screenshot_path,
                "message": "文章发布成功",
            }

        except Exception as e:
            logger.error(f"发布文章失败: {e}")
            # 尝试截图保存失败现场
            screenshot_path = None
            if page:
                try:
                    screenshot_path = await self._take_screenshot(
                        page, f"error_{profile_name}"
                    )
                except Exception:
                    pass

            return {
                "success": False,
                "article_url": None,
                "screenshot_path": screenshot_path,
                "message": f"发布失败: {str(e)}",
            }
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _paste_content(self, page, html_content: str):
        """
        通过剪贴板粘贴 HTML 内容到编辑器

        知乎编辑器支持富文本粘贴，我们利用这个特性
        将 HTML 内容设置到剪贴板后粘贴

        Args:
            page: Playwright Page 对象
            html_content: HTML 格式的内容
        """
        # 方案1: 使用 evaluate 设置剪贴板内容并触发粘贴事件
        await page.evaluate(
            """
            async (html) => {
                // 创建一个临时 div 来持有 HTML 内容
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;

                // 获取当前焦点元素
                const editor = document.querySelector(
                    '.public-DraftEditor-content, div[contenteditable="true"]'
                );
                if (!editor) return;

                editor.focus();

                // 尝试使用 Clipboard API
                try {
                    const blob = new Blob([html], { type: 'text/html' });
                    const clipboardItem = new ClipboardItem({
                        'text/html': blob,
                        'text/plain': new Blob([tempDiv.textContent], { type: 'text/plain' })
                    });
                    await navigator.clipboard.write([clipboardItem]);
                } catch (e) {
                    // 降级方案：使用 execCommand
                    const selection = window.getSelection();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand('insertHTML', false, html);
                    return;
                }
            }
            """,
            html_content,
        )

        await HumanBehavior.random_delay(500, 1000)

        # 执行粘贴
        await page.keyboard.press("Control+V")
        await HumanBehavior.random_delay(1000, 2000)

        # 验证内容是否已粘贴
        editor_text = await page.evaluate("""
            () => {
                const editor = document.querySelector(
                    '.public-DraftEditor-content, div[contenteditable="true"]'
                );
                return editor ? editor.innerText.length : 0;
            }
        """)

        if editor_text < 10:
            # 降级方案：直接插入 HTML
            logger.warning("剪贴板粘贴失败，使用降级方案直接插入 HTML")
            await page.evaluate(
                """
                (html) => {
                    const editor = document.querySelector(
                        '.public-DraftEditor-content, div[contenteditable="true"]'
                    );
                    if (editor) {
                        editor.focus();
                        document.execCommand('insertHTML', false, html);
                    }
                }
                """,
                html_content,
            )
            await HumanBehavior.random_delay(1000, 2000)

    async def _add_tags(self, page, tags: list[str]):
        """
        添加话题标签

        Args:
            page: Playwright Page 对象
            tags: 标签列表
        """
        try:
            # 知乎写作页面的话题选择按钮
            topic_button_selectors = [
                'button:has-text("添加话题")',
                'div[class*="TopicSelector"]',
                '.WriteIndex-topicInput',
                'button:has-text("话题")',
            ]

            topic_button = None
            for selector in topic_button_selectors:
                try:
                    locator = page.locator(selector)
                    if await locator.count() > 0:
                        topic_button = locator.first
                        break
                except Exception:
                    continue

            if not topic_button:
                logger.warning("未找到话题标签按钮，跳过标签添加")
                return

            await topic_button.click()
            await HumanBehavior.random_delay(1000, 2000)

            # 逐个添加标签
            for tag in tags[:5]:  # 最多 5 个标签
                tag_input_selectors = [
                    'input[placeholder*="搜索话题"]',
                    'input[placeholder*="话题"]',
                    'input[class*="TopicSelector"]',
                ]

                tag_input = None
                for selector in tag_input_selectors:
                    try:
                        locator = page.locator(selector)
                        if await locator.count() > 0:
                            tag_input = locator.first
                            break
                    except Exception:
                        continue

                if not tag_input:
                    logger.warning("未找到话题输入框")
                    break

                # 输入标签
                await tag_input.click()
                await tag_input.fill("")  # 清空
                await HumanBehavior.random_delay(200, 500)

                for char in tag:
                    await page.keyboard.type(char, delay=80)

                await HumanBehavior.random_delay(1000, 2000)

                # 从下拉列表中选择第一个匹配的话题
                try:
                    suggestion = page.locator(
                        'div[class*="TopicSelector"] li, '
                        'ul[class*="suggest"] li, '
                        '.Popover-content li'
                    ).first
                    if await suggestion.count() > 0:
                        await suggestion.click()
                        await HumanBehavior.random_delay(500, 1000)
                except Exception:
                    # 如果没有建议列表，按回车确认
                    await page.keyboard.press("Enter")
                    await HumanBehavior.random_delay(500, 1000)

        except Exception as e:
            logger.error(f"添加话题标签失败: {e}")

    async def _click_publish(self, page) -> bool:
        """
        点击发布按钮

        Args:
            page: Playwright Page 对象

        Returns:
            bool: 是否成功点击
        """
        publish_selectors = [
            'button:has-text("发布文章")',
            'button:has-text("发布")',
            'button[class*="PublishButton"]',
            '.WriteIndex-publishButton',
            'button.Button--primary:has-text("发布")',
        ]

        for selector in publish_selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0:
                    await HumanBehavior.human_click(page, selector)
                    logger.info(f"已点击发布按钮: {selector}")

                    # 等待可能出现的确认对话框
                    await HumanBehavior.random_delay(1000, 2000)

                    # 如果有确认发布的弹窗
                    confirm_selectors = [
                        'button:has-text("确认发布")',
                        'button:has-text("确认")',
                        '.Modal-footer button.Button--primary',
                    ]
                    for confirm_sel in confirm_selectors:
                        try:
                            confirm_btn = page.locator(confirm_sel)
                            if await confirm_btn.count() > 0:
                                await confirm_btn.first.click()
                                logger.info("已确认发布")
                                break
                        except Exception:
                            continue

                    return True
            except Exception:
                continue

        logger.error("未找到发布按钮")
        return False

    async def _take_screenshot(self, page, prefix: str) -> Optional[str]:
        """
        截图并保存

        Args:
            page: Playwright Page 对象
            prefix: 文件名前缀

        Returns:
            str | None: 截图文件路径
        """
        try:
            os.makedirs(settings.SCREENSHOT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(settings.SCREENSHOT_DIR, filename)

            await page.screenshot(path=filepath, full_page=True)
            logger.info(f"截图已保存: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None

    async def _get_article_url(self, page) -> Optional[str]:
        """
        从发布成功后的页面获取文章 URL

        Args:
            page: Playwright Page 对象

        Returns:
            str | None: 文章 URL
        """
        try:
            # 等待页面跳转
            await HumanBehavior.random_delay(2000, 3000)
            url = page.url

            if "zhuanlan.zhihu.com/p/" in url:
                return url

            # 尝试从页面中提取
            article_link = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="zhuanlan.zhihu.com/p/"]');
                    if (links.length > 0) return links[0].href;
                    return null;
                }
            """)

            return article_link or url

        except Exception as e:
            logger.error(f"获取文章 URL 失败: {e}")
            return None

    @staticmethod
    def _markdown_to_html(markdown_text: str) -> str:
        """
        简单的 Markdown 转 HTML
        用于将 AI 生成的 Markdown 内容转换为富文本

        Args:
            markdown_text: Markdown 文本

        Returns:
            str: HTML 文本
        """
        import re

        html = markdown_text

        # 处理图片 ![alt](url) -> <figure><img>
        html = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            r'<figure style="text-align:center;margin:16px 0">'
            r'<img src="\2" alt="\1" style="max-width:100%">'
            r'<figcaption style="color:#999;font-size:14px;margin-top:4px">\1</figcaption>'
            r'</figure>',
            html,
        )

        # 处理代码块（先处理，避免被其他规则干扰）
        html = re.sub(
            r"```(\w*)\n(.*?)```",
            r"<pre><code>\2</code></pre>",
            html,
            flags=re.DOTALL,
        )

        # 处理标题 ### -> <h3>（从高级到低级）
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # 处理粗体 **text** -> <strong>text</strong>
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        # 处理斜体 *text* -> <em>text</em>
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # 处理行内代码 `code` -> <code>code</code>
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # 处理无序列表项 - item -> <li class="ul">item</li>
        html = re.sub(
            r"^- (.+)$", r'<li class="ul">\1</li>', html, flags=re.MULTILINE
        )

        # 处理有序列表项 1. item -> <li class="ol">item</li>
        html = re.sub(
            r"^\d+\. (.+)$", r'<li class="ol">\1</li>', html, flags=re.MULTILINE
        )

        # 将连续的无序列表项包裹到 <ul>
        html = re.sub(
            r'(<li class="ul">.*?</li>\n?)+',
            lambda m: "<ul>" + re.sub(r' class="ul"', "", m.group()) + "</ul>",
            html,
        )

        # 将连续的有序列表项包裹到 <ol>
        html = re.sub(
            r'(<li class="ol">.*?</li>\n?)+',
            lambda m: "<ol>" + re.sub(r' class="ol"', "", m.group()) + "</ol>",
            html,
        )

        # 处理引用 > text -> <blockquote>text</blockquote>
        html = re.sub(
            r"^> (.+)$",
            r"<blockquote>\1</blockquote>",
            html,
            flags=re.MULTILINE,
        )

        # 处理分割线
        html = re.sub(r"^---+$", r"<hr>", html, flags=re.MULTILINE)

        # 处理段落：连续两个换行分隔的文本块
        paragraphs = html.split("\n\n")
        processed = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # 如果已经被标签包裹，不再添加 <p>
            if p.startswith(("<h", "<ul", "<ol", "<blockquote", "<pre", "<hr", "<figure")):
                processed.append(p)
            else:
                # 替换单个换行为 <br>
                p = p.replace("\n", "<br>")
                processed.append(f"<p>{p}</p>")

        return "\n".join(processed)


# 全局单例
zhihu_publisher = ZhihuPublisher()
