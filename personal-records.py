from datetime import date, datetime
from garminconnect import Garmin
from notion_client import Client
import os

def get_icon_for_record(activity_name):
    icon_map = {
        "1K": "🥇",
        "1mi": "⚡",
        "5K": "👟",
        "10K": "⭐",
        "Longest Run": "🏃",
        "Longest Ride": "🚴",
        "Total Ascent": "🚵",
        "Max Avg Power (20 min)": "🔋",
        "Most Steps in a Day": "👣",
        "Most Steps in a Week": "🚶",
        "Most Steps in a Month": "📅",
        "Longest Goal Streak": "✔️",
        "Other": "🏅"
    }
    return icon_map.get(activity_name, "🏅")  # Default to "Other" icon if not found

def get_cover_for_record(activity_name):
    cover_map = {
        "1K": "https://images.unsplash.com/photo-1526676537331-7747bf8278fc?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "1mi": "https://images.unsplash.com/photo-1638183395699-2c0db5b6afbb?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "5K": "https://images.unsplash.com/photo-1571008887538-b36bb32f4571?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "10K": "https://images.unsplash.com/photo-1529339944280-1a37d3d6fa8c?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Longest Run": "https://images.unsplash.com/photo-1532383282788-19b341e3c422?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Longest Ride": "https://images.unsplash.com/photo-1471506480208-91b3a4cc78be?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Max Avg Power (20 min)": "https://images.unsplash.com/photo-1591741535018-d042766c62eb?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w2MzkyMXwwfDF8c2VhcmNofDJ8fHNwaW5uaW5nfGVufDB8fHx8MTcyNjM1Mzc0Mnww&ixlib=rb-4.0.3&q=80&w=4800",
        "Most Steps in a Day": "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Most Steps in a Week": "https://images.unsplash.com/photo-1602174865963-9159ed37e8f1?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Most Steps in a Month": "https://images.unsplash.com/photo-1580058572462-98e2c0e0e2f0?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800",
        "Longest Goal Streak": "https://images.unsplash.com/photo-1477332552946-cfb384aeaf1c?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800"
    }
    return cover_map.get(activity_name, "https://images.unsplash.com/photo-1471506480208-91b3a4cc78be?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=4800") 

def format_activity_type(activity_type):
    if activity_type is None:
        return "Walking"
    return activity_type.replace('_', ' ').title()

def format_activity_name(activity_name):
    if not activity_name or activity_name is None:
        return "Unnamed Activity"
    return activity_name

def format_garmin_value(value, activity_type, typeId):
    if typeId  == 1:  # 1K
        total_seconds = round(value)  # Round to the nearest second
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted_value = f"{minutes}:{seconds:02d} /km"
        pace = formatted_value  # For these types, the value is the pace
        return formatted_value, pace

    if typeId  == 2:  # 1mile
        total_seconds = round(value)  # Round to the nearest second
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted_value = f"{minutes}:{seconds:02d}"
        total_pseconds = total_seconds / 1.60934  # Divide by 1.60934 to get pace per km
        pminutes = int(total_pseconds // 60)      # Convert to integer
        pseconds = int(total_pseconds % 60)       # Convert to integer
        formatted_pace = f"{pminutes}:{pseconds:02d} /km"
        return formatted_value, formatted_pace

    if typeId == 3:  # 5K
        total_seconds = round(value) 
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted_value = f"{minutes}:{seconds:02d}"
        total_pseconds = total_seconds // 5  # Divide by 5km
        pminutes = total_pseconds // 60
        pseconds = total_pseconds % 60
        formatted_pace = f"{pminutes}:{pseconds:02d} /km"
        return formatted_value, formatted_pace

    if typeId == 4:  # 10K
        # Round to the nearest second
        total_seconds = round(value)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            formatted_value = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            formatted_value = f"{minutes}:{seconds:02d}"
        total_pseconds = total_seconds // 10  # Divide by 10km
        phours = total_pseconds // 3600
        pminutes = (total_pseconds % 3600) // 60
        pseconds = total_pseconds % 60
        formatted_pace = f"{pminutes}:{pseconds:02d} /km"
        return formatted_value, formatted_pace

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
                {"property": "Record", "title": {"equals": activity_name}},
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
                {"property": "Record", "title": {"equals": activity_name}},
                {"property": "Date", "date": {"equals": activity_date}}
            ]
        }
    )
    return query['results'][0] if query['results'] else None

def update_record(client, page_id, activity_date, value, pace, activity_name, is_pr=True):
    properties = {
        "Date": {"date": {"start": activity_date}},
        "PR": {"checkbox": is_pr}
    }
    
    if value:
        properties["Value"] = {"rich_text": [{"text": {"content": value}}]}
    
    if pace:
        properties["Pace"] = {"rich_text": [{"text": {"content": pace}}]}

    icon = get_icon_for_record(activity_name)
    cover = get_cover_for_record(activity_name)

    try:
        client.pages.update(
            page_id=page_id,
            properties=properties,
            icon={"emoji": icon},
            cover={"type": "external", "external": {"url": cover}}
        )
        
    except Exception as e:
        print(f"Error updating record: {e}")

def write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace):
    properties = {
        "Date": {"date": {"start": activity_date}},
        "Activity Type": {"select": {"name": activity_type}},
        "Record": {"title": [{"text": {"content": activity_name}}]},
        "typeId": {"number": typeId},
        "PR": {"checkbox": True}
    }
    
    if value:
        properties["Value"] = {"rich_text": [{"text": {"content": value}}]}
    
    if pace:
        properties["Pace"] = {"rich_text": [{"text": {"content": pace}}]}
    
    icon = get_icon_for_record(activity_name)
    cover = get_cover_for_record(activity_name)

    try:
        client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            icon={"emoji": icon},
            cover={"type": "external", "external": {"url": cover}}
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

        existing_pr_record = get_existing_record(client, database_id, activity_name)
        existing_date_record = get_record_by_date_and_name(client, database_id, activity_date, activity_name)

        if existing_date_record:
            update_record(client, existing_date_record['id'], activity_date, value, pace, activity_name, True)
            print(f"Updated existing record: {activity_type} - {activity_name}")
        elif existing_pr_record:
            # Add error handling here
            try:
                date_prop = existing_pr_record['properties']['Date']
                if date_prop and date_prop.get('date') and date_prop['date'].get('start'):
                    existing_date = date_prop['date']['start']
                    
                    if activity_date > existing_date:
                        update_record(client, existing_pr_record['id'], existing_date, None, None, activity_name, False)
                        print(f"Archived old record: {activity_type} - {activity_name}")
                        
                        write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace)
                        print(f"Created new PR record: {activity_type} - {activity_name}")
                    else:
                        print(f"No update needed: {activity_type} - {activity_name}")
                else:
                    # Handle case where date is missing or improperly formatted
                    print(f"Warning: Record {activity_name} has invalid date format - updating anyway")
                    update_record(client, existing_pr_record['id'], activity_date, value, pace, activity_name, True)
            except (KeyError, TypeError) as e:
                print(f"Error processing record {activity_name}: {e}")
                print(f"Record data: {existing_pr_record['properties']}")
                # Fallback - create new record if we can't process the existing one properly
                write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace)
        else:
            write_new_record(client, database_id, activity_date, activity_type, activity_name, typeId, value, pace)
            print(f"Successfully written new record: {activity_type} - {activity_name}")

if __name__ == '__main__':
    main()
