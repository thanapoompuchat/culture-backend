from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image

load_dotenv()

# ✅ ใช้ OpenRouter (ศูนย์รวมของฟรี)
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
if not openrouter_api_key:
    print("⚠️ WARNING: OPENROUTER_API_KEY is missing")

# ตั้งค่า Client ให้วิ่งไป OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "OpenRouter (Free Vision) is Ready! 🚀"}

# --- ฟังก์ชันย่อรูป (จำเป็นสำหรับของฟรี เพื่อไม่ให้ Time out) ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ย่อเหลือ 800px (ชัดพอให้ AI อ่าน UI ออก)
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

# --- Endpoint Analyze ---
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
        Output ONLY raw HTML (no markdown) with: 
        <div class="score">Score 0-100</div>
        <div class="issues">Critical Issues</div>
        <div class="suggestions">Suggestions</div>
        """
        
        # เรียก OpenRouter
        response = client.chat.completions.create(
            # ✅ ใช้โมเดล Qwen 2 VL (Free) -> เก่งเรื่องรูปมาก
            model="qwen/qwen-2-vl-7b-instruct:free", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_uri
                            }
                        }
                    ]
                }
            ],
            # ต้องใส่ Header นี้ตามกฎของ OpenRouter เพื่อให้ใช้ของฟรีได้เสถียร
            extra_headers={
                "HTTP-Referer": "https://render.com", 
                "X-Title": "UI Analyzer App",
            },
            temperature=0.2, 
            max_tokens=1024
        )
        
        result = response.choices[0].message.content
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"result": f"<div style='color:red'><h3>System Error</h3><p>{str(e)}</p></div>"}

# --- Endpoint Fix ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("375"),    
    height: str = Form("812")
):
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        prompt = f"""
        Create SVG wireframe for {country}. {width}x{height}.
        Output ONLY raw SVG code. Start with <svg. No markdown.
        """
        
        response = client.chat.completions.create(
            model="qwen/qwen-2-vl-7b-instruct:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_uri
                            }
                        }
                    ]
                }
            ],
            extra_headers={
                "HTTP-Referer": "https://render.com", 
                "X-Title": "UI Analyzer App",
            },
            temperature=0.2,
            max_tokens=2048
        )
        
        svg = response.choices[0].message.content.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}