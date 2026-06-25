import requests
import json
import os
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
FILE_NAME = "sent_jobs.json"

# Job source APIs - Focus on India and Remote jobs
JOB_SOURCES = {
    "Amazon": {
        "url": "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India",
        "parser": "amazon_api",
        "base_url": "https://amazon.jobs"
    },
    "LinkedIn": {
        "url": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting?jobId=",
        "parser": "linkedin",
        "base_url": "https://www.linkedin.com/jobs/search"
    },
    "RemoteOK": {
        "url": "https://remoteok.com/api/jobs?tag=data+analyst,remote,india&limit=50",
        "parser": "remoteok_api",
        "base_url": "https://remoteok.com"
    }
}

# Role/Title keywords - More specific for Data Analysts
ROLE_KEYWORDS = [
    r"\bdata\s*analyst\b",
    r"\bsenior\s*data\s*analyst\b",
    r"\bjunior\s*data\s*analyst\b",
    r"\bbusiness\s*analyst\b",
    r"\bdata\s*analyst\s*-",
    r"\banalytics\s*engineer\b",
]

# Job description keywords
JD_KEYWORDS = [
    r"data\s*analysis",
    r"sql",
    r"python",
    r"tableau",
    r"power\s*bi",
    r"dashboard",
    r"business\s*intelligence",
    r"reporting",
    r"etl",
    r"excel",
]

# Location keywords to ensure India or Remote
LOCATION_KEYWORDS = [
    r"\bindia\b",
    r"\bremote\b",
    r"\bwork\s*from\s*home\b",
    r"\bwfh\b",
    r"\bbangalore\b",
    r"\bdelhi\b",
    r"\bmumbai\b",
    r"\bhyderabad\b",
    r"\bpune\b",
    r"\bchenai\b",
    r"\bgurgaon\b",
    r"\bnoida\b",
]

ROLE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ROLE_KEYWORDS]
JD_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JD_KEYWORDS]
LOCATION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in LOCATION_KEYWORDS]

COMPANY_ALIASES = {
    "amazon": "Amazon",
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "meta": "Meta",
    "netflix": "Netflix",
    "uber": "Uber",
    "airbnb": "Airbnb",
    "linkedin": "LinkedIn",
    "adobe": "Adobe",
    "salesforce": "Salesforce",
    "databricks": "Databricks",
    "stripe": "Stripe",
    "notion": "Notion",
    "figma": "Figma",
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "cognizant": "Cognizant",
    "infosys": "Infosys",
    "tcs": "TCS",
    "wipro": "Wipro",
    "hcl": "HCL",
    "mindtree": "Mindtree",
    "deloitte": "Deloitte",
    "ey": "EY",
    "pwc": "PwC",
    "kpmg": "KPMG",
    "citi": "Citi",
    "hsbc": "HSBC",
    "goldman sachs": "Goldman Sachs",
    "jp morgan": "JP Morgan",
    "morgan stanley": "Morgan Stanley",
    "mastercard": "Mastercard",
    "visa": "Visa",
    "paypal": "PayPal",
    "flipkart": "Flipkart",
    "amazon india": "Amazon",
    "microsoft india": "Microsoft",
    "google india": "Google",
}

COMPANY_PATTERNS = [(re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v) for k, v in COMPANY_ALIASES.items()]


def send_discord_message(message, max_retries=3):
    """Send message to Discord with retry logic"""
    if not DISCORD_WEBHOOK_URL:
        print("No DISCORD_WEBHOOK_URL configured; skipping Discord send.")
        return False
    
    # Split long messages if needed
    if len(message) > 2000:
        messages = [message[i:i+1990] for i in range(0, len(message), 1990)]
    else:
        messages = [message]
    
    for msg in messages:
        payload = {'content': msg}
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
            except Exception as e:
                print(f"Discord API Error: {e}")
        
        time.sleep(0.5)
    
    return False


def get_amazon_jobs():
    """Parse jobs from Amazon careers API"""
    try:
        url = JOB_SOURCES["Amazon"]["url"]
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            jobs = response.json().get('jobs', [])
            result_jobs = []
            for job in jobs:
                # Filter for India location
                location = job.get('location', '').lower()
                if 'india' in location or 'remote' in location.lower():
                    job['company'] = 'Amazon'
                    job['posted_date'] = job.get('posting_date', datetime.now().strftime('%Y-%m-%d'))
                    job['description'] = job.get('description_short', '')
                    result_jobs.append(job)
            print(f"✓ Fetched {len(result_jobs)} jobs from Amazon (India/Remote)")
            return result_jobs
    except Exception as e:
        print(f"Amazon scraper error: {e}")
    return []


def get_remoteok_jobs():
    """Get jobs from RemoteOK API"""
    try:
        url = "https://remoteok.com/api/jobs?tag=data&limit=50"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            jobs_data = response.json()
            result_jobs = []
            
            for job in jobs_data[:50]:
                # Filter for India or Remote
                title = job.get('title', '').lower()
                location = job.get('location', '').lower()
                tags = ' '.join(job.get('tags', [])).lower()
                
                if 'india' in location or 'remote' in location or 'remote' in tags or 'india' in tags:
                    result_job = {
                        'title': job.get('title', ''),
                        'company': job.get('company', 'RemoteOK'),
                        'location': job.get('location', 'Remote'),
                        'url': job.get('url', 'https://remoteok.com'),
                        'posted_date': datetime.now().strftime('%Y-%m-%d'),
                        'description': job.get('description', ''),
                        'id': job.get('id', '')
                    }
                    result_jobs.append(result_job)
            
            print(f"✓ Fetched {len(result_jobs)} jobs from RemoteOK (India/Remote)")
            return result_jobs
    except Exception as e:
        print(f"RemoteOK scraper error: {e}")
    return []


def get_linkedin_jobs_simple():
    """Simple LinkedIn job fetch - returns limited results"""
    try:
        # Using unofficial LinkedIn API approach
        search_terms = "data%20analyst%20india%20remote"
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting?keywords={search_terms}&location=India&pageNum=0&start=0"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        # LinkedIn heavily restricts scraping; this typically returns limited data
        print("✓ LinkedIn fetch attempted (limited results expected)")
        return []
    except Exception as e:
        print(f"LinkedIn scraper error: {e}")
    return []


def get_all_jobs():
    """Fetch jobs from all sources"""
    all_jobs = []
    print("🔍 Starting job scraping from all sources...\n")
    
    # Amazon
    amazon_jobs = get_amazon_jobs()
    all_jobs.extend(amazon_jobs)
    time.sleep(1)
    
    # RemoteOK
    remoteok_jobs = get_remoteok_jobs()
    all_jobs.extend(remoteok_jobs)
    time.sleep(1)
    
    # LinkedIn (limited)
    linkedin_jobs = get_linkedin_jobs_simple()
    all_jobs.extend(linkedin_jobs)
    time.sleep(1)
    
    return all_jobs


def normalize_text(s):
    """Normalize text for matching"""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def detect_company_in_text(text):
    """Return canonical company name if any alias matched"""
    for pattern, canonical in COMPANY_PATTERNS:
        if pattern.search(text):
            return canonical
    return None


def check_location_match(job):
    """Check if job is in India or Remote"""
    location = normalize_text(job.get('location', ''))
    title = normalize_text(job.get('title', ''))
    desc = normalize_text(job.get('description', ''))
    
    combined = f"{location} {title} {desc}"
    
    # Must have India or Remote
    return any(p.search(combined) for p in LOCATION_PATTERNS)


def job_matches(job):
    """Check if job matches our criteria"""
    title = normalize_text(job.get('title') or '')
    desc = normalize_text(job.get('description') or '')
    combined = f"{title} {desc}"

    # Must have analyst role
    role_match = any(p.search(combined) for p in ROLE_PATTERNS)
    
    # Should have data-related keywords
    jd_match = any(p.search(combined) for p in JD_PATTERNS)
    
    # Must be in India or Remote
    location_match = check_location_match(job)

    # Accept if: analyst + location
    if role_match and location_match:
        return True
    
    # Also accept: analyst + jd keywords + location (even without explicit analyst in title)
    if location_match and jd_match:
        # Check if it has analyst-like role
        if re.search(r'\b(analyst|analytics|engineer|specialist|developer)\b', combined):
            return True

    return False


def parse_posted_date(date_str):
    """Parse posted date"""
    if not date_str:
        return datetime.now().date()
    
    # Try common formats
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%Y%m%d']
    for f in formats:
        try:
            return datetime.strptime(date_str.strip()[:10], f).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(date_str[:10]).date()
    except Exception:
        return datetime.now().date()


def format_job_message(job):
    """Format job for Discord"""
    title = job.get('title', 'Unknown Title')
    location = job.get('location', 'Remote/India')
    company = job.get('company', 'Unknown Company')
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    
    link = job.get('url', '#')
    if company == "Amazon" and job.get('job_path'):
        link = f"https://amazon.jobs{job.get('job_path')}"
    
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


def format_job_short_line(job):
    """Format job for summary"""
    title = job.get('title', 'Unknown Title')[:50]
    company = job.get('company', 'Unknown')[:20]
    location = job.get('location', 'Remote')[:20]
    link = job.get('url', '#')
    return f"• {company:20} | {title:50} | {location:20}"


def create_job_id(job):
    """Create unique job ID"""
    company = job.get('company', 'unknown')
    job_title = str(job.get('title', 'unknown')).replace(' ', '_')[:40]
    job_id = job.get('id', job_title)
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    return f"{company}_{job_id}_{posted_date}"


def load_sent_jobs():
    """Load previously sent jobs"""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, 'r') as f:
            try:
                data = json.load(f)
                if isinstance(data, dict) and 'sent_jobs' in data:
                    return data
                else:
                    return {'sent_jobs': data, 'last_check': None}
            except json.JSONDecodeError:
                return {'sent_jobs': [], 'last_check': None}
    return {'sent_jobs': [], 'last_check': None}


def save_sent_jobs(sent_jobs_data):
    """Save sent jobs"""
    with open(FILE_NAME, 'w') as f:
        json.dump(sent_jobs_data, f, indent=2)


def clean_old_jobs(sent_jobs_data, days=7):
    """Remove jobs older than specified days"""
    today = datetime.now().strftime('%Y-%m-%d')
    today_date = datetime.strptime(today, '%Y-%m-%d')
    cutoff_date = today_date - timedelta(days=days)
    
    cleaned_jobs = []
    for job_id in sent_jobs_data['sent_jobs']:
        try:
            date_str = job_id.split('_')[-1]
            job_date = datetime.strptime(date_str, '%Y-%m-%d')
            if job_date >= cutoff_date:
                cleaned_jobs.append(job_id)
        except Exception:
            cleaned_jobs.append(job_id)
    
    return cleaned_jobs


# Main execution
print("=" * 60)
print("🤖 JOB SCRAPER BOT - DATA ANALYST JOBS (INDIA & REMOTE)")
print("=" * 60)

sent_jobs_data = load_sent_jobs()
sent_jobs = sent_jobs_data.get('sent_jobs', [])
last_check = sent_jobs_data.get('last_check')

if last_check:
    print(f"📅 Last check: {last_check}")

new_jobs = get_all_jobs()
jobs_found = []

print(f"\n📊 Fetched {len(new_jobs)} total jobs from all sources.")

# Filter jobs
matched_jobs = [job for job in new_jobs if job_matches(job)]
print(f"🔎 Jobs matching criteria (Data Analyst + India/Remote): {len(matched_jobs)}")

# Parse dates
for job in matched_jobs:
    job['posted_date'] = job.get('posted_date') or datetime.now().strftime('%Y-%m-%d')
    try:
        parsed = parse_posted_date(str(job['posted_date']))
        job['_parsed_date'] = parsed
        job['posted_date'] = parsed.strftime('%Y-%m-%d')
    except Exception:
        job['_parsed_date'] = datetime.now().date()
        job['posted_date'] = datetime.now().strftime('%Y-%m-%d')

# Remove duplicates by job_id
unique_jobs = {}
for job in matched_jobs:
    job_id = create_job_id(job)
    if job_id not in unique_jobs:
        unique_jobs[job_id] = job

matched_jobs = list(unique_jobs.values())
matched_jobs.sort(key=lambda j: j.get('_parsed_date', datetime.now().date()), reverse=True)

print(f"✨ Unique jobs after dedup: {len(matched_jobs)}")

# Send summary
if matched_jobs:
    summary_lines = [
        "=" * 60,
        f"🔔 **DATA ANALYST JOBS - INDIA & REMOTE**",
        f"📊 Total: {len(matched_jobs)} positions",
        "=" * 60,
        ""
    ]
    
    for i, job in enumerate(matched_jobs[:15], 1):
        summary_lines.append(format_job_short_line(job))
    
    if len(matched_jobs) > 15:
        summary_lines.append(f"\n... and {len(matched_jobs) - 15} more jobs")
    
    summary_message = "\n".join(summary_lines)
    send_discord_message(summary_message)
    time.sleep(1)
else:
    print("❌ No matching jobs found")
    send_discord_message("🔍 No matching data analyst jobs found in India or Remote positions for this search cycle.")

# Send individual alerts for new jobs
new_jobs_count = 0
for job in matched_jobs[:15]:  # Limit to top 15
    job_id = create_job_id(job)
    
    # Check if already sent
    if job_id not in sent_jobs:
        message = format_job_message(job)
        if send_discord_message(message):
            jobs_found.append(job_id)
            sent_jobs.append(job_id)
            new_jobs_count += 1
        time.sleep(0.5)

# Save
sent_jobs = clean_old_jobs({'sent_jobs': sent_jobs}, days=7)
sent_jobs_data = {
    'sent_jobs': sent_jobs,
    'last_check': datetime.now().isoformat()
}
save_sent_jobs(sent_jobs_data)

print(f"\n✅ Scraper finished!")
print(f"🆕 New jobs sent: {new_jobs_count}")
print(f"📈 Total tracked (last 7 days): {len(sent_jobs)}")
print("=" * 60)
