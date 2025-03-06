import requests
import  pprint
import json


APP_ID = "a68048d5"
APP_KEY = "466d63d3da8528f8fe2dc245e748ebfc"
SEARCH_TITLE = "Tester"



response = requests.get("https://api.adzuna.com/v1/api/jobs/pl/search/1?app_id=a68048d5&app_key=466d63d3da8528f8fe2dc245e748ebfc&results_per_page=100&what=Tester&title_only=Tester&where=Gdansk&distance=50&sort_by=date")



with open("oferty_pracy.txt", "w", encoding="utf-8") as file:
    # Przejście przez wszystkie oferty pracy
    for job in response.json()["results"]:
        # Zapisanie danych o każdej ofercie
        file.write(f"Tytuł: {job['title']}\n")
        file.write(f"Firma: {job['company']['display_name']}\n")
        file.write(f"Link: {job['redirect_url']}\n")
        file.write(f"Opis: {job['description']}\n")
        file.write("-" * 50 + "\n\n")  # Separator między ofertami

