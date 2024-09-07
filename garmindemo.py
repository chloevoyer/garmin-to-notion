from garminconnect import Garmin
from getpass import getpass
from datetime import datetime
from notion_client import Client
import os
import json

LAST_SYNC_FILE = "last_sync.json"  # File to store the last sync date

def get_last_sync_date():
    """
    Retrieve the last sync date from a JSON file.
    If the file does not exist, return a date far in the past.
    """
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, "r") as file:
            data = json.load(file)
            return datetime.fromisoformat(data.get("last_sync", "2000-01-01T00:00:00"))
    return datetime(2000, 1, 1)

def update_last_sync_date(sync_date):
    """
    Update the last sync date in a JSON file.
    """
    with open(LAST_SYNC_FILE, "w") as file:
        json.dump({"last_sync": sync_date.isoformat()}, file)

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

    # Get the last sync date and fetch activities since that date
    last_sync_date = get_last_sync_date()
    today = datetime.now()

    # Fetch the first 100 activities
    activities = garmin.get_activities(0, 100)
    # Filter new activities since the last sync date
    new_activities = [act for act in activities if datetime.fromisoformat(act.get('startTimeLocal')) > last_sync_date]

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

        # Print the extracted details
        print(f"Processing {activity_type}: {activity_name}")
        print(f"Distance: {distance_km} km, Duration: {duration_minutes} min, Calories: {calories}, Avg Pace: {avg_pace}, Date: {activity_date}")

        # Write activity details to the Notion database
        try:
            write_row(client, database_id, activity_type, activity_name, distance_km, duration_minutes, calories, activity_date, avg_pace)
            print("Successfully written to Notion database.")
        except Exception as e:
            print(f"Failed to write to Notion: {e}")

    # Update the last sync date
    update_last_sync_date(today)
    print("Finished processing all activities.")

if __name__ == '__main__':
    main()
