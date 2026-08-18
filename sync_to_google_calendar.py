#!/usr/bin/env python3
"""
Pousse les événements du club (Sportcorico) dans des agendas Google Calendar
dédiés, via l'API Calendar. L'authentification passe par la fédération
d'identité de charge de travail (aucune clé de compte de service stockée) :
en CI, l'action google-github-actions/auth prépare les identifiants avant
que ce script ne s'exécute.

Variables d'environnement requises :
    SPORTCORICO_AUTH             -> token Sportcorico (voir sportcorico.py)
    GOOGLE_CALENDAR_ID_TRAININGS -> agenda entraînements uniquement
    GOOGLE_CALENDAR_ID_MATCHES   -> agenda matchs & autres événements

Usage :
    python3 sync_to_google_calendar.py
"""
import os
import sys

import google.auth
from googleapiclient.discovery import build

from sportcorico import build_description, build_title, fetch_events, get_auth_header, is_training, iter_valid_events

SPORTCORICO_ID_KEY = "sportcoricoId"

TARGETS = [
    ("GOOGLE_CALENDAR_ID_TRAININGS", is_training),
    ("GOOGLE_CALENDAR_ID_MATCHES", lambda evt: not is_training(evt)),
]


def get_calendar_id(env_var):
    calendar_id = os.environ.get(env_var)
    if not calendar_id:
        print(f"ERREUR : variable d'environnement {env_var} absente", file=sys.stderr)
        sys.exit(1)
    return calendar_id


def build_event_body(evt, begin, end):
    body = {
        "summary": build_title(evt),
        "description": build_description(evt),
        "start": {"dateTime": begin.isoformat(), "timeZone": "Europe/Paris"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Paris"},
        "extendedProperties": {"private": {SPORTCORICO_ID_KEY: str(evt["id"])}},
    }
    if evt.get("location"):
        body["location"] = evt["location"]
    return body


def list_synced_events(service, calendar_id):
    """Renvoie {sportcoricoId: event Google} pour tout ce que ce script a déjà poussé."""
    existing = {}
    page_token = None
    while True:
        resp = service.events().list(
            calendarId=calendar_id,
            singleEvents=True,
            maxResults=2500,
            pageToken=page_token,
        ).execute()
        for event in resp.get("items", []):
            if event.get("status") == "cancelled":
                continue
            sportcorico_id = event.get("extendedProperties", {}).get("private", {}).get(SPORTCORICO_ID_KEY)
            if sportcorico_id:
                existing[sportcorico_id] = event
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return existing


def sync(service, calendar_id, events, event_filter):
    existing = list_synced_events(service, calendar_id)
    seen_ids = set()
    created = updated = deleted = 0

    for evt, begin, end in iter_valid_events(events):
        if not event_filter(evt):
            continue

        sportcorico_id = str(evt["id"])
        seen_ids.add(sportcorico_id)
        body = build_event_body(evt, begin, end)

        if sportcorico_id in existing:
            service.events().update(
                calendarId=calendar_id,
                eventId=existing[sportcorico_id]["id"],
                body=body,
            ).execute()
            updated += 1
        else:
            service.events().insert(calendarId=calendar_id, body=body).execute()
            created += 1

    for sportcorico_id, event in existing.items():
        if sportcorico_id not in seen_ids:
            service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            deleted += 1

    return created, updated, deleted


def main():
    auth_header = get_auth_header()
    events = fetch_events(auth_header)

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/calendar"])
    service = build("calendar", "v3", credentials=credentials)

    for env_var, event_filter in TARGETS:
        calendar_id = get_calendar_id(env_var)
        created, updated, deleted = sync(service, calendar_id, events, event_filter)
        print(f"OK ({env_var}) : {created} créés, {updated} mis à jour, {deleted} supprimés")


if __name__ == "__main__":
    main()
