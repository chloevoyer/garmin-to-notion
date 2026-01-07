from datetime import datetime, timezone
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv
import pytz
import os

# Your local time zone, replace with the appropriate one if needed
local_tz = pytz.timezone('America/Toronto')

ACTIVITY_ICONS = {
    "Barre": "https://img.icons8.com/?size=100&id=66924&format=png&color=000000",
    "Breathwork": "https://img.icons8.com/?size=100&id=9798&format=png&color=000000",
    "Cardio": "https://img.icons8.com/?size=100&id=71221&format=png&color=000000",
    "Cycling": "https://img.icons8.com/?size=100&id=47443&format=png&color=000000",
    "Hiking": "https://img.icons8.com/?size=100&id=9844&format=png&color=000000",
    "Indoor Cardio": "https://img.icons8.com/?size=100&id=62779&format=png&color=000000",
    "Indoor Cycling": "https://img.icons8.com/?size=100&id=47443&format=png&color=000000",
    "Indoor Rowing": "https://img.icons8.com/?size=100&id=71098&format=png&color=000000",
    "Pilates": "https://img.icons8.com/?size=100&id=9774&format=png&color=000000",
    "Meditation": "https://img.icons8.com/?size=100&id=9798&format=png&color=000000",
    "Rowing": "https://img.icons8.com/?size=100&id=71491&format=png&color=000000",
    "Running": "https://img.icons8.com/?size=100&id=k1l1XFkME39t&format=png&color=000000",
    "Strength Training": "https://img.icons8.com/?size=100&id=107640&format=png&color=000000",
    "Stretching": "https://img.icons8.com/?size=100&id=djfOcRn1m_kh&format=png&color=000000",
    "Swimming": "https://img.icons8.com/?size=100&id=9777&format=png&color=000000",
    "Treadmill Running": "https://img.icons8.com/?size=100&id=9794&format=png&color=000000",
    "Walking": "https://img.icons8.com/?size=100&id=9807&format=png&color=000000",
    "Yoga": "https://img.icons8.com/?size=100&id=9783&format=png&color=000000",
    # Add more mappings as needed
}
TYPE_TRANSLATION = {
    "Running": "跑步",
    "Cycling": "骑行",
    "Walking": "徒步",
    "Swimming": "游泳",
    "Strength": "力量训练",
    "Cardio": "有氧运动",
    "Yoga": "瑜伽",
    "Pilates": "普拉提",
    "Breathwork": "呼吸练习",
    "Hiking": "登山",
    "Indoor Cardio": "室内有氧",
    "Indoor Cycling": "室内骑行",
    "Indoor Rowing": "室内划船",
    "Rowing": "划船",
    "Stretching": "拉伸",
    "Meditation": "冥想",
    "Treadmill Running": "跑步机",
    "Elliptical": "椭圆机",
    "Floor Climbing": "爬楼梯",
    "Unknown": "未知"
}

def translate_type(english_type):
    return TYPE_TRANSLATION.get(english_type, english_type)
    
def get_all_activities(garmin, limit=1000):
    return garmin.get_activities(0, limit)

def format_activity_type(activity_type, activity_name=""):
    # First format the activity type as before
    formatted_type = activity_type.replace('_', ' ').title() if activity_type else "Unknown"

    # Initialize subtype as the same as the main type
    activity_subtype = formatted_type
    activity_type = formatted_type

    # Map of specific subtypes to their main types
    activity_mapping = {
        "Barre": "Strength",
        "Indoor Cardio": "Cardio",
        "Indoor Cycling": "Cycling",
        "Indoor Rowing": "Rowing",
        "Speed Walking": "Walking",
        "Strength Training": "Strength",
        "Treadmill Running": "Running"
    }

    # Special replacement for Rowing V2
    if formatted_type == "Rowing V2":
        activity_type = "Rowing"

    # Special case for Yoga and Pilates
    elif formatted_type in ["Yoga", "Pilates"]:
        activity_type = "Yoga/Pilates"
        activity_subtype = formatted_type

    # If the formatted type is in our mapping, update both main type and subtype
    if formatted_type in activity_mapping:
        activity_type = activity_mapping[formatted_type]
        activity_subtype = formatted_type

    # Special cases for activity names
    if activity_name and "meditation" in activity_name.lower():
        return "Meditation", "Meditation"
    if activity_name and "barre" in activity_name.lower():
        return "Strength", "Barre"
    if activity_name and "stretch" in activity_name.lower():
        return "Stretching", "Stretching"
    
    return activity_type, activity_subtype

def format_entertainment(activity_name):
    return activity_name.replace('ENTERTAINMENT', 'Netflix')

def format_training_message(message):
    messages = {
        'NO_': 'No Benefit',
        'MINOR_': 'Some Benefit',
        'RECOVERY_': 'Recovery',
        'MAINTAINING_': 'Maintaining',
        'IMPROVING_': 'Impacting',
        'IMPACTING_': 'Impacting',
        'HIGHLY_': 'Highly Impacting',
        'OVERREACHING_': 'Overreaching'
    }
    for key, value in messages.items():
        if message.startswith(key):
            return value
    return message

def format_training_effect(trainingEffect_label):
    return trainingEffect_label.replace('_', ' ').title()

def format_pace(average_speed):
    if average_speed > 0:
        pace_min_km = 1000 / (average_speed * 60)  # Convert to min/km
        minutes = int(pace_min_km)
        seconds = int((pace_min_km - minutes) * 60)
        return f"{minutes}:{seconds:02d} min/km"
    else:
        return ""
    
def activity_exists(client, database_id, activity_date, activity_type, activity_name):
    if isinstance(activity_type, tuple):
        main_type, _ = activity_type
    else:
        main_type = activity_type[0] if isinstance(activity_type, (list, tuple)) else activity_type
    
    lookup_type = "Stretching" if "stretch" in activity_name.lower() else main_type
    
    # [修复] 这里的 property 必须是 "日期"、"运动类型"、"运动名称"
    query = client.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "日期", "date": {"equals": activity_date.split('T')[0]}}, 
                {"property": "运动类型", "select": {"equals": translate_type(lookup_type)}},
                {"property": "运动名称", "title": {"equals": activity_name}}
            ]
        }
    )
    results = query['results']
    return results[0] if results else None

def activity_needs_update(existing_activity, new_activity):
    existing_props = existing_activity['properties']
    
    activity_name = new_activity.get('activityName', '').lower()
    activity_type, activity_subtype = format_activity_type(
        new_activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )
    
    # Check if 'Subactivity Type' property exists (Check using Chinese Key)
    # [修改] 这里检查中文属性 "子类型"
    has_subactivity = (
        '子类型' in existing_props and 
        existing_props['子类型'] is not None and
        existing_props['子类型'].get('select') is not None
    )
    
    # [修改] 所有的对比逻辑都换成中文属性名
    return (
        existing_props['距离 (km)']['number'] != round(new_activity.get('distance', 0) / 1000, 2) or
        existing_props['时长 (min)']['number'] != round(new_activity.get('duration', 0) / 60, 2) or
        existing_props['卡路里']['number'] != round(new_activity.get('calories', 0)) or
        existing_props['平均配速']['rich_text'][0]['text']['content'] != format_pace(new_activity.get('averageSpeed', 0)) or
        existing_props['平均功率']['number'] != round(new_activity.get('avgPower', 0), 1) or
        existing_props['最大功率']['number'] != round(new_activity.get('maxPower', 0), 1) or
        existing_props['训练效果']['select']['name'] != format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown')) or
        existing_props['有氧 TE']['number'] != round(new_activity.get('aerobicTrainingEffect', 0), 1) or
        existing_props['有氧效果']['select']['name'] != format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown')) or
        existing_props['无氧 TE']['number'] != round(new_activity.get('anaerobicTrainingEffect', 0), 1) or
        existing_props['无氧效果']['select']['name'] != format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown')) or
        existing_props['PR']['checkbox'] != new_activity.get('pr', False) or
        existing_props['收藏']['checkbox'] != new_activity.get('favorite', False) or
        existing_props['运动类型']['select']['name'] != translate_type(activity_type) or
        (has_subactivity and existing_props['子类型']['select']['name'] != translate_type(activity_subtype)) or
        (not has_subactivity)
    )

def create_activity(client, database_id, activity):
    # Create a new activity in the Notion database
    activity_date = activity.get('startTimeGMT')
    activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
    activity_type, activity_subtype = format_activity_type(
        activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )
    
    # Get icon for the activity type (Note: Logic uses English type to find icon, which is correct)
    icon_url = ACTIVITY_ICONS.get(activity_subtype if activity_subtype != activity_type else activity_type)
    
    # [修改] 属性名全部汉化，并调用 translate_type 把内容也汉化
    properties = {
        "日期": {"date": {"start": activity_date}},
        "运动类型": {"select": {"name": translate_type(activity_type)}},
        "子类型": {"select": {"name": translate_type(activity_subtype)}},
        "运动名称": {"title": [{"text": {"content": activity_name}}]},
        "距离 (km)": {"number": round(activity.get('distance', 0) / 1000, 2)},
        "时长 (min)": {"number": round(activity.get('duration', 0) / 60, 2)},
        "卡路里": {"number": round(activity.get('calories', 0))},
        "平均配速": {"rich_text": [{"text": {"content": format_pace(activity.get('averageSpeed', 0))}}]},
        "平均功率": {"number": round(activity.get('avgPower', 0), 1)},
        "最大功率": {"number": round(activity.get('maxPower', 0), 1)},
        "训练效果": {"select": {"name": format_training_effect(activity.get('trainingEffectLabel', 'Unknown'))}},
        "有氧 TE": {"number": round(activity.get('aerobicTrainingEffect', 0), 1)},
        "有氧效果": {"select": {"name": format_training_message(activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
        "无氧 TE": {"number": round(activity.get('anaerobicTrainingEffect', 0), 1)},
        "无氧效果": {"select": {"name": format_training_message(activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
        "PR": {"checkbox": activity.get('pr', False)},
        "收藏": {"checkbox": activity.get('favorite', False)}
    }
    
    page = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    
    if icon_url:
        page["icon"] = {"type": "external", "external": {"url": icon_url}}
    
    client.pages.create(**page)
    
def update_activity(client, existing_activity, new_activity):
    # Update an existing activity in the Notion database with new data
    activity_name = new_activity.get('activityName', 'Unnamed Activity')
    activity_type, activity_subtype = format_activity_type(
        new_activity.get('activityType', {}).get('typeKey', 'Unknown'),
        activity_name
    )
    
    icon_url = ACTIVITY_ICONS.get(activity_subtype if activity_subtype != activity_type else activity_type)
    
    # [修改] 属性名汉化
    properties = {
        "运动类型": {"select": {"name": translate_type(activity_type)}},
        "子类型": {"select": {"name": translate_type(activity_subtype)}},
        "距离 (km)": {"number": round(new_activity.get('distance', 0) / 1000, 2)},
        "时长 (min)": {"number": round(new_activity.get('duration', 0) / 60, 2)},
        "卡路里": {"number": round(new_activity.get('calories', 0))},
        "平均配速": {"rich_text": [{"text": {"content": format_pace(new_activity.get('averageSpeed', 0))}}]},
        "平均功率": {"number": round(new_activity.get('avgPower', 0), 1)},
        "最大功率": {"number": round(new_activity.get('maxPower', 0), 1)},
        "训练效果": {"select": {"name": format_training_effect(new_activity.get('trainingEffectLabel', 'Unknown'))}},
        "有氧 TE": {"number": round(new_activity.get('aerobicTrainingEffect', 0), 1)},
        "有氧效果": {"select": {"name": format_training_message(new_activity.get('aerobicTrainingEffectMessage', 'Unknown'))}},
        "无氧 TE": {"number": round(new_activity.get('anaerobicTrainingEffect', 0), 1)},
        "无氧效果": {"select": {"name": format_training_message(new_activity.get('anaerobicTrainingEffectMessage', 'Unknown'))}},
        "PR": {"checkbox": new_activity.get('pr', False)},
        "收藏": {"checkbox": new_activity.get('favorite', False)}
    }
    
    update = {
        "page_id": existing_activity['id'],
        "properties": properties,
    }
    
    if icon_url:
        update["icon"] = {"type": "external", "external": {"url": icon_url}}
        
    client.pages.update(**update)

def main():
    load_dotenv()

    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DB_ID")

    # Initialize Garmin client and login
    #garmin = Garmin(garmin_email, garmin_password)
    garmin = Garmin(garmin_email, garmin_password, is_cn=True)
    garmin.login()
    client = Client(auth=notion_token)
    
    # Get all activities
    activities = get_all_activities(garmin)

    # Process all activities
    for activity in activities:
        activity_date = activity.get('startTimeGMT')
        activity_name = format_entertainment(activity.get('activityName', 'Unnamed Activity'))
        activity_type, activity_subtype = format_activity_type(
            activity.get('activityType', {}).get('typeKey', 'Unknown'),
            activity_name
        )
        
        # Check if activity already exists in Notion
        existing_activity = activity_exists(client, database_id, activity_date, activity_type, activity_name)
        
        if existing_activity:
            if activity_needs_update(existing_activity, activity):
                update_activity(client, existing_activity, activity)
                # print(f"Updated: {activity_type} - {activity_name}")
        else:
            create_activity(client, database_id, activity)
            # print(f"Created: {activity_type} - {activity_name}")

if __name__ == '__main__':
    main()
