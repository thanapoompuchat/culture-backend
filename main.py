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

# --- UPDATE: ใช้ Gemini 2.5 Flash (Latest Stable 2025) ---
# ตัวนี้ไวและฉลาดกว่า 1.5/2.0 ครับ
MODEL_NAME = 'gemini-2.5-flash' 

try:
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    print(f"Error loading model {MODEL_NAME}: {e}")
    # Fallback เผื่อ API Key พี่เก่ายังไม่เปิด Access (แต่ปกติ 2.5 เปิด public แล้ว)
    model = genai.GenerativeModel('gemini-1.5-flash')

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

        # Prompt จูนให้เข้ากับความฉลาดของ 2.5 Flash
        prompt = f"""
        You are a Senior UI/UX & Localization Expert using Gemini 2.5 capabilities.
        Analyze this UI design for target market: {country}.
        
        Context:
        - Platform: {device}
        - Description: {context if context else "None"}

        Analyze deeply on:
        1. Visual Culture (Colors, Layout, Symbols)
        2. Language & Tone (Read text in image: Is it polite? formal? appropriate?)
        3. Style Recommendations (Generate specific hex codes and font styles)

        Output ONLY raw JSON (no markdown):
        {{
            "score": (0-100 integer),
            "culture_fit_level": "High/Medium/Low",
            "suggestions": ["3-4 actionable UX improvements"],
            "language_analysis": "Analyze the text/copywriting in the image. Is the tone appropriate for {country} culture? Any taboo words?",
            "style_guide": {{
                "recommended_colors": ["#Hex1", "#Hex2", "#Hex3"],
                "recommended_fonts": ["Name of generic font style (e.g. Serif, Rounded)"],
                "vibe_keywords": ["Keyword1", "Keyword2"]
            }},
            "layout_analysis": "Feedback on layout for {country} on {device}"
        }}
        """

        response = model.generate_content([prompt, image_part])
        
        json_str = response.text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:-3]
        elif json_str.startswith("```"):
            json_str = json_str[3:-3]
            
        return json.loads(json_str)

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}