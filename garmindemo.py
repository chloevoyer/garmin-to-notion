import json
import os
from datetime import datetime
from garminconnect import Garmin
from notion_client import Client
from getpass import getpass

def load_last_sync(filename):
    """Load last sync information from a JSON file."""
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    else:
        return {"last_sync_timestamp": "1970-01-01T00:00:00Z", "latest_activity_id": ""}

def save_last_sync(filename, last_sync_data):
    """Save last sync information to a JSON file."""
    with open(filename, 'w') as file:
        json.dump(last_sync_data, file, indent=4)

def format_activity_type(activity_type):
    """Formats the activity type to be capitalized and removes underscores."""
    return activity_type.replace('_', ' ').title()

def format_pace(average_speed):
    """Converts average speed (m/s) to pace (min/km) and formats it as a string."""
    if average_speed > 0:
        pace_min_km = 1000 / (average_speed * 60)  # Convert to min/km
        minutes = int(pace_min_km)
        seconds = int((pace_min_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/km"
    else:
        return ""

def write_row(client, database_id, activity_type, activity_name, distance, duration, calories, activity_date, avg_pace):
    """Writes a row to the Notion database with the specified activity details."""
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
    # Load last sync data
    last_sync_file = 'last_sync.json'
    last_sync_data = load_last_sync(last_sync_file)
    last_sync_timestamp = last_sync_data["last_sync_timestamp"]
    last_sync_id = last_sync_data["latest_activity_id"]

    # Initialize Garmin and Notion clients
    garmin = Garmin(getpass("Enter email address: "), getpass("Enter password: "))
    garmin.login()
    client = Client(auth=os.getenv("NOTION_TOKEN"))

    # Fetch activities
    activities = garmin.get_activities(0, 100)
    latest_id = last_sync_id

    # Process activities
    for activity in activities:
        activity_id = activity.get('activityId', '')
        if activity_id <= last_sync_id:
            continue
        
        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
        activity_name = activity.get('activityName', 'Unnamed Activity')
        distance_km = round(activity.get('distance', 0) / 1000, 2)
        duration_minutes = round(activity.get('duration', 0) / 60, 2)
        calories = activity.get('calories', 0)
        activity_date = activity.get('startTimeLocal', datetime.now().isoformat())
        average_speed = activity.get('averageSpeed', 0)
        avg_pace = format_pace(average_speed)

        # Write to Notion
        try:
            write_row(client, os.getenv("NOTION_DB_ID"), activity_type, activity_name, distance_km, duration_minutes, calories, activity_date, avg_pace)
            print(f"Successfully written: {activity_type} - {activity_name}")
            latest_id = max(latest_id, activity_id)
        except Exception as e:
            print(f"Failed to write to Notion: {e}")

    # Update last sync data
    if latest_id != last_sync_id:
        last_sync_data["last_sync_timestamp"] = datetime.now().isoformat()
        last_sync_data["latest_activity_id"] = latest_id
        save_last_sync(last_sync_file, last_sync_data)
        print("Last sync data updated.")

if __name__ == '__main__':
    main()
