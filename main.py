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

genai.configure(api_key=api_key)

# 🔥 SYSTEM: AUTO-SELECT MODEL (ระบบเลือกโมเดลอัตโนมัติ)
# พยายามใช้ตัว Pro ก่อน ถ้าไม่ได้ให้ใช้ Flash
def get_model():
    generation_config = {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }
    
    # รายชื่อโมเดลที่อยากใช้ (เรียงจากฉลาดสุด -> เร็วสุด)
    candidates = ["gemini-1.5-pro-latest", "gemini-1.5-pro", "gemini-1.5-flash"]
    
    selected_model = None
    
    # ลอง Test เรียกโมเดลทีละตัว
    for model_name in candidates:
        try:
            print(f"🔄 Testing model: {model_name}...")
            m = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            # ลองส่งคำสั่งเปล่าๆ เพื่อเช็คว่า Error 404 ไหม
            m.count_tokens("test") 
            print(f"✅ Selected Model: {model_name}")
            return m
        except Exception as e:
            print(f"❌ Failed to load {model_name}: {e}")
            continue
            
    # ถ้าพังทุกตัว ให้ใช้ Flash เป็นค่า Default ตายตัว
    print("⚠️ All selection failed. Forcing fallback to gemini-1.5-flash")
    return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

# Initialize Model (รันตอนเปิด Server)
model = get_model()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI is Ready! 🚀"}

# ✅ Endpoint พิเศษ: เช็คว่า Account พี่ใช้อะไรได้บ้าง
@app.get("/check-models")
def check_models():
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        return {"available_models": available}
    except Exception as e:
        return {"error": str(e)}

# --- Utility Functions ---
def clean_svg_code(text):
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        svg = re.sub(r'```[a-z]*', '', svg)
        svg = svg.replace('```', '')
        # Remove dangerous tags
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        svg = re.sub(r'<image[\s\S]*?>', '', svg, flags=re.IGNORECASE)
        return svg
    return text

def get_culture_prompt(country):
    rules = {
        "Thailand": {
            "style": "Friendly, Colorful, Accessible. High Information Density.",
            "colors": "Primary: Orange (#FF9F1C) or Teal (#2EC4B6). Background: White/Cream.",
            "shapes": "Rounded corners (rx='12'). Friendly icons.",
            "instruction": "Thai users prefer colorful interfaces. Group information clearly."
        },
        "Japan": {
            "style": "Minimalist, Clean, Trustworthy, Organized.",
            "colors": "Primary: Muted Blue (#2C3E50) or Soft Red. Background: White.",
            "shapes": "Square/Slightly rounded (rx='4'). Thin borders.",
            "instruction": "Japanese UX relies on precision, grids, and readability."
        },
        "China": {
            "style": "Festive, Complex, Super-App Vibe, Maximum Density.",
            "colors": "Primary: Red (#D32F2F) and Gold.",
            "shapes": "Compact buttons, small padding.",
            "instruction": "Maximize screen usage. Dense layout."
        },
        "USA": {
            "style": "Bold, Direct, Spacious, Minimalist.",
            "colors": "Primary: Royal Blue (#1D4ED8) or Black.",
            "shapes": "Large buttons, Sharp/Pill shapes.",
            "instruction": "Use ample whitespace. Big headings."
        }
    }
    return rules.get(country, rules["USA"])

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true"),
    translate_text: str = Form("false")
):
    print(f"🚀 Fixing UI for: {country}")
    
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    culture_data = get_culture_prompt(country)
    is_keep_layout = keep_layout.lower() == 'true'

    # 🔥 Prompt Strategy
    if is_keep_layout:
        task_instruction = f"""
        **MODE: EXACT LAYOUT TRACING**
        1. **VISUAL SCAN:** Count the exact number of columns/rows.
        2. **GEOMETRY:** Recreate the grid structure exactly. (e.g. If grid is 3x2, draw 6 cards).
        3. **PRESERVATION:** Maintain spatial arrangement relative to canvas {width}x{height}.
        4. **ADAPTATION:** Only change Styling for {country}:
           - Colors: {culture_data['colors']}
           - Shapes: {culture_data['shapes']}
        """
    else:
        task_instruction = f"""
        **MODE: CULTURAL REDESIGN**
        1. Analyze content hierarchy.
        2. **RE-LAYOUT** to fit {country} user habits:
           - {culture_data['style']}
           - {culture_data['instruction']}
        """

    prompt = f"""
    You are a Senior UI Engineer & SVG Specialist.
    Target Canvas: width="{width}" height="{height}"
    
    {task_instruction}

    **TECHNICAL SVG RULES (STRICT):**
    1. Output **RAW SVG CODE ONLY**. No Markdown.
    2. Start with `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">`.
    3. Use `<rect>` for all containers. 
       - Image placeholders: fill="#E0E0E0"
    4. **DO NOT** use `<foreignObject>` or `<img>`.
    5. Ensure high contrast and solid fills.
    
    GENERATE THE SVG NOW.
    """

    try:
        response = model.generate_content([prompt, image])
        clean_code = clean_svg_code(response.text)
        
        if "<svg" not in clean_code:
            raise Exception("Invalid SVG output")
            
        return {"svg": clean_code}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#fee2e2"/><text x="50%" y="50%" fill="red" font-family="sans-serif" text-anchor="middle">Generation Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        prompt = f"Analyze for {country}. Output HTML only (score, issues, fix)."
        response = model.generate_content([prompt, image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}