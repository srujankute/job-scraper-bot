import os
import json
import requests

# Get our secret keys from GitHub Settings
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# File to store jobs we already sent
TRACKING_FILE = "notified_jobs.json"

def send_telegram_message(message):
    """Sends a message to your Telegram chat"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_already_notified_jobs():
    """Loads the list of jobs we already sent from our json file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_notified_jobs(notified_set):
    """Saves the updated list of sent jobs to our json file"""
    with open(TRACKING_FILE, "w") as f:
        json.dump(list(notified_set), f, indent=4)

def scrape_greenhouse(board_token):
    """Scrapes Greenhouse boards used by E-commerce firms like Airbnb or Instacart"""
    jobs_found =
    # Greenhouse uses a public API that returns clean JSON data
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for job in data.get("jobs",):
                title = job.get("title", "").lower()
                # Check for entry-level data analyst keywords
                if "data analyst" in title or "analytics" in title:
                    jobs_found.append({
                        "id": str(job.get("id")),
                        "title": job.get("title"),
                        "company": board_token.capitalize(),
                        "url": job.get("absolute_url")
                    })
    except Exception as e:
        print(f"Greenhouse error for {board_token}: {e}")
    return jobs_found

def scrape_amazon():
    """Scrapes Amazon Jobs directly using their background JSON search API"""
    jobs_found =
    # Amazon uses a background JSON search endpoint
    url = "https://www.amazon.jobs/en/search.json?base_query=Data%20Analyst&result_limit=20"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for job in data.get("jobs",):
                title = job.get("title", "").lower()
                # Ensure it is a Data Analyst role and not senior or manager
                if "data analyst" in title and "senior" not in title and "manager" not in title:
                    jobs_found.append({
                        "id": str(job.get("id")),
                        "title": job.get("title"),
                        "company": "Amazon (FAANG)",
                        "url": "https://www.amazon.jobs" + job.get("job_path")
                    })
    except Exception as e:
        print(f"Amazon API error: {e}")
    return jobs_found

def main():
    print("Scraping started...")
    notified_jobs = get_already_notified_jobs()
    
    # We will search Amazon and E-commerce companies on Greenhouse (e.g. Airbnb, Stitchfix)
    all_jobs =
    all_jobs.extend(scrape_amazon())
    all_jobs.extend(scrape_greenhouse("airbnb"))
    all_jobs.extend(scrape_greenhouse("stitchfix"))

    new_jobs_count = 0
    for job in all_jobs:
        job_id = job["id"]
        # If we have not sent this job yet, send it now!
        if job_id not in notified_jobs:
            message = (
                f"🚨 *New Data Analyst Job Found!*\n\n"
                f"💼 *Role:* {job['title']}\n"
                f"🏢 *Company:* {job['company']}\n"
                f"🔗 [Apply Here]({job['url']})"
            )
            send_telegram_message(message)
            notified_jobs.add(job_id)
            new_jobs_count += 1
            
    # Save the new jobs list so we don't notify them again
    save_notified_jobs(notified_jobs)
    print(f"Done! Sent {new_jobs_count} new job alerts to Telegram.")

if __name__ == "__main__":
    main()
