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

# โหลดตัวแปรจากไฟล์ .env (สำหรับรันในเครื่อง)
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
# ⚙️ SYSTEM SETUP: โหลด 10 API Keys
# ==============================================================================
# ดึง String ยาวๆ มาจาก Environment
keys_string = os.getenv("GEMINI_API_KEYS")

if keys_string:
    # แยกด้วยลูกน้ำ (,) และตัดช่องว่างออก
    VALID_KEYS = [k.strip() for k in keys_string.split(",") if k.strip()]
else:
    # กันเหนียว: กรณีลืมตั้งค่า ให้ลองหา key เดี่ยวๆ
    fallback_key = os.getenv("GENAI_API_KEY")
    VALID_KEYS = [fallback_key] if fallback_key else []

print(f"🔥 ACTIVE KEYS LOADED: {len(VALID_KEYS)} keys ready for rotation.")

# ใช้โมเดลตัว TOP สุด
MODEL_NAME = "gemini-2.0-flash-exp"

# ฟังก์ชันสลับคีย์อัตโนมัติ (The Magic Function)
async def generate_with_smart_rotation(content_parts):
    if not VALID_KEYS:
        raise Exception("No API Keys found in configuration!")

    # 1. เทคนิค Shuffle: สุ่มลำดับใหม่ทุกครั้ง เพื่อไม่ให้ Key ตัวแรกรับภาระหนักสุด
    # เช่น รอบนี้ลำดับอาจเป็น [Key9, Key2, Key5, ...]
    shuffled_keys = random.sample(VALID_KEYS, len(VALID_KEYS))
    
    last_error = None

    # 2. วนลูปไล่ลองทีละคีย์
    for i, key in enumerate(shuffled_keys):
        try:
            # log บอกหน่อยว่าใช้คีย์ไหน (ดู 4 ตัวท้าย)
            # print(f"🔄 Attempt {i+1}/{len(VALID_KEYS)}: Using Key ...{key[-4:]}")
            
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            
            # ยิง API
            response = await model.generate_content_async(content_parts)
            
            # ถ้าผ่าน ส่งของกลับเลย!
            return response

        except (ResourceExhausted, ServiceUnavailable) as e:
            # ถ้าคีย์นี้เต็ม (429) หรือเซิฟล่ม (503) -> ข้ามไปตัวต่อไปทันที!
            print(f"⚠️ Key ...{key[-4:]} is BUSY/EXHAUSTED. Switching...")
            last_error = e
            continue
            
        except Exception as e:
            # ถ้า Error แปลกๆ ก็ข้ามเหมือนกัน
            print(f"❌ Error on key ...{key[-4:]}: {e}")
            last_error = e
            continue

    # 3. ถ้าซวยจัดๆ วนครบ 10 คีย์แล้วยังไม่ได้ (โอกาสน้อยมาก)
    raise Exception(f"All {len(VALID_KEYS)} keys are exhausted/busy. Last error: {last_error}")

# ==============================================================================
# 📦 DATA MODELS
# ==============================================================================
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

# ==============================================================================
# 🚀 API ENDPOINT
# ==============================================================================
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
        You are an expert UX/UI Consultant specialized in Localized Design for: {country}.
        Role: {persona}. Industry: {industry}.
        Task: Analyze the attached UI image (Platform: {device}).
        Context: "{context}"

        Output ONLY raw JSON format (no markdown code blocks):
        {{
            "score": (integer 0-100),
            "language_analysis": "Critique language/grammar usage for {country}.",
            "suggestions": ["suggestion1", "suggestion2", "suggestion3"],
            "style_guide": {{
                "recommended_colors": ["#hex", "#hex"],
                "recommended_fonts": ["font_name"],
                "vibe_keywords": ["keyword"]
            }}
        }}
        """

        # เรียกใช้ระบบหมุนคีย์ 10 ร่าง
        response = await generate_with_smart_rotation([
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt
        ])
        
        # Clean ข้อมูลเผื่อ AI ใส่ Markdown มา
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        
        # หาปีกกาเปิดปิด เพื่อเอาแค่ JSON เนื้อๆ
        start_idx = raw_text.find("{")
        end_idx = raw_text.rfind("}") + 1
        if start_idx != -1 and end_idx != -1:
             json_str = raw_text[start_idx:end_idx]
        else:
             json_str = raw_text

        data = json.loads(json_str)
        data['persona_used'] = persona 
        return data

    except Exception as e:
        print(f"🔥 FINAL ERROR: {e}")
        # Return fallback json ถ้าพังจริงๆ (กันหน้าขาว)
        return {
            "score": 0,
            "language_analysis": "System is currently experiencing heavy traffic. Please try again in a few seconds.",
            "suggestions": ["Click Analyze again."],
            "style_guide": {"recommended_colors": [], "recommended_fonts": [], "vibe_keywords": []},
            "persona_used": persona
        }