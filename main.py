from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from groq import Groq
import base64
import traceback

load_dotenv()

# ✅ ตั้งค่า Client
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Groq Server is Live! (Fixed Model) 🚀"}

# --- Helper: แปลงรูป ---
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

# --- Helper: ฟังก์ชันเรียก AI แบบกันเหนียว (ถ้าตัวแรกดับ ใช้ตัวสอง) ---
def call_groq_with_fallback(messages, max_tokens):
    # รายชื่อโมเดลที่จะลองใช้ (เรียงจาก ดีสุด -> รองลงมา)
    models_to_try = [
        "llama-3.2-90b-vision-preview",  # ตัวเทพ (แนะนำ)
        "llama-3.2-11b-vision-preview",  # ตัวเล็ก (สำรอง)
        "llama-3.3-70b-versatile"        # ตัวใหม่ล่าสุด (ถ้ามันรองรับรูป)
    ]
    
    last_error = None
    
    for model_name in models_to_try:
        try:
            print(f"🔄 Trying model: {model_name}...")
            response = client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=0.2,
                max_tokens=max_tokens,
            )
            print(f"✅ Success with {model_name}!")
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Model {model_name} failed: {str(e)}")
            last_error = e
            continue # ลองตัวถัดไป
            
    # ถ้าพังทุกตัว
    raise last_error

# --- Endpoint: Analyze ---
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
        
        prompt_text = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        IMPORTANT: Do NOT output markdown code blocks. Just the HTML.
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }
        ]

        # ✅ เรียกใช้ฟังก์ชันกันเหนียว
        result = call_groq_with_fallback(messages, max_tokens=1024)
        
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print("❌ Final Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint: Fix ---
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
    print(f"🎨 Fix Request")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)

        layout_instruction = "Maintain exact layout structure." if keep_layout == "true" else "Optimize layout slightly."

        prompt_text = f"""
        Act as a UI Designer. Create an SVG wireframe for {country} culture.
        Specs: {width}x{height}, Context: {context}, Desc: "{description}"
        RULES:
        1. Output ONLY raw SVG code. NO markdown.
        2. Start with <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
        3. {layout_instruction}
        4. Use cultural colors suitable for {country}.
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }
        ]

        # ✅ เรียกใช้ฟังก์ชันกันเหนียว
        svg_code = call_groq_with_fallback(messages, max_tokens=6000)
        
        # Clean up
        clean_svg = svg_code.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in clean_svg:
            clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg:
            clean_svg = clean_svg[:clean_svg.find("</svg>")+6]
            
        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Final Error:", e)
        raise HTTPException(status_code=500, detail=str(e))