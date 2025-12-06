# main.py (แบบ Debug)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback # เพิ่มตัวนี้มาช่วยดู Error

load_dotenv()

# --- เช็ก Key ตั้งแต่เริ่ม ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ CRITICAL ERROR: ไม่เจอ GOOGLE_API_KEY ใน Environment Variables!")

genai.configure(api_key=GOOGLE_API_KEY)
# ลองใช้ model นี้ดู (เสถียรกว่าในบางโซน)
model = genai.GenerativeModel('gemini-1.5-pro-001')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    print(f"📥 กำลังรับไฟล์... Country: {country}, Context: {context}")
    
    try:
        # 1. อ่านไฟล์
        contents = await file.read()
        print(f"✅ อ่านไฟล์สำเร็จ ขนาด: {len(contents)} bytes")

        # 2. เตรียม Prompt
        prompt = f"""
        Act as a UX Expert. Analyze this image for {country} culture in {context} context.
        Return HTML output with:
        - Score (0-100)
        - Critical Issues (Red flags)
        - Suggestions
        """
        
        # 3. ส่ง Gemini
        print("🤖 กำลังส่งให้ Gemini...")
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        print("✅ Gemini ตอบกลับมาแล้ว!")
        
        return {"result": response.text}

    except Exception as e:
        print("❌ เกิดข้อผิดพลาด (Traceback):") # <--- ต้องมีบรรทัดนี้
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")