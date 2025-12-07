from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

# โหลด Environment Variables
load_dotenv()

# ตรวจสอบ API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ ERROR: No API Key found in environment variables!")

# ตั้งค่า AI
genai.configure(api_key=GOOGLE_API_KEY)

# ตั้งค่า FastAPI
app = FastAPI()

# เปิดให้ Figma เข้าถึงได้ (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint เช็กสถานะ Server
@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

# Endpoint เช็กรายชื่อ Model (เผื่อไว้ debug)
@app.get("/models")
def list_available_models():
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        return {"available_models": available}
    except Exception as e:
        return {"error": str(e)}

# Endpoint หลักสำหรับวิเคราะห์ UI
@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ใช้ Model ตัวล่าสุดที่เช็กมา
    target_model_name = 'gemini-2.5-flash'
    
    # ถ้า 2.5 ยังมีปัญหา ให้ลองเปลี่ยนกลับเป็น 'gemini-1.5-flash-001'
    # target_model_name = 'gemini-1.5-flash-001'

    print(f"📥 Receiving file... Model: {target_model_name}")
    
    try:
        # สร้าง Model Object
        model = genai.GenerativeModel(target_model_name)

        # อ่านไฟล์รูป
        contents = await file.read()
        
        # PROMPT: สั่งให้ตอบเป็น HTML
        prompt = f"""
        Act as a Strict UX & Cultural Audit AI. 
        Analyze this UI screenshot for target audience: {country}.
        Context: {context}.

        Your goal: Identify cultural mistakes and suggest fix immediately.
        
        RULES:
        1. Be extremely concise. No fluffy introduction.
        2. Use Thai language for output (ตอบเป็นภาษาไทย).
        3. Output MUST be raw HTML format (without ```html wrappers).
        4. Use specific CSS classes: <div class='score'>, <ul class='issues'>, <li class='fix'>.

        STRUCTURE THE RESPONSE EXACTLY LIKE THIS:
        
        <div class="score-container">
            <div class="score-label">Cultural Fit Score</div>
            <div class="score-value">[Score]/100</div>
        </div>

        <div class="section">
            <h3>🚨 สิ่งที่ต้องรีบแก้ (Critical)</h3>
            <ul class="issues">
                <li>
                    <strong>[Point 1]</strong>: [Why it is bad in {country}]
                    <div class="fix">💡 แก้โดย: [Specific Action]</div>
                </li>
                <li>
                    <strong>[Point 2]</strong>: [Why it is bad]
                    <div class="fix">💡 แก้โดย: [Specific Action]</div>
                </li>
            </ul>
        </div>

        <div class="section">
            <h3>✅ สิ่งที่ทำดีแล้ว (Keep it)</h3>
            <ul class="good">
                <li>[Point 1]</li>
                <li>[Point 2]</li>
            </ul>
        </div>
        """
        
        print("🤖 Sending to Gemini...")
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        # ล้าง Code block ที่ AI อาจเผลอใส่มา
        clean_text = response.text.replace("```html", "").replace("```", "")
        
        print("✅ Success!")
        return {"result": clean_text}

    except Exception as e:
        print("❌ Error:")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")