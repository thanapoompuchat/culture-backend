from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

# ✅ ใช้ GOOGLE_API_KEY (อย่าลืมไปแก้ใน Render)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Server is running with Gemini 1.5 Flash! ⚡"}

# --- Endpoint: Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze Request: {country}")
    try:
        # ✅ ใช้ 1.5 Flash ตัวเสถียร (โควต้าเยอะสุด)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        contents = await file.read()
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        IMPORTANT: Return ONLY the HTML code. Do not include markdown like ```html.
        """
        
        # ส่งรูป + Prompt
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        
        print(f"🤖 AI Response: {response.text[:50]}...") 
        clean_response = response.text.replace("```html", "").replace("```", "").strip()
        
        return {"result": clean_response}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
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
    print(f"🎨 Fix Request")
    try:
        # ✅ ใช้ 1.5 Flash เหมือนเดิม
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        contents = await file.read()
        
        layout_instruction = "Maintain the main layout structure but update styles." if keep_layout == "true" else "You can modernize the layout."

        prompt = f"""
        Act as a UI Designer. Generate an SVG wireframe for {country} culture.
        Specs: {width}x{height}, Context: {context}, Desc: "{description}"
        
        CRITICAL RULES:
        1. Output ONLY raw SVG code. NO markdown blocks.
        2. Start immediately with <svg ...>
        3. {layout_instruction}
        4. Make sure all text is visible.
        """
        
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        
        print(f"🤖 AI SVG Response: {response.text[:50]}...")
        
        clean_svg = response.text.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        
        if "<svg" in clean_svg:
            clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg:
            clean_svg = clean_svg[:clean_svg.find("</svg>")+6]

        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))