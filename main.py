from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re

load_dotenv()

# ✅ SETUP API KEY
api_key = os.environ.get("GEMINI_API_KEY")
# ถ้าไม่มี Key ใส่ค่าหลอกๆ ไปก่อน กันพัง
if not api_key: 
    print("⚠️ Warning: GEMINI_API_KEY is missing")
    api_key = "MISSING_KEY"

genai.configure(api_key=api_key)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Alive! (Waiting for requests...)"}

# ✅ Endpoint ใหม่: เอาไว้เช็คกุญแจโดยเฉพาะ
@app.get("/debug")
def check_key():
    try:
        # ลองแหย่ API ดูว่าผ่านไหม
        m = genai.GenerativeModel("gemini-1.5-flash")
        m.count_tokens("test")
        return {"status": "PASS ✅", "message": "API Key is WORKING!"}
    except Exception as e:
        return {
            "status": "FAIL ❌", 
            "error": str(e),
            "tip": "Please check GEMINI_API_KEY in Render Dashboard"
        }

# --- LOGIC ---
def clean_svg_code(text):
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        svg = re.sub(r'```[a-z]*', '', svg).replace('```', '')
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        return svg
    return text

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true")
):
    print(f"🚀 Processing: {country}")
    
    # ย้ายการเลือกโมเดลมาไว้ตรงนี้ (ถ้าพังก็พังแค่ตรงนี้ Server ไม่ดับ)
    try:
        # พยายามใช้ Flash ก่อน
        model = genai.GenerativeModel("gemini-1.5-flash")
    except:
        model = genai.GenerativeModel("gemini-pro")

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as UI Engineer. Target: {width}x{height}
        Task: Convert UI image to SVG.
        Style: {country} culture.
        Mode: {'Strict Layout Trace' if keep_layout == 'true' else 'Redesign'}.
        
        RULES:
        1. Output RAW SVG ONLY. No Markdown.
        2. Start with <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
        3. Use <rect> only. No <img>. No <foreignObject>.
        """

        response = model.generate_content([prompt, image])
        clean = clean_svg_code(response.text)
        if "<svg" not in clean: return {"svg": "Error: Invalid SVG from AI"}
        return {"svg": clean}

    except Exception as e:
        # ถ้า Error ให้ส่งกลับไปบอก Plugin ตรงๆ
        return {"svg": f'<svg width="{width}" height="{height}"><text x="20" y="50" fill="red" font-size="20">Server Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        response = model.generate_content([f"Analyze for {country}", image])
        return {"result": response.text}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}