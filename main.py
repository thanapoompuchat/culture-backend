from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# โหลดตัวแปรจาก .env (ถ้ามี)
load_dotenv()

app = FastAPI()

# ตั้งค่า CORS (เพื่อให้หน้าเว็บเรียกใช้ได้)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ตั้งค่า Google Gemini API
# (บน Render อย่าลืมไปใส่ Environment Variable ชื่อ GEMINI_API_KEY นะครับ)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
def read_root():
    return {"message": "Culture AI Backend is Running!"}

@app.post("/analyze-json")
async def analyze_img_json(
    file: UploadFile = File(...),
    country: str = Form(...),
    device: str = Form("mobile"),      # <--- รับค่า Device
    context: str = Form("")            # <--- รับรายละเอียดเพิ่มเติม
):
    try:
        # 1. อ่านไฟล์รูปภาพ
        content = await file.read()
        image_part = {"mime_type": file.content_type, "data": content}

        # 2. สร้าง Prompt ส่งให้ AI (รวมค่า Device และ Context เข้าไป)
        prompt = f"""
        You are an expert UI/UX Designer specialized in Localization and Cross-cultural design.
        Analyze this UI design for a target audience in: {country}.
        
        Context Information:
        - Device Platform: {device} (Start by checking if the layout/spacing fits a {device} screen)
        - Design Description/Context: {context if context else "No specific context provided"}

        Please output ONLY raw JSON (no markdown, no ```json) with this structure:
        {{
            "score": (0-100 integer),
            "culture_fit_level": "High/Medium/Low",
            "suggestions": ["list of 3-5 specific actionable improvements regarding culture and {device} usability"],
            "color_palette_analysis": "Analysis of colors for {country}",
            "layout_analysis": "Analysis of layout/UX for {country} on {device}"
        }}
        """

        # 3. ส่งข้อมูลให้ Gemini
        response = model.generate_content([prompt, image_part])
        
        # 4. แปลงผลลัพธ์เป็น JSON
        json_str = response.text.strip()
        # ลบ markdown ```json ออกถ้ามี
        if json_str.startswith("```json"):
            json_str = json_str[7:-3]
        elif json_str.startswith("```"):
            json_str = json_str[3:-3]
            
        return json.loads(json_str)

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}