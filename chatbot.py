import sys
import time
import datetime
import requests
import random
import re
import csv
import logging
import os
import json
import argparse
import schedule
import threading
import unittest
from difflib import get_close_matches
from datetime import datetime, timedelta
try:
    from sense_hat import SenseHat
    sense = SenseHat()
except ImportError:
    sense = None


def setup_logger(log_enabled, log_level):
    logging.root.handlers = []

    if log_enabled:
        level = logging.WARNING
        if log_level == "INFO":
            level = logging.INFO
        elif log_level == "WARNING":
            level = logging.WARNING
        else:
            print(
                f"[WARN] Log-Level '{log_level}' ist ungültig. WARNING wird benutzt.")
            level = logging.WARNING
        logging.basicConfig(
            filename='app.log',
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8',
            force=True
        )

        logging.info("Logging wird Aktiviert.")
        logging.info(f"Programm gestartet mit Log-Level: {log_level}")
        logging.warning("Das ist ein WARNING-Test.")  # Test WARNING
    else:
        logging.disable(logging.CRITICAL)


# API-Schlüssel
API_KEY = "75bae2cb12c0bb142a22fcd9a9eb9db4"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"
CITY = "Goslar"
SAVE_FILE = "temperature_log.json"

# Zeitfunktionen


def get_time():
    return time.strftime("(%H:%M:%S)")


def get_current_time():
    """Aktuelle Uhrzeit im Format '(HH:MM:SS)' abrufen"""
    return f"({datetime.now().strftime('%H:%M:%S')})"  #


# Datebase_für_ort.task 14&25
LOCATIONS = {
    "gotec": {
        "Name": "GoTEC (Konferenzzentrum Goslar)",
        "Universität": "Zugehörig zur TU Clausthal und Ostfalia Hochschule",
        "Adresse": "EnergyCampus Goslar, Am Stollen 19A, 38640 Goslar, Deutschland",
        "Beschreibung": "GoTEC ist ein Konferenzzentrum im EnergyCampus Goslar, das für universitäre Veranstaltungen, Workshops und das Programm Digital Technologies genutzt wird. Seit 2022 ist es der Hauptort für Kurse des Digital Technologies-Programms.",
        "Stadt": "Goslar"
    },
    "hörsaal_wolfenbüttel": {
        "Name": "Hörsaal A (Ostfalia Hochschule Wolfenbüttel)",
        "Universität": "Ostfalia Hochschule für angewandte Wissenschaften",
        "Adresse": "Salzdahlumer Straße 46/48, 38302 Wolfenbüttel, Deutschland",
        "Beschreibung": "Hörsaal A ist ein moderner Vorlesungssaal im Campus Wolfenbüttel der Ostfalia Hochschule, geeignet für Vorlesungen und kleinere universitäre Veranstaltungen.",
        "Stadt": "Wolfenbüttel"
    }
}


def get_coordinates(city_name):
    """Koordinaten der Stadt abrufen"""
    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={API_KEY}"
        response = requests.get(geo_url)
        response.raise_for_status()
        if response.json():
            data = response.json()[0]
            return data['lat'], data['lon']
        return None, None
    except requests.RequestException:
        return None, None


def get_weather(city_name, date=None):
    """Wetterbedingungen für Stadt und Datum abrufen"""
    try:
        lat, lon = get_coordinates(city_name)
        if not lat or not lon:
            return f"{get_current_time()} Ort nicht gefunden!"

        # Aktuelles Wetter
        if not date:
            url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
            response = requests.get(url)
            response.raise_for_status()
            if response.status_code == 200:
                data = response.json()
                return {
                    "Temperatur": f"{data['main']['temp']} °C",
                    "Beschreibung": data['weather'][0]['description'],
                    "Luftfeuchtigkeit": f"{data['main']['humidity']}%",
                    "Zeit": get_current_time()
                }
            return f"{get_current_time()} Fehler beim Abrufen des Wetters!"

        # Vorhersage für ein bestimmtes Datum
        target_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        today = datetime.datetime.now()
        delta = (target_date - today).days

        if delta < 0:
            return f"{get_current_time()} Für vergangene Daten benötigen Sie eine historische API!"
        elif delta > 7:
            return f"{get_current_time()} Vorhersagen für mehr als 7 Tage sind nicht verfügbar!"
        else:
            url = f"{FORECAST_URL}?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=de"
            response = requests.get(url)
            response.raise_for_status()
            if response.status_code == 200:
                data = response.json()
                for forecast in data['list']:
                    forecast_time = datetime.datetime.fromtimestamp(
                        forecast['dt'])
                    if forecast_time.date() == target_date.date():
                        return {
                            "Temperatur": f"{forecast['main']['temp']} °C",
                            "Beschreibung": forecast['weather'][0]['description'],
                            "Luftfeuchtigkeit": f"{forecast['main']['humidity']}%",
                            "Datum der Vorhersage": forecast_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Tage bis zur Vorhersage": f"{delta} Tag(e)",
                            "Zeit": get_current_time()
                        }
                return f"{get_current_time()} Keine Vorhersage für das genaue Datum gefunden!"
            return f"{get_current_time()} Fehler beim Abrufen der Vorhersage!"

    except ValueError:
        return f"{get_current_time()} Falsches Datumsformat! (Beispiel: 2025-05-10)"
    except requests.RequestException:
        return f"{get_current_time()} Fehler beim Abrufen des Wetters!"


def get_location_info(location_key, date=None, query=""):
    """Informationen zu einem Ort und Wetter abrufen"""
    if location_key not in LOCATIONS:
        return f"{get_current_time()} Ort nicht in der Datenbank gefunden!"
    location_info = LOCATIONS[location_key]
    weather = get_weather(location_info["Stadt"], date)

    # task27 : zeit_intervall_erkennung

    query = query.lower()
    time_slot = "all"
    if "morgen" in query or "vormittag" in query:
        time_slot = "morning"
    elif "nachmittag" in query or "abend" in query:
        time_slot = "afternoon"

    avg_temp = get_average_sensor_temp(time_slot)
    avg_temp_str = f"{avg_temp} °C" if avg_temp is not None else "Keine Daten verfügbar"

    return {
        "Ort-Informationen": {**location_info, "Zeit": get_current_time()},
        "Wetter": weather,
        "Durchschnittstemperatur (Sensor, 3 Tage)": {
            "Zeitraum": time_slot.capitalize(),
            "Temperatur": avg_temp_str
        }
    }


def process_user_query(query):
    """Benutzeranfrage verarbeiten"""
    query = query.lower()
    date = None

    # Datum

    date_pattern = r"\b(\d{1,2}\.\s*(?:Mai|mai|MAY)\s*\d{4})\b|(\d{4}-\d{2}-\d{2})"
    date_match = re.search(date_pattern, query)
    if date_match:
        if date_match.group(1):  # فرمت "10. Mai 2025"
            date_str = date_match.group(1).replace(
                "mai", "05").replace(".", "").replace(" ", "-")
            parts = date_str.split("-")
            date = f"{parts[2]}-05-{parts[0].zfill(2)}"
        elif date_match.group(2):  # فرمت "2025-05-10"
            date = date_match.group(2)

    # Was ist seine frage
    if "gotec" in query or "konferenzzentrum" in query or "energy campus" in query or "digital technologies" in query:
        return get_location_info("gotec", date, query)
    elif "hörsaal" in query or "vorlesungssaal" in query or "wolfenbüttel" in query or "ostfalia" in query:
        return get_location_info("hörsaal_wolfenbüttel", date, query)
    elif "veranstaltung" in query or "universität" in query:
        return get_location_info("gotec", date, query)
    else:
        return None


# Frage-Antwort-Dictionary
faq = {
    "wie spät ist es?": lambda: f"Es ist jetzt: {time.strftime('%H:%M:%S')}",
    "wie heißt du?": lambda: "Ich bin ein einfacher Chatbot.",
    "was kannst du tun?": lambda: "Ich kann einfache Fragen beantworten.",
    "was ist python?": lambda: "Python ist eine Programmiersprache."
}

# Random-Antworten-Dictionary
antworten_db = {
    "was ist dein name?": [
        "Ich bin dein freundlicher Chatbot.",
        "Mein Name ist Chatbot.",
        "Du kannst mich Bot nennen!"
    ]
}

# Knowledge-Base
knowledge_base = {
    "semester": [
        "Wann beginnt das neue Semester?",
        "Wie lange dauert ein Semester?",
        "Welche Kurse gibt es dieses Semester?"
    ],
    "prüfung": [
        "Wie kann ich mich für Prüfungen anmelden?",
        "Wann finden die Prüfungen statt?",
        "Wie viele Versuche habe ich pro Prüfung?"
    ]
}

# Vordefinierte Antworten für Knowledge-Base
knowledge_base_answers = {
    "wann beginnt das neue semester": "Das Semester beginnt am 1. Oktober.",
    "wie lange dauert ein semester": "Ein Semester dauert in der Regel sechs Monate.",
    "welche kurse gibt es dieses semester": "Die Kursliste hängt von der Universität ab. Bitte überprüfe den Studienplan.",
    "wie kann ich mich für prüfungen anmelden": "Du kannst dich über das Online-Portal der Universität für Prüfungen anmelden.",
    "wann finden die prüfungen statt": "Die Prüfungen finden normalerweise am Ende des Semesters statt.",
    "wie viele versuche habe ich pro prüfung": "In der Regel hast du drei Versuche pro Prüfung."
}

# Neues Wörterbuch für Varianten
question_variants = {
    "hörsaal_location": {
        "keywords": ["hörsaal", "vorlesungssaal", "wo", "finde", "erreiche", "befindet"],
        "variants": [
            "wo befindet sich der vorlesungssaal xxx?",
            "wo befindet sich der hörsaal xxx?",
            "wo finde ich den hörsaal xxx?",
            "wie erreiche ich den hörsaal xxx?"
        ],
        "response": "Bitte spezifizieren Sie den Hörsaal oder die Stadt (z.B. 'Hörsaal Wolfenbüttel')."
    },
    "bibliothek_hours": {
        "keywords": ["bibliothek", "öffnungszeiten", "geöffnet"],
        "variants": [
            "wann ist die bibliothek geöffnet?",
            "was sind die öffnungszeiten der bibliothek?",
            "bibliothek"
        ],
        "response": "Die Bibliothek ist von 8 bis 20 Uhr geöffnet."
    }
}
# task 23
# question_variants

quiz_questions = [
    {
        "question": "Welches Jahr wurde die TU Clausthal gegründet?",
        "options": ["1775", "1800", "1900", "2000"],
        "correct": "1775"
    },
    {
        "question": "Wie heißt das Konferenzzentrum in Goslar?",
        "options": ["EnergyCampus", "GoTEC", "Ostfalia", "Hörsaal A"],
        "correct": "GoTEC"
    },
    {
        "question": "In welcher Stadt liegt die Ostfalia Hochschule Hörsaal A?",
        "options": ["Goslar", "Braunschweig", "Wolfenbüttel", "Hannover"],
        "correct": "Wolfenbüttel"
    },
    {
        "question": "Welches Programm wird im GoTEC seit 2022 angeboten?",
        "options": ["Digital Technologies", "Maschinenbau", "Chemie", "Physik"],
        "correct": "Digital Technologies"
    },
    {
        "question": "Wie viele Fakultäten hat die TU Clausthal?",
        "options": ["3", "4", "5", "6"],
        "correct": "4"
    },
    {
        "question": "Welcher Campus beherbergt GoTEC?",
        "options": ["EnergyCampus", "ScienceCampus", "TechCampus", "MainCampus"],
        "correct": "EnergyCampus"
    },
    {
        "question": "Welche Adresse hat GoTEC?",
        "options": ["Am Stollen 19A", "Hauptstraße 10", "Bahnhofstraße 5", "Schillerstraße 3"],
        "correct": "Am Stollen 19A"
    },
    {
        "question": "Welche Hochschule betreibt Hörsaal A in Wolfenbüttel?",
        "options": ["TU Clausthal", "Ostfalia", "Uni Hannover", "TU Braunschweig"],
        "correct": "Ostfalia"
    },
    {
        "question": "Wie viele Monate dauert ein Semester an der Ostfalia?",
        "options": ["4", "5", "6", "7"],
        "correct": "6"
    },
    {
        "question": "Wann beginnt das Wintersemester an der TU Clausthal?",
        "options": ["1. Oktober", "1. September", "15. Oktober", "1. November"],
        "correct": "1. Oktober"
    }
]

# Task 3: Compound questions


def process_compound_question(user_input, questions=None):
    predefined_questions = {
        "wie melde ich mich für ein seminar an": [
            "Die Anmeldung für Seminare erfolgt über das Online-Portal der Universität unter dem Bereich 'Veranstaltungen'"
        ],
        "wie kann ich meine noten einsehen": [
            "Du kannst deine Noten im Campus-Management-System unter dem Reiter 'Leistungen' einsehen"
        ],
        "wann beginnt das semester winter 2025": [
            "Der Beginn des Semesters ist für Anfang Oktober geplant. Am 1.10.2025 starten die Lehrveranstaltungen für das Wintersemester 2025."
        ],
        "bis wann muss ich den semesterbeitrag bezahlen": [
            "Der Semesterbeitrag muss bis zum 15. September 2025 bezahlt werden."
        ],
        "wo befindet sich der vorlesungssaal": [
            "Gebäude 2, Raum 201, neben dem Treppenhaus"
        ],
        "wo finde ich den hörsaal": [
            "Gebäude 2, Raum 201, neben dem Treppenhaus"
        ],
        "wie erreiche ich den hörsaal": [
            "Gebäude 2, Raum 201, neben dem Treppenhaus"
        ],
    }

    # Einleitungen wie "Hallo" oder "Hey" weglassen
    user_input = re.sub(
        r"^(hallo|hey|hi)[,\s]*", "", user_input.lower().strip(), flags=re.IGNORECASE)

    # Die Frage in Teile mit "und" oder "oder" aufteilen
    parts = [p.strip().replace('?', '').replace('.', '')
             for p in re.split(r'\s*(?:und|oder)\s*', user_input) if p.strip()]
    responses = []

    for index, part in enumerate(parts, 1):
        if not part:
            responses.append(f"{index}. Frage nicht erkannt: (Leer Bereich)")
            continue

        matched = False
        for question, answers in predefined_questions.items():
            question_clean = question.replace('?', '').replace('.', '').lower()
            if part == question_clean or question_clean in part or part in question_clean:
                response = answers[0]
                response = f"{index}. {response}"
                if 'hörsaal' in part or 'vorlesungssaal' in part:
                    weather_info = get_weather('Goslar')
                    avg_temp = get_average_sensor_temp('all')
                    response += f"\n   Wetter in Goslar: {weather_info}"
                    response += f"\n   Durchschnittstemperatur: {avg_temp}°C" if avg_temp is not None else "\n   Durchschnittstemperatur: Keine Daten verfügbar"
                responses.append(response)
                matched = True
                break
            # Gleiche Wörter suchen
            part_words = set(part.split())
            question_words = set(question_clean.split())
            common_words = part_words.intersection(question_words)
            if len(common_words) >= min(len(part_words), len(question_words)) * 0.5:
                response = answers[0]
                response = f"{index}. {response}"
                if 'hörsaal' in part or 'vorlesungssaal' in part:
                    weather_info = get_weather('Goslar')
                    avg_temp = get_average_sensor_temp('all')
                    response += f"\n   Wetter in Goslar: {weather_info}"
                    response += f"\n   Durchschnittstemperatur: {avg_temp}°C" if avg_temp is not None else "\n   Durchschnittstemperatur: Keine Daten verfügbar"
                responses.append(response)
                matched = True
                break

        if not matched:
            responses.append(f"{index}. Frage nicht erkannt: {part}")

    return '\n'.join(responses)

# task16


def list_all_questions():
    """Alle Fragen in der Chatbot-Wissensdatenbank anzeigen"""
    print(f"{get_time()} Liste aller Fragen in der Wissensbasis:\n")

    # Fragen sind in antworten_db aus CSV-Datei

    print("=== Fragen aus der CSV-Datei (antworten_db) ===")
    if antworten_db:
        for idx, question in enumerate(sorted(antworten_db.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in antworten_db vorhanden.")
    print()

    # Fragen sind in knowledge_base_answers

    print("=== Fragen aus der Knowledge Base (knowledge_base_answers) ===")
    if knowledge_base_answers:
        for idx, question in enumerate(sorted(knowledge_base_answers.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in knowledge_base_answers vorhanden.")
    print()

    # Fragen sind in FAQ
    print("=== Fragen aus der FAQ (faq) ===")
    if faq:
        for idx, question in enumerate(sorted(faq.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in faq vorhanden.")
    print()

    # Fragen sind in question_variants
    print("=== Fragen aus Varianten (question_variants) ===")
    if question_variants:
        for key, variant_info in question_variants.items():
            print(f"--- Kategorie: {key} ---")
            for idx, variant in enumerate(variant_info["variants"], 1):
                print(f"{idx}. {variant}")
    else:
        print("Keine Fragen in question_variants vorhanden.")

# task19


def list_all_questions():
    "wissen bassis"""
    print(f"{get_time()} Liste aller Fragen in der Wissensbasis:\n")

    # Fragen sind in antworten_db. Die Datei ist CSV
    print("=== Fragen aus der CSV-Datei (antworten_db) ===")
    if antworten_db:
        for idx, question in enumerate(sorted(antworten_db.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in antworten_db vorhanden.")
    print()

    # Fragen sind in knowledge_base_answers
    print("=== Fragen aus der Knowledge Base (knowledge_base_answers) ===")
    if knowledge_base_answers:
        for idx, question in enumerate(sorted(knowledge_base_answers.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in knowledge_base_answers vorhanden.")
    print()

    # Fragen sind in FAQ
    print("=== Fragen aus der FAQ (faq) ===")
    if faq:
        for idx, question in enumerate(sorted(faq.keys()), 1):
            print(f"{idx}. {question}")
    else:
        print("Keine Fragen in faq vorhanden.")
    print()

    # Fragen sind in question_variants
    print("=== Fragen aus Varianten (question_variants) ===")
    if question_variants:
        for key, variant_info in question_variants.items():
            print(f"--- Kategorie: {key} ---")
            for idx, variant in enumerate(variant_info["variants"], 1):
                print(f"{idx}. {variant}")
    else:
        print("Keine Fragen in question_variants vorhanden.")
    print()

    # Fragen sind in der CSV-Datei
    print("=== Fragen aus der externen CSV-Datei ===")
    csv_file_path = "data/sample_data.csv"
    if not os.path.exists(csv_file_path):
        print(f"{get_time()} Fehler: CSV-Datei nicht gefunden: {csv_file_path}")
    else:
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                if 'question' not in reader.fieldnames:
                    print(
                        f"{get_time()} Fehler: CSV-Datei muss eine Spalte 'question' enthalten.")
                else:
                    questions = [row['question'] for row in reader]
                    if questions:
                        for idx, question in enumerate(sorted(questions), 1):
                            print(f"{idx}. {question}")
                    else:
                        print("Keine Fragen in der CSV-Datei vorhanden.")
        except Exception as e:
            print(
                f"{get_time()} Unerwarteter Fehler beim Lesen der CSV-Datei: {str(e)}")


def frage_aufteilen(eingabe_text):
    sätze = re.split(
        r'\s*(?:\?|\? und |\? oder | und | oder )\s*', eingabe_text.strip())
    fragen = [s.strip() + '?' if not s.endswith('?') else s.strip()
              for s in sätze if s.strip()]
    return fragen


def frage_beantworten(frage):
    frage = frage.lower().rstrip('?')
    if frage in knowledge_base_answers:
        return knowledge_base_answers[frage]
    if "semester" in frage and "beginnt" in frage:
        return "Das Semester beginnt am 1. Oktober."
    elif "semesterbeitrag" in frage or "bezahlen" in frage:
        return "Der Semesterbeitrag muss bis zum 15. Oktober bezahlt werden."
    else:
        for key, variant_info in question_variants.items():
            if any(keyword in frage for keyword in variant_info["keywords"]):
                return variant_info["response"]
        return "Leider habe ich keine Antwort auf diese Frage."


def get_antwort(frage, all_answers=False):
    frage_lower = frage.lower().rstrip('?')
    if frage_lower in antworten_db:
        antworten = antworten_db[frage_lower]
        if all_answers:
            return "\n".join([f"{i+1}. {antwort}" for i, antwort in enumerate(antworten)])
        return random.choice(antworten)
    else:
        return "Tut mir leid, dazu habe ich keine Antwort."

# Task 20
# Nach der Funktion get_antwort (etwa Zeile 550)


class AntwortTest(unittest.TestCase):
    def test_known_question(self):
        frage = "was ist dein name?"
        antwort = get_antwort(frage)
        self.assertIn(antwort, antworten_db["was ist dein name"])

    def test_unknown_question(self):
        frage = "wie alt bist du?"
        antwort = get_antwort(frage)
        self.assertEqual(antwort, "Tut mir leid, dazu habe ich keine Antwort.")

# weiter


def check_typo(user_input, valid_inputs=["zeit", "hauptstadt", "deutschland", "name", "hörsaal", "bibliothek", "vorlesungssaal"]):
    matches = get_close_matches(user_input, valid_inputs, n=1, cutoff=0.8)
    return matches[0] if matches else None


def find_closest_question(frage, valid_questions):
    matches = get_close_matches(frage.lower().rstrip(
        '?'), valid_questions, n=1, cutoff=0.8)
    return matches[0] if matches else None


def create_sample_csv(filepath):
    sample_data = [
        {"question": "Was ist dein Name?", "answer1": "Ich bin ein Chatbot.",
            "answer2": "Mein Name ist Bot.", "answer3": "Nenn mich Freund!", "answer4": "Bot hier!"},
        {"question": "Was ist die Hauptstadt?", "answer1": "Das hängt vom Land ab!",
            "answer2": "Welches Land meinst du?", "answer3": "Sag mir das Land!", "answer4": ""},
        {"question": "Wie spät ist es?", "answer1": "Schau auf die Uhr!",
            "answer2": "Es ist Zeit!", "answer3": "Weiß nicht, frag die Uhr!", "answer4": ""},
        {"question": "Was kannst du tun?", "answer1": "Fragen beantworten!",
            "answer2": "Witze erzählen!", "answer3": "Wetter checken!", "answer4": ""},
        {"question": "Wer bist du?", "answer1": "Ein Bot!",
            "answer2": "Dein Helfer!", "answer3": "Ein Chatbot!", "answer4": ""},
        {"question": "Was ist Python?", "answer1": "Eine Programmiersprache.",
            "answer2": "Python ist cool!", "answer3": "Für Coding super!", "answer4": ""},
        {"question": "Wie geht's dir?", "answer1": "Mir geht's gut!", "answer2": "Super, danke!",
            "answer3": "Bin ein Bot, mir geht's immer gut!", "answer4": ""},
        {"question": "Was ist ein Algorithmus?", "answer1": "Eine Lösungsanleitung.",
            "answer2": "Schritt-für-Schritt-Plan.", "answer3": "Logik für Probleme.", "answer4": ""},
        {"question": "Erzähl einen Witz!", "answer1": "Warum lacht der Computer? Weil er Bits hat!", "answer2": "Warum sind Geister schlecht im Lügen? Man sieht durch sie!",
            "answer3": "Was sagt ein Mathematiker auf einer Party? Ich bin sin²x + cos²x!", "answer4": ""}
    ]
    try:
        with open(filepath, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(
                file, fieldnames=["question", "answer1", "answer2", "answer3", "answer4"])
            writer.writeheader()
            for row in sample_data:
                writer.writerow(row)
        print(f"{get_time()} Sample-CSV-Datei wurde unter {filepath} erstellt.")
        return True
    except Exception as e:
        print(f"{get_time()} Fehler beim Erstellen der Sample-CSV-Datei: {str(e)}")
        return False


def import_csv(filepath):
    global antworten_db
    new_db = {}
    if not os.path.exists(filepath):
        print(
            f"{get_time()} Datei {filepath} nicht gefunden. Erstelle eine Sample-CSV-Datei...")
        if not create_sample_csv(filepath):
            return False
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or 'question' not in reader.fieldnames:
                print(
                    f"{get_time()} Fehler: CSV-Datei muss eine Spalte 'question' enthalten.")
                return False

            for row in reader:
                question = row['question'].strip().lower().rstrip('?')
                answers = [row.get(f'answer{i}', '').strip() for i in range(
                    1, 5) if row.get(f'answer{i}', '').strip()]
                if answers:
                    new_db[question] = answers

            if len(new_db) < 9:
                print(
                    f"{get_time()} Fehler: CSV-Datei muss mindestens 9 Fragen enthalten.")
                return False

            antworten_db = new_db
            print(
                f"{get_time()} CSV-Datei erfolgreich importiert. Wissensbasis wurde aktualisiert.")
            print(f"{get_time()} Inhalt von antworten_db: {antworten_db}")
            return True
    except Exception as e:
        print(f"{get_time()} Fehler beim Importieren der CSV-Datei: {str(e)}")
        return


def add_question_to_db(question, answer, filepath="sample_data.csv"):
    """Frage und Antwort in antworten_db tun und als CSV speichern"""
    question_clean = question.lower().rstrip('?')
    if question_clean not in antworten_db:
        antworten_db[question_clean] = [answer]
    else:
        if answer not in antworten_db[question_clean]:
            antworten_db[question_clean].append(answer)
    save_to_csv(filepath)
    print(f"{get_time()} Frage hinzugefügt: {question} -> {answer}")


def remove_question_from_db(question, filepath="sample_data.csv"):
    """Frage weg aus antworten_db und CSV neu machen"""
    question_clean = question.lower().rstrip('?')
    if question_clean in antworten_db:
        del antworten_db[question_clean]
        save_to_csv(filepath)
        print(f"{get_time()} Frage entfernt: {question}")
    else:
        print(f"{get_time()} Frage nicht gefunden: {question}")


def save_to_csv(filepath):
    """Antworten_db als CSV-Datei speichern"""
    try:
        with open(filepath, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(
                file, fieldnames=["question", "answer1", "answer2", "answer3", "answer4"])
            writer.writeheader()
            for question, answers in antworten_db.items():
                row = {"question": question}
                for i, answer in enumerate(answers[:4], 1):
                    row[f"answer{i}"] = answer
                for i in range(len(answers), 4):
                    row[f"answer{i+1}"] = ""
                writer.writerow(row)
        print(f"{get_time()} CSV-Datei erfolgreich aktualisiert: {filepath}")
    except Exception as e:
        print(f"{get_time()} Fehler beim Speichern der CSV-Datei: {str(e)}")


def handle_knowledge_base(user_input, command_line=False):
    user_input = user_input.lower().rstrip('?')
    for key, questions in knowledge_base.items():
        if key in user_input or any(user_input == q.lower().rstrip('?') for q in questions):
            if user_input in knowledge_base_answers:
                print(
                    f"{get_time()} Antwort: {knowledge_base_answers[user_input]}")
                return True
            if command_line:
                closest = find_closest_question(
                    user_input, knowledge_base_answers.keys())
                if closest:
                    print(
                        f"{get_time()} Antwort: {knowledge_base_answers[closest]}")
                    return True
            print(f"{get_time()} Meintest du vielleicht eine dieser Fragen?\n")
            for idx, frage in enumerate(questions, 1):
                print(f"{idx}. {frage}")

            try:
                auswahl = int(
                    input(f"{get_time()} Gib die Zahl deiner Wahl ein: "))
                if 1 <= auswahl <= len(questions):
                    selected_frage = questions[auswahl - 1].lower().rstrip('?')
                    print(
                        f"{get_time()} Ausgewählte Frage: {questions[auswahl - 1]}")
                    if selected_frage in knowledge_base_answers:
                        print(
                            f"{get_time()} Antwort: {knowledge_base_answers[selected_frage]}")
                    else:
                        print(
                            f"{get_time()} Leider habe ich keine Antwort auf diese Frage.")
                else:
                    print(f"{get_time()} Ungültige Auswahl.")
            except ValueError:
                print(f"{get_time()} Bitte gib eine gültige Zahl ein.")
            return True
    return False


def handle_complex_questions(user_input, command_line=False):
    if "?" in user_input or " und " in user_input or " oder " in user_input:
        fragen = frage_aufteilen(user_input)
        if len(fragen) > 0:
            print(f"{get_time()} Antworten:")
            for idx, frage in enumerate(fragen, 1):
                frage_clean = frage.lower().rstrip('?')
                if frage_clean in antworten_db:
                    antwort = get_antwort(
                        frage_clean, all_answers=command_line)
                elif frage_clean in knowledge_base_answers:
                    antwort = knowledge_base_answers[frage_clean]
                else:
                    antwort = frage_beantworten(frage)
                print(f"{get_time()} {idx}. {antwort}")
            return True
    return False


def chatbot():
    print(f"{get_time()} Hallo!")
    display_start_symbol(sense)
    print(f"{get_time()} Wie kann ich Ihnen helfen?")

    while True:
        # Temperatur auf SenseHat zeigen, wenn es wartet
        display_temperature(sense)
        time.sleep(5)

        try:
            user_input = input("Du: ").lower().strip()
        except KeyboardInterrupt:
            print(f"\n{get_time()} Auf Wiedersehen!")
            break

        user_input_clean = user_input.rstrip('?')

        # Quiz überprüfen
        if user_input_clean == "trivia":
            if not run_quiz(sense):
                continue
            continue

        location_response = process_user_query(user_input)
        if location_response:
            print(f"\n{get_time()} Antwort:")
            print(location_response)
            print()
            continue

        # Komplexe Fragen prüfen
        if " und " in user_input.lower() or " oder " in user_input.lower():
            print(f"{get_time()} Antwort auf zusammengesetzte Frage:")
            print(process_compound_question(user_input))
            continue

        if user_input == "bye":
            print(f"{get_time()} Auf Wiedersehen!")
            break
        elif user_input_clean in antworten_db:
            print(f"{get_time()} {get_antwort(user_input_clean)}")
        elif user_input in faq:
            print(f"{get_time()} {faq[user_input]()}")
        elif handle_knowledge_base(user_input):
            continue
        elif "wetter" in user_input:
            print(f"{get_time()} {get_weather('Goslar')}")
        elif "uhr" in user_input or "zeit" in user_input:
            print(f"{get_time()} Es ist {get_current_time()} Uhr.")
        elif "hauptstadt" in user_input and "deutschland" in user_input:
            print(f"{get_time()} Die Hauptstadt von Deutschland ist Berlin.")
        elif "hauptstadt" in user_input:
            print(
                f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
        elif "witz" in user_input:
            print(
                f"{get_time()} Warum können Geister so schlecht lügen? Weil man durch sie hindurchsehen kann!")
        elif "algorithmus" in user_input:
            print(
                f"{get_time()} Ein Algorithmus ist eine Schritt-für-Schritt-Anleitung zur Lösung eines Problems.")
        elif "7 mal 8" in user_input or "7 * 8" in user_input:
            print(f"{get_time()} 7 mal 8 ist 56.")
        elif "funktionen" in user_input:
            print(
                f"{get_time()} Ich kann einfache Fragen beantworten, rechnen, Witze erzählen und mehr!")
        elif "helfen" in user_input:
            print(f"{get_time()} Klar! Ich helfe dir gerne. Was möchtest du wissen?")
        elif any(keyword in user_input for keyword in question_variants["bibliothek_hours"]["keywords"]):
            print(
                f"{get_time()} {question_variants['bibliothek_hours']['response']}")
        elif handle_complex_questions(user_input):
            continue
        else:
            typo = check_typo(user_input)
            if typo == "zeit":
                print(
                    f"{get_time()} Meinen Sie 'zeit'? Es ist {get_current_time()} Uhr.")
            elif typo == "hauptstadt":
                print(
                    f"{get_time()} Meinen Sie 'hauptstadt'? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            elif typo == "deutschland":
                print(
                    f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            elif typo == "name":
                print(
                    f"{get_time()} Meinen Sie 'name'? Frag mich 'Was ist dein Name?'!")
            elif typo == "bibliothek":
                print(
                    f"{get_time()} Meinen Sie 'bibliothek'? {question_variants['bibliothek_hours']['response']}")
            else:
                print(
                    f"{get_time()} Das habe ich leider nicht verstanden. Versuch es nochmal!")

# Kommandozeilenargumentه prüfen


if len(sys.argv) > 5 and sys.argv[1] == "--import" and sys.argv[2] == "--filetype" and sys.argv[3] == "CSV" and sys.argv[4] == "--filepath":
    filepath = sys.argv[5]
    if import_csv(filepath):
        chatbot()
elif len(sys.argv) > 2 and sys.argv[1] == "--question":
    default_csv_path = "sample_data.csv"
    import_csv(default_csv_path)

    frage = sys.argv[2].lower().strip()
    frage_clean = frage.rstrip('?')
    all_answers = "--all-answers" in sys.argv

    location_response = process_user_query(frage)
    if location_response:
        print(f"{get_time()} Antwort:")
        print(location_response)
    elif frage_clean in antworten_db:
        print(f"{get_time()} {get_antwort(frage_clean, all_answers)}")
        logging.info(f"Antwort aus antworten_db für Frage: '{frage_clean}'")
    elif frage in faq:
        print(f"{get_time()} {faq[frage]()}")
        logging.info(f"Antwort aus FAQ für Frage: '{frage}'")
    elif handle_knowledge_base(frage, command_line=True):
        logging.info(f"Antwort aus Knowledge Base für Frage: '{frage}'")
        # pass
    elif "wetter" in frage:
        print(f"{get_time()} {get_weather('Goslar')}")
        logging.info("Wetterdaten als Antwort zurückgegeben.")
    elif "uhr" in frage or "zeit" in frage:
        print(f"{get_time()} Es ist {get_current_time()} Uhr.")
        logging.info("Uhrzeit als Antwort zurückgegeben.")
    elif "hauptstadt" in frage and "deutschland" in frage:
        print(f"{get_time()} Die Hauptstadt von Deutschland ist Berlin.")
        logging.info("Antwort zur Hauptstadt von Deutschland gegeben.")
    elif "hauptstadt" in frage:
        print(f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
    elif "witz" in frage:
        print(f"{get_time()} Warum können Geister so schlecht lügen? Weil man durch sie hindurchsehen kann!")
    elif "algorithmus" in frage:
        print(f"{get_time()} Ein Algorithmus ist eine Schritt-für-Schritt-Anleitung zur Lösung eines Problems.")
    elif "7 mal 8" in frage or "7 * 8" in frage:
        print(f"{get_time()} 7 mal 8 ist 56.")
    elif "funktionen" in frage:
        print(
            f"{get_time()} Ich kann einfache Fragen beantworten, rechnen, Witze erzählen und mehr!")
    elif "helfen" in frage:
        print(f"{get_time()} Klar! Ich helfe dir gerne. Was möchtest du wissen?")
    elif any(keyword in frage_clean for keyword in question_variants["bibliothek_hours"]["keywords"]):
        print(
            f"{get_time()} {question_variants['bibliothek_hours']['response']}")
    else:
        typo = check_typo(frage)
        if typo == "zeit":
            print(f"{get_time()} Meinen Sie 'zeit'? Es ist {get_current_time()} Uhr.")
            logging.info("Typo erkannt: 'zeit' → Antwort mit Uhrzeit gegeben")

        elif typo == "hauptstadt":
            print(
                f"{get_time()} Meinen Sie 'hauptstadt'? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            logging.info(
                "Typo erkannt: 'hauptstadt' → Hinweis auf Deutschland gegeben")

        elif typo == "deutschland":
            print(
                f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            logging.info(
                "Typo erkannt: 'deutschland' → Hauptstadt-Hinweis gegeben")

        elif typo == "name":
            print(f"{get_time()} Meinen Sie 'name'? Frag mich 'Was ist dein Name?'!")
            logging.info("Typo erkannt: 'name' → Name-Antwort gegeben")

        elif typo == "bibliothek":
            print(
                f"{get_time()} Meinen Sie 'bibliothek'? {question_variants['bibliothek_hours']['response']}")
            logging.info(
                "Typo erkannt: 'bibliothek' → Bibliothekzeiten-Antwort gegeben")
        else:
            closest = find_closest_question(frage_clean, list(
                antworten_db.keys()) + list(knowledge_base_answers.keys()))
            if closest and closest in antworten_db:
                logging.info(
                    f"Unbekannte Frage '{frage_clean}', nächstgelegene bekannte Frage: '{closest}' aus antworten_db")
                print(
                    f"{get_time()} Meinen Sie '{closest}'? Antwort:\n{get_antwort(closest, all_answers)}")

            elif closest and closest in knowledge_base_answers:
                print(
                    f"{get_time()} Meinen Sie '{closest}'? Antwort: {knowledge_base_answers[closest]}")
            else:
                print(f"{get_time()} Diese Frage kenne ich leider nicht!")
                logging.warning(
                    f"Keine Antwort gefunden für Frage: '{frage_clean}'")

# task 26 & 27


def get_weather_temp():
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["main"]["temp"]
    except Exception:
        return None


def get_local_temp():
    if sense is None:
        return None
    return round(sense.get_temperature(), 1)


def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def update_temperature():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    local_temp = get_local_temp()
    weather_temp = get_weather_temp()

    if local_temp is None or weather_temp is None:
        return

    data = load_data()
    if date_str not in data:
        data[date_str] = {
            "sensor_readings": [{"timestamp": timestamp, "temp": local_temp}],
            "weather": {"min": weather_temp, "max": weather_temp}
        }
    else:
        if "sensor_readings" not in data[date_str]:
            data[date_str]["sensor_readings"] = []
        data[date_str]["sensor_readings"].append(
            {"timestamp": timestamp, "temp": local_temp})
        weather = data[date_str]["weather"]
        weather["min"] = min(weather["min"], weather_temp)
        weather["max"] = max(weather["max"], weather_temp)
    save_data(data)

    # task27


def get_average_sensor_temp(time_slot="all"):
    """Temperatur vom Sensor in drei Tagen im Zeitfenster rechnen"""
    data = load_data()
    today = datetime.now().date()
    temps = []

    if time_slot == "morning":
        start_hour, end_hour = 8, 12  # Morgen: 8:00 bis 12:00
    elif time_slot == "afternoon":
        start_hour, end_hour = 12, 18  # Nachmittag: 12:00 bis 18:00
    else:
        start_hour, end_hour = 0, 24  # Ganzen Tag

    # Temperaturen für die letzten drei Tage sammeln
    for i in range(3):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        if date_str in data and "sensor_readings" in data[date_str]:
            for reading in data[date_str]["sensor_readings"]:
                reading_time = datetime.strptime(
                    reading["timestamp"], "%Y-%m-%d %H:%M:%S")
                if start_hour <= reading_time.hour < end_hour:
                    temps.append(reading["temp"])

    if temps:
        return round(sum(temps) / len(temps), 1)
    return None

# task23 led


def display_temperature(sense):
    """Aktuelle Temperatur auf SenseHat LED-Matrix anzeigen"""
    if sense is None:
        return
    temp = get_local_temp()
    if temp is not None:
        sense.show_message(f"{temp}C", text_colour=[
                           255, 255, 255], scroll_speed=0.05)
    else:
        sense.show_message("No Temp", text_colour=[
                           255, 0, 0], scroll_speed=0.05)

# Task 30


def display_start_symbol(sense):
    """Startzeichen auf SenseHat LED zeigen"""
    if sense is None:
        return
    G = [0, 255, 0]  # Grün
    O = [0, 0, 0]    # Aus
    start_pattern = [
        O, O, G, G, G, O, O, O,
        O, G, O, O, O, G, O, O,
        G, O, O, O, O, O, G, O,
        G, O, O, O, O, O, G, O,
        G, O, O, O, O, O, G, O,
        G, O, O, O, O, O, G, O,
        O, G, O, O, O, G, O, O,
        O, O, G, G, G, O, O, O
    ]
    sense.set_pixels(start_pattern)
    time.sleep(2)
    sense.clear()


def display_game_start_symbol(sense):
    """Startsymbol auf SenseHat LED-Matrix zeigen"""
    if sense is None:
        return
    B = [0, 0, 255]  # Blau
    O = [0, 0, 0]    # Aus
    game_start_pattern = [
        O, O, B, B, B, O, O, O,
        O, B, O, O, O, B, O, O,
        B, O, O, B, O, O, B, O,
        B, O, B, O, B, O, B, O,
        B, O, O, B, O, O, B, O,
        B, O, O, O, O, O, B, O,
        O, B, O, O, O, B, O, O,
        O, O, B, B, B, O, O, O
    ]
    sense.set_pixels(game_start_pattern)
    time.sleep(2)
    sense.clear()


def display_end_symbol(sense, score, total):
    """Endsymbol und Punktzahl auf SenseHat LED-Matrix zeigen"""
    if sense is None:
        return
    R = [255, 0, 0]  # Rot
    O = [0, 0, 0]    # Aus
    end_pattern = [
        O, O, R, R, R, O, O, O,
        O, R, O, O, O, R, O, O,
        R, O, O, O, O, O, R, O,
        R, O, O, O, O, O, R, O,
        R, O, O, O, O, O, R, O,
        R, O, O, O, O, O, R, O,
        O, R, O, O, O, R, O, O,
        O, O, R, R, R, O, O, O
    ]
    sense.set_pixels(end_pattern)
    time.sleep(1)
    sense.show_message(f"{score}/{total}",
                       text_colour=[255, 255, 255], scroll_speed=0.05)
    time.sleep(2)
    sense.clear()


def display_correct_answer(sense, correct):
    """Richtig (✅) oder falsch (❌) auf SenseHat LED-Matrix zeigen"""
    if sense is None:
        return

    # 8x8 Muster für ✅ und ❌ definieren
    G = [0, 255, 0]  # Grün für richtig
    R = [255, 0, 0]  # Rot für falsch
    O = [0, 0, 0]    # Aus
    correct_pattern = [
        O, O, O, O, O, O, O, O,
        O, O, O, G, G, O, O, O,
        O, O, G, G, G, O, O, O,
        O, G, G, G, O, O, O, O,
        O, O, G, G, O, O, O, O,
        O, O, O, G, O, O, O, O,
        O, O, O, O, O, O, O, O,
        O, O, O, O, O, O, O, O
    ]
    incorrect_pattern = [
        O, O, O, O, O, O, O, O,
        O, R, O, O, O, R, O, O,
        O, O, R, O, R, O, O, O,
        O, O, O, R, O, O, O, O,
        O, O, R, O, R, O, O, O,
        O, R, O, O, O, R, O, O,
        O, O, O, O, O, O, O, O,
        O, O, O, O, O, O, O, O
    ]
    sense.set_pixels(correct_pattern if correct else incorrect_pattern)
    time.sleep(2)
    sense.clear()


def run_quiz(sense):
    """Quiz-Spiel mit 10 zufälligen Fragen starten"""
    print(f"{get_time()} Quiz-Spiel gestartet! 10 Fragen warten auf dich. Gib die Nummer der Antwort ein (1-4).")
    display_game_start_symbol(sense)
    print(f"{get_time()} Zum Beenden des Spiels gib 'trivia' ein.")

    selected_questions = random.sample(
        quiz_questions, min(10, len(quiz_questions)))
    score = 0
    total_questions = 10

    for i, q in enumerate(selected_questions, 1):
        print(
            f"\n{get_time()} Frage {i} von {total_questions}: {q['question']}")
        for j, option in enumerate(q['options'], 1):
            print(f"{j}. {option}")
        print(f"{get_time()} Aktueller Punktestand: {score}/{i-1}")

        while True:
            answer = input(
                f"{get_time()} Deine Antwort (1-4 oder 'trivia'): ").strip().lower()
            if answer == "trivia":
                print(f"{get_time()} Quiz beendet! Endstand: {score}/{i-1}")
                display_end_symbol(sense, score, total_questions)
                return False  # Zurück zum Chatbot
            if answer in ["1", "2", "3", "4"]:
                user_choice = q['options'][int(answer) - 1]
                correct = user_choice == q['correct']
                if correct:
                    score += 1
                    print(f"{get_time()} Richtig! ✅")
                else:
                    print(
                        f"{get_time()} Falsch! ❌ Die richtige Antwort ist: {q['correct']}")
                display_correct_answer(sense, correct)
                break
            else:
                print(
                    f"{get_time()} Bitte gib eine gültige Antwort (1-4) oder 'trivia' ein.")

        time.sleep(1)

    print(f"{get_time()} Quiz beendet! Endstand: {score}/{total_questions}")
    return True  # Quiz ist fertig
    data = load_data()
    if date_str not in data:
        data[date_str] = {
            "sensor_readings": [{"timestamp": timestamp, "temp": local_temp}],
            "weather": {"min": weather_temp, "max": weather_temp}
        }
    else:
        if "sensor_readings" not in data[date_str]:
            data[date_str]["sensor_readings"] = []
        data[date_str]["sensor_readings"].append(
            {"timestamp": timestamp, "temp": local_temp})
        weather = data[date_str]["weather"]
        weather["min"] = min(weather["min"], weather_temp)
        weather["max"] = max(weather["max"], weather_temp)
    save_data(data)


def show_comparison():
    data = load_data()
    today = datetime.now().date()

    print(f"{get_time()} {'Date':<12} | {'Sensor ΔT (°C)':<16} | {'Forecast ΔT (°C)'}")
    print(f"{get_time()} {'-' * 50}")

    for i in range(3):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        if date_str in data:
            s = data[date_str]["sensor"]
            w = data[date_str]["weather"]
            sensor_delta = round(s["max"] - s["min"], 1)
            weather_delta = round(w["max"] - w["min"], 1)
            print(
                f"{get_time()} {date_str} | {sensor_delta:^16} | {weather_delta:^20}")
        else:
            print(f"{get_time()} {date_str} | {'No data':<16} | {'No data'}")


def run_temperature_monitoring():
    """Temperatur im Hintergrund überwachen"""
    schedule.every(5).minutes.do(update_temperature)
    while True:
        schedule.run_pending()
        time.sleep(1)

# funktion task 18


def remove_answer_from_question(question, answer, csv_path):
    question_clean = question.lower().strip().rstrip("?")
    answer_clean = answer.strip()

    if question_clean in antworten_db:
        if answer_clean in antworten_db[question_clean]:
            antworten_db[question_clean].remove(answer_clean)
            if not antworten_db[question_clean]:
                del antworten_db[question_clean]
        else:
            print(
                f"{get_time()} Antwort '{answer_clean}' nicht gefunden für Frage '{question_clean}'.")
            return

        # Änderungen in CSV-Datei speichern

        save_to_csv(csv_path)
        print(
            f"{get_time()} Antwort '{answer_clean}' wurde von der Frage '{question_clean}' entfernt.")
    else:
        print(f"{get_time()} Frage '{question_clean}' nicht gefunden.")

# -- Hauptteil app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chatbot and Temperature Comparison Tool")
    parser.add_argument("--import-csv", action="store_true",
                        help="Import CSV file")
    parser.add_argument(
        "--filetype", choices=["CSV"], help="File type to import")
    parser.add_argument("--filepath", help="Path to the CSV file")
    parser.add_argument("--question", help="Ask a single question")
    parser.add_argument("--all-answers", action="store_true",
                        help="Show all possible answers for a question")
    parser.add_argument("--compare", action="store_true",
                        help="Show 3-day temperature comparison")
    parser.add_argument("--list-questions", action="store_true",
                        help="List all questions in the knowledge base")
    parser.add_argument('--add', action='store_true',
                        help="Add a question to the knowledge base")
    parser.add_argument('--remove', action='store_true',
                        help="Remove a question or an answer from the knowledge base")
    parser.add_argument(
        '--answer', help="Answer for the question to add or remove")
    parser.add_argument('--log', action='store_true',
                        help="Aktiviere Logging in Datei")
    parser.add_argument('--level', choices=['INFO', 'WARNING'],
                        default='WARNING', help="Logging-Level (Standard: WARNING)")
    parser.add_argument('--debug', action='store_true',
                        help="Enable debug mode")
    parser.add_argument('--run-tests', action='store_true',
                        help="Run unit tests")
    parser.add_argument('--temp-diff', action='store_true',
                        help="Show temperature difference")

    # Test Task 22

    args = parser.parse_args()

    setup_logger(args.log, args.level)
    logging.info(f"Programm gestartet mit Log-Level: {args.level}")

    default_csv_path = "sample_data.csv"
    import_csv(default_csv_path)

    # task 20

    if args.debug:
        print(f"{get_time()} [DEBUG] Debug mode is ON.")

    if args.run_tests:
        unittest.main(argv=['ignored'], exit=False)

    if args.list_questions:
        list_all_questions()

    elif args.import_csv and args.filetype == "CSV" and args.filepath:
        if import_csv(args.filepath):
            logging.info(f"Starte Import der CSV-Datei: {args.filepath}")
            logging.info(f"CSV importiert von Datei: {args.filepath}")
            logging.info("CSV Import abgeschlossen")
            threading.Thread(target=run_temperature_monitoring,
                             daemon=True).start()
            chatbot()

    elif args.add and args.question and args.answer:
        add_question_to_db(args.question, args.answer, default_csv_path)
        logging.info(
            f"Aufruf: Frage hinzufügen: '{args.question}' mit Antwort '{args.answer}'")
        print(f"{get_time()} Inhalt von antworten_db nach Hinzufügen: {antworten_db}")

    elif args.remove and args.question and args.answer:
        remove_answer_from_question(
            args.question, args.answer, default_csv_path)
        logging.info(
            f"Antwort entfernt: '{args.answer}' von Frage: '{args.question}'")
        print(
            f"{get_time()} Inhalt von antworten_db nach Entfernen der Antwort: {antworten_db}")

    elif args.remove and args.question and not args.answer:
        remove_question_from_db(args.question, default_csv_path)
        logging.info(f"Frage entfernt: '{args.question}'")
        print(f"{get_time()} Frage '{args.question}' wurde entfernt.")
        print(f"{get_time()} Inhalt von antworten_db nach Entfernen: {antworten_db}")

    elif args.question:
        frage = args.question.lower().strip()
        frage_clean = frage.rstrip('?')
        all_answers = args.all_answers
        location_response = process_user_query(frage)

        if location_response:
            print(f"{get_time()} Antwort:")
            print(location_response)
        elif frage_clean in antworten_db:
            print(f"{get_time()} {get_antwort(frage_clean, all_answers)}")
            logging.info(
                f"Antwort gegeben: Frage '{frage_clean}' -> {get_antwort(frage_clean, all_answers)}")
        elif frage in faq:
            print(f"{get_time()} {faq[frage]()}")

        elif handle_knowledge_base(frage, command_line=True):
            pass
        elif "wetter" in frage:
            print(f"{get_time()} {get_weather('Goslar')}")
        elif "uhr" in frage or "zeit" in frage:
            print(f"{get_time()} Es ist {get_current_time()} Uhr.")
        elif "hauptstadt" in frage and "deutschland" in frage:
            print(f"{get_time()} Die Hauptstadt von Deutschland ist Berlin.")
        elif "hauptstadt" in frage:
            print(
                f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
        elif "witz" in frage:
            print(
                f"{get_time()} Warum können Geister so schlecht lügen? Weil man durch sie hindurchsehen kann!")
        elif "algorithmus" in frage:
            print(
                f"{get_time()} Ein Algorithmus ist eine Schritt-für-Schritt-Anleitung zur Lösung eines Problems.")
        elif "7 mal 8" in frage or "7 * 8" in frage:
            print(f"{get_time()} 7 mal 8 ist 56.")
        elif "funktionen" in frage:
            print(
                f"{get_time()} Ich kann einfache Fragen beantworten, rechnen, Witze erzählen und mehr!")
        elif "helfen" in frage:
            print(f"{get_time()} Klar! Ich helfe dir gerne. Was möchtest du wissen؟")
        elif "compare" in frage or "temperature" in frage:
            show_comparison()
        elif any(keyword in frage_clean for keyword in question_variants["bibliothek_hours"]["keywords"]):
            print(
                f"{get_time()} {question_variants['bibliothek_hours']['response']}")
        else:
            typo = check_typo(frage)
            if typo == "zeit":
                print(
                    f"{get_time()} Meinen Sie 'zeit'? Es ist {get_current_time()} Uhr.")
            elif typo == "hauptstadt":
                print(
                    f"{get_time()} Meinen Sie 'hauptstadt'? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            elif typo == "deutschland":
                print(
                    f"{get_time()} Meinen Sie die Hauptstadt von Deutschland? Bitte geben Sie 'Hauptstadt Deutschland' ein.")
            elif typo == "name":
                print(
                    f"{get_time()} Meinen Sie 'name'? Frag mich 'Was ist dein Name?'!")
            elif typo == "bibliothek":
                print(
                    f"{get_time()} Meinen Sie 'bibliothek'? {question_variants['bibliothek_hours']['response']}")
            else:
                closest = find_closest_question(frage_clean, list(
                    antworten_db.keys()) + list(knowledge_base_answers.keys()))
                if closest and closest in antworten_db:
                    logging.info(
                        f"Unbekannte Frage '{frage_clean}', nächstgelegene bekannte Frage: '{closest}' aus antworten_db")
                    print(
                        f"{get_time()} Meinen Sie '{closest}'? Antwort:\n{get_antwort(closest, all_answers)}")
                elif closest and closest in knowledge_base_answers:
                    print(
                        f"{get_time()} Meinen Sie '{closest}'? Antwort: {knowledge_base_answers[closest]}")
                else:
                    print(f"{get_time()} Diese Frage kenne ich leider nicht!")
                    logging.warning(
                        f"Keine Antwort gefunden für Frage: '{frage_clean}'")

    elif args.compare:
        show_comparison()

    else:
        threading.Thread(target=run_temperature_monitoring,
                         daemon=True).start()
        chatbot()
