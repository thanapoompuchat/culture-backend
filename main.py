from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re

load_dotenv()

# ✅ ตั้งค่า API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("⚠️ Warning: GEMINI_API_KEY is missing")

genai.configure(api_key=api_key)

# 🔥 ใช้โมเดล 'gemini-1.5-pro' (ฉลาดที่สุดในตระกูล 1.5)
# Config นี้เน้นความแม่นยำ (Temperature ต่ำๆ)
generation_config = {
    "temperature": 0.2,  
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# ถ้า Render ยังฟ้อง 404 อีก ให้ลองเปลี่ยนชื่อเป็น "gemini-1.5-pro-latest"
model = genai.GenerativeModel(model_name="gemini-1.5-pro", generation_config=generation_config)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI (Gemini Pro Engine) is Ready! 🚀"}

# --- Utility Functions ---
def clean_svg_code(text):
    # ฟังก์ชันกรอง SVG ให้สะอาดที่สุด (Clean Markdown & Dangerous Tags)
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        svg = re.sub(r'```[a-z]*', '', svg)
        svg = svg.replace('```', '')
        # ลบ Tag ที่ทำให้ Figma เด้ง
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        svg = re.sub(r'<image[\s\S]*?>', '', svg, flags=re.IGNORECASE) 
        return svg
    return text

# --- 🧠 สมองส่วนวัฒนธรรม (Cultural System) ---
def get_culture_prompt(country):
    rules = {
        "Thailand": {
            "style": "Friendly, Colorful, Accessible. High Information Density.",
            "colors": "Primary: Vibrant Orange (#FF9F1C) or Teal (#2EC4B6). Background: White or Cream.",
            "shapes": "Rounded corners (rx='12'). Friendly icons with soft shadows.",
            "instruction": "Thai users prefer colorful interfaces. Group information clearly. Use engaging visuals."
        },
        "Japan": {
            "style": "Minimalist, Clean, Trustworthy, Highly Organized.",
            "colors": "Primary: Muted Blue (#2C3E50) or Soft Red. Background: White. Borders: Thin & Subtle.",
            "shapes": "Square or slightly rounded (rx='4'). Compact grids.",
            "instruction": "Japanese UX relies on precision, clear grids, and high information density with high readability."
        },
        "China": {
            "style": "Festive, Complex, Super-App Vibe, Maximum Density.",
            "colors": "Primary: Red (#D32F2F) and Gold (#FFC107).",
            "shapes": "Compact buttons, complex icons, small padding.",
            "instruction": "Maximize screen usage. Very small padding. Many entry points on one screen."
        },
        "USA": {
            "style": "Bold, Direct, Spacious, Minimalist.",
            "colors": "Primary: Royal Blue (#1D4ED8) or Black. High Contrast.",
            "shapes": "Large buttons, Sharp or Pill shapes.",
            "instruction": "Use ample whitespace (padding). Big headings. Clear hierarchy and Call-to-Actions."
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
    print(f"🚀 Gemini Pro Processing: {country} | Keep Layout: {keep_layout}")
    
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    culture_data = get_culture_prompt(country)
    is_keep_layout = keep_layout.lower() == 'true'

    # 🔥 Prompt ที่แบ่งโหมดชัดเจน
    if is_keep_layout:
        # 🟢 โหมด TRACING (เน้นคงโครงสร้าง)
        task_instruction = f"""
        **TASK: EXACT LAYOUT CLONING (TRACING)**
        1. **VISUAL SCAN:** Count the exact number of columns and rows in the image.
        2. **GEOMETRY:** Recreate the grid structure exactly. If there are 3 cards in a row, you MUST draw 3 rectangles.
        3. **PRESERVATION:** Do NOT remove elements. Do NOT simplify layout into a list. Keep the spatial arrangement.
        4. **ADAPTATION:** Only change the Styling to match {country}:
           - Colors: {culture_data['colors']}
           - Shapes: {culture_data['shapes']}
        """
    else:
        # 🟡 โหมด REDESIGN (รื้อใหม่)
        task_instruction = f"""
        **TASK: CULTURAL REDESIGN**
        1. Analyze the content hierarchy and purpose.
        2. **RE-LAYOUT** the interface to fit {country} user habits:
           - {culture_data['style']}
           - {culture_data['instruction']}
        3. You may rearrange elements, resize grids, or change navigation styles to optimize for {country}.
        """

    # Final Prompt
    prompt = f"""
    You are a Senior UI Engineer & SVG Specialist.
    Target Canvas: width="{width}" height="{height}"
    
    {task_instruction}

    **TECHNICAL SVG RULES (STRICT):**
    1. Output **RAW SVG CODE ONLY**. No Markdown. No comments.
    2. Start with `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">`.
    3. Use `<rect>` for all containers/cards. 
       - Image placeholders: fill="#E0E0E0"
       - Text lines: fill="#9CA3AF" (simulated text)
    4. **CRITICAL:** Do NOT use `<foreignObject>` or `<img>`. They cause crashes in Figma.
    5. Ensure high contrast and solid fills.
    
    GENERATE THE SVG NOW.
    """

    try:
        # ส่งรูปให้ Gemini Pro
        response = model.generate_content([prompt, image])
        clean_code = clean_svg_code(response.text)
        
        # เช็คว่าได้ SVG จริงไหม
        if "<svg" not in clean_code:
            raise Exception("AI did not generate valid SVG")
            
        return {"svg": clean_code}

    except Exception as e:
        print(f"❌ Error: {e}")
        # Fallback SVG กรณีฉุกเฉิน
        return {"svg": f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#fee2e2"/><text x="50%" y="50%" fill="red" font-family="sans-serif" text-anchor="middle">Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Analyze this UI for {country} culture (Context: {context}).
        Output HTML ONLY (no markdown):
        <div class='score-container'><div class='score-value'>[Score 0-100]</div></div>
        <ul class='issues'><li>[Cultural Issue 1]</li><li>[Cultural Issue 2]</li></ul>
        <div class='fix'>[Main Suggestion]</div>
        """
        
        response = model.generate_content([prompt, image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}