from datetime import datetime
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv, dotenv_values
import pytz
import os

# Constants
local_tz = pytz.timezone("America/New_York")

# Load environment variables
load_dotenv()
CONFIG = dotenv_values()

def get_sleep_data(garmin):
    today = datetime.today().date()
    return garmin.get_sleep_data(today.isoformat())

def format_duration(seconds):
    minutes = (seconds or 0) // 60
    return f"{minutes // 60}h {minutes % 60}m"

def format_time(timestamp):
    return (
        datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if timestamp else None
    )

def format_time_readable(timestamp):
    return (
        datetime.fromtimestamp(timestamp / 1000, local_tz).strftime("%H:%M")
        if timestamp else "Unknown"
    )

def format_date_for_name(sleep_date):
    return datetime.strptime(sleep_date, "%Y-%m-%d").strftime("%d.%m.%Y") if sleep_date else "Unknown"

def sleep_data_exists(client, database_id, sleep_date):
    query = client.databases.query(
        database_id=database_id,
        filter={"property": "Long Date", "date": {"equals": sleep_date}}
    )
    results = query.get('results', [])
    return results[0] if results else None  # Ensure it returns None instead of causing IndexError

def create_sleep_data(client, database_id, sleep_data, skip_zero_sleep=True):
    daily_sleep = sleep_data.get('dailySleepDTO', {})
    if not daily_sleep:
        return
    
    sleep_date = daily_sleep.get('calendarDate', "Unknown Date")
    total_sleep = sum(
        (daily_sleep.get(k, 0) or 0) for k in ['deepSleepSeconds', 'lightSleepSeconds', 'remSleepSeconds']
    )
    
    
    if skip_zero_sleep and total_sleep == 0:
        print(f"Skipping sleep data for {sleep_date} as total sleep is 0")
        return

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
        "Resting HR": {"number": sleep_data.get('restingHeartRate', 0)}
    }
    
    client.pages.create(parent={"database_id": database_id}, properties=properties, icon={"emoji": "😴"})
    print(f"Created sleep entry for: {sleep_date}")

def main():
    load_dotenv()

    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_SLEEP_DB_ID")

    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    client = Client(auth=notion_token)

    data = get_sleep_data(garmin)
    if data:
        sleep_date = data.get('dailySleepDTO', {}).get('calendarDate')
        if sleep_date and not sleep_data_exists(client, database_id, sleep_date):
            create_sleep_data(client, database_id, data, skip_zero_sleep=True)

if __name__ == '__main__':
    main()
