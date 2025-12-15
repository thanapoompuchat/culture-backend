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

github_token = os.environ.get("GITHUB_TOKEN")
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

# --- ฟังก์ชันทำความสะอาด SVG (ตัวใหม่! สำคัญมาก) ---
def clean_svg_content(raw_content):
    # 1. ลบ Markdown (```xml หรือ ```)
    clean = raw_content.replace("```xml", "").replace("```svg", "").replace("```", "")
    
    # 2. หาจุดเริ่ม <svg และจุดจบ </svg>
    start_match = re.search(r'<svg', clean, re.IGNORECASE)
    end_match = re.search(r'</svg>', clean, re.IGNORECASE)
    
    if start_match and end_match:
        start_index = start_match.start()
        end_index = end_match.end()
        svg_code = clean[start_index:end_index]
        return svg_code
    
    return None

# --- Endpoint Analyze ---
@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    print(f"📥 Analyze: {country}")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        prompt = f"""
        Act as a UX/UI Cultural Expert for {country}. Context: {context}.
        Analyze the image. Output HTML only (no markdown):
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> [Bullet points of issues] </div>
        <div class="suggestions"> [Bullet points of fixes] </div>
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output raw HTML only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1, max_tokens=1000,
        )
        return {"result": response.choices[0].message.content.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

# --- Endpoint Fix (ตัวแก้ปัญหาหลัก) ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("375"),    
    height: str = Form("812"),
    translate_text: str = Form("false"), # รับมาเป็น String ก่อนกันเหนียว
    keep_layout: str = Form("true")
):
    # แปลง String เป็น Boolean
    is_translate = translate_text.lower() == 'true'
    is_keep_layout = keep_layout.lower() == 'true'
    
    print(f"🛠️ Fix: {country} | Size: {width}x{height} | Trans: {is_translate} | Keep: {is_keep_layout}")
    
    try:
        contents = await file.read()
        image_uri = process_image(contents)

        # 🔥 Prompt ที่สั่งให้ output สะอาดที่สุด
        prompt = f"""
        You are a UI Wireframe Generator. Output ONLY valid SVG XML code.
        
        Task: Recreate the UI in the image for {country}.
        Canvas: width="{width}" height="{height}"
        
        Instructions:
        1. BACKGROUND: Start with <rect width="100%" height="100%" fill="#FFFFFF"/>
        2. STRUCTURE: Draw rectangles for Header, Content, Footer.
        3. DETAILS: Draw internal elements (buttons, images, inputs) as simple <rect> tags.
        4. COLOR: Use high contrast colors (Light Gray #F3F4F6 for background, Dark Gray #374151 for elements).
        
        Logic for {country}:
        - If {country} is Thailand/Asia: High density, many boxes.
        - If {country} is Western: More whitespace.
        
        CRITICAL RULES:
        - OUTPUT RAW SVG ONLY. NO MARKDOWN (```). NO EXPLANATION.
        - DO NOT use <foreignObject>.
        - DO NOT use <image>. Use <rect> as placeholder.
        - Ensure string starts with <svg and ends with </svg>.
        """

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an SVG rendering engine. Output code only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-11B-Vision-Instruct",
            temperature=0.1, # นิ่งที่สุด
            max_tokens=3000,
        )
        
        raw_content = response.choices[0].message.content
        print(f"🤖 Raw AI Response Length: {len(raw_content)}")

        # ✅ เรียกใช้ฟังก์ชันทำความสะอาด
        clean_svg = clean_svg_content(raw_content)
        
        if clean_svg:
            print("✅ SVG Extracted Successfully")
            return {"svg": clean_svg}
        else:
            print("❌ SVG Extraction Failed, sending fallback")
            # SVG สำรองกรณีฉุกเฉิน
            return {"svg": f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#fee2e2"/><text x="50%" y="50%" fill="red" font-family="sans-serif" text-anchor="middle">AI generated invalid code</text></svg>'}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}