import asyncio
import io
import os
import re
import time
import zipfile
import streamlit as st
import edge_tts

st.set_page_config(page_title='Thai Chameleon Book | Microsoft TTS', page_icon='🦎', layout='centered')
st.title('🦎 Thai Chameleon Book')
st.caption('Microsoft Neural TTS • English / 中文 / ไทย • MP3')

GROUPS = {
 'English': {'Jenny · หญิง':'en-US-JennyNeural','Michelle · หญิง':'en-US-MichelleNeural','Aria · หญิง':'en-US-AriaNeural','Ana · เด็กหญิง':'en-US-AnaNeural','Sonia · หญิง UK':'en-GB-SoniaNeural','Libby · หญิง UK':'en-GB-LibbyNeural','Guy · ชาย':'en-US-GuyNeural'},
 '中文 · 普通话': {'Xiaoxiao · 女':'zh-CN-XiaoxiaoNeural','Xiaoyi · 女':'zh-CN-XiaoyiNeural','Yunxi · 男':'zh-CN-YunxiNeural','Yunjian · 男':'zh-CN-YunjianNeural'},
 '中文 · 台灣': {'HsiaoChen · 女':'zh-TW-HsiaoChenNeural','YunJhe · 男':'zh-TW-YunJheNeural'},
 'ภาษาไทย': {'Premwadee · หญิง':'th-TH-PremwadeeNeural','Niwat · ชาย':'th-TH-NiwatNeural'}
}
lang = st.selectbox('ภาษา', list(GROUPS))
voice_label = st.selectbox('เสียง Microsoft', list(GROUPS[lang]))
voice = GROUPS[lang][voice_label]
rate_label = st.select_slider('ความเร็ว', ['Very slow','Slow','Normal','Fast'], value='Normal')
rate = {'Very slow':'-40%','Slow':'-20%','Normal':'+0%','Fast':'+20%'}[rate_label]
content = st.text_area('ข้อความ', height=180, max_chars=30000, placeholder='วางข้อความภาษาอังกฤษ จีน หรือไทย')
st.caption(f'จำนวนอักขระ: {len(content):,} • ระบบแบ่งข้อความยาวเป็นช่วงให้อัตโนมัติ')

# Chunk at punctuation/whitespace boundaries; never cut through words unnecessarily.
def split_text(value, limit=850):
    value = value.strip()
    if not value:
        return []
    parts = []
    while len(value) > limit:
        region = value[:limit]
        candidates = [region.rfind(sep) for sep in ['\n','。','！','？','. ','! ','? ','；','; ', '，', ', ', ' ']]
        cut = max(candidates)
        if cut < limit // 3:
            cut = limit
        else:
            cut += 1
        parts.append(value[:cut].strip())
        value = value[cut:].strip()
    if value:
        parts.append(value)
    return parts

async def make_chunk(text, voice, rate):
    # Network hiccups are common; retry only temporary errors.
    for attempt in range(3):
        buffer = bytearray()
        try:
            async def receive():
                async for event in edge_tts.Communicate(text, voice, rate=rate).stream():
                    if event.get('type') == 'audio':
                        buffer.extend(event.get('data', b''))
            await asyncio.wait_for(receive(), timeout=65)
            if not buffer:
                raise RuntimeError('NoAudioReceived: empty audio stream')
            return bytes(buffer)
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))

async def synthesize_all(chunks, voice, rate, progress):
    result = []
    for i, part in enumerate(chunks):
        audio = await make_chunk(part, voice, rate)
        result.append(audio)
        progress.progress((i+1)/len(chunks), text=f'สร้างเสียงแล้ว {i+1}/{len(chunks)} ช่วง')
    return result

if st.button('🎧 สร้างเสียง Microsoft', type='primary', use_container_width=True):
    if not content.strip():
        st.warning('กรุณาใส่ข้อความก่อน')
    else:
        chunks = split_text(content)
        if len(chunks) > 40:
            st.error('ข้อความยาวเกินไป กรุณาแบ่งงานเป็นชุดละไม่เกินประมาณ 30,000 อักขระ')
        else:
            bar = st.progress(0, text=f'เริ่มสร้างเสียง 0/{len(chunks)} ช่วง')
            try:
                audios = asyncio.run(synthesize_all(chunks, voice, rate, bar))
                st.session_state['audio_parts'] = audios
                st.session_state['voice'] = voice
                st.session_state['error'] = None
                st.success(f'สร้างเสียงสำเร็จ {len(audios)} ช่วง')
            except Exception as exc:
                st.session_state.pop('audio_parts', None)
                st.session_state['error'] = type(exc).__name__
                st.error('Microsoft Edge TTS ไม่ส่งเสียงกลับมาในขณะนี้ (อาจเป็นปัญหาบริการหรือการเชื่อมต่อของเซิร์ฟเวอร์)')
                st.info('ลองข้อความสั้น ๆ และเสียง Jenny อีกครั้ง หากยังล้มเหลว ปัญหาไม่ได้เกิดจากจำนวนอักขระ การแบ่งข้อความหรือการกดซ้ำไม่สามารถแก้การบล็อกบริการต้นทางได้')

if st.session_state.get('audio_parts'):
    parts = st.session_state['audio_parts']
    st.subheader('▶ ฟังเสียง')
    for idx, part in enumerate(parts):
        if len(parts) > 1:
            st.caption(f'ช่วงที่ {idx+1}/{len(parts)}')
        st.audio(part, format='audio/mpeg')
    if len(parts) == 1:
        st.download_button('⬇️ ดาวน์โหลด MP3', parts[0], file_name=f'ThaiChameleon_{st.session_state["voice"]}.mp3', mime='audio/mpeg', use_container_width=True)
    else:
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', compression=zipfile.ZIP_STORED) as archive:
            for idx, part in enumerate(parts, 1):
                archive.writestr(f'ThaiChameleon_{idx:02d}.mp3', part)
        st.download_button('⬇️ ดาวน์โหลด MP3 ทุกช่วง (ZIP)', mem.getvalue(), file_name='ThaiChameleon_MP3_Parts.zip', mime='application/zip', use_container_width=True)
        st.caption('ไฟล์ยาวแบ่งเป็น MP3 หลายช่วง เพื่อหลีกเลี่ยงปัญหาการต่อ MP3 ที่ไม่สมบูรณ์')

st.caption('ใช้บริการ Microsoft Edge TTS ผ่านอินเทอร์เน็ต ไม่ใช้เสียง TTS ในโทรศัพท์ • การทำงานขึ้นอยู่กับความพร้อมของบริการต้นทาง')
