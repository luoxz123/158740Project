"""Renewable energy GIR pipeline for New Zealand WebGIS.

The pipeline supports four practical modes:
1. Offline sample mode for demos and marking without network dependency.
2. Manual URL mode for known article URLs.
3. Automatic news discovery from public news sitemaps.
4. Optional PostGIS insertion of extracted GIR point features.

Facebook is intentionally handled through CSV import or official API exports,
not through blind scraping, because public Facebook pages are commonly gated,
rate-limited, and subject to platform permissions.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - handled at runtime
    BeautifulSoup = None

try:
    from geopy.geocoders import Nominatim
except ImportError:  # pragma: no cover - handled at runtime
    Nominatim = None

try:
    import psycopg2
except ImportError:  # pragma: no cover - handled at runtime
    psycopg2 = None

try:
    import spacy
except ImportError:  # pragma: no cover - handled at runtime
    spacy = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_ARTICLES = PROJECT_ROOT / "data" / "raw" / "sample_articles.csv"
DEFAULT_URLS_FILE = PROJECT_ROOT / "data" / "raw" / "renewable_article_urls.txt"
DEFAULT_FACEBOOK_CSV = PROJECT_ROOT / "data" / "raw" / "facebook_mentions.csv"
DEFAULT_PLACES_FILE = PROJECT_ROOT / "data" / "raw" / "nz_place_names.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "renewable_energy_mentions.geojson"
DEFAULT_FRONTEND_OUTPUT = PROJECT_ROOT / "frontend" / "data" / "gir_mentions.geojson"
DEFAULT_CACHE = PROJECT_ROOT / "data" / "processed" / "cache" / "geocode_cache.json"

DEFAULT_NEWS_SITES = [
    "https://www.rnz.co.nz",
    "https://www.stuff.co.nz",
    "https://www.nzherald.co.nz",
]

DEFAULT_KEYWORDS = [
    "wind",
    "windy",
    "wind farm",
    "wind turbine",
    "strong wind",
    "strong wind watch",
    "strong wind warning",
    "wind watch",
    "wind warning",
    "gale",
    "gust",
    "gusts",
    "sun",
    "sunshine",
    "solar",
    "solar farm",
    "photovoltaic",
    "pv",
    "renewable",
    "renewable energy",
    "clean energy",
    "electricity generation",
    "severe weather watch",
    "severe weather warning",
    "weather warning",
    "weather watch",
    "thunderstorm watch",
]

DEFAULT_USER_AGENT = "Massey WebGIS GIR student project"

KNOWN_NZ_PLACES = {
    "Auckland": (-36.8509, 174.7645),
    "Bay of Plenty": (-37.6878, 176.1651),
    "Canterbury": (-43.7542, 171.1637),
    "Central Otago": (-45.1300, 169.6000),
    "Christchurch": (-43.5321, 172.6362),
    "Dunedin": (-45.8788, 170.5028),
    "Gisborne": (-38.6623, 178.0176),
    "Hamilton": (-37.7870, 175.2793),
    "Hawke's Bay": (-39.4928, 176.9120),
    "Invercargill": (-46.4132, 168.3538),
    "Manawatu": (-40.3523, 175.6082),
    "Marlborough": (-41.5917, 173.7624),
    "Napier": (-39.4928, 176.9120),
    "Nelson": (-41.2706, 173.2840),
    "New Plymouth": (-39.0556, 174.0752),
    "Northland": (-35.5795, 173.7624),
    "Otago": (-45.4791, 170.1548),
    "Queenstown": (-45.0312, 168.6626),
    "Rotorua": (-38.1368, 176.2497),
    "Southland": (-46.4132, 168.3538),
    "Taranaki": (-39.3538, 174.4383),
    "Tasman": (-41.3010, 172.6740),
    "Taupo": (-38.6857, 176.0702),
    "Tauranga": (-37.6878, 176.1651),
    "Waikato": (-37.6191, 175.0233),
    "Wellington": (-41.2865, 174.7762),
    "West Coast": (-42.4064, 171.6912),
    "Whangarei": (-35.7251, 174.3237),
}


@dataclass
class Article:
    title: str
    text: str
    source_url: str


def log(message: str) -> None:
    print(message, flush=True)


def require_scraping_dependencies() -> None:
    if requests is None or BeautifulSoup is None:
        raise RuntimeError("Live discovery/scraping requires requests and beautifulsoup4.")


def load_spacy_model():
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return None


def load_known_places(path: Path) -> dict[str, tuple[float, float]]:
    places = dict(KNOWN_NZ_PLACES)
    if not path.exists():
        return places

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("place_name") or "").strip()
            if not name:
                continue
            try:
                latitude = float(row["latitude"])
                longitude = float(row["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            places[name] = (latitude, longitude)
    return places


def read_sample_articles(path: Path) -> list[Article]:
    articles: list[Article] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            articles.append(
                Article(
                    title=row["title"].strip(),
                    text=row["text"].strip(),
                    source_url=row["source_url"].strip(),
                )
            )
    return articles


def read_facebook_csv(path: Path) -> list[Article]:
    if not path.exists():
        return []

    articles: list[Article] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = (row.get("title") or "Facebook renewable energy mention").strip()
            text = (row.get("text") or "").strip()
            source_url = (row.get("source_url") or "facebook://manual-export").strip()
            if text:
                articles.append(Article(title=title, text=text, source_url=source_url))
    return articles


def read_urls(path: Path) -> list[str]:
    if not path.exists():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def keyword_pattern(keywords: Iterable[str]) -> re.Pattern:
    escaped = []
    for keyword in keywords:
        keyword = keyword.strip().lower()
        if not keyword:
            continue
        if " " in keyword:
            escaped.append(re.escape(keyword))
        else:
            escaped.append(rf"\b{re.escape(keyword)}\b")
    return re.compile("|".join(escaped), flags=re.IGNORECASE)


def contains_keywords(text: str, keywords: Iterable[str]) -> bool:
    return bool(keyword_pattern(keywords).search(text))


def normalise_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path) or "/"
    return urllib.parse.urlunparse((scheme, netloc, path, "", parsed.query, ""))


def same_site(url: str, site: str) -> bool:
    url_host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    site_host = urllib.parse.urlparse(site).netloc.lower().replace("www.", "")
    return url_host == site_host or url_host.endswith(f".{site_host}")


def is_probably_html_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    blocked_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".css",
        ".js",
        ".pdf",
        ".zip",
        ".mp3",
        ".mp4",
        ".xml",
    )
    return not path.endswith(blocked_extensions)


def get_session(user_agent: str):
    require_scraping_dependencies()
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    return session


def fetch_text(session, url: str, timeout: int) -> str | None:
    try:
        response = session.get(url, timeout=timeout)
        if response.status_code >= 400:
            return None
        content_type = response.headers.get("content-type", "")
        if "text" not in content_type and "xml" not in content_type and "html" not in content_type:
            return None
        return response.text
    except requests.RequestException:
        return None


def load_robot_parser(session, site: str, timeout: int):
    parsed_site = urllib.parse.urlparse(site)
    robots_url = f"{parsed_site.scheme}://{parsed_site.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    text = fetch_text(session, robots_url, timeout)
    if text is None:
        return None
    parser.parse(text.splitlines())
    return parser


def sitemap_candidates(session, site: str, timeout: int) -> list[str]:
    parsed_site = urllib.parse.urlparse(site)
    base = f"{parsed_site.scheme}://{parsed_site.netloc}"
    candidates = {
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap-news.xml",
        f"{base}/news-sitemap.xml",
    }

    robots_text = fetch_text(session, f"{base}/robots.txt", timeout)
    if robots_text:
        for line in robots_text.splitlines():
            if line.lower().startswith("sitemap:"):
                candidates.add(line.split(":", 1)[1].strip())

    return sorted(candidates)


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    sitemaps: list[str] = []
    urls: list[str] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return sitemaps, urls

    for loc in root.findall(".//{*}loc"):
        value = (loc.text or "").strip()
        if not value:
            continue
        if value.lower().endswith(".xml") or "sitemap" in value.lower():
            sitemaps.append(value)
        else:
            urls.append(value)
    return sitemaps, urls


def discover_urls_from_seed_pages(
    session,
    site: str,
    keywords: list[str],
    max_pages: int,
    timeout: int,
    request_delay: float,
    robot_parser,
    user_agent: str,
    deep_scan: bool,
) -> list[str]:
    parsed_site = urllib.parse.urlparse(site)
    base = f"{parsed_site.scheme}://{parsed_site.netloc}"
    seed_urls = [
        base,
        f"{base}/",
        f"{base}/warnings/home",
        f"{base}/warnings",
        f"{base}/severe-weather",
        f"{base}/forecasts",
        f"{base}/maps-radar",
        f"{base}/warnings",
        f"{base}/towns-cities",
        f"{base}/rural",
        f"{base}/marine",
    ]
    queue = [normalise_url(url) for url in seed_urls]
    seen_pages: set[str] = set()
    selected: list[str] = []
    kw_pattern = keyword_pattern(keywords)

    while queue and len(seen_pages) < max_pages * 3 and len(selected) < max_pages:
        url = queue.pop(0)
        if url in seen_pages or not same_site(url, site) or not is_probably_html_url(url):
            continue
        seen_pages.add(url)

        if robot_parser is not None and not robot_parser.can_fetch(user_agent, url):
            continue

        html = fetch_text(session, url, timeout)
        if not html:
            continue

        if deep_scan:
            if kw_pattern.search(html):
                selected.append(url)
        elif kw_pattern.search(url):
            selected.append(url)

        if BeautifulSoup is None:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(base, anchor["href"])
            href = normalise_url(href)
            if href in seen_pages or not same_site(href, site) or not is_probably_html_url(href):
                continue
            if deep_scan or kw_pattern.search(href) or any(section in href.lower() for section in ["/forecast", "/warning", "/town", "/city", "/rural", "/marine"]):
                queue.append(href)

        time.sleep(request_delay)

    return selected[:max_pages]


def discover_urls_from_sitemaps(
    site: str,
    keywords: list[str],
    max_sitemaps: int,
    max_pages: int,
    timeout: int,
    request_delay: float,
    ignore_robots: bool,
    deep_scan: bool,
    user_agent: str,
) -> list[str]:
    session = get_session(user_agent)
    robot_parser = None if ignore_robots else load_robot_parser(session, site, timeout)
    sitemap_queue = sitemap_candidates(session, site, timeout)
    seen_sitemaps: set[str] = set()
    seen_urls: set[str] = set()
    selected: list[str] = []
    kw_pattern = keyword_pattern(keywords)

    while sitemap_queue and len(seen_sitemaps) < max_sitemaps and len(selected) < max_pages:
        sitemap_url = sitemap_queue.pop(0)
        sitemap_url = normalise_url(sitemap_url)
        if sitemap_url in seen_sitemaps or not same_site(sitemap_url, site):
            continue
        seen_sitemaps.add(sitemap_url)

        if robot_parser is not None and not robot_parser.can_fetch(user_agent, sitemap_url):
            continue

        xml_text = fetch_text(session, sitemap_url, timeout)
        if not xml_text:
            continue

        nested_sitemaps, urls = parse_sitemap(xml_text)
        for nested in nested_sitemaps:
            if len(seen_sitemaps) + len(sitemap_queue) >= max_sitemaps:
                break
            if same_site(nested, site):
                sitemap_queue.append(nested)

        for url in urls:
            if len(selected) >= max_pages:
                break
            url = normalise_url(url)
            if url in seen_urls or not same_site(url, site) or not is_probably_html_url(url):
                continue
            seen_urls.add(url)
            if robot_parser is not None and not robot_parser.can_fetch(user_agent, url):
                continue
            if deep_scan or kw_pattern.search(url):
                selected.append(url)

        time.sleep(request_delay)

    if not selected:
        log(f"[discover] {site}: no sitemap URL keyword matches; trying seed-page crawl")
        selected = discover_urls_from_seed_pages(
            session=session,
            site=site,
            keywords=keywords,
            max_pages=max_pages,
            timeout=timeout,
            request_delay=request_delay,
            robot_parser=robot_parser,
            user_agent=user_agent,
            deep_scan=deep_scan,
        )

    return selected[:max_pages]


def scrape_article(url: str, timeout: int = 20, session=None) -> Article:
    require_scraping_dependencies()
    session = session or get_session(DEFAULT_USER_AGENT)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "form"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else url
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(" ", strip=True)) > 40
    ]
    text = "\n".join(paragraphs)
    return Article(title=title, text=text, source_url=url)


def discover_articles(
    sites: list[str],
    keywords: list[str],
    max_sitemaps_per_site: int,
    max_pages_per_site: int,
    timeout: int,
    request_delay: float,
    ignore_robots: bool,
    deep_scan: bool,
    user_agent: str,
) -> list[Article]:
    session = get_session(user_agent)
    articles: list[Article] = []
    seen_article_urls: set[str] = set()

    for site in sites:
        log(f"[discover] scanning {site}")
        urls = discover_urls_from_sitemaps(
            site=site,
            keywords=keywords,
            max_sitemaps=max_sitemaps_per_site,
            max_pages=max_pages_per_site,
            timeout=timeout,
            request_delay=request_delay,
            ignore_robots=ignore_robots,
            deep_scan=deep_scan,
            user_agent=user_agent,
        )
        log(f"[discover] {site}: {len(urls)} candidate URLs")

        for url in urls:
            if url in seen_article_urls:
                continue
            seen_article_urls.add(url)
            try:
                article = scrape_article(url, timeout=timeout, session=session)
            except Exception:
                continue

            combined_text = f"{article.title}\n{article.text}"
            if contains_keywords(combined_text, keywords):
                articles.append(article)
                log(f"[article] matched: {article.title[:90]}")
            time.sleep(request_delay)

    return articles


def infer_energy_type(text: str) -> str:
    lower = text.lower()
    has_wind = "wind" in lower or "turbine" in lower
    has_solar = (
        "solar" in lower
        or "sunshine" in lower
        or "photovoltaic" in lower
        or re.search(r"\bpv\b", lower) is not None
    )
    if has_wind and has_solar:
        return "mixed"
    if has_wind:
        return "wind"
    if has_solar:
        return "solar"
    return "renewable"


def extract_places(text: str, nlp_model) -> list[str]:
    places = set()

    if nlp_model is not None:
        doc = nlp_model(text)
        for entity in doc.ents:
            if entity.label_ in {"GPE", "LOC", "FAC"}:
                cleaned = clean_place_name(entity.text)
                if cleaned:
                    places.add(cleaned)

    for place in KNOWN_NZ_PLACES:
        if re.search(rf"\b{re.escape(place)}\b", text, flags=re.IGNORECASE):
            places.add(place)

    return sorted(places)


def clean_place_name(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" ,.;:()[]")
    if len(cleaned) < 3:
        return None
    if re.search(r"\d", cleaned):
        return None
    blocked = {"New Zealand", "NZ", "RNZ", "Stuff", "Herald", "Facebook"}
    if cleaned in blocked:
        return None
    return cleaned


def load_cache(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: dict[str, dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def geocode_place(
    place_name: str,
    geocoder,
    cache: dict[str, dict[str, float]],
    offline_only: bool,
) -> tuple[float, float, float] | None:
    if place_name in KNOWN_NZ_PLACES:
        lat, lon = KNOWN_NZ_PLACES[place_name]
        return lat, lon, 0.95

    if place_name in cache:
        item = cache[place_name]
        return item["latitude"], item["longitude"], item.get("confidence", 0.75)

    if offline_only or geocoder is None:
        return None

    location = geocoder.geocode(f"{place_name}, New Zealand", timeout=15)
    time.sleep(1.1)
    if not location:
        return None

    cache[place_name] = {
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
        "confidence": 0.75,
    }
    return float(location.latitude), float(location.longitude), 0.75


def build_features(
    articles: Iterable[Article],
    nlp_model,
    offline_only: bool,
    cache_path: Path,
) -> list[dict]:
    cache = load_cache(cache_path)
    if offline_only:
        geocoder = None
    else:
        if Nominatim is None:
            raise RuntimeError("Live geocoding requires geopy.")
        geocoder = Nominatim(user_agent="renewable_energy_gir_massey")

    features: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for article in articles:
        combined_text = f"{article.title}\n{article.text}"
        energy_type = infer_energy_type(combined_text)
        places = extract_places(combined_text, nlp_model)

        for place in places:
            key = (article.source_url, place)
            if key in seen:
                continue
            seen.add(key)

            result = geocode_place(place, geocoder, cache, offline_only)
            if result is None:
                continue

            latitude, longitude, confidence = result
            feature_id = f"gir-{len(features) + 1:03d}"
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": feature_id,
                        "article_title": article.title,
                        "place_name": place,
                        "latitude": latitude,
                        "longitude": longitude,
                        "energy_type": energy_type,
                        "source_url": article.source_url,
                        "confidence": round(confidence, 3),
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                }
            )

    save_cache(cache_path, cache)
    return features


def write_geojson(features: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": "renewable_energy_mentions",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }
    output_path.write_text(json.dumps(collection, indent=2), encoding="utf-8")


def validate_sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return value


def default_db_dsn() -> str:
    if os.getenv("POSTGIS_DSN"):
        return os.environ["POSTGIS_DSN"]

    host = os.getenv("POSTGIS_HOST", "localhost")
    port = os.getenv("POSTGIS_PORT", "5432")
    dbname = os.getenv("POSTGIS_DB", "renewable_nz")
    user = os.getenv("POSTGIS_USER", "postgres")
    password = os.getenv("POSTGIS_PASSWORD", "")
    parts = [
        f"host={host}",
        f"port={port}",
        f"dbname={dbname}",
        f"user={user}",
    ]
    if password:
        parts.append(f"password={password}")
    return " ".join(parts)


def insert_features_to_postgis(features: list[dict], db_dsn: str, schema: str) -> int:
    if psycopg2 is None:
        raise RuntimeError("PostGIS insertion requires psycopg2-binary.")
    schema = validate_sql_identifier(schema)

    sql = f"""
        INSERT INTO {schema}.gir_locations (
            article_title,
            place_name,
            latitude,
            longitude,
            energy_type,
            source_url,
            confidence,
            geom
        )
        SELECT
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 2193)
        WHERE NOT EXISTS (
            SELECT 1
            FROM {schema}.gir_locations
            WHERE source_url = %s
              AND place_name = %s
        );
    """

    inserted = 0
    with psycopg2.connect(db_dsn) as conn:
        with conn.cursor() as cursor:
            for feature in features:
                props = feature["properties"]
                longitude, latitude = feature["geometry"]["coordinates"][:2]
                cursor.execute(
                    sql,
                    (
                        props["article_title"],
                        props["place_name"],
                        props["latitude"],
                        props["longitude"],
                        props["energy_type"],
                        props["source_url"],
                        props["confidence"],
                        longitude,
                        latitude,
                        props["source_url"],
                        props["place_name"],
                    ),
                )
                inserted += cursor.rowcount
    return inserted


def parse_keyword_arg(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate GIR renewable energy GeoJSON.")
    parser.add_argument("--offline-sample", action="store_true", help="Use local sample article text.")
    parser.add_argument("--auto-discover", action="store_true", help="Discover articles from public news sitemaps.")
    parser.add_argument("--deep-scan", action="store_true", help="Scan sitemap pages even when keywords are not in the URL.")
    parser.add_argument("--ignore-robots", action="store_true", help="Do not check robots.txt before sitemap/page access.")
    parser.add_argument("--include-facebook-csv", action="store_true", help="Include manually exported Facebook CSV text.")
    parser.add_argument("--insert-db", action="store_true", help="Insert generated GIR point features into PostGIS.")
    parser.add_argument("--sample-file", type=Path, default=DEFAULT_SAMPLE_ARTICLES)
    parser.add_argument("--urls-file", type=Path, default=DEFAULT_URLS_FILE)
    parser.add_argument("--facebook-csv", type=Path, default=DEFAULT_FACEBOOK_CSV)
    parser.add_argument("--places-file", type=Path, default=DEFAULT_PLACES_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frontend-output", type=Path, default=None)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--db-dsn", default=default_db_dsn())
    parser.add_argument("--db-schema", default=os.getenv("POSTGIS_SCHEMA", "renewable_nz"))
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    parser.add_argument("--sites", nargs="*", default=DEFAULT_NEWS_SITES)
    parser.add_argument("--max-sitemaps-per-site", type=int, default=25)
    parser.add_argument("--max-pages-per-site", type=int, default=80)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--offline-geocode", action="store_true", help="Use only known NZ place coordinates and cache.")
    return parser.parse_args()


def collect_articles(args: argparse.Namespace, keywords: list[str]) -> list[Article]:
    articles: list[Article] = []

    if args.offline_sample:
        log(f"[input] reading sample articles: {args.sample_file}")
        articles.extend(read_sample_articles(args.sample_file))

    if args.auto_discover:
        log(f"[input] auto-discover enabled for {len(args.sites)} sites")
        articles.extend(
            discover_articles(
                sites=args.sites,
                keywords=keywords,
                max_sitemaps_per_site=args.max_sitemaps_per_site,
                max_pages_per_site=args.max_pages_per_site,
                timeout=args.timeout,
                request_delay=args.request_delay,
                ignore_robots=args.ignore_robots,
                deep_scan=args.deep_scan,
                user_agent=args.user_agent,
            )
        )

    manual_urls = read_urls(args.urls_file)
    if manual_urls:
        log(f"[input] scraping {len(manual_urls)} manual URLs from {args.urls_file}")
        session = get_session(args.user_agent)
        for url in manual_urls:
            try:
                article = scrape_article(url, timeout=args.timeout, session=session)
            except Exception:
                continue
            if contains_keywords(f"{article.title}\n{article.text}", keywords):
                articles.append(article)
            time.sleep(args.request_delay)

    if args.include_facebook_csv:
        log(f"[input] reading Facebook CSV export: {args.facebook_csv}")
        facebook_articles = read_facebook_csv(args.facebook_csv)
        articles.extend(
            article
            for article in facebook_articles
            if contains_keywords(f"{article.title}\n{article.text}", keywords)
        )

    seen_urls: set[str] = set()
    unique_articles: list[Article] = []
    for article in articles:
        if article.source_url in seen_urls:
            continue
        seen_urls.add(article.source_url)
        unique_articles.append(article)
    return unique_articles


def main() -> int:
    args = parse_args()
    keywords = parse_keyword_arg(args.keywords)
    nlp_model = load_spacy_model()

    log("[start] Renewable Energy GIR pipeline")
    log(f"[mode] auto_discover={args.auto_discover}, offline_sample={args.offline_sample}, facebook_csv={args.include_facebook_csv}, insert_db={args.insert_db}")
    log(f"[keywords] {', '.join(keywords)}")

    global KNOWN_NZ_PLACES
    KNOWN_NZ_PLACES = load_known_places(args.places_file)
    log(f"[places] loaded {len(KNOWN_NZ_PLACES)} known NZ place names")

    articles = collect_articles(args, keywords)
    if not articles:
        log("[result] No matching articles were collected.")
        log("[hint] Try running from the project root, or add --deep-scan / increase --max-pages-per-site.")
        return 1

    offline_geocode = args.offline_sample or args.offline_geocode
    log(f"[geocode] offline_geocode={offline_geocode}")
    features = build_features(
        articles=articles,
        nlp_model=nlp_model,
        offline_only=offline_geocode,
        cache_path=args.cache,
    )
    write_geojson(features, args.output)

    frontend_output = args.frontend_output or (
        DEFAULT_FRONTEND_OUTPUT if args.offline_sample else None
    )
    if frontend_output:
        write_geojson(features, frontend_output)

    print(f"Collected {len(articles)} matching articles.")
    print(f"Generated {len(features)} GIR features: {args.output}")
    if frontend_output:
        print(f"Updated frontend data: {frontend_output}")
    if args.insert_db:
        inserted = insert_features_to_postgis(features, args.db_dsn, args.db_schema)
        print(f"Inserted {inserted} new GIR rows into {args.db_schema}.gir_locations.")
    if nlp_model is None:
        print("SpaCy model not loaded. Known-place fallback was used.")
    if args.include_facebook_csv:
        print("Facebook data was imported from CSV, not scraped directly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
