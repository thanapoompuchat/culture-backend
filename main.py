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
    # ✅ กลับมาตายรังที่ตัวนี้ครับ (Key ใหม่ + ตัวนี้ = รอดชัวร์)
    target_model_name = 'gemini-1.5-flash' 
    
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
    # ✅ กลับมาใช้ตัวนี้
    target_model_name = 'gemini-1.5-flash'
    
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
        
        INPUT DETAILS:
        - Context: {context}
        - User Description: "{description}"
        - Screen Size: {width}x{height} pixels
        
        YOUR TASK:
        Generate a High-Fidelity Wireframe using SVG Code.
        
        DESIGN RULES:
        1. {layout_instruction}
        2. Use a color palette that perfectly matches {country} culture.
        3. Output ONLY raw SVG code. No markdown.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        return {"svg": response.text.replace("```svg", "").replace("```xml", "").replace("```", "")}

    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))