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

# 🔥 SYSTEM: DYNAMIC MODEL FINDER (ระบบค้นหาโมเดลอัตโนมัติ)
# ไม่ระบุชื่อตายตัว แต่ถาม Google ว่า "มีอะไรให้ใช้บ้าง"
def get_available_model_name():
    try:
        print("🔍 Asking Google for available models...")
        for m in genai.list_models():
            # หาโมเดลที่รองรับการสร้างเนื้อหา (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                name = m.name
                # เอาชื่อที่สะอาดๆ (ตัด models/ ออกถ้ามี)
                clean_name = name.replace("models/", "")
                print(f"✅ Found working model: {clean_name}")
                return clean_name
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return None
    return None

# เลือกโมเดลเก็บไว้ในตัวแปร
current_model_name = get_available_model_name()
# ถ้าหาไม่เจอจริงๆ ให้ Default เป็น gemini-pro ไปก่อน
if not current_model_name:
    print("⚠️ No models found in list. Defaulting to 'gemini-1.5-flash'")
    current_model_name = "gemini-1.5-flash"

print(f"🚀 SYSTEM INITIALIZED WITH MODEL: {current_model_name}")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": f"Active using model: {current_model_name}"}

# ✅ Endpoint เช็คของ (กดดูได้เลยว่า Account พี่มีอะไรบ้าง)
@app.get("/debug-models")
def debug_models():
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return {"my_models": models, "selected": current_model_name}
    except Exception as e:
        return {"error": str(e), "tip": "API Key might be invalid or has no access."}

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
    # ใช้โมเดลที่หาเจอตอน Start
    model = genai.GenerativeModel(current_model_name)
    
    print(f"🚀 Processing with {current_model_name}")
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as UI Engineer. Canvas: {width}x{height}
        Task: Convert UI to SVG. Style: {country}.
        Mode: {'Strict Trace' if keep_layout == 'true' else 'Redesign'}.
        RULES: RAW SVG ONLY. No Markdown. No <img>. Use <rect> placeholders.
        """
        
        response = model.generate_content([prompt, image])
        clean = clean_svg_code(response.text)
        if "<svg" not in clean: return {"svg": "Error: AI output invalid"}
        return {"svg": clean}

    except Exception as e:
        return {"svg": f'<svg width="{width}" height="{height}"><text x="20" y="50" fill="red">Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        model = genai.GenerativeModel(current_model_name)
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        response = model.generate_content([f"Analyze for {country}", image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}