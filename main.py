from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# ใส่ try-except ดักไว้ ถ้าไม่มี Library จะได้รู้
try:
    from huggingface_hub import InferenceClient
except ImportError:
    print("❌ CRITICAL ERROR: 'huggingface_hub' is missing in requirements.txt")
    raise

import os
from dotenv import load_dotenv
import base64
import traceback

load_dotenv()

# ✅ ใช้ Token ที่คุณให้มา (แต่จริงๆ ควรใส่ใน Render Environment)
# เพื่อความชัวร์ ผมใส่ Code ดักไว้ว่าถ้าใน Render ไม่มี ให้ใช้ค่าว่าง (จะไม่ Crash แต่จะ Error ตอนเรียกใช้แทน)
hf_token = os.environ.get("HF_TOKEN")
if not hf_token:
    print("⚠️ WARNING: HF_TOKEN is missing. Please add it to Render Environment Variables.")

client = InferenceClient(api_key=hf_token)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Hugging Face Server is Live! 🚀"}

def get_image_data_uri(image_content):
    base64_img = base64.b64encode(image_content).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_img}"

# --- Analyze Endpoint ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze: {country}")
    try:
        contents = await file.read()
        image_uri = get_image_data_uri(contents)
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output raw HTML with: Score, Issues, Suggestions.
        """
        
        # ใช้ Qwen2-VL-7B (ตัวเล็ก เสถียรสุดสำหรับ Free Tier)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_uri}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        completion = client.chat.completions.create(
            model="Qwen/Qwen2-VL-7B-Instruct", 
            messages=messages, 
            max_tokens=1000,
            temperature=0.1
        )
        
        return {"result": completion.choices[0].message.content.replace("```html", "").replace("```", "").strip()}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return {"result": f"Error: {str(e)}"}

# --- Fix Endpoint ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...),
    description: str = Form(""), 
    width: str = Form("375"),    
    height: str = Form("812"),
    keep_layout: str = Form("false")
):
    try:
        contents = await file.read()
        image_uri = get_image_data_uri(contents)
        
        prompt = f"""
        Create SVG wireframe for {country}. {width}x{height}.
        Output ONLY raw SVG. Start with <svg.
        """
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_uri}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        completion = client.chat.completions.create(
            model="Qwen/Qwen2-VL-7B-Instruct",
            messages=messages,
            max_tokens=4000
        )
        
        svg = completion.choices[0].message.content.replace("```svg", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print("❌ Error:", e)
        return {"svg": ""}