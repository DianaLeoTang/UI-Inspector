"""
Storybook 截图工具
支持 Storybook v7/v8，通过 iframe URL 直接渲染组件
"""

import asyncio
from pathlib import Path


class StorybookScreenshotter:
    """
    通过 Playwright 对 Storybook story 进行截图
    
    Storybook iframe URL 格式：
    http://localhost:6006/iframe.html?id=button--primary&viewMode=story
    """

    async def capture(
        self,
        story_id: str,
        storybook_url: str,
        output_path: str,
        viewport: dict = None,
        wait_selector: str = "#storybook-root",
        wait_timeout: int = 10000,
    ) -> str:
        """
        截图单个 Story
        
        Args:
            story_id:       Story ID，如 "button--primary"（Storybook URL 中的 id 参数）
            storybook_url:  Storybook 服务地址
            output_path:    截图保存路径
            viewport:       视口尺寸，默认 1440x900
            wait_selector:  等待元素出现后再截图
            wait_timeout:   最大等待时间（ms）
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "请先安装 Playwright：\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        viewport = viewport or {"width": 1440, "height": 900}
        iframe_url = (
            f"{storybook_url.rstrip('/')}/iframe.html"
            f"?id={story_id}&viewMode=story"
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport=viewport,
                device_scale_factor=2,   # Retina 清晰度
            )
            page = await context.new_page()

            await page.goto(iframe_url, wait_until="networkidle")

            # 等待 Storybook 渲染完成
            try:
                await page.wait_for_selector(wait_selector, timeout=wait_timeout)
                # 额外等待动画/字体加载
                await page.wait_for_timeout(500)
            except Exception:
                print(f"  ⚠️  等待 {wait_selector} 超时，直接截图")

            # 截取组件区域（裁剪掉 Storybook padding）
            root = await page.query_selector(wait_selector)
            if root:
                bounding_box = await root.bounding_box()
                if bounding_box and bounding_box["width"] > 0:
                    await page.screenshot(
                        path=output_path,
                        clip={
                            "x": max(0, bounding_box["x"] - 16),
                            "y": max(0, bounding_box["y"] - 16),
                            "width": bounding_box["width"] + 32,
                            "height": bounding_box["height"] + 32,
                        }
                    )
                    await browser.close()
                    return output_path

            # fallback: 全页截图
            await page.screenshot(path=output_path, full_page=False)
            await browser.close()
            return output_path


class MockScreenshotter:
    """
    Mock 截图工具（用于测试，不需要真实 Storybook）
    直接复制传入的图片作为截图
    """

    async def capture(
        self,
        story_id: str,
        storybook_url: str,
        output_path: str,
        viewport: dict = None,
        **kwargs
    ) -> str:
        """Mock 实现：复制设计图作为"截图"（仅用于测试）"""
        import shutil
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # 实际使用时替换为真实截图
        return output_path
