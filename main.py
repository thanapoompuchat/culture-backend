from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import re

load_dotenv()

# ✅ เช็ค Token
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("⚠️ WARNING: GITHUB_TOKEN is missing")

# 🔗 เชื่อมต่อ GitHub Models
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI Backend is Ready! 🚀"}

# --- ฟังก์ชันย่อรูป ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        max_size = 800
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70) 
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Resize Error: {e}")
        return ""

# --- Endpoint 1: Analyze (วิเคราะห์จุดที่ผิดวัฒนธรรม) ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze: {country}")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        prompt = f"""
        Act as a UX/UI Cultural Expert for {country}.
        Context: {context}.
        Task: Analyze the UI image and identify cultural mismatches.
        Output ONLY raw HTML (no markdown) with this structure:
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> [Bullet points of cultural issues (colors, layout, imagery)] </div>
        <div class="suggestions"> [Bullet points of specific actionable fixes] </div>
        Keep it concise.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a UX auditor. Output HTML only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct", # ตัวฉลาดสุดใช้วิเคราะห์
            temperature=0.1,
            max_tokens=1000,
        )
        
        result = response.choices[0].message.content
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        return {"result": f"<div style='color:red'>Error: {str(e)}</div>"}

# --- Endpoint 2: Fix (เจน Wireframe ใหม่ + ฟีเจอร์ภาษา) ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("375"),    
    height: str = Form("812"),
    translate_text: bool = Form(False) # ✅ รับค่า Checkbox ว่าจะแก้ภาษาไหม
):
    print(f"🛠️ Fix Request: {country} | Size: {width}x{height} | Translate: {translate_text}")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        # 📝 สร้าง Prompt แบบ Dynamic ตาม Checkbox
        translation_instruction = ""
        if translate_text:
            translation_instruction = f"IMPORTANT: Adjust layout direction for {country} (e.g., Right-to-Left for Arabic). Change text placeholders to mimic the visual density of {country} language."
        else:
            translation_instruction = "Keep text as abstract lines or generic English labels."

        # 🔥 Ultimate Prompt: บังคับวาดละเอียด + ปรับตามวัฒนธรรม
        prompt = f"""
        You are an expert UI Wireframe Coder.
        Task: Redesign this UI structure specifically for {country} culture.
        
        Settings:
        - Canvas: width="{width}" height="{height}"
        - Translate Mode: {translate_text} ({translation_instruction})
        
        STRICT DRAWING RULES (To avoid empty box):
        1. Background: White <rect width="100%" height="100%" fill="#FFFFFF"/>
        2. Content Blocks: You MUST draw separate rectangles for every button, image, and text block you see.
        3. Color System:
           - Header/Nav: fill="#F3F4F6" (Light Gray)
           - Images: fill="#D1D5DB" (Medium Gray) with stroke="#9CA3AF"
           - Buttons: fill="#1F2937" (Dark Gray)
           - Text Lines: fill="#6B7280" (Gray lines)
        
        CULTURAL ADAPTATION rules for {country}:
        - If {country} is Thailand/Japan/China: Make information density HIGHER. Smaller text blocks, more content.
        - If {country} is US/Europe: Use more whitespace (Padding).
        - If {country} is Arabic/Hebrew: FLIP the layout to Right-to-Left.
        
        Output:
        - ONLY valid SVG XML code starting with <svg> and ending with </svg>.
        - NO text explanations.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a machine that outputs SVG code only. You draw detailed wireframes."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-11B-Vision-Instruct", # ตัวไว หัวอ่อน ยอมทำตามสั่ง
            temperature=0.2, 
            max_tokens=2500, # เพิ่ม Token ให้วาดได้เยอะขึ้น
        )
        
        raw_content = response.choices[0].message.content
        print(f"🤖 AI Response Length: {len(raw_content)}")

        # Regex ดึง SVG
        match = re.search(r'<svg.*?</svg>', raw_content, re.DOTALL)
        
        if match:
            clean_svg = match.group(0)
            return {"svg": clean_svg}
        else:
            # Fallback SVG ถ้ายังพัง
            return {"svg": f"""
            <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#fee2e2"/>
                <text x="50%" y="50%" font-family="Arial" font-size="24" fill="#dc2626" text-anchor="middle">
                    AI Generation Failed
                </text>
                <text x="50%" y="60%" font-family="Arial" font-size="14" fill="#dc2626" text-anchor="middle">
                    Try simpler image or refresh
                </text>
            </svg>
            """}

    except Exception as e:
        print(f"❌ Fix Error: {e}")
        return {"svg": ""}