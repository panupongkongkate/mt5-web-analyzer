# MT5 Web Analyzer

📊 **Web Application สำหรับดึงข้อมูลและวิเคราะห์ราคาจาก MetaTrader 5 ด้วย Claude AI**

## 📋 ความต้องการของระบบ

- **Windows OS** (MetaTrader 5 ทำงานบน Windows เท่านั้น)
- **Python 3.8** หรือสูงกว่า
- **MetaTrader 5 Terminal** ติดตั้งในเครื่อง
- **Claude Code SDK** (ถ้าต้องการใช้ AI วิเคราะห์)

## 🚀 การติดตั้ง

### 1. Clone Repository

```bash
git clone https://github.com/panupongkongkate/mt5-web-analyzer.git
cd mt5-web-analyzer
```

### 2. สร้าง Virtual Environment

```bash
# สร้าง virtual environment
python -m venv venv

# เปิดใช้งาน virtual environment
# Windows:
venv\Scripts\activate
# หรือ
.\venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate
```

### 3. ติดตั้ง Dependencies

```bash
cd web
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

```bash
# คัดลอกไฟล์ตัวอย่าง
cp .env.example .env

# แก้ไขไฟล์ .env ด้วย text editor
notepad .env
```

แก้ไขค่าใน `.env` ให้ตรงกับบัญชี MT5 ของคุณ:

```env
# MT5 Configuration
DIR="MetaTrader 5"          # ชื่อโฟลเดอร์ MT5 ใน Program Files
LOGIN=5110866                # เลขบัญชี MT5
PWD="your_password"          # รหัสผ่าน MT5
SERVER="EightcapGlobal-Live" # ชื่อ Server
SYMBOL="XAUUSD"              # Symbol เริ่มต้น

# ตัวเลือกการเก็บไฟล์
KEEP_CSV_FILES=false         # true = เก็บไฟล์ CSV, false = ลบหลังวิเคราะห์
```

## 💻 การใช้งาน

### 1. เปิด MetaTrader 5

- เปิดโปรแกรม MetaTrader 5 และ Login
- ตรวจสอบว่า Symbol ที่ต้องการดูอยู่ใน Market Watch

### 2. รัน Web Application

```bash
# อยู่ในโฟลเดอร์ web
cd web

# รันโปรแกรม
python app.py
```

### 3. เปิด Browser

เข้าไปที่: `http://localhost:5000`

### 4. วิธีใช้งาน

1. **เลือก Symbol** - เลือกคู่เงินที่ต้องการวิเคราะห์ (เช่น XAUUSD, EURUSD)
2. **เลือก Timeframe** - เลือกได้หลายอัน:
   - M1 (1 นาที)
   - M5 (5 นาที)
   - M15 (15 นาที)
   - M30 (30 นาที)
   - H1 (1 ชั่วโมง)
   - H4 (4 ชั่วโมง)
   - D1 (1 วัน)
3. **คลิก Analyze** - ระบบจะ:
   - ดึงข้อมูลแท่งเทียนจาก MT5
   - วิเคราะห์ด้วย Claude AI
   - แสดงผลการวิเคราะห์

## 📁 โครงสร้างโปรเจค

```
mt5-web-analyzer/
├── web/
│   ├── app.py              # Flask application หลัก
│   ├── templates/
│   │   └── index.html      # หน้า Web UI
│   ├── downloads/          # เก็บไฟล์ CSV (สร้างอัตโนมัติ)
│   ├── .env                # ไฟล์ config (ไม่ push ขึ้น git)
│   ├── .env.example        # ตัวอย่าง config
│   └── requirements.txt    # Python packages
├── .gitignore
└── README.md
```

## 🔧 การแก้ไขปัญหาที่พบบ่อย

### ❌ Error: "ไม่สามารถเชื่อมต่อ MT5"

1. ตรวจสอบว่า MT5 เปิดอยู่
2. ตรวจสอบข้อมูลใน `.env` ถูกต้อง
3. ลอง Login ใหม่ใน MT5

### ❌ Error: "Missing required environment variables"

1. ตรวจสอบว่ามีไฟล์ `.env`
2. ตรวจสอบว่ากรอกข้อมูลครบทุกช่อง
3. ไม่ใส่ comment หลังค่า config

### ❌ Error: "ไม่สามารถเชื่อมต่อกับ Claude Code SDK"

1. ตรวจสอบการติดตั้ง Claude Code SDK
2. ตรวจสอบ API key (ถ้ามี)

## 📊 ข้อมูลที่ได้จากการวิเคราะห์

- **แนวโน้มราคา** - Bullish/Bearish/Sideways
- **Support & Resistance** - ระดับราคาสำคัญ
- **Pattern** - รูปแบบแท่งเทียน
- **Momentum** - แรงซื้อขาย
- **คำแนะนำการเทรด** - จุด Entry/Exit

## 🛡️ ความปลอดภัย

- **อย่า commit ไฟล์ `.env`** ที่มีรหัสผ่านจริง
- ใช้ `.env.example` เป็นตัวอย่าง
- ไฟล์ `.env` อยู่ใน `.gitignore` แล้ว

## 📝 License

MIT License
