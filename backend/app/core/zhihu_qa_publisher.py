"""
知乎回答自动发布器
使用 Playwright 自动化操作知乎问题页面，提交回答
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


class ZhihuQAPublisher:
    """
    知乎回答发布器
    自动化操作知乎问题页面，完成回答提交

    流程：
    1. 打开问题页面
    2. 点击"写回答"按钮
    3. 在编辑器中粘贴回答内容
    4. 点击发布
    5. 截图存档
    6. 获取回答URL
    """

    QUESTION_URL = "https://www.zhihu.com/question/{}"

    async def publish_answer(
        self,
        profile_name: str,
        question_id: str,
        content: str,
    ) -> dict:
        """
        发布回答到知乎问题

        Args:
            profile_name: 浏览器配置文件名
            question_id: 知乎问题ID
            content: 回答内容（Markdown）

        Returns:
            dict: {
                "success": bool,
                "answer_url": str | None,
                "screenshot_path": str | None,
                "message": str,
            }
        """
        url = self.QUESTION_URL.format(question_id)
        logger.info(f"开始发布回答: 问题ID={question_id} (账号: {profile_name})")

        page = None
        try:
            context = await browser_manager.get_persistent_context(profile_name)
            page = await browser_manager.new_page(context)

            # ========== Step 1: 打开问题页面 ==========
            logger.info("Step 1/6: 打开问题页面...")
            await page.goto(url, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(3000, 5000)

            # 检查是否被重定向到登录页
            if "signin" in page.url or "login" in page.url:
                screenshot_path = await self._take_screenshot(
                    page, f"qa_not_logged_in_{profile_name}"
                )
                return {
                    "success": False,
                    "answer_url": None,
                    "screenshot_path": screenshot_path,
                    "message": "账号未登录或登录已过期，请重新登录",
                }

            # 模拟阅读问题
            await HumanBehavior.random_scroll(page, times=2)
            await HumanBehavior.random_delay(1000, 2000)

            # ========== Step 2: 点击"写回答"按钮 ==========
            logger.info("Step 2/6: 点击写回答按钮...")
            write_answer_clicked = await self._click_write_answer(page)

            if not write_answer_clicked:
                screenshot_path = await self._take_screenshot(
                    page, f"qa_no_write_btn_{profile_name}"
                )
                return {
                    "success": False,
                    "answer_url": None,
                    "screenshot_path": screenshot_path,
                    "message": "未找到'写回答'按钮，可能已回答过或页面结构变化",
                }

            await HumanBehavior.random_delay(2000, 3000)

            # ========== Step 3: 填入回答内容 ==========
            logger.info("Step 3/6: 填入回答内容...")
            content_filled = await self._fill_answer_content(page, content)

            if not content_filled:
                screenshot_path = await self._take_screenshot(
                    page, f"qa_content_failed_{profile_name}"
                )
                return {
                    "success": False,
                    "answer_url": None,
                    "screenshot_path": screenshot_path,
                    "message": "填入回答内容失败",
                }

            await HumanBehavior.random_delay(2000, 3000)
            await HumanBehavior.random_scroll(page, times=1)

            # ========== Step 4: 点击发布回答 ==========
            logger.info("Step 4/6: 点击发布回答...")
            publish_success = await self._click_submit(page)

            if not publish_success:
                screenshot_path = await self._take_screenshot(
                    page, f"qa_publish_failed_{profile_name}"
                )
                return {
                    "success": False,
                    "answer_url": None,
                    "screenshot_path": screenshot_path,
                    "message": "点击发布按钮失败",
                }

            await HumanBehavior.random_delay(3000, 5000)

            # ========== Step 5: 截图存档 ==========
            logger.info("Step 5/6: 截图存档...")
            screenshot_path = await self._take_screenshot(
                page, f"qa_published_{profile_name}"
            )

            # ========== Step 6: 获取回答URL ==========
            logger.info("Step 6/6: 获取回答URL...")
            answer_url = await self._get_answer_url(page, question_id)

            logger.info(f"回答发布成功: {answer_url or page.url}")

            return {
                "success": True,
                "answer_url": answer_url,
                "screenshot_path": screenshot_path,
                "message": "回答发布成功",
            }

        except Exception as e:
            logger.error(f"发布回答失败: {e}")
            screenshot_path = None
            if page:
                try:
                    screenshot_path = await self._take_screenshot(
                        page, f"qa_error_{profile_name}"
                    )
                except Exception:
                    pass

            return {
                "success": False,
                "answer_url": None,
                "screenshot_path": screenshot_path,
                "message": f"发布失败: {str(e)}",
            }
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _click_write_answer(self, page) -> bool:
        """点击写回答按钮"""
        selectors = [
            'button:has-text("写回答")',
            'a:has-text("写回答")',
            '.QuestionAnswer-writeButton',
            'button[class*="WriteAnswer"]',
            '.AnswerForm button:has-text("写回答")',
            'div[class*="AnswerButton"] button',
        ]

        for selector in selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0:
                    await button.first.click()
                    logger.info(f"已点击写回答按钮: {selector}")
                    await HumanBehavior.random_delay(1000, 2000)
                    return True
            except Exception:
                continue

        # Fallback: try to find and click any element that contains "写回答"
        try:
            elements = page.get_by_text("写回答", exact=False)
            if await elements.count() > 0:
                await elements.first.click()
                logger.info("通过文本匹配点击了写回答")
                return True
        except Exception:
            pass

        # Another fallback: check if editor is already visible
        # (maybe the write answer area is already expanded)
        editor_selectors = [
            '.public-DraftEditor-content',
            'div[contenteditable="true"]',
            '.RichTextEditor',
            '.AnswerForm-editor',
        ]
        for sel in editor_selectors:
            try:
                if await page.locator(sel).count() > 0:
                    logger.info("编辑器已展开，无需点击写回答")
                    return True
            except Exception:
                continue

        return False

    async def _fill_answer_content(self, page, content: str) -> bool:
        """在编辑器中填入回答内容"""
        # Wait for editor to be ready
        editor_selectors = [
            '.public-DraftEditor-content',
            'div[contenteditable="true"]',
            '.RichTextEditor div[contenteditable]',
            '.AnswerForm-editor div[contenteditable]',
            '.Editable[contenteditable="true"]',
        ]

        editor = None
        for selector in editor_selectors:
            try:
                await page.wait_for_selector(selector, timeout=8000)
                locator = page.locator(selector)
                if await locator.count() > 0:
                    editor = locator.first
                    break
            except Exception:
                continue

        if not editor:
            logger.error("未找到回答编辑器")
            return False

        try:
            await editor.click()
            await HumanBehavior.random_delay(500, 1000)

            # Convert markdown to HTML
            html_content = self._markdown_to_html(content)

            # Paste via clipboard (same approach as zhihu_publisher)
            await page.evaluate(
                """
                async (html) => {
                    const editor = document.querySelector(
                        '.public-DraftEditor-content, div[contenteditable="true"], .Editable[contenteditable="true"]'
                    );
                    if (!editor) return;
                    editor.focus();

                    try {
                        const blob = new Blob([html], { type: 'text/html' });
                        const clipboardItem = new ClipboardItem({
                            'text/html': blob,
                            'text/plain': new Blob([html.replace(/<[^>]*>/g, '')], { type: 'text/plain' })
                        });
                        await navigator.clipboard.write([clipboardItem]);
                    } catch (e) {
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
            await page.keyboard.press("Control+V")
            await HumanBehavior.random_delay(1000, 2000)

            # Verify content was pasted
            editor_text = await page.evaluate("""
                () => {
                    const editor = document.querySelector(
                        '.public-DraftEditor-content, div[contenteditable="true"], .Editable[contenteditable="true"]'
                    );
                    return editor ? editor.innerText.length : 0;
                }
            """)

            if editor_text < 10:
                logger.warning("剪贴板粘贴失败，使用降级方案")
                await page.evaluate(
                    """
                    (html) => {
                        const editor = document.querySelector(
                            '.public-DraftEditor-content, div[contenteditable="true"], .Editable[contenteditable="true"]'
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

            logger.info(f"回答内容已填入 (长度: {editor_text})")
            return True

        except Exception as e:
            logger.error(f"填入回答内容失败: {e}")
            return False

    async def _click_submit(self, page) -> bool:
        """点击提交/发布回答按钮"""
        submit_selectors = [
            'button:has-text("提交回答")',
            'button:has-text("发布回答")',
            '.AnswerForm-submit button',
            'button[class*="SubmitButton"]',
            '.AnswerForm button.Button--primary',
            'button.Button--primary:has-text("发布")',
            'button:has-text("发布")',
        ]

        for selector in submit_selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0:
                    await HumanBehavior.random_delay(500, 1000)
                    await button.first.click()
                    logger.info(f"已点击发布回答: {selector}")

                    # Handle possible confirmation dialog
                    await HumanBehavior.random_delay(1000, 2000)
                    confirm_selectors = [
                        'button:has-text("确认")',
                        'button:has-text("确定")',
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

        logger.error("未找到发布回答按钮")
        return False

    async def _take_screenshot(self, page, prefix: str) -> Optional[str]:
        """截图存档"""
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

    async def _get_answer_url(self, page, question_id: str) -> Optional[str]:
        """获取发布后的回答URL"""
        try:
            await HumanBehavior.random_delay(2000, 3000)
            url = page.url

            # Check if URL contains answer id
            if f"/question/{question_id}/answer/" in url:
                return url

            # Try to extract from page
            answer_url = await page.evaluate("""
                (qid) => {
                    // Look for answer links
                    const links = document.querySelectorAll(
                        `a[href*="/question/${qid}/answer/"]`
                    );
                    if (links.length > 0) return links[links.length - 1].href;

                    // Check current URL
                    if (window.location.href.includes('/answer/')) {
                        return window.location.href;
                    }

                    // Fallback: return question URL
                    return window.location.href;
                }
            """, question_id)

            return answer_url or url
        except Exception as e:
            logger.error(f"获取回答URL失败: {e}")
            return None

    @staticmethod
    def _markdown_to_html(markdown_text: str) -> str:
        """Markdown 转 HTML（复用 zhihu_publisher 的逻辑）"""
        import re
        html = markdown_text

        # 处理代码块
        html = re.sub(
            r"```(\w*)\n(.*?)```",
            r"<pre><code>\2</code></pre>",
            html,
            flags=re.DOTALL,
        )

        # 处理标题
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # 粗体和斜体
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # 行内代码
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # 列表
        html = re.sub(
            r"^- (.+)$", r'<li class="ul">\1</li>', html, flags=re.MULTILINE
        )
        html = re.sub(
            r"^\d+\. (.+)$", r'<li class="ol">\1</li>', html, flags=re.MULTILINE
        )
        html = re.sub(
            r'(<li class="ul">.*?</li>\n?)+',
            lambda m: "<ul>" + re.sub(r' class="ul"', "", m.group()) + "</ul>",
            html,
        )
        html = re.sub(
            r'(<li class="ol">.*?</li>\n?)+',
            lambda m: "<ol>" + re.sub(r' class="ol"', "", m.group()) + "</ol>",
            html,
        )

        # 引用
        html = re.sub(
            r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE
        )

        # 分割线
        html = re.sub(r"^---+$", r"<hr>", html, flags=re.MULTILINE)

        # 段落处理
        paragraphs = html.split("\n\n")
        processed = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith(("<h", "<ul", "<ol", "<blockquote", "<pre", "<hr")):
                processed.append(p)
            else:
                p = p.replace("\n", "<br>")
                processed.append(f"<p>{p}</p>")

        return "\n".join(processed)


# 全局单例
zhihu_qa_publisher = ZhihuQAPublisher()
