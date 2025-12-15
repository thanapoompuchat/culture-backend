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

# ✅ ตั้งค่า Client
# ใช้ Token จาก Render Environment หรือ Fallback
hf_token = os.environ.get("HF_TOKEN")
if not hf_token:
    print("⚠️ WARNING: HF_TOKEN missing")

client = InferenceClient(api_key=hf_token)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Hugging Face Server (Optimized) is Live! 🚀"}

# --- ฟังก์ชันย่อรูป (หัวใจสำคัญแก้ Error 400) ---
def process_image(image_bytes):
    try:
        # เปิดรูปจาก bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # แปลงเป็น RGB (กันเหนียวเผื่อเจอไฟล์ PNG ใส)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # ✅ ย่อรูป: ถ้าด้านไหนเกิน 800px ให้ย่อลง (AI อ่านรู้เรื่อง ประหยัด Bandwidth)
        max_size = 800
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
            
        # ✅ แปลงกลับเป็น Base64 (JPEG Quality 70 พอ)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"⚠️ Image processing failed: {e}")
        # ถ้าพัง ให้ส่งแบบเดิมไปวัดดวง
        return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"

# --- ฟังก์ชันเรียก AI แบบสู้ชีวิต ---
def call_huggingface(prompt, image_uri, max_tokens=1000):
    # รายชื่อโมเดลเรียงตามความน่าจะเป็นที่จะรอด (ของฟรี)
    models = [
        "Qwen/Qwen2-VL-7B-Instruct",       # ตัวแรกที่ลอง
        "microsoft/Phi-3.5-vision-instruct", # ตัวสำรอง (เก่งมาก)
        "meta-llama/Llama-3.2-11B-Vision-Instruct" # ตัวสุดท้าย (ต้องมีสิทธิ์)
    ]
    
    last_error = None
    
    for model_id in models:
        try:
            print(f"🔄 Trying model: {model_id}...")
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
                model=model_id, 
                messages=messages, 
                max_tokens=max_tokens,
                temperature=0.2
            )
            
            print(f"✅ Success with {model_id}!")
            return completion.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ Failed with {model_id}: {e}")
            last_error = e
            continue
    
    # ถ้าพังทุกตัว ให้โยน Error จริงออกมา
    raise last_error

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
        # ✅ เรียกใช้ฟังก์ชันย่อรูปก่อนส่ง
        image_uri = process_image(contents)
        
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML with: Score (0-100), Critical Issues, and Suggestions.
        Do NOT use markdown.
        """
        
        result = call_huggingface(prompt, image_uri)
        return {"result": result.replace("```html", "").replace("```", "").strip()}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        # ส่งค่า Error กลับไปแบบเนียนๆ ไม่ให้หน้าเว็บพัง
        return {"result": f"<div style='color:red'><h3>AI Busy/Error</h3><p>{str(e)}</p></div>"}

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
        image_uri = process_image(contents)
        
        prompt = f"""
        Create SVG wireframe for {country}. {width}x{height}.
        Output ONLY raw SVG. Start with <svg.
        """
        
        svg = call_huggingface(prompt, image_uri, max_tokens=2000)
        
        clean_svg = svg.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in clean_svg: clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg: clean_svg = clean_svg[:clean_svg.find("</svg>")+6]
        
        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Error:", e)
        return {"svg": ""}