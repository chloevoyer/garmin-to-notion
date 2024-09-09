
from datetime import date, datetime
from garminconnect import Garmin
from notion_client import Client

def format_activity_type(activity_type):
    """
    Formats the activity type, ensuring it is not None.

    Parameters:
        activity_type (str or None): The activity type to format.

    Returns:
        str: The formatted activity type or a default string if None.
    """
    if activity_type is None:
        return "Walking"  # or any default value you prefer
    return activity_type.replace('_', ' ').title()

def format_activity_name(activity_name):
    """
    Formats the activity name, ensuring it is not None.

    Parameters:
        activity_name (str): The activity name to format.

    Returns:
        str: The formatted activity name or a default name if None.
    """
    # Check if activity_name is None or empty and replace it with a default string
    if not activity_name or activity_name is None:
        return "Unnamed Activity"
    return activity_name

def format_entertainment(activity_name):
    """
    Formats the activity name, replacing 'ENTERTAINMENT' with 'Netflix'.
    
    Parameters:
        activity_name (str or None): The activity name to format.
    
    Returns:
        str: The formatted activity name or an empty string if None.
    """
    if activity_name is None:
        return ""  # Return an empty string or any default value if activity_name is None
    return activity_name.replace('ENTERTAINMENT', 'Netflix')

def format_garmin_value_to_time(value):
    """
    Format a Garmin value in seconds into a time string.
    
    Parameters:
        value (float): The time value in seconds.
    
    Returns:
        str: Formatted time string in "MM:SS" or "HH:MM:SS" format.
    """
    if int(value // 60) < 60:  # If total time is less than an hour
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        time_string = f"{minutes}:{seconds:05.2f}"
    else:  # If total time is one hour or more
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = round(value % 60, 2)
        time_string = f"{hours}:{minutes:02}:{seconds:05.2f}"
    
    return time_string

def write_row(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value):
    """
    Writes a row to the Notion database with the specified activity details.
    """
    client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Date": {"date": {"start": activity_date}},
            "Activity Type": {"select": {"name": activity_type}},
            "Activity Name": {"title": [{"text": {"content": activity_name}}]},
            "typeId": {"number": typeId},
            "Value": {"rich_text": [{"text": {"content": pr_value}}]}
        }
    )

def main():
    # Notion integration credentials
    PG_ID = 'e2c8f20577304f5b968da7d95a46f8d8'  # Notion Page ID 
    DB_ID = 'dc44f72c041840d2bd1751b2d37336b4'  # Notion Database ID
    NOTION_TOKEN = 'secret_WdTG9OOoFgCHNhQBgQFSWenBH4kPvWfyQGTZ4H3aoT2'  # Notion Integration Token

    # Garmin credentials
    email = "chloe.voyer@hotmail.com"
    password = "1AAeL0O*40iZ"

    # Initialize Garmin client and login
    garmin = Garmin(email, password)
    garmin.login()

    # Initialize Notion client with the correct token
    client = Client(auth=NOTION_TOKEN)

    records = garmin.get_personal_record()
    print(records)    
    print(len(records))  

    for record in records:
        activity_date = record.get('prStartTimeGmtFormatted')
        activity_type = format_activity_type(record.get('activityType'))
        activity_name = format_activity_name(format_entertainment(record.get('activityName')))
        typeId = record.get('typeId', 0)
        pr_value = format_garmin_value_to_time(record.get('value', 0))   

        # Write to Notion
        try:
            write_row(client, DB_ID, activity_date, activity_type, activity_name, typeId, pr_value)
            print(f"Successfully written: {activity_type} - {activity_name}")
        except Exception as e:
            print(f"Failed to write to Notion: {e}")

if __name__ == '__main__':
    main()

