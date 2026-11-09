"""
Gmail API Fetcher & AI Classifier
Connects to Gmail via Google OAuth 2.0 (gmail.readonly scope),
fetches real incoming messages, analyzes them using MailClassifier,
and updates sample_emails.json and index.html.
"""
import os
import base64
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import SAMPLE_EMAILS_PATH
from mail_classifier import MailClassifier, EmailItem

load_dotenv()

# Only request read-only access to emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / 'token.json'
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'

def get_gmail_service():
    """Authenticates the user and returns an authorized Gmail API service."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"\n[오류] {CREDENTIALS_FILE.name} 파일이 없습니다.\n"
                    "1. Google Cloud Console (https://console.cloud.google.com/) 접속\n"
                    "2. '사용자 인증 정보' -> 'OAuth 클라이언트 ID 만들기' (데스크톱 앱)\n"
                    "3. 다운로드한 JSON 파일 이름을 'credentials.json'으로 변경하여 이 폴더에 넣어주세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next runs
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def clean_body_text(raw_text: str) -> str:
    """Cleans HTML tags and removes excess whitespaces."""
    if not raw_text:
        return ""
    text = BeautifulSoup(raw_text, "html.parser").get_text()
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:1000]

def fetch_recent_gmails(service, max_results: int = 8, mask_privacy: bool = True) -> list[EmailItem]:
    """Fetches recent emails from user's Gmail inbox."""
    print(f"\n[1/3] Gmail 수신함에서 최신 메일 목록 조회 중 (최대 {max_results}건)...")
    results = service.users().messages().list(userId='me', maxResults=max_results, q='in:inbox').execute()
    messages = results.get('messages', [])

    if not messages:
        print("  - 수신함에 이메일이 없습니다.")
        return []

    email_items = []
    print(f"\n[2/3] 메일 본문 및 헤더 상세 데이터 파싱 중...")

    for idx, msg_meta in enumerate(messages, start=1):
        msg = service.users().messages().get(userId='me', id=msg_meta['id'], format='full').execute()
        headers = msg.get('payload', {}).get('headers', [])

        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(제목 없음)')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '알 수 없음')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '오늘')

        # Extract body
        body = ""
        payload = msg.get('payload', {})
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
                elif part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}) and not body:
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        body_cleaned = clean_body_text(body) or clean_body_text(msg.get('snippet', ''))

        if mask_privacy:
            sender_display = re.sub(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'***@\2', sender)
        else:
            sender_display = sender

        item = EmailItem(
            id=f"gmail-{idx:03d}",
            sender=sender_display,
            subject=subject,
            date=date[:25] if date else "오늘",
            body=body_cleaned
        )
        email_items.append(item)
        print(f"  [{idx}/{len(messages)}] {subject[:35]}... ({sender_display[:20]})")

    return email_items

def update_portfolio_data(emails: list[EmailItem]):
    """Classifies emails and updates sample_emails.json and index.html."""
    print(f"\n[3/3] AI 엔진을 통한 Gmail 중요도 분석 및 카테고리 분류 중...")
    classifier = MailClassifier()
    analyzed = classifier.classify_all(emails)

    # 1. Update sample_emails.json
    export_data = []
    for m in emails:
        export_data.append({
            "id": m.id,
            "sender": m.sender,
            "subject": m.subject,
            "date": m.date,
            "body": m.body
        })

    with open(SAMPLE_EMAILS_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {SAMPLE_EMAILS_PATH.name} 파일 갱신 완료")

    # 2. Update index.html
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        js_data = []
        for m, a in zip(emails, analyzed):
            js_data.append({
                "id": m.id,
                "sender": m.sender,
                "subject": m.subject,
                "date": m.date,
                "importance": a.importance,
                "category": a.category,
                "summary": a.one_line_summary,
                "reason": a.reason,
                "action_items": a.action_items,
                "body": m.body
            })

        formatted_json = json.dumps(js_data, ensure_ascii=False, indent=12)
        pattern = r'const emailsData = \[.*?\];'
        replacement = f'const emailsData = {formatted_json};'
        new_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"  ✓ {index_path.name} 웹 대시보드 데이터 갱신 완료")

    print("\n🎉 실제 Gmail 연동 및 AI 분류가 완료되었습니다!")

if __name__ == '__main__':
    print("=" * 60)
    print(" 📧 Gmail API 실시간 AI 연동기 (Google OAuth 2.0)")
    print("=" * 60)

    try:
        service = get_gmail_service()
        emails = fetch_recent_gmails(service, max_results=8, mask_privacy=True)
        if emails:
            update_portfolio_data(emails)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

