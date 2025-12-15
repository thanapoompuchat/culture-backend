from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from groq import Groq
import base64
import traceback

load_dotenv()

# ✅ เรียกใช้ Groq (อย่าลืมตั้งค่า GROQ_API_KEY ใน Render)
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Groq Server (Llama-90b) is running! 🚀"}

# --- Helper: แปลงรูปเป็น Base64 ---
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

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
        
        # ใช้ Prompt แบบสั้นกระชับสำหรับ Groq
        prompt_text = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output ONLY raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        IMPORTANT: Do NOT output markdown code blocks. Just the HTML.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            # ✅ ใช้ตัว 90b เพราะฉลาดสุดและยังไม่โดนปิด
            model="llama-3.2-90b-vision-preview", 
            temperature=0.1,
            max_tokens=1024,
        )

        result = chat_completion.choices[0].message.content
        print("✅ Analyze Done")
        
        # Clean up
        clean_result = result.replace("```html", "").replace("```", "").strip()
        return {"result": clean_result}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
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
    print(f"🎨 Fix Request using Groq 90b")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)

        layout_instruction = "Maintain exact layout structure." if keep_layout == "true" else "You can optimize the layout slightly."

        prompt_text = f"""
        Act as a UI Designer. Create an SVG wireframe for {country} culture.
        Specs: {width}x{height}, Context: {context}, Desc: "{description}"
        
        RULES:
        1. Output ONLY raw SVG code. NO markdown. NO intro text.
        2. Start immediately with <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
        3. {layout_instruction}
        4. Use cultural colors suitable for {country}.
        5. Ensure all text is visible.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            # ✅ ใช้ตัว 90b ตัวเดิม (เสถียรสุดสำหรับรูปภาพตอนนี้)
            model="llama-3.2-90b-vision-preview",
            temperature=0.2,
            max_tokens=6000,
        )

        svg_code = chat_completion.choices[0].message.content
        
        # Clean up output (เผื่อ AI เผลอใส่ Text มา)
        clean_svg = svg_code.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        
        # ตัดส่วนเกินออก (ถ้ามี)
        if "<svg" in clean_svg:
            clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg:
            clean_svg = clean_svg[:clean_svg.find("</svg>")+6]
            
        print("✅ Fix Done")
        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))