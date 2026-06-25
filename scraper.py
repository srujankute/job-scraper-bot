import requests
import json
import os
import time
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
FILE_NAME = "sent_jobs.json"

# Job source URLs with working APIs and scraping endpoints
JOB_SOURCES = {
    "Amazon": {
        "url": "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India",
        "parser": "amazon_api",
        "base_url": "https://amazon.jobs"
    },
    "Indeed": {
        "url": "https://www.indeed.com/jobs?q=data+analyst&l=India",
        "parser": "indeed_html",
        "base_url": "https://www.indeed.com/jobs"
    },
    "Glassdoor": {
        "url": "https://www.glassdoor.co.in/Job/data-analyst-jobs-SRCH_KO0,12.htm",
        "parser": "glassdoor_html",
        "base_url": "https://www.glassdoor.co.in"
    }
}

# Role/Title related keywords
ROLE_KEYWORDS = [
    r"\bdata\s*analyst\b",
    r"\bbusiness\s*analyst\b",
    r"\banalyst\b",
    r"\bdata\s*science\b",
    r"\bdata\s*analysis\b",
    r"\bdata\s*analytics\b",
    r"\banalytics\b",
    r"\bsql\s*analyst\b",
]

# Job description keywords
JD_KEYWORDS = [
    r"data\s*model(ing)?",
    r"data\s*analysis",
    r"insight(s)?",
    r"power\s*bi",
    r"sas(\b|\s)",
    r"tableau",
    r"sql\b",
    r"python\b",
    r"r\b",
    r"data\s*visuali(s|z)ation",
    r"reporting",
    r"etl\b",
    r"business\s*intelligence|bi\b",
    r"excel\b",
    r"dashboard",
]

ROLE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ROLE_KEYWORDS]
JD_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JD_KEYWORDS]

COMPANY_ALIASES = {
    "amazon": "Amazon",
    "google": "Google",
    "netflix": "Netflix",
    "apple": "Apple",
    "hsbc": "HSBC",
    "goldman sachs": "Goldman Sachs",
    "goldman": "Goldman Sachs",
    "jp morgan": "JP Morgan",
    "jpmorgan": "JP Morgan",
    "morgan stanley": "Morgan Stanley",
    "hdfc": "HDFC",
    "deloitte": "Deloitte",
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "tcs": "TCS",
    "ey": "EY",
    "mastercard": "Mastercard",
    "citi": "Citi",
    "citigroup": "Citi",
    "meta": "Meta",
    "facebook": "Meta",
    "zs associates": "ZS Associates",
    "zs": "ZS Associates",
    "zomato": "Zomato",
    "swiggy": "Swiggy",
    "blinkit": "Blinkit",
    "microsoft": "Microsoft",
    "indeed": "Indeed",
    "glassdoor": "Glassdoor",
}

COMPANY_PATTERNS = [(re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v) for k, v in COMPANY_ALIASES.items()]


def send_discord_message(message, max_retries=3):
    """Send message to Discord with retry logic"""
    if not DISCORD_WEBHOOK_URL:
        print("No DISCORD_WEBHOOK_URL configured; skipping Discord send.")
        return False
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
        except Exception as e:
            print(f"Discord API Error: {e}")
    
    return False


def get_amazon_jobs():
    """Parse jobs from Amazon careers API"""
    try:
        url = JOB_SOURCES["Amazon"]["url"]
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            jobs = response.json().get('jobs', [])
            for job in jobs:
                job['company'] = 'Amazon'
                job['posted_date'] = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
            print(f"✓ Fetched {len(jobs)} jobs from Amazon API")
            return jobs
    except Exception as e:
        print(f"Amazon scraper error: {e}")
    return []


def get_indeed_jobs():
    """Scrape jobs from Indeed"""
    try:
        url = JOB_SOURCES["Indeed"]["url"]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            jobs = []
            job_cards = soup.find_all('div', {'data-tn-component': 'structuredJobSearchResult'})
            
            for card in job_cards[:15]:
                try:
                    title_elem = card.find('h2', class_='jobTitle')
                    company_elem = card.find('span', {'data-testid': 'company-name'})
                    location_elem = card.find('div', {'data-testid': 'job-location'})
                    link_elem = card.find('a', {'data-testid': 'job-item-summary'})
                    
                    if title_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else 'Indeed',
                            'location': location_elem.get_text(strip=True) if location_elem else 'India',
                            'url': link_elem['href'] if link_elem and link_elem.get('href') else url,
                            'posted_date': datetime.now().strftime('%Y-%m-%d'),
                            'description': ''
                        }
                        jobs.append(job)
                except Exception:
                    continue
            
            print(f"✓ Fetched {len(jobs)} jobs from Indeed")
            return jobs
    except Exception as e:
        print(f"Indeed scraper error: {e}")
    return []


def get_glassdoor_jobs():
    """Scrape jobs from Glassdoor"""
    try:
        url = JOB_SOURCES["Glassdoor"]["url"]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            jobs = []
            job_cards = soup.find_all('div', {'data-test': 'JobCard'})
            
            for card in job_cards[:15]:
                try:
                    title_elem = card.find('a', {'data-test': 'job-title'})
                    company_elem = card.find('a', {'data-test': 'employer-name'})
                    location_elem = card.find('div', {'data-test': 'job-location'})
                    
                    if title_elem:
                        job = {
                            'title': title_elem.get_text(strip=True),
                            'company': company_elem.get_text(strip=True) if company_elem else 'Glassdoor',
                            'location': location_elem.get_text(strip=True) if location_elem else 'India',
                            'url': title_elem.get('href') if title_elem.get('href') else url,
                            'posted_date': datetime.now().strftime('%Y-%m-%d'),
                            'description': ''
                        }
                        jobs.append(job)
                except Exception:
                    continue
            
            print(f"✓ Fetched {len(jobs)} jobs from Glassdoor")
            return jobs
    except Exception as e:
        print(f"Glassdoor scraper error: {e}")
    return []


def get_all_jobs():
    """Fetch jobs from all sources"""
    all_jobs = []
    print("🔍 Starting job scraping from all sources...\n")
    
    amazon_jobs = get_amazon_jobs()
    all_jobs.extend(amazon_jobs)
    time.sleep(1)
    
    indeed_jobs = get_indeed_jobs()
    all_jobs.extend(indeed_jobs)
    time.sleep(1)
    
    glassdoor_jobs = get_glassdoor_jobs()
    all_jobs.extend(glassdoor_jobs)
    time.sleep(1)
    
    return all_jobs


def normalize_text(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def detect_company_in_text(text):
    """Return canonical company name if any alias matched"""
    for pattern, canonical in COMPANY_PATTERNS:
        if pattern.search(text):
            return canonical
    return None


def job_matches(job):
    """Check if job matches our criteria"""
    title = normalize_text(job.get('title') or job.get('position') or '')
    desc = normalize_text(job.get('description') or job.get('summary') or job.get('requirements') or '')
    combined = f"{title} {desc}"

    role_match = any(p.search(combined) for p in ROLE_PATTERNS)
    jd_match = any(p.search(combined) for p in JD_PATTERNS)

    company_field = normalize_text(job.get('company', ''))
    company_match = None
    if company_field:
        company_match = detect_company_in_text(company_field)
    if not company_match:
        company_match = detect_company_in_text(combined)

    if role_match:
        if company_match:
            job['company'] = company_match
        return True

    return False


def parse_posted_date(date_str):
    """Parse posted date"""
    if not date_str:
        return datetime.now().date()
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
    for f in formats:
        try:
            return datetime.strptime(date_str.strip(), f).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(date_str).date()
    except Exception:
        return datetime.now().date()


def format_job_message(job):
    """Format job for Discord"""
    title = job.get('title', job.get('position', 'Unknown Title'))
    location = job.get('location', job.get('loc_query', 'India'))
    company = job.get('company', 'Unknown Company')
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    
    job_path = job.get('job_path', job.get('path', ''))
    if company == "Amazon" and job_path:
        link = f"https://amazon.jobs{job_path}"
    else:
        link = job.get('url', JOB_SOURCES.get(company, {}).get('base_url', '#'))
    
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
    title = job.get('title', job.get('position', 'Unknown Title'))
    company = job.get('company', 'Unknown Company')
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    link = job.get('url', JOB_SOURCES.get(company, {}).get('base_url', '#'))
    return f"- {posted_date} | {company} | {title} | {link}"


def create_job_id(job):
    """Create unique job ID"""
    company = job.get('company', 'unknown')
    job_id = str(job.get('id', job.get('title', 'unknown'))).replace(' ', '_')[:50]
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
sent_jobs_data = load_sent_jobs()
sent_jobs = sent_jobs_data.get('sent_jobs', [])
last_check = sent_jobs_data.get('last_check')

new_jobs = get_all_jobs()
jobs_found = []

print(f"\n📊 Fetched {len(new_jobs)} total jobs from all sources.")

matched_jobs = [job for job in new_jobs if job_matches(job)]
print(f"🔎 Jobs matching requested keywords: {len(matched_jobs)}")

for job in matched_jobs:
    job['posted_date'] = job.get('posted_date') or datetime.now().strftime('%Y-%m-%d')
    try:
        parsed = parse_posted_date(str(job['posted_date']))
        job['_parsed_date'] = parsed
        job['posted_date'] = parsed.strftime('%Y-%m-%d')
    except Exception:
        job['_parsed_date'] = datetime.now().date()
        job['posted_date'] = datetime.now().strftime('%Y-%m-%d')

matched_jobs.sort(key=lambda j: j.get('_parsed_date', datetime.now().date()), reverse=True)

if matched_jobs:
    summary_lines = [f"🔔 Job Listings — total: {len(matched_jobs)}\n"]
    for job in matched_jobs[:20]:
        summary_lines.append(format_job_short_line(job))
    if len(matched_jobs) > 20:
        summary_lines.append(f"\n... and {len(matched_jobs) - 20} more jobs")
    summary_message = "\n".join(summary_lines)
    send_discord_message(summary_message)
    time.sleep(1)
else:
    print("No matched jobs to list in summary.")
    send_discord_message("🔍 No matching data analyst jobs found in this search cycle.")

for job in matched_jobs[:10]:
    job_id = create_job_id(job)
    message = format_job_message(job)
    if send_discord_message(message):
        jobs_found.append(job_id)
        sent_jobs.append(job_id)
    time.sleep(1)

sent_jobs = clean_old_jobs({'sent_jobs': sent_jobs}, days=7)

sent_jobs_data = {
    'sent_jobs': sent_jobs,
    'last_check': datetime.now().isoformat()
}
save_sent_jobs(sent_jobs_data)

print(f"\n✅ Scraper finished. Successfully sent {len(jobs_found)} job alerts.")
print(f"📈 Total unique jobs tracked (last 7 days): {len(sent_jobs)}")
