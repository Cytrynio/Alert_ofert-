import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
import time
# Importuj bezpośrednio funkcje z twojego głównego modułu
import main  # Zakładam, że główny plik nazywa się main.py


# ---- Fixtures ----

@pytest.fixture
def mock_env_variables(monkeypatch):
    """Fixture zapewniający zmienne środowiskowe dla testów"""
    # Użyj monkeypatch zamiast patch.dict dla zmiennych środowiskowych
    monkeypatch.setenv("EMAIL", "test@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "test_password")
    monkeypatch.setenv("ADZUNA_APP_ID", "test_app_id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "test_app_key")
    monkeypatch.setenv("SEARCH_TERMS", "Python Developer")
    monkeypatch.setenv("LOCATION", "Warszawa")
    monkeypatch.setenv("DISTANCE", "30")

    # Konieczne jest ponowne wczytanie wartości do zmiennych w module main
    main.APP_ID = os.getenv("ADZUNA_APP_ID")
    main.APP_KEY = os.getenv("ADZUNA_APP_KEY")
    main.EMAIL = os.getenv("EMAIL")
    main.PASSWORD = os.getenv("EMAIL_PASSWORD")
    main.SEARCH_TERMS = os.getenv("SEARCH_TERMS", "Tester")
    main.LOCATION = os.getenv("LOCATION", "Gdansk")
    main.DISTANCE = os.getenv("DISTANCE", "50")


@pytest.fixture
def sample_job_data():
    """Fixture dostarczający przykładowe dane ofert pracy"""
    return {
        "results": [
            {
                "id": "job1",
                "title": "Senior Python Developer",
                "company": {"display_name": "Example Corp"},
                "location": {"display_name": "Warszawa, Polska"},
                "description": "Poszukujemy doświadczonego programisty Python...",
                "redirect_url": "https://example.com/job1",
                "salary_min": 15000,
                "salary_max": 20000,
                "salary_currency": "PLN"
            },
            {
                "id": "job2",
                "title": "Python Backend Developer",
                "company": {"display_name": "Tech Solutions"},
                "location": {"display_name": "Warszawa, Polska"},
                "description": "Praca w dynamicznym zespole...",
                "redirect_url": "https://example.com/job2"
            }
        ]
    }


@pytest.fixture
def temp_sent_jobs_file(tmp_path):
    """Fixture tworzący tymczasowy plik dla sent_jobs.txt"""
    file_path = tmp_path / "sent_jobs.txt"
    with open(file_path, 'w') as f:
        f.write("job3\njob4\n")

    # Patch funkcji aby używały tymczasowego pliku
    with patch('main.SENT_JOBS_FILE', str(file_path)):
        yield str(file_path)


# ---- Testy ----

def test_get_jobs(mock_env_variables, sample_job_data):
    """Test funkcji pobierającej oferty z API"""
    with patch('requests.get') as mock_get:
        # Konfiguracja mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_job_data
        mock_get.return_value = mock_response

        # Wywołanie testowanej funkcji
        result = main.get_jobs()

        # Asercje
        assert result is not None
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "job1"
        assert result["results"][1]["title"] == "Python Backend Developer"

        # Sprawdź czy API zostało wywołane z prawidłowymi parametrami
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        assert "api.adzuna.com" in call_args
        assert "app_id=test_app_id" in call_args
        assert "app_key=test_app_key" in call_args


def test_load_and_save_sent_jobs(temp_sent_jobs_file):
    """Test wczytywania i zapisywania wysłanych ofert"""
    # Test wczytywania
    sent_jobs = main.load_sent_jobs()
    assert isinstance(sent_jobs, set)
    assert len(sent_jobs) == 2
    assert "job3" in sent_jobs
    assert "job4" in sent_jobs

    # Test zapisywania
    new_jobs = {"job3", "job4", "job5"}
    main.save_sent_jobs(new_jobs)

    # Sprawdź czy plik został zaktualizowany
    with open(temp_sent_jobs_file, 'r') as f:
        content = f.read().splitlines()

    assert len(content) == 3
    assert set(content) == new_jobs


def test_send_email(mock_env_variables):
    """Test wysyłania emaila"""
    with patch('smtplib.SMTP') as mock_smtp:
        # Konfiguracja mocka
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        # Wywołanie testowanej funkcji
        result = main.send_email(
            "Test Subject",
            "Test Body",
            "recipient@example.com"
        )

        # Asercje
        assert result is True
        mock_smtp.assert_called_once_with('smtp.gmail.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


def test_format_job_listing(sample_job_data):
    """Test formatowania pojedynczej oferty pracy"""
    job = sample_job_data["results"][0]
    formatted = main.format_job_listing(job)

    # Sprawdź czy wszystkie kluczowe informacje są zawarte
    assert "Senior Python Developer" in formatted
    assert "Example Corp" in formatted
    assert "15000 - 20000 PLN" in formatted
    assert "Warszawa, Polska" in formatted
    assert "https://example.com/job1" in formatted

#
# def test_check_for_new_jobs(mock_env_variables, sample_job_data):
#     """Test głównej funkcji sprawdzającej nowe oferty pracy"""
#     # Użyj konkretnych nazw funkcji z modułu
#     with patch('main.get_jobs') as mock_get, \
#             patch('main.load_sent_jobs') as mock_load, \
#             patch('main.send_email') as mock_send, \
#             patch('main.save_sent_jobs') as mock_save:
#         # Konfiguracja mocków
#         mock_get.return_value = sample_job_data
#         mock_load.return_value = {"job2"}  # job1 będzie nową ofertą
#         mock_send.return_value = True
#
#         # Wywołanie testowanej funkcji
#         main.check_for_new_jobs()
#
#         # Asercje
#         mock_get.assert_called_once()
#         mock_load.assert_called_once()
#
#         # Sprawdź czy email został wysłany z prawidłowym tytułem
#         mock_send.assert_called_once()
#         # Sprawdź argumenty wywołania
#         call_args = mock_send.call_args
#         assert call_args is not None
#
#         # Sprawdź czy zapisano zaktualizowaną listę ofert
#         mock_save.assert_called_once()
#         # Sprawdź argumenty wywołania
#         call_args = mock_save.call_args
#         assert call_args is not None
#         saved_jobs = call_args[0][0]
#         assert "job1" in saved_jobs  # Sprawdź czy dodano nową ofertę
def test_check_for_new_jobs_weekday(mock_env_variables, sample_job_data, caplog):
    """Test głównej funkcji w dniu roboczym"""
    caplog.set_level("INFO")  # Umożliwia przechwytywanie logów
    # Symuluj dzień roboczy (poniedziałek, 3 marca 2025)
    fake_time = time.struct_time((2025, 3, 3, 12, 0, 0, 0, 62, 0))  # tm_wday=0 (poniedziałek)

    with patch('main.time.localtime') as mock_time, \
            patch('main.get_jobs') as mock_get, \
            patch('main.load_sent_jobs') as mock_load, \
            patch('main.send_email') as mock_send, \
            patch('main.save_sent_jobs') as mock_save:
        mock_time.return_value = fake_time
        mock_get.return_value = sample_job_data
        mock_load.return_value = {"job2"}  # job1 będzie nową ofertą
        mock_send.return_value = True

        main.check_for_new_jobs()

        # Asercje dla dnia roboczego
        mock_get.assert_called_once()
        mock_load.assert_called_once()
        mock_send.assert_called_once()
        subject = mock_send.call_args[0][0]
        assert "new" in subject.lower()
        mock_save.assert_called_once()
        saved_jobs = mock_save.call_args[0][0]
        assert "job1" in saved_jobs
        assert "job2" in saved_jobs

def test_check_for_new_jobs_weekend(mock_env_variables, sample_job_data, caplog):
    """Test głównej funkcji w weekend"""
    caplog.set_level("INFO")  # Umożliwia przechwytywanie logów
    # Symuluj weekend (sobota, 8 marca 2025)
    fake_time = time.struct_time((2025, 3, 8, 12, 0, 0, 5, 67, 0))  # tm_wday=5 (sobota)

    with patch('main.time.localtime') as mock_time, \
            patch('main.get_jobs') as mock_get, \
            patch('main.load_sent_jobs') as mock_load, \
            patch('main.send_email') as mock_send, \
            patch('main.save_sent_jobs') as mock_save:
        mock_time.return_value = fake_time
        mock_get.return_value = sample_job_data
        mock_load.return_value = {"job2"}
        mock_send.return_value = True

        main.check_for_new_jobs()

        # Asercje dla weekendu
        mock_get.assert_not_called()  # get_jobs nie powinno być wywołane
        assert "Dzisiaj jest weekend. Pomijam sprawdzanie ofert." in caplog.text
        mock_send.assert_not_called()  # Email nie powinien być wysłany
        mock_save.assert_not_called()  # Nie zapisujemy nic w weekend