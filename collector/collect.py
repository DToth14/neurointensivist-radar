"""Fetch neurocritical-care *physician* vacancies from permitted job APIs.

No unsupported promise of 100% coverage. Errors preserve existing records.
Setup: configure data/sources.json and optional API-key environment variables.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
AGENT = "NeurointensivistRadar/1.0 (public-job-listing-monitor; respectful-fetches)"
TIMEOUT = 18
UTC = timezone.utc
MAX_KEEP_DAYS = int(os.getenv("MAX_KEEP_DAYS", "45"))
LOG = logging.getLogger("radar")
HEADERS = {"User-Agent": AGENT, "Accept": "application/json"}

STATE_ABBR = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
    "colorado":"CO","connecticut":"CT","delaware":"DE","district of columbia":"DC",
    "florida":"FL","georgia":"GA","hawaii":"HI","idaho":"ID","illinois":"IL",
    "indiana":"IN","iowa":"IA","kansas":"KS","kentucky":"KY","louisiana":"LA",
    "maine":"ME","maryland":"MD","massachusetts":"MA","michigan":"MI",
    "minnesota":"MN","mississippi":"MS","missouri":"MO","montana":"MT",
    "nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ",
    "new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND",
    "ohio":"OH","oklahoma":"OK","oregon":"OR","pennsylvania":"PA",
    "rhode island":"RI","south carolina":"SC","south dakota":"SD","tennessee":"TN",
    "texas":"TX","utah":"UT","vermont":"VT","virginia":"VA","washington":"WA",
    "west virginia":"WV","wisconsin":"WI","wyoming":"WY","puerto rico":"PR",
}
VALID_STATES = set(STATE_ABBR.values())
EXCLUDE_TITLE = re.compile(
    r"\b(?:nurse|nursing|registered nurse|\brn\b|\bnp\b|\bpa\b|"
    r"physician assistant|advanced practice|\bapp\b|pharmacist|pharmacy|"
    r"resident|residency|fellowship|\bfellow\b|technician|therapist|"
    r"research coordinator|medical assistant|critical care nurse|"
    r"social worker|medical coder|medical editor|recruiter)\b", re.I,
)
SPECIFIC = re.compile(r"neuro[ -]?intensivist|neuro[ -]?critical\s+care|neuro[ -]?icu|neuroscience\s+critical\s+care|neurologic\s+critical\s+care|neuro\s+intensive\s+care", re.I)
PHYSICIAN = re.compile(r"\b(physician|md/do|m\.d\.|d\.o\.|intensivist|attending|medical director|faculty|neurologist|neurosurgeon)\b", re.I)
TITLE_PREFIX = re.compile(r"\b(?:neuro[ -]?critical|neuro[ -]?intensivist|neuro[ -]?icu)\b", re.I)
HTML_TAG = re.compile(r"<[^>]+>")


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utcnow().isoformat(timespec="seconds").replace("+00:00", "Z")


def plain(s: object, limit=1600) -> str:
    value = html.unescape(html.unescape(str(s or "")))
    return re.sub(r"\s+", " ", HTML_TAG.sub(" ", value)).strip()[:limit]


def clean_url(value: str) -> str:
    value = str(value or "").strip()
    parts = urlsplit(value)
    if parts.scheme not in ("https", "http") or not parts.netloc:
        return ""
    allowed = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(("utm_", "ref_", "trk", "fbclid", "gclid"))]
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), urlencode(allowed), ""))


def loc_state(location: str) -> str:
    loc = str(location or "")
    codes = re.findall(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", loc)
    for code in codes:
        if code in VALID_STATES:
            return code
    lower = loc.lower()
    for state in sorted(STATE_ABBR, key=len, reverse=True):
        if re.search(rf"\b{re.escape(state)}\b", lower):
            return STATE_ABBR[state]
    return "REMOTE" if "remote" in lower or "united states" in lower else "OTHER"


def is_physician_job(title: str, description: str = "") -> tuple[bool, str]:
    title = plain(title, 350)
    description = plain(description, 2200)
    if EXCLUDE_TITLE.search(title):
        return False, "Excluded non-attending clinician/fellowship"
    if SPECIFIC.search(title):
        # "Neuro ICU Coordinator" / RN titles are filtered above, but miscellaneous roles should not pass.
        if PHYSICIAN.search(title) or re.search(r"(?:physician|md/do|medical degree|board certif|attending|neurocritical care fellowship)", description, re.I):
            return True, "High"
        if re.search(r"\b(intensivist|neurointensivist)\b", title, re.I):
            return True, "High"
        return False, "Needs physician evidence"
    if SPECIFIC.search(description) and PHYSICIAN.search(title):
        # Avoid generic neurologist / reviewer / clinician listings that mention neuro ICU as a casual task.
        if re.search(r"(?:neuro|intensivist|critical care|medical director)", title, re.I):
            return True, "Medium"
    return False, "Not specifically neurocritical physician"


def categorize(title: str, description: str) -> str:
    txt = f"{title} {description}".lower()
    if any(t in title.lower() for t in ("director", "chief", "chair", "division head")):
        return "Leadership"
    if "tele-neuro" in txt or "telemedicine" in title.lower() or "remote" in title.lower():
        return "Tele-neurocritical"
    if "faculty" in title.lower() or "professor" in title.lower() or "academic" in title.lower():
        return "Academic"
    return "Clinical"


def stable_id(row: dict) -> str:
    parts = [plain(row.get(k), 500).lower() for k in ("title", "company", "location")]
    norm = [re.sub(r"\W+", "", p) for p in parts]
    return "ncc-" + hashlib.sha256("|".join(norm).encode("utf-8")).hexdigest()[:16]


def normalize(row: dict, source: str) -> dict | None:
    title, company = plain(row.get("title"), 300), plain(row.get("company"), 200)
    url = clean_url(row.get("url", ""))
    loc = plain(row.get("location"), 200) or "United States (unspecified)"
    desc = plain(row.get("description", ""))
    if not (title and url):
        return None
    relevant, confidence = is_physician_job(title, desc)
    if not relevant:
        return None
    posted = row.get("posted_at")
    if not isinstance(posted, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^ ]+)?", posted):
        posted = None
    job = {
        "title": title,
        "company": company or "Employer not provided",
        "location": loc,
        "state": loc_state(loc),
        "source": source,
        "sources": [source],
        "url": url,
        "posted_at": posted,
        "updated_at": row.get("updated_at"),
        "description": desc[:520],
        "salary": plain(row.get("salary"), 140),
        "employment_type": plain(row.get("employment_type"), 90),
        "workplace": plain(row.get("workplace"), 90),
        "category": categorize(title, desc),
        "confidence": confidence,
        "status": "active",
    }
    job["id"] = stable_id(job)
    return job


def get_json(url: str, params: dict | None = None, headers: dict | None = None) -> object:
    resp = requests.get(url, params=params, headers=headers or HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def from_greenhouse(token: str) -> list[dict]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", {"content": "true"})
    jobs = []
    for p in data.get("jobs", []):
        jobs.append({"title": p.get("title"), "company": token, "location": (p.get("location") or {}).get("name", ""),
            "url": p.get("absolute_url"), "description": p.get("content", ""),
            "posted_at": str(p.get("first_published", ""))[:10] or None,
            "updated_at": p.get("updated_at")})
    return jobs


def from_lever(token: str) -> list[dict]:
    data = get_json(f"https://api.lever.co/v0/postings/{token}", {"mode": "json"})
    jobs = []
    for p in data:
        c = p.get("categories") or {}
        date = datetime.fromtimestamp(p["createdAt"] / 1000, UTC).date().isoformat() if p.get("createdAt") else None
        jobs.append({"title": p.get("text"), "company": token, "location": c.get("location"),
            "url": p.get("hostedUrl") or p.get("applyUrl"), "description": p.get("descriptionPlain") or " ".join(
                plain(x.get("content", "")) for x in p.get("lists", []) if isinstance(x, dict)),
            "posted_at": date, "salary": str(p.get("salaryRange", "")) if p.get("salaryRange") else "",
            "employment_type": c.get("commitment"), "workplace": p.get("workplaceType")})
    return jobs


def from_ashby(token: str) -> list[dict]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}", {"includeCompensation":"true"})
    jobs = []
    for p in data.get("jobs", []):
        compensation = (p.get("compensation") or {}).get("compensationTierSummary", "")
        jobs.append({"title": p.get("title"), "company": token, "location": p.get("location"),
            "url": p.get("jobUrl") or p.get("applyUrl"), "description": p.get("descriptionPlain") or p.get("descriptionHtml"),
            "posted_at": str(p.get("publishedAt", ""))[:10] or None, "salary": compensation,
            "employment_type": p.get("employmentType"), "workplace": p.get("workplaceType")})
    return jobs


def from_smartrecruiters(token: str) -> list[dict]:
    jobs = []
    offset = 0
    while offset < 1500:
        data = get_json(f"https://api.smartrecruiters.com/v1/companies/{token}/postings", {"limit":100,"offset":offset})
        content = data.get("content", [])
        for p in content:
            loc = p.get("location") or {}
            jobs.append({"title": p.get("name"), "company": p.get("company", {}).get("name") or token,
                "location": ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x),
                "url": p.get("ref") or f'https://jobs.smartrecruiters.com/{token}/{p.get("id", "")}',
                "description": p.get("department", {}).get("label", ""),
                "posted_at": str(p.get("releasedDate", ""))[:10] or None,
                "employment_type": p.get("typeOfEmployment", {}).get("label", "")})
        if not content or len(content) < 100:
            break
        offset += len(content)
    return jobs


def from_workday(item: dict) -> list[dict]:
    # config: {"host":"hospital.wd5.myworkdayjobs.com", "tenant":"hospital", "site":"External"}
    host = item["host"].strip().replace("https://", "").rstrip("/")
    tenant, site = item["tenant"].strip(), item["site"].strip()
    if not re.fullmatch(r"[A-Za-z0-9.-]+\.myworkdayjobs\.com", host):
        raise ValueError("Unsafe/invalid Workday host")
    if not all(re.fullmatch(r"[\w-]+", x) for x in (tenant, site)):
        raise ValueError("Invalid Workday tenant or site")
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    jobs = []
    for term in ("neurocritical", "neurointensivist", "neuro ICU"):
        for offset in range(0, 100, 20):
            resp = requests.post(url, json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term}, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
            postings = payload.get("jobPostings", [])
            for p in postings:
                ext = p.get("externalPath", "")
                url_job = f'https://{host}/{site}{ext}' if ext.startswith("/") else ""
                jobs.append({"title": p.get("title"), "company": item.get("name", tenant),
                    "location": p.get("locationsText") or p.get("bulletFields", [""])[0],
                    "url": url_job, "description": p.get("title", "") + " " + " ".join(map(str, p.get("bulletFields", []))),
                    "posted_at": None})
            if len(postings) < 20:
                break
    return jobs


def from_serpapi(api_key: str, cfg: dict) -> list[dict]:
    queries = cfg.get("serpapi_queries") or ["neurointensivist"]
    regions = cfg.get("serpapi_regions") or ["United States"]
    combinations = [(q, loc) for q in queries for loc in regions]
    # Rotate to cover all search terms/regions over time without high per-hour billing.
    max_scans = min(int(os.getenv("MAX_SERPAPI_QUERIES_PER_RUN", "2")), len(combinations))
    start = int(utcnow().timestamp() // 3600 * max_scans) % len(combinations)
    selected = [combinations[(start + i) % len(combinations)] for i in range(max_scans)]
    rows = []
    for q, loc in selected:
        data = get_json("https://serpapi.com/search.json", {
            "engine":"google_jobs", "api_key":api_key, "q":q, "location":loc, "hl":"en", "gl":"us"
        })
        if data.get("error"):
            raise RuntimeError(f"SerpApi error: {data['error']}")
        for p in data.get("jobs_results", []):
            applications = p.get("apply_options") or []
            url = next((a.get("link") for a in applications if a.get("link")), "")
            url = url or p.get("share_link", "")
            rows.append({"title":p.get("title"), "company":p.get("company_name"), "location":p.get("location"),
                "url":url, "description":p.get("description"), "salary":(p.get("detected_extensions") or {}).get("salary", ""),
                "workplace":"Remote" if (p.get("detected_extensions") or {}).get("work_from_home") else "",
                "posted_at":None})
        time.sleep(.5)
    return rows


def from_adzuna(app_id: str, app_key: str) -> list[dict]:
    jobs = []
    for q in ("neurocritical care physician", "neurointensivist"):
        data = get_json("https://api.adzuna.com/v1/api/jobs/us/search/1", {
            "app_id":app_id, "app_key":app_key, "results_per_page":50, "what":q, "content-type":"application/json"
        })
        for p in data.get("results", []):
            loc = p.get("location") or {}
            jobs.append({"title":p.get("title"), "company":(p.get("company") or {}).get("display_name"),
                "location":loc.get("display_name", ""), "url":p.get("redirect_url"),
                "description":p.get("description"), "posted_at":str(p.get("created", ""))[:10],
                "salary": f'${p["salary_min"]:,.0f}–${p["salary_max"]:,.0f}' if p.get("salary_min") and p.get("salary_max") else ""})
    return jobs


def from_usajobs(key: str, user_email: str) -> list[dict]:
    rows = []
    headers = {"Host":"data.usajobs.gov", "User-Agent": user_email, "Authorization-Key": key, "Accept":"application/json"}
    for query in ("neurocritical", "neurointensivist", "neuro ICU"):
        data = get_json("https://data.usajobs.gov/api/search", {"Keyword":query,"ResultsPerPage":100}, headers)
        for p in (data.get("SearchResult") or {}).get("SearchResultItems", []):
            obj = p.get("MatchedObjectDescriptor") or {}
            details = obj.get("UserArea", {}).get("Details", {})
            locs = obj.get("PositionLocation") or []
            rows.append({"title":obj.get("PositionTitle"), "company":obj.get("OrganizationName"),
                "location":locs[0].get("LocationName") if locs else "United States",
                "url":obj.get("PositionURI"),
                "description":f'{obj.get("PositionTitle", "")} {details.get("JobSummary", "")} {details.get("MajorDuties", "")}',
                "posted_at":str(obj.get("PublicationStartDate", ""))[:10],
                "salary": str(obj.get("PositionRemuneration", ""))[:160]})
    return rows


def combine_job(previous: dict, newest: dict, now: str) -> dict:
    merged = {**previous, **newest}
    merged["first_seen"] = previous.get("first_seen") or now
    merged["last_seen"] = now
    merged["sources"] = sorted(set(previous.get("sources", [])) | set(newest.get("sources", [])))
    merged["source"] = ", ".join(merged["sources"])
    merged["posted_at"] = newest.get("posted_at") or previous.get("posted_at")
    merged["salary"] = newest.get("salary") or previous.get("salary") or ""
    merged["description"] = max([previous.get("description", ""), newest.get("description", "")], key=len)
    merged["status"] = "active"
    return merged



def send_telegram_alerts(new_jobs: list[dict]) -> None:
    """Optional push notification for genuinely newly detected roles.

    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. This does not make
    upstream publisher detection instantaneous; it runs after each scan.
    """
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat and new_jobs):
        return
    jobs = new_jobs[:12]
    lines = [f"🧠 Neurointensivist Radar: {len(new_jobs)} newly detected job(s)"]
    for j in jobs:
        lines.extend(["", f"• {j['title']}", f"{j['company']} · {j['location']}", j['url']])
    if len(new_jobs)>len(jobs):
        lines.extend(["", f"Plus {len(new_jobs)-len(jobs)} more in the dashboard."])
    message = "\n".join(lines)
    # Telegram sendMessage has a 4096-character text limit.
    if len(message) > 4000:
        message = message[:3997] + "..."
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": message, "disable_web_page_preview": "true"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()


def run() -> dict:
    cfg = json.loads((DATA_DIR / "sources.json").read_text())
    previous = json.loads((DATA_DIR / "jobs.json").read_text())
    earlier = {p["id"]:p for p in previous.get("jobs", [])}
    # Do not throw away starter listings merely because a vendor is not yet connected.
    output = {**earlier}
    now = iso_now()
    status = []
    fresh_ids = set()
    ok_count = 0

    def ingest(name: str, fn, *args) -> None:
        nonlocal ok_count
        try:
            rows = fn(*args)
            accepted = 0
            for candidate in rows:
                job = normalize(candidate, name)
                if not job:
                    continue
                identifier = job["id"]
                # Cross-site duplication: stable title/employer/location key, preserve one record.
                prev = output.get(identifier, {})
                output[identifier] = combine_job(prev, job, now)
                fresh_ids.add(identifier)
                accepted += 1
            ok_count += 1
            status.append({"source":name,"state":"ok","fetched":len(rows),"matched":accepted})
            LOG.info("%s: fetched %d; physician matches %d",name,len(rows),accepted)
        except (requests.RequestException, ValueError, RuntimeError, KeyError, TypeError) as exc:
            status.append({"source":name,"state":"error","message":str(exc)[:160]})
            LOG.warning("%s failed: %s", name, exc)

    for category, fetcher in (("greenhouse",from_greenhouse),("lever",from_lever),
                                ("ashby",from_ashby),("smartrecruiters",from_smartrecruiters),
                                ("workday",from_workday)):
        for index, token in enumerate(cfg.get(category, [])):
            ingest(f"{category}:{token if isinstance(token,str) else token.get('name',index)}", fetcher, token)
            time.sleep(.2)

    if os.getenv("SERPAPI_KEY"):
        ingest("Google Jobs (SerpApi)", from_serpapi, os.environ["SERPAPI_KEY"], cfg)
    else:
        status.append({"source":"Google Jobs (SerpApi)","state":"not_configured","message":"Add SERPAPI_KEY secret"})
    if os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"):
        ingest("Adzuna", from_adzuna, os.environ["ADZUNA_APP_ID"], os.environ["ADZUNA_APP_KEY"])
    else:
        status.append({"source":"Adzuna","state":"not_configured","message":"Add ADZUNA_APP_ID and ADZUNA_APP_KEY"})
    if os.getenv("USAJOBS_API_KEY") and os.getenv("USAJOBS_EMAIL"):
        ingest("USAJOBS", from_usajobs, os.environ["USAJOBS_API_KEY"], os.environ["USAJOBS_EMAIL"])
    else:
        status.append({"source":"USAJOBS","state":"not_configured","message":"Add USAJOBS_API_KEY and USAJOBS_EMAIL"})

    # Do not erroneously call a job closed simply because an API missed a query or failed.
    cutoff = utcnow() - timedelta(days=MAX_KEEP_DAYS)
    for identifier, job in list(output.items()):
        try:
            seen = datetime.fromisoformat(str(job.get("last_seen", "")).replace("Z", "+00:00"))
        except ValueError:
            seen = cutoff
        if seen < cutoff:
            del output[identifier]
        elif identifier not in fresh_ids and job.get("status") != "unverified":
            job["status"] = "not_recently_seen"

    newest_ids = [i for i in fresh_ids if i not in earlier]
    dataset = {
        "meta": {
            "project":"Neurointensivist Radar",
            "generated_at": now,
            "mode": "live" if ok_count else "starter",
            "note": "A monitored subset of publicly accessible job listings, not an exhaustive census. Date reflects detection time.",
            "scan_interval_minutes":60,
            "source_status":status,
            "new_detected":len(newest_ids),
            "active_count":sum(1 for j in output.values() if j.get("status") == "active"),
            "monitored_sources":ok_count
        },
        "jobs": sorted(output.values(), key=lambda j:(j.get("last_seen") or "",j.get("updated_at") or ""),reverse=True)
    }
    rendered = json.dumps(dataset,ensure_ascii=False,indent=2)
    (DATA_DIR / "jobs.json").write_text(rendered + "\n")
    (DATA_DIR / "bootstrap.js").write_text("window.RADAR_BOOTSTRAP = " + json.dumps(dataset,ensure_ascii=False,separators=(",", ":")) + ";\n")
    # Delivery failure must never discard a successful job scan.
    if ok_count and newest_ids:
        try:
            send_telegram_alerts([output[i] for i in newest_ids])
        except requests.RequestException as exc:
            LOG.warning("Telegram alert failed (job data retained): %s", type(exc).__name__)
    LOG.info("Finished: %s successful sources, %s tracked jobs (%s newly detected)",ok_count,len(dataset["jobs"]),len(newest_ids))
    return dataset


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        result = run()
        # Distinguish completed-but-unconfigured runs from success in Actions logs.
        if not result["meta"]["monitored_sources"]:
            LOG.warning("No connected sources succeeded. Starter listings remain visible; configure an API key or ATS board.")
    except Exception:
        LOG.exception("Fatal scanner failure; existing data retained")
        sys.exit(1)
