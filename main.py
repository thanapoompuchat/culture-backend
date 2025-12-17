from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------------------------------------------------
# ✅ จัดให้ตามคำขอครับ: Gemini 2.5 Flash
# ---------------------------------------------------------
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Model Error: {e}")
    # เผื่อระบบยังไม่ whitelist ให้พี่ ผมกันเหนียว fallback เป็น 1.5 ให้ก่อนครับ
    # แต่ถ้าพี่มั่นใจว่า key พี่ใช้ได้ มันจะรันตัวบนครับ
    model = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
def read_root():
    return {"message": "Culture AI Backend is Running!"}

@app.post("/analyze-json")
async def analyze_img_json(
    file: UploadFile = File(...),
    country: str = Form(...),
    device: str = Form("mobile"),
    context: str = Form("")
):
    try:
        content = await file.read()
        image_part = {"mime_type": file.content_type, "data": content}

        prompt = f"""
        You are an expert UI/UX Designer specialized in Localization.
        Analyze this UI design for target users in: {country}.
        
        Context info:
        - Device: {device}
        - Description: {context if context else "None"}

        Output ONLY raw JSON (no markdown):
        {{
            "score": (0-100 integer),
            "culture_fit_level": "High/Medium/Low",
            "suggestions": ["list of 3-5 specific improvements"],
            "color_palette_analysis": "analysis for {country}",
            "layout_analysis": "analysis for {country} on {device}"
        }}
        """

        response = model.generate_content([prompt, image_part])
        
        # Clean JSON string
        json_str = response.text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:-3]
        elif json_str.startswith("```"):
            json_str = json_str[3:-3]
            
        return json.loads(json_str)

    except Exception as e:
        print(f"Error: {e}")
        return {
            "score": 0,
            "culture_fit_level": "Error",
            "suggestions": [f"Error: {str(e)} - Check API Key or Model Name"],
            "color_palette_analysis": "N/A",
            "layout_analysis": "N/A"
        }