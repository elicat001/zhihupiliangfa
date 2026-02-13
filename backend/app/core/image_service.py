"""
图片服务
支持 CogView-3-Flash (AI 生成) 和 Unsplash (图库搜索) 两种图片源
"""

import os
import uuid
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import httpx
from PIL import Image as PILImage

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ImageResult:
    """图片获取结果"""
    id: str                     # e.g., "IMG1", "cover"
    local_path: str             # relative path: "images/20260212/xxxx.jpg"
    source: str                 # "cogview" | "unsplash"
    alt_text: str               # alt text for <img>
    width: Optional[int] = None
    height: Optional[int] = None
    original_url: Optional[str] = None


@dataclass
class ImageRequest:
    """图片请求描述（来自 LLM 输出）"""
    id: str                     # "IMG1", "IMG2", "cover"
    ai_prompt: str              # prompt for CogView
    search_query: str           # English search query for Unsplash
    alt_text: str               # Chinese alt text
    position: Optional[str] = None
    is_cover: bool = False


class ImageService:
    """图片服务：CogView AI 生图 + Unsplash 图库搜索"""

    # ---- Gemini Image Generation ----

    async def generate_image_gemini(
        self, prompt: str
    ) -> Optional[str]:
        """
        调用 Gemini-3-Pro-Image 通过 Chat API 生成图片

        返回本地文件相对路径（而非 URL），因为 Gemini 直接返回 base64 数据。
        Returns:
            本地文件相对路径 或 None（失败时）
        """
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY 未配置，跳过 AI 生图")
            return None

        url = f"{settings.GEMINI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gemini-3-pro-image-preview",
            "messages": [
                {
                    "role": "user",
                    "content": f"Generate an image: {prompt}. Only return the image, no text.",
                }
            ],
            "max_tokens": 4096,
        }

        try:
            async with httpx.AsyncClient(
                timeout=180.0, trust_env=False
            ) as client:
                response = await client.post(
                    url, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]

            # 提取 base64 图片数据: ![image](data:image/jpeg;base64,...)
            import re, base64
            match = re.search(
                r'data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=]+)',
                content,
            )
            if not match:
                logger.warning("Gemini 响应中未找到 base64 图片数据")
                return None

            image_bytes = base64.b64decode(match.group(1))

            # 保存到本地
            date_dir = datetime.now().strftime("%Y%m%d")
            save_dir = os.path.join(settings.IMAGES_DIR, date_dir)
            os.makedirs(save_dir, exist_ok=True)
            filename = f"{uuid.uuid4().hex[:12]}.jpg"
            filepath = os.path.join(save_dir, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            relative_path = f"{date_dir}/{filename}"
            logger.info(f"Gemini 生成图片成功: {relative_path}")
            return relative_path
        except Exception as e:
            logger.error(f"Gemini 生图失败: {e}")
            return None

    # ---- Unsplash ----

    async def search_image_unsplash(
        self, query: str, per_page: int = 1
    ) -> Optional[str]:
        """
        在 Unsplash 搜索图片

        Returns:
            图片 URL 或 None（失败时）
        """
        if not settings.UNSPLASH_ACCESS_KEY:
            logger.warning("UNSPLASH_ACCESS_KEY 未配置，跳过 Unsplash")
            return None

        url = "https://api.unsplash.com/search/photos"
        headers = {
            "Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}",
        }
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape",
        }

        try:
            async with httpx.AsyncClient(
                timeout=30.0, trust_env=False
            ) as client:
                response = await client.get(
                    url, headers=headers, params=params
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            if not results:
                logger.warning(f"Unsplash 未找到: '{query}'")
                return None

            # 使用 regular 尺寸（约 1080px 宽）
            image_url = results[0]["urls"]["regular"]
            logger.info(f"Unsplash 找到图片: {image_url[:80]}...")
            return image_url
        except Exception as e:
            logger.error(f"Unsplash 搜索失败: {e}")
            return None

    # ---- 下载与保存 ----

    async def download_image(
        self, image_url: str, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        下载图片到本地存储

        Returns:
            相对路径（如 "20260212/abc123.jpg"）或 None
        """
        date_dir = datetime.now().strftime("%Y%m%d")
        save_dir = os.path.join(settings.IMAGES_DIR, date_dir)
        os.makedirs(save_dir, exist_ok=True)

        if not filename:
            filename = f"{uuid.uuid4().hex[:12]}.jpg"

        filepath = os.path.join(save_dir, filename)
        relative_path = f"{date_dir}/{filename}"

        try:
            async with httpx.AsyncClient(
                timeout=60.0, trust_env=False
            ) as client:
                response = await client.get(image_url)
                response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            # Pillow 验证和优化
            try:
                img = PILImage.open(filepath)
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                    img.save(filepath, "JPEG", quality=85)
                logger.info(
                    f"图片已保存: {relative_path} ({img.width}x{img.height})"
                )
            except Exception as e:
                logger.warning(f"Pillow 验证失败: {e}")

            return relative_path
        except Exception as e:
            logger.error(f"图片下载失败: {e}")
            return None

    # ---- 编排 ----

    async def fetch_image(self, request: ImageRequest) -> Optional[ImageResult]:
        """
        获取单张图片（混合策略）:
        - 封面图: 优先 Gemini AI 生图，失败回退 Unsplash
        - 正文图: 优先 Unsplash，失败回退 Gemini
        """
        local_path: Optional[str] = None
        image_url: Optional[str] = None
        source: str = "unsplash"

        if request.is_cover:
            # 封面图：优先 AI 生成
            local_path = await self.generate_image_gemini(request.ai_prompt)
            if local_path:
                source = "gemini"

        if not local_path:
            # 回退到 Unsplash
            image_url = await self.search_image_unsplash(request.search_query)
            if image_url:
                source = "unsplash"
                local_path = await self.download_image(image_url)

        if not local_path and not request.is_cover:
            # 正文图 Unsplash 失败时，回退到 Gemini AI
            local_path = await self.generate_image_gemini(request.ai_prompt)
            if local_path:
                source = "gemini"

        if not local_path:
            logger.warning(f"图片获取失败: {request.id}")
            return None

        return ImageResult(
            id=request.id,
            local_path=local_path,
            source=source,
            alt_text=request.alt_text,
            original_url=image_url,
        )

    async def fetch_all_images(
        self, requests: list[ImageRequest]
    ) -> list[ImageResult]:
        """
        批量获取文章所有图片（顺序执行以遵守速率限制）
        """
        results: list[ImageResult] = []
        for req in requests:
            result = await self.fetch_image(req)
            if result:
                results.append(result)
        return results


# 全局单例
image_service = ImageService()
