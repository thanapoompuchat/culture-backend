from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io

load_dotenv()

# ✅ ตั้งค่า SambaNova Client
# (ใช้ Library OpenAI แต่ชี้ไปที่ Server ของ SambaNova)
sambanova_api_key = os.environ.get("SAMBANOVA_API_KEY")
if not sambanova_api_key:
    print("⚠️ WARNING: SAMBANOVA_API_KEY is missing!")

client = OpenAI(
    api_key=sambanova_api_key,
    base_url="https://api.sambanova.ai/v1", # ชี้เป้าไปที่ SambaNova
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "SambaNova Server (Llama Vision) is Running! 🐢"}

# --- ฟังก์ชันแปลงรูปเป็น Base64 ---
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

# --- Endpoint Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze: {country}")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML (no markdown) with: 
        <div class="score">Score 0-100</div>
        <div class="issues">Critical Issues</div>
        <div class="suggestions">Suggestions</div>
        """
        
        response = client.chat.completions.create(
            model="Llama-3.2-11B-Vision-Instruct", # โมเดลนี้ฟรีและเปิดตลอด
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1024
        )
        
        result = response.choices[0].message.content
        return {"result": result.replace("```html", "").replace("```", "").strip()}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"result": f"<div style='color:red'>Server Error: {str(e)}</div>"}

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
        base64_image = encode_image(contents)
        
        prompt = f"""
        Create SVG wireframe for {country}. {width}x{height}.
        Output ONLY raw SVG code. Start with <svg. No markdown.
        """
        
        response = client.chat.completions.create(
            model="Llama-3.2-11B-Vision-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=2048
        )
        
        svg = response.choices[0].message.content.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}