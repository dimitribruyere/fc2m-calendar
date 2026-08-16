#!/usr/bin/env python3
"""
Génère un fichier .ics à partir des événements du club sur Sportcorico.

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

from sportcorico import PARIS, build_description, build_title, fetch_events, get_auth_header, iter_valid_events

OUTPUT_PATH = "docs/fc2m.ics"


def convert(events, calendar_name="FC2M - Sportcorico"):
    cal = Calendar()
    cal.add("prodid", "-//FC2M Sportcorico Sync//fr//")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-timezone", "Europe/Paris")
    cal.add("refresh-interval;value=duration", "PT15M")
    cal.add("x-published-ttl", "PT15M")

    for evt, begin, end in iter_valid_events(events):
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
    cal = convert(events)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        f.write(cal.to_ical())

    print(f"OK : {len(events)} événements écrits dans {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
