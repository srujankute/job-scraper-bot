import requests
import json
import os
import time
import re
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
FILE_NAME = "sent_jobs.json"

# Job source URLs (best-effort). Parsers for many sites are "generic" and may need
# custom parsers for structured JSON. We keep existing sources and add common
# career pages for the requested companies so the scraper can attempt to fetch them.
JOB_SOURCES = {
    "Amazon": {
        "url": "https://www.amazon.jobs/en/search.json?base_query=Data+Analyst&loc_query=India",
        "parser": "amazon",
        "base_url": "https://amazon.jobs"
    },
    "Google": {
        "url": "https://careers.google.com/jobs/results/?location=India",
        "parser": "google_careers",
        "base_url": "https://careers.google.com"
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
    "Netflix": {
        "url": "https://jobs.netflix.com/",
        "parser": "netflix",
        "base_url": "https://jobs.netflix.com"
    },
    "HSBC": {
        "url": "https://www.hsbc.com/careers/",
        "parser": "hsbc",
        "base_url": "https://www.hsbc.com/careers"
    },
    "Goldman Sachs": {
        "url": "https://www.goldmansachs.com/careers/",
        "parser": "goldman",
        "base_url": "https://www.goldmansachs.com/careers"
    },
    "JP Morgan": {
        "url": "https://careers.jpmorgan.com/us/en",
        "parser": "jpmorgan",
        "base_url": "https://careers.jpmorgan.com"
    },
    "Morgan Stanley": {
        "url": "https://www.morganstanley.com/people/",
        "parser": "morgan_stanley",
        "base_url": "https://www.morganstanley.com"
    },
    "HDFC": {
        "url": "https://www.hdfcbank.com/working-with-us",
        "parser": "hdfc",
        "base_url": "https://www.hdfcbank.com"
    },
    "Deloitte": {
        "url": "https://jobs2.deloitte.com/",
        "parser": "deloitte",
        "base_url": "https://www2.deloitte.com"
    },
    "Accenture": {
        "url": "https://www.accenture.com/us-en/careers",
        "parser": "accenture",
        "base_url": "https://www.accenture.com"
    },
    "Capgemini": {
        "url": "https://www.capgemini.com/careers/",
        "parser": "capgemini",
        "base_url": "https://www.capgemini.com"
    },
    "TCS": {
        "url": "https://www.tcs.com/careers",
        "parser": "tcs",
        "base_url": "https://www.tcs.com"
    },
    "EY": {
        "url": "https://www.ey.com/en_gl/careers",
        "parser": "ey",
        "base_url": "https://www.ey.com"
    },
    "Mastercard": {
        "url": "https://www.mastercard.com/careers/",
        "parser": "mastercard",
        "base_url": "https://www.mastercard.com"
    },
    "Citi": {
        "url": "https://www.citigroup.com/citi/careers/",
        "parser": "citi",
        "base_url": "https://www.citigroup.com"
    },
    "ZS Associates": {
        "url": "https://www.zs.com/careers",
        "parser": "zs",
        "base_url": "https://www.zs.com"
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
    "Blinkit": {
        "url": "https://blinkit.com/careers",
        "parser": "blinkit",
        "base_url": "https://blinkit.com/careers"
    }
}

# Role/Title related keywords (match roles like "data analyst", "business analyst", "analyst", "analytics")
ROLE_KEYWORDS = [
    r"\bdata\s*analyst\b",
    r"\bbusiness\s*analyst\b",
    r"\banalyst\b",
    r"\bdata\s*science\b",
    r"\bdata\s*analysis\b",
    r"\bdata\s*analytics\b",
    r"\banalytics\b",
]

# Job description / qualification keywords to help detect relevant JD content
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
]

# Compile regex patterns (case-insensitive)
ROLE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ROLE_KEYWORDS]
JD_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JD_KEYWORDS]

# Companies to match (normalized aliases mapped to canonical name)
COMPANY_ALIASES = {
    "amazon": "Amazon",
    "google": "Google",
    "netflix": "Netflix",
    "apple": "Apple",
    "hsbc": "HSBC",
    "goldman sachs": "Goldman Sachs",
    "goldman": "Goldman Sachs",
    "goldman schacs": "Goldman Sachs",
    "jp morgan": "JP Morgan",
    "jpmorgan": "JP Morgan",
    "morgan stanley": "Morgan Stanley",
    "morgan stanly": "Morgan Stanley",
    "hdfc": "HDFC",
    "deloitte": "Deloitte",
    "delloite": "Deloitte",
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "cap gemini": "Capgemini",
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
    "blinkit": "Blinkit"
}

# Precompute company patterns for faster matching
COMPANY_PATTERNS = [(re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v) for k, v in COMPANY_ALIASES.items()]


def send_discord_message(message, max_retries=3):
    """Send message to Discord with retry logic for rate limiting"""
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
            except Exception:
                # No JSON available; try to extract basic info from HTML heuristically
                text = response.text
                # Heuristic: some pages list job titles in <title> or in structured data — skip heavy parsing
                print(f"No JSON data available for {company_name}. Consider adding a custom parser.")
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


def normalize_text(s):
    if not s:
        return ""
    # Lowercase and collapse whitespace
    return re.sub(r"\s+", " ", s.strip().lower())


def detect_company_in_text(text):
    """Return canonical company name if any alias matched in text, otherwise None"""
    for pattern, canonical in COMPANY_PATTERNS:
        if pattern.search(text):
            return canonical
    return None


def job_matches(job):
    """Return True if job matches role keywords + JD keywords and is from one of the requested companies."""
    title = normalize_text(job.get('title') or job.get('position') or '')
    desc = normalize_text(job.get('description') or job.get('summary') or job.get('requirements') or '')
    combined = f"{title} {desc}"

    # Role match (title or description)
    role_match = any(p.search(combined) for p in ROLE_PATTERNS)

    # JD keywords match (optional but helpful)
    jd_match = any(p.search(combined) for p in JD_PATTERNS)

    # Company match: check job['company'] first, then fall back to scanning title/desc
    company_field = normalize_text(job.get('company', ''))
    company_match = None
    if company_field:
        company_match = detect_company_in_text(company_field)
    if not company_match:
        company_match = detect_company_in_text(combined)

    # We require company to be one of the listed companies and (role or jd match)
    if company_match and (role_match or jd_match):
        # ensure canonical company name is set for downstream
        job['company'] = company_match
        return True

    return False


def parse_posted_date(date_str):
    """Try to parse posted_date string into a datetime.date; fallback to today."""
    if not date_str:
        return datetime.now().date()
    # Try common date formats
    formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']
    for f in formats:
        try:
            return datetime.strptime(date_str.strip(), f).date()
        except Exception:
            continue
    # Try ISO parse
    try:
        return datetime.fromisoformat(date_str).date()
    except Exception:
        return datetime.now().date()


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
        link = JOB_SOURCES.get(company, {}).get('base_url', job.get('url', '#'))
    
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
    """Return a compact one-line summary for the listing message"""
    title = job.get('title', job.get('position', 'Unknown Title'))
    company = job.get('company', 'Unknown Company')
    posted_date = job.get('posted_date', datetime.now().strftime('%Y-%m-%d'))
    link = JOB_SOURCES.get(job.get('company'), {}).get('base_url', job.get('url', '#'))
    return f"- {posted_date} | {company} | {title} | {link}"


def create_job_id(job):
    """Create unique job ID combining company, title, and date"""
    company = job.get('company', 'unknown')
    job_id = str(job.get('id', job.get('title', 'unknown'))).replace(' ', '_')
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
        except Exception:
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

# Filter jobs by company + keywords
matched_jobs = [job for job in new_jobs if job_matches(job)]
print(f"🔎 Jobs matching requested companies & keywords: {len(matched_jobs)}")

# Parse and normalize posted_date for sorting; default to today if missing
for job in matched_jobs:
    job['posted_date'] = job.get('posted_date') or datetime.now().strftime('%Y-%m-%d')
    # try to normalize formats
    try:
        parsed = parse_posted_date(str(job['posted_date']))
        job['_parsed_date'] = parsed
        # store normalized string
        job['posted_date'] = parsed.strftime('%Y-%m-%d')
    except Exception:
        job['_parsed_date'] = datetime.now().date()
        job['posted_date'] = datetime.now().strftime('%Y-%m-%d')

# Sort by parsed_date descending (newest first). Change reverse=False if you want oldest-first.
matched_jobs.sort(key=lambda j: j.get('_parsed_date', datetime.now().date()), reverse=True)

# Build and send a single summary message listing all matched jobs (duplicates allowed)
if matched_jobs:
    summary_lines = [f"🔔 Job Listings — total: {len(matched_jobs)}\n"]
    for job in matched_jobs:
        summary_lines.append(format_job_short_line(job))
    summary_message = "\n".join(summary_lines)
    send_discord_message(summary_message)
    time.sleep(1)
else:
    print("No matched jobs to list in summary.")

# Now send individual alerts for each matched job (duplicates allowed per your request)
for job in matched_jobs:
    job_id = create_job_id(job)

    # Send alert (we do not suppress duplicates per your instruction)
    message = format_job_message(job)
    if send_discord_message(message):
        jobs_found.append(job_id)
        # Record it in history for bookkeeping
        sent_jobs.append(job_id)
    time.sleep(1)

# Clean old jobs (keep only last 7 days)
sent_jobs = clean_old_jobs({'sent_jobs': sent_jobs}, days=7)

# Save history with metadata
sent_jobs_data = {
    'sent_jobs': sent_jobs,
    'last_check': datetime.now().isoformat()
}
save_sent_jobs(sent_jobs_data)

print(f"\n✅ Scraper finished. Successfully sent {len(jobs_found)} job alerts.")
print(f"📈 Total unique jobs tracked (last 7 days): {len(sent_jobs)}")
