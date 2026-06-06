import requests
import json
import os

# 1. Fetch Secrets
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India"
FILE_NAME = "sent_jobs.json"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram API Error: {e}")

def get_jobs():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            return response.json().get('jobs', [])
    except Exception as e:
        print(f"Scraper Error: {e}")
    return []

# 2. Load History Safely
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, 'r') as f:
        try:
            sent_jobs = json.load(f)
        except json.JSONDecodeError:
            sent_jobs = []
else:
    sent_jobs = []

# 3. Process Jobs
new_jobs = get_jobs()
jobs_found = []

for job in new_jobs:
    job_id = str(job.get('id', ''))
    if not job_id:
        continue
        
    if job_id not in sent_jobs:
        title = job.get('title', 'Unknown Title')
        location = job.get('location', 'Unknown Location')
        path = job.get('job_path', '')
        
        message = f"New Job Found: {title}\nLocation: {location}\nLink: https://amazon.jobs{path}"
        send_telegram_message(message)
        
        sent_jobs.append(job_id)
        jobs_found.append(job_id)

# 4. Save State
with open(FILE_NAME, 'w') as f:
    json.dump(sent_jobs, f)

print(f"Scraper finished. Found {len(jobs_found)} new jobs.")
