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

# ✅ ตั้งค่า GitHub Token
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("⚠️ WARNING: GITHUB_TOKEN is missing. Make sure to set it in Render Environment!")

# 🔗 เชื่อมต่อ Server ของ Microsoft Azure (GitHub Models)
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "GitHub Models API is Ready! 🚀"}

# --- ฟังก์ชันย่อรูป (จำเป็นสำหรับความเร็วและลด Error) ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ย่อเหลือ 800px เพื่อให้ AI ประมวลผลไว
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

# --- Endpoint 1: Analyze (วิเคราะห์วัฒนธรรม) ---
# ใช้โมเดล 90B เพราะฉลาดกว่าในการวิเคราะห์
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze Request: {country}")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML (no markdown code blocks) with this structure:
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> [List of Critical Cultural Issues] </div>
        <div class="suggestions"> [List of Actionable Suggestions] </div>
        Keep it brief and direct.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes UI designs."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            # ✅ ใช้ Llama 3.2 90B (ตัวฉลาด) สำหรับงานวิเคราะห์
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1,
            max_tokens=1000,
            top_p=1.0
        )
        
        result = response.choices[0].message.content
        # ล้าง Markdown ออก
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print(f"❌ Analyze Error: {e}")
        return {"result": f"<div style='color:red'><h3>System Error</h3><p>{str(e)}</p></div>"}

# --- Endpoint 2: Fix (สร้าง SVG) ---
# ใช้โมเดล 11B เพราะหัวอ่อนกว่า ยอมเขียนโค้ดง่ายกว่า
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("375"),    
    height: str = Form("812")
):
    print(f"🛠️ Fix Request: {country} ({width}x{height})")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        # 🔥 Prompt หลอก AI ว่าเป็น Coding Engine (ไม่ใช่ Designer)
        prompt = f"""
        You are a frontend coding engine.
        Task: Write SVG code that represents the layout structure of the provided image.
        
        Rules:
        1. Canvas size: width="{width}" height="{height}".
        2. Use <rect> (fill="#e5e7eb") for images/cards blocks.
        3. Use <rect> (fill="#9ca3af") for text blocks.
        4. Output ONLY valid XML starting with <svg> and ending with </svg>.
        5. Do NOT include any conversational text or markdown.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a strict code generator that outputs only SVG XML."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            # ✅ ใช้ Llama 3.2 11B (ตัวเล็ก) เพื่อลดโอกาสปฏิเสธงาน (Refusal)
            model="Llama-3.2-11B-Vision-Instruct", 
            temperature=0.3,
            max_tokens=2048,
        )
        
        raw_content = response.choices[0].message.content
        print(f"🤖 Raw AI Response: {raw_content[:100]}...")

        # ✅ ใช้ Regex ดึงเฉพาะ <svg>...</svg>
        match = re.search(r'<svg.*?</svg>', raw_content, re.DOTALL)
        
        if match:
            clean_svg = match.group(0)
            return {"svg": clean_svg}
        else:
            # Fallback SVG กรณีฉุกเฉิน
            print("⚠️ SVG Extraction failed")
            return {"svg": f"""
            <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#fee2e2"/>
                <text x="50%" y="50%" font-family="Arial" font-size="20" fill="#dc2626" text-anchor="middle">
                    AI could not generate layout
                </text>
            </svg>
            """}

    except Exception as e:
        print(f"❌ Fix Error: {e}")
        return {"svg": ""}