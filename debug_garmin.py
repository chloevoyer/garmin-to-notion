import os
from garminconnect import Garmin
from datetime import date, timedelta

# 获取环境变量
email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

def main():
    print("--- 开始 Garmin 连通性测试 ---")
    
    if not email or not password:
        print("❌ 错误：未找到环境变量 GARMIN_EMAIL 或 GARMIN_PASSWORD")
        return

    print(f"🔄 正在尝试登录 Garmin (账号: {email[:3]}***)...")
    try:
        # 如果你是中国区账号，保留 is_cn=True；如果不是，请去掉它
        # 你的原代码里似乎没加 is_cn=True，这里先保持原样，如果报错再加
        garmin = Garmin(email, password) 
        garmin.login()
        print("✅ 登录成功！")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return

    # 设置日期
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    print(f"\n📅 测试日期: {today} (今天)")
    
    # 1. 测试睡眠数据 (Sleep)
    print("\n----- 1. 🛌 睡眠数据检测 -----")
    try:
        sleep_data = garmin.get_sleep_data(today)
        daily_sleep = sleep_data.get('dailySleepDTO', {})
        sleep_seconds = daily_sleep.get('sleepTimeSeconds', 0)
        
        if sleep_seconds > 0:
            print(f"✅ 获取成功！睡眠时长: {sleep_seconds / 3600:.2f} 小时")
        else:
            print(f"⚠️ 警告：获取到的睡眠时长为 0。")
            print("   (原因可能是：手表还没同步给手机App，或者Garmin服务器还没处理完)")
    except Exception as e:
        print(f"❌ 获取睡眠数据报错: {e}")

    # 2. 测试步数 (Steps - 昨天)
    # 因为原脚本只同步昨天的步数，我们重点测昨天
    print(f"\n----- 2. 👣 昨日步数检测 ({yesterday}) -----")
    try:
        steps_data = garmin.get_daily_steps(yesterday, yesterday)
        if steps_data:
            steps = steps_data[0]['totalSteps']
            print(f"✅ 获取成功！昨日步数: {steps}")
        else:
            print("⚠️ 警告：昨日步数数据为空。")
    except Exception as e:
        print(f"❌ 获取步数报错: {e}")

    print("\n--- 测试结束 ---")

if __name__ == "__main__":
    main()
