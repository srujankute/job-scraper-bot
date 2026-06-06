import requests
import json
import os

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
URL = "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India"
FILE_NAME = "sent_jobs.json"

def send_discord_message(message):
    payload = {'content': message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print("✓ Message sent to Discord successfully")
    except Exception as e:
        print(f"Discord API Error: {e}")
        raise e

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
        
        message = f"🎯 **New Job Found**\n**Title:** {title}\n**Location:** {location}\n**Link:** https://amazon.jobs{path}"
        
        send_discord_message(message)
        
        sent_jobs.append(job_id)
        jobs_found.append(job_id)

# Save history only if everything succeeded
with open(FILE_NAME, 'w') as f:
    json.dump(sent_jobs, f)

print(f"Scraper finished. Successfully sent {len(jobs_found)} new job alerts.")
