from datetime import datetime, timezone
from garminconnect import Garmin
from notion_client import Client
import pytz
import os

# Your local time zone, replace with the appropriate one if needed
local_tz = pytz.timezone('America/Toronto')

# Define a mapping of activity types to icon URLs in Notion
ACTIVITY_ICONS = {
    "Running": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2F73a73bb9-bc6c-4d1a-9ba5-ba29d84632b8%2FExercise3.svg?table=block&id=10015ce7-0588-81bc-bd01-d1757711a430&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Treadmill Running": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2Fe862ecc4-314c-4e63-a2b8-af2b4f3e96a7%2FTreadmill.svg?table=block&id=10015ce7-0588-81c6-beb7-c4695c0a1d24&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Cycling": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2F98271e2c-055b-4eab-b449-df056eddf357%2FCycling.svg?table=block&id=10115ce7-0588-8131-8f0e-e16f3f1c152f&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Swimming": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2F23364b02-cacb-40cf-98b3-0f3254daae95%2FSwimming.svg?table=block&id=10115ce7-0588-80ce-9fa3-da6b7e18a114&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Strength Training": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2Faba98524-d444-44dc-a662-8e251645cdc8%2FSit_Ups.svg?table=block&id=10015ce7-0588-8176-8025-e542a2b6fa92&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Walking": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2Fbb62a42f-bb7f-4add-8a1d-86804ed8350c%2FWalking.svg?table=block&id=10015ce7-0588-814f-92f0-f4b73324352c&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Yoga": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2F15ed81b6-5b02-4d87-9ec0-a448b49f1a90%2FYoga.svg?table=block&id=86b0a6a3-a4ae-4f35-a031-fe8fe2c2e222&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Hiking": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2Fbef1a0d4-1a06-4859-8521-1fe971bcf11e%2FTrekking.svg?table=block&id=10015ce7-0588-81ae-bb2c-d8152cfe93eb&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2",
    "Rowing": "https://www.notion.so/image/https%3A%2F%2Fprod-files-secure.s3.us-west-2.amazonaws.com%2F5f8cbff8-587c-40dc-b000-881bd747e0a2%2Fbae973e7-30a2-45ed-ae0c-a153c9cc6f31%2FRow_Boat.svg?table=block&id=10015ce7-0588-81cd-bdd2-f90e6b8cca6e&spaceId=5f8cbff8-587c-40dc-b000-881bd747e0a2&userId=b35f54bf-0b56-45c2-badf-b107f94a79d3&cache=v2"
    # Add more mappings as needed
}

def get_all_activities(garmin, limit=1000):
    return garmin.get_activities(0, limit)

def format_activity_type(activity_type):
    return activity_type.replace('_', ' ').title()

def format_entertainment(activity_name):
    return activity_name.replace('ENTERTAINMENT', 'Netflix')

def format_training_message(message):
    messages = {
        'NO_': 'No Benefit',
        'MINOR_': 'Some Benefit',
        'RECOVERY_': 'Recovery',
        'MAINTAINING_': 'Maintaining',
        'IMPROVING_': 'Improving',
        'IMPACTING_': 'Impacting',
        'HIGHLY_': 'Highly Impacting',
        'OVERREACHING_': 'Overreaching'
    }
    for key, value in messages.items():
        if message.startswith(key):
            return value
    return message

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

def activity_exists(client, database_id, activity_date, activity_type, activity_name):
    """
    Check if an activity already exists in the Notion database and return it if found.
    """
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"equals": activity_date.split('T')[0]}},
                {"property": "Activity Type", "select": {"equals": activity_type}},
                {"property": "Activity Name", "title": {"equals": activity_name}}
            ]
        }
    )
    results = query['results']
    return results[0] if results else None

def activity_needs_update(existing_activity, new_activity):
    """
    Compare existing activity with new activity data to determine if an update is needed.
    """
    existing_props = existing_activity['properties']
    return (
        existing_props['Distance (km)']['number'] != round(new_activity.get('distance', 0) / 1000, 2) or
        existing_props['Duration (min)']['number'] != round(new_activity.get('duration', 0) / 60, 2) or
        existing_props['Calories']['number'] != new_activity.get('calories', 0) or
        existing_props['Avg Pace']['rich_text'][0]['text']['content'] != format_pace(new_activity.get('averageSpeed', 0)) or
        existing_props['Training Effect']['select']['name'] != format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown')) or
        existing_props['Aerobic']['number'] != round(new_activity.get('aerobicTrainingEffect', 1)) or
        existing_props['Aerobic Effect']['select']['name'] != format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown')) or
        existing_props['Anaerobic']['number'] != round(new_activity.get('anaerobicTrainingEffect', 1)) or
        existing_props['Anaerobic Effect']['select']['name'] != format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown')) or
        existing_props['PR']['checkbox'] != new_activity.get('pr', False)
    )

def update_activity(client, existing_activity, new_activity):
    """
    Update an existing activity in the Notion database with new data.
    """
    client.pages.update(
        page_id=existing_activity['id'],
        properties={
            "Distance (km)": {"number": round(new_activity.get('distance', 0) / 1000, 2)},
            "Duration (min)": {"number": round(new_activity.get('duration', 0) / 60, 2)},
            "Calories": {"number": new_activity.get('calories', 0)},
            "Avg Pace": {"rich_text": [{"text": {"content": format_pace(new_activity.get('averageSpeed', 0))}}]},
            "Training Effect": {"select": {"name": format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown'))}},
            "Aerobic": {"number": round(new_activity.get('aerobicTrainingEffect', 1))},
            "Aerobic Effect": {"select": {"name": format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
            "Anaerobic": {"number": round(new_activity.get('anaerobicTrainingEffect', 1))},
            "Anaerobic Effect": {"select": {"name": format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
            "PR": {"checkbox": new_activity.get('pr', False)}
        }
    )

def create_activity(client, database_id, activity):
    """
    Create a new activity in the Notion database.
    """
    activity_date = activity.get('startTimeGMT')
    activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
    activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
    
    # Get icon and cover for the activity type
    icon_url = ACTIVITY_ICONS.get(activity_type)
    cover = ACTIVITY_COVERS.get(activity_type)
    
    properties = {
        "Date": {"date": {"start": activity_date}},
        "Activity Type": {"select": {"name": activity_type}},
        "Activity Name": {"title": [{"text": {"content": activity_name}}]},
        "Distance (km)": {"number": round(activity.get('distance', 0) / 1000, 2)},
        "Duration (min)": {"number": round(activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": activity.get('calories', 0)},
        "Avg Pace": {"rich_text": [{"text": {"content": format_pace(activity.get('averageSpeed', 0))}}]},
        "Training Effect": {"select": {"name": format_training_effect(activity.get('trainingEffectLabel', 'Unknown'))}},
        "Aerobic": {"number": round(activity.get('aerobicTrainingEffect', 1))},
        "Aerobic Effect": {"select": {"name": format_training_message(activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
        "Anaerobic": {"number": round(activity.get('anaerobicTrainingEffect', 1))},
        "Anaerobic Effect": {"select": {"name": format_training_message(activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
        "PR": {"checkbox": activity.get('pr', False)}
    }
    
    page = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    
    if icon_url:
        page["icon"] = {"type": "external", "external": {"url": icon_url}}
    
    if cover:
        page["cover"] = {"type": "external", "external": {"url": cover}}
    
    client.pages.create(**page)

def update_activity(client, existing_activity, new_activity):
    """
    Update an existing activity in the Notion database with new data.
    """
    activity_type = format_activity_type(new_activity.get('activityType', {}).get('typeKey', 'Unknown'))
    
    # Get icon and cover for the activity type
    icon_url = ACTIVITY_ICONS.get(activity_type)
    cover = ACTIVITY_COVERS.get(activity_type)
    
    properties = {
        "Distance (km)": {"number": round(new_activity.get('distance', 0) / 1000, 2)},
        "Duration (min)": {"number": round(new_activity.get('duration', 0) / 60, 2)},
        "Calories": {"number": new_activity.get('calories', 0)},
        "Avg Pace": {"rich_text": [{"text": {"content": format_pace(new_activity.get('averageSpeed', 0))}}]},
        "Training Effect": {"select": {"name": format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown'))}},
        "Aerobic": {"number": round(new_activity.get('aerobicTrainingEffect', 1))},
        "Aerobic Effect": {"select": {"name": format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
        "Anaerobic": {"number": round(new_activity.get('anaerobicTrainingEffect', 1))},
        "Anaerobic Effect": {"select": {"name": format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
        "PR": {"checkbox": new_activity.get('pr', False)}
    }
    
    update = {
        "page_id": existing_activity['id'],
        "properties": properties,
    }
    
    if icon_url:
        update["icon"] = {"type": "external", "external": {"url": icon_url}}
        
    client.pages.update(**update)

def main():
    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    client = Client(auth=notion_token)
    
    # Get all activities
    activities = get_all_activities(garmin)

    # Process all activities
    for activity in activities:
        activity_date = activity.get('startTimeGMT')
        activity_type = format_activity_type(activity.get('activityType', {}).get('typeKey', 'Unknown'))
        activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
        
        # Check if activity already exists in Notion
        existing_activity = activity_exists(client, database_id, activity_date, activity_type, activity_name)
        
        if existing_activity:
            if activity_needs_update(existing_activity, activity):
                update_activity(client, existing_activity, activity)
                print(f"Updated: {activity_type} - {activity_name}")
            else:
                print(f"No update needed: {activity_type} - {activity_name}")
        else:
            create_activity(client, database_id, activity)
            print(f"Created: {activity_type} - {activity_name}")

if __name__ == '__main__':
    main()
