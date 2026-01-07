import os
from garminconnect import Garmin
from datetime import date, timedelta

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

def main():
    print("--- 开始 Garmin 连通性测试 (尝试连接中国服务器) ---")
    
    if not email or not password:
        print("❌ 错误：未找到环境变量")
        return

    print(f"🔄 正在登录 (is_cn=True)...")
    try:
        # ⚠️ 关键修改：加入了 is_cn=True 参数
        garmin = Garmin(email, password, is_cn=True) 
        garmin.login()
        print("✅ 登录成功！(连接的是中国区接口)")
    except Exception as e:
        print(f"❌ 中国区登录失败: {e}")
        print("   -> 如果登录失败，说明你可能是国际区账号，请把代码里的 is_cn=True 去掉再试。")
        return

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    print(f"\n📅 测试日期: {today}")
    
    # 1. 睡眠测试 (修复了报错逻辑)
    print("\n----- 1. 🛌 睡眠数据检测 -----")
    try:
        sleep_data = garmin.get_sleep_data(today)
        daily_sleep = sleep_data.get('dailySleepDTO', {})
        
        # 打印原始数据看看到底是啥
        print(f"   (调试: Garmin返回的原始睡眠ID: {daily_sleep.get('id')})")
        
        sleep_seconds = daily_sleep.get('sleepTimeSeconds')
        
        # 修复：先判断 sleep_seconds 是否存在 (不是None)
        if sleep_seconds and sleep_seconds > 0:
            print(f"✅ 获取成功！睡眠时长: {sleep_seconds / 3600:.2f} 小时")
        else:
            print(f"⚠️ 数据为空。sleepTimeSeconds 是: {sleep_seconds}")
    except Exception as e:
        print(f"❌ 报错: {e}")

    # 2. 步数测试
    print(f"\n----- 2. 👣 昨日步数检测 ({yesterday}) -----")
    try:
        steps_data = garmin.get_daily_steps(yesterday, yesterday)
        if steps_data:
            print(f"✅ 获取成功！昨日步数: {steps_data[0]['totalSteps']}")
        else:
            print("⚠️ 警告：昨日步数数据列表为空 []")
    except Exception as e:
        print(f"❌ 报错: {e}")

if __name__ == "__main__":
    main()
