"""
Unit Tests for SmartMail & DailyBriefing AI
Verifies classification accuracy, fallback logic, and news summarization pipeline.
"""
import unittest
import json
from pathlib import Path

from config import SAMPLE_EMAILS_PATH
from mail_classifier import MailClassifier, EmailItem, EmailAnalysisResult
from news_summarizer import NewsSummarizer

class TestMailClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = MailClassifier()
        with open(SAMPLE_EMAILS_PATH, "r", encoding="utf-8") as f:
            self.emails = [EmailItem(**item) for item in json.load(f)]

    def test_sample_emails_exist(self):
        self.assertGreaterEqual(len(self.emails), 5)

    def test_urgent_email_detection(self):
        # First email is urgent: [긴급] SK AIGEN 2차 프로젝트 최종 기획서 검토 요청 (금일 17시 마감)
        urgent_email = self.emails[0]
        result = self.classifier.classify_email(urgent_email)
        self.assertEqual(result.importance, "HIGH")
        self.assertEqual(result.category, "긴급 업무")
        self.assertTrue(result.is_urgent)
        self.assertTrue(len(result.action_items) > 0)

    def test_advertisement_detection(self):
        # mail-005 is promo: [광고] 2026 최신 MLOps & LLM 파이프라인 올인원 패키지 75% 특별 할인
        promo_email = next(m for m in self.emails if "광고" in m.subject)
        result = self.classifier.classify_email(promo_email)
        self.assertEqual(result.importance, "LOW")
        self.assertEqual(result.category, "광고/홍보")
        self.assertFalse(result.is_urgent)

    def test_notice_detection(self):
        # mail-004 is notice: [공지] 11월 정기 서버 보안 점검 및 2차 인증(MFA) 갱신 안내
        notice_email = next(m for m in self.emails if "공지" in m.subject)
        result = self.classifier.classify_email(notice_email)
        self.assertEqual(result.category, "단순 공지")
        self.assertEqual(result.importance, "LOW")

class TestNewsSummarizer(unittest.TestCase):
    def setUp(self):
        self.summarizer = NewsSummarizer()

    def test_fetch_and_summarize(self):
        news = self.summarizer.fetch_and_summarize(max_per_category=1)
        self.assertIn("IT/테크", news)
        self.assertIn("경제/금융", news)
        self.assertIn("시사/종합", news)

        # Check each category has at least 1 article
        for cat, articles in news.items():
            self.assertGreaterEqual(len(articles), 1)
            self.assertTrue(len(articles[0].title) > 0)
            self.assertTrue(len(articles[0].summary) > 0)

if __name__ == "__main__":
    unittest.main()

