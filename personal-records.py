from datetime import date, datetime
from garminconnect import Garmin
from notion_client import Client
import os

def format_activity_type(activity_type):
    if activity_type is None:
        return "Walking"
    return activity_type.replace('_', ' ').title()

def format_activity_name(activity_name):
    if not activity_name or activity_name is None:
        return "Unnamed Activity"
    return activity_name

def format_entertainment(activity_name):
    if activity_name is None:
        return ""
    return activity_name.replace('ENTERTAINMENT', 'Netflix')

def format_garmin_value(value, activity_type, typeId):
    if typeId in [1, 2, 3, 4]:  # Distance-based records
        total_seconds = round(value)  # Round to the nearest second
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted_value = f"{minutes}:{seconds:02d}"
        pace = formatted_value  # For these types, the value is the pace
        return formatted_value, pace

    if typeId in [7, 8]:  # Longest Run, Longest Ride
        value_km = value / 1000
        formatted_value = f"{value_km:.2f} km"
        pace = ""  # No pace for these types
        return formatted_value, pace

    if typeId == 9:  # Total Ascent
        value_m = int(value)
        formatted_value = f"{value_m:,} m"
        pace = ""
        return formatted_value, pace

    if typeId == 10:  # Max Avg Power
        value_w = round(value)
        formatted_value = f"{value_w} W"
        pace = ""
        return formatted_value, pace

    if typeId in [12, 13, 14]:  # Step counts
        value_steps = round(value)
        formatted_value = f"{value_steps:,}"
        pace = ""
        return formatted_value, pace

    if typeId == 15:  # Longest Goal Streak
        value_days = round(value)
        formatted_value = f"{value_days} days"
        pace = ""
        return formatted_value, pace

    # Default case
    if int(value // 60) < 60:  # If total time is less than an hour
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        formatted_value = f"{minutes}:{seconds:05.2f}"
    else:  # If total time is one hour or more
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = round(value % 60, 2)
        formatted_value = f"{hours}:{minutes:02}:{seconds:05.2f}"
    
    pace = ""
    return formatted_value, pace

def replace_activity_name_by_typeId(typeId):
    typeId_name_map = {
        1: "1K",
        2: "1mi",
        3: "5K",
        4: "10K",
        7: "Longest Run",
        8: "Longest Ride",
        9: "Total Ascent",
        10: "Max Avg Power (20 min)",
        12: "Most Steps in a Day",
        13: "Most Steps in a Week",
        14: "Most Steps in a Month",
        15: "Longest Goal Streak"
    }
    return typeId_name_map.get(typeId, "Unnamed Activity")

def get_existing_record(client, database_id, activity_name):
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Activity Name", "title": {"equals": activity_name}},
                {"property": "PR", "checkbox": {"equals": True}}
            ]
        }
    )
    return query['results'][0] if query['results'] else None


def get_existing_record(client, database_id, activity_name):
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Activity Name", "title": {"equals": activity_name}},
                {"property": "PR", "checkbox": {"equals": True}}
            ]
        }
    )
    return query['results'][0] if query['results'] else None

def get_record_by_date_and_name(client, database_id, activity_date, activity_name):
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Activity Name", "title": {"equals": activity_name}},
                {"property": "Date", "date": {"equals": activity_date}}
            ]
        }
    )
    return query['results'][0] if query['results'] else None

def update_record(client, page_id, activity_date, value, pace, is_pr=True):
    properties = {
        "Date": {"date": {"start": activity_date}},
        "PR": {"checkbox": is_pr}
    }
    
    if value:
        properties["Value"] = {"rich_text": [{"text": {"content": value}}]}
    
    if pace:
        properties["Pace"] = {"rich_text": [{"text": {"content": pace}}]}
    
    try:
        client.pages.update(
            page_id=page_id,
            properties=properties
        )
    except Exception as e:
        print(f"Error updating record: {e}")

def write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace, seconds):
    properties = {
        "Date": {"date": {"start": activity_date}},
        "Activity Type": {"select": {"name": activity_type}},
        "Activity Name": {"title": [{"text": {"content": activity_name}}]},
        "typeId": {"number": typeId},
        "PR": {"checkbox": True}
    }
    
    if value:
        properties["Value"] = {"rich_text": [{"text": {"content": value}}]}
    
    if pace:
        properties["Pace"] = {"rich_text": [{"text": {"content": pace}}]}
    
    try:
        client.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
    except Exception as e:
        print(f"Error writing new record: {e}")

def main():
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_PR_DB_ID")

    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()

    client = Client(auth=notion_token)

    records = garmin.get_personal_record()
    filtered_records = [record for record in records if record.get('typeId') != 16]

    for record in filtered_records:
        activity_date = record.get('prStartTimeGmtFormatted')
        activity_type = format_activity_type(record.get('activityType'))
        activity_name = replace_activity_name_by_typeId(record.get('typeId'))
        typeId = record.get('typeId', 0)
        value, pace = format_garmin_value(record.get('value', 0), activity_type, typeId)
        seconds = record.get('value', 0)

        existing_pr_record = get_existing_record(client, database_id, activity_name)
        existing_date_record = get_record_by_date_and_name(client, database_id, activity_date, activity_name)

        if existing_date_record:
            # Update the existing record for this date and activity
            update_record(client, existing_date_record['id'], activity_date, value, pace, True)
            print(f"Updated existing record: {activity_type} - {activity_name}")
        elif existing_pr_record:
            existing_date = existing_pr_record['properties']['Date']['date']['start']
            if activity_date > existing_date:
                # Archive old record
                update_record(client, existing_pr_record['id'], existing_date, None, None, False)
                print(f"Archived old record: {activity_type} - {activity_name}")
                
                # Create new PR record
                write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace, seconds)
                print(f"Created new PR record: {activity_type} - {activity_name}")
            else:
                print(f"No update needed: {activity_type} - {activity_name}")
        else:
            # New record
            write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace, seconds)
            print(f"Successfully written new record: {activity_type} - {activity_name}")

if __name__ == '__main__':
    main()
