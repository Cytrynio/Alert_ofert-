# README dla skryptu Alert Ofert Pracy

Ten skrypt w języku Python monitoruje oferty pracy z API Adzuna dla określonych słów kluczowych (np. "Tester") w Polsce, wysyła powiadomienia e-mail o nowych ofertach i zapisuje wcześniej wysłane oferty, aby uniknąć duplikatów. Działa codziennie, pomijając weekendy, i korzysta ze zmiennych środowiskowych do konfiguracji.

## Funkcje
- Pobiera oferty pracy z API Adzuna na podstawie zdefiniowanych słów kluczowych.
- Wysyła powiadomienia e-mail z formatowanymi szczegółami ofert (tytuł, firma, wynagrodzenie, lokalizacja, link i opis).
- Śledzi identyfikatory wysłanych ofert, aby zapobiec duplikatom.
- Rejestruje działania i błędy w konsoli oraz pliku `job_search.log`.
- Pomija sprawdzanie ofert w weekendy (sobota i niedziela).

## Wymagania
- Python 3.6+
- Wymagane pakiety Python:
  - `requests`
  - `python-dotenv`
  - `smtplib` (wbudowany w standardową bibliotekę Python)
- Dane uwierzytelniające API Adzuna (`APP_ID` i `APP_KEY`).
- Konto Gmail z hasłem aplikacji do wysyłania e-maili.

## Instalacja
1. Sklonuj lub pobierz skrypt na swój komputer.
2. Zainstaluj wymagane pakiety Python:
   ```bash
   pip install requests python-dotenv
   ```
3. Utwórz plik `.env` w katalogu projektu z następującymi zmiennymi:
   ```env
   EMAIL=twój_email@gmail.com
   EMAIL_PASSWORD=hasło_aplikacji
   APP_ID=twój_adzuna_app_id
   APP_KEY=twój_adzuna_app_key
   SEARCH_TERMS=Tester
   ```
   - Zastąp `twój_email@gmail.com` swoim adresem Gmail.
   - Zastąp `hasło_aplikacji` hasłem aplikacji Gmail (wygeneruj je w ustawieniach konta Google).
   - Zastąp `twój_adzuna_app_id` i `twój_adzuna_app_key` swoimi danymi API Adzuna.
   - Opcjonalnie zmień `SEARCH_TERMS`, aby dostosować słowo kluczowe wyszukiwania (domyślnie "Tester").

## Użycie
1. Upewnij się, że plik `.env` jest poprawnie skonfigurowany.
2. Uruchom skrypt:
   ```bash
   python job_search.py
   ```
3. Skrypt sprawdzi nowe oferty pracy, wyśle e-mail z nowymi ofertami (jeśli istnieją) i zapisze ich identyfikatory w pliku `sent_jobs.txt`.

## Uwagi
- Skrypt pomija działanie w weekendy (sobota i niedziela).
- W przypadku problemów z wysyłką e-mail, sprawdź poprawność hasła aplikacji Gmail.
- Logi są zapisywane w pliku `job_search.log` dla łatwego debugowania.

## Licencja
Brak określonej licencji. Skrypt jest przeznaczony do użytku osobistego lub edukacyjnego.
