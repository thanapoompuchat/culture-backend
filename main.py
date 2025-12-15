from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import time

load_dotenv()

# ✅ ใช้ Hugging Face Token
hf_token = os.environ.get("HF_TOKEN")
if not hf_token:
    print("⚠️ WARNING: HF_TOKEN missing")

client = InferenceClient(api_key=hf_token)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Hugging Face (Ultra Lite) is Live! 🔧"}

# --- ฟังก์ชันย่อรูป (โหมดบีบอัดขีดสุด) ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # แปลงเป็น RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ⚠️ บีบเหลือ 350px (เล็กเท่า thumbnail)
        # Hugging Face Free Tier รับ Payload ได้น้อยมาก ต้องเอาให้เล็กที่สุด
        max_size = 350
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
            
        # ⚠️ ลด Quality เหลือ 40 (ภาพแตกนิดหน่อย แต่ AI อ่าน Text/UI ได้อยู่)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=40) 
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"⚠️ Resize failed: {e}")
        return ""

# --- ฟังก์ชันเรียก AI พร้อมระบบ Retry ---
def ask_huggingface(prompt, image_uri, max_retries=3):
    # โมเดลนี้เสถียรสุดใน Free Tier สำหรับ Vision
    model_id = "Qwen/Qwen2-VL-7B-Instruct"
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_uri}},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt+1}/{max_retries}...")
            completion = client.chat.completions.create(
                model=model_id, 
                messages=messages, 
                max_tokens=600, # ลด Token ลงเพื่อประหยัดแรง Server
                temperature=0.2
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Error: {e}")
            if "400" in str(e):
                return "Error: Image too big. Please crop or try again."
            time.sleep(2) # รอ 2 วิแล้วลองใหม่เผื่อ Server Busy
            
    return "Error: Hugging Face Server is currently overloaded. Please try again later."

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
        image_uri = process_image(contents)
        
        if not image_uri:
            return {"result": "Error processing image."}

        prompt = f"""
        Act as a UX Expert for {country}. Analyze this UI.
        Context: {context}.
        Output ONLY HTML:
        <div class="score">Score 0-100</div>
        <div class="issues">Critical Issues</div>
        <div class="suggestions">Suggestions</div>
        """
        
        result = ask_huggingface(prompt, image_uri)
        clean_result = result.replace("```html", "").replace("```", "").strip()
        
        # ถ้า AI ตอบกลับมาไม่ใช่ HTML (เช่น Error message) ให้จัด Format ให้สวยงาม
        if "<div" not in clean_result:
            clean_result = f"<div class='score'>N/A</div><div class='issues'>{clean_result}</div>"
            
        return {"result": clean_result}

    except Exception as e:
        return {"result": f"<div style='color:red'>System Error: {str(e)}</div>"}

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
        Output ONLY raw SVG. Start with <svg.
        """
        
        result = ask_huggingface(prompt, image_uri)
        
        svg = result.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        return {"svg": ""}