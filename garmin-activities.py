import os
from datetime import datetime, UTC, timedelta

import pytz
from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

# Your local time zone, replace with the appropriate one if needed
local_tz = pytz.timezone('America/Toronto')

ACTIVITY_ICONS = {
    "Barre": "https://img.icons8.com/?size=100&id=66924&format=png&color=000000",
    "Breathwork": "https://img.icons8.com/?size=100&id=9798&format=png&color=000000",
    "Cardio": "https://img.icons8.com/?size=100&id=71221&format=png&color=000000",
    "Cycling": "https://img.icons8.com/?size=100&id=47443&format=png&color=000000",
    "Hiking": "https://img.icons8.com/?size=100&id=9844&format=png&color=000000",
    "Indoor Cardio": "https://img.icons8.com/?size=100&id=62779&format=png&color=000000",
    "Indoor Cycling": "https://img.icons8.com/?size=100&id=47443&format=png&color=000000",
    "Indoor Rowing": "https://img.icons8.com/?size=100&id=71098&format=png&color=000000",
    "Pilates": "https://img.icons8.com/?size=100&id=9774&format=png&color=000000",
    "Meditation": "https://img.icons8.com/?size=100&id=9798&format=png&color=000000",
    "Rowing": "https://img.icons8.com/?size=100&id=71491&format=png&color=000000",
    "Running": "https://img.icons8.com/?size=100&id=k1l1XFkME39t&format=png&color=000000",
    "Strength Training": "https://img.icons8.com/?size=100&id=107640&format=png&color=000000",
    "Stretching": "https://img.icons8.com/?size=100&id=djfOcRn1m_kh&format=png&color=000000",
    "Swimming": "https://img.icons8.com/?size=100&id=9777&format=png&color=000000",
    "Treadmill Running": "https://img.icons8.com/?size=100&id=9794&format=png&color=000000",
    "Walking": "https://img.icons8.com/?size=100&id=9807&format=png&color=000000",
    "Yoga": "https://img.icons8.com/?size=100&id=9783&format=png&color=000000",
    # Add more mappings as needed
}


def get_all_activities(garmin_client: GarminClient, limit: int = 1000) -> list[dict]:
    return garmin_client.get_activities(0, limit)


def format_activity_type(activity_type: str, activity_name: str = "") -> tuple[str, str]:
    # First format the activity type as before
    formatted_type = activity_type.replace('_', ' ').title() if activity_type else "Unknown"

    # Initialize subtype as the same as the main type
    activity_subtype = formatted_type
    activity_type = formatted_type

    # Map of specific subtypes to their main types
    activity_mapping = {
        "Barre": "Strength",
        "Indoor Cardio": "Cardio",
        "Indoor Cycling": "Cycling",
        "Indoor Rowing": "Rowing",
        "Speed Walking": "Walking",
        "Strength Training": "Strength",
        "Treadmill Running": "Running"
    }

    # Special replacement for Rowing V2
    if formatted_type == "Rowing V2":
        activity_type = "Rowing"

    # Special case for Yoga and Pilates
    elif formatted_type in ["Yoga", "Pilates"]:
        activity_type = "Yoga/Pilates"
        activity_subtype = formatted_type

    # If the formatted type is in our mapping, update both main type and subtype
    if formatted_type in activity_mapping:
        activity_type = activity_mapping[formatted_type]
        activity_subtype = formatted_type

    # Special cases for activity names
    if activity_name and "meditation" in activity_name.lower():
        return "Meditation", "Meditation"
    if activity_name and "barre" in activity_name.lower():
        return "Strength", "Barre"
    if activity_name and "stretch" in activity_name.lower():
        return "Stretching", "Stretching"

    return activity_type, activity_subtype


def format_entertainment(activity_name: str) -> str:
    return activity_name.replace('ENTERTAINMENT', 'Netflix')


def format_training_message(message: str) -> str:
    messages = {
        'NO_': 'No Benefit',
        'MINOR_': 'Some Benefit',
        'RECOVERY_': 'Recovery',
        'MAINTAINING_': 'Maintaining',
        'IMPROVING_': 'Impacting',
        'IMPACTING_': 'Impacting',
        'HIGHLY_': 'Highly Impacting',
        'OVERREACHING_': 'Overreaching'
    }
    for key, value in messages.items():
        if message.startswith(key):
            return value
    return message


def format_training_effect(training_effect_label: str) -> str:
    return training_effect_label.replace('_', ' ').title()


def format_pace(average_speed: float) -> str:
    if average_speed > 0:
        pace_min_km = 1000 / (average_speed * 60)  # Convert to min/km
        minutes = int(pace_min_km)
        seconds = int((pace_min_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/km"
    else:
        return ""


def activity_exists(
    notion_client: NotionClient,
    database_id: str,
    activity_date: datetime,
    activity_type: str,
    activity_name: str,
) -> dict | None:
    # Check if an activity already exists in the Notion database and return it if found.

    # Determine the correct activity type for the lookup
    lookup_type = "Stretching" if "stretch" in activity_name.lower() else activity_type

    # Create a time window to search for the activity. Notion has been observed to truncate datetimes to the minutes in
    # some instances, causing the lookup using exact datetime to fail.
    # TODO: We should store the activity ID in the Notion page to avoid this complexity.
    lookup_min_date = activity_date - timedelta(minutes=5)
    lookup_max_date = activity_date + timedelta(minutes=5)

    query = notion_client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"on_or_after": lookup_min_date.isoformat()}},
                {"property": "Date", "date": {"on_or_before": lookup_max_date.isoformat()}},
                # Further refine the search by activity type and name
                {"property": "Activity Type", "select": {"equals": lookup_type}},
                {"property": "Activity Name", "title": {"equals": activity_name}}
            ]
        }
    )
    results = query['results']
    return results[0] if results else None


def activity_needs_update(existing_activity: dict, new_activity: dict) -> bool:
    existing_props = existing_activity['properties']

    activity_name = new_activity.get('activityName', '').lower()
    activity_type, activity_subtype = format_activity_type(
        new_activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )

    # Check if 'Subactivity Type' property exists
    has_subactivity = (
        'Subactivity Type' in existing_props and
        existing_props['Subactivity Type'] is not None and
        existing_props['Subactivity Type'].get('select') is not None
    )

    return (
        existing_props['Distance (km)']['number'] != round(new_activity.get('distance', 0) / 1000, 2) or
        existing_props['Duration (min)']['number'] != round(new_activity.get('duration', 0) / 60, 2) or
        existing_props['Calories']['number'] != round(new_activity.get('calories', 0)) or
        existing_props['Avg Pace']['rich_text'][0]['text']['content'] != format_pace(
        new_activity.get('averageSpeed', 0)
    ) or
        existing_props['Avg Power']['number'] != round(new_activity.get('avgPower', 0), 1) or
        existing_props['Max Power']['number'] != round(new_activity.get('maxPower', 0), 1) or
        existing_props['Training Effect']['select']['name'] != format_training_effect(
        new_activity.get('trainingEffectLabel', 'Unknown')
    ) or
        existing_props['Aerobic']['number'] != round(new_activity.get('aerobicTrainingEffect', 0), 1) or
        existing_props['Aerobic Effect']['select']['name'] != format_training_message(
        new_activity.get('aerobicTrainingEffectMessage', 'Unknown')
    ) or
        existing_props['Anaerobic']['number'] != round(new_activity.get('anaerobicTrainingEffect', 0), 1) or
        existing_props['Anaerobic Effect']['select']['name'] != format_training_message(
        new_activity.get('anaerobicTrainingEffectMessage', 'Unknown')
    ) or
        existing_props['PR']['checkbox'] != new_activity.get('pr', False) or
        existing_props['Fav']['checkbox'] != new_activity.get('favorite', False) or
        existing_props['Activity Type']['select']['name'] != activity_type or
        (has_subactivity and existing_props['Subactivity Type']['select']['name'] != activity_subtype) or
        (not has_subactivity)  # If the property doesn't exist, we need an update
    )


def create_activity(notion_client: NotionClient, database_id: str, activity: dict) -> None:
    # Create a new activity in the Notion database
    activity_date = activity.get('startTimeGMT')
    activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
    activity_type, activity_subtype = format_activity_type(
        activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )

    # Get icon for the activity type
    icon_url = ACTIVITY_ICONS.get(activity_subtype if activity_subtype != activity_type else activity_type)

    properties = {
        "Date": {"date": {"start": activity_date}},
        "Activity Type": {"select": {"name": activity_type}},
        "Subactivity Type": {"select": {"name": activity_subtype}},
        "Activity Name": {"title": [{"text": {"content": activity_name}}]},
        "Distance (km)": {"number": round(activity.get('distance', 0) / 1000, 2)},
        "Duration (min)": {"number": round(activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": round(activity.get('calories', 0))},
        "Avg Pace": {"rich_text": [{"text": {"content": format_pace(activity.get('averageSpeed', 0))}}]},
        "Avg Power": {"number": round(activity.get('avgPower', 0), 1)},
        "Max Power": {"number": round(activity.get('maxPower', 0), 1)},
        "Training Effect": {"select": {"name": format_training_effect(activity.get('trainingEffectLabel', 'Unknown'))}},
        "Aerobic": {"number": round(activity.get('aerobicTrainingEffect', 0), 1)},
        "Aerobic Effect": {
            "select": {"name": format_training_message(activity.get('aerobicTrainingEffectMessage', 'Unknown'))}
        },
        "Anaerobic": {"number": round(activity.get('anaerobicTrainingEffect', 0), 1)},
        "Anaerobic Effect": {
            "select": {"name": format_training_message(activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}
        },
        "PR": {"checkbox": activity.get('pr', False)},
        "Fav": {"checkbox": activity.get('favorite', False)}
    }

    page = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }

    if icon_url:
        page["icon"] = {"type": "external", "external": {"url": icon_url}}

    notion_client.pages.create(**page)


def update_activity(notion_client: NotionClient, existing_activity: dict, new_activity: dict) -> None:
    # Update an existing activity in the Notion database with new data
    activity_name = new_activity.get('activityName', 'Unnamed Activity')
    activity_type, activity_subtype = format_activity_type(
        new_activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )

    # Get icon for the activity type
    icon_url = ACTIVITY_ICONS.get(activity_subtype if activity_subtype != activity_type else activity_type)

    properties = {
        "Activity Type": {"select": {"name": activity_type}},
        "Subactivity Type": {"select": {"name": activity_subtype}},
        "Distance (km)": {"number": round(new_activity.get('distance', 0) / 1000, 2)},
        "Duration (min)": {"number": round(new_activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": round(new_activity.get('calories', 0))},
        "Avg Pace": {"rich_text": [{"text": {"content": format_pace(new_activity.get('averageSpeed', 0))}}]},
        "Avg Power": {"number": round(new_activity.get('avgPower', 0), 1)},
        "Max Power": {"number": round(new_activity.get('maxPower', 0), 1)},
        "Training Effect": {
            "select": {"name": format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown'))}
        },
        "Aerobic": {"number": round(new_activity.get('aerobicTrainingEffect', 0), 1)},
        "Aerobic Effect": {
            "select": {"name": format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown'))}
        },
        "Anaerobic": {"number": round(new_activity.get('anaerobicTrainingEffect', 0), 1)},
        "Anaerobic Effect": {
            "select": {"name": format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}
        },
        "PR": {"checkbox": new_activity.get('pr', False)},
        "Fav": {"checkbox": new_activity.get('favorite', False)}
    }

    update = {
        "page_id": existing_activity['id'],
        "properties": properties,
    }

    if icon_url:
        update["icon"] = {"type": "external", "external": {"url": icon_url}}

    notion_client.pages.update(**update)


def main():
    load_dotenv()

    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")
    garmin_fetch_limit = int(os.getenv("GARMIN_ACTIVITIES_FETCH_LIMIT") or "1000")

    # Initialize Garmin client and login
    garmin_client = GarminClient(garmin_email, garmin_password)
    garmin_client.login()
    notion_client = NotionClient(auth=notion_token)

    # Get all activities
    activities = get_all_activities(garmin_client, garmin_fetch_limit)

    # Process all activities
    for activity in activities:
        activity_date_raw: str = activity.get('startTimeGMT')
        activity_date: datetime = (
            datetime
            .strptime(activity_date_raw, '%Y-%m-%d %H:%M:%S')  # Parse as format received from Garmin
            .replace(tzinfo=UTC)  # Set timezone to UTC, as Garmin times are in GMT/UTC. Close enough.
        )

        activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
        activity_type, activity_subtype = format_activity_type(
            activity.get('activityType', {}).get('typeKey', 'Unknown'),
            activity_name
        )

        # Check if activity already exists in Notion
        existing_activity = activity_exists(notion_client, database_id, activity_date, activity_type, activity_name)

        if existing_activity:
            if activity_needs_update(existing_activity, activity):
                update_activity(notion_client, existing_activity, activity)
                # print(f"Would update: {activity_type} - {activity_name} - {activity_date}")
        else:
            create_activity(notion_client, database_id, activity)
            # print(f"Would create: {activity_type} - {activity_name} - {activity_date}")


if __name__ == '__main__':
    main()
