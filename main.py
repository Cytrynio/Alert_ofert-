import json
import smtplib
import time
import requests
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("job_search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("job_search")

# Load environment variables
load_dotenv()

# Configuration
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")
SEARCH_TERMS = os.getenv("SEARCH_TERMS", "Tester")
SENT_JOBS_FILE = "sent_jobs.txt"

# Priority cities for grouping
PRIORITY_CITIES = ["Gdansk", "Warszawa", "Wroclaw", "Poznan", "Krakow"]


def get_jobs():
    """Fetch job listings from Adzuna API for all of Poland"""
    url = (
        f"https://api.adzuna.com/v1/api/jobs/pl/search/1"
        f"?app_id={APP_ID}"
        f"&app_key={APP_KEY}"
        f"&results_per_page=100"  # Maximum per page
        f"&what={SEARCH_TERMS}"
        f"&sort_by=date"
    )

    try:
        logger.info(f"Requesting jobs for all of Poland")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check if we got results and how many pages there are
        if "results" in data:
            total_results = data.get("count", 0)
            total_pages = (total_results + 99) // 100  # Ceil division
            logger.info(f"Found {total_results} total results across {total_pages} pages")
            
            # If more than one page, fetch additional pages (up to 5 to avoid rate limits)
            all_results = data["results"]
            max_pages = min(5, total_pages)
            
            for page in range(2, max_pages + 1):
                page_url = url.replace("/search/1", f"/search/{page}")
                logger.info(f"Fetching page {page} of results")
                try:
                    page_response = requests.get(page_url, timeout=30)
                    page_response.raise_for_status()
                    page_data = page_response.json()
                    if "results" in page_data:
                        all_results.extend(page_data["results"])
                        logger.info(f"Added {len(page_data['results'])} jobs from page {page}")
                    # Small delay to respect rate limits
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
            
            data["results"] = all_results
            logger.info(f"Total jobs collected: {len(all_results)}")
        
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None
    except ValueError as e:
        logger.error(f"JSON decoding error: {e}")
        return None


def categorize_by_city(jobs):
    """Group jobs by city, with 'Remote' and 'Other' categories"""
    jobs_by_city = defaultdict(list)
    
    for job in jobs:
        # Get location from job data
        location = job.get('location', {}).get('display_name', '').split(',')[0].strip()
        
        # Check for remote indicators
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        
        is_remote = any(keyword in title.lower() + " " + description.lower() 
                        for keyword in ["remote", "zdaln", "home office", "praca z domu"])
        
        if is_remote:
            jobs_by_city["Praca zdalna"].append(job)
        elif location in PRIORITY_CITIES:
            jobs_by_city[location].append(job)
        elif location:
            jobs_by_city[location].append(job)
        else:
            jobs_by_city["Inne lokalizacje"].append(job)
    
    return jobs_by_city


def load_sent_jobs():
    """Load previously sent job IDs from file"""
    try:
        with open(SENT_JOBS_FILE, "r") as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        logger.info(f"No {SENT_JOBS_FILE} file found. Creating new set.")
        return set()


def save_sent_jobs(sent_jobs):
    """Save sent job IDs to file"""
    try:
        with open(SENT_JOBS_FILE, "w") as file:
            for job_id in sent_jobs:
                file.write(f"{job_id}\n")
        logger.info(f"Saved {len(sent_jobs)} job IDs to {SENT_JOBS_FILE}")
    except Exception as e:
        logger.error(f"Error saving sent jobs: {e}")


def send_email(subject, body, to_email):
    """Send email with job listings"""
    if not EMAIL or not PASSWORD:
        logger.error("Email credentials not configured")
        return False

    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def format_job_listing(job):
    """Format a single job listing for email"""
    listing = f"Tytuł: {job.get('title', 'Brak tytułu')}\n"
    listing += f"Firma: {job.get('company', {}).get('display_name', 'Brak nazwy firmy')}\n"
    if 'salary_min' in job and 'salary_max' in job:
        listing += f"Wynagrodzenie: {job.get('salary_min')} - {job.get('salary_max')} {job.get('salary_currency', 'PLN')}\n"
    location = job.get('location', {}).get('display_name', 'Brak informacji o lokalizacji')
    listing += f"Lokalizacja: {location}\n"
    listing += f"Link: {job.get('redirect_url', 'Brak dostępnego linku')}\n"
    description = job.get('description', 'Brak dostępnego opisu')
    if len(description) > 500:
        description = description[:497] + "..."
    listing += f"Opis: {description}\n"
    listing += "-" * 50 + "\n\n"
    return listing


def check_for_new_jobs():
    """Main function to check for and send new job listings"""
    current_day = time.localtime().tm_wday
    if current_day >= 5:  # 5=sobota, 6=niedziela
        logger.info("Dzisiaj jest weekend. Pomijam sprawdzanie ofert.")
        return

    logger.info("Checking for new job listings...")

    # Load previously sent jobs
    sent_jobs = load_sent_jobs()
    logger.info(f"Loaded {len(sent_jobs)} previously sent job IDs")

    # Get current job listings
    response_json = get_jobs()
    if not response_json or "results" not in response_json:
        logger.error("Failed to retrieve job listings or invalid response format")
        return

    total_jobs = len(response_json["results"])
    logger.info(f"Retrieved {total_jobs} job listings from API")

    # Process new job listings
    new_jobs = []
    newly_sent_jobs = set(sent_jobs)  # Copy of sent_jobs set

    for job in response_json["results"]:
        job_id = str(job.get("id", ""))
        if not job_id:
            logger.warning("Job with no ID found, skipping")
            continue

        if job_id not in sent_jobs:
            logger.info(f"Found new job: {job_id}")
            new_jobs.append(job)
            newly_sent_jobs.add(job_id)

    new_jobs_count = len(new_jobs)
    logger.info(f"Found {new_jobs_count} new jobs out of {total_jobs} total jobs")

    # Send email if new jobs found
    if new_jobs_count > 0:
        # Group jobs by city
        jobs_by_city = categorize_by_city(new_jobs)
        
        # Create email content
        email_body = f"Znaleziono {new_jobs_count} nowych ofert pracy dla słów kluczowych: {SEARCH_TERMS}\n\n"
        
        # Add priority cities first
        for city in PRIORITY_CITIES:
            if city in jobs_by_city and jobs_by_city[city]:
                email_body += f"=== {city} ({len(jobs_by_city[city])} ofert) ===\n\n"
                for i, job in enumerate(jobs_by_city[city], 1):
                    email_body += f"{i}. "
                    email_body += format_job_listing(job)
                email_body += "\n"
                # Remove from dictionary to avoid duplication
                del jobs_by_city[city]
        
        # Add remote jobs next if they exist
        if "Praca zdalna" in jobs_by_city and jobs_by_city["Praca zdalna"]:
            email_body += f"=== Praca zdalna ({len(jobs_by_city['Praca zdalna'])} ofert) ===\n\n"
            for i, job in enumerate(jobs_by_city['Praca zdalna'], 1):
                email_body += f"{i}. "
                email_body += format_job_listing(job)
            email_body += "\n"
            del jobs_by_city["Praca zdalna"]
        
        # Add all other cities, sorted alphabetically
        for city in sorted(jobs_by_city.keys()):
            if jobs_by_city[city]:  # Check if there are any jobs for this city
                email_body += f"=== {city} ({len(jobs_by_city[city])} ofert) ===\n\n"
                for i, job in enumerate(jobs_by_city[city], 1):
                    email_body += f"{i}. "
                    email_body += format_job_listing(job)
                email_body += "\n"
        
        subject = f"{new_jobs_count} nowych ofert pracy {SEARCH_TERMS} w Polsce"
        email_sent = send_email(subject, email_body, EMAIL)
        if email_sent:
            save_sent_jobs(newly_sent_jobs)
            logger.info(f"Sent {new_jobs_count} new job listings and saved {len(newly_sent_jobs)} job IDs")
        else:
            logger.warning("Email sending failed, not updating sent_jobs.txt to retry next time")
    else:
        logger.info("No new job listings found")


def main():
    """Main function to run the script"""
    logger.info("Starting job search monitoring...")

    if not APP_ID or not APP_KEY:
        logger.error("Adzuna API credentials not configured")
        return

    check_for_new_jobs()


if __name__ == "__main__":
    main()
