import json
from garminconnect import Garmin
from getpass import getpass
from datetime import date
from notion_client import Client
import os

# File path for last_sync.json
SYNC_FILE_PATH = 'last_sync.json'

def read_last_sync(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"last_sync_timestamp": "1970-01-01T00:00:00Z", "latest_activity_id": ""}

def update_last_sync(file_path, new_timestamp, new_activity_id):
    data = {
        "last_sync_timestamp": new_timestamp,
        "latest_activity_id": new_activity_id
    }
    with open(file_path, 'w') as file:
        json.dump(data, file)

def format_activity_type(activity_type):
    """
    Formats the activity type to be capitalized and removes underscores.
    Example: 'running' -> 'Running', 'indoor_cycling' -> 'Indoor Cycling'
    """
    return activity_type.replace('_', ' ').title()

def format_pace(average_speed):
    """
    Converts average speed (m/s) to pace (min/km) and formats it as a string.
    """
    if average_speed > 0:
        pace_min_km = 1000 / (average_speed * 60)  # Convert to min/km
        minutes = int(pace_min_km)
        seconds = int((pace_min_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/km"
    else:
        return ""

def write_row(client, database_id, activity_type, activity_name, distance, duration, calories, activity_date, avg_pace):
    """
    Writes a row to the Notion database with the specified activity details.
    """
    client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Activity Name": {"title": [{"text": {"content": activity_name}}]},
            "Activity Type": {"select": {"name": activity_type}},
            "Distance (km)": {"number": distance},
            "Duration (min)": {"number": duration},
            "Calories": {"number": calories},
            "Date": {"date": {"start": activity_date}},
            "Avg Pace": {"rich_text": [{"text": {"content": avg_pace}}]}
        }
    )

def main():
    # Notion credentials from environment variables
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    # Garmin credentials from environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")

    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()

    # Initialize Notion client with the correct token
    client = Client(auth=notion_token)

    # Read last sync info
    last_sync = read_last_sync(SYNC_FILE_PATH)
    last_sync_timestamp = last_sync["last_sync_timestamp"]
    latest_activity_id = last_sync["latest_activity_id"]

    # Fetch activities
    activities = garmin.get_activities(0, 100)  # Adjust to filter by last_sync_timestamp or latest_activity_id

    # Iterate through each new activity and extract required details
    for activity in new_activities:
        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
        activity_name = activity.get('activityName', 'Unnamed Activity')
        distance_km = round(activity.get('distance', 0) / 1000, 2)  # Convert distance to km
        duration_minutes = round(activity.get('duration', 0) / 60, 2)  # Convert duration to minutes
        calories = activity.get('activeKilocalories', 0)  # Extract calories
        activity_date = activity.get('startTimeLocal')  # Extract activity date
        average_speed = activity.get('averageSpeed', 0)  # Get the average speed in m/s
        avg_pace = format_pace(average_speed)  # Convert speed to pace in min/km format

        # Write to Notion
        write_row(client, database_id, activity_type, activity_name, distance_km, duration_minutes, calories, activity_date, avg_pace)

        # Update latest_activity_id
        if activity_id > latest_activity_id:
            latest_activity_id = activity_id

    # Update last sync file
    update_last_sync(SYNC_FILE_PATH, date.today().isoformat(), latest_activity_id)

if __name__ == '__main__':
    main()
