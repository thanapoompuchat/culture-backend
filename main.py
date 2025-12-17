from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import re
import json

load_dotenv()

# --- SETUP ---
app = FastAPI()

# Config CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing in Environment Variables!")

genai.configure(api_key=api_key)

# เรียกใช้โมเดลตรงๆ ไม่ต้องวนหา (ใช้ชื่อนี้เสถียรสุดตอนนี้)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- UTILS ---
def clean_code_block(text, lang="json"):
    pattern = r"```" + lang + r"([\s\S]*?)```"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.replace("```", "").strip()

@app.get("/")
def read_root():
    return {"status": "Culture AI is Running 🚀"}

# --- ENDPOINTS ---

@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    keep_layout: str = Form("true")
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as UI Engineer. Canvas: {width}x{height}.
        Task: Convert UI to SVG. Style: {country}.
        Mode: {'Strict Trace' if keep_layout == 'true' else 'Redesign'}.
        RULES: RAW SVG ONLY. No Markdown. Use <rect> placeholders.
        """
        response = model.generate_content([prompt, image])
        clean = clean_code_block(response.text, "xml")
        if "<svg" not in clean: clean = clean_code_block(response.text, "svg")
        
        return {"svg": clean}
    except Exception as e:
        print(f"Error: {e}")
        return {"svg": f'<svg><text>Error: {str(e)}</text></svg>'}

@app.post("/generate-code")
async def generate_code(
    file: UploadFile = File(...), 
    country: str = Form(...),
    framework: str = Form("react_tailwind")
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Act as Developer. Convert UI to code.
        Framework: {framework}
        Style: {country}
        Output: ONLY CODE. No markdown text.
        """
        
        response = model.generate_content([prompt, image])
        return {"code": clean_code_block(response.text)}
    except Exception as e:
        return {"code": f"// Error: {str(e)}"}

@app.post("/analyze-json")
async def analyze_json(
    file: UploadFile = File(...), 
    country: str = Form(...)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        prompt = f"""
        Analyze this UI for {country} culture.
        Return JSON structure ONLY:
        {{
            "score": 0-100,
            "culture_fit_level": "Low/Medium/High",
            "primary_issues": ["..."],
            "positive_points": ["..."],
            "suggestions": ["..."],
            "color_palette_analysis": "...",
            "layout_analysis": "..."
        }}
        """
        
        response = model.generate_content([prompt, image])
        clean_json = clean_code_block(response.text, "json")
        return json.loads(clean_json)
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            "score": 0,
            "culture_fit_level": "Error",
            "primary_issues": [str(e)],
            "suggestions": ["Check Server Logs"]
        }