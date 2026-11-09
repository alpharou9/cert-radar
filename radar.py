import os
import json
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9246640626:AAFY90tZ5rhKxfZaWFmhh97ykvD9oFh3pFM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "904278297")

CERTS_CACHE_FILE = "known_certs.json"
PROMOS_CACHE_FILE = "known_promos.json"

KEYWORDS = [
    "agent", "semantic kernel", "machine learning", "data engineer", 
    "data scientist", "openai", "ai-102", "dp-100", "dp-600", "vertex ai",
    "fabric", "deep learning", "langchain", "llamaindex"
]

SUBREDDIT_URLS = [
    "https://www.reddit.com/r/AzureCertification/search.json?q=voucher+OR+free+OR+challenge&restrict_sr=1&sort=new&limit=10",
    "https://www.reddit.com/r/googlecloud/search.json?q=free+voucher+OR+arcade&restrict_sr=1&sort=new&limit=10",
    "https://www.reddit.com/r/freecertifications/new.json?limit=10",
    "https://www.reddit.com/r/AWSCertifications/search.json?q=voucher+OR+free&restrict_sr=1&sort=new&limit=10"
]

TRIGGER_KEYWORDS = [
    "free voucher", "100% off", "cloud skills challenge", 
    "free exam", "discount code", "arcade points", "free certification"
]

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print("Telegram notification status:", resp.status_code)
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def check_official_certs():
    print("Checking Microsoft Learn API for official certifications...")
    url = "https://learn.microsoft.com/api/catalog/?type=certifications"
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
    except Exception as e:
        print(f"Error fetching MS certs: {e}")
        return

    known_uids = set()
    if os.path.exists(CERTS_CACHE_FILE):
        try:
            with open(CERTS_CACHE_FILE, "r") as f:
                known_uids = set(json.load(f))
        except Exception:
            known_uids = set()

    new_certs = []
    for cert in data.get("certifications", []):
        uid = cert.get("uid")
        title = cert.get("title", "")
        summary = cert.get("summary", "")
        combined = f"{title} {summary}".lower()

        if any(k in combined for k in KEYWORDS):
            if uid not in known_uids:
                new_certs.append({
                    "uid": uid,
                    "title": title,
                    "url": cert.get("url")
                })
                known_uids.add(uid)

    print(f"Found {len(new_certs)} new matching official certifications.")
    # Alert for up to 3 at a time so we don't spam on initial run
    for c in new_certs[:5]:
        msg = (
            f"🎓 *New AI / Data Science Cert Detected!*\n\n"
            f"📌 *Title:* {c['title']}\n"
            f"🔗 [View Official Page]({c['url']})"
        )
        send_telegram(msg)

    with open(CERTS_CACHE_FILE, "w") as f:
        json.dump(list(known_uids), f, indent=2)

def check_free_promotions():
    print("Hunting for free vouchers & promotional challenges...")
    headers = {"User-Agent": "CertPromotionRadar/1.0 (Mozilla/5.0)"}
    
    known_promos = set()
    if os.path.exists(PROMOS_CACHE_FILE):
        try:
            with open(PROMOS_CACHE_FILE, "r") as f:
                known_promos = set(json.load(f))
        except Exception:
            known_promos = set()

    for endpoint in SUBREDDIT_URLS:
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            posts = resp.json().get("data", {}).get("children", [])
            for p in posts:
                d = p.get("data", {})
                pid = d.get("id")
                title = d.get("title", "")
                body = d.get("selftext", "")
                text = f"{title} {body}".lower()

                if any(kw in text for kw in TRIGGER_KEYWORDS):
                    if pid not in known_promos:
                        msg = (
                            f"🚨 *FREE VOUCHER / PROMOTION DETECTED!* 🚨\n\n"
                            f"📢 *Deal:* {title}\n\n"
                            f"🔗 [Claim / View Reddit Post](https://reddit.com{d.get('permalink')})"
                        )
                        send_telegram(msg)
                        known_promos.add(pid)
        except Exception as e:
            print(f"Error checking promo endpoint {endpoint}: {e}")

    with open(PROMOS_CACHE_FILE, "w") as f:
        json.dump(list(known_promos), f, indent=2)

if __name__ == "__main__":
    check_official_certs()
    check_free_promotions()
    print("Done!")
