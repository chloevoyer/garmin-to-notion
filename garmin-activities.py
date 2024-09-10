from datetime import date, datetime, timezone
from garminconnect import Garmin
from notion_client import Client
import pytz  
import os

# Your local time zone, replace with the appropriate one if needed
local_tz = pytz.timezone('America/Toronto')

def get_todays_activities(garmin):
    # Fetch recent activities, adjust the count if needed
    activities = garmin.get_activities(0, 10)

    # Get today's date in your local time zone
    today = datetime.now(local_tz).date()

    # Filter activities that occurred today in your local time zone
    todays_activities = [
        activity for activity in activities
        if datetime.strptime(activity['startTimeGMT'], "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .astimezone(local_tz)
        .date() == today
    ]

    return todays_activities

def format_activity_type(activity_type):
    return activity_type.replace('_', ' ').title()

def format_entertainment(activity_name):
    return activity_name.replace('ENTERTAINMENT', 'Netflix')

def format_training_effect(trainingEffect_label):
    return trainingEffect_label.replace('_', ' ').title()

def format_pace(average_speed):
    if average_speed > 0:
        pace_min_km = 1000 / (average_speed * 60)  # Convert to min/km
        minutes = int(pace_min_km)
        seconds = int((pace_min_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/km"
    else:
        return ""
    
def write_row(client, database_id, activity_date, activity_type, activity_name, distance, duration, calories, avg_pace, 
              aerobic_TrainingEffect, anaerobic_TrainingEffect, trainingEffect_label, 
              pr_status):
    """
    Writes a row to the Notion database with the specified activity details.
    """
    client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Date": {"date": {"start": activity_date}},
            "Activity Type": {"select": {"name": activity_type}},
            "Activity Name": {"title": [{"text": {"content": activity_name}}]},
            "Distance (km)": {"number": distance},
            "Duration (min)": {"number": duration},
            "Calories": {"number": calories},
            "Avg Pace": {"rich_text": [{"text": {"content": avg_pace}}]},
            "Aerobic": {"number": aerobic_TrainingEffect},
            "Anaerobic": {"number": anaerobic_TrainingEffect},
            "Training Effect": {"select": {"name": trainingEffect_label}}, 
            "Month": {"relation": [{"id": relation_id}]}, 
            "PR": {"checkbox": pr_status}  
        }
    )

def main():
    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")
    relation_id = os.getenv("NOTION_RL_ID")
    
    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    client = Client(auth=notion_token)

    # This is only used to initialize all Garmin activities in my database, but I only sync today's event regularly
        # Fetch activities (0, 100) is a range; you may adjust it if needed.
        # activities = garmin.get_activities(0, 5)
        # print(activities)

    # Get today's activities
    todays_activities = get_todays_activities(garmin)
    print("Today's Activities:", todays_activities)

    # Process only today's activities
    for activity in todays_activities:
        activity_date = activity.get('startTimeGMT')
        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
        activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
        distance_km = round(activity.get('distance', 0) / 1000, 2)
        duration_minutes = round(activity.get('duration', 0) / 60, 2)
        calories = activity.get('calories', 0)
        average_speed = activity.get('averageSpeed', 0)
        avg_pace = format_pace(average_speed)
        aerobic_TrainingEffect = round(activity.get('aerobicTrainingEffect', 0), 2)
        anaerobic_TrainingEffect = round(activity.get('anaerobicTrainingEffect', 0), 2)
        trainingEffect_label = format_training_effect(activity.get('trainingEffectLabel', 'Unknown'))
        pr_status = activity.get('pr', False) 

        # Write to Notion
        try:
            write_row(client, database_id, activity_date, activity_type, activity_name, distance_km, duration_minutes, calories, avg_pace,
                      aerobic_TrainingEffect, anaerobic_TrainingEffect, trainingEffect_label, 
                      pr_status)
            print(f"Successfully written: {activity_type} - {activity_name}")
        except Exception as e:
            print(f"Failed to write to Notion: {e}")


if __name__ == '__main__':
    main()
