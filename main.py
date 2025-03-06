import json
import smtplib
import time
import schedule
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os

my_email = "mlukasik277@gmail.com"
password = os.getenv("EMAIL_PASSWORD")
APP_KEY = os.getenv("APP_KEY")



# Funkcja do pobierania ofert z API Adzuna
def get_jobs():
    url = f"https://api.adzuna.com/v1/api/jobs/pl/search/1?app_id=a68048d5&app_key=APP_KEY&results_per_page=100&what=Tester&title_only=Tester&where=Gdansk&distance=50&sort_by=date"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return response.json()  # Przekształcenie odpowiedzi na JSON
        except ValueError:
            print(f"Błąd dekodowania JSON. Odpowiedź: {response.text}")
            return None
    else:
        print(f"Błąd zapytania API. Status: {response.status_code}, Treść: {response.text}")
        return None

# Funkcja do wczytywania już wysłanych ofert
def load_sent_jobs():
    try:
        with open("sent_jobs.txt", "r") as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        return set()


# Funkcja do zapisywania wysłanych ofert
def save_sent_jobs(sent_jobs):
    with open("sent_jobs.txt", "w") as file:
        for job_id in sent_jobs:
            file.write(f"{job_id}\n")


# Funkcja do wysyłania maila
def send_email(subject, body, to_email):

    msg = MIMEMultipart()
    msg['To'] = my_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(my_email, password)
        server.send_message(msg)
        server.quit()
        print("Email wysłany pomyślnie")
    except Exception as e:
        print(f"Błąd wysyłania emaila: {e}")


# Główna funkcja sprawdzająca i wysyłająca nowe oferty
def check_for_new_jobs():
    # Pobierz zapisane oferty
    sent_jobs = load_sent_jobs()

    # Pobierz aktualne oferty
    response_json = get_jobs()

    # Przygotuj tekst maila
    email_body = ""
    new_jobs_found = False
    newly_sent_jobs = set(sent_jobs)  # Kopia wysłanych ofert

    # Sprawdź każdą ofertę
    for job in response_json["results"]:
        job_id = job["id"]

        # Jeśli to nowa oferta, dodaj ją do maila
        if job_id not in sent_jobs:
            new_jobs_found = True
            email_body += f"Tytuł: {job['title']}\n"
            email_body += f"Firma: {job.get('company', {}).get('display_name', 'Brak nazwy firmy')}\n"
            email_body += f"Link: {job['redirect_url']}\n"
            email_body += f"Opis: {job['description']}\n"
            email_body += "-" * 50 + "\n\n"

            # Dodaj ID do zestawu wysłanych ofert
            newly_sent_jobs.add(job_id)

    # Wyślij maila tylko jeśli znaleziono nowe oferty
    if new_jobs_found:
        send_email("Nowe oferty pracy w Gdańsku", email_body, my_email)

        # Zapisz zaktualizowaną listę wysłanych ofert
        save_sent_jobs(newly_sent_jobs)
    else:
        print("Brak nowych ofert")


# Ustawienie harmonogramu
schedule.every(1).hour.do(check_for_new_jobs)

# Kod do uruchomienia jako skrypt
if __name__ == "__main__":
    print("Rozpoczęto monitorowanie ofert pracy...")
    # Wykonaj od razu pierwsze sprawdzenie
    check_for_new_jobs()

    # Następnie uruchom harmonogram
    while True:
        schedule.run_pending()
        time.sleep(60)  #
