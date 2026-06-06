import requests
import json
import os
import time
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
FILE_NAME = "sent_jobs.json"

JOB_SOURCES = {
    "Amazon": {
        "url": "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India",
        "parser": "amazon",
        "base_url": "https://amazon.jobs"
    },
    "Google": {
        "url": "https://www.google.com/careers/jobs/?location=India",
        "parser": "google_careers",
        "base_url": "https://google.com/careers/jobs"
    },
    "Meta": {
        "url": "https://www.metacareers.com/jobs/?experience_level=ENTRY_LEVEL&role=2409&location=APAC",
        "parser": "meta_careers",
        "base_url": "https://metacareers.com"
    },
    "Microsoft": {
        "url": "https://careers.microsoft.com/us/en/search-results?job_field=All",
        "parser": "microsoft_careers",
        "base_url": "https://careers.microsoft.com"
    },
    "Apple": {
        "url": "https://jobs.apple.com/en-us/search",
        "parser": "apple_careers",
        "base_url": "https://jobs.apple.com"
    },
    "LinkedIn": {
        "url": "https://careers.linkedin.com/jobs",
        "parser": "linkedin_careers",
        "base_url": "https://linkedin.com/jobs"
    },
    "Flipkart": {
        "url": "https://www.flipkartcareers.com/",
        "parser": "flipkart",
        "base_url": "https://flipkartcareers.com"
    },
    "Blinkit": {
        "url": "https://blinkit.com/careers",
        "parser": "blinkit",
        "base_url": "https://blinkit.com/careers"
    },
    "Zomato": {
        "url": "https://www.zomato.com/careers",
        "parser": "zomato",
        "base_url": "https://zomato.com/careers"
    },
    "Swiggy": {
        "url": "https://careers.swiggy.in/",
        "parser": "swiggy",
        "base_url": "https://careers.swiggy.in"
    },
    "Airbnb": {
        "url": "https://careers.airbnb.com/positions/",
        "parser": "airbnb",
        "base_url": "https://careers.airbnb.com"
    },
    "Uber": {
        "url": "https://www.uber.com/en-IN/careers/",
        "parser": "uber",
        "base_url": "https://uber.com/careers"
    },
    "PayTM": {
        "url": "https://www.paytm.com/careers",
        "parser": "paytm",
        "base_url": "https://paytm.com/careers"
    },
    "OYO": {
        "url": "https://www.oyorooms.com/careers",
        "parser": "oyo",
        "base_url": "https://oyorooms.com/careers"
    },
    "Shopify": {
        "url": "https://www.shopify.com/careers",
        "parser": "shopify",
        "base_url": "https://shopify.com/careers"
    }
}

def send_discord_message(message, max_retries=3):
    """Send message to Discord with retry logic for rate limiting"""
    payload = {'content': message}
    for attempt in range(max_retries):
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            print("✓ Message sent to Discord successfully")
            return True
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Discord API Error: {e}")
                raise e
        except Exception as e:
            print(f"Discord API Error: {e}")
            raise e
    
    print("Failed to send message after max retries")
    return False

def get_amazon_jobs():
    """Parse jobs from Amazon careers API"""
    try:
        url = JOB_SOURCES["Amazon"]["url"]
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            jobs = response.json().get('jobs', [])
            # Add company and posting date
            for job in jobs:
                job['company'] = 'Amazon'
                # Use current date as posting date if not available
                job['posted_date'] = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
            return jobs
    except Exception as e:
        print(f"Amazon scraper error: {e}")
    return []

def get_generic_jobs(company_name):
    """Generic job fetcher for companies without dedicated APIs"""
    try:
        source = JOB_SOURCES.get(company_name)
        if not source:
            return []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(source["url"], headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and 'jobs' in data:
                    jobs = data.get('jobs', [])
                    for job in jobs:
                        job['company'] = company_name
                        job['posted_date'] = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
                    return jobs
            except:
                print(f"No JSON data available for {company_name}. Consider adding custom parser.")
    except Exception as e:
        print(f"{company_name} scraper error: {e}")
    return []

def get_all_jobs():
    """Fetch jobs from all sources"""
    all_jobs = []
    
    print("🔍 Starting job scraping from all sources...")
    
    # Amazon (has dedicated API)
    amazon_jobs = get_amazon_jobs()
    all_jobs.extend(amazon_jobs)
    print(f"✓ Fetched {len(amazon_jobs)} jobs from Amazon")
    time.sleep(1)
    
    # Try other sources
    for company_name in JOB_SOURCES.keys():
        if company_name == "Amazon":
            continue
        
        jobs = get_generic_jobs(company_name)
        all_jobs.extend(jobs)
        print(f"✓ Fetched {len(jobs)} jobs from {company_name}")
        time.sleep(1)
    
    return all_jobs

def format_job_message(job):
    """Format job details for Discord message"""
    title = job.get('title', job.get('position', 'Unknown Title'))
    location = job.get('location', job.get('loc_query', 'Unknown Location'))
    company = job.get('company', 'Unknown Company')
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Try to construct job link
    job_path = job.get('job_path', job.get('path', ''))
    if company == "Amazon" and job_path:
        link = f"https://amazon.jobs{job_path}"
    else:
        link = JOB_SOURCES.get(company, {}).get('base_url', '#')
    
    message = f"""
🎯 **New Job Found**
📱 **Company:** {company}
💼 **Title:** {title}
📍 **Location:** {location}
🔗 **Link:** {link}
📅 **Posted:** {posted_date}
⏰ **Checked:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return message.strip()

def create_job_id(job):
    """Create unique job ID combining company, title, and date"""
    company = job.get('company', 'unknown')
    job_id = job.get('id', job.get('title', 'unknown'))
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    return f"{company}_{job_id}_{posted_date}"

def load_sent_jobs():
    """Load previously sent jobs"""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, 'r') as f:
            try:
                data = json.load(f)
                # Support both old format (list) and new format (dict with metadata)
                if isinstance(data, dict) and 'sent_jobs' in data:
                    return data
                else:
                    return {'sent_jobs': data, 'last_check': None}
            except json.JSONDecodeError:
                return {'sent_jobs': [], 'last_check': None}
    return {'sent_jobs': [], 'last_check': None}

def save_sent_jobs(sent_jobs_data):
    """Save sent jobs with metadata"""
    with open(FILE_NAME, 'w') as f:
        json.dump(sent_jobs_data, f, indent=2)

def clean_old_jobs(sent_jobs_data, days=7):
    """Remove jobs older than specified days to keep file size manageable"""
    today = datetime.now().strftime('%Y-%m-%d')
    today_date = datetime.strptime(today, '%Y-%m-%d')
    cutoff_date = today_date - timedelta(days=days)
    
    cleaned_jobs = []
    for job_id in sent_jobs_data['sent_jobs']:
        # Extract date from job_id (format: company_id_YYYY-MM-DD)
        try:
            date_str = job_id.split('_')[-1]
            job_date = datetime.strptime(date_str, '%Y-%m-%d')
            if job_date >= cutoff_date:
                cleaned_jobs.append(job_id)
        except:
            # Keep jobs we can't parse the date from
            cleaned_jobs.append(job_id)
    
    return cleaned_jobs

# Load History
sent_jobs_data = load_sent_jobs()
sent_jobs = sent_jobs_data.get('sent_jobs', [])
last_check = sent_jobs_data.get('last_check')

new_jobs = get_all_jobs()
jobs_found = []

print(f"\n📊 Fetched {len(new_jobs)} total jobs from all sources.")

today = datetime.now().strftime('%Y-%m-%d')

# Only process jobs posted today
today_jobs = [job for job in new_jobs if job.get('posted_date', today) == today]
print(f"📅 Jobs posted today: {len(today_jobs)}")

if len(today_jobs) == 0:
    print("✅ No new jobs posted today. Sending notification.")
    no_jobs_message = f"""
❌ **No Job Openings Today**
📅 **Date:** {today}
⏰ **Checked:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

No new job openings were found across all sources today. Better luck next time!
"""
    send_discord_message(no_jobs_message.strip())
else:
    for job in today_jobs:
        job_id = create_job_id(job)
        
        if job_id not in sent_jobs:
            message = format_job_message(job)
            
            if send_discord_message(message):
                sent_jobs.append(job_id)
                jobs_found.append(job_id)
            
            # Add delay between messages to avoid rate limiting
            time.sleep(1)

# Clean old jobs (keep only last 7 days)
sent_jobs = clean_old_jobs({'sent_jobs': sent_jobs}, days=7)

# Save history with metadata
sent_jobs_data = {
    'sent_jobs': sent_jobs,
    'last_check': datetime.now().isoformat()
}
save_sent_jobs(sent_jobs_data)

print(f"\n✅ Scraper finished. Successfully sent {len(jobs_found)} new job alerts.")
print(f"📈 Total unique jobs tracked (last 7 days): {len(sent_jobs)}")
