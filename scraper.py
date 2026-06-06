import requests
import json
import os

# We changed this to matching TELEGRAM_TOKEN
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India"
FILE_NAME = "sent_jobs.json"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        response = requests.post(url, data=payload, timeout=10)
        # This line forces Python to crash if the Telegram token or Chat ID is wrong
        response.raise_for_status() 
    except Exception as e:
        print(f"Telegram API Error: {e}")
        raise e  # Stops the script so GitHub Actions shows a red error if it fails

def get_jobs():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            return response.json().get('jobs', [])
    except Exception as e:
        print(f"Scraper Error: {e}")
    return []

# Load History
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, 'r') as f:
        try:
            sent_jobs = json.load(f)
        except json.JSONDecodeError:
            sent_jobs = []
else:
    sent_jobs = []

new_jobs = get_jobs()
jobs_found = []

print(f"Fetched {len(new_jobs)} jobs from Amazon Careers.")

for job in new_jobs:
    job_id = str(job.get('id', ''))
    if not job_id:
        continue
        
    if job_id not in sent_jobs:
        title = job.get('title', 'Unknown Title')
        location = job.get('location', 'Unknown Location')
        path = job.get('job_path', '')
        
        message = f"New Job Found: {title}\nLocation: {location}\nLink: https://amazon.jobs{path}"
        
        # This will only add the job to sent_jobs.json if Telegram successfully delivers it
        send_telegram_message(message)
        
        sent_jobs.append(job_id)
        jobs_found.append(job_id)

# Save history only if everything succeeded
with open(FILE_NAME, 'w') as f:
    json.dump(sent_jobs, f)

print(f"Scraper finished. Successfully sent {len(jobs_found)} new job alerts.")
