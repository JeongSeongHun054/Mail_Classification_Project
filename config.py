"""
SmartMail & DailyBriefing AI - Configuration
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_EMAILS_PATH = BASE_DIR / "sample_emails.json"

# Category Definitions
EMAIL_CATEGORIES = {
    "URGENT": "긴급 업무",
    "NORMAL": "일반 업무",
    "NOTICE": "단순 공지",
    "PROMO": "광고/홍보"
}

IMPORTANCE_LEVELS = ["HIGH", "MEDIUM", "LOW"]

# RSS Feeds for 3 Key News Domains
NEWS_RSS_FEEDS = {
    "IT/테크": [
        "https://www.yonhapnewstv.co.kr/category/news/economy/feed/",
        "https://rss.donga.com/it.xml",
    ],
    "경제/금융": [
        "https://www.mk.co.kr/rss/30100041/", # 매일경제 경제
        "https://rss.hankyung.com/feed/economy.xml" # 한국경제
    ],
    "시사/종합": [
        "https://rss.donga.com/total.xml",
        "https://www.khan.co.kr/rss/rssdata/total_news.xml"
    ]
}

# Fallback Sample News for offline/resilient presentation
FALLBACK_NEWS = [
    {
        "category": "IT/테크",
        "title": "SK텔레콤, 차세대 AI 에이전트 인프라 확장 및 생성형 AI 서비스 가속화",
        "link": "https://example.com/news/it/1",
        "published": "2026-11-09 09:30",
        "summary": "• SKT가 자체 거대언어모델(LLM)과 글로벌 파트너십을 결합한 통합 AI 서비스 생태계를 본격 확대합니다.\n• 기업 및 개인 맞춤형 인공지능 비서 서비스의 연동 성능을 대폭 끌어올렸습니다.\n• 향후 일상 자동화와 데이터 분석 파이프라인의 핵심 축으로 자리잡을 전망입니다."
    },
    {
        "category": "IT/테크",
        "title": "오픈소스 경량 LLM 모델 고도화... 온디바이스 AI 채택 급증",
        "link": "https://example.com/news/it/2",
        "published": "2026-11-09 08:45",
        "summary": "• 파라미터 7B 이하의 초경량 언어 모델들이 텍스트 분류와 요약 태스크에서 상용 대형 모델에 필적하는 정확도를 기록했습니다.\n• 프라이버시 보호와 클라우드 API 호출 비용 절감 측면에서 엔터프라이즈 도입이 가속화되고 있습니다.\n• 로컬 자동화 에이전트 개발 트렌드가 활성화되는 추세입니다."
    },
    {
        "category": "경제/금융",
        "title": "글로벌 금리 인하 기대감 속 신기술 스타트업 투자 심리 점진적 회복세",
        "link": "https://example.com/news/eco/1",
        "published": "2026-11-09 09:10",
        "summary": "• 주요 중앙은행들의 통화 완화 기조 전망에 따라 AI 및 로보틱스 기술 기반 벤처 투자가 반등하고 있습니다.\n• 단순 아이디어보다는 실질적 비용 절감과 자동화 솔루션을 검증한 B2B 소프트웨어에 자금이 집중되고 있습니다.\n• 국내 테크 생태계에도 긍정적인 파급 효과가 예상됩니다."
    },
    {
        "category": "시사/종합",
        "title": "정부, '전국민 AI 일상화 및 디지털 인재 양성' 집중 투자 계획 발표",
        "link": "https://example.com/news/current/1",
        "published": "2026-11-09 07:50",
        "summary": "• 디지털 전환 시대를 주도할 실무형 AI 핵심 인력 육성을 위한 2~3년 전일제 심화 교육 프로젝트가 확대 시행됩니다.\n• 산학 연계 프로젝트 중심의 실무 커리큘럼을 통해 현업 투입 즉시 성과를 내는 엔지니어를 양성할 계획입니다.\n• 기업들의 AI 인재 채용 수요와 맞물려 큰 호응을 얻고 있습니다."
    }
]

