from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

# --- Endpoint: Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    target_model_name = 'gemini-2.5-flash' # ใช้ตัวเดิมที่เวิร์ค
    
    print(f"📥 Analyze using {target_model_name}")
    try:
        # 🔥 ปรับ Config ให้ตอบไวขึ้นและตรงประเด็น
        generation_config = genai.types.GenerationConfig(
            temperature=0.4, # กลางๆ สำหรับการวิเคราะห์
            max_output_tokens=1000
        )
        
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        Keep it concise.
        """
        response = model.generate_content(
            [{'mime_type': 'image/jpeg', 'data': contents}, prompt],
            generation_config=generation_config
        )
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint: Fix (จูนใหม่!) ---
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
    target_model_name = 'gemini-2.5-flash'
    
    print(f"🎨 Generating SVG using {target_model_name} (Low Temp)")
    try:
        # 🔥 ทีเด็ด: ลดความมั่ว (Temperature) ให้ AI นิ่งขึ้น
        generation_config = genai.types.GenerationConfig(
            temperature=0.2,       # ต่ำมาก = นิ่ง, คงเส้นคงวา, ไม่มั่ว
            top_p=0.8,             # เลือกคำตอบที่ชัวร์เท่านั้น
            top_k=40,
            max_output_tokens=4000 # เผื่อ SVG ยาวๆ
        )

        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        # ปรับ Prompt ให้ดุขึ้น เรื่องตำแหน่ง
        layout_instruction = ""
        if keep_layout == "true":
            layout_instruction = """
            CRITICAL: PRESERVE THE EXACT LAYOUT STRUCTURE. 
            - Do NOT move buttons, images, or text blocks. 
            - Maintain relative positions exactly as seen in the image.
            - Only update colors, fonts, and corner radius to match culture.
            """
        else:
            layout_instruction = "Refine the layout to be cleaner but keep the main sections."

        prompt = f"""
        Act as a Professional Frontend Developer & UI Designer.
        Recreate this UI as a Clean SVG Wireframe for {country}.
        
        INPUT SPECS:
        - Viewport: {width}x{height}
        - Context: {context}
        - User Desc: "{description}"
        
        STRICT RULES:
        1. Output ONLY valid SVG code. No markdown text.
        2. Set <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">.
        3. {layout_instruction}
        4. Use <rect> for backgrounds (fill screen width/height).
        5. Use meaningful colors for {country} (e.g., Red/Gold for China, Minimal/Pastel for Japan).
        6. Group elements logically (<g>).
        
        """
        
        response = model.generate_content(
            [{'mime_type': 'image/jpeg', 'data': contents}, prompt],
            generation_config=generation_config # 👈 ยัด Config เข้าไป
        )
        
        return {"svg": response.text.replace("```svg", "").replace("```xml", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))