"""
Naver Mail IMAP Fetcher & AI Classifier
Connects to Naver Mail via IMAP, fetches recent inbox emails,
analyzes importance and categories using MailClassifier, and updates data.
"""
import imaplib
import email
from email.header import decode_header
import json
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from config import SAMPLE_EMAILS_PATH
from mail_classifier import MailClassifier, EmailItem

# Load .env if present
load_dotenv()

NAVER_IMAP_SERVER = "imap.naver.com"
NAVER_IMAP_PORT = 993

def clean_header(header_value: str) -> str:
    """Decodes MIME encoded email headers (e.g. EUC-KR, UTF-8, Base64)."""
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    result = []
    for fragment, charset in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                charset = charset or "utf-8"
                result.append(fragment.decode(charset, errors="ignore"))
            except Exception:
                result.append(fragment.decode("utf-8", errors="ignore"))
        else:
            result.append(str(fragment))
    return " ".join(result).strip()

def extract_body(msg: email.message.Message) -> str:
    """Extracts plain text or cleans HTML content from an email message."""
    text_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                continue
            if content_type == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    text_content += payload.decode(charset, errors="ignore")
                    break
            elif content_type == "text/html" and not text_content:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    html_text = payload.decode(charset, errors="ignore")
                    text_content = BeautifulSoup(html_text, "html.parser").get_text()
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        if payload:
            text_content = payload.decode(charset, errors="ignore")
            if msg.get_content_type() == "text/html":
                text_content = BeautifulSoup(text_content, "html.parser").get_text()

    # Clean consecutive whitespaces
    clean_body = re.sub(r'\s+', ' ', text_content).strip()
    return clean_body[:1000] # Limit to first 1000 characters for token efficiency

def fetch_naver_inbox(username: str, password: str, limit: int = 8, mask_privacy: bool = True) -> list[EmailItem]:
    """
    Connects to Naver IMAP and fetches the latest emails.
    """
    # Clean username if user entered full email
    user_id = username.split("@")[0].strip()

    print(f"\n[1/3] 네이버 IMAP 서버({NAVER_IMAP_SERVER}:{NAVER_IMAP_PORT})에 접속 중...")
    mail = imaplib.IMAP4_SSL(NAVER_IMAP_SERVER, NAVER_IMAP_PORT)
    
    try:
        mail.login(user_id, password)
        print("  ✓ 로그인 성공!")
    except Exception as e:
        raise RuntimeError(
            f"네이버 로그인 실패: {e}\n"
            "※ 확인 사항:\n"
            "1. 네이버 메일 웹설정에서 'IMAP/SMTP 사용'이 [사용함]으로 설정되어 있는지 확인하세요.\n"
            "2. 네이버 2단계 인증을 사용 중이시라면 '일반 비밀번호' 대신 '애플리케이션 비밀번호(종류: 메일)'를 사용해야 합니다."
        )

    mail.select("INBOX")
    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        print("  - 수신함에 메일이 없습니다.")
        return []

    mail_ids = messages[0].split()
    latest_ids = mail_ids[-limit:] # Take recent N emails
    latest_ids.reverse() # Newest first

    fetched_emails = []
    print(f"\n[2/3] 최신 수신 메일 {len(latest_ids)}개 수집 및 본문 파싱 중...")

    for idx, mid in enumerate(latest_ids, start=1):
        status, data = mail.fetch(mid, "(RFC822)")
        if status != "OK":
            continue

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = clean_header(msg.get("Subject", "(제목 없음)"))
        sender = clean_header(msg.get("From", "알 수 없음"))
        date = clean_header(msg.get("Date", ""))
        body = extract_body(msg)

        if not body:
            body = subject

        # Optional privacy masking for portfolio publishing
        if mask_privacy:
            # Mask user real name or sensitive digits
            sender_display = re.sub(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'***@\2', sender)
        else:
            sender_display = sender

        fetched_emails.append(EmailItem(
            id=f"naver-{idx:03d}",
            sender=sender_display,
            subject=subject,
            date=date[:25] if date else "오늘",
            body=body
        ))
        print(f"  [{idx}/{len(latest_ids)}] {subject[:35]}... ({sender[:20]})")

    mail.logout()
    return fetched_emails

def update_portfolio_data(emails: list[EmailItem]):
    """
    Classifies fetched emails and updates sample_emails.json and index.html data.
    """
    print(f"\n[3/3] AI 엔진을 통한 네이버 메일 중요도 분석 및 카테고리 분류 중...")
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

    # 2. Update index.html emailsData
    index_path = Path(__file__).resolve().parent / "index.html"
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
        # Replace const emailsData = [...] in index.html
        pattern = r'const emailsData = \[.*?\];'
        replacement = f'const emailsData = {formatted_json};'
        new_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"  ✓ {index_path.name} 웹 대시보드 데이터 갱신 완료")

    print("\n🎉 네이버 메일 연동 및 AI 분류가 완료되었습니다!")
    print("브라우저에서 새로고침(F5)을 누르면 실제 네이버 메일이 분류된 결과를 바로 확인할 수 있습니다.")

if __name__ == "__main__":
    import getpass
    print("=" * 60)
    print(" 📧 네이버 메일 수신함 실시간 AI 연동기 (Naver Mail Importer)")
    print("=" * 60)

    user = os.getenv("NAVER_ID") or input("네이버 아이디: ").strip()
    pwd = os.getenv("NAVER_PW") or getpass.getpass("네이버 비밀번호 (or 애플리케이션 비밀번호): ").strip()
    
    count_input = input("가져올 최신 메일 개수 (기본값: 8): ").strip()
    count = int(count_input) if count_input.isdigit() else 8

    mask_input = input("깃허브 공개를 위해 이메일 주소/개인정보를 마스킹할까요? (Y/n): ").strip().lower()
    mask = False if mask_input == "n" else True

    try:
        emails = fetch_naver_inbox(user, pwd, limit=count, mask_privacy=mask)
        if emails:
            update_portfolio_data(emails)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

