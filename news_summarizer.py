"""
SmartMail & DailyBriefing AI - News Summarizer Module
Collects real-time articles across IT, Economy, and Current Affairs via RSS,
and generates concise 3-line key point summaries.
"""
from dataclasses import dataclass
import os
import re
from typing import List, Dict, Optional
import feedparser
from bs4 import BeautifulSoup
import requests

from config import NEWS_RSS_FEEDS, FALLBACK_NEWS

@dataclass
class NewsArticle:
    category: str
    title: str
    link: str
    published: str
    summary: str
    takeaway: str = ""

class NewsSummarizer:
    """
    Multi-category News Scraper & AI Summarizer.
    Collects articles from IT, Economy, and General news feeds and summarizes them.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def fetch_and_summarize(self, max_per_category: int = 2) -> Dict[str, List[NewsArticle]]:
        """
        Fetches news for all categories and returns summarized articles by category.
        """
        results: Dict[str, List[NewsArticle]] = {}

        for category, feed_urls in NEWS_RSS_FEEDS.items():
            category_articles: List[NewsArticle] = []
            for url in feed_urls:
                if len(category_articles) >= max_per_category:
                    break
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:max_per_category]:
                        title = entry.get("title", "").strip()
                        link = entry.get("link", "#")
                        published = entry.get("published", entry.get("updated", "오늘"))
                        raw_summary = entry.get("summary", entry.get("description", ""))

                        # Clean HTML tags
                        clean_text = BeautifulSoup(raw_summary, "html.parser").get_text().strip()
                        clean_text = re.sub(r'\s+', ' ', clean_text)

                        # Generate 3-line summary
                        summary_points, takeaway = self._summarize_text(title, clean_text)

                        article = NewsArticle(
                            category=category,
                            title=title,
                            link=link,
                            published=published[:16] if len(published) > 16 else published,
                            summary=summary_points,
                            takeaway=takeaway
                        )
                        category_articles.append(article)
                        if len(category_articles) >= max_per_category:
                            break
                except Exception as e:
                    print(f"[Warning] Failed to fetch feed {url}: {e}")

            # If RSS fetching failed or gave zero articles, use curated fallback news
            if not category_articles:
                matched = [item for item in FALLBACK_NEWS if item["category"] == category]
                for m in matched[:max_per_category]:
                    category_articles.append(
                        NewsArticle(
                            category=m["category"],
                            title=m["title"],
                            link=m["link"],
                            published=m["published"],
                            summary=m["summary"],
                            takeaway="기술 및 시장 동향을 주시하여 개발 역량에 반영 필요"
                        )
                    )

            results[category] = category_articles

        return results

    def _summarize_text(self, title: str, text: str) -> tuple[str, str]:
        """
        Summarizes news content into 3 key bullet points and 1 takeaway insight.
        """
        if self.api_key and len(text) > 40:
            try:
                return self._summarize_with_llm(title, text)
            except Exception as e:
                print(f"[Warning] LLM News summarization failed: {e}. Using fallback.")

        # Heuristic / Extractive fallback summarization
        sentences = [s.strip() for s in re.split(r'[\.\?\!]\s+', text) if len(s.strip()) > 15]
        if len(sentences) >= 3:
            bullet_summary = f"• {sentences[0]}.\n• {sentences[1]}.\n• {sentences[2]}."
        elif len(sentences) == 2:
            bullet_summary = f"• {sentences[0]}.\n• {sentences[1]}.\n• {title} 관련 주요 후속 조치 예정."
        elif len(sentences) == 1:
            bullet_summary = f"• {sentences[0]}.\n• 관련 분야 전문가들의 기술/시장 분석 지속.\n• 업계 영향도 모니터링 필요."
        else:
            bullet_summary = f"• {title} 보도 핵심 내용 전달.\n• 주요 세부 지표 및 향후 일정 확인 필요.\n• 관련 업계 파급 효과 주목."

        takeaway = f"주요 시사점: {title[:20]} 관련 시장 흐름과 최신 기술 동향 파악"
        return bullet_summary, takeaway

    def _summarize_with_llm(self, title: str, text: str) -> tuple[str, str]:
        """Uses Gemini API to produce high-density 3-line summaries."""
        prompt = f"""다음 기사를 읽고 직장인/엔지니어가 10초 만에 핵심을 파악할 수 있도록
1. 핵심 요약 3줄 (각 줄은 '• '로 시작하는 불릿포인트)
2. 실무자 관점의 1줄 시사점(Takeaway)
을 생성하세요.

[기사 제목] {title}
[기사 본문]
{text[:1500]}

출력 형식:
• 첫 번째 핵심 내용 요약
• 두 번째 핵심 내용 요약
• 세 번째 핵심 내용 요약
[시사점] 실무자 관점의 한 줄 인사이트
"""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            res_json = resp.json()
            out_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()

            lines = [l.strip() for l in out_text.split('\n') if l.strip()]
            bullets = [l for l in lines if l.startswith('•') or l.startswith('-')]
            takeaway_line = next((l for l in lines if '시사점' in l or 'Takeaway' in l), "")
            takeaway = takeaway_line.replace('[시사점]', '').strip() if takeaway_line else "핵심 트렌드 파악 및 업무 적용"

            bullet_summary = "\n".join(bullets[:3]) if bullets else out_text
            return bullet_summary, takeaway
        else:
            raise RuntimeError(f"Gemini API returned status {resp.status_code}")

