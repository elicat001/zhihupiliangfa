"""
AI 提供商基类
所有 AI 提供商适配器都继承此抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class GeneratedArticle:
    """AI 生成的文章结构"""
    title: str
    content: str
    summary: str
    tags: list[str]
    word_count: int


class BaseAIProvider(ABC):
    """AI 提供商抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        ...

    @abstractmethod
    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> GeneratedArticle:
        """生成文章"""
        ...

    @abstractmethod
    async def generate_article_stream(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> AsyncIterator[str]:
        """流式生成文章，逐 token 返回"""
        ...
        yield ""  # type: ignore

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词（升级版）
        融合知乎排版规范、SEO 优化、互动引导
        """
        return """你是一位拥有10万+粉丝的知乎头部创作者，文章多次登上知乎热榜。你的写作遵循以下原则：

## 思维方式
- 写作前先在心里构建文章骨架：核心论点 → 3-5个分论点 → 每个分论点的论据
- 确保每个观点都有数据、案例或逻辑推理作为支撑
- 在关键位置提出反直觉的观点或洞察，引发读者思考

## 知乎排版规范
- 使用 ## 二级标题分段，每段控制在 300-500 字
- 重要观点用 **加粗** 标注
- 适当使用 > 引用块来突出金句或数据
- 使用有序/无序列表来归纳要点
- 段与段之间用 --- 分割线过渡
- 偶尔使用「」而非""来增加知乎平台感

## SEO 与流量优化
- 标题包含核心关键词，长度控制在 15-25 字
- 标题格式优先：疑问式、数字式、颠覆认知式
- 文章开头 100 字内出现核心关键词 2-3 次
- 每个小标题自然嵌入长尾关键词

## 互动引导
- 文末用一个开放性问题引导读者在评论区讨论
- 适当使用"你觉得呢？"、"欢迎在评论区聊聊"等互动语句

## 输出格式要求
你必须严格按照以下 JSON 格式返回，不要返回任何其他内容：
{
    "title": "文章标题（15-25字，含核心关键词）",
    "content": "文章正文内容（Markdown 格式）",
    "summary": "100字以内的文章摘要，用于知乎文章描述",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}"""

    def _build_user_prompt(
        self, topic: str, style: str, word_count: int
    ) -> str:
        """构建用户提示词"""
        style_map = {
            "professional": "专业严谨，数据驱动，引用行业报告和研究，适合从业者深度阅读",
            "casual": "轻松活泼，通俗易懂，用生活化的比喻和例子，适合大众读者",
            "humorous": "幽默风趣，善用段子和反转，在笑点中传递知识，像脱口秀般吸引人",
            "academic": "学术严谨，逻辑缜密，引经据典，论证充分，适合学术讨论",
            "analytical": "数据分析型，大量使用图表描述、对比数据和趋势分析，用数字说话",
            "controversial": "观点碰撞型，提出大胆的反主流观点，正反论证，引发激烈讨论",
            "comparison": "对比评测型，多维度横向对比，列出优缺点，帮助读者做决策",
            "storytelling": "叙事型，通过真实故事和案例展开，情感共鸣，引人入胜",
            "tutorial": "教程型，步骤清晰，有代码示例或操作指南，手把手教学",
        }
        style_desc = style_map.get(style, style_map["professional"])

        return f"""请以「{topic}」为主题，写一篇知乎专栏文章。

要求：
- 写作风格：{style_desc}
- 目标字数：约 {word_count} 字
- 标题要吸引眼球，含核心关键词
- 内容要有深度、有独到见解，避免泛泛而谈
- 使用 Markdown 格式排版
- 选择 5 个知乎上热度高的相关话题标签
- 文末加一个引导评论的互动问题

请严格按照指定的 JSON 格式返回。"""

    def _build_rewrite_prompt(
        self, content: str, style: str, instruction: str = ""
    ) -> str:
        """构建改写提示词"""
        style_map = {
            "professional": "专业严谨",
            "casual": "轻松活泼",
            "humorous": "幽默风趣",
            "academic": "学术严谨",
            "simplified": "精简浓缩，只保留核心要点",
            "expanded": "扩展丰富，增加更多案例和细节",
        }
        style_desc = style_map.get(style, style)
        extra = f"\n额外要求：{instruction}" if instruction else ""

        return f"""请改写以下文章，保留核心观点但用全新的表达方式重写。

改写风格：{style_desc}{extra}

原文：
{content}

请严格按照以下 JSON 格式返回：
{{
    "title": "改写后的标题",
    "content": "改写后的正文（Markdown 格式）",
    "summary": "100字以内的摘要",
    "tags": ["标签1", "标签2", "标签3"]
}}"""

    def _build_series_outline_prompt(self, topic: str, count: int = 5) -> str:
        """构建系列文章大纲生成提示词"""
        return f"""请为「{topic}」这个主题设计一个 {count} 篇文章的系列专栏计划。

要求：
- 每篇文章有明确的子主题和角度，互相关联但不重复
- 整体有递进或并列的逻辑关系
- 每篇文章附带简要描述（50字以内）

请严格按照以下 JSON 格式返回：
{{
    "series_title": "系列总标题",
    "description": "系列整体介绍（100字以内）",
    "articles": [
        {{
            "order": 1,
            "title": "第一篇标题",
            "description": "简要描述",
            "key_points": ["要点1", "要点2", "要点3"]
        }}
    ]
}}"""

    def _parse_response(self, text: str) -> GeneratedArticle:
        """
        解析 AI 返回的 JSON 文本

        Args:
            text: AI 返回的原始文本

        Returns:
            GeneratedArticle: 解析后的文章对象
        """
        import json

        # 尝试从文本中提取 JSON
        text = text.strip()

        # 如果被 markdown 代码块包裹，去除
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到 JSON 对象
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(text[start:end])
            else:
                raise ValueError(f"无法从 AI 返回内容中解析 JSON: {text[:200]}...")

        title = data.get("title", "无标题")
        content = data.get("content", "")
        summary = data.get("summary", "")
        tags = data.get("tags", [])

        # 计算字数（中文按字计算）
        actual_word_count = len(content.replace(" ", "").replace("\n", ""))

        return GeneratedArticle(
            title=title,
            content=content,
            summary=summary,
            tags=tags if isinstance(tags, list) else [],
            word_count=actual_word_count,
        )
