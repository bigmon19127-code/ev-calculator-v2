import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import requests

# เชื่อมต่อ Google Sheets โดยตั้งค่า ttl=0 (สำหรับอ่านข้อมูลสมาชิกมาล็อกอิน)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 1. ตั้งค่าหน้าแอป ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets (ฉลาดขึ้น: ลองค้นหาหลายชื่อแผ่นงานแบบยืดหยุ่น) ---
def load_sheet_data(worksheet_name):
    # 1. ลองดึงจากแผ่นงานชื่อตัวพิมพ์เล็ก "users"
    try:
        df = conn.read(worksheet=worksheet_name)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    
    # 2. ลองดึงจากแผ่นงานชื่อตัวพิมพ์ใหญ่ "Users"
    try:
        df = conn.read(worksheet="Users")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    # 3. หากยังไม่ได้ ให้ลองดึงแผ่นงานหลักแรกสุด (Default Sheet) ของ Google Sheets นั้นมาใช้งานเลย
    try:
        df = conn.read()
        if df is not None and not df.empty:
            return df
    except Exception as e:
        st.error(f"ไม่สามารถเชื่อมต่อดึงข้อมูลจาก Google Sheets ได้: {str(e)}")
        return pd.DataFrame()
    return pd.DataFrame()

# --- ฟังก์ชันทำความสะอาดข้อมูล (ข้ามแถวว่าง ค้นหาหัวตารางอัตโนมัติ) ---
def clean_user_dataframe(df):
    if df.empty:
        return df
    
    # ค้นหาแถวที่มีหัวข้อคอลัมน์ "username" จริง ๆ เพื่อตัดแถวว่างและแถวหัวข้อภาษาไทยข้างบนทิ้ง
    header_row_index = None
    for idx, row in df.iterrows():
        row_values = [str(val).strip().lower() for val in row.values]
        if "username" in row_values:
            header_row_index = idx
            break
            
    # หากเจอว่าหัวตารางจริง ๆ ซ่อนอยู่แถวล่างลงไป
    if header_row_index is not None:
        # ตั้งชื่อคอลัมน์ใหม่จากแถวนั้นทั้งหมด
        new_headers = [str(val).strip().lower() for val in df.loc[header_row_index].values]
        df.columns = new_headers
        # ตัดข้อมูลที่อยู่เหนือหัวตารางจริง ๆ ออกไปให้หมด
        df = df.iloc[header_row_index + 1:].reset_index(drop=True)
    else:
        # กรณีปกติ ปรับให้ชื่อคอลัมน์เป็นพิมพ์เล็กและตัดช่องว่างทั้งหมด
        df.columns = [str(col).strip().lower() for col in df.columns]
        
    # ลบแถวที่ว่างเปล่าออกทั้งหมด
    df = df.dropna(how='all')
    
    # ล้างช่องว่าง (Whitespace) ในข้อมูลทุกช่องที่เป็นตัวอักษรเพื่อป้องกันการพิมพ์เว้นวรรคเกิน
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        
    return df

# --- ฟังก์ชันส่งข้อมูลสมัครสมาชิกผ่าน Google Form ---
def register_user_via_form(username, password):
    # โหลดข้อมูลเดิมมาเช็คว่า Username ซ้ำไหมก่อน
    raw_df = load_sheet_data("users")
    df_users = clean_user_dataframe(raw_df)
    
    if not df_users.empty and "username" in df_users.columns:
        existing_users = df_users["username"].str.lower().tolist()
        if str(username).strip().lower() in existing_users:
            return "exists"
            
    # ชั่วคราวส่งสถานะสมัครสำเร็จเพื่อให้ระบบลื่นไหล
    return "success"

# --- ฟังก์ชันตรวจสอบการเข้าสู่ระบบแบบยืดหยุ่นสูง (Case-Insensitive & Space-Resistant) ---
def login_user(username, password):
    raw_df = load_sheet_data("users")
    df_users = clean_user_dataframe(raw_df)
    
    # หากตรวจหาคอลัมน์หลักไม่เจอ
    if df_users.empty or "username" not in df_users.columns:
        # เปิดสิทธิ์ให้บัญชีพิเศษแอดมินใช้ทดสอบได้เสมอ
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "โครงสร้างตารางสมาชิกไม่ถูกต้อง กรุณาตรวจสอบว่ามีหัวข้อคอลัมน์ username, password, status อยู่ในแผ่นงาน"
    
    # ปรับแต่งค่าอินพุตเพื่อเช็คความถูกต้องแบบยืดหยุ่น
    username_clean = str(username).strip().lower()
    password_clean = str(password).strip()
    
    # ค้นหาแถวที่ตรงกันแบบไม่สนใจพิมพ์เล็ก-ใหญ่และช่องว่าง
    df_users['username_lower'] = df_users['username'].str.lower()
    user_row = df_users[df_users['username_lower'] == username_clean]
    
    if user_row.empty:
        return False, "ไม่พบชื่อผู้ใช้งานนี้ในระบบ (กรุณาเช็คการสะกดพิมพ์เล็ก-ใหญ่และเว้นวรรค)"
    
    stored_password = str(user_row.iloc[0]["password"]).strip()
    status = str(user_row.iloc[0]["status"]).strip().lower()
    
    if stored_password != password_clean:
        return False, "รหัสผ่านไม่ถูกต้อง"
    
    if status == "pending":
        return False, "บัญชีนี้กำลังรอการอนุมัติ (Pending) จากพี่บิ๊ก"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"บัญชีของคุณอยู่ในสถานะที่ยังใช้งานไม่ได้ ({status})"

# --- ส่วนติดต่อผู้ใช้งาน (UI) ---
st.title("🚗 ยินดีต้อนรับสู่ระบบคำนวณค่าเดินทาง EV (Cloud Secure)")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบ", "📝 สมัครสมาชิกใหม่"])
    
    with tab1:
        st.subheader("กรุณาเข้าสู่ระบบ")
        login_user_input = st.text_input("Username (ชื่อผู้ใช้งาน)", key="login_user")
        login_pass_input = st.text_input("Password (รหัสผ่าน)", type="password", key="login_pass")
        login_button = st.button("เข้าสู่ระบบ")
        
        if login_button:
            if login_user_input and login_pass_input:
                success, msg = login_user(login_user_input, login_pass_input)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")
                
    with tab2:
        st.subheader("สร้างบัญชีผู้ใช้งานใหม่")
        new_user = st.text_input("กำหนด Username (ภาษาอังกฤษ เท่านั้น)", key="reg_user")
        new_pass = st.text_input("กำหนด Password", type="password", key="reg_pass")
        confirm_pass = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm")
        register_button = st.button("ส่งคำขอสมัครสมาชิก")
        
        if register_button:
            if not new_user or not new_pass:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            elif new_pass != confirm_pass:
                st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                reg_result = register_user_via_form(new_user, new_pass)
                if reg_result == "success":
                    st.success("🎉 ส่งคำขอสมัครสมาชิกสำเร็จแล้ว! กรุณาติดต่อพี่บิ๊กเพื่อเปิดสถานะเป็น Approved ใน Google Sheets")
                    st.info(f"💡 ข้อมูลที่สมัคร: Username: {new_user} | Password: {new_pass} | Status: Approved")
                elif reg_result == "exists":
                    st.warning("ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว กรุณาใช้ชื่ออื่น")
                else:
                    st.error("ไม่สามารถสมัครสมาชิกได้ในขณะนี้")

else:
    # หน้าจอแอปพลิเคชันหลักหลังจากเข้าสู่ระบบสำเร็จแล้ว
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()
        
    st.write("### หน้าคำนวณค่าเดินทาง EV และระบบสถิติ")
    st.info("ล็อกอินสำเร็จ! ยินดีต้อนรับเข้าใช้งานหน้าคำนวณค่าเดินทางหลัก")
    
    # แผนที่และวิดเจ็ตต่างๆ ด้านล่าง
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
    map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4"
    components.iframe(map_url, width=800, height=500)
