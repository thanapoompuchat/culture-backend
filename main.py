from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import base64
import io

# 🚀 ไม่ต้องใช้ .env หรือ API Key ใดๆ ทั้งสิ้น
# เรายิงไปที่ Pollinations ซึ่งเป็น Public Proxy ฟรี
client = OpenAI(
    base_url="https://text.pollinations.ai/openai", # ชี้เป้าไปที่นี่
    api_key="super-free-key", # ใส่อะไรก็ได้ ไม่มีการตรวจ
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Pollinations (GPT-4o Vision) is Ready! 🦄"}

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
    print(f"📥 Analyze Request via Pollinations: {country}")
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
        
        # ใช้ GPT-4o ฟรีผ่าน Pollinations
        response = client.chat.completions.create(
            model="gpt-4o", # ใช้ตัวท็อปสุดได้เลย
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
            temperature=0.2, 
            max_tokens=2048
        )
        
        result = response.choices[0].message.content
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"result": f"<div style='color:red'><h3>Service Error</h3><p>{str(e)}</p></div>"}

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
        Make sure the code is valid SVG.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
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
            temperature=0.2,
            max_tokens=3000
        )
        
        svg = response.choices[0].message.content.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}