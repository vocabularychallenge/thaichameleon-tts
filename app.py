import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import streamlit as st

st.set_page_config(page_title="แปลงตัวหนังสือเป็นเสียง", page_icon="🎧", layout="centered")
st.markdown("""<style>.block-container{max-width:780px;padding-top:1rem}div.stButton>button[kind=primary]{width:100%;min-height:3.2rem;border-radius:14px}textarea{font-size:1rem!important}</style>""",unsafe_allow_html=True)
st.title("🎧 แปลงตัวหนังสือเป็นเสียง")
st.caption("เลือกเสียงสองภาษาแยกกัน · อ่านต้นฉบับ แล้วอ่าน ‘แปลว่า ...’ ด้วยเสียงไทย · ดาวน์โหลด MP3")
VOICES={
 "🇬🇧 อังกฤษ":{"Jenny · หญิง":"en-US-JennyNeural","Michelle · หญิง":"en-US-MichelleNeural","Aria · หญิง":"en-US-AriaNeural","Ana · เด็กหญิง":"en-US-AnaNeural","Sonia · หญิง UK":"en-GB-SoniaNeural","Libby · หญิง UK":"en-GB-LibbyNeural","Guy · ชาย":"en-US-GuyNeural"},
 "🇹🇭 ไทย":{"Premwadee · หญิง":"th-TH-PremwadeeNeural","Niwat · ชาย":"th-TH-NiwatNeural"},
 "🇨🇳 จีน":{"Xiaoxiao · หญิง":"zh-CN-XiaoxiaoNeural","Xiaoyi · หญิง":"zh-CN-XiaoyiNeural","Yunxi · ชาย":"zh-CN-YunxiNeural","Yunjian · ชาย":"zh-CN-YunjianNeural"}
}
langs=list(VOICES)
left,right=st.columns(2)
with left:
    src_lang=st.selectbox("ภาษาที่อ่านก่อน",langs,index=0)
    src_voice=st.selectbox("เสียงอ่านต้นฉบับ",list(VOICES[src_lang]))
with right:
    target_choices=[x for x in langs if x!=src_lang]
    dst_lang=st.selectbox("ภาษาที่อ่านต่อ",target_choices,index=0)
    dst_voice=st.selectbox("เสียงอ่านคำแปล",list(VOICES[dst_lang]))
rate_choices={"ช้ามาก":"-35%","ช้า":"-20%","ปกติ":"+0%","เร็ว":"+15%"}
a,b=st.columns(2)
with a: rate_a=st.select_slider("ความเร็วต้นฉบับ",list(rate_choices),value="ปกติ")
with b: rate_b=st.select_slider("ความเร็วคำแปล",list(rate_choices),value="ปกติ")
layout=st.radio("รูปแบบการใส่ข้อความ",["สองภาษาในบรรทัดเดียว","แยกข้อความเป็นสองช่อง"],horizontal=True)
st.info("ใส่ได้ทั้ง ‘Dog - สุนัข’ และ ‘Dog แปลว่า สุนัข’ · ระบบยังไม่แปลภาษาให้อัตโนมัติ")
if layout.startswith("สองภาษา"):
    src=st.text_area("ข้อความต้นฉบับ - คำแปล (หนึ่งคู่ต่อบรรทัด)",height=240,placeholder="1. Dog แปลว่า สุนัข\n2. Cat - แมว\n3. Food Chain - ห่วงโซ่อาหาร")
    dst=""
else:
    src=st.text_area("ข้อความภาษาต้นฉบับ (หนึ่งบรรทัดต่อหนึ่งรายการ)",height=155)
    dst=st.text_area("ข้อความภาษาคำแปล (เรียงตามต้นฉบับ)",height=155)
thai_prefix=st.checkbox("ให้เสียงไทยพูดคำว่า ‘แปลว่า’ ก่อนคำแปล",value=True,disabled=(dst_lang!="🇹🇭 ไทย"))
pause=st.slider("เว้นจังหวะระหว่างเสียง (วินาที)",0.0,2.0,0.4,0.1)

def clean(s):return re.sub(r'^\s*\d+[.)]\s*','',s).strip()
def parse_pairs():
    if layout.startswith("สองภาษา"):
        rows=[]
        for line_no,line in enumerate(src.splitlines(),1):
            if not line.strip():continue
            parts=re.split(r'\s+แปลว่า\s+|\s+[-–—:]\s+',line,maxsplit=1)
            if len(parts)!=2 or not all(x.strip() for x in parts):
                raise ValueError(f"บรรทัด {line_no}: ใช้รูปแบบ Dog - สุนัข หรือ Dog แปลว่า สุนัข")
            rows.append((clean(parts[0]),parts[1].strip()))
        return rows
    a=[clean(x) for x in src.splitlines() if x.strip()]
    b=[clean(x) for x in dst.splitlines() if x.strip()]
    if len(a)!=len(b):raise ValueError(f"จำนวนบรรทัดไม่เท่ากัน: {len(a)} กับ {len(b)}")
    return list(zip(a,b))

async def make_voice(text,voice,rate,out):
    await edge_tts.Communicate(text,voice,rate=rate).save(str(out))
    if not out.exists() or out.stat().st_size<100:raise RuntimeError("บริการเสียงไม่ส่งไฟล์กลับมา")

async def create_tracks(pairs,folder,progress):
    files=[]
    for i,(original,translation) in enumerate(pairs):
        spoken_translation = ("แปลว่า " + re.sub(r"^แปลว่า\s*", "", translation).strip()) if dst_lang=="🇹🇭 ไทย" and thai_prefix else translation
        for label,text,voice,rate in [("a",original,VOICES[src_lang][src_voice],rate_choices[rate_a]),("b",spoken_translation,VOICES[dst_lang][dst_voice],rate_choices[rate_b])]:
            f=folder/f"{i:03d}_{label}.mp3"
            await make_voice(text,voice,rate,f)
            files.append(f)
        progress.progress((i+1)/len(pairs),text=f"สร้างแล้ว {i+1}/{len(pairs)} คู่")
    return files

def combine(files,folder,pause):
    # Concatenation through a demuxer avoids a giant filter graph for long vocabulary lists.
    silence=folder/'pause.mp3'
    if pause>0:
        r=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t',str(pause),'-c:a','libmp3lame','-b:a','64k',str(silence)],capture_output=True,text=True,timeout=30)
        if r.returncode:raise RuntimeError(r.stderr[-400:])
    playlist=folder/'playlist.txt'
    sequence=[]
    for i,f in enumerate(files):
        sequence.append(f)
        if pause>0 and i<len(files)-1:sequence.append(silence)
    playlist.write_text(''.join("file '"+f.as_posix()+"'\n" for f in sequence),encoding='utf-8')
    output=folder/'multilingual.mp3'
    r=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(playlist),'-c:a','libmp3lame','-b:a','96k',str(output)],capture_output=True,text=True,timeout=240)
    if r.returncode:raise RuntimeError(r.stderr[-400:])
    return output.read_bytes()

if st.button(f"🎧 สร้าง MP3: {src_lang} → {dst_lang}",type="primary"):
    try:
        pairs=parse_pairs()
        if not pairs:raise ValueError("กรุณาใส่ข้อความ")
        if len(pairs)>100:raise ValueError("กรุณาแบ่งข้อความไม่เกิน 100 คู่ต่อครั้ง")
        if any(len(x)>1000 or len(y)>1000 for x,y in pairs):raise ValueError("แต่ละช่องไม่ควรเกิน 1,000 ตัวอักษรต่อบรรทัด")
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            progress=st.progress(0,text="กำลังสร้างเสียง...")
            tracks=asyncio.run(create_tracks(pairs,folder,progress))
            st.session_state['audio']=combine(tracks,folder,pause)
            st.session_state['filename']='Multilingual_TTS.mp3'
            st.session_state['description']=f'{src_lang} → {dst_lang} · {len(pairs)} คู่'
            progress.empty()
    except Exception as e:
        st.error(f"สร้างเสียงไม่สำเร็จ: {e}")
        st.caption("ระบบใช้ Edge TTS แบบไม่เป็นทางการ จึงอาจเกิด NoAudioReceived หรือถูกจำกัดบริการได้")
if st.session_state.get('audio'):
    st.success('สร้างเสียงสำเร็จ: '+st.session_state['description'])
    st.audio(st.session_state['audio'],format='audio/mpeg')
    st.download_button('⬇️ ดาวน์โหลด MP3',st.session_state['audio'],file_name=st.session_state['filename'],mime='audio/mpeg',use_container_width=True)
st.caption("การเลือกภาษาเป็นการเลือกเสียงอ่าน ไม่ใช่การแปลอัตโนมัติ · ต้องใช้อินเทอร์เน็ต")
