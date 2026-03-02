"""
Claude Vision 视觉对比工具
将设计稿和截图发送给 Claude，获取结构化差异分析
"""

import base64
import json
import re
from pathlib import Path


def _encode_image(image_path: str) -> tuple[str, str]:
    """将图片编码为 base64，返回 (base64_data, media_type)"""
    path = Path(image_path)
    suffix = path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_type_map.get(suffix, "image/png")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


class VisionComparator:
    """
    使用 Claude claude-opus-4-6 进行视觉对比
    """

    def __init__(self, client, system_prompt: str):
        self.client = client
        self.system_prompt = system_prompt

    async def compare(
        self,
        design_path: str,
        screenshot_path: str,
        component_name: str,
        extra_context: str = "",
    ) -> dict:
        """
        对比设计稿和截图，返回结构化差异报告
        
        Returns:
            {
                "overall_score": int,
                "summary": str,
                "issues": [...],
                "passed_checks": [...]
            }
        """
        design_b64, design_mime = _encode_image(design_path)
        screenshot_b64, screenshot_mime = _encode_image(screenshot_path)

        user_content = [
            {
                "type": "text",
                "text": f"## 走查任务：{component_name}\n"
                        + (f"额外说明：{extra_context}\n" if extra_context else "")
                        + "\n**图1（下方）为设计稿，图2（下方）为代码实现截图。**\n"
                          "请仔细对比两张图的样式差异，输出 JSON 报告。"
            },
            {
                "type": "text",
                "text": "### 图1：设计稿 ↓"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": design_mime,
                    "data": design_b64,
                }
            },
            {
                "type": "text",
                "text": "### 图2：代码实现截图 ↓"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": screenshot_mime,
                    "data": screenshot_b64,
                }
            },
        ]

        response = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text
        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: str) -> dict:
        """解析 Claude 返回的 JSON"""
        # 提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # fallback
        return {
            "overall_score": 0,
            "summary": "解析失败，原始输出：" + raw_text[:200],
            "issues": [],
            "passed_checks": []
        }
