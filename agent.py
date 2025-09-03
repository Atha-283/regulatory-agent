import requests
from bs4 import BeautifulSoup
import smtplib, ssl
from email.message import EmailMessage
import openai
import json
import os

# Datei für gespeicherte Links
SEEN_FILE = "seen_items.json"

# Deine Keywords
KEYWORDS = [
    "Vorabpauschale","Investment","Fonds","Fond","ETC","ETFs",
    "Abgeltungssteuer", "CSDR", "FATCA", "CRS", "AWV",
    "Kirchensteuer", "Quellensteuer", "Steuerbescheinigung"
]

# Feed-URLs (Beispiele, ggf. anpassen)
FEEDS = {
    "Tagesschau": "https://www.tagesschau.de/xml/rss2",
    "BMF": "https://www.bundesfinanzministerium.de/Content/DE/RSS/ffrss.xml",
    "ESMA": "https://www.esma.europa.eu/rss.xml",
    "BaFin": "https://www.bafin.de/DE/Service/TopNavigation/RSS/_function/rssnewsfeed.xml",
    "BZsT": "https://www.bundesfinanzministerium.de/SiteGlobals/Functions/RSSFeed/DE/Aktuelles/RSSAktuelles.xml",
    "BMF zu Steuern": "https://www.bundesfinanzministerium.de/SiteGlobals/Functions/RSSFeed/DE/Steuern/RSSSteuern.xml",
    "BMF Investmetn": "https://www.bundesfinanzministerium.de/Web/DE/Themen/Steuern/Steuerarten/Investmentsteuer/investmentsteuer.html",
}

# -------------------------------
# Funktionen zum Laden / Speichern der gesehenen Links
# -------------------------------
def load_seen_links():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_links(links):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(links), f)

# -------------------------------
# News-Feeds auslesen und filtern
# -------------------------------
def fetch_news_from_feed(url, seen_links):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml-xml")
    items = soup.find_all("item")
    items = filter_news(items)

    news = []
    new_links = set()

    for item in items:
        titel = item.title.text.strip()
        link = item.link.text.strip()
        if link not in seen_links:
            news.append(f"- {titel}\n  {link}")
            new_links.add(link)

    return news, new_links

def filter_news(items):
    filtered = []
    for item in items:
        titel = item.title.text.lower()
        beschreibung = item.description.text.lower() if item.description else ""
        text = titel + " " + beschreibung
        print(f"Überprüfe Artikel: {titel[:50]}...")
        if any(keyword.lower() in text for keyword in KEYWORDS):
            filtered.append(item)
    print(f"Gefilterte Artikel: {len(filtered)}")
    return filtered

# -------------------------------
# Alle Feeds durchlaufen
# -------------------------------
def fetch_all_news():
    seen_links = load_seen_links()
    all_news = []
    all_new_links = set()

    for name, url in FEEDS.items():
        try:
            feed_news, new_links = fetch_news_from_feed(url, seen_links)
            if feed_news:
                all_news.append(f"## News von {name} ##")
                all_news.extend(feed_news)
                all_news.append("")  # Leerzeile
                all_new_links.update(new_links)
        except Exception as e:
            all_news.append(f"## Fehler bei Feed {name}: {e}")

    return "\n".join(all_news) if all_news else "❌ Keine relevanten News gefunden.", seen_links, all_new_links

# -------------------------------
# OpenAI Zusammenfassung
# -------------------------------
openai.api_key = os.environ.get("OPENAI_API_KEY")  # sicherer Weg

def summarize_news(text):
    prompt = f"Fasse den folgenden Text kurz zusammen und gib Handlungsempfehlungen für Investmentbesteuerung:\n\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return response.choices[0].message.content

# -------------------------------
# E-Mail versenden
# -------------------------------
def send_mail(subject, body):
    print("Bereite E-Mail vor …")
    msg = EmailMessage()
    msg["From"] = "chatzopoulou8@gmail.com"
    msg["To"] = "athanasia.chatzopoulou@gmx.de"
    msg["Subject"] = subject
    msg.set_content(body or "Kein Inhalt übermittelt")

    print(f"🧾 Mailinhalt:\n{body}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login("chatzopoulou8@gmail.com", os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)
    print("✅ Nachricht erfolgreich gesendet!")

# -------------------------------
# Hauptlogik
# -------------------------------
if __name__ == "__main__":
    news, seen_links, all_new_links = fetch_all_news()

    body = news  # Direkt die gefilterten Artikel senden – ohne Zusammenfassung
    send_mail("🧠 Neue BaFin-News", body)
    print("Mail gesendet.")

    # Neue Links speichern
    seen_links.update(all_new_links)
    save_seen_links(seen_links)
