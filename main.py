from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError
import json
import os
import random
import asyncio
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

# ==============================================================================
# ⚙️ SYSTEM SETUP
# ==============================================================================
keys_string = os.getenv("GEMINI_API_KEYS")

if keys_string:
    VALID_KEYS = [k.strip() for k in keys_string.split(",") if k.strip()]
else:
    fallback_key = os.getenv("GENAI_API_KEY")
    VALID_KEYS = [fallback_key] if fallback_key else []

print(f"🔥 ACTIVE KEYS LOADED: {len(VALID_KEYS)} keys ready for rotation.")

# ✅ จัดให้ตามคำขอครับพี่: Gemini 2.0 Flash (Experimental)
# ตัวนี้คือตัวใหม่ล่าสุดที่มีให้ใช้ตอนนี้ครับ (Google ยังไม่ปล่อยชื่อ 2.5 ออกมาในโค้ดครับ แต่ตัวนี้คือตัว Flash ใหม่สุดครับ)
MODEL_NAME = "gemini-2.5-flash-exp"

async def generate_with_smart_rotation(content_parts):
    if not VALID_KEYS:
        raise Exception("No API Keys found in configuration!")

    shuffled_keys = random.sample(VALID_KEYS, len(VALID_KEYS))
    last_error = None

    for key in shuffled_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            
            # ยิง API
            response = await model.generate_content_async(content_parts)
            return response

        except (ResourceExhausted, ServiceUnavailable) as e:
            # print(f"⚠️ Key ...{key[-4:]} BUSY. Switching...")
            last_error = e
            continue
            
        except Exception as e:
            # print(f"❌ Error on key ...{key[-4:]}: {e}")
            last_error = e
            continue

    raise Exception(f"All keys exhausted. Last error: {last_error}")

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
    try:
        image_bytes = await file.read()
        
        prompt = f"""
        You are an expert UX/UI Consultant for {country}.
        Role: {persona}. Industry: {industry}.
        Analyze the attached UI image (Platform: {device}).
        Context: "{context}"

        Output ONLY raw JSON format:
        {{
            "score": (0-100),
            "language_analysis": "Critique text in {country} context.",
            "suggestions": ["suggestion1", "suggestion2", "suggestion3"],
            "style_guide": {{
                "recommended_colors": ["#hex"],
                "recommended_fonts": ["font"],
                "vibe_keywords": ["keyword"]
            }}
        }}
        """

        response = await generate_with_smart_rotation([
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt
        ])
        
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        
        start_idx = raw_text.find("{")
        end_idx = raw_text.rfind("}") + 1
        json_str = raw_text[start_idx:end_idx] if start_idx != -1 else raw_text

        data = json.loads(json_str)
        data['persona_used'] = persona 
        return data

    except Exception as e:
        print(f"🔥 FINAL ERROR: {e}")
        return {
            "score": 0,
            "language_analysis": "Error: " + str(e),
            "suggestions": ["Please check server logs."],
            "style_guide": {"recommended_colors": [], "recommended_fonts": [], "vibe_keywords": []},
            "persona_used": persona
        }