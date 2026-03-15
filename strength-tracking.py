import os
from datetime import datetime, UTC, timedelta

from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient


def format_activity_type(activity_type: str, activity_name: str = "") -> tuple[str, str]:
    formatted_type = activity_type.replace('_', ' ').title() if activity_type else "Unknown"

    activity_subtype = formatted_type
    activity_type = formatted_type

    activity_mapping = {
        "Barre": "Strength",
        "Indoor Cardio": "Cardio",
        "Indoor Cycling": "Cycling",
        "Indoor Rowing": "Rowing",
        "Speed Walking": "Walking",
        "Strength Training": "Strength",
        "Treadmill Running": "Running"
    }

    if formatted_type == "Rowing V2":
        activity_type = "Rowing"
    elif formatted_type in ["Yoga", "Pilates"]:
        activity_type = "Yoga/Pilates"
        activity_subtype = formatted_type

    if formatted_type in activity_mapping:
        activity_type = activity_mapping[formatted_type]
        activity_subtype = formatted_type

    if activity_name and "meditation" in activity_name.lower():
        return "Meditation", "Meditation"
    if activity_name and "barre" in activity_name.lower():
        return "Strength", "Barre"
    if activity_name and "stretch" in activity_name.lower():
        return "Stretching", "Stretching"

    return activity_type, activity_subtype


def get_strength_activities(garmin_client: GarminClient, limit: int = 1000) -> list[dict]:
    activities = garmin_client.get_activities(0, limit)
    strength = []
    for activity in activities:
        activity_type, _ = format_activity_type(
            activity.get('activityType', {}).get('typeKey', 'Unknown'),
            activity.get('activityName', '')
        )
        if activity_type == "Strength":
            strength.append(activity)
    return strength


def get_exercise_sets(garmin_client: GarminClient, activity_id: int) -> list[dict]:
    data = garmin_client.get_activity_exercise_sets(activity_id)
    return data.get("exerciseSets", [])


def format_exercise_name(name: str) -> str:
    return name.replace('_', ' ').title() if name else "Unknown"


def format_category(category: str) -> str:
    return category.title() if category else "Unknown"


def aggregate_by_exercise(
    sets: list[dict],
    activity_date: datetime,
    activity_name: str
) -> list[dict]:
    active_sets = [s for s in sets if s.get("setType") == "ACTIVE"]

    grouped: dict[str, list[dict]] = {}
    for s in active_sets:
        exercises = s.get("exercises", [])
        if not exercises:
            continue
        exercise = exercises[0]
        category = exercise.get("category") or "UNKNOWN"
        name = exercise.get("name") or "UNKNOWN"
        if category == "UNKNOWN" and name == "UNKNOWN":
            continue
        if name == "UNKNOWN":
            name = category
        raw_name = category + "__" + name
        if raw_name not in grouped:
            grouped[raw_name] = {"sets": [], "category": category, "name": name}
        grouped[raw_name]["sets"].append(s)

    results = []
    for key, group in grouped.items():
        exercise_sets = group["sets"]
        sets_count = len(exercise_sets)

        reps_list = [s.get("repetitionCount") or 0 for s in exercise_sets]
        weight_list = [(s.get("weight") or 0) / 1000 for s in exercise_sets]  # grams → kg

        if sum(reps_list) == 0:
            continue

        avg_reps = round(sum(reps_list) / sets_count, 1) if sets_count else 0
        max_weight_kg = round(max(weight_list), 3) if weight_list else 0
        avg_weight_kg = round(sum(weight_list) / sets_count, 3) if sets_count else 0
        total_volume_kg = round(sum(r * w for r, w in zip(reps_list, weight_list)), 3)

        results.append({
            "exercise_name": format_exercise_name(group["name"] or "UNKNOWN"),
            "category": format_category(group["category"] or "UNKNOWN"),
            "date": activity_date,
            "workout_name": activity_name,
            "sets_count": sets_count,
            "avg_reps": avg_reps,
            "max_weight_kg": max_weight_kg,
            "avg_weight_kg": avg_weight_kg,
            "total_volume_kg": total_volume_kg,
        })

    return results


def exercise_exists(
    notion_client: NotionClient,
    db_id: str,
    date: datetime,
    exercise_name: str,
    workout_name: str
) -> dict | None:
    lookup_min = (date - timedelta(minutes=5)).isoformat()
    lookup_max = (date + timedelta(minutes=5)).isoformat()

    query = notion_client.databases.query(
        database_id=db_id,
        filter={
            "and": [
                {"property": "Date", "date": {"on_or_after": lookup_min}},
                {"property": "Date", "date": {"on_or_before": lookup_max}},
                {"property": "Exercise", "title": {"equals": exercise_name}},
                {"property": "Workout", "rich_text": {"equals": workout_name}},
            ]
        }
    )
    results = query["results"]
    return results[0] if results else None


def exercise_needs_update(existing: dict, new_data: dict) -> bool:
    props = existing["properties"]
    return (
        props["Sets"]["number"] != new_data["sets_count"] or
        props["Avg Reps"]["number"] != new_data["avg_reps"] or
        props["Max Weight (kg)"]["number"] != new_data["max_weight_kg"] or
        props["Avg Weight (kg)"]["number"] != new_data["avg_weight_kg"] or
        props["Total Volume (kg)"]["number"] != new_data["total_volume_kg"]
    )


def create_exercise_entry(notion_client: NotionClient, db_id: str, data: dict) -> None:
    notion_client.pages.create(
        parent={"database_id": db_id},
        properties={
            "Exercise": {"title": [{"text": {"content": data["exercise_name"]}}]},
            "Date": {"date": {"start": data["date"].isoformat()}},
            "Workout": {"rich_text": [{"text": {"content": data["workout_name"]}}]},
            "Category": {"select": {"name": data["category"]}},
            "Sets": {"number": data["sets_count"]},
            "Avg Reps": {"number": data["avg_reps"]},
            "Max Weight (kg)": {"number": data["max_weight_kg"]},
            "Avg Weight (kg)": {"number": data["avg_weight_kg"]},
            "Total Volume (kg)": {"number": data["total_volume_kg"]},
        }
    )


def update_exercise_entry(notion_client: NotionClient, existing: dict, new_data: dict) -> None:
    notion_client.pages.update(
        page_id=existing["id"],
        properties={
            "Sets": {"number": new_data["sets_count"]},
            "Avg Reps": {"number": new_data["avg_reps"]},
            "Max Weight (kg)": {"number": new_data["max_weight_kg"]},
            "Avg Weight (kg)": {"number": new_data["avg_weight_kg"]},
            "Total Volume (kg)": {"number": new_data["total_volume_kg"]},
        }
    )


def main():
    load_dotenv()

    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_STRENGTH_DB_ID")
    fetch_limit = int(os.getenv("GARMIN_ACTIVITIES_FETCH_LIMIT") or "1000")

    garmin_client = GarminClient(garmin_email, garmin_password)
    garmin_client.login()
    notion_client = NotionClient(auth=notion_token)

    strength_activities = get_strength_activities(garmin_client, fetch_limit)

    for activity in strength_activities:
        activity_id = activity.get("activityId")
        activity_name = activity.get("activityName", "Unnamed Workout")
        activity_date_raw: str = activity.get("startTimeGMT")
        activity_date: datetime = (
            datetime
            .strptime(activity_date_raw, '%Y-%m-%d %H:%M:%S')
            .replace(tzinfo=UTC)
        )

        sets = get_exercise_sets(garmin_client, activity_id)
        exercises = aggregate_by_exercise(sets, activity_date, activity_name)

        for exercise_data in exercises:
            existing = exercise_exists(
                notion_client, db_id,
                exercise_data["date"],
                exercise_data["exercise_name"],
                exercise_data["workout_name"]
            )

            if existing:
                if exercise_needs_update(existing, exercise_data):
                    update_exercise_entry(notion_client, existing, exercise_data)
            else:
                create_exercise_entry(notion_client, db_id, exercise_data)


if __name__ == "__main__":
    main()
