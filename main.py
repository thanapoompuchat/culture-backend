from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image

load_dotenv()

# ✅ ใช้ GitHub Token
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("⚠️ WARNING: GITHUB_TOKEN is missing")

# 🔗 เชื่อมต่อ Server ของ Microsoft Azure (ผ่าน GitHub Models)
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "GitHub Models (Llama 3.2 Vision) is Live! 🐙"}

# --- ฟังก์ชันย่อรูป (จำเป็นมากสำหรับ Azure Free Tier) ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ย่อเหลือ 800px (ขนาดที่ Azure อ่านได้แม่นและไม่เกิน Limit)
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
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes UI designs."
                },
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
            # ✅ ใช้โมเดล Llama 3.2 90B ตัวท็อปสุด (ฟรีบน GitHub Models)
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1,
            max_tokens=1024,
            top_p=1.0
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
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert UI designer who outputs only SVG code."
                },
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
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1,
            max_tokens=2048,
            top_p=1.0
        )
        
        svg = response.choices[0].message.content.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}