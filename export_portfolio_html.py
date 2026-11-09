"""
HTML Portfolio Exporter
Converts PORTFOLIO.md into a beautifully styled HTML file ready for browser viewing or PDF printing.
"""
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
MD_PATH = BASE_DIR / "PORTFOLIO.md"
HTML_PATH = BASE_DIR / "portfolio.html"

def convert_md_to_html():
    if not MD_PATH.exists():
        print(f"Error: {MD_PATH} not found.")
        return

    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Preprocess mermaid diagrams
    def replace_mermaid(match):
        diagram = match.group(1).strip()
        return f'<div class="mermaid">\n{diagram}\n</div>'

    processed_md = re.sub(r'```mermaid\s+(.*?)\s+```', replace_mermaid, md_text, flags=re.DOTALL)

    # Use markdown-it if available, else simple converter
    try:
        from markdown_it import MarkdownIt
        md = MarkdownIt("commonmark", {"breaks": True, "html": True})
        body_html = md.render(processed_md)
    except ImportError:
        # Fallback simple converter
        body_html = f"<pre style='white-space: pre-wrap;'>{processed_md}</pre>"

    full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartMail & DailyBriefing AI - 포트폴리오</title>
    <!-- Mermaid JS -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true, theme: 'neutral'}});</script>
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        * {{
            box-sizing: border-box;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
        }}
        
        body {{
            background-color: #f8fafc;
            color: #1e293b;
            line-height: 1.7;
            margin: 0;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            padding: 50px 60px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }}

        h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            color: #0f172a;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 12px;
            margin-top: 0;
        }}

        h2 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e3a8a;
            margin-top: 36px;
            margin-bottom: 16px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
        }}

        h3 {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #2563eb;
            margin-top: 24px;
            margin-bottom: 12px;
        }}

        blockquote {{
            background: #f1f5f9;
            border-left: 5px solid #3b82f6;
            margin: 16px 0;
            padding: 14px 20px;
            border-radius: 0 8px 8px 0;
            color: #334155;
            font-size: 0.98rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95rem;
        }}

        th, td {{
            padding: 12px 14px;
            border: 1px solid #cbd5e1;
            text-align: left;
        }}

        th {{
            background-color: #f8fafc;
            font-weight: 700;
            color: #0f172a;
        }}

        tr:nth-child(even) {{
            background-color: #fbfcfe;
        }}

        code {{
            background: #f1f5f9;
            color: #dc2626;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: Consolas, Monaco, monospace;
        }}

        .mermaid {{
            text-align: center;
            background: #f8fafc;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin: 24px 0;
        }}

        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.3);
            transition: all 0.2s ease;
        }}

        .print-btn:hover {{
            background: #1d4ed8;
            transform: translateY(-1px);
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                border: none;
                padding: 0;
                max-width: 100%;
            }}
            .print-btn {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">🖨️ PDF로 저장 / 인쇄</button>
    <div class="container">
        {body_html}
    </div>
</body>
</html>
"""

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Successfully generated: {HTML_PATH}")

if __name__ == "__main__":
    convert_md_to_html()
