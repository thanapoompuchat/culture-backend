from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import json
import os
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

# ตั้งค่า API KEY
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

class StyleGuide(BaseModel):
    recommended_colors: List[str]
    recommended_fonts: List[str]
    vibe_keywords: List[str]

class AnalysisResult(BaseModel):
    score: int
    language_analysis: str
    suggestions: List[str]
    style_guide: StyleGuide
    persona_used: Optional[str] = None # ส่งกลับไปให้ frontend โชว์

@app.post("/analyze-json", response_model=AnalysisResult)
async def analyze_json(
    file: UploadFile = File(...),
    country: str = Form(...),
    device: str = Form(...),
    context: str = Form(""),
    industry: str = Form("General"),      # รับค่า Industry
    persona: str = Form("General User")   # รับค่า Persona
):
    
    # อ่านไฟล์ภาพ
    image_bytes = await file.read()
    
    # Prompt เทพ (อัปเกรดแล้ว)
    prompt = f"""
    You are an expert UX/UI Consultant specialized in Localized Design for the market: {country}.
    
    YOUR ROLE:
    - You must act as a "{persona}" user in {country}. Adopt their mindset, pain points, and tech-literacy level.
    - You must judge the design based on standard practices for the "{industry}" industry (e.g., if Fintech: focus on trust/security. if Gen Z: focus on vibe/speed).

    TASK:
    Analyze the attached UI image (Platform: {device}).
    Context provided by user: "{context}"

    Analyze deeply on:
    1. Visual Culture: Do the colors, symbols, and layout fit {country}'s norms for a {industry} app?
    2. Usability for Persona: Is this design easy or appealing for a "{persona}"? (e.g., text size for seniors, navigation for non-tech users).
    3. Language: Is the tone appropriate for {country} and this industry?

    Output ONLY raw JSON format with these fields:
    - score: (0-100) How well it fits {country}'s culture AND the {persona}'s needs.
    - language_analysis: Critique the text/language. Speak as the expert consultant.
    - suggestions: List 3-4 specific improvements for this persona/industry.
    - style_guide: {{
        "recommended_colors": ["#hex", "#hex", ...],
        "recommended_fonts": ["FontName", ...],
        "vibe_keywords": ["keyword", ...]
    }}
    """

    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    response = model.generate_content([
        {"mime_type": "image/jpeg", "data": image_bytes},
        prompt
    ])

    # Clean JSON
    raw_text = response.text.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(raw_text)
        # เติม persona กลับไปให้ frontend
        data['persona_used'] = persona 
        return data
    except json.JSONDecodeError:
        return {
            "score": 0,
            "language_analysis": "Error parsing AI response.",
            "suggestions": ["Try again."],
            "style_guide": {"recommended_colors": [], "recommended_fonts": [], "vibe_keywords": []},
            "persona_used": persona
        }

@app.get("/")
def read_root():
    return {"status": "CultureAI API is running (Enhanced Version)"}