from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError # เพิ่ม import นี้
import json
import os
from dotenv import load_dotenv
import asyncio 

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ใช้ตัวเทพตัวเดิมของพี่
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

# ✅ ยืนยันใช้ 2.0 ตามที่พี่ต้องการ (เพราะ 1.5 มันกาก)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

class StyleGuide(BaseModel):
    recommended_colors: List[str]
    recommended_fonts: List[str]
    vibe_keywords: List[str]

class AnalysisResult(BaseModel):
    score: int
    language_analysis: str
    suggestions: List[str]
    style_guide: StyleGuide
    persona_used: Optional[str] = None

@app.post("/analyze-json", response_model=AnalysisResult)
async def analyze_json(
    file: UploadFile = File(...),
    country: str = Form(...),
    device: str = Form(...),
    context: str = Form(""),
    industry: str = Form("General"),
    persona: str = Form("General User")
):
    image_bytes = await file.read()
    
    prompt = f"""
    You are an expert UX/UI Consultant specialized in Localized Design for the market: {country}.
    
    YOUR ROLE:
    - You must act as a "{persona}" user in {country}. Adopt their mindset, pain points, and tech-literacy level.
    - You must judge the design based on standard practices for the "{industry}" industry.

    TASK:
    Analyze the attached UI image (Platform: {device}).
    Context: "{context}"

    Output ONLY raw JSON format with these fields:
    - score: (0-100) How well it fits {country}'s culture AND the {persona}'s needs.
    - language_analysis: Critique the text/language. Speak as the expert consultant.
    - suggestions: List 3-4 specific improvements for this persona/industry.
    - style_guide: {{
        "recommended_colors": ["#hex", ...],
        "recommended_fonts": ["FontName", ...],
        "vibe_keywords": ["keyword", ...]
    }}
    """

    try:
        # ยิงไปหา AI
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt
        ])
        
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_text)
        data['persona_used'] = persona 
        return data

    except ResourceExhausted:
        # ⚠️ จับ error เวลาโควต้าเต็ม (429)
        print("Quota exceeded! Please wait.")
        return {
            "score": 0,
            "language_analysis": "🚨 Server Busy (Google Quota Limit). Please wait 1 minute and try again.",
            "suggestions": ["The AI model is currently cooling down.", "Please retry in 60 seconds."],
            "style_guide": {
                "recommended_colors": ["#333333"], 
                "recommended_fonts": ["System"], 
                "vibe_keywords": ["Busy"]
            },
            "persona_used": persona
        }
    
    except Exception as e:
        # จับ Error อื่นๆ
        print(f"Error: {e}")
        return {
            "score": 0,
            "language_analysis": "System Error. Please try again.",
            "suggestions": [str(e)],
            "style_guide": {"recommended_colors": [], "recommended_fonts": [], "vibe_keywords": []},
            "persona_used": persona
        }