"""
知乎盐选故事生成 Agent
基于参考素材生成知乎盐选风格故事文章

工作流程：
1. 素材提取 (extract_material) — 分析参考素材，提取人物、时代、设定、核心冲突
2. 故事规划 (plan_story) — 设计故事弧线、人物卡片、章节大纲、悬念分布
3. 分场景草稿 (draft_chapters) — 逐章生成，每章 2000-3000 字
4. 组装润色 (assemble_story) — 合并章节、添加过渡、伏笔回收
5. 去AI味 (polish_story) — 替换模板表达、添加口语化元素、调整节奏
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Optional

from app.core.ai_generator import ai_generator
from app.core.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

# 阶段级重试配置（在 provider 级重试之上再加一层保护）
_PHASE_MAX_RETRIES = 3
_PHASE_BASE_DELAY = 5  # 秒

# 故事类型对应的敏感题材处理规则
STORY_TYPE_RULES = {
    "corruption": """敏感题材处理原则（反腐类）：
- 聚焦个人道德堕落过程，不涉及体制性批评
- 用"某市""某县"代替真实地名，用虚构人名
- 确保正义最终胜利：贪官落网、制度完善
- 可以写纪检监察人员的正面形象
- 避免对在世官员有影射""",
    "historical": """敏感题材处理原则（历史类）：
- 用"某市""某县"代替真实地名
- 聚焦个体命运和人性光辉，不做宏观政治评判
- 历史事件作为背景，故事聚焦普通人的遭遇和选择
- 结尾传递希望和反思""",
    "suspense": """写作原则（悬疑类）：
- 注重逻辑推理和线索布置
- 适当使用红鲱鱼（误导性线索）
- 结局要合理，伏笔要有回收""",
    "romance": """写作原则（情感类）：
- 注重情感细腻度和人物内心描写
- 感情发展要有节奏，不能太突兀
- 结局可以不完美但要有意义""",
    "workplace": """写作原则（职场类）：
- 聚焦职场博弈和人际关系
- 展现真实的职场生态
- 正面展现努力和智慧的价值""",
}


class StoryAgent:
    """知乎盐选故事生成 Agent"""

    def __init__(self):
        self.ai_generator = ai_generator

    async def _call_chat(
        self, provider: BaseAIProvider, system_prompt: str, user_prompt: str
    ) -> str:
        """统一调用 AI Chat，带阶段级重试保护"""
        last_exc: Exception | None = None
        for attempt in range(1, _PHASE_MAX_RETRIES + 1):
            try:
                return await self.ai_generator._call_provider_chat(
                    provider, system_prompt, user_prompt
                )
            except Exception as e:
                last_exc = e
                if attempt < _PHASE_MAX_RETRIES:
                    delay = _PHASE_BASE_DELAY * attempt
                    logger.warning(
                        f"Story Agent 阶段调用第{attempt}次失败 "
                        f"({type(e).__name__}: {str(e)[:100]})，"
                        f"{delay}s 后重试..."
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
        raise last_exc  # type: ignore[misc]

    def _parse_json_response(self, text: str) -> dict:
        """解析 AI 返回的 JSON（strict=False 允许控制字符）"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end], strict=False)
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end], strict=False)
            raise ValueError(f"无法解析 AI 返回的 JSON: {text[:200]}...")

    # ==================== Phase 1: 素材提取 ====================

    async def extract_material(
        self,
        reference_text: str,
        reference_articles: list[dict],
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        阶段 1：分析参考素材，提取叙事核心元素

        Args:
            reference_text: 用户粘贴的原始参考素材
            reference_articles: 可选的已有文章列表
            ai_provider: AI 提供商

        Returns:
            素材分析结果 dict
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        # 构建素材文本
        material_text = reference_text[:8000]

        articles_text = ""
        if reference_articles:
            for i, article in enumerate(reference_articles, 1):
                preview = article["content"][:2000]
                articles_text += f"\n\n--- 参考文章 {i}: {article['title']} ---\n{preview}"

        system_prompt = """你是一位资深的故事素材分析师，擅长从原始素材中提取叙事核心元素。
请认真分析给出的参考素材，提取所有可用于构建故事的关键信息。
你必须严格按照指定的 JSON 格式返回，不要返回任何其他内容。"""

        user_prompt = f"""请分析以下参考素材，提取可用于构建知乎盐选故事的核心元素：

--- 参考素材 ---
{material_text}
{articles_text}

请严格按照以下 JSON 格式返回分析结果：
{{
    "era": "故事发生的时代背景（如：2003年某北方小城）",
    "setting": "故事发生的具体环境描写（50字以内）",
    "characters": [
        {{
            "name": "角色名（可虚构）",
            "role": "主角/配角/反派",
            "identity": "身份职业",
            "personality": "性格特点（30字以内）",
            "motivation": "核心动机",
            "arc": "人物变化弧线（一句话）"
        }}
    ],
    "core_conflict": "核心矛盾冲突（50字以内）",
    "key_events": ["关键事件1", "关键事件2", "关键事件3", "关键事件4", "关键事件5"],
    "emotional_tone": "情感基调（如：压抑中带希望）",
    "sensitivity_notes": "敏感点处理建议",
    "story_seeds": ["可发展的故事线索1", "线索2", "线索3"]
}}"""

        logger.info("Story Agent 阶段1：素材提取")
        text = await self._call_chat(provider, system_prompt, user_prompt)
        material = self._parse_json_response(text)
        logger.info(
            f"Story Agent 素材提取完成：时代={material.get('era', '未知')}, "
            f"角色数={len(material.get('characters', []))}"
        )
        return material

    # ==================== Phase 2: 故事规划 ====================

    async def plan_story(
        self,
        material: dict,
        chapter_count: int,
        total_word_count: int,
        story_type: str,
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        阶段 2：设计故事弧线、角色卡片、章节大纲

        Args:
            material: 阶段1的素材分析结果
            chapter_count: 章节数
            total_word_count: 总目标字数
            story_type: 故事类型
            ai_provider: AI 提供商

        Returns:
            故事规划 dict
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        sensitivity_rules = STORY_TYPE_RULES.get(story_type, STORY_TYPE_RULES["suspense"])
        words_per_chapter = total_word_count // chapter_count

        system_prompt = f"""你是一位知乎盐选专栏的金牌编辑，对爆款故事的节奏把控极为精准。
你深谙知乎故事的"黄金结构"：前三分之一免费区必须有强钩子，中段持续升级冲突，结尾必须有反转或情感释放。

{sensitivity_rules}

你必须严格按照指定的 JSON 格式返回，不要返回任何其他内容。"""

        characters_json = json.dumps(material.get("characters", []), ensure_ascii=False)
        key_events_json = json.dumps(material.get("key_events", []), ensure_ascii=False)
        story_seeds_json = json.dumps(material.get("story_seeds", []), ensure_ascii=False)

        user_prompt = f"""基于以下素材分析结果，请规划一个 {chapter_count} 章的知乎盐选故事：

素材分析：
- 时代背景：{material.get('era', '当代')}
- 场景设定：{material.get('setting', '')}
- 核心冲突：{material.get('core_conflict', '')}
- 关键人物：{characters_json}
- 关键事件：{key_events_json}
- 情感基调：{material.get('emotional_tone', '')}
- 可发展线索：{story_seeds_json}

总目标字数：约 {total_word_count} 字
每章约 {words_per_chapter} 字

规划要求：
1. 第一人称视角叙事
2. 采用"黄金三步开头"：悬念句 → 异常场景 → 核心冲突暗示
3. 前1/3（约前{chapter_count // 3 + 1}章，免费区）必须有足够强的钩子让读者付费
4. 每章结尾留悬念（章尾钩子）
5. 悬念分布：每2000字至少一个小悬念，每章至少一个大悬念
6. 结局要有力量感（正义得到伸张 / 命运得到回响）

请严格按照以下 JSON 格式返回：
{{
    "story_title": "故事标题（10-20字，有悬念感）",
    "story_summary": "故事梗概（100字以内）",
    "narrator": {{
        "name": "第一人称叙述者名字",
        "identity": "叙述者身份",
        "voice_style": "叙述语气特点（如：中年男人的回忆口吻、带点自嘲）"
    }},
    "character_cards": [
        {{
            "name": "角色名",
            "nickname": "外号/日常称呼",
            "appearance": "外貌特征（一句话）",
            "speech_pattern": "说话特点（如：爱说某句口头禅）",
            "key_detail": "标志性细节（如：总是穿黑色皮夹克）"
        }}
    ],
    "chapters": [
        {{
            "chapter_num": 1,
            "chapter_title": "章节标题",
            "target_words": {words_per_chapter},
            "time_span": "本章时间跨度",
            "pov_location": "叙事视角所在场景",
            "key_plot_points": ["情节点1", "情节点2", "情节点3"],
            "emotional_curve": "本章情感走向（如：平静→紧张→震惊）",
            "chapter_hook": "章尾悬念/钩子",
            "suspense_points": ["小悬念1", "小悬念2"]
        }}
    ],
    "foreshadowing": [
        {{
            "hint_chapter": 1,
            "reveal_chapter": 4,
            "description": "伏笔内容描述"
        }}
    ]
}}"""

        logger.info(f"Story Agent 阶段2：故事规划（{chapter_count}章，{total_word_count}字）")
        text = await self._call_chat(provider, system_prompt, user_prompt)
        plan = self._parse_json_response(text)
        logger.info(
            f"Story Agent 规划完成：标题={plan.get('story_title', '未知')}, "
            f"章节数={len(plan.get('chapters', []))}"
        )
        return plan

    # ==================== Phase 3: 分章草稿 ====================

    async def draft_chapters(
        self,
        plan: dict,
        material: dict,
        story_type: str,
        ai_provider: Optional[str] = None,
    ) -> list[dict]:
        """
        阶段 3：逐章生成故事内容

        每章单独一次 LLM 调用，输出纯文本（避免长文本 JSON 解析问题）。
        每章生成后提取摘要供后续章节参考。

        Args:
            plan: 阶段2的故事规划
            material: 阶段1的素材分析
            story_type: 故事类型
            ai_provider: AI 提供商

        Returns:
            章节列表 [{"chapter_num", "title", "content", "word_count", "summary"}, ...]
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        narrator = plan.get("narrator", {})
        character_cards = plan.get("character_cards", [])
        chapters_plan = plan.get("chapters", [])
        foreshadowing = plan.get("foreshadowing", [])
        sensitivity_rules = STORY_TYPE_RULES.get(story_type, "")

        # 构建角色卡片文本
        cards_text = ""
        for card in character_cards:
            cards_text += (
                f"- {card.get('name', '?')}（{card.get('nickname', '')}）：{card.get('appearance', '')}，"
                f"说话特点：{card.get('speech_pattern', '')}，"
                f"标志：{card.get('key_detail', '')}\n"
            )

        generated_chapters = []
        chapter_summaries = []  # 累积前情摘要

        for idx, ch_plan in enumerate(chapters_plan):
            ch_num = ch_plan.get("chapter_num", idx + 1)
            ch_title = ch_plan.get("chapter_title", f"第{ch_num}章")
            target_words = ch_plan.get("target_words", 3000)
            time_span = ch_plan.get("time_span", "")
            pov_location = ch_plan.get("pov_location", "")
            plot_points = ch_plan.get("key_plot_points", [])
            emotional_curve = ch_plan.get("emotional_curve", "")
            chapter_hook = ch_plan.get("chapter_hook", "")
            suspense_points = ch_plan.get("suspense_points", [])

            points_text = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(plot_points))
            suspense_text = "\n".join(f"  - {s}" for s in suspense_points)

            # 找出本章需要埋设的伏笔
            hints_for_chapter = [
                f for f in foreshadowing if f.get("hint_chapter") == ch_num
            ]
            hints_text = ""
            if hints_for_chapter:
                hints_text = "本章需要埋入的伏笔：\n" + "\n".join(
                    f"  - {h['description']}（将在第{h['reveal_chapter']}章揭示）"
                    for h in hints_for_chapter
                )

            # 找出本章需要回收的伏笔
            reveals_for_chapter = [
                f for f in foreshadowing if f.get("reveal_chapter") == ch_num
            ]
            reveals_text = ""
            if reveals_for_chapter:
                reveals_text = "本章需要回收的伏笔：\n" + "\n".join(
                    f"  - {r['description']}（第{r['hint_chapter']}章埋下的）"
                    for r in reveals_for_chapter
                )

            # 前情摘要
            summaries_text = "（故事开头，无前情）"
            if chapter_summaries:
                summaries_text = "\n".join(
                    f"第{i+1}章摘要：{s}" for i, s in enumerate(chapter_summaries)
                )

            # 特殊章节指令
            special_instructions = ""
            if ch_num == 1:
                special_instructions = """【第一章特殊要求】
这是故事的开头，决定读者是否继续阅读。你必须：
1. 第一句话就是悬念（如："我到现在都记得那天下午三点十七分，老李推开办公室门时脸上的表情。"）
2. 前200字内建立异常场景，让读者产生"发生了什么"的强烈好奇
3. 前500字内暗示核心冲突，但不要揭晓
4. 用具体的时间、地点、感官细节建立真实感"""
            elif ch_num == len(chapters_plan):
                special_instructions = """【最后一章特殊要求】
这是故事结尾，你必须：
1. 收束所有未解悬念和伏笔
2. 给出有力量感的结局（正义得到伸张 / 命运回响 / 深刻反思）
3. 最后一段要有余韵，给读者回味空间
4. 不要草草收尾"""

            narrator_name = narrator.get("name", "我")
            narrator_identity = narrator.get("identity", "")
            narrator_voice = narrator.get("voice_style", "平实叙述")

            system_prompt = f"""你是一位知乎盐选故事签约作者，擅长第一人称沉浸式叙事。

写作规则：
1. 严格第一人称视角，叙述者是{narrator_name}（{narrator_identity}），语气：{narrator_voice}
2. 对话要生动，每个角色有独特的说话方式
3. 场景描写用感官细节（视觉、听觉、嗅觉、触觉）
4. 不要用"我心想"，用行为和对话暗示心理
5. 禁止使用AI腔表达：禁止"然而""不禁""竟然""值得一提的是""毫无疑问""与此同时"
6. 多用短句，偶尔用长句制造节奏变化
7. 用具体时间地点代替模糊描述（"2003年腊月初八下午"而非"那年冬天"）
8. 适当加入不完美叙事：犹豫、自嘲、跑题后拉回
9. 对话中加入语气词和口语（"得了吧""你说呢""嘿"）

{sensitivity_rules}

直接输出故事正文，不要加任何标题、章节号、说明或JSON格式。纯文本输出，使用 Markdown 段落格式。"""

            user_prompt = f"""请写第 {ch_num}/{len(chapters_plan)} 章：{ch_title}

角色卡片：
{cards_text}

前情摘要：
{summaries_text}

本章要求：
- 目标字数：{target_words} 字
- 时间跨度：{time_span}
- 场景：{pov_location}
- 情感曲线：{emotional_curve}

情节要点（必须覆盖）：
{points_text}

悬念安排：
{suspense_text}

章尾钩子：{chapter_hook}

{hints_text}
{reveals_text}

{special_instructions}"""

            logger.info(
                f"Story Agent 阶段3：生成第 {ch_num}/{len(chapters_plan)} 章 - {ch_title}"
            )

            try:
                content = await self._call_chat(provider, system_prompt, user_prompt)

                # 清理可能的格式包裹
                content = content.strip()
                if content.startswith("```"):
                    first_newline = content.find("\n")
                    if first_newline != -1:
                        content = content[first_newline + 1:]
                if content.endswith("```"):
                    content = content[:-3].strip()

                word_count = len(content.replace(" ", "").replace("\n", ""))

                # 生成本章摘要（取前后各 150 字拼接）
                clean_content = content.replace("\n", " ").strip()
                if len(clean_content) > 300:
                    summary = clean_content[:150] + "…… " + clean_content[-150:]
                else:
                    summary = clean_content

                generated_chapters.append({
                    "chapter_num": ch_num,
                    "title": ch_title,
                    "content": content,
                    "word_count": word_count,
                    "summary": summary,
                })
                chapter_summaries.append(
                    f"{ch_title} — {summary[:100]}"
                )

                logger.info(
                    f"Story Agent 第{ch_num}章完成：{ch_title}（{word_count}字）"
                )

            except Exception as e:
                logger.error(f"Story Agent 第{ch_num}章生成失败：{e}")
                generated_chapters.append({
                    "chapter_num": ch_num,
                    "title": ch_title,
                    "content": f"【生成失败：{str(e)}】",
                    "word_count": 0,
                    "summary": "",
                    "error": str(e),
                })
                chapter_summaries.append(f"{ch_title} — （生成失败）")

        return generated_chapters

    # ==================== Phase 4: 组装 ====================

    async def assemble_story(
        self,
        chapters: list[dict],
        plan: dict,
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        阶段 4：组装章节，添加过渡，审查连贯性

        对于较短的故事（≤12K字），整体发给LLM审查。
        对于较长的故事（>12K字），逐对章节生成过渡句后直接拼接。

        Returns:
            {"full_story": str, "title": str, "summary": str, "tags": list}
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        story_title = plan.get("story_title", "未命名故事")

        # 过滤掉失败的章节
        valid_chapters = [ch for ch in chapters if "error" not in ch]
        if not valid_chapters:
            return {
                "full_story": "所有章节生成失败",
                "title": story_title,
                "summary": "",
                "tags": [],
            }

        # 计算总字数
        total_chars = sum(ch["word_count"] for ch in valid_chapters)

        if total_chars <= 12000:
            # 短故事：整体审查
            return await self._assemble_full(valid_chapters, plan, provider)
        else:
            # 长故事：轻量组装
            return await self._assemble_light(valid_chapters, plan, provider)

    async def _assemble_full(
        self,
        chapters: list[dict],
        plan: dict,
        provider: BaseAIProvider,
    ) -> dict:
        """短故事整体组装审查"""
        story_title = plan.get("story_title", "未命名故事")
        foreshadowing = plan.get("foreshadowing", [])
        foreshadowing_text = json.dumps(foreshadowing, ensure_ascii=False) if foreshadowing else "无"

        chapters_text = ""
        for ch in chapters:
            chapters_text += f"\n\n{'='*40}\n## 第{ch['chapter_num']}章：{ch['title']}\n{'='*40}\n\n{ch['content']}"

        system_prompt = """你是一位资深的故事编辑，负责将分章草稿组装为流畅的完整故事。

你的任务：
1. 检查章节之间的过渡是否自然，如不自然请添加1-2句过渡
2. 检查伏笔是否有回收，如有遗漏请在合适位置补充
3. 确保全文第一人称视角一致，人物称呼一致
4. 不要大幅修改原文，只做必要的过渡和修补
5. 用 --- 分隔章节，每章开头加 ## 标题

输出要求：
返回 JSON 格式：
{
    "full_story": "完整故事文本（Markdown格式，章节间用 --- 分隔）",
    "title": "最终故事标题",
    "summary": "200字以内的故事摘要（用于知乎描述）",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}"""

        user_prompt = f"""请组装以下分章草稿为完整故事。

故事标题：{story_title}
伏笔清单：{foreshadowing_text}

分章草稿：
{chapters_text}

请检查过渡、伏笔回收和一致性后，按 JSON 格式返回完整故事。"""

        logger.info("Story Agent 阶段4：整体组装审查")
        text = await self._call_chat(provider, system_prompt, user_prompt)
        result = self._parse_json_response(text)

        # 确保字段存在
        if "title" not in result:
            result["title"] = story_title
        if "summary" not in result:
            result["summary"] = ""
        if "tags" not in result:
            result["tags"] = []
        if "full_story" not in result:
            # 回退：直接拼接
            result["full_story"] = self._simple_concat(chapters)

        return result

    async def _assemble_light(
        self,
        chapters: list[dict],
        plan: dict,
        provider: BaseAIProvider,
    ) -> dict:
        """长故事轻量组装：逐对生成过渡句"""
        story_title = plan.get("story_title", "未命名故事")

        # 直接拼接章节，在每对之间请求一个简短过渡
        parts = []
        for i, ch in enumerate(chapters):
            if i > 0:
                # 生成过渡句
                prev_ending = chapters[i - 1]["content"][-300:]
                curr_opening = ch["content"][:300]

                transition_prompt = f"""上一章结尾：
{prev_ending}

下一章开头：
{curr_opening}

请写一句简短的过渡句（1-2句，30字以内），自然连接上下章节。
只输出过渡句本身，不要任何解释。"""

                try:
                    transition = await self._call_chat(
                        provider,
                        "你是一位故事编辑，专门写章节间的过渡句。只输出过渡句，不要任何格式或解释。",
                        transition_prompt,
                    )
                    transition = transition.strip().strip('"').strip("'")
                    parts.append(f"\n\n{transition}\n")
                except Exception:
                    parts.append("\n")

            parts.append(f"\n---\n\n## 第{ch['chapter_num']}章：{ch['title']}\n\n{ch['content']}")

        full_story = "".join(parts).strip()

        # 生成摘要和标签
        summary_prompt = f"""请为以下故事写一个200字以内的摘要和5个知乎话题标签。

故事标题：{story_title}
故事开头500字：{full_story[:500]}

返回 JSON：
{{
    "summary": "故事摘要",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}"""

        try:
            text = await self._call_chat(
                provider,
                "你是一位故事编辑，擅长写引人入胜的故事摘要。返回 JSON 格式。",
                summary_prompt,
            )
            meta = self._parse_json_response(text)
        except Exception:
            meta = {"summary": "", "tags": []}

        return {
            "full_story": full_story,
            "title": story_title,
            "summary": meta.get("summary", ""),
            "tags": meta.get("tags", []),
        }

    def _simple_concat(self, chapters: list[dict]) -> str:
        """简单拼接章节"""
        parts = []
        for ch in chapters:
            parts.append(f"## 第{ch['chapter_num']}章：{ch['title']}\n\n{ch['content']}")
        return "\n\n---\n\n".join(parts)

    # ==================== Phase 5: 去AI味润色 ====================

    async def polish_story(
        self,
        assembled: dict,
        story_type: str,
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        阶段 5：去 AI 味润色

        逐章处理，替换模板化表达，添加自然语感。

        Returns:
            润色后的 {"full_story", "title", "summary", "tags"}
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        full_story = assembled.get("full_story", "")
        if not full_story or len(full_story) < 100:
            return assembled

        # 按章节分割
        chapter_parts = re.split(r'\n---\n', full_story)
        if len(chapter_parts) <= 1:
            # 没有分隔符，尝试按 ## 分割
            chapter_parts = re.split(r'\n(?=## )', full_story)

        polished_parts = []

        system_prompt = """你是一位文字打磨师，专门让AI生成的文字变得更像真人写的。

去AI味清单：
1. 替换模板表达：
   - "然而" → 删除或改用具体转折
   - "不禁" → 删除
   - "竟然" → 控制频率（全文最多出现1次）
   - "值得一提的是" → 删除
   - "毫无疑问" → 删除
   - "与此同时" → 改用具体时间连接
   - "如同……一般" → 改用更具体的比喻

2. 添加自然元素：
   - 叙述者的犹豫和插嘴（"说到这儿我得先交代一下……"）
   - 口语化表达（"说白了""得了吧""谁知道呢""可不是嘛"）
   - 不完美的回忆口吻（"具体是哪天我记不清了，大概是……"）

3. 节奏调整：
   - 紧张处用短句连续推进
   - 平静处允许长句
   - 对话后加入动作或环境描写

4. 细节强化：
   - 模糊时间 → 具体时间（"那天下午三点多"）
   - 模糊感受 → 身体反应（"心里不舒服" → "胃里翻江倒海"）

保留原文的情节和结构，只做文字层面的润色。
直接输出润色后的文本，不要加任何说明或JSON格式。"""

        for i, part in enumerate(chapter_parts):
            part = part.strip()
            if not part or len(part) < 50:
                polished_parts.append(part)
                continue

            user_prompt = f"""请润色以下故事章节（第{i+1}/{len(chapter_parts)}段），去除AI痕迹：

{part}

直接输出润色后的文本。"""

            try:
                polished = await self._call_chat(provider, system_prompt, user_prompt)
                polished = polished.strip()
                # 清理可能的格式包裹
                if polished.startswith("```"):
                    first_nl = polished.find("\n")
                    if first_nl != -1:
                        polished = polished[first_nl + 1:]
                if polished.endswith("```"):
                    polished = polished[:-3].strip()

                polished_parts.append(polished)
                logger.info(f"Story Agent 润色完成：第{i+1}/{len(chapter_parts)}段")
            except Exception as e:
                logger.warning(f"Story Agent 润色第{i+1}段失败，保留原文：{e}")
                polished_parts.append(part)

        polished_story = "\n\n---\n\n".join(polished_parts)

        return {
            "full_story": polished_story,
            "title": assembled.get("title", ""),
            "summary": assembled.get("summary", ""),
            "tags": assembled.get("tags", []),
        }

    # ==================== run() 完整流程 ====================

    async def run(
        self,
        reference_text: str,
        reference_articles: list[dict],
        chapter_count: int = 5,
        total_word_count: int = 15000,
        story_type: str = "corruption",
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        运行完整的 5 阶段故事生成流水线

        Args:
            reference_text: 参考素材原文
            reference_articles: 可选的已有文章
            chapter_count: 章节数
            total_word_count: 总目标字数
            story_type: 故事类型
            ai_provider: AI 提供商

        Returns:
            完整结果 dict
        """
        logger.info(
            f"Story Agent 启动：章节数={chapter_count}, "
            f"目标字数={total_word_count}, 类型={story_type}, provider={ai_provider}"
        )

        # Phase 1: 素材提取
        material = await self.extract_material(
            reference_text, reference_articles, ai_provider
        )

        # Phase 2: 故事规划
        plan = await self.plan_story(
            material, chapter_count, total_word_count, story_type, ai_provider
        )

        # Phase 3: 分章草稿
        chapters = await self.draft_chapters(
            plan, material, story_type, ai_provider
        )

        # Phase 4: 组装
        assembled = await self.assemble_story(chapters, plan, ai_provider)

        # Phase 5: 去AI味润色
        final_story = await self.polish_story(assembled, story_type, ai_provider)

        # 统计
        valid_chapters = [ch for ch in chapters if "error" not in ch]
        total_wc = len(
            final_story.get("full_story", "").replace(" ", "").replace("\n", "")
        )

        result = {
            "material": material,
            "plan": plan,
            "chapters": chapters,
            "final_story": final_story,
            "stats": {
                "chapter_count": len(chapters),
                "success_count": len(valid_chapters),
                "failed_count": len(chapters) - len(valid_chapters),
                "total_word_count": total_wc,
                "phases_completed": 5,
            },
        }

        logger.info(
            f"Story Agent 完成：{len(valid_chapters)}/{len(chapters)}章成功, "
            f"总字数={total_wc}"
        )
        return result


# 全局单例
story_agent = StoryAgent()
