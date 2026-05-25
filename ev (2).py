import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. ตั้งค่าหน้าแอป (ต้องอยู่บรรทัดแรกสุด) ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- 2. ตั้งค่าระบบฐานข้อมูล ---
def init_db():
    conn = sqlite3.connect("travel_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS trips 
                      (id INTEGER PRIMARY KEY, user_id TEXT, trip_date TEXT, 
                       vehicle_type TEXT, distance REAL, total_cost REAL)''')
    conn.commit()
    conn.close()

def save_trip(user_id, vehicle_type, distance, total_cost):
    conn = sqlite3.connect("travel_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trips (user_id, trip_date, vehicle_type, distance, total_cost) VALUES (?, ?, ?, ?, ?)",
                   (user_id, datetime.now().strftime("%Y-%m-%d %H:%M"), vehicle_type, distance, total_cost))
    conn.commit()
    conn.close()

init_db()

# --- 3. ระบบ Login แบบ Custom (เสถียร 100% ไม่พึ่งพาภายนอก) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

def login_user(username, password):
    # กำหนดรหัสผ่านตรงนี้ได้เลย
    if username == "vip" and password == "1234":
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        return True
    return False

def logout_user():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

# --- ตรวจสอบสถานะก่อนแสดงหน้าหลัก ---
if not st.session_state['logged_in']:
    st.title("🔒 เข้าสู่ระบบ")
    with st.form("login_form"):
        st.write("กรุณากรอก Username และ Password")
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if login_user(user_input, pass_input):
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun()
            else:
                st.error("Username หรือ Password ไม่ถูกต้อง (ลองใช้: vip / 1234)")
    st.stop() # หยุดการทำงานตรงนี้ถ้ายังไม่ Login

# ==========================================
# --- 4. เนื้อหาโปรแกรมหลัก (เมื่อ Login ผ่านแล้ว) ---
# ==========================================

# ปุ่ม Logout ด้านข้าง
st.sidebar.button("🚪 ออกจากระบบ", on_click=logout_user)
st.sidebar.markdown(f"👤 เข้าสู่ระบบในชื่อ: **{st.session_state['username']}**")

st.title(f'🚗 ระบบคำนวณค่าเดินทาง & แชร์พิกัด EV')

# --- ส่วนเครื่องคำนวณ ---
st.header("💰 เครื่องคำนวณค่าใช้จ่าย")
col1, col2 = st.columns(2)
with col1:
    st.subheader("⛽ ค่าน้ำมัน")
    dist = st.number_input("ระยะทาง (กม.)", value=155.0, key="dist_oil")
    cons = st.number_input("อัตราสิ้นเปลือง (กม./ลิตร)", value=14.0)
    price = st.number_input("ราคาน้ำมัน (บาท/ลิตร)", value=38.5)
    
    if st.button("คำนวณและบันทึก (น้ำมัน)", type="primary"):
        total_oil = (dist/cons)*price
        st.success(f"ค่าน้ำมันประมาณ: {total_oil:,.2f} บาท")
        save_trip(st.session_state['username'], "รถน้ำมัน", dist, total_oil)
        st.info("✅ บันทึกข้อมูลลงฐานข้อมูลเรียบร้อย")
        
with col2:
    st.subheader("⚡ ค่าไฟ EV")
    dist_ev = st.number_input("ระยะทาง EV (กม.)", value=155.0, key="dist_ev")
    eff = st.number_input("อัตรากินไฟ (กม./หน่วย)", value=5.5)
    price_ev = st.number_input("ค่าไฟ (บาท/หน่วย)", value=4.7)
    
    if st.button("คำนวณและบันทึก (EV)", type="primary"):
        total_ev = (dist_ev/eff)*price_ev
        st.success(f"ค่าไฟ EV ประมาณ: {total_ev:,.2f} บาท")
        save_trip(st.session_state['username'], "รถไฟฟ้า", dist_ev, total_ev)
        st.info("✅ บันทึกข้อมูลลงฐานข้อมูลเรียบร้อย")

# --- ส่วนแผนที่ (Embed) ---
st.markdown("---")
st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgGcjGt-VehLjKEufqTn4"
# ใช้ st.components.v1.iframe เพื่อฝังแผนที่ลงในหน้าเว็บ
components.iframe(map_url, width=800, height=500)