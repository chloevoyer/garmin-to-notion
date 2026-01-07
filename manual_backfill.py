import os
import time
import importlib.util
import sys
from datetime import date, timedelta, datetime
from garminconnect import Garmin
from notion_client import Client

# ================= 动态加载带横杠的文件 =================
def load_module_from_file(module_name, file_path):
    """
    Python 默认不支持 import 带横杠的文件(如 garmin-activities.py)
    这个函数用来强行加载它们。
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            print(f"❌ 找不到文件: {file_path}")
            print("请确认该文件在当前目录下。")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"❌ 加载模块 {file_path} 失败: {e}")
        return None

# 加载那三个带横杠的脚本
print("📦 正在加载依赖脚本...")
ga = load_module_from_file("garmin_activities", "garmin-activities.py")
ds = load_module_from_file("daily_steps", "daily-steps.py")
sd = load_module_from_file("sleep_data", "sleep-data.py")

# 检查是否加载成功
if not all([ga, ds, sd]):
    print("❌ 关键脚本加载失败，程序终止。")
    exit(1)
# =======================================================

# ================= 配置区域 =================
# 回填过去多少天的数据？(建议先试 30 天)
DAYS_TO_BACKFILL = 30 

# 回填多少条运动记录？
ACTIVITY_LIMIT = 50 
# ===========================================

def main():
    print("--- 🚀 开始执行历史数据回填脚本 (Fix版) ---")

    # 1. 初始化 (读取环境变量)
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    
    # 优先使用 CN 版数据库 ID
    db_activities = os.getenv("NOTION_CN_DB_ID") or os.getenv("NOTION_DB_ID")
    db_steps = os.getenv("NOTION_CN_STEPS_DB_ID") or os.getenv("NOTION_STEPS_DB_ID")
    db_sleep = os.getenv("NOTION_CN_SLEEP_DB_ID") or os.getenv("NOTION_SLEEP_DB_ID")

    if not all([email, password, notion_token]):
        print("❌ 错误：环境变量缺失，请检查 Secrets 设置")
        return

    # 2. 登录 Garmin (强制中国区)
    print("🔄 正在登录 Garmin (CN)...")
    try:
        garmin = Garmin(email, password, is_cn=True)
        garmin.login()
        print("✅ Garmin 登录成功")
    except Exception as e:
        print(f"❌ Garmin 登录失败: {e}")
        return

    # 3. 连接 Notion
    try:
        notion = Client(auth=notion_token)
        print("✅ Notion 连接成功")
    except Exception as e:
        print(f"❌ Notion 连接失败: {e}")
        return

    # ================= 阶段一：回填运动记录 =================
    print(f"\n🏃 [1/3] 开始回填最近 {ACTIVITY_LIMIT} 条运动记录...")
    try:
        activities = garmin.get_activities(0, ACTIVITY_LIMIT)
        print(f"   -> 成功获取到 {len(activities)} 条原始数据")

        for activity in activities:
            activity_date = activity.get('startTimeGMT')
            activity_name = ga.format_entertainment(activity.get('activityName', 'Unnamed Activity'))
            activity_type, _ = ga.format_activity_type(
                activity.get('activityType', {}).get('typeKey', 'Unknown'), activity_name
            )

            # 调用 garmin-activities.py 里的函数
            existing = ga.activity_exists(notion, db_activities, activity_date, activity_type, activity_name)
            if not existing:
                ga.create_activity(notion, db_activities, activity)
                print(f"   [+] 新增: {activity_date[:10]} - {activity_name}")
            else:
                print(f"   [.] 跳过: {activity_date[:10]} - {activity_name} (已存在)")
            
    except Exception as e:
        print(f"⚠️ 回填运动记录时出错: {e}")


    # ================= 阶段二 & 三：按天回填步数和睡眠 =================
    print(f"\n📅 [2/3 & 3/3] 开始按天回填步数与睡眠 (过去 {DAYS_TO_BACKFILL} 天)...")
    
    today = date.today()
    start_date = today - timedelta(days=DAYS_TO_BACKFILL)
    current_date = start_date
    
    while current_date < today:
        day_str = current_date.isoformat()
        print(f"\n🔎 处理日期: {day_str}")

        # --- 补全步数 ---
        try:
            steps_data = garmin.get_daily_steps(day_str, day_str)
            if steps_data:
                step_item = steps_data[0]
                if not ds.daily_steps_exist(notion, db_steps, day_str):
                    ds.create_daily_steps(notion, db_steps, step_item)
                    print(f"   👣 步数已补全: {step_item.get('totalSteps')}")
                else:
                    print(f"   👣 步数已存在")
            else:
                print(f"   👣 无步数数据")
        except Exception as e:
            print(f"   ⚠️ 步数错误: {e}")

        # --- 补全睡眠 ---
        try:
            sleep_data = garmin.get_sleep_data(day_str)
            daily_sleep = sleep_data.get('dailySleepDTO', {})
            
            if daily_sleep and daily_sleep.get('sleepTimeSeconds', 0) > 0:
                if not sd.sleep_data_exists(notion, db_sleep, day_str):
                    sd.create_sleep_data(notion, db_sleep, sleep_data)
                    print(f"   🛌 睡眠已补全")
                else:
                    print(f"   🛌 睡眠已存在")
            else:
                print(f"   🛌 无睡眠数据")
        except Exception as e:
            print(f"   ⚠️ 睡眠错误: {e}")

        time.sleep(1) # 防封号延迟
        current_date += timedelta(days=1)

    print("\n✅ --- 所有历史数据回填完成 ---")

if __name__ == "__main__":
    main()
