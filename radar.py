import os
import json
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9246640626:AAFY90tZ5rhKxfZaWFmhh97ykvD9oFh3pFM")
# Can be a single ID or comma-separated list of IDs: "904278297, 555123456"
RAW_CHAT_IDS = os.getenv("TELEGRAM_CHAT_ID", "904278297")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in RAW_CHAT_IDS.split(",") if cid.strip()]

CERTS_CACHE_FILE = "known_certs.json"
PROMOS_CACHE_FILE = "known_promos.json"

KEYWORDS = [
    "agent", "semantic kernel", "machine learning", "data engineer", 
    "data scientist", "openai", "ai-102", "ai-500", "dp-100", "dp-600", "dp-700",
    "vertex ai", "fabric", "deep learning", "langchain", "llamaindex"
]

SUBREDDIT_URLS = [
    "https://www.reddit.com/r/AzureCertification/search.json?q=voucher+OR+free+OR+challenge+OR+fest&restrict_sr=1&sort=new&limit=15",
    "https://www.reddit.com/r/googlecloud/search.json?q=free+voucher+OR+arcade+OR+innovators&restrict_sr=1&sort=new&limit=15",
    "https://www.reddit.com/r/freecertifications/new.json?limit=15",
    "https://www.reddit.com/r/AWSCertifications/search.json?q=voucher+OR+free+OR+discount&restrict_sr=1&sort=new&limit=15",
    "https://www.reddit.com/r/devops/search.json?q=free+certification+OR+voucher&restrict_sr=1&sort=new&limit=10"
]

GITHUB_TRACKERS = [
    "https://api.github.com/repos/nisalgunawardhana/microsoft-certification-voucher-offers/commits?per_page=5"
]

TRIGGER_KEYWORDS = [
    "free voucher", "100% off", "cloud skills challenge", 
    "free exam", "discount code", "arcade points", "free certification",
    "ai fest", "ai tour", "microsoft build", "microsoft ignite",
    "free voucher code", "exam voucher", "100% discount", "voucher drop",
    "levelup", "partner certification week", "emerging talent", "student pack"
]

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Broadcast message to all registered chat IDs
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            print(f"Delivered to {chat_id}: status {resp.status_code}")
        except Exception as e:
            print(f"Error sending to {chat_id}: {e}")

def check_official_certs():
    print("Checking Microsoft Learn API for active certifications...")
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
        if cert.get("is_retired", False):
            continue

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
    for c in new_certs[:5]:
        msg = (
            f"🎓 *Active AI / Data Science Cert Detected!*\n\n"
            f"📌 *Title:* {c['title']}\n"
            f"🔗 [View Official Page]({c['url']})"
        )
        send_telegram(msg)

    with open(CERTS_CACHE_FILE, "w") as f:
        json.dump(list(known_uids), f, indent=2)

def check_community_and_trackers():
    print("Hunting for free vouchers across Reddit & GitHub Trackers...")
    headers = {"User-Agent": "CertPromotionRadar/2.0 (Mozilla/5.0)"}
    
    known_promos = set()
    if os.path.exists(PROMOS_CACHE_FILE):
        try:
            with open(PROMOS_CACHE_FILE, "r") as f:
                known_promos = set(json.load(f))
        except Exception:
            known_promos = set()

    # Check Subreddits
    for endpoint in SUBREDDIT_URLS:
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            posts = resp.json().get("data", {}).get("children", [])
            for p in posts:
                d = p.get("data", {})
                pid = str(d.get("id"))
                title = d.get("title", "")
                body = d.get("selftext", "")
                text = f"{title} {body}".lower()

                if any(kw in text for kw in TRIGGER_KEYWORDS):
                    if pid not in known_promos:
                        msg = (
                            f"🚨 *FREE VOUCHER / EVENT PROMO DETECTED!* 🚨\n\n"
                            f"📢 *Event/Deal:* {title}\n\n"
                            f"🔗 [Claim / View Details](https://reddit.com{d.get('permalink')})"
                        )
                        send_telegram(msg)
                        known_promos.add(pid)
        except Exception as e:
            print(f"Error checking promo endpoint {endpoint}: {e}")

    # Check GitHub Voucher Repositories (nisalgunawardhana tracker)
    for gh_url in GITHUB_TRACKERS:
        try:
            gh_resp = requests.get(gh_url, headers=headers, timeout=15)
            if gh_resp.status_code == 200:
                commits = gh_resp.json()
                for commit in commits:
                    sha = commit.get("sha", "")[:8]
                    commit_msg = commit.get("commit", {}).get("message", "")
                    if sha not in known_promos:
                        if any(kw in commit_msg.lower() for kw in ["add", "update", "voucher", "free", "fest", "challenge"]):
                            telegram_msg = (
                                f"🔥 *GitHub Voucher Tracker Updated!*\n\n"
                                f"📝 *Update:* {commit_msg}\n\n"
                                f"🔗 [View Repository Offer Page](https://github.com/nisalgunawardhana/microsoft-certification-voucher-offers)"
                            )
                            send_telegram(telegram_msg)
                        known_promos.add(sha)
        except Exception as e:
            print(f"Error checking GitHub tracker: {e}")

    with open(PROMOS_CACHE_FILE, "w") as f:
        json.dump(list(known_promos), f, indent=2)

if __name__ == "__main__":
    check_official_certs()
    check_community_and_trackers()
    print("Run completed successfully.")
