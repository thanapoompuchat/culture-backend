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

# --- ✅ ฟังก์ชันเช็กชื่อ Model (เผื่อต้องใช้) ---
@app.get("/models")
def list_models():
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return {"models": models}
    except Exception as e:
        return {"error": str(e)}

# --- Endpoint: Analyze ---
@app.post("/analyze")
async def analyze_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    context: str = Form(...)
):
    # ✅ แก้เป็นชื่อเต็มยศ (มี -001) เพื่อความชัวร์
    target_model_name = 'gemini-1.5-flash-001' 
    
    print(f"📥 Analyze using {target_model_name}")
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
    # ✅ ใช้ชื่อเต็มเหมือนกัน
    target_model_name = 'gemini-1.5-flash-001'
    
    print(f"🎨 Generating SVG using {target_model_name}")
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        
        layout_instruction = ""
        if keep_layout == "true":
            layout_instruction = "STRICTLY follow the original layout structure. Do not move main elements."
        else:
            layout_instruction = "You can rearrange the layout to be more modern."

        prompt = f"""
        Act as a Professional UI Designer.
        Redesign this UI for target audience: {country}.
        INPUT DETAILS: Context: {context}, Desc: "{description}", Size: {width}x{height}
        YOUR TASK: Generate SVG Code.
        RULES: {layout_instruction}, Match {country} culture, Output ONLY SVG.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        return {"svg": response.text.replace("```svg", "").replace("```xml", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))