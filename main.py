from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀"}

# --- Endpoint Analyze ---
@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ✅ ใช้ตัวนี้ รอดชัวร์
    target_model_name = 'gemini-1.5-flash'
    print(f"📥 Analyze using {target_model_name}")
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        prompt = f"Analyze UI for {country} in {context} context. Output raw HTML with specific advice in Thai."
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        return {"result": response.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint Fix ---
@app.post("/fix")
async def fix_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ✅ ใช้ตัวนี้ รอดชัวร์
    target_model_name = 'gemini-1.5-flash'
    print(f"🎨 Fix using {target_model_name}")
    try:
        model = genai.GenerativeModel(target_model_name)
        contents = await file.read()
        prompt = f"Redesign UI for {country}. Output ONLY raw SVG code (375x812 mobile)."
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': contents}, prompt])
        return {"svg": response.text.replace("```svg", "").replace("```xml", "").replace("```", "")}
    except Exception as e:
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e)) 