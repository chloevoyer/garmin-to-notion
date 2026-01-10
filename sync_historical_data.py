"""
Sync Historical Data from Garmin to Notion
==========================================
This script is designed to run ONCE to sync all historical data from Garmin to Notion:
- Activities (up to 1000 most recent)
- Daily Steps (configurable days)
- Sleep Data (configurable days)

After running this script once, use the regular daily sync scripts for updates.

Usage:
    python sync_historical_data.py [--days 90] [--activities 1000]
    
Arguments:
    --days: Number of days to sync for steps and sleep (default: 90)
    --activities: Maximum number of activities to sync (default: 1000)
"""

from datetime import datetime, date, timedelta, timezone
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv
import pytz
import os
import time
import argparse

# ============================================================================
# CONFIGURATION
# ============================================================================

# Time zones
LOCAL_TZ = pytz.timezone('America/Toronto')
SLEEP_TZ = pytz.timezone("America/New_York")

# Default values
DEFAULT_DAYS_TO_SYNC = 365
DEFAULT_MAX_ACTIVITIES = 100
BATCH_SIZE = 100

# Activity icons
ACTIVITY_ICONS = {
    "Barre": "https://img.icons8.com/?size=100&id=66924&format=png&color=000000",
    "Breathwork": "https://img.icons8.com/?size=100&id=9798&format=png&color=000000",
    "Cardio": "https://img.icons8.com/?size=100&id=71221&format=png&color=000000",
    "Cycling": "https://img.icons8.com/?size=100&id=9782&format=png&color=000000",
    "Elliptical": "https://img.icons8.com/?size=100&id=9796&format=png&color=000000",
    "Hiking": "https://img.icons8.com/?size=100&id=9808&format=png&color=000000",
    "Indoor Cycling": "https://img.icons8.com/?size=100&id=63305&format=png&color=000000",
    "Meditation": "https://img.icons8.com/?size=100&id=9786&format=png&color=000000",
    "Pilates": "https://img.icons8.com/?size=100&id=66925&format=png&color=000000",
    "Running": "https://img.icons8.com/?size=100&id=9795&format=png&color=000000",
    "Strength Training": "https://img.icons8.com/?size=100&id=23279&format=png&color=000000",
    "Stretching": "https://img.icons8.com/?size=100&id=9799&format=png&color=000000",
    "Swimming": "https://img.icons8.com/?size=100&id=9803&format=png&color=000000",
    "Treadmill Running": "https://img.icons8.com/?size=100&id=9794&format=png&color=000000",
    "Walking": "https://img.icons8.com/?size=100&id=9807&format=png&color=000000",
    "Yoga": "https://img.icons8.com/?size=100&id=9783&format=png&color=000000",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_activity_type(activity_type, activity_name=""):
    """Format activity type and subtype based on activity type key."""
    if "cycling" in activity_type or "bike" in activity_type or "Bike" in activity_name:
        return ("Cycling", "Indoor Cycling") if "indoor" in activity_type else ("Cycling", "Cycling")
    elif "running" in activity_type or "Run" in activity_name:
        return ("Running", "Treadmill Running") if "treadmill" in activity_type else ("Running", "Running")
    elif "walking" in activity_type or "Walk" in activity_name:
        return ("Walking", "Walking")
    elif "hiking" in activity_type or "Hike" in activity_name:
        return ("Hiking", "Hiking")
    elif "swimming" in activity_type or "Swim" in activity_name:
        return ("Swimming", "Swimming")
    elif "strength" in activity_type or "Strength" in activity_name:
        return ("Strength Training", "Strength Training")
    elif "yoga" in activity_type or "Yoga" in activity_name:
        return ("Yoga", "Yoga")
    elif "pilates" in activity_type or "Pilates" in activity_name:
        return ("Pilates", "Pilates")
    elif "barre" in activity_type or "Barre" in activity_name:
        return ("Barre", "Barre")
    elif "meditation" in activity_type or "Meditation" in activity_name:
        return ("Meditation", "Meditation")
    elif "breathwork" in activity_type or "Breathwork" in activity_name or "Breathing" in activity_name:
        return ("Breathwork", "Breathwork")
    elif "stretching" in activity_type or "Stretch" in activity_name:
        return ("Stretching", "Stretching")
    elif "cardio" in activity_type or "Cardio" in activity_name:
        return ("Cardio", "Cardio")
    elif "elliptical" in activity_type or "Elliptical" in activity_name:
        return ("Elliptical", "Elliptical")
    else:
        return (activity_type.replace('_', ' ').title(), activity_type.replace('_', ' ').title())

def format_entertainment(activity_name):
    """Format entertainment/activity name for Peloton activities."""
    if "Peloton" in activity_name:
        parts = activity_name.split(" - ")
        if len(parts) >= 3:
            return f"{parts[0]} - {parts[1]}"
    return activity_name

def format_training_message(message):
    """Format training effect message."""
    if not message:
        return "Unknown"
    formatted = message.replace('_', ' ').title()
    formatted = formatted.replace('Hr', 'Heart Rate').replace('Vo2', 'VO2')
    return formatted

def format_training_effect(label):
    """Format training effect label."""
    if not label:
        return "Unknown"
    return label.replace('_', ' ').title()

def format_pace(average_speed):
    """Format pace from speed."""
    if average_speed and average_speed > 0:
        pace_seconds = 1000 / average_speed
        pace_minutes = int(pace_seconds // 60)
        pace_seconds = int(pace_seconds % 60)
        return f"{pace_minutes}:{pace_seconds:02d}"
    return "N/A"

def format_duration(seconds):
    """Format duration in hours and minutes."""
    minutes = (seconds or 0) // 60
    return f"{minutes // 60}h {minutes % 60}m"

def format_time(timestamp):
    """Format timestamp for Notion."""
    return (
        datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if timestamp else None
    )

def format_time_readable(timestamp):
    """Format timestamp for readable display."""
    return (
        datetime.fromtimestamp(timestamp / 1000, SLEEP_TZ).strftime("%H:%M")
        if timestamp else "Unknown"
    )

def format_date_for_name(sleep_date):
    """Format date for sleep entry name."""
    return datetime.strptime(sleep_date, "%Y-%m-%d").strftime("%d.%m.%Y") if sleep_date else "Unknown"

# ============================================================================
# ACTIVITIES SYNC
# ============================================================================

def get_all_activities(garmin, max_activities=1000, batch_size=100):
    """Get activities from Garmin Connect in batches."""
    all_activities = []
    offset = 0
    
    print(f"   Fetching up to {max_activities} activities...")
    
    while offset < max_activities:
        try:
            activities = garmin.get_activities(offset, batch_size)
            if not activities:
                break
            all_activities.extend(activities)
            offset += batch_size
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"   ⚠️  Error at offset {offset}: {e}")
            break
    
    return all_activities

def activity_exists(client, database_id, activity_date, activity_type, activity_name):
    """Check if activity exists in Notion."""
    if isinstance(activity_type, tuple):
        main_type, _ = activity_type
    else:
        main_type = activity_type[0] if isinstance(activity_type, (list, tuple)) else activity_type
    
    lookup_type = "Stretching" if "stretch" in activity_name.lower() else main_type
    
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"equals": activity_date.split('T')[0]}},
                {"property": "Activity Type", "select": {"equals": lookup_type}},
                {"property": "Activity Name", "title": {"equals": activity_name}}
            ]
        }
    )
    results = query['results']
    return results[0] if results else None

def create_activity(client, database_id, activity):
    """Create activity in Notion."""
    activity_date = activity.get('startTimeGMT')
    activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
    activity_type, activity_subtype = format_activity_type(
        activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )
    
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
        "Aerobic Effect": {"select": {"name": format_training_message(activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
        "Anaerobic": {"number": round(activity.get('anaerobicTrainingEffect', 0), 1)},
        "Anaerobic Effect": {"select": {"name": format_training_message(activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
        "PR": {"checkbox": activity.get('pr', False)},
        "Fav": {"checkbox": activity.get('favorite', False)}
    }
    
    page = {"parent": {"database_id": database_id}, "properties": properties}
    if icon_url:
        page["icon"] = {"type": "external", "external": {"url": icon_url}}
    
    client.pages.create(**page)

def sync_activities(garmin, client, database_id, max_activities):
    """Sync all activities from Garmin to Notion."""
    print("\n📊 SYNCING ACTIVITIES")
    print("=" * 40)
    
    activities = get_all_activities(garmin, max_activities, BATCH_SIZE)
    print(f"   Found {len(activities)} activities")
    
    created, skipped = 0, 0
    for activity in activities:
        activity_date = activity.get('startTimeGMT')
        activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
        activity_type, _ = format_activity_type(
            activity.get('activityType', {}).get('typeKey', 'Unknown'),
            activity_name
        )
        
        if not activity_exists(client, database_id, activity_date, activity_type, activity_name):
            try:
                create_activity(client, database_id, activity)
                created += 1
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
        else:
            skipped += 1
    
    print(f"   ✅ Created: {created}, Skipped: {skipped}")
    return created, skipped

# ============================================================================
# DAILY STEPS SYNC
# ============================================================================

def get_historical_daily_steps(garmin, days_back):
    """Get historical daily steps from Garmin."""
    enddate = date.today()
    startdate = enddate - timedelta(days=days_back)
    daterange = [startdate + timedelta(days=x) for x in range((enddate - startdate).days)]
    
    daily_steps = []
    for d in daterange:
        try:
            daily_steps += garmin.get_daily_steps(d.isoformat(), d.isoformat())
        except:
            continue
    return daily_steps

def daily_steps_exist(client, database_id, activity_date):
    """Check if daily steps exist in Notion."""
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Date", "date": {"equals": activity_date}},
                {"property": "Activity Type", "title": {"equals": "Walking"}}
            ]
        }
    )
    results = query['results']
    return results[0] if results else None

def create_daily_steps(client, database_id, steps):
    """Create daily steps entry in Notion."""
    total_distance = steps.get('totalDistance') or 0
    properties = {
        "Activity Type": {"title": [{"text": {"content": "Walking"}}]},
        "Date": {"date": {"start": steps.get('calendarDate')}},
        "Total Steps": {"number": steps.get('totalSteps')},
        "Step Goal": {"number": steps.get('stepGoal')},
        "Total Distance (km)": {"number": round(total_distance / 1000, 2)}
    }
    client.pages.create(parent={"database_id": database_id}, properties=properties)

def sync_daily_steps(garmin, client, database_id, days_back):
    """Sync daily steps from Garmin to Notion."""
    print("\n👣 SYNCING DAILY STEPS")
    print("=" * 40)
    print(f"   Fetching last {days_back} days...")
    
    daily_steps = get_historical_daily_steps(garmin, days_back)
    print(f"   Found {len(daily_steps)} days of data")
    
    created, skipped = 0, 0
    for steps in daily_steps:
        steps_date = steps.get('calendarDate')
        if not daily_steps_exist(client, database_id, steps_date):
            try:
                create_daily_steps(client, database_id, steps)
                created += 1
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
        else:
            skipped += 1
    
    print(f"   ✅ Created: {created}, Skipped: {skipped}")
    return created, skipped

# ============================================================================
# SLEEP DATA SYNC
# ============================================================================

def get_historical_sleep_data(garmin, days_back):
    """Get historical sleep data from Garmin."""
    enddate = date.today()
    startdate = enddate - timedelta(days=days_back)
    daterange = [startdate + timedelta(days=x) for x in range((enddate - startdate).days)]
    
    sleep_data_list = []
    for d in daterange:
        try:
            data = garmin.get_sleep_data(d.isoformat())
            if data:
                sleep_data_list.append(data)
        except:
            continue
    return sleep_data_list

def sleep_data_exists(client, database_id, sleep_date):
    """Check if sleep data exists in Notion."""
    query = client.databases.query(
        database_id=database_id,
        filter={"property": "Long Date", "date": {"equals": sleep_date}}
    )
    results = query.get('results', [])
    return results[0] if results else None

def create_sleep_data(client, database_id, data):
    """Create sleep data entry in Notion."""
    daily_sleep = data.get('dailySleepDTO', {})
    if not daily_sleep:
        return False
    
    sleep_date = daily_sleep.get('calendarDate', "Unknown Date")
    total_sleep = sum((daily_sleep.get(k, 0) or 0) for k in ['deepSleepSeconds', 'lightSleepSeconds', 'remSleepSeconds'])
    
    if total_sleep == 0:
        return False
    
    properties = {
        "Date": {"title": [{"text": {"content": format_date_for_name(sleep_date)}}]},
        "Times": {"rich_text": [{"text": {"content": f"{format_time_readable(daily_sleep.get('sleepStartTimestampGMT'))} → {format_time_readable(daily_sleep.get('sleepEndTimestampGMT'))}"}}]},
        "Long Date": {"date": {"start": sleep_date}},
        "Full Date/Time": {"date": {"start": format_time(daily_sleep.get('sleepStartTimestampGMT')), "end": format_time(daily_sleep.get('sleepEndTimestampGMT'))}},
        "Total Sleep (h)": {"number": round(total_sleep / 3600, 1)},
        "Light Sleep (h)": {"number": round(daily_sleep.get('lightSleepSeconds', 0) / 3600, 1)},
        "Deep Sleep (h)": {"number": round(daily_sleep.get('deepSleepSeconds', 0) / 3600, 1)},
        "REM Sleep (h)": {"number": round(daily_sleep.get('remSleepSeconds', 0) / 3600, 1)},
        "Awake Time (h)": {"number": round(daily_sleep.get('awakeSleepSeconds', 0) / 3600, 1)},
        "Total Sleep": {"rich_text": [{"text": {"content": format_duration(total_sleep)}}]},
        "Light Sleep": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('lightSleepSeconds', 0))}}]},
        "Deep Sleep": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('deepSleepSeconds', 0))}}]},
        "REM Sleep": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('remSleepSeconds', 0))}}]},
        "Awake Time": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('awakeSleepSeconds', 0))}}]},
        "Resting HR": {"number": data.get('restingHeartRate', 0)}
    }
    
    client.pages.create(parent={"database_id": database_id}, properties=properties, icon={"emoji": "😴"})
    return True

def sync_sleep_data(garmin, client, database_id, days_back):
    """Sync sleep data from Garmin to Notion."""
    print("\n😴 SYNCING SLEEP DATA")
    print("=" * 40)
    print(f"   Fetching last {days_back} days...")
    
    sleep_data_list = get_historical_sleep_data(garmin, days_back)
    print(f"   Found {len(sleep_data_list)} days of data")
    
    created, skipped = 0, 0
    for data in sleep_data_list:
        daily_sleep = data.get('dailySleepDTO', {})
        sleep_date = daily_sleep.get('calendarDate')
        
        if sleep_date and not sleep_data_exists(client, database_id, sleep_date):
            try:
                if create_sleep_data(client, database_id, data):
                    created += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
        else:
            skipped += 1
    
    print(f"   ✅ Created: {created}, Skipped: {skipped}")
    return created, skipped

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Sync historical Garmin data to Notion')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS_TO_SYNC,
                        help=f'Days to sync for steps/sleep (default: {DEFAULT_DAYS_TO_SYNC})')
    parser.add_argument('--activities', type=int, default=DEFAULT_MAX_ACTIVITIES,
                        help=f'Max activities to sync (default: {DEFAULT_MAX_ACTIVITIES})')
    args = parser.parse_args()
    
    load_dotenv()
    
    # Get environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    activities_db = os.getenv("NOTION_DB_ID")
    steps_db = os.getenv("NOTION_STEPS_DB_ID")
    sleep_db = os.getenv("NOTION_SLEEP_DB_ID")
    
    if not all([garmin_email, garmin_password, notion_token]):
        print("❌ Missing required environment variables!")
        return
    
    print("=" * 50)
    print("🚀 GARMIN TO NOTION - HISTORICAL SYNC")
    print("=" * 50)
    print(f"📅 Days to sync: {args.days}")
    print(f"🏃 Max activities: {args.activities}")
    
    # Login to Garmin
    try:
        garmin = Garmin(garmin_email, garmin_password)
        garmin.login()
        print("✅ Logged in to Garmin Connect")
    except Exception as e:
        print(f"❌ Garmin login failed: {e}")
        return
    
    # Connect to Notion
    client = Client(auth=notion_token)
    print("✅ Connected to Notion")
    
    total_created, total_skipped = 0, 0
    
    # Sync Activities
    if activities_db:
        c, s = sync_activities(garmin, client, activities_db, args.activities)
        total_created += c
        total_skipped += s
    else:
        print("\n⚠️  NOTION_DB_ID not set, skipping activities")
    
    # Sync Daily Steps
    if steps_db:
        c, s = sync_daily_steps(garmin, client, steps_db, args.days)
        total_created += c
        total_skipped += s
    else:
        print("\n⚠️  NOTION_STEPS_DB_ID not set, skipping steps")
    
    # Sync Sleep Data
    if sleep_db:
        c, s = sync_sleep_data(garmin, client, sleep_db, args.days)
        total_created += c
        total_skipped += s
    else:
        print("\n⚠️  NOTION_SLEEP_DB_ID not set, skipping sleep")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ HISTORICAL SYNC COMPLETED!")
    print("=" * 50)
    print(f"📊 Total created: {total_created}")
    print(f"⏭️  Total skipped: {total_skipped}")
    print("\n💡 Use the daily sync workflow for regular updates")

if __name__ == '__main__':
    main()
