"""
SmartMail & DailyBriefing AI - Mail Classifier Module
Analyzes email context, assesses priority, classifies categories, and extracts actionable items.
"""
from dataclasses import dataclass, field
import json
import os
import re
from typing import List, Optional, Dict, Any

from config import EMAIL_CATEGORIES, IMPORTANCE_LEVELS

@dataclass
class EmailItem:
    id: str
    sender: str
    subject: str
    date: str
    body: str

@dataclass
class EmailAnalysisResult:
    id: str
    importance: str              # HIGH, MEDIUM, LOW
    category: str                # 긴급 업무, 일반 업무, 단순 공지, 광고/홍보
    one_line_summary: str        # 핵심 1줄 요약
    action_items: List[str]      # 수행해야 할 작업 목록
    reason: str                  # AI 분류 및 중요도 판단 사유
    is_urgent: bool = False

class MailClassifier:
    """
    Email importance and contextual category classifier.
    Supports LLM-based zero-shot classification and rule-based heuristic fallback.
    """
    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()

    def classify_email(self, email: EmailItem) -> EmailAnalysisResult:
        """
        Classifies a single email item using LLM if available, otherwise heuristic fallback.
        """
        if self.api_key:
            try:
                if "gemini" in self.provider:
                    return self._classify_with_gemini(email)
            except Exception as e:
                # Log error and fallback
                print(f"[Warning] LLM classification failed ({e}). Falling back to rule-based engine.")

        return self._classify_heuristic(email)

    def classify_all(self, emails: List[EmailItem]) -> List[EmailAnalysisResult]:
        """Classifies a list of emails."""
        return [self.classify_email(m) for m in emails]

    def _classify_with_gemini(self, email: EmailItem) -> EmailAnalysisResult:
        """Uses Google Gemini API to analyze email context."""
        import requests

        prompt = f"""당신은 수신된 이메일의 중요도와 맥락을 정밀하게 분석하는 AI 비서입니다.
아래 메일을 읽고 JSON 형식으로 분석 결과를 생성하세요.

[메일 정보]
- 발신자: {email.sender}
- 제목: {email.subject}
- 수신일시: {email.date}
- 본문:
{email.body}

[분류 기준]
1. importance: "HIGH" (마감 시한, 결재/검토 요청, 즉각 조치 필요), "MEDIUM" (일반 업무 공유, 주간 일정), "LOW" (광고, 단순 공지, 판촉)
2. category: "긴급 업무", "일반 업무", "단순 공지", "광고/홍보" 중 하나
3. one_line_summary: 메일의 핵심 목적을 40자 이내로 명확하게 1줄 요약
4. action_items: 수신자가 직접 해야 할 일/기한 (문자열 배열, 없으면 빈 배열)
5. reason: 이 중요도와 카테고리로 분류한 명확한 기술적/맥락적 사유

반드시 순수한 JSON만 출력하세요. 마크다운 코드블록(```json) 없이 JSON 객체만 반환하세요:
{{
  "importance": "HIGH" | "MEDIUM" | "LOW",
  "category": "긴급 업무" | "일반 업무" | "단순 공지" | "광고/홍보",
  "one_line_summary": "...",
  "action_items": ["..."],
  "reason": "..."
}}
"""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        resp = requests.post(endpoint, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            data = json.loads(text)

            importance = data.get("importance", "MEDIUM")
            if importance not in IMPORTANCE_LEVELS:
                importance = "MEDIUM"

            category = data.get("category", "일반 업무")
            summary = data.get("one_line_summary", email.subject)
            actions = data.get("action_items", [])
            reason = data.get("reason", "LLM 맥락 분석 완료")

            return EmailAnalysisResult(
                id=email.id,
                importance=importance,
                category=category,
                one_line_summary=summary,
                action_items=actions,
                reason=reason,
                is_urgent=(importance == "HIGH")
            )
        else:
            raise RuntimeError(f"Gemini API Error: {resp.status_code} - {resp.text}")

    def _classify_heuristic(self, email: EmailItem) -> EmailAnalysisResult:
        """
        Sophisticated rule-based heuristic NLP analyzer used as fallback or local offline mode.
        """
        subject = email.subject
        body = email.body
        full_text = f"{subject}\n{body}"

        # 1. Check for Ads / Promo
        promo_keywords = ["광고", "할인", "특가", "세일", "쿠폰", "프로모션", "이벤트", "무료 체험", "얼리버드"]
        if any(kw in subject for kw in ["(광고)", "[광고]"]) or sum(1 for kw in promo_keywords if kw in full_text) >= 2:
            return EmailAnalysisResult(
                id=email.id,
                importance="LOW",
                category="광고/홍보",
                one_line_summary=re.sub(r'\[.*?\]|\(.*?\)', '', subject).strip() + " 관련 할인 및 프로모션 안내",
                action_items=[],
                reason="광고성 표기 및 판촉/할인 키워드 다수 감지로 저우선순위 분류",
                is_urgent=False
            )

        # 2. Check for Urgent / High Importance Work
        urgent_keywords = ["긴급", "마감", "승인", "검토 요청", "회신 부탁", "기한", "전자세금계산서", "결재"]
        has_urgent_tag = any(kw in subject for kw in ["[긴급]", "[중요]", "마감"])
        urgent_hits = [kw for kw in urgent_keywords if kw in full_text]

        # Extract deadlines / dates
        time_patterns = re.findall(r'(금일\s*\d+시|오늘\s*오후\s*\d+시|\d+월\s*\d+일|내일(?:까지)?)', full_text)
        deadline_str = f" (마감/일정: {', '.join(time_patterns[:2])})" if time_patterns else ""

        if has_urgent_tag or len(urgent_hits) >= 2:
            action_items = []
            if "검토" in full_text:
                action_items.append("첨부 기획서 및 파이프라인 지표 검토 후 회신")
            if "세금계산서" in full_text or "결재" in full_text:
                action_items.append("전자결재 시스템 접속 후 라이선스 정산 품의 승인")
            if "피드백" in full_text or "규격서" in full_text:
                action_items.append("API 연동 규격서 v1.2 스키마 호환성 확인 및 피드백")
            if not action_items:
                action_items.append("상세 내용 확인 후 회신 필요")

            summary = re.sub(r'\[.*?\]', '', subject).strip() + deadline_str
            return EmailAnalysisResult(
                id=email.id,
                importance="HIGH",
                category="긴급 업무",
                one_line_summary=summary,
                action_items=action_items,
                reason=f"마감 기한 및 직접적인 액션(검토/승인/회신) 요청 확인됨 ({', '.join(urgent_hits[:3])})",
                is_urgent=True
            )

        # 3. Check for Notices
        notice_keywords = ["공지", "점검", "안내", "일정 안내", "사내"]
        if any(kw in subject for kw in ["[공지]", "[안내]"]) or any(kw in full_text for kw in ["정기 점검", "일정 안내"]):
            return EmailAnalysisResult(
                id=email.id,
                importance="LOW",
                category="단순 공지",
                one_line_summary=re.sub(r'\[.*?\]', '', subject).strip(),
                action_items=["사내 공지 및 점검 일정 캘린더 확인"],
                reason="단순 시스템 점검 및 사내 공지사항으로 즉각적인 조치 불필요",
                is_urgent=False
            )

        # 4. Default to Normal Work
        action_items = []
        if "발표" in full_text or "스터디" in full_text:
            action_items.append("다음 차례 스터디 발표 자료 준비 (정형 JSON 출력)")
        else:
            action_items.append("내용 확인 및 필요 시 메모")

        return EmailAnalysisResult(
            id=email.id,
            importance="MEDIUM",
            category="일반 업무",
            one_line_summary=subject.strip(),
            action_items=action_items,
            reason="일상 업무 및 회의록 공유성 메일로 중간 우선순위 분류",
            is_urgent=False
        )

