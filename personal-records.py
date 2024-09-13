from datetime import date, datetime
from garminconnect import Garmin
from notion_client import Client
import os

# ... (keep all the existing functions up to update_record)

def update_record(client, page_id, activity_date, pr_value, is_pr=True):
    """
    Update an existing record in the Notion database.
    """
    properties = {
        "Date": {"date": {"start": activity_date}},
        "PR": {"checkbox": is_pr}
    }
    
    # Only update the Value if pr_value is not None and is a non-empty string
    if pr_value and isinstance(pr_value, str):
        properties["Value"] = {"rich_text": [{"text": {"content": pr_value}}]}
    
    try:
        client.pages.update(
            page_id=page_id,
            properties=properties
        )
    except Exception as e:
        print(f"Error updating record: {e}")

def write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value):
    """
    Write a new record to the Notion database.
    """
    properties = {
        "Date": {"date": {"start": activity_date}},
        "Activity Type": {"select": {"name": activity_type}},
        "Activity Name": {"title": [{"text": {"content": activity_name}}]},
        "typeId": {"number": typeId},
        "PR": {"checkbox": True}
    }
    
    # Only add the Value if pr_value is not None and is a non-empty string
    if pr_value and isinstance(pr_value, str):
        properties["Value"] = {"rich_text": [{"text": {"content": pr_value}}]}
    
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
        pr_value = format_garmin_value(record.get('value', 0), activity_type, typeId)

        existing_record = get_existing_record(client, database_id, activity_name)

        if existing_record:
            existing_date = existing_record['properties']['Date']['date']['start']
            if activity_date > existing_date:
                # New PR: Update the existing record and mark it as not PR
                update_record(client, existing_record['id'], existing_date, None, False)
                print(f"Archived old record: {activity_type} - {activity_name}")
                
                # Create a new record for the new PR
                write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value)
                print(f"Created new PR record: {activity_type} - {activity_name}")
            else:
                print(f"No update needed: {activity_type} - {activity_name}")
        else:
            # New record: Write to Notion
            write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value)
            print(f"Successfully written new record: {activity_type} - {activity_name}")

if __name__ == '__main__':
    main()
