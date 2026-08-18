#!/usr/bin/env python3
"""
Génère des fichiers .ics à partir des événements du club sur Sportcorico :
un fichier avec tout (conservé pour les abonnés existants, plus proposé
sur la page), un avec uniquement les entraînements, un avec les matchs
et autres événements.

Auth : lit le token depuis la variable d'environnement SPORTCORICO_AUTH
       (format attendu : "Bearer xxxxxxx...")
       -> en local : export SPORTCORICO_AUTH="Bearer xxxx"
       -> en CI     : GitHub Secret du même nom, injecté par le workflow

Usage :
    python3 fetch_and_convert.py
"""
import os
from datetime import datetime

from icalendar import Calendar, Event, vText

from sportcorico import (
    PARIS,
    build_description,
    build_title,
    fetch_events,
    get_auth_header,
    is_training,
    iter_valid_events,
)

OUTPUTS = {
    "docs/fc2m-entrainements.ics": ("FC2M - Entraînements", is_training),
    "docs/fc2m-matchs.ics": ("FC2M - Matchs & événements", lambda evt: not is_training(evt)),
}


def convert(events, calendar_name, event_filter):
    cal = Calendar()
    cal.add("prodid", "-//FC2M Sportcorico Sync//fr//")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-timezone", "Europe/Paris")
    cal.add("refresh-interval;value=duration", "PT15M")
    cal.add("x-published-ttl", "PT15M")

    for evt, begin, end in iter_valid_events(events):
        if not event_filter(evt):
            continue

        e = Event()
        e.add("uid", f"sportcorico-{evt['id']}@fc2m")
        e.add("summary", vText(build_title(evt)))
        e.add("dtstart", begin)
        e.add("dtend", end)
        e.add("dtstamp", datetime.now(tz=PARIS))
        if evt.get("location"):
            e.add("location", vText(evt["location"]))
        e.add("description", vText(build_description(evt)))
        e.add("status", "CONFIRMED")

        cal.add_component(e)

    return cal


def main():
    auth_header = get_auth_header()
    events = fetch_events(auth_header)

    for output_path, (calendar_name, event_filter) in OUTPUTS.items():
        cal = convert(events, calendar_name, event_filter)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(cal.to_ical())
        print(f"OK : {output_path} généré")


if __name__ == "__main__":
    main()
