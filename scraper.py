import requests
import json
import os

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
URL = "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=payload)

def get_jobs():
    response = requests.get(URL)
    if response.status_code == 200:
        return response.json().get('jobs', [])
    return []

if os.path.exists('sent_jobs.json'):
    with open('sent_jobs.json', 'r') as f:
        sent_jobs = json.load(f)
else:
    sent_jobs = []

new_jobs = get_jobs()
jobs_found = [] # This is what was missing on your line 43

for job in new_jobs:
    job_id = str(job['id'])
    if job_id not in sent_jobs:
        message = f"New Job Found: {job['title']}\nLocation: {job['location']}\nLink: https://amazon.jobs{job['job_path']}"
        send_telegram_message(message)
        sent_jobs.append(job_id)
        jobs_found.append(job_id)

with open('sent_jobs.json', 'w') as f:
    json.dump(sent_jobs, f)

print(f"Scraper finished. Found {len(jobs_found)} new jobs.")
