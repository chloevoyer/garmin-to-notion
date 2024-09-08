import os
from datetime import datetime
from garminconnect import Garmin
from notion_client import Client

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
    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")
    page_id = os.getenv("NOTION_PG_ID")

    if not (garmin_email and garmin_password and notion_token and database_id):
        print("Error: Missing one or more environment variables.")
        return

    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    client = Client(auth=notion_token)

    # Fetch activities
    activities = garmin.get_activities(0, 10)
    
    # Get today's date
    today = datetime.now().date()

    # Process only today's activities
    for activity in activities:
        # Convert the activity date string to a datetime object
        activity_date = datetime.fromisoformat(activity.get('startTimeLocal')).date()

        # Check if the activity date is today
        if activity_date != today:
            continue  # Skip activities that are not from today

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
            write_row(client, database_id, activity_type, activity_name, distance_km, duration_minutes, calories, activity_date, avg_pace)
            print(f"Successfully written: {activity_type} - {activity_name}")
            latest_id = max(latest_id, activity_id)
        except Exception as e:
            print(f"Failed to write to Notion: {e}")

if __name__ == '__main__':
    main()
