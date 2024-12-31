from datetime import date, datetime, timedelta
from garminconnect import Garmin
from notion_client import Client
import os

def get_all_daily_steps(garmin):
    """
    Get last 60 days of daily step count data from Garmin Connect.
    """
    startdate = date.today() - timedelta(days=60)
    daterange = [startdate + timedelta(days=x) 
                 for x in range((date.today() - startdate).days)] # excl. today
    daily_steps = []
    for d in daterange:
        daily_steps += garmin.get_daily_steps(d.isoformat(), d.isoformat())
    return daily_steps

def daily_steps_exist(client, database_id, activity_date):
    """
    Check if daily step count already exists in the Notion database.
    """
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

def steps_need_update(existing_steps, new_steps):
    """
    Compare existing steps data with imported data to determine if an update is needed.
    """
    existing_props = existing_steps['properties']
    activity_type = "Walking"
    
    return (
        existing_props['Total Steps']['number'] != new_steps.get('totalSteps') or
        existing_props['Step Goal']['number'] != new_steps.get('stepGoal') or
        existing_props['Total Distance (km)']['number'] != new_steps.get('totalDistance') or
        existing_props['Activity Type']['title'] != activity_type
    )

def update_daily_steps(client, existing_steps, new_steps):
    """
    Update an existing daily steps entry in the Notion database with new data.
    """
    properties = {
        "Activity Type":  {"title": [{"text": {"content": "Walking"}}]},
        "Total Steps": {"number": new_steps.get('totalSteps')},
        "Step Goal": {"number": new_steps.get('stepGoal')},
        "Total Distance (km)": {"number": new_steps.get('totalDistance')}
    }
    
    update = {
        "page_id": existing_steps['id'],
        "properties": properties,
    }
        
    client.pages.update(**update)

def create_daily_steps(client, database_id, steps):
    """
    Create a new daily steps entry in the Notion database.
    """
    properties = {
        "Activity Type": {"title": [{"text": {"content": "Walking"}}]},
        "Date": {"date": {"start": steps.get('calendarDate')}},
        "Total Steps": {"number": steps.get('totalSteps')},
        "Step Goal": {"number": steps.get('stepGoal')},
        "Total Distance (km)": {"number": steps.get('totalDistance')}
    }
    
    page = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    
    client.pages.create(**page)

def main():
    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_GARMINTOKEN")
    database_id = os.getenv("NOTION_DB_ID_STEPS")

    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()
    client = Client(auth=notion_token)

    daily_steps = get_all_daily_steps(garmin)
    for steps in daily_steps:
        steps_date = steps.get('calendarDate')
        existing_steps = daily_steps_exist(client, database_id, steps_date)
        if existing_steps:
            if steps_need_update(existing_steps, steps):
                update_daily_steps(client, existing_steps, steps)
        else:
            create_daily_steps(client, database_id, steps)

if __name__ == '__main__':
    main()
# %%
