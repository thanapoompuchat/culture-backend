from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import traceback

load_dotenv()

# ✅ เช็ก Token
hf_token = os.environ.get("HF_TOKEN")
if not hf_token:
    print("⚠️ WARNING: HF_TOKEN missing")

client = InferenceClient(api_key=hf_token)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Hugging Face (Super Lite) is Live! 🚀"}

# --- ฟังก์ชันย่อรูป (Super Compressed Mode) ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ⚠️ บีบให้เหลือ 512px (เล็กแต่ AI อ่านรู้เรื่อง)
        max_size = 512 
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
            
        # ⚠️ ลดคุณภาพเหลือ 50% เพื่อให้ไฟล์เล็กที่สุด
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=50) 
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"⚠️ Resize failed: {e}")
        return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"

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
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML with: Score (0-100), Critical Issues, and Suggestions.
        Do NOT use markdown.
        """
        
        # ✅ ใช้ Qwen-VL-7B ตัวเดียว (ตัวอื่นเอาออกเพราะมันไม่มีให้ใช้ฟรี)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_uri}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # ลด Max Tokens ลงเพื่อกัน Timeout
        completion = client.chat.completions.create(
            model="Qwen/Qwen2-VL-7B-Instruct", 
            messages=messages, 
            max_tokens=800,
            temperature=0.2
        )
        
        result = completion.choices[0].message.content
        return {"result": result.replace("```html", "").replace("```", "").strip()}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        # ส่งข้อความกลับไปบอกผู้ใช้ตรงๆ ถ้า AI พัง
        return {"result": f"<div style='color:red'><h3>AI Error</h3><p>HuggingFace is busy. Please try again.</p><p>Detail: {str(e)}</p></div>"}

# --- Endpoint Fix ---
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
        image_uri = process_image(contents)
        
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
            max_tokens=2000
        )
        
        svg = completion.choices[0].message.content.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in svg: svg = svg[svg.find("<svg"):]
        if "</svg>" in svg: svg = svg[:svg.find("</svg>")+6]
        
        return {"svg": svg}

    except Exception as e:
        print("❌ Error:", e)
        return {"svg": ""}