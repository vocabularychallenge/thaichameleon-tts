import asyncio
import io
import re
import time
import zipfile
import streamlit as st
import edge_tts

st.set_page_config(page_title='Thai Chameleon Book | Microsoft Voices', page_icon='🦎')
st.title('🦎 Thai Chameleon Book')
st.caption('Microsoft Neural Voices • English / 中文 / ไทย • MP3 • Long text')
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
content = st.text_area('ข้อความที่ต้องการให้อ่าน (ไม่จำกัดจำนวนตัวอักษรในแอป)', height=240,
                       placeholder='พิมพ์หรือวางข้อความที่นี่')
st.caption(f'จำนวนตัวอักษร: {len(content):,} • ระบบจะแบ่งข้อความยาวเป็นช่วงอัตโนมัติ')

# Limit each individual Edge TTS request, not the overall user text.
def split_text(text, limit=1600):
    text = text.strip()
    if not text:
        return []
    # Preserve the original content, including punctuation and whitespace.
    parts = re.findall(r'.+?(?:[.!?。！？\n]+(?:\s+|$)|$)', text, flags=re.S)
    if not parts:
        parts = [text]
    result = []
    current = ''
    for part in parts:
        while len(part) > limit:
            if current:
                result.append(current)
                current = ''
            candidate = part[:limit]
            # Prefer a whitespace boundary when available.
            cut = max(candidate.rfind(' '), candidate.rfind('\n'))
            if cut < limit // 3:
                cut = limit
            else:
                cut += 1
            result.append(part[:cut])
            part = part[cut:]
        if len(current) + len(part) > limit:
            if current:
                result.append(current)
            current = part
        else:
            current += part
    if current:
        result.append(current)
    return [p for p in result if p.strip()]

async def synthesize_chunk(chunk, voice, rate):
    # Edge TTS returns encoded MP3 bytes. Each chunk can be saved independently.
    for attempt in range(3):
        try:
            data = bytearray()
            async for message in edge_tts.Communicate(chunk, voice, rate=rate).stream():
                if message['type'] == 'audio':
                    data.extend(message['data'])
            if not data:
                raise RuntimeError('Microsoft TTS returned no audio')
            return bytes(data)
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))

async def synthesize_all(parts, voice, rate, on_progress):
    audio_parts = []
    for index, part in enumerate(parts):
        audio_parts.append(await synthesize_chunk(part, voice, rate))
        on_progress(index + 1, len(parts))
    return audio_parts

if st.button('🎧 สร้างเสียง Microsoft', type='primary', use_container_width=True):
    if not content.strip():
        st.warning('กรุณาใส่ข้อความก่อน')
    else:
        st.session_state.pop('mp3', None)
        st.session_state.pop('mp3_zip', None)
        chunks = split_text(content)
        bar = st.progress(0, text=f'กำลังสร้างเสียง 0% • 0/{len(chunks)} ช่วง')
        percent_display = st.empty()
        percent_display.markdown('### 🎧 สร้างเสียงแล้ว 0%')
        def update(done, total):
            percent = round(done * 100 / total)
            bar.progress(percent, text=f'กำลังสร้างเสียง {percent}% • {done}/{total} ช่วง')
            percent_display.markdown(f'### 🎧 สร้างเสียงแล้ว {percent}%')
        try:
            pieces = asyncio.run(synthesize_all(chunks, voices[voice_name], rates[rate_name], update))
            # Concatenated MPEG audio frames are normally playable as a single MP3.
            combined = b''.join(pieces)
            st.session_state['mp3'] = combined
            st.session_state['mp3_filename'] = f'ThaiChameleon_{voices[voice_name]}.mp3'
            st.success(f'สร้างเสียงสำเร็จ 100% • {len(chunks)} ช่วง')
        except Exception as exc:
            st.error(f'สร้างเสียงไม่สำเร็จ: {type(exc).__name__}: {exc}')
            st.info('หากข้อความยาวมาก ลองแบ่งเป็นบทเพื่อหลีกเลี่ยงข้อจำกัดเวลาและหน่วยความจำของเซิร์ฟเวอร์')
if st.session_state.get('mp3'):
    st.audio(st.session_state['mp3'], format='audio/mp3')
    st.download_button('⬇️ ดาวน์โหลด MP3', st.session_state['mp3'],
                       file_name=st.session_state['mp3_filename'], mime='audio/mpeg',
                       use_container_width=True)
st.caption('ใช้ Microsoft Edge Neural TTS ผ่านอินเทอร์เน็ต ไม่ใช้เสียงในโทรศัพท์ • การสร้างข้อความยาวขึ้นอยู่กับข้อจำกัดของเซิร์ฟเวอร์และบริการ TTS')
