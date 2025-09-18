"""
MT5 Web Data Downloader - Windows Version
ดึงข้อมูลจริงจาก MetaTrader 5 (ต้องใช้ Windows เท่านั้น)
"""

from flask import Flask, render_template, request, jsonify
import MetaTrader5 as mt
import pandas as pd
from datetime import datetime
import os
import subprocess
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from claude_code_sdk import query, ClaudeCodeOptions, AssistantMessage, TextBlock

# Load environment variables
load_dotenv()

app = Flask(__name__)

# อ่านค่า config สำหรับการเชื่อมต่อ MT5 จาก environment variables
# ต้องมีครบทุกค่า ไม่งั้น Error
required_env_vars = ['DIR', 'LOGIN', 'PWD', 'SERVER']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")

MT5_CONFIG = {
    'DIR': os.getenv('DIR'),
    'LOGIN': int(os.getenv('LOGIN')),
    'PWD': os.getenv('PWD'),
    'SERVER': os.getenv('SERVER')
}

def connect_mt5():
    """เชื่อมต่อกับ MetaTrader 5"""
    path = f"C:/Program Files/{MT5_CONFIG['DIR']}/terminal64.exe"
    if not mt.initialize(path=path, login=MT5_CONFIG['LOGIN'],
                         server=MT5_CONFIG['SERVER'], password=MT5_CONFIG['PWD']):
        return False, mt.last_error()
    return True, None

def get_all_symbols():
    """ดึงรายการ symbols ทั้งหมดจาก MT5"""
    symbols = mt.symbols_get()
    if symbols is None:
        return []

    symbol_list = []
    for symbol in symbols:
        if symbol.visible:  # เฉพาะ symbols ที่แสดงใน Market Watch
            symbol_list.append({
                'name': symbol.name,
                'description': symbol.description,
                'path': symbol.path
            })

    symbol_list.sort(key=lambda x: x['name'])
    return symbol_list

def save_historical_data(symbol, timeframe, timeframe_name, num_candles=None):
    """ดึงข้อมูลแท่งเทียนจริงจาก MT5"""

    # กำหนดจำนวนแท่งเทียนตาม timeframe
    if num_candles is None:
        candle_counts = {
            'M1': 500,   # 8 ชั่วโมง
            'M5': 500,   # 1.7 วัน
            'M15': 500,  # 5 วัน
            'M30': 500,  # 10 วัน
            'H1': 168,   # 1 สัปดาห์
            'H4': 180,   # 1 เดือน
            'D1': 90     # 3 เดือน
        }
        num_candles = candle_counts.get(timeframe_name, 500)

    rates = mt.copy_rates_from_pos(symbol, timeframe, 0, num_candles)

    if rates is None:
        return None, f"ไม่สามารถดึงข้อมูล {timeframe_name} ได้"

    # แปลงเป็น DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['symbol'] = symbol
    df['timeframe'] = timeframe_name

    # คำนวณข้อมูลเพิ่มเติม
    df['body'] = abs(df['close'] - df['open'])
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    df['is_bullish'] = df['close'] > df['open']
    df['change_percent'] = ((df['close'] - df['open']) / df['open']) * 100

    # จัดเรียงคอลัมน์
    columns_order = ['time', 'symbol', 'timeframe', 'open', 'high', 'low', 'close',
                     'tick_volume', 'spread', 'real_volume', 'body', 'upper_shadow',
                     'lower_shadow', 'is_bullish', 'change_percent']
    df = df[columns_order]

    # เรียงตามเวลาจากใหม่ไปเก่า (descending)
    df = df.sort_values('time', ascending=False).reset_index(drop=True)

    # สร้างชื่อไฟล์และบันทึก
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timeframe_name}_{num_candles}candles_{timestamp}.csv"
    filepath = os.path.join('downloads', filename)

    os.makedirs('downloads', exist_ok=True)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    # สร้างข้อมูลสรุป
    summary = {
        'filename': filename,
        'filepath': filepath,
        'candles_count': len(df),
        'time_range': f"{df['time'].min()} ถึง {df['time'].max()}",
        'min_price': float(df['low'].min()),
        'max_price': float(df['high'].max()),
        'bullish_candles': int(df['is_bullish'].sum()),
        'bearish_candles': int((~df['is_bullish']).sum())
    }

    return summary, None


# ==================== ROUTES ====================

@app.route('/')
def index():
    """หน้าแรก"""
    return render_template('index.html')

@app.route('/api/symbols')
def api_symbols():
    """API สำหรับดึงรายการ symbols"""
    connected, error = connect_mt5()
    if not connected:
        return jsonify({'error': f'ไม่สามารถเชื่อมต่อ MT5 ได้: {error}'}), 500

    symbols = get_all_symbols()
    mt.shutdown()

    return jsonify({'symbols': symbols})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API สำหรับดาวน์โหลดและวิเคราะห์ข้อมูลด้วย Claude Code SDK"""
    print(f"🚀 [ANALYZE] Starting analysis...")

    try:
        # รับข้อมูลจาก request
        data = request.json
        symbol = data.get('symbol')
        timeframes = data.get('timeframes', [])
        keep_files = os.getenv('KEEP_CSV_FILES', 'false').lower() == 'true'

        print(f"📊 [ANALYZE] {symbol} | Timeframes: {timeframes} | Keep: {keep_files}")

        if not symbol:
            return jsonify({'error': 'กรุณาเลือก symbol'}), 400

        if not timeframes:
            return jsonify({'error': 'กรุณาเลือก timeframe อย่างน้อย 1 รายการ'}), 400

        # เชื่อมต่อ MT5
        connected, error = connect_mt5()
        if not connected:
            print(f"❌ [ANALYZE] MT5 connection failed: {error}")
            return jsonify({'error': f'ไม่สามารถเชื่อมต่อ MT5 ได้: {error}'}), 500

        print("✅ [ANALYZE] MT5 connected")

        # Mapping timeframe สำหรับ MT5 จริง
        timeframe_map = {
            'M1': (mt.TIMEFRAME_M1, 'M1'),
            'M5': (mt.TIMEFRAME_M5, 'M5'),
            'M15': (mt.TIMEFRAME_M15, 'M15'),
            'M30': (mt.TIMEFRAME_M30, 'M30'),
            'H1': (mt.TIMEFRAME_H1, 'H1'),
            'H4': (mt.TIMEFRAME_H4, 'H4'),
            'D1': (mt.TIMEFRAME_D1, 'D1')
        }

        download_results = []
        download_errors = []
        downloaded_files = []

        # ดึงข้อมูลแต่ละ timeframe
        for tf in timeframes:
            if tf in timeframe_map:
                mt_tf, tf_name = timeframe_map[tf]
                summary, error = save_historical_data(symbol, mt_tf, tf_name)

                if summary:
                    print(f"✅ [ANALYZE] {tf}: {summary['candles_count']} candles")
                    download_results.append(summary)
                    downloaded_files.append(summary['filepath'])
                else:
                    print(f"❌ [ANALYZE] {tf} failed: {error}")
                    download_errors.append(f"{tf_name}: {error}")

        mt.shutdown()

        if not download_results:
            print(f"❌ [ANALYZE] No data downloaded")
            return jsonify({
                'success': False,
                'errors': download_errors
            }), 500

        # สร้างข้อมูลสำหรับวิเคราะห์
        analysis_data = []
        for file_path in downloaded_files:
            try:
                df = pd.read_csv(file_path)
                if len(df) > 0:
                    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'Unknown'
                    timeframe = df['timeframe'].iloc[0] if 'timeframe' in df.columns else 'Unknown'

                    file_info = {
                        'filename': Path(file_path).name,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'candles_count': len(df),
                        'date_range': f"{df['time'].min()} ถึง {df['time'].max()}" if 'time' in df.columns else 'Unknown',
                        'min_price': float(df['low'].min()) if 'low' in df.columns else 0,
                        'max_price': float(df['high'].max()) if 'high' in df.columns else 0,
                        'bullish_candles': int(df['is_bullish'].sum()) if 'is_bullish' in df.columns else 0,
                        'bearish_candles': int((~df['is_bullish']).sum()) if 'is_bullish' in df.columns else 0
                    }
                    analysis_data.append(file_info)
            except Exception as e:
                print(f"❌ [ANALYZE] Error processing file: {e}")
                continue

        print(f"🧠 [ANALYZE] Starting Claude AI analysis...")

        # รันการวิเคราะห์ด้วย Claude Code SDK
        try:
            result = run_claude_analysis(analysis_data)
            print("✅ [ANALYZE] Claude AI completed")

            # ลบไฟล์ถ้า config ระบุว่าไม่เก็บ
            if not keep_files:
                for file_path in downloaded_files:
                    try:
                        os.remove(file_path)
                    except:
                        pass
                print("🗑️ [ANALYZE] CSV files cleaned up")

            print("🎉 [ANALYZE] Analysis completed!")
            return jsonify({
                'success': True,
                'analysis_result': result,
                'files_analyzed': len(analysis_data),
                'files_info': analysis_data,
                'files_kept': keep_files,
                'download_errors': download_errors
            })

        except Exception as e:
            print(f"❌ [ANALYZE] Error: {e}")
            if not keep_files:
                for file_path in downloaded_files:
                    try:
                        os.remove(file_path)
                    except:
                        pass

            return jsonify({
                'success': False,
                'error': f'เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}'
            }), 500

    except Exception as e:
        print(f"❌ [ANALYZE] Error: {e}")
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

def run_claude_analysis(data):
    """วิเคราะห์ข้อมูล MT5 จากไฟล์ CSV ด้วย Claude Code SDK"""
    if not data:
        return "ไม่มีข้อมูลสำหรับวิเคราะห์"

    # สร้างข้อมูลสรุปสำหรับ Claude
    main_symbol = data[0]['symbol']
    summary_text = f"📊 **{main_symbol} - {len(data)} Timeframes**\n\n"

    for i, item in enumerate(data, 1):
        summary_text += f"{i}. **{item['timeframe']}** ({item['candles_count']} แท่ง): {item['date_range']}\n"
        summary_text += f"   - ราคา: {item['min_price']:.2f} - {item['max_price']:.2f} USD\n"
        summary_text += f"   - แท่งเขียว: {item['bullish_candles']} | แท่งแดง: {item['bearish_candles']}\n\n"

    # สร้าง prompt สำหรับ Claude Code SDK
    prompt = f"""ข้อมูลจริงจาก MetaTrader 5 สำหรับ {main_symbol}:

{summary_text}

โปรดวิเคราะห์ข้อมูลนี้และให้คำแนะนำ:

1. **แนวโน้มราคา**: วิเคราะห์จากจำนวนแท่งเขียว/แดงในแต่ละ timeframe
2. **ความผันผวน**: ดูจากช่วงราคาและ spread ของแต่ละ timeframe
3. **สัญญาณการเทรด**: แนะนำ entry points และ risk management

กรุณาตอบเป็นภาษาไทยและใช้ข้อมูลที่ให้มาข้างต้นในการวิเคราะห์"""

    print(f"📝 [CLAUDE] Starting analysis for {main_symbol}")

    try:
        # ตั้งค่า options แบบง่าย
        options = ClaudeCodeOptions(
            system_prompt="คุณเป็นนักวิเคราะห์การเทรดมืออาชีพ ตอบเป็นภาษาไทย",
            max_turns=1
        )

        # ฟังก์ชัน async สำหรับรัน Claude query
        async def get_analysis():
            result = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result += block.text
            return result.strip()

        # รัน async function ด้วย anyio (ที่ทำงานได้ดีกับ Flask)
        import anyio
        result = anyio.run(get_analysis)

        print(f"✅ [CLAUDE] Analysis completed: {len(result)} characters")
        return result

    except Exception as e:
        print(f"❌ [CLAUDE] Error: {type(e).__name__}: {str(e)}")

        # Handle specific SDK errors
        from claude_code_sdk import CLINotFoundError, ProcessError, CLIJSONDecodeError

        if isinstance(e, CLINotFoundError):
            return "Error: Claude CLI ไม่พบในระบบ กรุณาติดตั้ง Claude Code ก่อน"
        elif isinstance(e, ProcessError):
            return f"Error: Claude process ล้มเหลว (exit code: {e.exit_code})"
        elif isinstance(e, CLIJSONDecodeError):
            return "Error: ไม่สามารถอ่านข้อมูลจาก Claude ได้"
        else:
            return f"Error: เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)