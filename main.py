# --- main.py (แก้เฉพาะฟังก์ชัน analyze_ui) ---

@app.post("/analyze")
async def analyze_ui(file: UploadFile = File(...), country: str = "General", context: str = "App"):
    # ใช้ Model ตัวล่าสุดที่เราเทสผ่านเมื่อวาน
    target_model_name = 'gemini-2.5-flash' 
    
    global model
    model = genai.GenerativeModel(target_model_name)

    print(f"📥 Receiving file... Model: {target_model_name}")
    
    try:
        contents = await file.read()
        
        # 🔥🔥🔥 PROMPT ใหม่: สั่งให้โหด กระชับ และจัด Format HTML มาเลย 🔥🔥🔥
        prompt = f"""
        Act as a Strict UX & Cultural Audit AI. 
        Analyze this UI screenshot for target audience: {country}.
        Context: {context}.

        Your goal: Identify cultural mistakes and suggest fix immediately.
        
        RULES:
        1. Be extremely concise. No fluffy introduction.
        2. Use Thai language for output (ตอบเป็นภาษาไทย).
        3. Output MUST be raw HTML format (without ```html wrappers).
        4. Use specific CSS classes: <div class='score'>, <ul class='issues'>, <li class='fix'>.

        STRUCTURE THE RESPONSE LIKE THIS:
        
        <div class="score-container">
            <div class="score-label">Cultural Fit Score</div>
            <div class="score-value">[Score]/100</div>
        </div>

        <div class="section">
            <h3>🚨 สิ่งที่ต้องรีบแก้ (Critical)</h3>
            <ul class="issues">
                <li>
                    <strong>[Point 1]</strong>: [Why it is bad in {country}]
                    <div class="fix">💡 แก้โดย: [Specific Action]</div>
                </li>
                <li>
                    <strong>[Point 2]</strong>: [Why it is bad]
                    <div class="fix">💡 แก้โดย: [Specific Action]</div>
                </li>
            </ul>
        </div>

        <div class="section">
            <h3>✅ สิ่งที่ทำดีแล้ว (Keep it)</h3>
            <ul class="good">
                <li>[Point 1]</li>
                <li>[Point 2]</li>
            </ul>
        </div>
        """
        
        print("🤖 Sending to Gemini...")
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': contents},
            prompt
        ])
        
        # ล้าง Code block (เผื่อ AI เผลอใส่ ```html มา)
        clean_text = response.text.replace("```html", "").replace("```", "")
        
        return {"result": clean_text}

    except Exception as e:
        print("❌ Error:")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"AI Error: {str(e)}")