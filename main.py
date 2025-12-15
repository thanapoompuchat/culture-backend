from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import re

load_dotenv()

github_token = os.environ.get("GITHUB_TOKEN")
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI Backend is Ready! 🚀"}

def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
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

# --- ✅ ฟังก์ชันกรอง SVG ขั้นเทพ (แก้ใหม่) ---
def clean_and_repair_svg(raw_content):
    print("🧹 Cleaning SVG...")
    
    # 1. ลบ Markdown Code Block ทิ้งก่อนเลย
    content = raw_content.replace("```xml", "").replace("```svg", "").replace("```", "")
    
    # 2. ค้นหา <svg ... > จนถึง </svg> (ใช้ re.DOTALL เพื่อให้หาข้ามบรรทัดได้)
    pattern = r"(<svg[\s\S]*?</svg>)"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    
    if match:
        svg_code = match.group(1)
        
        # 3. 🔪 ตัด Tag ที่ Figma เกลียดออก (สำคัญมาก!)
        # Figma ไม่รองรับ foreignObject, switch, script, style แบบซับซ้อน
        forbidden_tags = ['foreignObject', 'script', 'iframe', 'animation']
        for tag in forbidden_tags:
            # ลบ tag เปิดและปิด และเนื้อหาข้างในทิ้ง
            svg_code = re.sub(f'<{tag}[\s\S]*?</{tag}>', '', svg_code, flags=re.IGNORECASE)
            # ลบ tag เดี่ยวๆ (เผื่อมี)
            svg_code = re.sub(f'<{tag}[^>]*>', '', svg_code, flags=re.IGNORECASE)

        # 4. ลบ attribute ที่อาจทำให้พัง
        svg_code = svg_code.replace('contenteditable="true"', '')
        
        return svg_code
    
    return None

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    print(f"📥 Analyze: {country}")
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        
        prompt = f"""
        Act as a UX/UI Cultural Expert for {country}. Context: {context}.
        Analyze the image. Output HTML only (no markdown):
        <div class="score"> [Score 0-100] </div>
        <div class="issues"> <ul><li>[Issue 1]</li><li>[Issue 2]</li></ul> </div>
        <div class="suggestions"> <ul><li>[Fix 1]</li><li>[Fix 2]</li></ul> </div>
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output raw HTML only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct",
            temperature=0.1, max_tokens=1000,
        )
        return {"result": response.choices[0].message.content.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("375"),    
    height: str = Form("812"),
    translate_text: str = Form("false"),
    keep_layout: str = Form("true")
):
    is_translate = translate_text.lower() == 'true'
    is_keep_layout = keep_layout.lower() == 'true'
    
    print(f"🛠️ Fix Request: {country} | Size: {width}x{height} | Trans: {is_translate} | Keep: {is_keep_layout}")
    
    try:
        contents = await file.read()
        image_uri = process_image(contents)

        # 🔥 Prompt แบบบังคับขู่เข็ญให้วาดง่ายๆ
        prompt = f"""
        You are a UI Wireframe Engine. Convert the image into valid SVG Code for {country}.
        Canvas Size: width="{width}" height="{height}"
        
        STRICT RULES FOR FIGMA COMPATIBILITY:
        1. OUTPUT ONLY SVG CODE. No explanations.
        2. DO NOT use <foreignObject> (Figma crashes).
        3. DO NOT use <img> tag (Figma blocks external URLs). Use <rect> with fill="#DDD" for images.
        4. Use ONLY these tags: <rect>, <circle>, <text>, <path>, <g>.
        5. All text must be inside <text> tags.
        
        DESIGN INSTRUCTION:
        - Recreate the layout structure.
        - Background: <rect width="100%" height="100%" fill="#FFFFFF"/>
        - Images: Draw a <rect> with color #e5e7eb.
        - Buttons: Draw a <rect> with rounded corners (rx="4").
        - Text: Use font-family="Arial, sans-serif".
        
        Cultural Adjustment ({country}):
        - If {country} is Thailand/Japan: Use tighter spacing, more information density.
        - If {country} is USA/Europe: Use more whitespace, bigger headings.
        """

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a coding machine. Return only SVG XML. No markdown."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-11B-Vision-Instruct", # รุ่น 11B เร็วและทำตามคำสั่ง Code ได้ดี
            temperature=0.1, 
            max_tokens=4000,
        )
        
        raw_content = response.choices[0].message.content
        print(f"🤖 AI Response Length: {len(raw_content)}")

        # เรียกใช้ตัวกรองใหม่
        clean_svg = clean_and_repair_svg(raw_content)
        
        if clean_svg:
            print("✅ SVG Sent to Figma")
            return {"svg": clean_svg}
        else:
            print("❌ Invalid SVG, Sending Fallback")
            # Fallback SVG ที่ดูดีขึ้นนิดนึง บอก User ว่าเกิดอะไรขึ้น
            return {"svg": f'''
                <svg width="{width}" height="{height}" xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)">
                    <rect width="100%" height="100%" fill="#F3F4F6"/>
                    <rect x="20" y="20" width="{int(width)-40}" height="{int(height)-40}" rx="10" fill="white" stroke="#EF4444" stroke-width="2"/>
                    <text x="50%" y="45%" fill="#EF4444" font-family="sans-serif" font-size="20" text-anchor="middle" font-weight="bold">Generation Failed</text>
                    <text x="50%" y="55%" fill="#666" font-family="sans-serif" font-size="14" text-anchor="middle">AI output contained invalid data.</text>
                </svg>
            '''}

    except Exception as e:
        print(f"❌ Server Error: {e}")
        return {"svg": ""}