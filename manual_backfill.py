import os
import time
from datetime import date, timedelta, datetime
from garminconnect import Garmin
from notion_client import Client

# 引入你现有脚本中的函数（复用你的汉化逻辑）
# 确保这几个 .py 文件都在同一个目录下
try:
    import garmin_activities as ga
    import daily_steps as ds
    import sleep_data as sd
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保 garmin_activities.py, daily_steps.py, sleep_data.py 都在当前目录下")
    exit(1)

# ================= 配置区域 =================
# 回填过去多少天的数据？(建议先试 30 天，以免 Garmin 封 IP)
DAYS_TO_BACKFILL = 30 

# 回填多少条运动记录？(0 表示从最新开始，50 表示最近 50 条)
ACTIVITY_LIMIT = 50 
# ===========================================

def main():
    print("--- 🚀 开始执行历史数据回填脚本 ---")

    # 1. 初始化 (读取环境变量)
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    notion_token = os.getenv("NOTION_TOKEN")
    
    # 获取数据库 ID (注意这里用的是 CN 版的 ID)
    db_activities = os.getenv("NOTION_CN_DB_ID") or os.getenv("NOTION_DB_ID")
    db_steps = os.getenv("NOTION_CN_STEPS_DB_ID") or os.getenv("NOTION_STEPS_DB_ID")
    db_sleep = os.getenv("NOTION_CN_SLEEP_DB_ID") or os.getenv("NOTION_SLEEP_DB_ID")

    if not all([email, password, notion_token]):
        print("❌ 错误：环境变量缺失，请检查 Secrets 设置")
        return

    # 2. 登录 Garmin (中国区)
    print("🔄 正在登录 Garmin (CN)...")
    try:
        garmin = Garmin(email, password, is_cn=True) # 强制中国区
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

    # ================= 阶段一：回填运动记录 (Activities) =================
    print(f"\n🏃 [1/3] 开始回填最近 {ACTIVITY_LIMIT} 条运动记录...")
    try:
        # 获取最近 X 条记录
        activities = garmin.get_activities(0, ACTIVITY_LIMIT)
        print(f"   -> 成功获取到 {len(activities)} 条原始数据")

        for activity in activities:
            # 复用 garmin_activities.py 里的逻辑
            activity_date = activity.get('startTimeGMT')
            activity_name = ga.format_entertainment(activity.get('activityName', 'Unnamed Activity'))
            activity_type, _ = ga.format_activity_type(
                activity.get('activityType', {}).get('typeKey', 'Unknown'), activity_name
            )

            # 检查是否存在
            existing = ga.activity_exists(notion, db_activities, activity_date, activity_type, activity_name)
            if not existing:
                ga.create_activity(notion, db_activities, activity)
                print(f"   [+] 新增: {activity_date[:10]} - {activity_name}")
            else:
                print(f"   [.] 跳过: {activity_date[:10]} - {activity_name} (已存在)")
            
            # 这里的 create_activity 已经包含了你的汉化翻译逻辑
            
    except Exception as e:
        print(f"⚠️ 回填运动记录时出错: {e}")


    # ================= 阶段二 & 三：按天循环回填步数和睡眠 =================
    print(f"\n📅 [2/3 & 3/3] 开始按天回填步数与睡眠 (过去 {DAYS_TO_BACKFILL} 天)...")
    
    # 生成日期列表 (从旧到新)
    today = date.today()
    start_date = today - timedelta(days=DAYS_TO_BACKFILL)
    
    # 循环遍历每一天
    current_date = start_date
    while current_date < today:
        day_str = current_date.isoformat()
        print(f"\n🔎 处理日期: {day_str}")

        # --- A. 补全步数 ---
        try:
            # 注意：get_daily_steps 返回的是列表
            steps_data = garmin.get_daily_steps(day_str, day_str)
            if steps_data:
                step_item = steps_data[0]
                # 检查 Notion 是否已存在
                if not ds.daily_steps_exist(notion, db_steps, day_str):
                    ds.create_daily_steps(notion, db_steps, step_item)
                    print(f"   👣 步数已补全: {step_item.get('totalSteps')} 步")
                else:
                    print(f"   👣 步数已存在，跳过")
            else:
                print(f"   👣 无步数数据")
        except Exception as e:
            print(f"   ⚠️ 步数同步出错: {e}")

        # --- B. 补全睡眠 ---
        try:
            sleep_data = garmin.get_sleep_data(day_str)
            daily_sleep = sleep_data.get('dailySleepDTO', {})
            
            if daily_sleep and daily_sleep.get('sleepTimeSeconds', 0) > 0:
                # 检查是否存在 (注意 sleep_data_exists 需要我们传 notion client)
                if not sd.sleep_data_exists(notion, db_sleep, day_str):
                    sd.create_sleep_data(notion, db_sleep, sleep_data)
                    print(f"   🛌 睡眠已补全")
                else:
                    print(f"   🛌 睡眠已存在，跳过")
            else:
                print(f"   🛌 无睡眠数据 (或时长为0)")
        except Exception as e:
            print(f"   ⚠️ 睡眠同步出错: {e}")

        # 重要：防止请求过快被 Garmin 封 IP，每处理一天暂停 1 秒
        time.sleep(1) 
        current_date += timedelta(days=1)

    print("\n✅ --- 所有历史数据回填完成 ---")

if __name__ == "__main__":
    main()
