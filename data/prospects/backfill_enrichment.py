from __future__ import annotations

import argparse
import csv
import re
import time
from collections import OrderedDict
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REQUEST_DELAY_SECONDS = 0.2
TIMEOUT_SECONDS = 30

PFF_PLAYER_URLS = {
    "Antonio Williams": "https://www.pff.com/ncaa/players/antonio-williams/156241",
    "Bryce Lance": "https://www.pff.com/ncaa/players/bryce-lance/148151",
    "Cade Klubnik": "https://www.pff.com/ncaa/players/cade-klubnik/156253",
    "Carnell Tate": "https://www.pff.com/ncaa/players/carnell-tate/170273",
    "Carson Beck": "https://www.pff.com/ncaa/players/carson-beck/124010",
    "Chris Bell": "https://www.pff.com/ncaa/players/chris-bell/156321",
    "Chris Brazzell II": "https://www.pff.com/ncaa/players/chris-brazzell/158409",
    "Deion Burks": "https://www.pff.com/ncaa/players/deion-burks/145107",
    "Denzel Boston": "https://www.pff.com/ncaa/players/denzel-boston/162481",
    "Drew Allar": "https://www.pff.com/ncaa/players/drew-allar/164157",
    "Eli Stowers": "https://www.pff.com/ncaa/players/eli-stowers/147013",
    "Elijah Sarratt": "https://www.pff.com/ncaa/players/elijah-sarratt/159499",
    "Fernando Mendoza": "https://www.pff.com/ncaa/players/fernando-mendoza/158323",
    "Garrett Nussmeier": "https://www.pff.com/ncaa/players/garrett-nussmeier/146757",
    "Germie Bernard": "https://www.pff.com/ncaa/players/germie-bernard/158374",
    "Jack Endries": "https://www.pff.com/ncaa/players/jack-endries/158317",
    "Jadarian Price": "https://www.pff.com/ncaa/players/jadarian-price/156985",
    "Ja'Kobi Lane": "https://www.pff.com/ncaa/players/jakobi-lane/176638",
    "Jeremiyah Love": "https://www.pff.com/ncaa/players/jeremiyah-love/171090",
    "Jordyn Tyson": "https://www.pff.com/ncaa/players/jordyn-tyson/157690",
    "Justin Joly": "https://www.pff.com/ncaa/players/justin-joly/158620",
    "Kenyon Sadiq": "https://www.pff.com/ncaa/players/kenyon-sadiq/174132",
    "Makai Lemon": "https://www.pff.com/ncaa/players/makai-lemon/174150",
    "Malachi Fields": "https://www.pff.com/ncaa/players/malachi-fields/151069",
    "Max Klare": "https://www.pff.com/ncaa/players/max-klare/162884",
    "Mike Washington Jr.": "https://www.pff.com/ncaa/players/mike-washington/145672",
    "Omar Cooper Jr.": "https://www.pff.com/ncaa/players/omar-cooper/156395",
    "Sam Roush": "https://www.pff.com/ncaa/players/sam-roush/157270",
    "Sawyer Robertson": "https://www.pff.com/ncaa/players/sawyer-robertson/146839",
    "Skyler Bell": "https://www.pff.com/ncaa/players/skyler-bell/145163",
    "Taylen Green": "https://www.pff.com/ncaa/players/taylen-green/145996",
    "Ty Simpson": "https://www.pff.com/ncaa/players/ty-simpson/157008",
    "Zachariah Branch": "https://www.pff.com/ncaa/players/zachariah-branch/174142",
}

ENRICHMENT_FIELDS = [
    "player_name",
    "position",
    "college_games",
    "college_targets",
    "college_receptions",
    "college_receiving_yards",
    "college_receiving_tds",
    "college_routes_run",
    "college_yprr",
    "college_ypt",
    "college_carries",
    "college_rushing_yards",
    "college_rushing_tds",
    "college_pass_attempts",
    "college_completions",
    "college_passing_yards",
    "college_passing_tds",
    "college_interceptions",
    "college_qb_rush_yards",
    "college_qb_rush_tds",
    "college_scramble_rate",
    "vertical",
    "bench",
    "cone",
    "shuttle",
    "production_source",
]


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", "ignore")
    time.sleep(REQUEST_DELAY_SECONDS)
    return body


def safe_fetch_text(url: str) -> str | None:
    try:
        return fetch_text(url)
    except (HTTPError, URLError, TimeoutError):
        return None


def slugify_player_name(name: str) -> str:
    return "-".join(part for part in re.sub(r"[^a-z0-9 ]+", "", name.lower()).split() if part)


def parse_number(value: str | None) -> float | None:
    if value in (None, "", "-", "N/S"):
        return None
    cleaned = value.replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def statmuse_field_value(payload: str, label: str) -> float | None:
    match = re.search(
        rf'"{re.escape(label)}":\[0,\{{"value":\[0,(-?\d+(?:\.\d+)?)\]',
        payload,
    )
    if not match:
        return None
    return float(match.group(1))


def fetch_statmuse_payload(url: str) -> str:
    body = safe_fetch_text(url)
    if body is None:
        return ""
    text = unescape(body)
    marker = '"NAME":[0,{"value":[0,'
    start = text.find(marker)
    if start == -1:
        return text
    return text[start : start + 5000]


def statmuse_query_candidates(name: str, suffix: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", name.strip())
    slug = slugify_player_name(cleaned)
    plain = quote_plus(cleaned.lower())
    compact = quote_plus(re.sub(r"[.']", "", cleaned.lower()))
    return [
        f"https://www.statmuse.com/cfb/ask/{slug}-{suffix}",
        f"https://www.statmuse.com/cfb/ask/{plain}-{suffix}",
        f"https://www.statmuse.com/cfb/ask/{compact}-{suffix}",
    ]


def first_statmuse_payload(name: str, suffix: str) -> str:
    for url in statmuse_query_candidates(name, suffix):
        payload = fetch_statmuse_payload(url)
        if '"NAME":[0,{"value":[0,' in payload:
            return payload
    return ""


def fetch_skill_statmuse_stats(name: str, season: int) -> dict[str, float | None]:
    payload = first_statmuse_payload(name, f"targets-{season}")
    return {
        "college_games": statmuse_field_value(payload, "GP"),
        "college_targets": statmuse_field_value(payload, "TRG"),
        "college_receptions": statmuse_field_value(payload, "REC"),
        "college_receiving_yards": statmuse_field_value(payload, "REC YDS"),
        "college_receiving_tds": statmuse_field_value(payload, "REC TD"),
        "college_carries": statmuse_field_value(payload, "ATT"),
        "college_rushing_yards": statmuse_field_value(payload, "RUSH YDS"),
        "college_rushing_tds": statmuse_field_value(payload, "RUSH TD"),
    }


def fetch_qb_statmuse_stats(name: str, season: int) -> dict[str, float | None]:
    passing_payload = first_statmuse_payload(name, f"{season}-stats")
    rushing_payload = first_statmuse_payload(name, f"rushing-stats-{season}")
    return {
        "college_games": statmuse_field_value(passing_payload, "GP"),
        "college_completions": statmuse_field_value(passing_payload, "CMP"),
        "college_pass_attempts": statmuse_field_value(passing_payload, "ATT"),
        "college_passing_yards": statmuse_field_value(passing_payload, "YDS"),
        "college_passing_tds": statmuse_field_value(passing_payload, "TD"),
        "college_interceptions": statmuse_field_value(passing_payload, "INT"),
        "college_qb_rush_yards": statmuse_field_value(rushing_payload, "RUSH YDS"),
        "college_qb_rush_tds": statmuse_field_value(rushing_payload, "RUSH TD"),
    }


def duckduckgo_result_url(query: str) -> str | None:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    body = safe_fetch_text(url)
    if body is None:
        return None
    matches = re.findall(r'href="//duckduckgo.com/l/\?([^"]+)"', body)
    for match in matches:
        params = parse_qs(match.replace("&amp;", "&"))
        uddg_values = params.get("uddg")
        if not uddg_values:
            continue
        candidate = unquote(uddg_values[0])
        if "pff.com/ncaa/players/" in candidate:
            return candidate
    return None


def pff_row_value(page: str, label: str) -> float | None:
    pattern = re.compile(
        rf">{re.escape(label)}</div></div><div[^>]*><div[^>]*data-testid=\"playerProfiles\.statsTableRow\.statValue\">([^<]+)</div>",
        re.IGNORECASE,
    )
    match = pattern.search(page)
    if not match:
        return None
    return parse_number(match.group(1))


def fetch_pff_metrics(name: str, position: str) -> dict[str, float | None]:
    player_url = PFF_PLAYER_URLS.get(name)
    if not player_url:
        query = f'site:pff.com/ncaa/players "{name}"'
        player_url = duckduckgo_result_url(query)
    if not player_url:
        return {}

    body = safe_fetch_text(player_url)
    if body is None:
        return {}
    metrics: dict[str, float | None] = {}

    if position == "QB":
        dropbacks = pff_row_value(body, "Dropbacks")
        scrambles = pff_row_value(body, "Scrambles")
        if scrambles is not None and dropbacks not in (None, 0):
            metrics["college_scramble_rate"] = scrambles / dropbacks
    else:
        routes_run = pff_row_value(body, "Routes Run")
        targets = pff_row_value(body, "Targets")
        receiving_yards = pff_row_value(body, "Receiving Yards")
        if routes_run is not None:
            metrics["college_routes_run"] = routes_run
        if receiving_yards is not None and routes_run not in (None, 0):
            metrics["college_yprr"] = receiving_yards / routes_run
        if receiving_yards is not None and targets not in (None, 0):
            metrics["college_ypt"] = receiving_yards / targets

    metrics["_pff_url"] = player_url  # diagnostic only, stripped before write
    return metrics


def read_existing_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            (row["player_name"], row["position"]): row
            for row in reader
            if row.get("player_name") and row.get("position")
        }


def merge_sources(existing: str, *sources: str) -> str:
    ordered: list[str] = []
    for value in (existing, *sources):
        for item in value.split("|"):
            item = item.strip()
            if item and item not in ordered:
                ordered.append(item)
    return "|".join(ordered)


def build_enrichment_rows(
    base_csv: Path,
    enrichment_csv: Path,
    season: int,
) -> list[dict[str, str]]:
    existing_rows = read_existing_rows(enrichment_csv)
    rows: list[dict[str, str]] = []

    with base_csv.open(newline="") as handle:
        base_reader = csv.DictReader(handle)
        for base_row in base_reader:
            player_name = base_row["player_name"]
            position = base_row["position"]
            key = (player_name, position)
            current = OrderedDict.fromkeys(ENRICHMENT_FIELDS, "")
            current["player_name"] = player_name
            current["position"] = position

            existing = existing_rows.get(key, {})
            for field in ENRICHMENT_FIELDS:
                if existing.get(field):
                    current[field] = existing[field]

            if position == "QB":
                statmuse_values = fetch_qb_statmuse_stats(player_name, season)
            else:
                statmuse_values = fetch_skill_statmuse_stats(player_name, season)

            pff_values = fetch_pff_metrics(player_name, position)

            for field, value in statmuse_values.items():
                if value is not None:
                    current[field] = format_value(value)
            for field, value in pff_values.items():
                if field.startswith("_"):
                    continue
                if value is not None:
                    current[field] = format_value(value)

            source_tags = []
            if any(value is not None for value in statmuse_values.values()):
                source_tags.append(f"statmuse_{season}")
            if any(value is not None for key, value in pff_values.items() if not key.startswith("_")):
                source_tags.append(f"pff_{season}_player_page")
            current["production_source"] = merge_sources(
                current["production_source"],
                *source_tags,
            )

            has_meaningful_data = any(
                current[field]
                for field in ENRICHMENT_FIELDS
                if field not in {"player_name", "position", "vertical", "bench", "cone", "shuttle", "production_source"}
            )
            if has_meaningful_data or any(current[field] for field in ("vertical", "bench", "cone", "shuttle")):
                rows.append(dict(current))

    return rows


def write_enrichment_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ENRICHMENT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill source-backed pre-draft enrichment data.")
    parser.add_argument("--base-csv", required=True, type=Path)
    parser.add_argument("--enrichment-csv", required=True, type=Path)
    parser.add_argument("--season", required=True, type=int)
    args = parser.parse_args()

    rows = build_enrichment_rows(args.base_csv, args.enrichment_csv, args.season)
    write_enrichment_rows(args.enrichment_csv, rows)
    print(f"wrote {len(rows)} rows to {args.enrichment_csv}")


if __name__ == "__main__":
    main()
