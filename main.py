# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv

# โหลด API Key จากไฟล์ .env (ความปลอดภัยระดับ Server)
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ตั้งค่า AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# เปิด CORS (อนุญาตให้ Figma ยิงเข้ามาได้)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ของจริงควรระบุ domain แต่ figma plugin ใช้ * ไปก่อนได้
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = "General", 
    context: str = "App"
):
    try:
        # 1. อ่านไฟล์รูปที่ส่งมา
        contents = await file.read()
        
        # 2. เตรียม Prompt
        prompt = f"""
        Act as a UX Expert. Analyze this image for {country} culture in {context} context.
        Return HTML output with:
        - Score (0-100)
        - Critical Issues (Red flags)
        - Suggestions
        """
        
        # 3. ส่งให้ Gemini (Server เป็นคนยิง AI เอง)
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        # 4. ส่งคำตอบกลับไปให้ Figma
        return {"result": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# วิธีรัน (ในเครื่อง): uvicorn main:app --reload