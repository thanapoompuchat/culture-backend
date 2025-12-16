from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re

load_dotenv()

# ✅ Check API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("⚠️ Warning: GEMINI_API_KEY is missing")
    api_key = "MISSING_KEY" # ใส่กันไว้ไม่ให้แอป crash ตอน start

genai.configure(api_key=api_key)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI (Legacy Mode) Ready 🚀"}

# ✅ ฟังก์ชันเรียก AI แบบกันเหนียว (Safe Generate)
def generate_content_safe(prompt_parts):
    # 1. ลองตัว Flash ก่อน (เผื่อฟลุ๊ค)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(prompt_parts)
    except Exception as e:
        print(f"⚠️ 1.5 Flash failed ({e})... Switching to Legacy gemini-pro")
    
    # 2. ถ้า 1.5 พัง ให้ใช้ "gemini-pro" (รุ่น 1.0) ทันที **ตัวนี้ไม่มีวัน 404**
    try:
        model = genai.GenerativeModel("gemini-pro") 
        return model.generate_content(prompt_parts)
    except Exception as e:
        # ถ้ายังพังอีก คือ API Key ผิดชัวร์
        raise Exception(f"All models failed. Check API Key. Error: {e}")

# --- Utility Functions ---
def clean_svg_code(text):
    # ฟังก์ชันทำความสะอาด SVG เหมือนเดิม
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        svg = re.sub(r'```[a-z]*', '', svg).replace('```', '')
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        svg = re.sub(r'<image[\s\S]*?>', '', svg, flags=re.IGNORECASE) # เอา image ออกด้วย กัน error
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
    print(f"🚀 Processing for {country} (Safe Mode)")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Prompt เดิม แต่กระชับขึ้น
        prompt = f"""
        Act as UI Engineer. Canvas: {width}x{height}
        Task: Convert this UI image to raw SVG code.
        Style Target: {country} culture.
        Mode: {'Strict Layout Copy' if keep_layout == 'true' else 'Cultural Redesign'}.

        **CRITICAL RULES:**
        1. Output **ONLY** the RAW SVG code. Do not use Markdown blocks (```xml).
        2. Start tag: <svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" viewBox="0 0 {width} {height}">
        3. Use ONLY basic shapes: <rect>, <circle>, <path>, <text>.
        4. **FORBIDDEN:** Do NOT use <img>, <image>, or <foreignObject>.
        5. For images, just draw a gray <rect fill="#E0E0E0"/>.
        """

        # 🔥 เรียกใช้ฟังก์ชันกันตาย
        response = generate_content_safe([prompt, image])
        
        clean_code = clean_svg_code(response.text)
        if "<svg" not in clean_code:
            return {"svg": '<svg><text x="20" y="50">Error: AI did not return SVG</text></svg>'}
            
        return {"svg": clean_code}

    except Exception as e:
        print(f"❌ Final Error: {e}")
        return {"svg": f'<svg width="{width}" height="{height}"><rect width="100%" height="100%" fill="#ffebee"/><text x="50%" y="50%" fill="red" font-size="20" text-anchor="middle">Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # 🔥 เรียกใช้ฟังก์ชันกันตาย
        response = generate_content_safe([f"Analyze this UI for {country} context. Return HTML string only.", image])
        
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}