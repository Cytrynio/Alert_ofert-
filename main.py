import json
import smtplib
import time
import requests
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

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


def get_jobs():
    """Fetch job listings from Adzuna API"""
    url = (
        f"https://api.adzuna.com/v1/api/jobs/pl/search/1"
        f"?app_id={APP_ID}"
        f"&app_key={APP_KEY}"
        f"&results_per_page=100"
        f"&what={SEARCH_TERMS}"
        f"&title_only={SEARCH_TERMS}"
        f"&sort_by=date"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None
    except ValueError as e:
        logger.error(f"JSON decoding error: {e}")
        return None


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
    listing = f"Title: {job.get('title', 'No title')}\n"
    listing += f"Company: {job.get('company', {}).get('display_name', 'No company name')}\n"
    if 'salary_min' in job and 'salary_max' in job:
        listing += f"Salary: {job.get('salary_min')} - {job.get('salary_max')} {job.get('salary_currency', 'PLN')}\n"
    location = job.get('location', {}).get('display_name', 'No location info')
    listing += f"Location: {location}\n"
    listing += f"Link: {job.get('redirect_url', 'No link available')}\n"
    description = job.get('description', 'No description available')
    if len(description) > 500:
        description = description[:497] + "..."
    listing += f"Description: {description}\n"
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
    email_body = ""
    new_jobs_count = 0
    newly_sent_jobs = set(sent_jobs)  # Kopia zbioru sent_jobs

    for job in response_json["results"]:
        job_id = str(job.get("id", ""))
        if not job_id:
            logger.warning("Job with no ID found, skipping")
            continue

        if job_id not in sent_jobs:
            logger.info(f"Found new job: {job_id}")
            email_body += format_job_listing(job)
            newly_sent_jobs.add(job_id)
            new_jobs_count += 1

    logger.info(f"Found {new_jobs_count} new jobs out of {total_jobs} total jobs")

    # Send email and update sent jobs if new jobs found
    if new_jobs_count > 0:
        subject = f"{new_jobs_count} new {SEARCH_TERMS} job offers in Poland"
        email_sent = send_email(subject, email_body, EMAIL)
        if email_sent:
            save_sent_jobs(newly_sent_jobs)
            logger.info(f"Sent {new_jobs_count} new job listings and saved {len(newly_sent_jobs)} job IDs to sent_jobs.txt")
        else:
            logger.warning("Email sending failed, not updating sent_jobs.txt to retry next time")
            # Opcjonalnie: Zapisz mimo niepowodzenia, jeśli chcesz uniknąć ponownego wysyłania
            # save_sent_jobs(newly_sent_jobs)
            # logger.info("Saved sent_jobs.txt despite email failure to avoid duplicates")
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
