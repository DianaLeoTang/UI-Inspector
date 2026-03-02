"""
UI Inspector Agent - 主调度器
协调截图、视觉对比、报告生成全流程
"""

import asyncio
import json
import base64
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from tools.screenshot import StorybookScreenshotter
from tools.compare import VisionComparator
from tools.report import ReportGenerator


@dataclass
class InspectionTask:
    """单个组件走查任务"""
    component_name: str
    design_image_path: str              # 设计稿路径（PNG/JPG/Figma导出）
    storybook_story_id: str             # e.g. "Button--primary"
    storybook_url: str = "http://localhost:6006"
    viewport: dict = field(default_factory=lambda: {"width": 1440, "height": 900})
    extra_context: str = ""             # 额外说明，如"暗色主题"


@dataclass
class InspectionResult:
    """走查结果"""
    task: InspectionTask
    screenshot_path: str
    issues: list[dict]
    severity_summary: dict
    overall_score: int                  # 0-100
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class UIInspectorAgent:
    """
    UI走查 Agent
    
    职责：
    1. 接收走查任务列表
    2. 调用 Storybook 截图工具
    3. 调用 Claude Vision 进行对比分析
    4. 汇总生成 Markdown + HTML 报告
    """

    SYSTEM_PROMPT = """你是一名专业的 UI 走查专家，精通前端开发和设计规范。
你的任务是对比设计稿和代码实现截图，找出所有样式和功能差异。

## 检查维度（按优先级）

### 🔴 Critical（阻断级）
- 布局结构完全不同（如横排变竖排）
- 核心交互组件缺失（按钮、输入框等）
- 颜色系统性偏差（品牌色、状态色错误）

### 🟠 Major（重要级）
- 间距/尺寸偏差超过 4px
- 字体大小偏差超过 2px
- 字重、行高不一致
- 圆角、阴影明显差异
- 边框样式/颜色不一致

### 🟡 Minor（轻微级）
- 间距偏差 1-4px
- 细微颜色差异（不影响品牌识别）
- 字母间距、段落间距轻微偏差

## 忽略项
- 具体文字内容差异
- 图片/图标的实际内容（只检查尺寸和位置）
- 动态数据填充内容

## 输出格式
必须严格返回 JSON，不要包含任何其他文字：

{
  "overall_score": 85,
  "summary": "整体实现较好，存在X处需修改的问题",
  "issues": [
    {
      "id": 1,
      "severity": "critical|major|minor",
      "category": "layout|spacing|color|typography|border|shadow|missing",
      "location": "组件区域描述，如：右上角操作按钮",
      "design_spec": "设计稿中的样式描述",
      "actual_impl": "代码实现中的实际样式",
      "suggestion": "具体修改建议，最好包含CSS属性和值",
      "coordinates": {"x": 100, "y": 200, "w": 150, "h": 40}
    }
  ],
  "passed_checks": ["布局结构一致", "主色调一致"]
}"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.screenshotter = StorybookScreenshotter()
        self.comparator = VisionComparator(self.client, self.SYSTEM_PROMPT)
        self.reporter = ReportGenerator()

    async def inspect(
        self,
        tasks: list[InspectionTask],
        output_dir: str = "./reports"
    ) -> str:
        """
        执行走查并生成报告
        Returns: 报告目录路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"🔍 开始 UI 走查，共 {len(tasks)} 个组件...\n")
        results = []

        for i, task in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] 正在检查：{task.component_name}")
            result = await self._inspect_single(task, output_path)
            results.append(result)
            self._print_summary(result)

        # 生成报告
        print("\n📝 生成报告中...")
        report_dir = self.reporter.generate(results, output_path)
        print(f"✅ 走查完成！报告已保存至：{report_dir}")
        return report_dir

    async def _inspect_single(
        self, task: InspectionTask, output_path: Path
    ) -> InspectionResult:
        """单个组件走查"""
        # Step 1: 截图
        screenshot_path = output_path / "screenshots" / f"{task.component_name}.png"
        screenshot_path.parent.mkdir(exist_ok=True)

        await self.screenshotter.capture(
            story_id=task.storybook_story_id,
            storybook_url=task.storybook_url,
            output_path=str(screenshot_path),
            viewport=task.viewport
        )

        # Step 2: 视觉对比
        raw_result = await self.comparator.compare(
            design_path=task.design_image_path,
            screenshot_path=str(screenshot_path),
            component_name=task.component_name,
            extra_context=task.extra_context
        )

        # Step 3: 汇总
        severity_summary = {
            "critical": sum(1 for i in raw_result["issues"] if i["severity"] == "critical"),
            "major": sum(1 for i in raw_result["issues"] if i["severity"] == "major"),
            "minor": sum(1 for i in raw_result["issues"] if i["severity"] == "minor"),
        }

        return InspectionResult(
            task=task,
            screenshot_path=str(screenshot_path),
            issues=raw_result["issues"],
            severity_summary=severity_summary,
            overall_score=raw_result["overall_score"],
        )

    def _print_summary(self, result: InspectionResult):
        s = result.severity_summary
        score = result.overall_score
        icon = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
        print(f"  {icon} 得分: {score}/100 | "
              f"🔴 {s['critical']} critical  "
              f"🟠 {s['major']} major  "
              f"🟡 {s['minor']} minor\n")
