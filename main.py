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

# 5. เปิด CORS (ให้ Figma เข้าถึงได้)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoint 1: เช็กสถานะ ---
@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

# --- Endpoint 2: เช็ก Model ---
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

# --- Endpoint 3: วิเคราะห์ (Analyze) ---
@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ใช้ Model ตัวล่าสุด
    target_model_name = 'gemini-2.5-flash'
    
    print(f"📥 [Analyze] Receiving file... Model: {target_model_name}")
    
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        # PROMPT: HTML Output
        prompt = f"""
        Act as a Strict UX & Cultural Audit AI. 
        Analyze this UI screenshot for target audience: {country}.
        Context: {context}.

        Your goal: Identify cultural mistakes and suggest fix immediately.
        
        RULES:
        1. Be extremely concise.
        2. Use Thai language for output.
        3. Output MUST be raw HTML format (without ```html wrappers).
        4. Use specific CSS classes: <div class='score'>, <ul class='issues'>, <li class='fix'>.

        STRUCTURE:
        <div class="score-container">
            <div class="score-label">Cultural Fit Score</div>
            <div class="score-value">[Score]/100</div>
        </div>
        <div class="section">
            <h3>🚨 สิ่งที่ต้องรีบแก้ (Critical)</h3>
            <ul class="issues">
                <li>
                    <strong>[Point 1]</strong>: [Why it is bad]
                    <div class="fix">💡 แก้โดย: [Specific Action]</div>
                </li>
            </ul>
        </div>
        <div class="section">
            <h3>✅ สิ่งที่ทำดีแล้ว (Keep it)</h3>
            <ul class="good">
                <li>[Point 1]</li>
            </ul>
        </div>
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        clean_text = response.text.replace("```html", "").replace("```", "")
        return {"result": clean_text}

    except Exception as e:
        print("❌ Analyze Error:")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")

# --- Endpoint 4: แก้ไข UI (Fix / SVG) ---
@app.post("/fix")
async def fix_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ใช้ Model ตัวเดิม
    target_model_name = 'gemini-2.5-flash'
    
    print(f"🎨 [Fix] Generating SVG Design for {country}...")

    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        # PROMPT: SVG Output
        prompt = f"""
        Act as a UI Designer. 
        Redesign this UI screenshot to fit {country} culture perfectly.
        Context: {context}.
        
        TASK:
        Generate a High-Fidelity Wireframe using SVG Code.
        
        REQUIREMENTS:
        1. Use colors suitable for {country}.
        2. Fix layout issues found in the image.
        3. Use <rect>, <text>, <circle>, <g> tags.
        4. Make it look modern and clean.
        5. Output ONLY raw SVG code (start with <svg> end with </svg>).
        6. Width: 375px, Height: 812px (Mobile size).
        7. Do not include markdown code blocks.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        # ล้าง Code block
        svg_code = response.text.replace("```svg", "").replace("```xml", "").replace("```", "")
        
        print("✅ SVG Generated!")
        return {"svg": svg_code}

    except Exception as e:
        print("❌ Fix Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")