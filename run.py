#!/usr/bin/env python3
"""
UI 走查工具 - 命令行入口

用法：
  # 单组件走查
  python run.py --design ./designs/Button.png --story button--primary --name "Button"

  # 批量走查（使用配置文件）
  python run.py --config ./inspection.json

  # 查看示例配置
  python run.py --example
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.agent import UIInspectorAgent, InspectionTask


EXAMPLE_CONFIG = {
    "storybook_url": "http://localhost:6006",
    "output_dir": "./reports",
    "tasks": [
        {
            "component_name": "PrimaryButton",
            "design_image_path": "./designs/button-primary.png",
            "storybook_story_id": "components-button--primary",
            "viewport": {"width": 1440, "height": 900},
            "extra_context": "检查悬停状态和禁用状态"
        },
        {
            "component_name": "InputField",
            "design_image_path": "./designs/input-default.png",
            "storybook_story_id": "components-input--default",
            "viewport": {"width": 1440, "height": 900},
            "extra_context": "重点检查聚焦边框颜色"
        }
    ]
}


def main():
    parser = argparse.ArgumentParser(
        description="UI 走查工具 - 对比设计稿和 Storybook 实现",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config",  "-c", help="批量走查配置文件（JSON）")
    parser.add_argument("--design",  "-d", help="设计稿图片路径")
    parser.add_argument("--story",   "-s", help="Storybook Story ID")
    parser.add_argument("--name",    "-n", help="组件名称", default="Component")
    parser.add_argument("--sb-url",        help="Storybook URL", default="http://localhost:6006")
    parser.add_argument("--output",  "-o", help="报告输出目录", default="./reports")
    parser.add_argument("--example",       help="打印示例配置", action="store_true")

    args = parser.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE_CONFIG, ensure_ascii=False, indent=2))
        return

    agent = UIInspectorAgent()

    if args.config:
        # 批量模式
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        tasks = [InspectionTask(**t) for t in config["tasks"]]
        output_dir = config.get("output_dir", args.output)
        asyncio.run(agent.inspect(tasks, output_dir))

    elif args.design and args.story:
        # 单组件模式
        task = InspectionTask(
            component_name=args.name,
            design_image_path=args.design,
            storybook_story_id=args.story,
            storybook_url=args.sb_url,
        )
        asyncio.run(agent.inspect([task], args.output))

    else:
        parser.print_help()
        print("\n💡 示例：")
        print("  python run.py --design ./Button.png --story button--primary --name Button")
        print("  python run.py --config inspection.json")
        print("  python run.py --example > inspection.json")


if __name__ == "__main__":
    main()
