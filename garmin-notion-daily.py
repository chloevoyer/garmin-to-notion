"""
Garmin → Notion Daily Rollup — v3.7.5

Changes from v3.7.4:
• Fix: **Activities were bucketed by GMT**. Now use **startTimeLocal** first for day assignment & filtering.
• Adds a log when today's activities are found/aggregated.
"""

from datetime import date, datetime, timedelta, timezone
from collections import defaultdict, Counter
import os, sys, time, calendar, re
from dotenv import load_dotenv
from notion_client import Client
from garminconnect import Garmin
import garth

# -----------------------------
# Helpers
# -----------------------------

def iso_date(d: date) -> str:
    return d.isoformat()

def today_local() -> date:
    return date.today()

def daterange(start: date, end_exclusive: date):
    d = start
    while d < end_exclusive:
        yield d
        d += timedelta(days=1)

def ms_to_local_iso(ms: int | None) -> str | None:
    if not ms:
        return None
    try:
        dt_utc = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        dt_local = dt_utc.astimezone()  # system local tz
        dt_local = dt_local.replace(second=0, microsecond=0)
        return dt_local.isoformat()  # 'YYYY-MM-DDTHH:MM:SS±HH:MM'
    except Exception:
        return None

def iso_week_parts(d: date):
    iso_year, iso_week, iso_weekday = d.isocalendar()
    return iso_year, iso_week, iso_weekday

def to_tokens(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    if not s:
        return []
    if any(sep in s for sep in [",", ";", "|"]):
        parts = re.split(r"[,\;\|]+", s)
    else:
        parts = s.split()
    return [p.strip() for p in parts if p.strip()]

def _first_present(dct, keys, default=None):
    for k in keys:
        if k in dct and dct.get(k) not in (None, ""):
            return dct.get(k)
    return default

# -----------------------------
# Garmin login
# -----------------------------

def login_to_garmin():
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    token_store = os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens")
    token_store = os.path.expanduser(token_store)
    mfa_code = os.getenv("GARMIN_MFA_CODE")

    if not garmin_email or not garmin_password:
        print("Missing GARMIN_EMAIL or GARMIN_PASSWORD")
        sys.exit(1)

    g = Garmin(garmin_email, garmin_password)
    try:
        if os.path.exists(token_store):
            print(f"[garmin] Using stored tokens: {token_store}")
            g.login(tokenstore=token_store)
        else:
            if mfa_code:
                print("[garmin] Non-interactive MFA login")
                client_state, _ = g.login(return_on_mfa=True)
                if client_state == "needs_mfa":
                    g.resume_login(client_state, mfa_code)
            else:
                g.login()

            if hasattr(g, "garth") and g.garth:
                os.makedirs(os.path.dirname(token_store), exist_ok=True)
                g.garth.save(token_store)
                print(f"[garmin] Saved tokens to {token_store}")

        try:
            garth.resume(token_store)
        except Exception:
            garth.login(garmin_email, garmin_password)
            garth.save(token_store)

        return g, token_store
    except Exception as e:
        print(f"[garmin] Login error: {e}")
        sys.exit(1)

# -----------------------------
# Notion schema helpers
# -----------------------------

P = {
    "Date": "Date",
    "date_key": "date_key",
    "ActivityCount": "Activities (#)",
    "ActivityDistanceMi": "Activity Distance (mi)",
    "ActivityDurationMin": "Activity Duration (min)",
    "ActivityCalories": "Activity Calories",
    "ActivityNames": "Activity Names",
    "ActivityTypes": "Activity Types",
    "ActTrainingEff": "Training Effect (list)",
    "ActAerobicEff": "Aerobic Effect (list)",
    "ActAnaerobicEff": "Anaerobic Effect (list)",
    "PrimarySport": "primary_sport",
    "ActivityTypesUnique": "activity_types_unique",
    "Steps": "Steps",
    "StepGoal": "Step Goal",
    "WalkDistanceMi": "Walk Distance (mi)",
    "SleepTotalH": "Sleep Total (h)",
    "SleepLightH": "Sleep Light (h)",
    "SleepDeepH": "Sleep Deep (h)",
    "SleepRemH": "Sleep REM (h)",
    "SleepAwakeH": "Sleep Awake (h)",
    "RestingHR": "Resting HR",
    "SleepStart": "Sleep Start (local)",
    "SleepEnd": "Sleep End (local)",
    "SS_overall": "Sleep Overall (q)",
    "SS_total_duration": "Sleep Duration (q)",
    "SS_stress": "Sleep Stress (q)",
    "SS_awake_count": "Sleep Awake Count (q)",
    "SS_rem_percentage": "Sleep REM % (q)",
    "SS_restlessness": "Sleep Restlessness (q)",
    "SS_light_percentage": "Sleep Light % (q)",
    "SS_deep_percentage": "Sleep Deep % (q)",
    "StressAvg": "Stress Avg",
    "StressMax": "Stress Max",
    "BodyBatteryAvg": "Body Battery Avg",
    "BodyBatteryMin": "Body Battery Min",
    "IntensityMin": "Intensity Minutes",
    "IntensityMod": "Intensity Moderate (min)",
    "IntensityVig": "Intensity Vigorous (min)",
    "HRV": "HRV",
    "WeightLb": "Weight (lb)",
    "BMI": "BMI",
    "has_sleep": "has_sleep",
    "has_steps": "has_steps",
    "has_activities": "has_activities",
    "has_weight": "has_weight",
    "weekday": "weekday",
    "iso_week": "iso_week",
    "year": "year",
    "month": "month"
}

def retrieve_db_types(notion: Client, database_id: str) -> dict:
    info = notion.databases.retrieve(database_id=database_id)
    props = info.get("properties", {})
    types = {}
    for name, meta in props.items():
        t = meta.get("type")
        types[name] = t
    return types

def as_prop_for_type(ptype: str, value):
    if ptype == "date":
        if isinstance(value, str):
            if "T" in value and ("+" in value or "Z" in value):
                iso_val = value
            else:
                if " " in value:
                    try:
                        dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
                        iso_val = dt.strftime("%Y-%m-%dT%H:%M:00")
                    except Exception:
                        iso_val = value
                else:
                    iso_val = value
        else:
            iso_val = value
        return {"date": None if not value else {"start": iso_val}}
    if ptype == "number":
        try:
            return {"number": None if value is None else float(value)}
        except Exception:
            return {"number": None}
    if ptype == "checkbox":
        return {"checkbox": bool(value)}
    if ptype == "title":
        text = "" if value is None else str(value)
        return {"title": [{"type": "text", "text": {"content": text[:2000]}}]}
    if ptype == "select":
        if not value:
            return {"select": None}
        return {"select": {"name": str(value)}}
    if ptype == "multi_select":
        tokens = to_tokens(value)
        return {"multi_select": [{"name": t} for t in tokens]}
    text = "" if value is None else str(value)
    return {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]}

def _query_pages_for_date(notion: Client, database_id: str, date_prop_for_filter: str | None, title_name: str | None, d_iso: str):
    """Return all pages that match the date (or title) filter, across pagination.
    First try date == d_iso; if none, try range [d_iso, d_iso+1).
    """
    filter_obj = None
    if date_prop_for_filter:
        # 1) Try exact date equality (works for date-only fields)
        filter_obj = {"property": date_prop_for_filter, "date": {"equals": d_iso}}
        results = []
        start_cursor = None
        while True:
            kwargs = {"database_id": database_id, "filter": filter_obj, "page_size": 100}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor
            resp = notion.databases.query(**kwargs)
            batch = resp.get("results", [])
            results.extend(batch)
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
        if results:
            print(f"[notion] Match via {date_prop_for_filter} == {d_iso}: {len(results)} page(s)")
            return results

        # 2) Range fallback: [on_or_after d_iso, before d_iso+1]
        from_iso = d_iso
        # Simple next-day ISO (date-only)
        y, m, d = map(int, d_iso.split('-'))
        from datetime import date, timedelta
        to_iso = (date(y, m, d) + timedelta(days=1)).isoformat()
        filter_obj = {
            "and": [
                {"property": date_prop_for_filter, "date": {"on_or_after": from_iso}},
                {"property": date_prop_for_filter, "date": {"before": to_iso}},
            ]
        }
        results = []
        start_cursor = None
        while True:
            kwargs = {"database_id": database_id, "filter": filter_obj, "page_size": 100}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor
            resp = notion.databases.query(**kwargs)
            batch = resp.get("results", [])
            results.extend(batch)
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
        if results:
            print(f"[notion] Match via {date_prop_for_filter} in [{from_iso},{to_iso}): {len(results)} page(s)")
            return results

    if title_name:
        filter_obj = {"property": title_name, "title": {"equals": d_iso}}
        results = []
        start_cursor = None
        while True:
            kwargs = {"database_id": database_id, "filter": filter_obj, "page_size": 100}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor
            resp = notion.databases.query(**kwargs)
            batch = resp.get("results", [])
            results.extend(batch)
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
        if results:
            print(f"[notion] Match via Title == {d_iso}: {len(results)} page(s)")
            return results

    print(f"[notion] No page found for {d_iso} via date or title filters.")
    return []

def _archive_duplicates(notion: Client, pages: list, keep_idx: int = 0):
    """Archive all but one page from the list."""
    for i, p in enumerate(pages):
        if i == keep_idx:
            continue
        try:
            notion.pages.update(page_id=p["id"], archived=True)
            print(f"[notion] Archived duplicate page for date: {p['id']}")
        except Exception as e:
            print(f"[notion] Failed to archive duplicate {p.get('id')}: {e}")

def _is_writable_type(ptype: str) -> bool:
    # Skip read-only types
    return ptype in {
        "title","rich_text","number","select","multi_select","date","checkbox","url",
        "email","phone_number","files","people","relation","status"
    }

def _empty_for_type(ptype: str):
    # Empties to clear fields when overwriting
    return {
        "title": [],
        "rich_text": [],
        "number": None,
        "select": None,
        "multi_select": [],
        "date": None,
        "checkbox": False,
        "url": None,
        "email": None,
        "phone_number": None,
        "files": [],
        "people": [],
        "relation": [],
        "status": None,
    }.get(ptype, None)

def _build_full_properties(db_types: dict, props: dict, d_iso: str, title_name: str | None, preferred_date_names: list[str]) -> dict:
    """Return a properties dict that sets *all* writable properties.
    Missing values are explicitly cleared, so the page is effectively overwritten.
    Ensures Title is d_iso, and sets preferred dates when they exist in schema.
    Also writes `Last Synced At` (date) if present in the schema.
    """
    properties = {}

    # Title
    if title_name:
        properties[title_name] = as_prop_for_type("title", d_iso)

    # Ensure both preferred date fields (if present) are set to d_iso
    for dname in preferred_date_names:
        if dname and db_types.get(dname) == "date":
            properties[dname] = as_prop_for_type("date", d_iso)

    # Sync stamp if DB has it
    if db_types.get("Last Synced At") == "date":
        from datetime import datetime, timezone
        properties["Last Synced At"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}

    # Fill/clear rest
    for key, ptype in db_types.items():
        if not _is_writable_type(ptype):
            continue
        if title_name and key == title_name:
            continue
        if key in preferred_date_names and db_types.get(key) == "date":
            continue
        if key == "Last Synced At":
            continue

        if key in props:
            properties[key] = as_prop_for_type(ptype, props[key])
        else:
            # Clear missing fields when overwriting
            properties[key] = as_prop_for_type(ptype, _empty_for_type(ptype))

    return properties

from datetime import datetime, timezone

def _normalize_value_for_compare(ptype: str, prop_value):
    """Return a simple comparable value for a Notion property value."""
    if ptype in ("title", "rich_text"):
        if isinstance(prop_value, list):
            return "".join([x.get("plain_text","") for x in prop_value])
        return ""
    if ptype == "number":
        return prop_value
    if ptype == "select":
        return (prop_value or {}).get("name")
    if ptype == "multi_select":
        names = [x.get("name") for x in (prop_value or [])]
        return sorted([n for n in names if n is not None])
    if ptype == "date":
        # Normalize to ISO date string (YYYY-MM-DD) if present
        if prop_value and isinstance(prop_value, dict):
            start = prop_value.get("start")
            if start:
                return str(start)[:10]
        return None
    if ptype == "checkbox":
        return bool(prop_value)
    if ptype in ("url","email","phone_number"):
        return prop_value
    if ptype == "status":
        return (prop_value or {}).get("name")
    if ptype in ("files","people","relation"):
        # Compare lengths only (cheap heuristic)
        return len(prop_value or [])
    return prop_value

def _page_current_values(page: dict, db_types: dict) -> dict:
    cur = {}
    props = page.get("properties", {})
    for key, meta in props.items():
        ptype = meta.get("type")
        if not ptype or key not in db_types:
            continue
        raw = meta.get(ptype)
        cur[key] = _normalize_value_for_compare(ptype, raw)
    return cur

def _props_target_values(db_types: dict, properties: dict) -> dict:
    tgt = {}
    for key, ptype in db_types.items():
        if key not in properties:
            continue
        raw = properties[key].get(ptype if ptype != "title" else "title")
        tgt[key] = _normalize_value_for_compare(ptype, raw)
    return tgt

def _diff_page(page: dict, db_types: dict, properties: dict) -> list[tuple[str, object, object]]:
    cur = _page_current_values(page, db_types)
    tgt = _props_target_values(db_types, properties)
    diffs = []
    for key in tgt.keys():
        if key not in cur:
            diffs.append((key, None, tgt[key]))
        elif cur[key] != tgt[key]:
            diffs.append((key, cur[key], tgt[key]))
    return diffs

def ensure_database(notion: Client, db_id: str | None, parent_page_id: str | None) -> str:
    if db_id:
        return db_id
    if not parent_page_id:
        print("Provide NOTION_DB_ID or NOTION_PARENT_PAGE_ID")
        sys.exit(1)

    properties = {
"Date": {"title": {}},  # Title property (page title) is "Date"
            P["Date"]: {"date": {}},
            P["date_key"]: {"date": {}},
            P["ActivityNames"]: {"rich_text": {}},
    }
    created = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Garmin Daily Rollup"}}],
        properties=properties,
    )
    return created["id"]



def upsert_row(notion: Client, database_id: str, d_iso: str, props: dict, overwrite: bool = True):
    """
    Strict upsert with dedupe:
      - Title is always the ISO date (d_iso)
      - Prefer a true date property for identity; if duplicates found, archive extras
      - Set both `date_key` and `Date` if those properties exist
      - If overwrite=True (default): set *all* writable properties every run (clears missing)
      - Otherwise: only update properties provided in props
    """
    db_types = retrieve_db_types(notion, database_id)

    # Identify title prop
    title_name = None
    for name, t in db_types.items():
        if t == "title":
            title_name = name
            break

    # Prefer date key order
    preferred_dates = ["date_key", "Date"]
    candidate_order = [c for c in preferred_dates if db_types.get(c) == "date"] + \
                      [k for k, t in db_types.items() if t == "date" and k not in preferred_dates]

    date_prop_for_filter = None
    for cand in candidate_order:
        if db_types.get(cand) == "date":
            date_prop_for_filter = cand
            break

    # Build properties for update/create
    preferred_date_names = [d for d in preferred_dates if db_types.get(d) == "date"]

    if overwrite:
        properties = _build_full_properties(db_types, props, d_iso, title_name, preferred_date_names)
    else:
        # Update only provided props + enforce title & preferred dates
        properties = {}
        if title_name:
            properties[title_name] = as_prop_for_type("title", d_iso)
        for dname in preferred_date_names:
            properties[dname] = as_prop_for_type("date", d_iso)
        for key, val in props.items():
            if title_name and key == title_name:
                continue
            if key in preferred_date_names and db_types.get(key) == "date":
                continue
            ptype = db_types.get(key)
            if not ptype:
                continue
            properties[key] = as_prop_for_type(ptype, val)

    # Query all pages that match this date
    pages = _query_pages_for_date(notion, database_id, date_prop_for_filter, title_name, d_iso)

    if not pages:
        # Create new
        notion.pages.create(parent={"database_id": database_id}, properties=properties)
        print(f"[notion] Created page for {d_iso}")
        return

    # If duplicates exist, archive extras but keep the oldest created
    if len(pages) > 1:
        try:
            pages.sort(key=lambda p: p.get("created_time", ""))
        except Exception:
            pass
        _archive_duplicates(notion, pages, keep_idx=0)
        master = pages[0]
    else:
        master = pages[0]

    # Update master page
    diffs = _diff_page(master, db_types, properties)
    if diffs:
        print(f"[notion] Changes for {d_iso} ({master['id']}):")
        for k, old, new in diffs:
            print(f"  - {k}: {old!r} -> {new!r}")
    else:
        print(f"[notion] No value changes detected for {d_iso} — updating anyway to enforce overwrite")

    notion.pages.update(page_id=master["id"], properties=properties)
    print(f"[notion] Overwrote page {master['id']} for {d_iso}" if overwrite else f"[notion] Updated page {master['id']} for {d_iso}")

    # Fetch & confirm
    try:
        refreshed = notion.pages.retrieve(master["id"])
        post_diffs = _diff_page(refreshed, db_types, properties)
        if post_diffs:
            print(f"[notion] WARNING: Differences remain after update: {post_diffs[:5]} ...")
        else:
            print(f"[notion] Confirmed update for {d_iso}.")
    except Exception as e:
        print(f"[notion] Could not re-fetch page after update: {e}")

# -----------------------------
# Garmin data fetchers
# -----------------------------

def fetch_steps_for_date(g: Garmin, d: date):
    try:
        arr = g.get_daily_steps(iso_date(d), iso_date(d)) or []
        if not arr:
            return None, None, None
        e = arr[0]
        total_distance_m = e.get("totalDistance") or 0
        miles = round((total_distance_m or 0) / 1609.34, 2)
        return e.get("totalSteps"), e.get("stepGoal"), miles
    except Exception:
        return None, None, None

def _format_score_value(source: dict, key_src: str):
    """
    Return 'value(qualifier_key)' with NO 'metric=' prefix.
    Examples: 'None(EXCELLENT)', '22(moderate)'
    """
    if not isinstance(source, dict):
        return None
    item = source.get(key_src) or {}
    if not isinstance(item, dict):
        return None
    score = item.get("score")
    if score is None:
        score = item.get("value", item.get("percentage"))
    qual = item.get("qualifierKey", item.get("qualifier"))
    score_str = "None" if score is None else str(score)
    return f"{score_str}({qual})" if qual is not None else score_str

def _sleep_scores_from(data: dict) -> dict:
    scores = {}
    source = data.get("sleepScores") or data.get("dailySleepDTO", {}).get("sleepScores") or {}

    def qual(key):
        v = source.get(key) or {}
        return v.get("qualifierKey") or v.get("qualifier") or None

    # Simple qualifiers
    scores["overall"] = qual("overall")
    scores["total_duration"] = qual("totalDuration")
    scores["stress"] = qual("stress")
    scores["restlessness"] = qual("restlessness")  # restored

    # "value(qualifier)" strings (no prefixes)
    scores["awake_count_fmt"] = _format_score_value(source, "awakeCount")
    scores["rem_percentage_fmt"] = _format_score_value(source, "remPercentage")
    scores["light_percentage_fmt"] = _format_score_value(source, "lightPercentage")
    scores["deep_percentage_fmt"] = _format_score_value(source, "deepPercentage")
    # Alt keys safety
    if scores["light_percentage_fmt"] is None:
        scores["light_percentage_fmt"] = _format_score_value(source, "light_percentage")
    if scores["deep_percentage_fmt"] is None:
        scores["deep_percentage_fmt"] = _format_score_value(source, "deep_percentage")

    return scores

def fetch_sleep_for_date(g: Garmin, d: date):
    try:
        data = g.get_sleep_data(iso_date(d)) or {}
        daily = data.get("dailySleepDTO") or {}
        total = sum((daily.get(k) or 0) for k in ["deepSleepSeconds","lightSleepSeconds","remSleepSeconds"])
        start_ms = daily.get("sleepStartTimestampGMT") or data.get("sleepStartTimestampGMT") or daily.get("sleepStartTimestampLocal")
        end_ms = daily.get("sleepEndTimestampGMT") or data.get("sleepEndTimestampGMT") or daily.get("sleepEndTimestampLocal")

        start_local_iso = ms_to_local_iso(start_ms)
        end_local_iso = ms_to_local_iso(end_ms)

        scores = _sleep_scores_from(data)

        return {
            "total_h": round(total / 3600, 2),
            "light_h": round((daily.get("lightSleepSeconds") or 0) / 3600, 2),
            "deep_h": round((daily.get("deepSleepSeconds") or 0) / 3600, 2),
            "rem_h":  round((daily.get("remSleepSeconds") or 0) / 3600, 2),
            "awake_h":round((daily.get("awakeSleepSeconds") or 0) / 3600, 2),
            "resting_hr": data.get("restingHeartRate") or daily.get("restingHeartRate"),
            "start_local": start_local_iso,
            "end_local": end_local_iso,
            "scores": scores,
        }
    except Exception:
        return {}

def fetch_activities_bulk(g: Garmin, start_d: date):
    try:
        acts = g.get_activities(0, 500) or []
    except Exception:
        acts = []
    keep = []
    for a in acts:
        dt_str = (a.get("startTimeLocal") or a.get("startTimeGMT") or "")[:10]
        try:
            if dt_str and datetime.strptime(dt_str, "%Y-%m-%d").date() >= start_d:
                keep.append(a)
        except Exception:
            pass
    return keep

def aggregate_activities_by_date(activities):
    by_date = defaultdict(lambda: {
        "count":0,"dist_mi":0.0,"dur_min":0.0,"cal":0.0,
        "names": [], "types": [], "te": [], "ae": [], "ane": []
    })
    for a in activities:
        dt = (a.get("startTimeLocal") or a.get("startTimeGMT") or "")[:10]
        if not dt:
            continue
        entry = by_date[dt]
        entry["count"] += 1
        entry["dist_mi"] += (a.get("distance") or 0) / 1609.34
        entry["dur_min"] += (a.get("duration") or 0) / 60.0
        entry["cal"] += float(a.get("calories") or 0)

        name = _first_present(a, ["activityName","activityId"], "")
        tdict = a.get("activityType") or {}
        atype = tdict.get("typeKey") if isinstance(tdict, dict) else ""

        te_label = _first_present(a, ["trainingEffectLabel","overallTrainingEffectMessage","trainingEffectMessage"])
        ae_msg = _first_present(a, ["aerobicTrainingEffectMessage","aerobicTrainingEffectLabel"])
        ane_msg = _first_present(a, ["anaerobicTrainingEffectMessage","anaerobicTrainingEffectLabel"])

        if name: entry["names"].append(str(name))
        if atype: entry["types"].append(str(atype))
        if te_label: entry["te"].append(str(te_label))
        if ae_msg: entry["ae"].append(str(ae_msg))
        if ane_msg: entry["ane"].append(str(ane_msg))

    for dt, v in by_date.items():
        v["dist_mi"] = round(v["dist_mi"], 2)
        v["dur_min"] = round(v["dur_min"], 2)
        v["cal"] = round(v["cal"], 0)

        type_counts = Counter(v["types"])
        primary = type_counts.most_common(1)[0][0] if type_counts else ""
        unique_types = " ".join(sorted(set(v["types"])))

        v["primary"] = primary
        v["types_unique"] = unique_types

        v["names"] = " ".join(v["names"])
        v["types"] = " ".join(v["types"])
        v["te"]    = " ".join(v["te"])
        v["ae"]    = " ".join(v["ae"])
        v["ane"]   = " ".join(v["ane"])
    return by_date

def map_intensity_last_n(n_days=50):
    out = {}
    try:
        rows = garth.DailyIntensityMinutes.list(period=n_days) or []
        for r in rows:
            d = r.calendar_date.isoformat()
            mod = getattr(r, "moderate_value", None)
            vig = getattr(r, "vigorous_value", None)
            total = None
            if mod is not None or vig is not None:
                total = (mod or 0) + 2 * (vig or 0)
            out[d] = {"total": total, "mod": mod, "vig": vig}
    except Exception:
        pass
    return out

def map_hrv_last_n(n_days=50):
    out = {}
    try:
        rows = garth.DailyHRV.list(period=n_days) or []
        for r in rows:
            d = r.calendar_date.isoformat()
            out[d] = getattr(r, "last_night_avg", None) or getattr(r, "weekly_avg", None)
    except Exception:
        pass
    return out

def main():
    load_dotenv()

    notion_token = os.getenv("NOTION_TOKEN")
    database_id = (os.getenv("NOTION_DB_ID") or "").strip() or None
    parent_page_id = (os.getenv("NOTION_PARENT_PAGE_ID") or "").strip() or None
    if not notion_token:
        print("Missing NOTION_TOKEN")
        sys.exit(1)

    end_d_inclusive = today_local() if os.getenv('INCLUDE_TODAY', '1') != '0' else today_local() - timedelta(days=1)
    window_days = int(os.getenv('WINDOW_DAYS', '5'))
    start_d = end_d_inclusive - timedelta(days=window_days - 1)

    g, token_store = login_to_garmin()
    notion = Client(auth=notion_token)
    dbid = ensure_database(notion, database_id, parent_page_id)

    intensity_map = map_intensity_last_n(5)
    hrv_map = map_hrv_last_n(5)

    activities = fetch_activities_bulk(g, start_d)
    act_by_date = aggregate_activities_by_date(activities)

    created_or_updated = 0
    for d in daterange(start_d, end_d_inclusive + timedelta(days=1)):
        d_iso = iso_date(d)
        iso_y, iso_w, _ = iso_week_parts(d)

        steps, step_goal, walk_mi = fetch_steps_for_date(g, d)
        sleep = fetch_sleep_for_date(g, d) or {}

        bb_avg = bb_min = stress_avg = stress_max = None
        try:
            daily_bb = garth.DailyBodyBatteryStress.get(d_iso)
            stress_avg = getattr(daily_bb, "avg_stress_level", None)
            stress_max = getattr(daily_bb, "max_stress_level", None)
            levels = [getattr(x, "level", None) for x in getattr(daily_bb, "body_battery_readings", [])]
            levels = [lv for lv in levels if isinstance(lv, (int, float))]
            if levels:
                bb_avg = round(sum(levels) / len(levels), 1)
                bb_min = min(levels)
        except Exception:
            pass

        inten = intensity_map.get(d_iso, {})
        intensity_total = inten.get("total")
        intensity_mod = inten.get("mod")
        intensity_vig = inten.get("vig")

        hrv = hrv_map.get(d_iso)

        weight_lb = bmi = None
        try:
            w = garth.WeightData.get(d_iso)
            if w:
                grams = getattr(w, "weight", None)
                if grams is not None:
                    kg = grams / 1000.0
                    weight_lb = round(kg * 2.2046226218, 2)
                bmi = getattr(w, "bmi", None)
        except Exception:
            pass

        act = act_by_date.get(d_iso, {
            "count":0,"dist_mi":0.0,"dur_min":0.0,"cal":0,
            "names":"", "types":"", "te":"", "ae":"", "ane":"",
            "primary":"", "types_unique":""
        })

        props = {
            P["date_key"]: d_iso,
            P["weekday"]: calendar.day_name[d.weekday()],
            P["iso_week"]: iso_w,
            P["year"]: d.year,
            P["month"]: d.month,

            P["ActivityCount"]: act["count"],
            P["ActivityDistanceMi"]: act["dist_mi"],
            P["ActivityDurationMin"]: act["dur_min"],
            P["ActivityCalories"]: act["cal"],
            P["ActivityNames"]: act.get("names", ""),
            P["ActivityTypes"]: act.get("types", ""),
            P["PrimarySport"]: act.get("primary", ""),
            P["ActivityTypesUnique"]: act.get("types_unique", ""),
            P["ActTrainingEff"]: act.get("te", ""),
            P["ActAerobicEff"]: act.get("ae", ""),
            P["ActAnaerobicEff"]: act.get("ane", ""),

            P["Steps"]: steps,
            P["StepGoal"]: step_goal,
            P["WalkDistanceMi"]: walk_mi,

            P["SleepTotalH"]: sleep.get("total_h"),
            P["SleepLightH"]: sleep.get("light_h"),
            P["SleepDeepH"]: sleep.get("deep_h"),
            P["SleepRemH"]: sleep.get("rem_h"),
            P["SleepAwakeH"]: sleep.get("awake_h"),
            P["RestingHR"]: sleep.get("resting_hr"),
            P["SleepStart"]: sleep.get("start_local"),
            P["SleepEnd"]: sleep.get("end_local"),
            P["SS_overall"]: (sleep.get("scores", {}) or {}).get("overall"),
            P["SS_total_duration"]: (sleep.get("scores", {}) or {}).get("total_duration"),
            P["SS_stress"]: (sleep.get("scores", {}) or {}).get("stress"),
            P["SS_awake_count"]: (sleep.get("scores", {}) or {}).get("awake_count_fmt"),
            P["SS_rem_percentage"]: (sleep.get("scores", {}) or {}).get("rem_percentage_fmt"),
            P["SS_restlessness"]: (sleep.get("scores", {}) or {}).get("restlessness"),
            P["SS_light_percentage"]: (sleep.get("scores", {}) or {}).get("light_percentage_fmt"),
            P["SS_deep_percentage"]: (sleep.get("scores", {}) or {}).get("deep_percentage_fmt"),

            P["StressAvg"]: stress_avg,
            P["StressMax"]: stress_max,
            P["BodyBatteryAvg"]: bb_avg,
            P["BodyBatteryMin"]: bb_min,
            P["IntensityMin"]: intensity_total,
            P["IntensityMod"]: intensity_mod,
            P["IntensityVig"]: intensity_vig,
            P["HRV"]: hrv,

            P["WeightLb"]: weight_lb,
            P["BMI"]: bmi,

            P["has_sleep"]: bool(sleep),
            P["has_steps"]: steps is not None,
            P["has_activities"]: act["count"] > 0,
            P["has_weight"]: weight_lb is not None
        }

        upsert_row(notion, dbid, d_iso, props)
        created_or_updated += 1
        time.sleep(0.05)

    print(f"Done. Upserted {created_or_updated} day rows into Notion DB {dbid}.")

if __name__ == "__main__":
    main()