from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

# --- Endpoint: Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    # ✅ เปลี่ยนมาใช้ตัวนี้ เร็ว + ยืดหยุ่นกว่า
    target_model_name = 'gemini-2.0-flash-exp'
    
    print(f"📥 Analyze Request: {country} - {target_model_name}")
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        IMPORTANT: Return ONLY the HTML code. Do not include markdown like ```html.
        """
        
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        
        # 🕵️‍♂️ Debug: ปริ้นท์คำตอบ AI ออกมาดูใน Log เลย
        print(f"🤖 AI Response: {response.text[:100]}...") 
        
        clean_response = response.text.replace("```html", "").replace("```", "").strip()
        return {"result": clean_response}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint: Fix ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...),
    description: str = Form(""), 
    width: str = Form("375"),    
    height: str = Form("812"),
    keep_layout: str = Form("false") 
):
    # ✅ ใช้ตัว 2.0 Flash Exp เหมือนกัน
    target_model_name = 'gemini-2.0-flash-exp'
    
    print(f"🎨 Fix Request: {target_model_name}")
    try:
        # 🔥 Config: บังคับให้ตอบแบบมั่นใจ ไม่มั่ว
        generation_config = genai.types.GenerationConfig(
            temperature=0.3, 
            max_output_tokens=8000
        )

        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        layout_instruction = "Maintain the main layout structure but update styles." if keep_layout == "true" else "You can modernize the layout."

        prompt = f"""
        Act as a UI Designer. Generate an SVG wireframe for {country} culture.
        Specs: {width}x{height}, Context: {context}, Desc: "{description}"
        
        CRITICAL RULES:
        1. Output ONLY raw SVG code. NO markdown blocks (```svg). NO explanatory text.
        2. Start immediately with <svg ...>
        3. {layout_instruction}
        4. Make sure all text is visible.
        """
        
        response = model.generate_content(
            [{'mime_type': 'image/jpeg', 'data': contents}, prompt],
            generation_config=generation_config
        )
        
        # 🕵️‍♂️ Debug: เช็กว่า AI ส่ง SVG มาจริงไหม
        print(f"🤖 AI SVG Response (First 100 chars): {response.text[:100]}")
        
        clean_svg = response.text.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        
        # ถ้า AI เผลอพูดนำหน้า ให้ตัดทิ้ง (Hack fix)
        if "<svg" in clean_svg:
            clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg:
            clean_svg = clean_svg[:clean_svg.find("</svg>")+6]

        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))