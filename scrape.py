import json
import re
import sys
import requests
from bs4 import BeautifulSoup

MATCHES_CENTER_URL = "https://www.yallakora.com/matches-center"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

STATUS_MAP = {
    "finish": "FINISHED",
    "now": "LIVE",
    "future": "SCHEDULED",
}


def clean_text(el):
    if el is None:
        return None
    text = el.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def fix_logo_url(url):
    if url is None:
        return None
    return url.replace("\\", "/")


def parse_matches_center_html(html):
    soup = BeautifulSoup(html, "html.parser")
    tournaments = []

    for card in soup.select(".matchCard"):
        tour_title_el = card.select_one(".tourTitle h2")
        tour_link_el = card.select_one(".tourTitle")
        tour_logo_el = card.select_one(".tourTitle img")

        tournament = {
            "name": clean_text(tour_title_el),
            "url": tour_link_el.get("href") if tour_link_el else None,
            "logo": fix_logo_url(tour_logo_el.get("src")) if tour_logo_el else None,
            "matches": [],
        }

        for item in card.select(".item.liItem"):
            classes = item.get("class", [])
            status_key = next((c for c in classes if c in STATUS_MAP), None)
            status_label_el = item.select_one(".matchStatus span")

            round_el = item.select_one(".topData .date")
            channel_el = item.select_one(".channel")
            time_el = item.select_one(".MResult .time")

            team_a_name_el = item.select_one(".teams.teamA p")
            team_a_logo_el = item.select_one(".teams.teamA img")
            team_b_name_el = item.select_one(".teams.teamB p")
            team_b_logo_el = item.select_one(".teams.teamB img")

            scores = item.select(".MResult .score")
            score_a = clean_text(scores[0]) if len(scores) > 0 else None
            score_b = clean_text(scores[1]) if len(scores) > 1 else None
            score_a = None if score_a == "-" else score_a
            score_b = None if score_b == "-" else score_b

            link_el = item.select_one("a[href]")

            match_url = link_el.get("href") if link_el else None
            if match_url and match_url.startswith("/"):
                match_url = "https://www.yallakora.com" + match_url

            match = {
                "match_id": item.get("livescorematchid"),
                "round": clean_text(round_el),
                "status": STATUS_MAP.get(status_key, "UNKNOWN"),
                "status_label": clean_text(status_label_el),
                "time": clean_text(time_el),
                "channel": clean_text(channel_el),
                "team_a": {
                    "name": clean_text(team_a_name_el),
                    "logo": fix_logo_url(team_a_logo_el.get("src")) if team_a_logo_el else None,
                },
                "team_b": {
                    "name": clean_text(team_b_name_el),
                    "logo": fix_logo_url(team_b_logo_el.get("src")) if team_b_logo_el else None,
                },
                "score_a": score_a,
                "score_b": score_b,
                "match_url": match_url,
            }
            tournament["matches"].append(match)

        tournaments.append(tournament)

    return tournaments


def main():
    resp = requests.get(MATCHES_CENTER_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = parse_matches_center_html(resp.text)

    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(t["matches"]) for t in data)
    print(f"Tournaments: {len(data)}")
    print(f"Total matches: {total}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Scrape failed: {e}")
        sys.exit(1)
