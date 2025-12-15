from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from groq import Groq
import base64

load_dotenv()

# ✅ เรียกใช้ Groq แทน Google
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Groq Server is running! ⚡"}

# --- Helper: แปลงรูปเป็น Base64 (Groq ต้องการแบบนี้) ---
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

# --- Endpoint: Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    print(f"📥 Analyze Request: {country} using Llama-3.2-Vision")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)
        
        # Groq (Llama 3.2 Vision) Prompt Structure
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this UI for {country} culture. Context: {context}. Output ONLY raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai. Do NOT use markdown formatting."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview", # 👈 รุ่นนี้มองเห็นภาพได้ + ฟรี
            temperature=0.1, # นิ่งๆ ไม่มั่ว
            max_tokens=1024,
        )

        result = chat_completion.choices[0].message.content
        print("✅ Analyze Done")
        return {"result": result.replace("```html", "").replace("```", "").strip()}

    except Exception as e:
        print("❌ Error:", e)
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
    print(f"🎨 Fix Request using Groq")
    try:
        contents = await file.read()
        base64_image = encode_image(contents)

        layout_instruction = "Maintain exact layout structure." if keep_layout == "true" else "You can optimize the layout."

        prompt_text = f"""
        Act as a UI Designer. Create an SVG wireframe for {country} culture.
        Specs: {width}x{height}, Context: {context}, Desc: "{description}"
        RULES:
        1. Output ONLY raw SVG code. NO markdown. NO intro text.
        2. Start with <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
        3. {layout_instruction}
        4. Use cultural colors suitable for {country}.
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
            model="llama-3.2-90b-vision-preview", # 👈 ใช้ตัวใหญ่ (90b) เพื่อความฉลาดในการเขียนโค้ด
            temperature=0.2,
            max_tokens=6000,
        )

        svg_code = chat_completion.choices[0].message.content
        
        # Clean up output
        clean_svg = svg_code.replace("```svg", "").replace("```xml", "").replace("```", "").strip()
        if "<svg" in clean_svg:
            clean_svg = clean_svg[clean_svg.find("<svg"):]
        if "</svg>" in clean_svg:
            clean_svg = clean_svg[:clean_svg.find("</svg>")+6]
            
        print("✅ Fix Done")
        return {"svg": clean_svg}

    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))