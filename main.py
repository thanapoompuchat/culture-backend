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
if not api_key:
    print("⚠️ Warning: GEMINI_API_KEY is missing")

genai.configure(api_key=api_key)

# 🔥 SYSTEM: AUTO-FIND BEST MODEL (ระบบหาโมเดลที่ดีที่สุดอัตโนมัติ)
def get_best_model():
    # รายชื่อโมเดลที่เราอยากใช้ (เรียงจาก ดีสุด -> กันตาย)
    # เราใส่ gemini-pro (รุ่น 1.0) ไว้ท้ายสุดเผื่อรุ่น 1.5 ใช้ไม่ได้
    candidates = [
        "gemini-1.5-pro-latest", 
        "gemini-1.5-pro", 
        "gemini-1.5-flash-latest", 
        "gemini-1.5-flash",
        "gemini-pro" 
    ]
    
    generation_config = {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }

    print("🔍 Scanning for available models...")
    try:
        # ดึงรายชื่อโมเดลที่ Google อนุญาตให้ Account นี้ใช้
        available_models = [m.name for m in genai.list_models()]
        print(f"📋 Available Models on Server: {available_models}")
        
        for candidate in candidates:
            # ต้องแปลงชื่อนิดหน่อยเพราะใน list มันจะมี models/ นำหน้า
            check_name = f"models/{candidate}"
            if check_name in available_models or candidate in available_models:
                print(f"✅ FOUND MATCH: Using '{candidate}'")
                return genai.GenerativeModel(model_name=candidate, generation_config=generation_config)
    except Exception as e:
        print(f"⚠️ Error listing models: {e}")

    # Fallback สุดท้ายถ้าหาไม่เจอจริงๆ ให้ลองเสี่ยงดวงกับ Flash
    print("⚠️ No exact match found in list, forcing 'gemini-1.5-flash'")
    return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

# Initialize Model
model = get_best_model()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI is Running 🚀"}

# ✅ Endpoint พิเศษ: เอาไว้เช็คว่า Server มองเห็นโมเดลอะไรบ้าง
@app.get("/check")
def check_status():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return {"available_models": models, "current_api_key_status": "OK" if api_key else "MISSING"}
    except Exception as e:
        return {"error": str(e)}

# --- CORE LOGIC (ส่วนสมอง) ---
def clean_svg_code(text):
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        svg = re.sub(r'```[a-z]*', '', svg).replace('```', '')
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        return svg
    return text

def get_culture_prompt(country):
    # Prompt ที่จูนมาให้ฉลาดที่สุดตามที่ขอ
    rules = {
        "Thailand": {
            "style": "Friendly, Colorful, Super-App Style, Information Dense.",
            "colors": "Primary: Orange (#FF9F1C) or Vibrant Blue. Bg: White.",
            "shapes": "Rounded corners (rx='12'). Soft shadows.",
            "instruction": "Thai users love colorful, lively interfaces with clear icons."
        },
        "Japan": {
            "style": "Minimalist, Clean, Trustworthy, Grid-heavy.",
            "colors": "Primary: Muted Blue/Navy. Bg: White. Thin borders.",
            "shapes": "Square or slightly rounded (rx='4').",
            "instruction": "Japanese users prioritize readability, order, and density."
        },
        "China": {
            "style": "Festive, Complex, High Density, Red/Gold.",
            "colors": "Primary: Red (#D32F2F) and Gold.",
            "shapes": "Compact elements, complex navigation.",
            "instruction": "Maximize screen real estate. Very small padding."
        },
        "USA": {
            "style": "Bold, Direct, Spacious, Simple.",
            "colors": "Primary: Royal Blue or Black. High Contrast.",
            "shapes": "Large buttons, Pill shapes.",
            "instruction": "Use lots of whitespace. Big distinct headings."
        }
    }
    return rules.get(country, rules["USA"])

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true")
):
    print(f"🚀 Processing for {country}...")
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    culture_data = get_culture_prompt(country)
    
    # Prompt: Strict Tracing vs Redesign
    if keep_layout.lower() == 'true':
        task = f"""
        **TASK: PIXEL-PERFECT TRACING**
        1. **GRID DETECTION:** Count the columns/rows in the image. Replicate the grid EXACTLY.
        2. **STRUCTURE:** Do not change positions. If it's a grid of 6, draw 6 cards.
        3. **STYLE:** Apply {country} style ({culture_data['style']}) to colors/shapes only.
        """
    else:
        task = f"""
        **TASK: CULTURAL REDESIGN**
        1. Analyze content.
        2. **REARRANGE** elements to fit {country} UX habits.
        3. Optimize flow and hierarchy for {country}.
        """

    prompt = f"""
    Act as a Senior UI Engineer. Target: {width}x{height}
    {task}
    
    **RULES:**
    - Output RAW SVG ONLY. No Markdown.
    - Start with <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
    - Use <rect> for cards. Fill image placeholders with #E0E0E0.
    - NO <foreignObject>. NO <img>.
    - Apply Colors: {culture_data['colors']}
    - Apply Shapes: {culture_data['shapes']}
    
    Generate SVG now.
    """

    try:
        response = model.generate_content([prompt, image])
        clean_code = clean_svg_code(response.text)
        if "<svg" not in clean_code: return {"svg": "Error: Invalid SVG"}
        return {"svg": clean_code}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": f'<svg width="{width}" height="{height}"><rect width="100%" height="100%" fill="#fee"/><text x="50%" y="50%" text-anchor="middle">Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        prompt = f"Analyze UI for {country} (Context: {context}). Output HTML: <div class='score'>Score</div><ul class='issues'>Issues</ul><div class='fix'>Fix</div>"
        response = model.generate_content([prompt, image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}