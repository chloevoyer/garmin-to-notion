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
    # (Keep the existing format_garmin_value function as is)
    pass

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
    """
    Check if a record with the given activity name exists in the Notion database.
    """
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

def update_record(client, page_id, activity_date, pr_value, is_pr=True):
    """
    Update an existing record in the Notion database.
    """
    client.pages.update(
        page_id=page_id,
        properties={
            "Date": {"date": {"start": activity_date}},
            "Value": {"rich_text": [{"text": {"content": pr_value}}]},
            "PR": {"checkbox": is_pr}
        }
    )

def write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value):
    """
    Write a new record to the Notion database.
    """
    client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Date": {"date": {"start": activity_date}},
            "Activity Type": {"select": {"name": activity_type}},
            "Activity Name": {"title": [{"text": {"content": activity_name}}]},
            "typeId": {"number": typeId},
            "Value": {"rich_text": [{"text": {"content": pr_value}}]},
            "PR": {"checkbox": True}
        }
    )

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
        pr_value = format_garmin_value(record.get('value', 0), activity_type, typeId)

        existing_record = get_existing_record(client, database_id, activity_name)

        if existing_record:
            existing_date = existing_record['properties']['Date']['date']['start']
            if activity_date > existing_date:
                # New PR: Update the existing record and mark it as PR
                update_record(client, existing_record['id'], activity_date, pr_value, True)
                print(f"Updated PR: {activity_type} - {activity_name}")
                
                # Archive the old record by unchecking the PR checkbox
                update_record(client, existing_record['id'], existing_date, existing_record['properties']['Value']['rich_text'][0]['text']['content'], False)
                print(f"Archived old record: {activity_type} - {activity_name}")
                
                # Create a new record for the new PR
                write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value)
                print(f"Created new PR record: {activity_type} - {activity_name}")
            else:
                print(f"No update needed: {activity_type} - {activity_name}")
        else:
            # New record: Write to Notion
            try:
                write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value)
                print(f"Successfully written new record: {activity_type} - {activity_name}")
            except Exception as e:
                print(f"Failed to write to Notion: {e}")

if __name__ == '__main__':
    main()
