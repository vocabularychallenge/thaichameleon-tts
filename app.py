import streamlit as st
import asyncio
import edge_tts
import os

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Thai Chameleon Book - TTS", page_icon="🔊", layout="centered")

st.title("🔊 Thai Chameleon Book: ระบบสร้างเสียง MP3")
st.write("พิมพ์บทเรียนหรือข้อความภาษาอังกฤษ แล้วแปลงเป็นไฟล์เสียง MP3 ได้ทันที")

# ระบบเช็ครหัสผ่าน
password = st.text_input("กรุณากรอกรหัสผ่านเพื่อเข้าใช้งาน:", type="password")

if password != "1978":
    if password != "":
        st.error("❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
    st.stop()  # หยุดการทำงานด้านล่างทั้งหมดจนกว่าจะใส่รหัสถูก

st.success("✅ รหัสผ่านถูกต้อง! ยินดีต้อนรับเข้าสู่ระบบ")

# ช่องกรอกข้อความ
text_input = st.text_area("วางข้อความภาษาอังกฤษที่นี่:", height=150, placeholder="Hello! Welcome to Little Writers...")

# ตั้งค่าเสียง (เลือกเสียงและระดับความเร็วได้)
voice_option = st.selectbox("เลือกเสียงผู้พูด:", ["en-US-JennyNeural", "en-US-AriaNeural", "en-US-GuyNeural"])
rate_option = st.selectbox("ความเร็วเสียง:", ["ปกติ (0%)", "ช้าลง (-10%)", "ช้าลงมาก (-20%)"])

# แปลงค่าความเร็วเป็นคำสั่ง
rate_value = "-10%"
if "0%" in rate_option:
    rate_value = "+0%"
elif "-20%" in rate_option:
    rate_value = "-20%"

# ปุ่มกดสร้างเสียง
if st.button("🚀 แปลงข้อความและสร้างไฟล์เสียง MP3", type="primary"):
    if not text_input.strip():
        st.warning("⚠️ กรุณากรอกข้อความก่อนกดแปลงเสียงครับ!")
    else:
        output_file = "output_audio.mp3"
        
        with st.spinner("⏳ กำลังสังเคราะห์เสียง โปรดรอสักครู่..."):
            async def generate():
                communicate = edge_tts.Communicate(text_input, voice_option, rate=rate_value)
                await communicate.save(output_file)
            
            asyncio.run(generate())
        
        st.success("🎉 สร้างไฟล์เสียงสำเร็จเรียบร้อยแล้ว!")
        
        # เปิดให้กดฟังและกดดาวน์โหลด
        audio_file = open(output_file, "rb")
        audio_bytes = audio_file.read()
        
        st.audio(audio_bytes, format="audio/mp3")
        
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ MP3 ลงเครื่อง",
            data=audio_bytes,
            file_name="ThaiChameleon_Lesson.mp3",
            mime="audio/mp3"
        )