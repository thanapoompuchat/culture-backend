from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import json
import os
import random
import io
from PIL import Image
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

keys_string = os.getenv("GEMINI_API_KEYS")
if keys_string:
    VALID_KEYS = [k.strip() for k in keys_string.split(",") if k.strip()]
else:
    fallback_key = os.getenv("GEMINI_API_KEY") 
    VALID_KEYS = [fallback_key] if fallback_key else []

print(f"🔥 ACTIVE KEYS: {len(VALID_KEYS)}")

MODEL_NAME = "gemini-2.5-flash" 

async def generate_with_smart_rotation(content_parts):
    if not VALID_KEYS:
        raise Exception("No API Keys found! Check .env file.")
    shuffled_keys = random.sample(VALID_KEYS, len(VALID_KEYS))
    for key in shuffled_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            response = await model.generate_content_async(content_parts)
            return response
        except Exception as e:
            print(f"⚠️ Key Error: {e}")
            continue
    raise Exception("All keys failed.")

def extract_json(text):
    text = text.replace("```json", "").replace("```xml", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return text[start:end] if start != -1 else text

@app.post("/analyze-json")
async def analyze_json(
    file: UploadFile = File(...),
    country: str = Form("General"),
    industry: str = Form("General"),
    persona: str = Form("General User"),
    context_description: str = Form("")
):
    print(f"🚀 Analyzing: {country} | Bounding Box Mode")
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # 🔥 ULTRA HEATMAP PROMPT: บังคับให้สร้าง 40+ จุดและใช้ Bounding Box
        prompt = f"""
        **ROLE:**
        You are a World-Class UX Researcher and Eye-Tracking Algorithm Specialist for the **{country}** market.
        
        **OBJECTIVE:**
        Analyze the provided UI screenshot with extreme spatial precision (0-100 coordinate system).

        **TASK 1: GENERATE DENSE HEATMAP DATA (The "Hotjar" Effect)**
        - Simulate 3 seconds of user attention.
        - **Rules:** Users fixate on High Contrast > Faces > Big Numbers > Headlines > CTA Buttons.
        - **GENERATION STRATEGY:** 1. Identify the Top 3 focus areas (e.g., Main Headline, Hero Image Face, Primary Button).
          2. For EACH focus area, generate a **CLUSTER of 10-15 points** closely packed around the center (gaussian distribution).
          3. Add scattered points for secondary elements.
        - **OUTPUT:** You MUST generate at least **40-50 points** total. 
        - **INTENSITY:** Core points = 10, Edge of cluster = 5.

        **TASK 2: PRECISE UX AUDIT (Bounding Box Method)**
        - Identify 3-5 specific visual or cultural flaws.
        - **SPATIAL PRECISION:** To find (x,y), first imagine a bounding box around the error element.
        - Return the EXACT CENTER of that bounding box.
        - **Avoid:** Do not point to empty whitespace. Point to the UI element itself.

        **RESPONSE FORMAT (STRICT JSON ONLY):**
        {{
            "total_score": (Integer 0-100),
            "overview": "Professional summary.",
            "visual_issues": [
                {{
                    "description": "Short Title",
                    "explanation": "Why it's bad.",
                    "x": (0-100), "y": (0-100) 
                }}
            ],
            "heatmap_points": [
                {{ "x": (0-100), "y": (0-100), "intensity": (Integer 1-10) }},
                ... (Generate 40+ points here for dense clusters)
            ],
            "suggestions": ["Fix 1", "Fix 2"],
            "legal_compliance": {{ "gdpr": "Status" }}
        }}
        """
        
        response = await generate_with_smart_rotation([prompt, image])
        data = json.loads(extract_json(response.text))
        return data

    except Exception as e:
        print(f"🔥 Error: {e}")
        return {
            "total_score": 0, 
            "overview": f"Error: {str(e)}", 
            "visual_issues": [], 
            "heatmap_points": []
        }

@app.post("/fix")
async def fix_design(file: UploadFile = File(...), country: str = Form(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        prompt = f"Redesign UI for {country}. Output raw SVG code only."
        response = await generate_with_smart_rotation([prompt, image])
        return {"svg": extract_json(response.text)}
    except Exception as e:
        return {"svg": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)