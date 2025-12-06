from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

# Check Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("❌ ERROR: No API Key found!")

genai.configure(api_key=GOOGLE_API_KEY)

# --- 🔥 ส่วนที่เพิ่มใหม่: เลือก Model อัตโนมัติ ---
# เราจะตั้งค่า Model เป็นตัวแปรไว้ก่อน แล้วค่อยกำหนดค่า
model = None 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🔥 ส่วนที่เพิ่มใหม่: Endpoint เช็กรายชื่อ Model ---
@app.get("/models")
def list_available_models():
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        return {"available_models": available}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    return {"status": "Server is running! 🚀 Go to /models to see available AI."}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # กำหนด Model ตรงนี้แทน (Hardcode ชื่อที่คิดว่าชัวร์สุดไปก่อน)
    # ถ้าอันนี้พัง เราจะไปดูรายชื่อใน /models แล้วค่อยมาแก้
    target_model_name = 'gemini-2.5-flash'
    
    global model
    model = genai.GenerativeModel(target_model_name)

    print(f"📥 Receiving file... Model: {target_model_name}")
    
    try:
        contents = await file.read()
        prompt = f"""
        Act as a UX Expert. Analyze this image for {country} culture in {context} context.
        Return HTML output with:
        - Score (0-100)
        - Critical Issues
        - Suggestions
        """
        
        print("🤖 Sending to Gemini...")
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        return {"result": response.text}

    except Exception as e:
        print("❌ Error:")
        traceback.print_exc() 
        # ส่ง Error กลับไปบอก Figma ด้วย จะได้ไม่ต้องดู Log บ่อยๆ
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")