"""
知乎问题抓取器
使用 Playwright 自动化从知乎抓取待回答问题
支持：邀请回答、推荐问题、话题问题、手动URL
"""

import logging
import random
import re
from datetime import datetime, timezone
from typing import Optional

from app.automation.browser_manager import browser_manager
from app.automation.anti_detect import HumanBehavior
from app.database.connection import async_session_factory
from app.models.qa import ZhihuQuestion
from app.models.account import Account
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


class ZhihuQAFetcher:
    """知乎问题抓取器"""

    # Zhihu URLs
    CREATOR_URL = "https://www.zhihu.com/creator"
    INVITE_URL = "https://www.zhihu.com/creator/invitation/question"
    RECOMMEND_URL = "https://www.zhihu.com/creator/recommendation/question"
    HOT_URL = "https://www.zhihu.com/hot"
    QUESTION_URL_TEMPLATE = "https://www.zhihu.com/question/{}"

    async def fetch_questions(
        self,
        profile_name: str,
        account_id: int,
        sources: list[str] = None,
        max_count: int = 20,
    ) -> dict:
        """
        从知乎抓取问题

        Args:
            profile_name: 浏览器配置文件名
            account_id: 账号ID
            sources: 抓取来源列表 ["invited", "recommended", "hot"]
            max_count: 最大抓取数量

        Returns:
            dict with total_fetched, new_questions, skipped_existing counts
        """
        if sources is None:
            sources = ["invited", "recommended"]

        logger.info(f"开始抓取问题 (账号: {profile_name}, 来源: {sources})")

        all_questions = []
        page = None

        try:
            context = await browser_manager.get_persistent_context(profile_name)
            page = await browser_manager.new_page(context)

            for source in sources:
                try:
                    if source == "invited":
                        questions = await self._fetch_invited(page, max_count)
                    elif source == "recommended":
                        questions = await self._fetch_recommended(page, max_count)
                    elif source == "hot":
                        questions = await self._fetch_hot(page, max_count)
                    else:
                        logger.warning(f"未知来源: {source}")
                        continue

                    for q in questions:
                        q["source"] = source
                    all_questions.extend(questions)
                    logger.info(f"从 {source} 抓取到 {len(questions)} 个问题")
                except Exception as e:
                    logger.error(f"抓取 {source} 失败: {e}")

            # Deduplicate by question_id
            seen = set()
            unique_questions = []
            for q in all_questions:
                if q["question_id"] not in seen:
                    seen.add(q["question_id"])
                    unique_questions.append(q)

            # Limit to max_count
            unique_questions = unique_questions[:max_count]

            # Save to database (skip existing)
            new_count = 0
            skipped = 0
            async with async_session_factory() as session:
                for q_data in unique_questions:
                    # Check if already exists
                    stmt = select(ZhihuQuestion).where(
                        ZhihuQuestion.question_id == q_data["question_id"]
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update counts only
                        existing.follower_count = q_data.get("follower_count", existing.follower_count)
                        existing.answer_count = q_data.get("answer_count", existing.answer_count)
                        existing.view_count = q_data.get("view_count", existing.view_count)
                        skipped += 1
                    else:
                        # Calculate score
                        score = self._calculate_score(q_data)

                        question = ZhihuQuestion(
                            question_id=q_data["question_id"],
                            title=q_data["title"],
                            detail=q_data.get("detail", ""),
                            topics=q_data.get("topics", []),
                            follower_count=q_data.get("follower_count", 0),
                            answer_count=q_data.get("answer_count", 0),
                            view_count=q_data.get("view_count", 0),
                            source=q_data["source"],
                            score=score,
                            status="pending",
                            account_id=account_id,
                            fetched_at=_utcnow(),
                        )
                        session.add(question)
                        new_count += 1

                await session.commit()

            result = {
                "total_fetched": len(unique_questions),
                "new_questions": new_count,
                "skipped_existing": skipped,
                "sources": sources,
            }
            logger.info(f"问题抓取完成: {result}")
            return result

        except Exception as e:
            logger.error(f"问题抓取失败: {e}")
            return {
                "total_fetched": 0,
                "new_questions": 0,
                "skipped_existing": 0,
                "error": str(e),
            }
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _fetch_invited(self, page, max_count: int) -> list[dict]:
        """抓取邀请回答的问题"""
        questions = []
        try:
            await page.goto(self.INVITE_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(3000, 5000)

            # Check login status
            if "signin" in page.url or "login" in page.url:
                logger.warning("账号未登录，无法抓取邀请问题")
                return []

            # Wait for content to load
            await HumanBehavior.random_delay(2000, 3000)

            # Scroll to load more
            for _ in range(3):
                await HumanBehavior.random_scroll(page, times=2)
                await HumanBehavior.random_delay(1500, 3000)

            # Extract questions - creator center invitation page
            # The page structure has question cards with titles and metadata
            items = await page.evaluate("""
                () => {
                    const results = [];
                    // Try multiple selectors for question items
                    const selectors = [
                        '.CreatorInvitation-questionItem',
                        '.QuestionItem',
                        '[class*="QuestionItem"]',
                        '.List-item',
                        'div[data-za-detail-view-path-module]',
                    ];

                    let elements = [];
                    for (const sel of selectors) {
                        elements = document.querySelectorAll(sel);
                        if (elements.length > 0) break;
                    }

                    // Fallback: find all links to question pages
                    if (elements.length === 0) {
                        const links = document.querySelectorAll('a[href*="/question/"]');
                        for (const link of links) {
                            const href = link.getAttribute('href') || '';
                            const match = href.match(/\\/question\\/(\\d+)/);
                            if (match) {
                                const title = link.textContent?.trim() || '';
                                if (title && title.length > 5) {
                                    results.push({
                                        question_id: match[1],
                                        title: title.substring(0, 500),
                                        detail: '',
                                        follower_count: 0,
                                        answer_count: 0,
                                        view_count: 0,
                                        topics: [],
                                    });
                                }
                            }
                        }
                        return results;
                    }

                    elements.forEach(el => {
                        try {
                            const titleEl = el.querySelector('a[href*="/question/"], h2, [class*="title"]');
                            if (!titleEl) return;

                            const href = titleEl.getAttribute('href') ||
                                         el.querySelector('a[href*="/question/"]')?.getAttribute('href') || '';
                            const match = href.match(/\\/question\\/(\\d+)/);
                            if (!match) return;

                            const title = titleEl.textContent?.trim() || '';
                            if (!title) return;

                            // Try to extract metadata
                            const metaText = el.textContent || '';
                            const followerMatch = metaText.match(/(\\d+)\\s*(?:人关注|个关注|关注)/);
                            const answerMatch = metaText.match(/(\\d+)\\s*(?:个回答|回答)/);
                            const viewMatch = metaText.match(/(\\d+)\\s*(?:次浏览|浏览)/);

                            // Extract topics
                            const topicEls = el.querySelectorAll('[class*="Topic"], .Tag');
                            const topics = Array.from(topicEls).map(t => t.textContent?.trim()).filter(Boolean);

                            results.push({
                                question_id: match[1],
                                title: title.substring(0, 500),
                                detail: '',
                                follower_count: followerMatch ? parseInt(followerMatch[1]) : 0,
                                answer_count: answerMatch ? parseInt(answerMatch[1]) : 0,
                                view_count: viewMatch ? parseInt(viewMatch[1]) : 0,
                                topics: topics,
                            });
                        } catch(e) {}
                    });

                    return results;
                }
            """)

            questions = items[:max_count] if items else []
            logger.info(f"邀请回答: 找到 {len(questions)} 个问题")

        except Exception as e:
            logger.error(f"抓取邀请问题失败: {e}")

        return questions

    async def _fetch_recommended(self, page, max_count: int) -> list[dict]:
        """抓取推荐回答的问题"""
        questions = []
        try:
            await page.goto(self.RECOMMEND_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(3000, 5000)

            if "signin" in page.url or "login" in page.url:
                logger.warning("账号未登录，无法抓取推荐问题")
                return []

            await HumanBehavior.random_delay(2000, 3000)

            # Scroll to load more
            for _ in range(3):
                await HumanBehavior.random_scroll(page, times=2)
                await HumanBehavior.random_delay(1500, 3000)

            # Extract questions using same logic
            items = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href*="/question/"]');
                    const seen = new Set();

                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        const match = href.match(/\\/question\\/(\\d+)/);
                        if (!match || seen.has(match[1])) continue;
                        seen.add(match[1]);

                        const title = link.textContent?.trim() || '';
                        if (!title || title.length < 5) continue;

                        // Walk up to find container
                        const container = link.closest('[class*="Item"], [class*="Card"], .List-item, div') || link;
                        const metaText = container.textContent || '';

                        const followerMatch = metaText.match(/(\\d+)\\s*(?:人关注|个关注|关注)/);
                        const answerMatch = metaText.match(/(\\d+)\\s*(?:个回答|回答)/);
                        const viewMatch = metaText.match(/(\\d+)\\s*(?:次浏览|浏览)/);

                        results.push({
                            question_id: match[1],
                            title: title.substring(0, 500),
                            detail: '',
                            follower_count: followerMatch ? parseInt(followerMatch[1]) : 0,
                            answer_count: answerMatch ? parseInt(answerMatch[1]) : 0,
                            view_count: viewMatch ? parseInt(viewMatch[1]) : 0,
                            topics: [],
                        });
                    }

                    return results;
                }
            """)

            questions = items[:max_count] if items else []
            logger.info(f"推荐回答: 找到 {len(questions)} 个问题")

        except Exception as e:
            logger.error(f"抓取推荐问题失败: {e}")

        return questions

    async def _fetch_hot(self, page, max_count: int) -> list[dict]:
        """抓取知乎热榜问题"""
        questions = []
        try:
            await page.goto(self.HOT_URL, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(3000, 5000)

            items = await page.evaluate("""
                () => {
                    const results = [];
                    const sections = document.querySelectorAll('.HotItem, [class*="HotItem"]');

                    if (sections.length === 0) {
                        // Fallback
                        const links = document.querySelectorAll('a[href*="/question/"]');
                        const seen = new Set();
                        for (const link of links) {
                            const href = link.getAttribute('href') || '';
                            const match = href.match(/\\/question\\/(\\d+)/);
                            if (!match || seen.has(match[1])) continue;
                            seen.add(match[1]);
                            const title = link.textContent?.trim() || '';
                            if (title && title.length > 5) {
                                results.push({
                                    question_id: match[1],
                                    title: title.substring(0, 500),
                                    detail: '',
                                    follower_count: 0,
                                    answer_count: 0,
                                    view_count: 0,
                                    topics: [],
                                });
                            }
                        }
                        return results;
                    }

                    sections.forEach(section => {
                        try {
                            const titleEl = section.querySelector('h2, [class*="title"], a[href*="/question/"]');
                            if (!titleEl) return;

                            const link = section.querySelector('a[href*="/question/"]');
                            const href = link?.getAttribute('href') || '';
                            const match = href.match(/\\/question\\/(\\d+)/);
                            if (!match) return;

                            const title = titleEl.textContent?.trim() || '';
                            const metaText = section.textContent || '';
                            const hotMatch = metaText.match(/(\\d+)\\s*万?\\s*热度/);

                            results.push({
                                question_id: match[1],
                                title: title.substring(0, 500),
                                detail: '',
                                follower_count: 0,
                                answer_count: 0,
                                view_count: hotMatch ? parseInt(hotMatch[1]) * (metaText.includes('万') ? 10000 : 1) : 0,
                                topics: [],
                            });
                        } catch(e) {}
                    });

                    return results;
                }
            """)

            questions = items[:max_count] if items else []
            logger.info(f"热榜: 找到 {len(questions)} 个问题")

        except Exception as e:
            logger.error(f"抓取热榜问题失败: {e}")

        return questions

    async def fetch_question_detail(self, page, question_id: str) -> dict:
        """
        获取单个问题的详细信息

        Args:
            page: Playwright Page
            question_id: 知乎问题ID

        Returns:
            dict with detail, follower_count, answer_count, view_count, topics
        """
        try:
            url = self.QUESTION_URL_TEMPLATE.format(question_id)
            await page.goto(url, wait_until="domcontentloaded")
            await HumanBehavior.random_delay(2000, 4000)

            detail = await page.evaluate("""
                () => {
                    const result = {
                        detail: '',
                        follower_count: 0,
                        answer_count: 0,
                        view_count: 0,
                        topics: [],
                    };

                    // Question detail/description
                    const detailEl = document.querySelector(
                        '.QuestionDetail-main .QuestionRichText, ' +
                        '[class*="QuestionDetail"] [class*="RichText"], ' +
                        '.QuestionDetail'
                    );
                    if (detailEl) {
                        result.detail = detailEl.textContent?.trim()?.substring(0, 2000) || '';
                    }

                    // Follower count
                    const sideInfo = document.querySelector('.QuestionFollowStatus, [class*="SideInfo"]');
                    if (sideInfo) {
                        const text = sideInfo.textContent || '';
                        const followerMatch = text.match(/(\\d[\\d,]*)\\s*(?:人关注|个关注)/);
                        if (followerMatch) {
                            result.follower_count = parseInt(followerMatch[1].replace(/,/g, ''));
                        }
                        const viewMatch = text.match(/(\\d[\\d,]*)\\s*(?:次浏览|被浏览)/);
                        if (viewMatch) {
                            result.view_count = parseInt(viewMatch[1].replace(/,/g, ''));
                        }
                    }

                    // Side column info
                    const pageText = document.body.textContent || '';
                    if (!result.follower_count) {
                        const fm = pageText.match(/(\\d[\\d,]*)\\s*(?:人关注)/);
                        if (fm) result.follower_count = parseInt(fm[1].replace(/,/g, ''));
                    }
                    if (!result.view_count) {
                        const vm = pageText.match(/(\\d[\\d,]*)\\s*(?:次浏览|被浏览)/);
                        if (vm) result.view_count = parseInt(vm[1].replace(/,/g, ''));
                    }

                    // Answer count
                    const answerHeader = document.querySelector('[class*="AnswerCount"], h4[class*="List-headerText"]');
                    if (answerHeader) {
                        const am = answerHeader.textContent?.match(/(\\d+)/);
                        if (am) result.answer_count = parseInt(am[1]);
                    }

                    // Topics
                    const topicEls = document.querySelectorAll('.QuestionTopic .Popover, .TopicLink, [class*="Tag"]');
                    result.topics = Array.from(topicEls)
                        .map(t => t.textContent?.trim())
                        .filter(t => t && t.length > 0 && t.length < 50);

                    return result;
                }
            """)

            return detail
        except Exception as e:
            logger.error(f"获取问题详情失败 (ID={question_id}): {e}")
            return {"detail": "", "follower_count": 0, "answer_count": 0, "view_count": 0, "topics": []}

    def _calculate_score(self, question_data: dict) -> float:
        """
        智能评分算法

        评分因素：
        1. 关注者多 = 流量大（权重最高）
        2. 回答数少 = 竞争小（回答越少越好）
        3. 浏览量高 = 曝光大
        4. 来源加权：invited > recommended > topic > hot

        Returns:
            float: 0-100 的综合评分
        """
        score = 0.0

        followers = question_data.get("follower_count", 0)
        answers = question_data.get("answer_count", 0)
        views = question_data.get("view_count", 0)
        source = question_data.get("source", "manual")

        # 关注者评分 (0-35分)
        if followers >= 10000:
            score += 35
        elif followers >= 5000:
            score += 30
        elif followers >= 1000:
            score += 25
        elif followers >= 500:
            score += 20
        elif followers >= 100:
            score += 15
        elif followers >= 10:
            score += 10
        else:
            score += 5

        # 回答数评分 (0-30分) — 回答越少越好
        if answers == 0:
            score += 30
        elif answers <= 3:
            score += 25
        elif answers <= 10:
            score += 20
        elif answers <= 30:
            score += 15
        elif answers <= 100:
            score += 10
        else:
            score += 5

        # 浏览量评分 (0-20分)
        if views >= 100000:
            score += 20
        elif views >= 50000:
            score += 17
        elif views >= 10000:
            score += 14
        elif views >= 5000:
            score += 11
        elif views >= 1000:
            score += 8
        else:
            score += 5

        # 来源加权 (0-15分)
        source_scores = {
            "invited": 15,
            "recommended": 12,
            "topic": 8,
            "hot": 6,
            "manual": 10,
        }
        score += source_scores.get(source, 5)

        return round(score, 1)

    async def add_manual_question(self, question_url: str, account_id: int = None) -> dict:
        """
        手动添加问题URL

        Args:
            question_url: 知乎问题URL，如 https://www.zhihu.com/question/12345
            account_id: 可选的账号ID

        Returns:
            dict with question data or error
        """
        # Extract question_id from URL
        match = re.search(r'/question/(\d+)', question_url)
        if not match:
            return {"error": "无效的问题URL，格式应为 https://www.zhihu.com/question/xxx"}

        question_id = match.group(1)

        # Check if already exists
        async with async_session_factory() as session:
            stmt = select(ZhihuQuestion).where(ZhihuQuestion.question_id == question_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return {"error": "该问题已存在", "question_id": existing.id}

        # Create with basic info, detail will be fetched later
        async with async_session_factory() as session:
            # Extract title from URL or set placeholder
            question = ZhihuQuestion(
                question_id=question_id,
                title=f"问题 #{question_id}（待获取详情）",
                source="manual",
                score=10.0,
                status="pending",
                account_id=account_id,
                fetched_at=_utcnow(),
            )
            session.add(question)
            await session.commit()
            await session.refresh(question)

            return {
                "id": question.id,
                "question_id": question_id,
                "message": "问题已添加",
            }


# 全局单例
zhihu_qa_fetcher = ZhihuQAFetcher()
