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
if not api_key: print("⚠️ Warning: GEMINI_API_KEY is missing")
genai.configure(api_key=api_key)

# 🔥 SYSTEM: THE SURVIVOR (ระบบเอาตัวรอด)
# พยายามหาโมเดลที่ใช้ได้จริงๆ ทีละตัว จนกว่าจะเจอ
def get_working_model():
    # เรียงลำดับจาก ฉลาดสุด -> ไปหาตัวที่ "ชัวร์สุด"
    model_list = [
        "gemini-1.5-pro-latest",  # ตัวเทพสุด
        "gemini-1.5-pro",         
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-pro"              # ตัวกันตาย (รุ่นเก่าแต่เสถียร 100%)
    ]
    
    print("🛡️ Starting Model Survival Check...")
    
    for model_name in model_list:
        try:
            print(f"🔄 Trying model: {model_name}...")
            # ลองสร้างโมเดลหลอกๆ ขึ้นมาเทส
            test_model = genai.GenerativeModel(model_name)
            # ลองยิงคำถามโง่ๆ ไป 1 ทีเพื่อดูว่า Error 404 ไหม
            test_model.count_tokens("test") 
            
            print(f"✅ SUCCESS! Connected to: {model_name}")
            return genai.GenerativeModel(
                model_name=model_name, 
                generation_config={"temperature": 0.2, "max_output_tokens": 8192}
            )
        except Exception as e:
            print(f"❌ {model_name} failed: {e}")
            continue # ไปลองตัวถัดไป
            
    # ถ้าซวยจริงๆ หาไม่เจอสักตัว (เป็นไปไม่ได้ถ้า Key ถูก)
    raise Exception("Critical: No Gemini models available with this API Key.")

# Initialize Model (รันตอนเปิด Server)
model = get_working_model()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Alive!"}

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
    print(f"🚀 Processing: {country}")
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # Prompt แบบย่อ เพื่อลดโอกาส Error
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

    try:
        response = model.generate_content([prompt, image])
        clean = clean_svg_code(response.text)
        if "<svg" not in clean: return {"svg": "Error: Invalid SVG"}
        return {"svg": clean}
    except Exception as e:
        return {"svg": f'<svg width="{width}" height="{height}"><text x="50" y="50">Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        response = model.generate_content([f"Analyze for {country}. Output HTML only.", image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}