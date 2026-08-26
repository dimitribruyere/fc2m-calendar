"""Fonctions partagées pour interroger l'API Sportcorico et normaliser les événements."""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

API_BASE = "https://api.sportcorico.com/api/events/v3"

# Fenêtre glissante : on récupère le passé récent (pour voir les annulations
# de dernière minute passer proprement) et le futur lointain (saison en cours)
DAYS_BEFORE = 14
DAYS_AFTER = 365

DEFAULT_DURATION = {
    "training": timedelta(hours=1, minutes=30),
    "match": timedelta(hours=2),
    "event": timedelta(hours=2),
}


def get_auth_header():
    token = os.environ.get("SPORTCORICO_AUTH")
    if not token:
        print("ERREUR : variable d'environnement SPORTCORICO_AUTH absente", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_events(auth_header):
    today = datetime.now(tz=PARIS).date()
    start = today - timedelta(days=DAYS_BEFORE)
    end = today + timedelta(days=DAYS_AFTER)

    all_events = []
    page = 1
    while True:
        url = (
            f"{API_BASE}?club&group"
            f"&start_at={start.isoformat()}&end_at={end.isoformat()}"
            f"&per_page&page={page}&web_calendar=1"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": auth_header,
            "Accept": "application/json",
            "User-Agent": "FC2M-Calendar-Sync/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"ERREUR HTTP {e.code} lors de l'appel à l'API Sportcorico", file=sys.stderr)
            print("-> le token a peut-être expiré, il faut le renouveler dans les secrets GitHub", file=sys.stderr)
            sys.exit(1)

        events = data.get("events", [])
        all_events.extend(events)

        # Pagination : on s'arrête si la page est vide ou incomplète.
        # (à ajuster si l'API renvoie un champ "last_page" / "total" explicite —
        #  à vérifier une fois en conditions réelles, voir note plus bas)
        if not events or len(events) < 1:
            break
        if page > 20:  # garde-fou anti-boucle infinie
            break
        # Sportcorico ne semble pas paginer sur une fenêtre d'un mois classique ;
        # si per_page n'est pas fourni, la 1ère page contient tout -> on sort.
        break

    return all_events


def parse_dt(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=PARIS)


def build_title(evt):
    if evt["event_type"] == "match" and evt.get("match_or_platter"):
        m = evt["match_or_platter"]["match"]
        home = (m.get("home_team_custom_name_for_event") or m.get("home_team_name")).replace("SENIORS", "FC2M")
        away = (m.get("outside_team_custom_name_for_event") or m.get("outside_team_name")).replace("SENIORS", "FC2M")
        score = ""
        if m.get("status") == "Terminé" and m.get("home_score") is not None:
            score = f" ({m['home_score']} - {m['outside_score']})"
        return f"⚽ {home} vs {away}{score}"

    icons = {"training": "🏃", "event": "📌"}
    icon = icons.get(evt["event_type"], "📅")
    return f"{icon} {evt['title']}"


def build_description(evt):
    lines = []
    if evt.get("description"):
        lines.append(evt["description"])
    if evt.get("group") and evt["group"].get("name"):
        lines.append(f"Groupe : {evt['group']['name']}")
    if evt.get("meet_at"):
        meet = parse_dt(evt["meet_at"])
        lines.append(f"Rendez-vous : {meet.strftime('%H:%M')}")
    if evt["event_type"] == "match" and evt.get("match_or_platter"):
        m = evt["match_or_platter"]["match"]
        if m.get("championship_name"):
            lines.append(m["championship_name"])
        if m.get("round"):
            lines.append(f"{m.get('day', '')} (tour {m['round']})".strip())
    lines.append(f"Source : Sportcorico (id {evt['id']})")
    return "\n".join(lines)


def iter_valid_events(events):
    """Filtre doublons/événements annulés et calcule les horaires de début/fin."""
    seen_ids = set()
    for evt in events:
        if evt["id"] in seen_ids:
            continue
        seen_ids.add(evt["id"])

        if evt.get("canceled_at"):
            continue

        begin = parse_dt(evt["begin_at"])
        if begin is None:
            continue

        end = parse_dt(evt.get("ending_at"))
        if end is None or end <= begin:
            end = begin + DEFAULT_DURATION.get(evt["event_type"], timedelta(hours=2))

        yield evt, begin, end


def is_training(evt):
    return evt["event_type"] == "training"
