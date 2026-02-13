"""
反检测策略
包含浏览器指纹伪装、人类行为模拟、UA 轮换、
发布时间抖动等反自动化检测措施
"""

import asyncio
import random
import logging

logger = logging.getLogger(__name__)


# ==================== UA 轮换池 ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ==================== 视窗尺寸池 ====================
VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 720},
    {"width": 2560, "height": 1440},
]

# ==================== 打字速度档位 (ms per character) ====================
TYPING_SPEEDS = {
    "slow": (150, 300),
    "normal": (80, 150),
    "fast": (40, 80),
}


def get_random_user_agent() -> str:
    """从 UA 池中随机选取一个 User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_viewport() -> dict:
    """从视窗池中随机选取一个分辨率"""
    return random.choice(VIEWPORT_SIZES)


def get_typing_delay(speed: str = "normal") -> float:
    """
    返回随机打字延迟（秒）

    Args:
        speed: 速度档位 slow / normal / fast
    """
    min_ms, max_ms = TYPING_SPEEDS.get(speed, TYPING_SPEEDS["normal"])
    return random.randint(min_ms, max_ms) / 1000.0


def get_random_jitter_minutes(max_minutes: int = 5) -> float:
    """
    返回 ±max_minutes 范围内的随机偏移（分钟）
    用于给定时发布添加时间抖动，防止行为模式被检测

    Args:
        max_minutes: 最大偏移分钟数（默认 5）

    Returns:
        float: 偏移分钟数，范围 [-max_minutes, +max_minutes]
    """
    return random.uniform(-max_minutes, max_minutes)


def get_human_like_pause() -> float:
    """
    模拟人类阅读/思考停顿（秒）

    Returns:
        float: 0.5 ~ 3.0 秒之间的随机停顿
    """
    return random.uniform(0.5, 3.0)


# ==================== Stealth JS 脚本 ====================
# 注入到浏览器页面中，覆盖自动化检测特征

STEALTH_JS = """
() => {
    // 1. 覆盖 navigator.webdriver 属性
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // 2. 覆盖 chrome runtime
    window.chrome = {
        runtime: {
            onConnect: undefined,
            onMessage: undefined,
            connect: function() {},
            sendMessage: function() {},
        },
        loadTimes: function() {
            return {};
        },
        csi: function() {
            return {};
        },
    };

    // 3. 覆盖 permissions query
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // 4. 覆盖 plugins 长度（正常浏览器有插件）
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // 5. 覆盖 languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
    });

    // 6. 覆盖 platform
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
    });

    // 7. 防止通过 iframe contentWindow 检测
    const originalAttachShadow = Element.prototype.attachShadow;
    Element.prototype.attachShadow = function() {
        return originalAttachShadow.apply(this, arguments);
    };

    // 8. 覆盖 WebGL 渲染器信息
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.apply(this, arguments);
    };

    // 9. 覆盖 canvas 指纹
    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png') {
            const context = this.getContext('2d');
            if (context) {
                // 添加微小的不可见噪声
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = imageData.data[i] + (Math.random() * 0.5 - 0.25);
                }
                context.putImageData(imageData, 0, 0);
            }
        }
        return toDataURL.apply(this, arguments);
    };

    console.log('[Stealth] 反检测脚本已注入');
}
"""


class HumanBehavior:
    """
    人类行为模拟器
    模拟真实用户的鼠标移动、打字速度、滚动行为等
    """

    @staticmethod
    async def random_delay(min_ms: int = 100, max_ms: int = 500):
        """
        随机延迟，模拟人类反应时间

        Args:
            min_ms: 最小延迟（毫秒）
            max_ms: 最大延迟（毫秒）
        """
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    @staticmethod
    async def human_type(page, selector: str, text: str, min_delay: int = 30, max_delay: int = 150):
        """
        模拟人类打字速度输入文字
        每个字符之间有随机间隔

        Args:
            page: Playwright Page 对象
            selector: 输入框选择器
            text: 要输入的文字
            min_delay: 每个字符之间的最小延迟（毫秒）
            max_delay: 每个字符之间的最大延迟（毫秒）
        """
        element = page.locator(selector)
        await element.click()
        await HumanBehavior.random_delay(200, 500)

        for char in text:
            delay = random.randint(min_delay, max_delay)
            await page.keyboard.type(char, delay=delay)
            # 偶尔暂停一下，模拟思考
            if random.random() < 0.05:
                await HumanBehavior.random_delay(500, 1500)

    @staticmethod
    async def human_click(page, selector: str):
        """
        模拟人类点击行为
        先移动鼠标到目标位置，再点击

        Args:
            page: Playwright Page 对象
            selector: 要点击的元素选择器
        """
        element = page.locator(selector)
        # 获取元素的边界框
        bounding_box = await element.bounding_box()
        if bounding_box:
            # 在元素区域内随机选一个点击位置
            x = bounding_box["x"] + random.uniform(
                bounding_box["width"] * 0.2,
                bounding_box["width"] * 0.8,
            )
            y = bounding_box["y"] + random.uniform(
                bounding_box["height"] * 0.2,
                bounding_box["height"] * 0.8,
            )
            # 先移动鼠标
            await page.mouse.move(x, y)
            await HumanBehavior.random_delay(50, 200)
            # 再点击
            await page.mouse.click(x, y)
        else:
            # 后备方案：直接点击
            await element.click()

        await HumanBehavior.random_delay(200, 500)

    @staticmethod
    async def random_scroll(page, times: int = 3):
        """
        随机滚动页面，模拟浏览行为

        Args:
            page: Playwright Page 对象
            times: 滚动次数
        """
        for _ in range(times):
            scroll_y = random.randint(100, 400)
            direction = random.choice([1, -1])
            await page.mouse.wheel(0, scroll_y * direction)
            await HumanBehavior.random_delay(300, 1000)

    @staticmethod
    async def random_mouse_move(page, count: int = 5):
        """
        随机移动鼠标，模拟真实用户行为

        Args:
            page: Playwright Page 对象
            count: 移动次数
        """
        viewport = page.viewport_size
        if not viewport:
            viewport = {"width": 1280, "height": 720}

        for _ in range(count):
            x = random.randint(0, viewport["width"])
            y = random.randint(0, viewport["height"])
            # 分步骤移动，模拟自然鼠标轨迹
            steps = random.randint(3, 8)
            await page.mouse.move(x, y, steps=steps)
            await HumanBehavior.random_delay(100, 400)

    @staticmethod
    async def simulate_reading(page, duration_seconds: int = 5):
        """
        模拟用户阅读页面的行为
        包含随机滚动和鼠标移动

        Args:
            page: Playwright Page 对象
            duration_seconds: 模拟阅读的时长（秒）
        """
        logger.info(f"模拟阅读行为 {duration_seconds} 秒...")
        loop = asyncio.get_running_loop()
        end_time = loop.time() + duration_seconds

        while loop.time() < end_time:
            action = random.choice(["scroll", "mouse_move", "wait"])
            if action == "scroll":
                await HumanBehavior.random_scroll(page, times=1)
            elif action == "mouse_move":
                await HumanBehavior.random_mouse_move(page, count=2)
            else:
                await HumanBehavior.random_delay(500, 2000)


def get_stealth_script() -> str:
    """获取反检测注入脚本"""
    return STEALTH_JS
