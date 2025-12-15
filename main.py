from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io

load_dotenv()

# ✅ ใช้ SambaNova Key เดิมได้เลย
sambanova_api_key = os.environ.get("SAMBANOVA_API_KEY")
if not sambanova_api_key:
    print("⚠️ WARNING: SAMBANOVA_API_KEY is missing")

client = OpenAI(
    api_key=sambanova_api_key,
    base_url="https://api.sambanova.ai/v1",
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "SambaNova Llama 90B (Big Boy) is Ready! 🦍"}

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
    print(f"📥 Analyze Request: {country}")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML code (no markdown code blocks) with this structure:
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> [List of Critical Cultural Issues] </div>
        <div class="suggestions"> [List of Actionable Suggestions] </div>
        """
        
        # ⚠️ แก้ตรงนี้: เปลี่ยนเป็น 90B (ตัวนี้ยังอยู่และฟรี)
        response = client.chat.completions.create(
            model="Llama-3.2-90B-Vision-Instruct", 
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
        base64_image = encode_image(contents)
        
        prompt = f"""
        Create SVG wireframe for {country}. {width}x{height}.
        Output ONLY raw SVG code. Start with <svg. Do not use markdown blocks.
        """
        
        # ⚠️ แก้ตรงนี้ด้วย: เปลี่ยนเป็น 90B
        response = client.chat.completions.create(
            model="Llama-3.2-90B-Vision-Instruct",
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