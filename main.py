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
# ถ้าไม่มี Key ให้ใส่ค่าหลอกๆ ไปก่อน กันพัง
if not api_key: 
    print("⚠️ Warning: GEMINI_API_KEY is missing in Environment Variables")
    api_key = "MISSING_KEY"

genai.configure(api_key=api_key)

# 🔥 SYSTEM: LAZY LOADER (โหลดเมื่อใช้ ไม่โหลดตอนเริ่ม)
# เราตัดระบบเช็คตอน Start ทิ้งไปเลยครับ จะได้ไม่ Error status 1
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Alive! (Waiting for requests...)"}

# ✅ Endpoint นี้เอาไว้เช็คว่า Key ใช้ได้จริงไหม (กดแล้วรู้เรื่องเลย)
@app.get("/debug-key")
def debug_key():
    try:
        # ลองเรียกโมเดลดู
        m = genai.GenerativeModel("gemini-1.5-flash")
        m.count_tokens("test")
        return {"status": "OK", "message": "API Key is VALID ✅"}
    except Exception as e:
        return {
            "status": "ERROR ❌", 
            "reason": str(e),
            "tip": "Check your API Key in Render Dashboard -> Environment"
        }

# --- CORE LOGIC ---
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
    # ย้ายมาประกาศ Model ตรงนี้แทน (ถ้าพังก็พังแค่ตรงนี้ Server ไม่ดับ)
    try:
        # พยายามใช้ Flash ก่อนเพื่อความเร็ว
        model = genai.GenerativeModel("gemini-1.5-flash")
    except:
        model = genai.GenerativeModel("gemini-pro")

    print(f"🚀 Processing: {country}")
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
        if "<svg" not in clean: return {"svg": "Error: Invalid SVG output from AI"}
        return {"svg": clean}

    except Exception as e:
        # ส่ง Error กลับไปบอกที่ Plugin เลย
        error_msg = str(e)
        if "400" in error_msg: error_msg = "API Key Invalid (400)"
        if "403" in error_msg: error_msg = "API Key Permission Denied (403)"
        return {"svg": f'<svg width="{width}" height="{height}"><text x="20" y="50" fill="red" font-size="20">Error: {error_msg}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        response = model.generate_content([f"Analyze for {country}. Output HTML only.", image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}