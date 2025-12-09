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

# --- Endpoint: Analyze (เหมือนเดิม) ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    target_model_name = 'gemini-flash-latest' # หรือ 'gemini-2.0-flash' ถ้าใช้ได้
    print(f"📥 Analyze for {country}")
    
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        prompt = f"""
        Act as a UX/UI Expert. Analyze this UI for {country} culture.
        Context: {context}.
        Output raw HTML with: Score (0-100), Critical Issues, and Suggestions in Thai.
        """
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint: Fix (อัปเกรดใหม่!) ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...),
    description: str = Form(""), # รับ Description
    width: str = Form("375"),    # รับขนาด
    height: str = Form("812"),
    keep_layout: str = Form("false") # รับ Checkbox
):
    target_model_name = 'gemini-flash-latest'
    print(f"🎨 Generating SVG for {country}. Size: {width}x{height}. Keep Layout: {keep_layout}")

    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        # 🔥 สร้าง Prompt แบบ Dynamic ตามเงื่อนไข
        layout_instruction = ""
        if keep_layout == "true":
            layout_instruction = "STRICTLY follow the original layout structure. Do not move main elements. Only adjust colors, spacing, and typography to fit the culture."
        else:
            layout_instruction = "You can rearrange the layout to be more modern and user-friendly, while keeping the main content."

        prompt = f"""
        Act as a Professional UI Designer.
        Redesign this UI for target audience: {country}.
        
        INPUT DETAILS:
        - Context: {context}
        - User Description: "{description}"
        - Screen Size: {width}x{height} pixels
        
        YOUR TASK:
        Generate a High-Fidelity Wireframe using SVG Code.
        
        DESIGN RULES:
        1. {layout_instruction}
        2. Use a color palette that perfectly matches {country} culture.
        3. Use <rect> for backgrounds/cards, <text> for labels, <circle> for avatars/icons.
        4. Make sure the SVG viewBox is "0 0 {width} {height}".
        5. Ensure all text is readable.
        
        OUTPUT FORMAT:
        - Return ONLY raw SVG code.
        - Start with <svg ...> and end with </svg>.
        - Do NOT use markdown code blocks.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        svg_code = response.text.replace("```svg", "").replace("```xml", "").replace("```", "")
        return {"svg": svg_code}

    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))