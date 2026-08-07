#!/usr/bin/env python3
"""
Fetch MLB + NFL moneylines from Lumify (https://lumify.ai) and write CSV snapshots.

Betclic's public offering API is blocked (see exploration.py / README). Lumify is a
hosted sports intelligence API with schedules, odds, and line-movement history —
useful for the short-term goal of tracking moneyline movement over time.

Setup:
  1. Get a free instant key (no signup): https://lumify.ai/docs/ai
  2. export LUMIFY_API_KEY=lmfy-...
  3. python scrape-lumify-games.py

Requires: requests, pandas
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from time import gmtime, strftime

import pandas as pd
import requests

BASE_URL = os.environ.get("LUMIFY_BASE_URL", "https://lumify.ai").rstrip("/")
API_KEY = os.environ.get("LUMIFY_API_KEY", "").strip()
SPORTS = ("mlb", "nfl")
# Multi-book costs 2 credits/event; default pinnacle alone is 1. Override with e.g. "all".
BOOKMAKER = os.environ.get("LUMIFY_BOOKMAKER", "pinnacle,draftkings,fanduel")


def _headers() -> dict:
    if not API_KEY:
        raise SystemExit(
            "Missing LUMIFY_API_KEY. Get a free instant key at "
            "https://lumify.ai/docs/ai and export LUMIFY_API_KEY=lmfy-..."
        )
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "User-Agent": "rafabelokurows-sports-odds/lumify",
    }


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=60)
    if resp.status_code == 401:
        raise SystemExit("Lumify auth failed (401). Check LUMIFY_API_KEY.")
    resp.raise_for_status()
    return resp.json()


def list_event_ids(sport: str) -> list[int]:
    """Collect event IDs for scheduled + in-progress games."""
    ids: list[int] = []
    for status in ("scheduled", "inprogress"):
        after_id = None
        while True:
            params = {"sport": sport, "status": status, "limit": 50}
            if after_id is not None:
                params["after_id"] = after_id
            payload = _get("/v1/events", params)
            batch = payload.get("events") or []
            for ev in batch:
                eid = ev.get("id")
                if eid is not None:
                    ids.append(int(eid))
            after_id = payload.get("next_after_id")
            if not batch or after_id is None:
                break
    return ids


def _participants(event: dict) -> tuple[str, str]:
    home = away = ""
    for p in event.get("participants") or []:
        role = (p.get("role") or "").lower()
        name = (
            (p.get("team") or {}).get("name")
            or (p.get("player") or {}).get("name")
            or p.get("name")
            or ""
        )
        if role == "home":
            home = name
        elif role == "away":
            away = name
    return home, away


def fetch_event_odds_rows(event_id: int, sport: str) -> list[dict]:
    """One compound call: event detail + odds (saves a round trip)."""
    event = _get(
        f"/v1/events/{event_id}",
        {"include_odds": "true", "bookmaker": BOOKMAKER},
    )
    home, away = _participants(event)
    start = event.get("starts_at") or event.get("scheduled_start_at")
    odds_payload = event.get("odds") or {}
    if odds_payload.get("available") is False and not odds_payload.get("bookmakers"):
        return []

    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    for book in odds_payload.get("bookmakers") or []:
        bookmaker = book.get("bookmaker") or ""
        captured_at = book.get("captured_at") or odds_payload.get("last_updated")
        for market in book.get("markets") or []:
            market_key = market.get("key") or market.get("label") or ""
            for outcome in market.get("outcomes") or []:
                rows.append(
                    {
                        "event_id": event_id,
                        "sport": sport,
                        "home": home,
                        "away": away,
                        "date": start,
                        "status": event.get("status"),
                        "bookmaker": bookmaker,
                        "market": market_key,
                        "outcome": outcome.get("outcome"),
                        "odds": outcome.get("price"),
                        "line": outcome.get("point"),
                        "captured_at": captured_at,
                        "scraped_at": scraped_at,
                    }
                )
    return rows


def scrape_sport(sport: str) -> pd.DataFrame:
    ids = list_event_ids(sport)
    print(f"  {len(ids)} events for {sport}")
    rows: list[dict] = []
    for event_id in ids:
        try:
            rows.extend(fetch_event_odds_rows(event_id, sport))
        except requests.HTTPError as exc:
            print(f"warn: event {event_id} failed: {exc}", file=sys.stderr)
    return pd.DataFrame(rows)


def main() -> None:
    stamp = strftime("%Y%m%d%H%M", gmtime())
    out_dir = os.path.join("data", "lumify")
    os.makedirs(out_dir, exist_ok=True)

    frames = []
    for sport in SPORTS:
        print(f"Fetching {sport} from Lumify…")
        df = scrape_sport(sport)
        if df.empty:
            print(f"  no odds rows for {sport}")
            continue
        path = os.path.join(out_dir, f"{sport}_games_{stamp}.csv")
        df.to_csv(path, index=False)
        print(f"  wrote {len(df)} rows → {path}")
        frames.append(df)

    if not frames:
        print("No odds rows returned. Check key / season window, or try again later.")
        sys.exit(0)

    combined = pd.concat(frames, ignore_index=True)
    combined_path = os.path.join(out_dir, f"all_games_{stamp}.csv")
    combined.to_csv(combined_path, index=False)
    print(f"wrote combined {len(combined)} rows → {combined_path}")


if __name__ == "__main__":
    main()
