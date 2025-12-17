from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re
import json

load_dotenv()

# ✅ SETUP API KEY
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: print("⚠️ Warning: GEMINI_API_KEY is missing")
genai.configure(api_key=api_key)

# 🔥 DYNAMIC MODEL FINDER (ระบบหาโมเดลอัตโนมัติ)
def get_best_model():
    # ลำดับความสำคัญ: Pro (ฉลาดสุด) -> Flash (เร็วสุด) -> Pro 1.0 (กันตาย)
    candidates = ["gemini-1.5-pro-latest", "gemini-1.5-flash", "gemini-pro"]
    for m in candidates:
        try:
            test = genai.GenerativeModel(m)
            test.count_tokens("test")
            print(f"✅ Selected Model: {m}")
            return test
        except:
            continue
    print("⚠️ Fallback to default gemini-1.5-flash")
    return genai.GenerativeModel("gemini-1.5-flash")

model = get_best_model()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI Ecosystem Ready 🚀"}

# --- UTILS ---
def clean_code_block(text, lang="json"):
    # ฟังก์ชันล้าง Markdown ออก ให้เหลือแต่โค้ดเพียวๆ
    pattern = r"```" + lang + r"([\s\S]*?)```"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.replace("```", "").strip()

# ---------------------------------------------------------
# 🎨 FEATURE 1: FIX UI (SVG Generation) - อันเดิมของ Plugin
# ---------------------------------------------------------
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true")
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as UI Engineer. Canvas: {width}x{height}.
        Task: Convert UI to SVG. Style: {country}.
        Mode: {'Strict Trace' if keep_layout == 'true' else 'Redesign'}.
        RULES: RAW SVG ONLY. No Markdown. Use <rect> placeholders.
        """
        response = model.generate_content([prompt, image])
        clean = clean_code_block(response.text, "xml") # SVG มักอยู่ใน xml block
        if "<svg" not in clean: clean = clean_code_block(response.text, "svg")
        
        return {"svg": clean}
    except Exception as e:
        return {"svg": f'<svg><text>Error: {str(e)}</text></svg>'}

# ---------------------------------------------------------
# 💻 FEATURE 2: CODE GENERATOR (สำหรับ Plugin)
# ---------------------------------------------------------
@app.post("/generate-code")
async def generate_code(
    file: UploadFile = File(...), 
    country: str = Form(...),
    framework: str = Form("react_tailwind") # react_tailwind, vue, html_css, flutter
):
    print(f"💻 Generating Code: {framework} for {country}")
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Prompt สำหรับเขียนโค้ดโดยเฉพาะ
        prompt = f"""
        Act as a Senior Frontend Developer.
        Task: Convert this UI image into clean, production-ready code.
        Target Framework: {framework}
        Cultural Style: {country} (Adjust colors/fonts to match).
        
        REQUIREMENTS:
        1. Output ONLY the code. No explanations.
        2. If React/Vue, make it a single component file.
        3. Use placeholder images (via [https://placehold.co/600x400](https://placehold.co/600x400)).
        4. Make it responsive if possible.
        """
        
        response = model.generate_content([prompt, image])
        # พยายามเดาภาษาเพื่อ Clean code
        lang_map = {"react_tailwind": "jsx", "vue": "vue", "html_css": "html", "flutter": "dart"}
        clean_code = clean_code_block(response.text, lang_map.get(framework, ""))
        
        return {"code": clean_code}
    except Exception as e:
        return {"code": f"// Error generating code: {str(e)}"}

# ---------------------------------------------------------
# 📊 FEATURE 3: ANALYTICS (สำหรับ Web Dashboard)
# ---------------------------------------------------------
@app.post("/analyze-json")
async def analyze_json(
    file: UploadFile = File(...), 
    country: str = Form(...)
):
    print(f"📊 Analyzing for Web Dashboard: {country}")
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # บังคับให้ AI ตอบเป็น JSON เท่านั้น เพื่อเอาไปทำกราฟ
        prompt = f"""
        Analyze this UI for {country} culture compatibility.
        Return ONLY a JSON object with this exact structure (no markdown):
        {{
            "score": 0-100,
            "culture_fit_level": "Low/Medium/High",
            "primary_issues": ["Issue 1", "Issue 2"],
            "positive_points": ["Good point 1", "Good point 2"],
            "suggestions": ["Fix 1", "Fix 2"],
            "color_palette_analysis": "Comment on colors",
            "layout_analysis": "Comment on layout"
        }}
        """
        
        response = model.generate_content([prompt, image])
        clean_json = clean_code_block(response.text, "json")
        
        # แปลง String เป็น JSON Object จริงๆ
        data = json.loads(clean_json)
        return data
        
    except Exception as e:
        # กรณี AI เอ๋อ ตอบไม่เป็น JSON ให้ส่งค่า Error กลับไป
        return {
            "score": 0,
            "culture_fit_level": "Error",
            "primary_issues": [str(e)],
            "suggestions": ["Try again"]
        }