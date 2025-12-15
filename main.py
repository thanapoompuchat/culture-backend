from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re

load_dotenv()

# 🔑 ตั้งค่า Gemini API Key (อย่าลืมไปใส่ใน Render Environment Variable ชื่อ GEMINI_API_KEY นะครับ)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("⚠️ Warning: GEMINI_API_KEY is missing")

genai.configure(api_key=api_key)

# ✅ ใช้ Gemini 1.5 Flash (เร็วและแม่นยำเรื่อง Layout มาก)
# Config นี้ปรับให้มัน "ไม่มั่ว" (Temperature 0.1)
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI (Gemini Engine) is Ready! 🚀"}

# --- Utility Functions ---
def clean_svg_code(text):
    # ฟังก์ชันกรอง SVG ให้สะอาดที่สุด ตัด Markdown ทิ้ง
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE | re.DOTALL)
    if match:
        svg = match.group(1)
        # ลบ tag ที่ Figma ไม่ชอบ
        svg = re.sub(r'```[a-z]*', '', svg)
        svg = svg.replace('```', '')
        # ลบ foreignObject (ตัวทำ Figma เด้ง)
        svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
        return svg
    return text

# --- 🧠 สมองส่วนวัฒนธรรม (Cultural Brain) ---
def get_culture_prompt(country):
    # Design System ที่แม่นยำสำหรับแต่ละชาติ
    rules = {
        "Thailand": {
            "style": "Friendly, Accessible, Colorful, High Information Density.",
            "colors": "Primary: Vibrant Orange (#FF9F1C) or Blue (#2EC4B6). Background: White. Text: Dark Grey.",
            "shapes": "Rounded corners (rx='12'). Soft drop shadows.",
            "instruction": "Thai interfaces often pack a lot of information. Make buttons distinct and colorful."
        },
        "Japan": {
            "style": "Minimal, Clean, Trustworthy, Information-heavy but organized.",
            "colors": "Primary: Muted Blue (#2C3E50) or Soft Red. Background: White. Borders: Thin & Subtle.",
            "shapes": "Square or slightly rounded (rx='4'). High usage of borders.",
            "instruction": "Japanese interfaces rely on clear grids and high readability. Use smaller text but clear hierarchy."
        },
        "China": {
            "style": "Festive, Complex, Super-App vibe, Very High Density.",
            "colors": "Primary: Red (#D32F2F) and Gold (#FFC107).",
            "shapes": "Complex icons, Compact buttons.",
            "instruction": "Chinese apps maximize screen real estate. Small padding, many elements."
        },
        "USA": {
            "style": "Bold, Direct, Spacious, Minimalist.",
            "colors": "Primary: Royal Blue (#1D4ED8) or Black. High Contrast.",
            "shapes": "Large buttons, Sharp or Pill shapes.",
            "instruction": "US interfaces love whitespace. Use big headings and clear Call-to-Actions."
        }
    }
    return rules.get(country, rules["USA"]) # Default เป็น USA ถ้าหาไม่เจอ

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true"),
    translate_text: str = Form("false")
):
    print(f"🚀 Gemini Fixing UI: {country} | Keep Layout: {keep_layout}")
    
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    culture_data = get_culture_prompt(country)
    is_keep_layout = keep_layout.lower() == 'true'

    # 🔥 Prompt: แยกโหมดชัดเจน (Strict Layout vs Redesign)
    if is_keep_layout:
        # โหมด "คงเดิม" -> สั่งให้ดราฟต์
        task_instruction = f"""
        **TASK: TRACE AND ADAPT (Do not redesign)**
        1. Look at the uploaded image. Identify every button, image, and text block.
        2. **Generate SVG code that mirrors the EXACT POSITIONS (x, y)** of elements in the image.
        3. Do NOT change the layout structure. If there is a grid of 6 cards, draw 6 cards in the same grid.
        4. **ONLY CHANGE THE STYLING** (Colors, Border Radius, Font look) to match {country} culture:
           - Colors: {culture_data['colors']}
           - Shapes: {culture_data['shapes']}
        """
    else:
        # โหมด "ออกแบบใหม่" -> สั่งให้จัดวางใหม่
        task_instruction = f"""
        **TASK: CULTURAL REDESIGN**
        1. Analyze the content in the image.
        2. **Re-layout the elements** to better fit {country} UX patterns:
           - {culture_data['style']}
           - {culture_data['instruction']}
        3. You can move elements around to improve flow for {country} users.
        """

    # Final Prompt Assembly
    prompt = f"""
    Act as a Senior UI Engineer specializing in SVG coding.
    Target Canvas Size: width="{width}" height="{height}"
    
    {task_instruction}

    **TECHNICAL SVG RULES (STRICT):**
    - Output **RAW SVG CODE ONLY**. No Markdown (```). No conversational text.
    - Start with `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">`.
    - Use `<rect>` for backgrounds, cards, and image placeholders (fill with gray #ddd).
    - Use `<text>` for labels.
    - **CRITICAL:** Do NOT use `<foreignObject>` or `<img>` tags. Use `<rect>` placeholders instead.
    - Ensure all elements have sufficient contrast.
    
    Generate the SVG now.
    """

    try:
        # ส่งรูป + คำสั่งไปให้ Gemini
        response = model.generate_content([prompt, image])
        
        raw_text = response.text
        print(f"🤖 Gemini Output: {len(raw_text)} chars")
        
        clean_code = clean_svg_code(raw_text)
        
        # เช็คความถูกต้องเบื้องต้น
        if "<svg" not in clean_code:
            raise Exception("No SVG tag found")
            
        return {"svg": clean_code}

    except Exception as e:
        print(f"❌ Error: {e}")
        # Fallback SVG กรณีฉุกเฉิน
        return {"svg": f'<svg width="{width}" height="{height}" xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)"><rect width="100%" height="100%" fill="#fee2e2"/><text x="50%" y="50%" fill="red" font-family="Arial" text-anchor="middle">AI Error: {str(e)}</text></svg>'}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as a UX Cultural Expert for {country}. Context: {context}.
        Analyze the attached UI design.
        
        Output ONLY HTML code (no markdown) with this structure:
        <div class="score-container">
            <div class="score-value">[Score 0-100]</div>
        </div>
        <ul class="issues">
            <li>[Critical Issue 1 related to {country} culture]</li>
            <li>[Critical Issue 2]</li>
        </ul>
        <div class="fix">Suggested Fix: [One specific actionable advice]</div>
        """
        
        response = model.generate_content([prompt, image])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}