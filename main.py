from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import re  # ✅ เพิ่มตัวนี้มาช่วยจับโค้ด

load_dotenv()

github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    print("⚠️ WARNING: GITHUB_TOKEN is missing")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "GitHub Models (Llama 3.2 Vision) is Live! 🐙"}

def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # ย่อรูปหน่อย AI จะได้ไม่งงและประมวลผลไว
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
        Output ONLY raw HTML (no markdown code blocks) with this structure:
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> [List of Critical Cultural Issues] </div>
        <div class="suggestions"> [List of Actionable Suggestions] </div>
        Keep it brief and direct.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes UI designs."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1,
            max_tokens=1000,
            top_p=1.0
        )
        
        result = response.choices[0].message.content
        # ล้าง Markdown ออกให้เกลี้ยง
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"result": f"<div style='color:red'><h3>System Error</h3><p>{str(e)}</p></div>"}

# --- Endpoint Fix (ตัวแก้ปัญหา SVG Error) ---
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
        
        # ปรับ Prompt ให้ดุขึ้น
        prompt = f"""
        Redesign this UI wireframe for {country} culture. Size: {width}x{height}.
        IMPORTANT: Output ONLY valid SVG code. 
        Start immediately with <svg ... and end with </svg>.
        Do not add any text, explanations, or markdown formatting.
        Use simple shapes (rect, circle, text). Ensure XML is valid.
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a UI generator that outputs strictly raw SVG code only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1,
            max_tokens=2048,
            top_p=1.0
        )
        
        raw_content = response.choices[0].message.content
        print("🤖 Raw AI Response:", raw_content[:100]) # Log ดูหน่อยว่าส่งไรมา

        # ✅ ใช้ Regex ค้นหา SVG แบบเจาะจง (แก้ปัญหา AI พูดเยอะ)
        match = re.search(r'<svg.*?</svg>', raw_content, re.DOTALL)
        
        if match:
            clean_svg = match.group(0)
            return {"svg": clean_svg}
        else:
            # 🛡️ ถ้าหา SVG ไม่เจอจริงๆ ให้ส่งรูป Error กลับไป (โปรแกรมจะได้ไม่เด้ง)
            fallback_svg = f"""
            <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#fee2e2"/>
                <text x="50%" y="50%" font-family="Arial" font-size="20" fill="#dc2626" text-anchor="middle" dominant-baseline="middle">
                    AI could not generate layout
                </text>
                <text x="50%" y="60%" font-family="Arial" font-size="14" fill="#dc2626" text-anchor="middle">
                    Try again or check logs
                </text>
            </svg>
            """
            print("⚠️ SVG Extraction failed, sending fallback.")
            return {"svg": fallback_svg}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"svg": ""}