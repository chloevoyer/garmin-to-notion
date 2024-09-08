import os
from datetime import datetime
from garminconnect import Garmin
from notion_client import Client
import pytz

# Convert the current UTC time to Montreal timezone
utc_time = datetime.now(pytz.utc)
montreal_time = utc_time.astimezone(pytz.timezone('America/Montreal'))
print(f"Current time in Montreal: {montreal_time}")

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
    print(f"Attempting to write to Notion: {activity_name}, Date: {activity_date}")
    try:
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
        print(f"Successfully written: {activity_name}")
    except Exception as e:
        print(f"Failed to write to Notion: {e}")

def main():
    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    # Check for missing environment variables
    if not garmin_email or not garmin_password or not notion_token or not database_id:
        print("Error: Missing one or more environment variables.")
        return

    # Initialize Garmin and Notion clients
    try:
        garmin = Garmin(garmin_email, garmin_password)
        garmin.login()
        print("Logged in to Garmin successfully.")
    except Exception as e:
        print(f"Error logging into Garmin: {e}")
        return

    try:
        client = Client(auth=notion_token)
        print("Connected to Notion successfully.")
    except Exception as e:
        print(f"Error connecting to Notion: {e}")
        return

    # Fetch activities (increase the range to ensure we fetch enough data)
    try:
        activities = garmin.get_activities(0, 50)  # Fetch more activities
        print(f"Fetched {len(activities)} activities from Garmin.")
        for activity in activities:  # Print all activities to inspect their details
            print(activity)
    except Exception as e:
        print(f"Error fetching activities from Garmin: {e}")
        return

    # Get today's date
    today = datetime.now().date()
    print(f"Today's date: {today}")

    # Process only today's activities
    for activity in activities:
        activity_date = datetime.fromisoformat(activity.get('startTimeLocal')).date()
        print(f"Activity date: {activity_date}, Activity name: {activity.get('activityName')}")

        if activity_date != today:
            print(f"Skipping activity on {activity_date} as it is not today.")
            continue

        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
        activity_name = activity.get('activityName', 'Unnamed Activity')
        distance_km = round(activity.get('distance', 0) / 1000, 2)
        duration_minutes = round(activity.get('duration', 0) / 60, 2)
        calories = activity.get('activeKilocalories', 0)
        average_speed = activity.get('averageSpeed', 0)
        avg_pace = format_pace(average_speed)

        # Attempt to write to Notion
        write_row(client, database_id, activity_type, activity_name, distance_km, duration_minutes, calories, str(activity_date), avg_pace)

if __name__ == '__main__':
    main()
