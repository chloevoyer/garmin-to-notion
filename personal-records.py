from datetime import date, datetime
from garminconnect import Garmin
from notion_client import Client
import os

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
    if activity_name is None:
        return ""  # Return an empty string or any default value if activity_name is None
    return activity_name.replace('ENTERTAINMENT', 'Netflix') # Formats the activity name, replacing 'ENTERTAINMENT' with 'Netflix'

def format_garmin_value(value, activity_type, typeId):
    # Apply specific formatting rules based on typeId
    if typeId == 3:
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        return f"{minutes}:{seconds:03}"

    if typeId == 4:
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        return f"{minutes}:{seconds:03}"

    if typeId in [7, 8]:
        value = value / 1000  # Divide value by 1000
        return f"{value:.2f} km"  # Format to 2 decimal places

    if typeId == 9:
        value = int(value)  # Convert to integer to remove decimal part
        return f"{value:,} m"  # Format with commas as thousands separators
    
    if typeId == 10:
        value = round(value)  # Round to integer
        return f"{value} W"  # Return as a string with 2 decimal places
    
    if typeId in [12, 13, 14]:
        value = round(value)  
        return f"{value:,}"  

    if typeId == 15:
        value = round(value) 
        return f"{value} days"  # Append " days" to the integer value

    # Default case for any other typeId, assume it's a time value
    if int(value // 60) < 60:  # If total time is less than an hour
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        return f"{minutes}:{seconds:03.1f}"
    else:  # If total time is one hour or more
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = round(value % 60, 2)
        return f"{hours}:{minutes:02}:{seconds:03}"

def replace_activity_name_by_typeId(typeId):
    """
    Replace activity_name based on typeId.
    
    Parameters:
        typeId (int): The type ID.
    
    Returns:
        str: The replaced activity name based on typeId.
    """
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
    return typeId_name_map.get(typeId, "Unnamed Activity")  # Default value if typeId is not in the map

def write_row(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value):
    # Writes a row to the Notion database with the specified activity details.
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
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_PR_DB_ID")

    # Initialize Garmin client and login
    garmin = Garmin(garmin_email, garmin_password)
    garmin.login()

    # Initialize Notion client with the correct token
    client = Client(auth=notion_token)

    records = garmin.get_personal_record()
    # print(records)    
    # print(len(records))  

    # Filter out records where typeId == 16
    filtered_records = [record for record in records if record.get('typeId') != 16]

    for record in filtered_records:
        activity_date = record.get('prStartTimeGmtFormatted')
        activity_type = format_activity_type(record.get('activityType'))
        activity_name = replace_activity_name_by_typeId(record.get('typeId'))  # Replace based on typeId
        typeId = record.get('typeId', 0)
        pr_value = format_garmin_value(record.get('value', 0), activity_type, typeId)   

        # Write to Notion
        try:
            write_row(client, database_id, activity_date, activity_type, activity_name, typeId, pr_value)
            print(f"Successfully written: {activity_type} - {activity_name}")
        except Exception as e:
            print(f"Failed to write to Notion: {e}")

if __name__ == '__main__':
    main()
