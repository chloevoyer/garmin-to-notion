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
    # [修复] 这里的 property 必须是 "长日期" (Long Date)
    query = client.databases.query(
        database_id=database_id,
        filter={"property": "长日期", "date": {"equals": sleep_date}}
    )
    results = query.get('results', [])
    return results[0] if results else None
    
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

    # [新增] 计算是否达成睡眠目标 (这里默认设为 8 小时，即 28800 秒)
    # 如果你想改成 7 小时，就把 28800 改成 25200 (7 * 3600)
    sleep_goal_seconds = 8 * 3600 
    is_goal_met = total_sleep >= sleep_goal_seconds

    properties = {
        "日期": {"title": [{"text": {"content": format_date_for_name(sleep_date)}}]},
        "时间段": {"rich_text": [{"text": {"content": f"{format_time_readable(daily_sleep.get('sleepStartTimestampGMT'))} → {format_time_readable(daily_sleep.get('sleepEndTimestampGMT'))}"}}]},
        "长日期": {"date": {"start": sleep_date}},
        "完整时间": {"date": {"start": format_time(daily_sleep.get('sleepStartTimestampGMT')), "end": format_time(daily_sleep.get('sleepEndTimestampGMT'))}},
        "总睡眠 (h)": {"number": round(total_sleep / 3600, 1)},
        "浅睡 (h)": {"number": round(daily_sleep.get('lightSleepSeconds', 0) / 3600, 1)},
        "深睡 (h)": {"number": round(daily_sleep.get('deepSleepSeconds', 0) / 3600, 1)},
        "快速眼动 (h)": {"number": round(daily_sleep.get('remSleepSeconds', 0) / 3600, 1)},
        "清醒时间 (h)": {"number": round(daily_sleep.get('awakeSleepSeconds', 0) / 3600, 1)},
        "总睡眠时长": {"rich_text": [{"text": {"content": format_duration(total_sleep)}}]},
        "浅睡时长": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('lightSleepSeconds', 0))}}]},
        "深睡时长": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('deepSleepSeconds', 0))}}]},
        "快速眼动时长": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('remSleepSeconds', 0))}}]},
        "清醒时长": {"rich_text": [{"text": {"content": format_duration(daily_sleep.get('awakeSleepSeconds', 0))}}]},
        "静息心率": {"number": sleep_data.get('restingHeartRate', 0)},
        "睡眠目标": {"checkbox": is_goal_met} # [新增] 写入 checkbox 状态
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
    garmin = Garmin(garmin_email, garmin_password, is_cn=True)
    garmin.login()
    client = Client(auth=notion_token)

    data = get_sleep_data(garmin)
    if data:
        sleep_date = data.get('dailySleepDTO', {}).get('calendarDate')
        if sleep_date and not sleep_data_exists(client, database_id, sleep_date):
            create_sleep_data(client, database_id, data, skip_zero_sleep=True)

if __name__ == '__main__':
    main()
