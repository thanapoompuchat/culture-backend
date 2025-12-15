from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
import re

load_dotenv()

github_token = os.environ.get("GITHUB_TOKEN")
# แนะนำให้ใช้รุ่น 90B ถ้า Token เหลือ เพราะฉลาดกว่ามากในการมอง Layout
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=github_token,
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "Culture AI Backend Optimized 🚀"}

# --- Utility Functions ---
def process_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        max_size = 1024 # ขยายให้ชัดขึ้นเพื่อให้ AI เห็น Detail
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=80) 
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Resize Error: {e}")
        return ""

def clean_and_repair_svg(raw_content):
    # ลบ Markdown
    content = raw_content.replace("```xml", "").replace("```svg", "").replace("```", "")
    # หา SVG block
    match = re.search(r"(<svg[\s\S]*?</svg>)", content, re.IGNORECASE | re.DOTALL)
    if match:
        svg_code = match.group(1)
        # ฆ่า Tag ที่ Figma เกลียด
        forbidden_tags = ['foreignObject', 'script', 'iframe', 'style']
        for tag in forbidden_tags:
            svg_code = re.sub(f'<{tag}[\s\S]*?</{tag}>', '', svg_code, flags=re.IGNORECASE)
        return svg_code
    return None

# --- 🎨 Cultural Design System (The Brain) ---
def get_cultural_rules(country):
    rules = {
        "Thailand": {
            "vibe": "Fun, Colorful, Accessible, High Information Density.",
            "colors": "Use vibrant colors: Orange (#FF9F1C), Bright Blue (#2EC4B6), or Pink (#FF99C8). Background: #FFFFFF or Light Cream.",
            "layout": "Grid-based, clearly defined borders, rounded corners (rx='8').",
            "text": "Large headings, clear contrast."
        },
        "Japan": {
            "vibe": "Minimalist, Clean, High Information Density but organized, Trustworthy.",
            "colors": "Use Soft colors: White, Light Grey (#F5F5F5), Muted Blue (#3D5A80), Soft Red accent.",
            "layout": "Tight grid, thin borders (stroke-width='1'), distinct sections, smaller text size but more content.",
            "text": "Clean sans-serif, high readability."
        },
        "USA": {
            "vibe": "Bold, clean, lots of whitespace, Direct.",
            "colors": "High contrast: Black, White, Royal Blue (#1D4ED8).",
            "layout": "Spacious, big hero sections, large buttons, less dense.",
            "text": "Very large headings, strong hierarchy."
        },
        "China": {
            "vibe": "Festive, dense, complex, Super-app style.",
            "colors": "Red (#D32F2F), Gold (#FFA000), White.",
            "layout": "Very dense grid, many small icons, complex navigation bars.",
            "text": "Compact text."
        }
    }
    return rules.get(country, rules["USA"])

# --- Endpoint Fix ---
@app.post("/fix")
async def fix_ui(
    file: UploadFile = File(...), 
    country: str = Form(...), 
    width: str = Form("1440"),    
    height: str = Form("1024"),
    translate_text: str = Form("false"),
    keep_layout: str = Form("true")
):
    is_keep_layout = keep_layout.lower() == 'true'
    is_translate = translate_text.lower() == 'true'
    
    culture_data = get_cultural_rules(country)
    contents = await file.read()
    image_uri = process_image(contents)

    print(f"🚀 Processing: {country} | Keep Layout: {is_keep_layout}")

    # --- 🧠 Prompt Strategy Split ---
    
    if is_keep_layout:
        # 👉 Strategy 1: TRACING (คงโครงสร้างเดิมเป๊ะ)
        system_instruction = "You are an expert SVG Reproduction Engine. Your goal is to CLONE the layout structure."
        prompt = f"""
        Analyze the uploaded image. Recreate the EXACT layout structure as valid SVG code.
        Canvas: width="{width}" height="{height}"
        
        STRICT OBJECTIVE:
        1. Look at the image: If there is a grid of 8 cards, DRAW A GRID OF 8 CARDS using <rect>.
        2. Do not simplify into a list. Maintain the x, y positions relative to the canvas.
        3. Abstract the content: Replace complex images with colored <rect> placeholders.
        
        APPLY CULTURAL STYLING ({country}):
        - {culture_data['colors']}
        - {culture_data['layout']}
        
        SVG RULES:
        - Use ONLY <rect>, <circle>, <text>, <g>. No foreignObject.
        - Group elements logically (e.g., <g id="card-1">...</g>).
        - Use simple shapes to represent the UI.
        
        OUTPUT FORMAT:
        Only raw SVG XML string. No markdown.
        """
    else:
        # 👉 Strategy 2: REDESIGN (รื้อทำใหม่)
        system_instruction = "You are a World-Class UI Designer. Redesign this interface."
        prompt = f"""
        Redesign the UI in the image to fit the cultural context of {country}.
        Canvas: width="{width}" height="{height}"
        
        CULTURAL RULES for {country}:
        - Vibe: {culture_data['vibe']}
        - Colors: {culture_data['colors']}
        - Layout: {culture_data['layout']}
        
        INSTRUCTIONS:
        1. Identify the key content (Header, Footer, Main Grid/Content).
        2. Rearrange them to suit {country}'s UX patterns.
        3. Create a High-Fidelity Wireframe using SVG shapes.
        
        SVG RULES:
        - Start with <rect width="100%" height="100%" fill="background_color"/>
        - Use <rect> for cards/buttons.
        - Use <text> for labels.
        - Ensure elements are properly aligned.
        
        OUTPUT FORMAT:
        Only raw SVG XML string. No markdown.
        """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}
            ],
            model="Llama-3.2-90B-Vision-Instruct", # แนะนำ 90B เพื่อความฉลาดในการแกะ Layout
            temperature=0.2, 
            max_tokens=4000,
        )
        
        clean_svg = clean_and_repair_svg(response.choices[0].message.content)
        
        if clean_svg:
            return {"svg": clean_svg}
        else:
            return {"svg": f'<svg width="{width}" height="{height}"><rect width="100%" height="100%" fill="#eee"/><text x="50%" y="50%" text-anchor="middle">AI Failed to Generate Valid SVG</text></svg>'}

    except Exception as e:
        print(f"Error: {e}")
        return {"svg": ""}

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = Form(...), context: str = Form(...)):
    # (Analyze Code เดิม ใช้ได้ดีอยู่แล้ว)
    try:
        contents = await file.read()
        image_uri = process_image(contents)
        prompt = f"Analyze this UI for {country} culture context {context}. Output HTML: <div class='score'>Score</div><div class='issues'>Issues</div><div class='suggestions'>Suggestions</div>"
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_uri}}]}],
            model="Llama-3.2-90B-Vision-Instruct", max_tokens=1000,
        )
        return {"result": response.choices[0].message.content.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"result": f"Error: {e}"}