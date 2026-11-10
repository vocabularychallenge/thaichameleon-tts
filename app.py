import asyncio
import streamlit as st
import edge_tts

st.set_page_config(page_title='Thai Chameleon Book | Microsoft Voices', page_icon='🦎')
st.title('🦎 Thai Chameleon Book')
st.caption('Microsoft Neural Voices • English / 中文 / ไทย • MP3')
try:
    required_password = st.secrets.get('APP_PASSWORD')
except Exception:
    required_password = None
if required_password:
    password = st.text_input('รหัสผ่าน', type='password')
    if password != str(required_password):
        if password:
            st.error('รหัสผ่านไม่ถูกต้อง')
        st.stop()

voice_groups = {
    'English': {
        'Jenny (US) · Female': 'en-US-JennyNeural',
        'Michelle (US) · Female': 'en-US-MichelleNeural',
        'Aria (US) · Female': 'en-US-AriaNeural',
        'Ana (US) · Female': 'en-US-AnaNeural',
        'Sonia (UK) · Female': 'en-GB-SoniaNeural',
        'Libby (UK) · Female': 'en-GB-LibbyNeural',
        'Guy (US) · Male': 'en-US-GuyNeural',
    },
    '中文 · 普通话': {
        'Xiaoxiao · Female': 'zh-CN-XiaoxiaoNeural',
        'Xiaoyi · Female': 'zh-CN-XiaoyiNeural',
        'Yunxi · Male': 'zh-CN-YunxiNeural',
        'Yunjian · Male': 'zh-CN-YunjianNeural',
    },
    '中文 · 台灣': {
        'HsiaoChen · Female': 'zh-TW-HsiaoChenNeural',
        'YunJhe · Male': 'zh-TW-YunJheNeural',
    },
    'ภาษาไทย': {
        'Premwadee · ผู้หญิง': 'th-TH-PremwadeeNeural',
        'Niwat · ผู้ชาย': 'th-TH-NiwatNeural',
    },
}
language = st.selectbox('ภาษา', list(voice_groups))
voices = voice_groups[language]
voice_name = st.selectbox('เสียง Microsoft', list(voices))
rate_name = st.select_slider('ความเร็ว', ['Very slow', 'Slow', 'Normal', 'Fast'], value='Normal')
rates = {'Very slow': '-40%', 'Slow': '-20%', 'Normal': '+0%', 'Fast': '+20%'}
text = st.text_area('ข้อความที่ต้องการให้อ่าน', height=190, placeholder='พิมพ์หรือวางข้อความที่นี่', max_chars=3500)

async def synthesize(content, voice, rate):
    import tempfile, os
    fd, filename = tempfile.mkstemp(suffix='.mp3')
    os.close(fd)
    try:
        await edge_tts.Communicate(content, voice, rate=rate).save(filename)
        with open(filename, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if st.button('🎧 สร้างเสียง Microsoft', type='primary', use_container_width=True):
    if not text.strip():
        st.warning('กรุณาใส่ข้อความก่อน')
    else:
        try:
            with st.spinner('กำลังสร้างเสียง...'):
                audio = asyncio.run(synthesize(text.strip(), voices[voice_name], rates[rate_name]))
            if not audio:
                raise ValueError('Empty MP3')
            st.session_state['mp3'] = audio
            st.session_state['mp3_filename'] = f'ThaiChameleon_{voices[voice_name]}.mp3'
        except Exception:
            st.error('สร้างเสียงไม่สำเร็จ กรุณาตรวจสอบอินเทอร์เน็ตและลองใหม่')
if st.session_state.get('mp3'):
    st.audio(st.session_state['mp3'], format='audio/mp3')
    st.download_button('⬇️ ดาวน์โหลด MP3', st.session_state['mp3'], file_name=st.session_state['mp3_filename'], mime='audio/mpeg', use_container_width=True)
st.caption('ใช้ Microsoft Edge Neural TTS ผ่านอินเทอร์เน็ต ไม่ใช้เสียงในโทรศัพท์')
