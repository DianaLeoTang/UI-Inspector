"""
报告生成器
输出 Markdown 摘要 + HTML 可视化报告
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


SEVERITY_CONFIG = {
    "critical": {"emoji": "🔴", "label": "Critical", "color": "#ef4444", "bg": "#fef2f2"},
    "major":    {"emoji": "🟠", "label": "Major",    "color": "#f97316", "bg": "#fff7ed"},
    "minor":    {"emoji": "🟡", "label": "Minor",    "color": "#eab308", "bg": "#fefce8"},
}

CATEGORY_LABELS = {
    "layout":     "布局结构",
    "spacing":    "间距/尺寸",
    "color":      "颜色",
    "typography": "字体排版",
    "border":     "边框",
    "shadow":     "阴影",
    "missing":    "元素缺失",
}


class ReportGenerator:

    def generate(self, results: list, output_path: Path) -> str:
        """生成完整报告，返回报告目录"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = output_path / f"report_{ts}"
        report_dir.mkdir(parents=True, exist_ok=True)

        # 复制截图到报告目录
        screenshots_dir = report_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        for r in results:
            src = Path(r.screenshot_path)
            if src.exists():
                shutil.copy2(src, screenshots_dir / src.name)
            design_src = Path(r.task.design_image_path)
            if design_src.exists():
                shutil.copy2(design_src, screenshots_dir / f"{r.task.component_name}_design{design_src.suffix}")

        # 生成报告
        md_path = report_dir / "report.md"
        html_path = report_dir / "report.html"

        md_content = self._build_markdown(results)
        html_content = self._build_html(results)

        md_path.write_text(md_content, encoding="utf-8")
        html_path.write_text(html_content, encoding="utf-8")

        # 保存原始数据
        data_path = report_dir / "data.json"
        data_path.write_text(
            json.dumps([self._result_to_dict(r) for r in results], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return str(report_dir)

    def _result_to_dict(self, result) -> dict:
        return {
            "component": result.task.component_name,
            "score": result.overall_score,
            "severity_summary": result.severity_summary,
            "issues": result.issues,
            "timestamp": result.timestamp,
        }

    # ─── Markdown ──────────────────────────────────────────────────────────────

    def _build_markdown(self, results: list) -> str:
        total = len(results)
        passed = sum(1 for r in results if r.overall_score >= 90)
        total_issues = sum(len(r.issues) for r in results)
        avg_score = sum(r.overall_score for r in results) // total if total else 0

        lines = [
            "# UI 走查报告",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 📊 总览",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 检查组件数 | {total} |",
            f"| 通过（≥90分）| {passed} |",
            f"| 需修改 | {total - passed} |",
            f"| 平均得分 | {avg_score}/100 |",
            f"| 问题总数 | {total_issues} |",
            "",
            "## 📋 组件详情",
            "",
        ]

        for r in results:
            score = r.overall_score
            icon = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
            s = r.severity_summary
            lines += [
                f"### {icon} {r.task.component_name}  —  {score}/100",
                "",
                f"🔴 Critical: {s['critical']}  |  🟠 Major: {s['major']}  |  🟡 Minor: {s['minor']}",
                "",
            ]

            if r.issues:
                lines.append("#### 问题清单\n")
                for issue in r.issues:
                    cfg = SEVERITY_CONFIG.get(issue["severity"], SEVERITY_CONFIG["minor"])
                    cat = CATEGORY_LABELS.get(issue["category"], issue["category"])
                    lines += [
                        f"**{cfg['emoji']} [{cfg['label']}] {issue['location']}** `{cat}`",
                        "",
                        f"- **设计稿：** {issue['design_spec']}",
                        f"- **实际实现：** {issue['actual_impl']}",
                        f"- **修改建议：** `{issue['suggestion']}`",
                        "",
                    ]
            else:
                lines.append("✅ 无问题，完全符合设计规范\n")

            lines.append("---\n")

        return "\n".join(lines)

    # ─── HTML ──────────────────────────────────────────────────────────────────

    def _build_html(self, results: list) -> str:
        total = len(results)
        passed = sum(1 for r in results if r.overall_score >= 90)
        avg_score = sum(r.overall_score for r in results) // total if total else 0

        cards_html = "".join(self._build_card(r) for r in results)

        critical_total = sum(r.severity_summary["critical"] for r in results)
        major_total    = sum(r.severity_summary["major"]    for r in results)
        minor_total    = sum(r.severity_summary["minor"]    for r in results)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UI 走查报告</title>
<style>
  :root {{
    --c-bg: #0f1117;
    --c-surface: #1a1d27;
    --c-border: #2a2d3a;
    --c-text: #e2e8f0;
    --c-muted: #64748b;
    --c-critical: #ef4444;
    --c-major: #f97316;
    --c-minor: #eab308;
    --c-pass: #22c55e;
    --c-accent: #6366f1;
    --radius: 12px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--c-bg); color: var(--c-text); font-family: 'SF Pro Display', -apple-system, system-ui, sans-serif; min-height: 100vh; }}
  
  .header {{ background: linear-gradient(135deg, #1e1b4b 0%, #0f1117 60%); border-bottom: 1px solid var(--c-border); padding: 40px 48px; }}
  .header h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
  .header h1 span {{ color: var(--c-accent); }}
  .header .meta {{ color: var(--c-muted); font-size: 13px; margin-top: 6px; }}

  .stats-bar {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: var(--c-border); border-bottom: 1px solid var(--c-border); }}
  .stat {{ background: var(--c-surface); padding: 24px 28px; }}
  .stat .num {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; }}
  .stat .label {{ font-size: 12px; color: var(--c-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat.pass .num {{ color: var(--c-pass); }}
  .stat.critical .num {{ color: var(--c-critical); }}
  .stat.major .num {{ color: var(--c-major); }}
  .stat.minor .num {{ color: var(--c-minor); }}

  .content {{ padding: 32px 48px; max-width: 1400px; }}
  .section-title {{ font-size: 13px; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; margin-top: 32px; }}

  .component-card {{ background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius); margin-bottom: 20px; overflow: hidden; }}
  .card-header {{ padding: 20px 24px; display: flex; align-items: center; gap: 16px; cursor: pointer; user-select: none; }}
  .card-header:hover {{ background: rgba(255,255,255,0.02); }}
  .score-badge {{ width: 52px; height: 52px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 800; flex-shrink: 0; }}
  .score-pass {{ background: rgba(34,197,94,.15); color: var(--c-pass); }}
  .score-warn {{ background: rgba(249,115,22,.15); color: var(--c-major); }}
  .score-fail {{ background: rgba(239,68,68,.15); color: var(--c-critical); }}
  .card-info {{ flex: 1; }}
  .card-info h3 {{ font-size: 16px; font-weight: 600; }}
  .card-info .chips {{ display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; }}
  .chip {{ padding: 2px 10px; border-radius: 100px; font-size: 11px; font-weight: 600; }}
  .chip-critical {{ background: rgba(239,68,68,.15); color: var(--c-critical); }}
  .chip-major {{ background: rgba(249,115,22,.15); color: var(--c-major); }}
  .chip-minor {{ background: rgba(234,179,8,.15); color: var(--c-minor); }}
  .chip-pass {{ background: rgba(34,197,94,.15); color: var(--c-pass); }}
  .toggle-icon {{ color: var(--c-muted); transition: transform .2s; }}
  .card-body {{ border-top: 1px solid var(--c-border); }}
  .card-body.collapsed {{ display: none; }}

  .diff-view {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
  .diff-panel {{ padding: 20px 24px; }}
  .diff-panel:first-child {{ border-right: 1px solid var(--c-border); }}
  .diff-panel h4 {{ font-size: 11px; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
  .diff-panel img {{ width: 100%; border-radius: 8px; border: 1px solid var(--c-border); }}
  .no-image {{ background: rgba(255,255,255,.03); border: 1px dashed var(--c-border); border-radius: 8px; height: 160px; display: flex; align-items: center; justify-content: center; color: var(--c-muted); font-size: 13px; }}

  .issues-list {{ padding: 0 24px 20px; }}
  .issue-item {{ border: 1px solid var(--c-border); border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; border-left-width: 3px; }}
  .issue-item.critical {{ border-left-color: var(--c-critical); background: rgba(239,68,68,.04); }}
  .issue-item.major    {{ border-left-color: var(--c-major);    background: rgba(249,115,22,.04); }}
  .issue-item.minor    {{ border-left-color: var(--c-minor);    background: rgba(234,179,8,.04);  }}
  .issue-top {{ display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }}
  .issue-sev {{ font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; }}
  .issue-sev.critical {{ background: rgba(239,68,68,.2); color: var(--c-critical); }}
  .issue-sev.major    {{ background: rgba(249,115,22,.2); color: var(--c-major); }}
  .issue-sev.minor    {{ background: rgba(234,179,8,.2);  color: var(--c-minor); }}
  .issue-cat {{ font-size: 11px; color: var(--c-muted); background: rgba(255,255,255,.05); padding: 2px 8px; border-radius: 4px; }}
  .issue-loc {{ font-size: 14px; font-weight: 600; color: var(--c-text); }}
  .issue-rows {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }}
  .issue-row {{ background: rgba(255,255,255,.03); border-radius: 6px; padding: 8px 12px; }}
  .issue-row label {{ display: block; font-size: 10px; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .issue-row p {{ font-size: 13px; color: var(--c-text); }}
  .issue-suggestion {{ background: rgba(99,102,241,.08); border: 1px solid rgba(99,102,241,.2); border-radius: 6px; padding: 8px 12px; }}
  .issue-suggestion label {{ display: block; font-size: 10px; color: var(--c-accent); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .issue-suggestion code {{ font-size: 12px; color: #a5b4fc; font-family: 'SF Mono', 'Fira Code', monospace; white-space: pre-wrap; }}

  .passed-section {{ padding: 0 24px 20px; }}
  .passed-item {{ display: inline-flex; align-items: center; gap: 6px; background: rgba(34,197,94,.08); border: 1px solid rgba(34,197,94,.15); color: var(--c-pass); font-size: 12px; padding: 4px 12px; border-radius: 100px; margin: 4px; }}

  @media (max-width: 768px) {{
    .stats-bar {{ grid-template-columns: repeat(3, 1fr); }}
    .diff-view {{ grid-template-columns: 1fr; }}
    .issue-rows {{ grid-template-columns: 1fr; }}
    .content {{ padding: 16px; }}
    .header {{ padding: 24px 16px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>UI <span>走查报告</span></h1>
  <p class="meta">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>

<div class="stats-bar">
  <div class="stat">
    <div class="num">{total}</div>
    <div class="label">检查组件</div>
  </div>
  <div class="stat pass">
    <div class="num">{passed}</div>
    <div class="label">通过（≥90分）</div>
  </div>
  <div class="stat">
    <div class="num">{avg_score}</div>
    <div class="label">平均得分</div>
  </div>
  <div class="stat critical">
    <div class="num">{critical_total}</div>
    <div class="label">🔴 Critical</div>
  </div>
  <div class="stat major">
    <div class="num">{major_total}</div>
    <div class="label">🟠 Major</div>
  </div>
</div>

<div class="content">
  <div class="section-title">组件走查详情</div>
  {cards_html}
</div>

<script>
document.querySelectorAll('.card-header').forEach(header => {{
  header.addEventListener('click', () => {{
    const body = header.nextElementSibling;
    const icon = header.querySelector('.toggle-icon');
    body.classList.toggle('collapsed');
    icon.style.transform = body.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
  }});
}});
</script>
</body>
</html>"""

    def _build_card(self, r) -> str:
        score = r.overall_score
        score_cls = "score-pass" if score >= 90 else "score-warn" if score >= 70 else "score-fail"
        s = r.severity_summary

        chips = []
        if s["critical"]: chips.append(f'<span class="chip chip-critical">🔴 {s["critical"]} Critical</span>')
        if s["major"]:    chips.append(f'<span class="chip chip-major">🟠 {s["major"]} Major</span>')
        if s["minor"]:    chips.append(f'<span class="chip chip-minor">🟡 {s["minor"]} Minor</span>')
        if not r.issues:  chips.append('<span class="chip chip-pass">✅ 通过</span>')

        # 图片路径（相对路径）
        design_ext = Path(r.task.design_image_path).suffix
        design_img = f'screenshots/{r.task.component_name}_design{design_ext}'
        screenshot_img = f'screenshots/{r.task.component_name}.png'

        issues_html = ""
        for issue in r.issues:
            cat = CATEGORY_LABELS.get(issue["category"], issue["category"])
            sev = issue["severity"]
            issues_html += f"""
<div class="issue-item {sev}">
  <div class="issue-top">
    <span class="issue-sev {sev}">{sev}</span>
    <span class="issue-cat">{cat}</span>
    <span class="issue-loc">{issue['location']}</span>
  </div>
  <div class="issue-rows">
    <div class="issue-row">
      <label>设计稿规范</label>
      <p>{issue['design_spec']}</p>
    </div>
    <div class="issue-row">
      <label>当前实现</label>
      <p>{issue['actual_impl']}</p>
    </div>
  </div>
  <div class="issue-suggestion">
    <label>修改建议</label>
    <code>{issue['suggestion']}</code>
  </div>
</div>"""

        passed_html = ""
        if r.issues == [] or hasattr(r, 'passed_checks'):
            passed_items = getattr(r, 'passed_checks', [])
            if passed_items:
                passed_html = '<div class="passed-section">'
                for p in passed_items:
                    passed_html += f'<span class="passed-item">✓ {p}</span>'
                passed_html += '</div>'

        return f"""
<div class="component-card">
  <div class="card-header">
    <div class="score-badge {score_cls}">{score}</div>
    <div class="card-info">
      <h3>{r.task.component_name}</h3>
      <div class="chips">{"".join(chips)}</div>
    </div>
    <svg class="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
  </div>
  <div class="card-body">
    <div class="diff-view">
      <div class="diff-panel">
        <h4>设计稿</h4>
        <img src="{design_img}" alt="设计稿" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'>暂无图片</div>'">
      </div>
      <div class="diff-panel">
        <h4>代码实现</h4>
        <img src="{screenshot_img}" alt="截图" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'>暂无截图</div>'">
      </div>
    </div>
    {issues_html}
    {passed_html}
  </div>
</div>"""
