import re
import sys
import requests
from datetime import datetime, timezone

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def find_team(name):
    resp = requests.get(f"{BASE}/teams", params={"limit": 32})
    resp.raise_for_status()
    data = resp.json()
    teams = data["sports"][0]["leagues"][0]["teams"]
    for entry in teams:
        team = entry.get("team", entry)
        if team.get("displayName", "").lower() == name.lower():
            return team
    print(f"Error: No team found matching '{name}'")
    return None


def get_standing(team):
    team_id = str(team["id"])
    try:
        resp = requests.get(f"{BASE}/teams/{team_id}")
        resp.raise_for_status()
        summary = resp.json().get("team", {}).get("standingSummary", "")
        if summary:
            return {"standing": summary}
        print(f"Error: Standing data not found for '{team.get('displayName', team_id)}'")
        return None
    except requests.HTTPError as e:
        print(f"Error: Failed to fetch standing for '{team.get('displayName', team_id)}' ({e})")
        return None
    except (KeyError, ValueError):
        print(f"Error: Unexpected response format when fetching standing for '{team.get('displayName', team_id)}'")
        return None


def get_record(team):
    team_id = str(team["id"])
    try:
        resp = requests.get(f"{BASE}/teams/{team_id}/record")
        resp.raise_for_status()
        items = resp.json().get("items", [])
        for item in items:
            if item.get("type") == "total":
                summary = item.get("summary", "")
                if summary:
                    return {"record": summary}
        print(f"Error: Record data not found for team '{team.get('displayName', team_id)}'")
        return None
    except requests.HTTPError as e:
        print(f"Error: Failed to fetch record for '{team.get('displayName', team_id)}' ({e})")
        return None
    except (KeyError, ValueError):
        print(f"Error: Unexpected response format when fetching record for '{team.get('displayName', team_id)}'")
        return None


def get_top_scorer(team):
    team_id = str(team["id"])
    try:
        resp = requests.get(f"{BASE}/teams/{team_id}/schedule")
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except requests.HTTPError as e:
        print(f"Error: Failed to fetch schedule for '{team.get('displayName', team_id)}' ({e})")
        return None
    except (KeyError, ValueError):
        print(f"Error: Unexpected response format when fetching top scorer for '{team.get('displayName', team_id)}'")
        return None

    last = next(
        (e for e in reversed(events)
         if e.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("state") == "post"),
        None,
    )
    if not last:
        print(f"Error: No completed games found for '{team.get('displayName', team_id)}'")
        return None

    leaders = last["competitions"][0].get("leaders", [])
    for category in ["Passing Yards", "Rushing Yards", "Receiving Yards"]:
        for cat in leaders:
            if cat.get("displayName") == category:
                entries = cat.get("leaders", [])
                if entries:
                    top = entries[0]
                    name = top.get("athlete", {}).get("displayName", "Unknown")
                    display = top.get("displayValue", "")
                    match = re.search(r"(\d+)\s*YDS", display, re.IGNORECASE)
                    yards = match.group(1) if match else display
                    stat = category.lower()
                    return {"top_scorer": f"{name} — {yards} {stat}"}

    print(f"Error: No leader stats found in last game for '{team.get('displayName', team_id)}'")
    return None


def get_last_and_next_game(team):
    team_id = str(team["id"])
    resp = requests.get(f"{BASE}/teams/{team_id}/schedule")
    resp.raise_for_status()
    events = resp.json().get("events", [])

    completed, upcoming = [], []
    for event in events:
        comps = event.get("competitions", [])
        if not comps:
            continue
        state = comps[0].get("status", {}).get("type", {}).get("state", "")
        if state == "post":
            completed.append(event)
        elif state == "pre":
            upcoming.append(event)

    def _score(competitor):
        s = competitor.get("score", 0)
        return int(s.get("displayValue", 0) if isinstance(s, dict) else s)

    def _short(competitor):
        return competitor["team"].get("shortDisplayName") or competitor["team"].get("name", "")

    def _format_completed(event):
        comp = event["competitions"][0]
        us, opp = None, None
        for c in comp.get("competitors", []):
            if c["team"]["id"] == team_id:
                us = c
            else:
                opp = c
        if not us or not opp:
            return "N/A"
        our_score, opp_score = _score(us), _score(opp)
        result = "W" if our_score > opp_score else "L"
        return f"{_short(us)} {our_score} - {_short(opp)} {opp_score} ({result})"

    def _format_upcoming(event):
        comp = event["competitions"][0]
        us, opp = None, None
        for c in comp.get("competitors", []):
            if c["team"]["id"] == team_id:
                us = c
            else:
                opp = c
        if not us or not opp:
            return "N/A"
        vs = "vs" if us.get("homeAway") == "home" else "@"
        date = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        date_str = date.strftime("%a %b %-d")
        return f"{_short(us)} {vs} {_short(opp)} — {date_str}"

    return {
        "last_game": _format_completed(completed[-1]) if completed else "N/A",
        "next_game": _format_upcoming(upcoming[0]) if upcoming else "N/A",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python nfl_dashboard.py \"Team Name\"")
        sys.exit(1)

    team_name = " ".join(sys.argv[1:])

    team = find_team(team_name)
    if team is None:
        sys.exit(1)

    games      = get_last_and_next_game(team)
    record     = get_record(team)
    standing   = get_standing(team)
    top_scorer = get_top_scorer(team)

    label_w = 13
    sep = "━" * 42

    print(f"\n{team['displayName']} — 2024 Season Dashboard")
    print(sep)
    print(f"{'Last game:':<{label_w}}{games['last_game']}")
    print(f"{'Next game:':<{label_w}}{games['next_game']}")
    print(f"{'Record:':<{label_w}}{record['record'] if record else 'N/A'}")
    print(f"{'Standing:':<{label_w}}{standing['standing'] if standing else 'N/A'}")
    print(f"{'Top scorer:':<{label_w}}{top_scorer['top_scorer'] if top_scorer else 'N/A'}")
    print()


if __name__ == "__main__":
    main()
