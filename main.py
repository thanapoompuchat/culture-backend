from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

# 1. โหลด Environment Variables
load_dotenv()

# 2. ตรวจสอบ API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ ERROR: No API Key found in environment variables!")

# 3. ตั้งค่า AI
genai.configure(api_key=GOOGLE_API_KEY)

# 4. ตั้งค่า App
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

# --- Endpoint: Analyze (ใช้ Gemini 2.0 Flash ตัวจริง) ---
@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ✅ เปลี่ยนมาใช้ตัวนี้ครับ (มีในลิสต์ของคุณแน่นอน)
    target_model_name = 'gemini-2.0-flash'
    
    print(f"📥 [Analyze] Receiving file... Model: {target_model_name}")
    
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        # Prompt สำหรับ Analyze
        prompt = f"""
        Act as a Strict UX & Cultural Audit AI. 
        Analyze this UI screenshot for target audience: {country}.
        Context: {context}.

        RULES:
        1. Answer in Thai (ภาษาไทย).
        2. Output RAW HTML only.
        3. Structure:
           <div class="score-container"><div class="score-label">คะแนนความเหมาะสม</div><div class="score-value">[Score]/100</div></div>
           <div class="section"><h3>🚨 สิ่งที่ต้องปรับปรุง (Critical)</h3><ul class="issues"><li><strong>[จุดที่ผิด]</strong>: [ทำไมถึงผิด]<div class="fix">💡 แก้ไข: [วิธีแก้]</div></li></ul></div>
           <div class="section"><h3>✅ สิ่งที่ทำได้ดี (Good)</h3><ul class="good"><li>[จุดที่ดี]</li></ul></div>
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        # ล้าง Code block
        clean_text = response.text.replace("```html", "").replace("```", "")
        print("✅ Analyze Success!")
        return {"result": clean_text}

    except Exception as e:
        print("❌ Analyze Error:")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

# --- Endpoint: Fix (ใช้ Gemini 2.0 Flash ตัวจริง) ---
@app.post("/fix")
async def fix_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ✅ ใช้ตัวเดียวกัน
    target_model_name = 'gemini-2.0-flash'
    
    print(f"🎨 [Fix] Generating SVG Design for {country}...")

    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        prompt = f"""
        Act as a UI Designer. Redesign this UI for {country} culture.
        Context: {context}.
        
        TASK: Generate SVG Code for a mobile UI (375x812).
        REQUIREMENTS:
        1. Clean, Modern, Cultural fit colors.
        2. Output ONLY raw SVG code. NO markdown.
        3. Start with <svg ...> and end with </svg>.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        svg_code = response.text.replace("```svg", "").replace("```xml", "").replace("```", "")
        
        print("✅ Fix SVG Success!")
        return {"svg": svg_code}

    except Exception as e:
        print("❌ Fix Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")