# UI-Inspector 🔍

基于 Claude Vision 的 UI 走查工具，自动对比设计稿和 Storybook 组件实现，生成可视化报告。

## 架构

```
Agent（调度器）
├── Tool: StorybookScreenshotter  → Playwright 渲染截图
├── Tool: VisionComparator        → Claude Vision 视觉对比
└── Tool: ReportGenerator         → Markdown + HTML 报告
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置 API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. 启动你的 Storybook

```bash
cd your-project && npm run storybook
# 默认运行在 http://localhost:6006
```

### 4. 运行走查

**单组件：**
```bash
python run.py \
  --design ./designs/Button.png \
  --story  components-button--primary \
  --name   "PrimaryButton"
```

**批量走查（推荐）：**
```bash
# 生成配置模板
python run.py --example > inspection.json

# 编辑配置后执行
python run.py --config inspection.json
```

## 配置文件格式

```json
{
  "storybook_url": "http://localhost:6006",
  "output_dir": "./reports",
  "tasks": [
    {
      "component_name": "PrimaryButton",
      "design_image_path": "./designs/button-primary.png",
      "storybook_story_id": "components-button--primary",
      "viewport": { "width": 1440, "height": 900 },
      "extra_context": "检查 hover/disabled 状态"
    }
  ]
}
```

### Story ID 查找方式

在 Storybook 中打开组件，URL 格式为：
```
http://localhost:6006/?path=/story/components-button--primary
                                        ↑ 这就是 story_id
```

## 报告输出

走查完成后，报告保存在 `./reports/report_YYYYMMDD_HHMMSS/` 目录：

```
report_20241201_143022/
├── report.html        ← 可视化报告（直接用浏览器打开）
├── report.md          ← Markdown 摘要
├── data.json          ← 原始数据（可接入 CI/CD）
└── screenshots/
    ├── Button.png            ← 代码截图
    └── Button_design.png     ← 设计稿
```

## 问题严重级别

| 级别 | 说明 | 示例 |
|------|------|------|
| 🔴 Critical | 阻断级，必须修复 | 布局错乱、品牌色错误、组件缺失 |
| 🟠 Major | 重要，影响体验 | 间距偏差 >4px、字重不对、阴影差异 |
| 🟡 Minor | 轻微，建议修复 | 间距偏差 1-4px、细微颜色差异 |

**忽略项：** 文字内容、图片内容、动态数据

## CI/CD 集成示例

```yaml
# .github/workflows/ui-inspection.yml
- name: UI 走查
  run: |
    pip install -r requirements.txt
    playwright install chromium
    python run.py --config inspection.json
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

- name: 上传报告
  uses: actions/upload-artifact@v3
  with:
    name: ui-inspection-report
    path: reports/
```

## Python API 用法

```python
import asyncio
from core.agent import UIInspectorAgent, InspectionTask

agent = UIInspectorAgent(api_key="sk-ant-...")

tasks = [
    InspectionTask(
        component_name="Button",
        design_image_path="./designs/button.png",
        storybook_story_id="components-button--primary",
    )
]

asyncio.run(agent.inspect(tasks, output_dir="./reports"))
```

