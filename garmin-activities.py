import os
from datetime import datetime, UTC, timedelta

from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

CUTOFF_DATE = datetime(2025, 12, 1, tzinfo=UTC)


ACTIVITY_TYPE_MAP = {
    "Walking": "Walk",
    "Running": "Run",
}


def format_activity_type(activity_type: str) -> str:
    if not activity_type:
        return "Unknown"
    title_cased = activity_type.replace('_', ' ').title()
    return ACTIVITY_TYPE_MAP.get(title_cased, title_cased)


def activity_exists(
    notion_client: NotionClient,
    database_id: str,
    activity_date: datetime,
    activity_type: str,
    activity_name: str,
) -> dict | None:
    # Check if an activity already exists in the Notion database and return it if found.

    # Create a time window to search for the activity. Notion has been observed to truncate datetimes to the minutes in
    # some instances, causing the lookup using exact datetime to fail.
    lookup_min_date = activity_date - timedelta(minutes=5)
    lookup_max_date = activity_date + timedelta(minutes=5)

    query = notion_client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"on_or_after": lookup_min_date.isoformat()}},
                {"property": "Date", "date": {"on_or_before": lookup_max_date.isoformat()}},
                {"property": "Type", "multi_select": {"contains": activity_type}},
                {"property": "Activity", "title": {"equals": activity_name}},
                {"property": "Data source", "select": {"equals": "Garmin"}},
            ]
        }
    )
    results = query['results']
    return results[0] if results else None


def activity_needs_update(existing_activity: dict, new_activity: dict) -> bool:
    existing_props = existing_activity['properties']
    activity_type = format_activity_type(new_activity.get('activityType', {}).get('typeKey', 'Unknown'))

    existing_type_names = [
        opt['name'] for opt in existing_props.get('Type', {}).get('multi_select', [])
    ]

    return (
        existing_props.get('Distance (km)', {}).get('number') != round(new_activity.get('distance', 0) / 1000, 2) or
        existing_props.get('Duration (min)', {}).get('number') != round(new_activity.get('duration', 0) / 60, 2) or
        existing_props.get('Calories', {}).get('number') != round(new_activity.get('calories', 0)) or
        existing_props.get('Avg heart rate', {}).get('number') != new_activity.get('averageHR') or
        existing_props.get('Steps', {}).get('number') != new_activity.get('steps') or
        activity_type not in existing_type_names
    )


def create_activity(notion_client: NotionClient, database_id: str, activity: dict) -> None:
    activity_name = activity.get('activityName', 'Unnamed Activity')
    activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
    activity_date = activity.get('startTimeLocal')  # Already in local time

    properties = {
        "Activity": {"title": [{"text": {"content": activity_name}}]},
        "Type": {"multi_select": [{"name": activity_type}]},
        "Date": {"date": {"start": activity_date}},
        "Duration (min)": {"number": round(activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": round(activity.get('calories', 0))},
        "Distance (km)": {"number": round(activity.get('distance', 0) / 1000, 2)},
        "Data source": {"select": {"name": "Garmin"}},
        "Record type": {"select": {"name": "Workout"}},
    }

    if activity.get('averageHR') is not None:
        properties["Avg heart rate"] = {"number": activity.get('averageHR')}

    if activity.get('steps') is not None:
        properties["Steps"] = {"number": activity.get('steps')}

    notion_client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
    )


def update_activity(notion_client: NotionClient, existing_activity: dict, new_activity: dict) -> None:
    activity_type = format_activity_type(new_activity.get('activityType', {}).get('typeKey', 'Unknown'))

    properties = {
        "Type": {"multi_select": [{"name": activity_type}]},
        "Duration (min)": {"number": round(new_activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": round(new_activity.get('calories', 0))},
        "Distance (km)": {"number": round(new_activity.get('distance', 0) / 1000, 2)},
        "Record type": {"select": {"name": "Workout"}},
    }

    if new_activity.get('averageHR') is not None:
        properties["Avg heart rate"] = {"number": new_activity.get('averageHR')}

    if new_activity.get('steps') is not None:
        properties["Steps"] = {"number": new_activity.get('steps')}

    notion_client.pages.update(
        page_id=existing_activity['id'],
        properties=properties,
    )


def main():
    garmin_email = os.environ["GARMIN_EMAIL"]
    garmin_password = os.environ["GARMIN_PASSWORD"]
    notion_token = os.environ["NOTION_TOKEN"]
    database_id = os.environ["NOTION_DATABASE_ID"]

    garmin_client = GarminClient(garmin_email, garmin_password)
    garmin_client.login()
    notion_client = NotionClient(auth=notion_token)

    activities = garmin_client.get_activities(0, 1000)

    for activity in activities:
        activity_date_raw: str = activity.get('startTimeLocal')
        activity_date: datetime = (
            datetime
            .strptime(activity_date_raw, '%Y-%m-%d %H:%M:%S')
            .replace(tzinfo=UTC)
        )

        if activity_date < CUTOFF_DATE:
            continue

        activity_name = activity.get('activityName', 'Unnamed Activity')
        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))

        existing_activity = activity_exists(notion_client, database_id, activity_date, activity_type, activity_name)

        if existing_activity:
            if existing_activity['properties'].get('Hidden', {}).get('checkbox', False):
                continue
            if activity_needs_update(existing_activity, activity):
                update_activity(notion_client, existing_activity, activity)
        else:
            create_activity(notion_client, database_id, activity)


if __name__ == '__main__':
    main()
