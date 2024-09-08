import os
from datetime import datetime, timedelta
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

    # Fetch activities without filtering dates to see all available data
    try:
        activities = garmin.get_activities(0, 50)  # Increase the range to capture more data
        print(f"Fetched {len(activities)} activities from Garmin.")
        if len(activities) == 0:
            print("No activities were fetched. Ensure there are activities to retrieve and that permissions are correct.")
        else:
            for activity in activities:
                # Print the raw activity data for debugging purposes
                print("Raw activity data:", activity)

                # Extract and print the start time to ensure correct date parsing
                start_time = activity.get('startTimeLocal', 'N/A')
                print(f"Activity Start Time: {start_time}")

                # Extract date to check alignment with today's date
                activity_date = datetime.fromisoformat(start_time).date() if start_time != 'N/A' else None
                if activity_date:
                    print(f"Parsed Activity Date: {activity_date}")
                else:
                    print("Error parsing activity date.")

                # Check if activity date matches today's date
                if activity_date != montreal_time.date():
                    print(f"Skipping activity on {activity_date} as it is not today.")
                    continue

                # Extract and process activity details
                activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
                activity_name = activity.get('activityName', 'Unnamed Activity')
                distance_km = round(activity.get('distance', 0) / 1000, 2)
                duration_minutes = round(activity.get('duration', 0) / 60, 2)
                calories = activity.get('activeKilocalories', 0)
                average_speed = activity.get('averageSpeed', 0)
                avg_pace = format_pace(average_speed)

                # Attempt to write to Notion
                write_row(client, database_id, activity_type, activity_name, distance_km, duration_minutes, calories, str(activity_date), avg_pace)

    except Exception as e:
        print(f"Error fetching activities from Garmin: {e}")

if __name__ == '__main__':
    main()
