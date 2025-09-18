import MetaTrader5 as mt
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

# ดึงค่าการตั้งค่าจากไฟล์ .env
folder_dir = os.getenv('DIR')
login = int(os.getenv('LOGIN'))
pwd = os.getenv('PWD')
server = os.getenv('SERVER')
symbol = os.getenv('SYMBOL')
path = "C:/Program Files/" + folder_dir +"/terminal64.exe"

def save_historical_data_to_csv(symbol, timeframe, timeframe_name, num_candles=1000):
    """
    ฟังก์ชันดึงข้อมูลแท่งเทียนย้อนหลังและบันทึกเป็น CSV
    
    Parameters:
    - symbol: คู่สกุลเงิน (เช่น EURUSD)
    - timeframe: กรอบเวลา (M1, M5, H1, etc.)
    - timeframe_name: ชื่อ timeframe สำหรับใช้ในชื่อไฟล์
    - num_candles: จำนวนแท่งเทียนที่ต้องการดึง (default=1000)
    """
    
    # ดึงข้อมูลแท่งเทียนย้อนหลัง
    rates = mt.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    
    if rates is None:
        print(f"❌ ไม่สามารถดึงข้อมูล {timeframe_name} ได้, error code = {mt.last_error()}")
        return False
    
    # แปลงเป็น DataFrame
    df = pd.DataFrame(rates)
    
    # แปลง timestamp เป็นวันที่และเวลาที่อ่านได้
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # เพิ่มคอลัมน์เสริมที่มีประโยชน์
    df['symbol'] = symbol
    df['timeframe'] = timeframe_name
    
    # คำนวณข้อมูลเพิ่มเติม
    df['body'] = abs(df['close'] - df['open'])  # ขนาดตัวเทียน
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)  # ไส้เทียนบน
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']  # ไส้เทียนล่าง
    df['is_bullish'] = df['close'] > df['open']  # เป็นแท่งเขียวหรือไม่
    df['change_percent'] = ((df['close'] - df['open']) / df['open']) * 100  # เปอร์เซ็นต์การเปลี่ยนแปลง
    
    # จัดเรียงคอลัมน์ใหม่
    columns_order = ['time', 'symbol', 'timeframe', 'open', 'high', 'low', 'close', 
                     'tick_volume', 'spread', 'real_volume', 'body', 'upper_shadow', 
                     'lower_shadow', 'is_bullish', 'change_percent']
    df = df[columns_order]
    
    # สร้างชื่อไฟล์พร้อม timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timeframe_name}_1000candles_{timestamp}.csv"
    
    # บันทึกเป็น CSV
    df.to_csv(filename, index=False, encoding='utf-8-sig')  # utf-8-sig เพื่อรองรับภาษาไทย
    
    print(f"\n✅ บันทึกข้อมูล {timeframe_name} เรียบร้อยแล้ว: {filename}")
    print(f"📊 จำนวนแท่งเทียน: {len(df)} แท่ง")
    print(f"📅 ช่วงเวลา: {df['time'].min()} ถึง {df['time'].max()}")
    print(f"📈 ข้อมูลสรุป {timeframe_name}:")
    print(f"  - ราคาต่ำสุด: {df['low'].min():.5f}")
    print(f"  - ราคาสูงสุด: {df['high'].max():.5f}")
    print(f"  - แท่งเขียว: {df['is_bullish'].sum()} แท่ง")
    print(f"  - แท่งแดง: {(~df['is_bullish']).sum()} แท่ง")
    
    return df

# โปรแกรมหลัก
if __name__ == '__main__':
    # เชื่อมต่อกับ MetaTrader5
    if not mt.initialize(path=path, login=login, server=server, password=pwd):
        print("Initialize() failed, error code =", mt.last_error())
        quit()
    
    print("✅ เชื่อมต่อ MetaTrader 5 สำเร็จ!")
    print(f"📊 คู่สกุลเงิน: {symbol}")
    print("\n" + "="*60)
    print("📥 กำลังดึงข้อมูล 5 Timeframes (M1, M5, M15, H1, H4)")
    print("📊 จำนวน 1000 แท่งเทียนต่อ Timeframe")
    print("="*60)
    
    # กำหนด timeframes ที่ต้องการดึง
    timeframes_to_save = [
        (mt.TIMEFRAME_M1, "M1"),
        (mt.TIMEFRAME_M5, "M5"),
        (mt.TIMEFRAME_M15, "M15"),
        (mt.TIMEFRAME_H1, "H1"),
        (mt.TIMEFRAME_H4, "H4")
    ]
    
    # ตัวนับไฟล์ที่สำเร็จ
    successful_files = []
    failed_files = []
    
    # ดึงข้อมูลแต่ละ timeframe
    for i, (tf, tf_name) in enumerate(timeframes_to_save, 1):
        print(f"\n{'='*60}")
        print(f"📍 [{i}/5] กำลังดึงข้อมูล {tf_name}...")
        print(f"{'='*60}")
        
        result = save_historical_data_to_csv(symbol, tf, tf_name, 1000)
        
        if result is not False:
            successful_files.append(tf_name)
        else:
            failed_files.append(tf_name)
    
    # สรุปผลการทำงาน
    print("\n" + "="*60)
    print("📊 สรุปผลการดึงข้อมูล")
    print("="*60)
    print(f"✅ สำเร็จ: {len(successful_files)} ไฟล์")
    if successful_files:
        print(f"   - Timeframes: {', '.join(successful_files)}")
    
    if failed_files:
        print(f"❌ ล้มเหลว: {len(failed_files)} ไฟล์")
        print(f"   - Timeframes: {', '.join(failed_files)}")
    
    print(f"\n📁 ไฟล์ CSV ทั้งหมดถูกบันทึกในโฟลเดอร์: {os.getcwd()}")
    
    # ปิดการเชื่อมต่อ
    mt.shutdown()
    print("\n✅ ปิดการเชื่อมต่อ MetaTrader 5 เรียบร้อย")
    print("="*60)