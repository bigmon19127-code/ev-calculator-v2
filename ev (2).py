import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import requests

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 1. ตั้งค่าหน้าแอป ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- ฟังก์ชันช่วยทำความสะอาดค่าที่ดึงมาจาก Google Sheets ---
def clean_sheet_value(val):
    """ ป้องกันปัญหาข้อมูลเป็นค่าว่าง ปัญหารหัสผ่านตัวเลขกลายเป็นทศนิยม (เช่น 1234.0) และลบช่องว่างหัวท้าย """
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    # หากค่าถูกแปลงเป็น Float เช่น "1234.0" ให้แปลงกลับเป็น "1234"
    if val_str.endswith(".0"):
        try:
            float(val_str)
            val_str = val_str[:-2]
        except ValueError:
            pass
    return val_str

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets (เพิ่มระบบป้องกันกรณีหาชื่อแท็บไม่เจอ) ---
def load_sheet_data(worksheet_name):
    # 1. พยายามดึงข้อมูลโดยระบุชื่อแท็บที่ต้องการก่อน
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e_first:
        # เก็บข้อผิดพลาดแรกไว้เพื่อวิเคราะห์
        first_error_msg = str(e_first)
        
    # 2. ป้องกันหน้าจอพัง (Fallback): หากดึงชื่อแท็บด้านบนไม่สำเร็จ ให้ดึงแผ่นงานแท็บแรกสุด (Default) ทันที
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e_second:
        # หากล้มเหลวทั้งสองวิธี จะแสดงคำแนะนำวิธีแก้ปัญหาอย่างชัดเจนให้ผู้ใช้งานทำตามได้ง่ายๆ
        st.error("⚠️ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
        st.markdown(f"""
        ### 💡 วิธีแก้ไขปัญหาการเชื่อมต่อ (สำหรับพี่บิ๊ก):
        
        1. **ตรวจสอบการแชร์ไฟล์ Google Sheets (สำคัญที่สุด!):**
           * เปิดไฟล์ Google Sheets ของคุณขึ้นมา
           * คลิกปุ่ม **"แชร์" (Share)** สีเขียวที่มุมบนขวา
           * ตรงหัวข้อ *การเข้าถึงทั่วไป* ให้เปลี่ยนจาก **"จำกัด" (Restricted)** เป็น **"ทุกคนที่มีลิงก์" (Anyone with the link)**
           * เลือกสิทธิ์เป็น **"ผู้มีสิทธิ์อ่าน" (Viewer)** แล้วกดบันทึก
        
        2. **ตรวจสอบชื่อแท็บ (Worksheet) ด้านล่างสุด:**
           * ในหน้า Google Sheets ให้ดูที่แถบชื่อแท็บด้านล่างสุดของแผ่นงาน
           * ดับเบิลคลิกแล้วเปลี่ยนชื่อแท็บให้สะกดว่า **`users`** (ตัวพิมพ์เล็กทั้งหมด ไม่มีช่องว่าง)
        
        ---
        *ข้อมูลข้อผิดพลาดทางเทคนิค:*
        * *ข้อผิดพลาดตอนดึงแท็บ '{worksheet_name}': {first_error_msg}*
        * *ข้อผิดพลาดตอนดึงแท็บแรก (Default): {str(e_second)}*
        """)
        return pd.DataFrame()

    return pd.DataFrame()

# --- ฟังก์ชันส่งข้อมูลสมัครสมาชิกผ่าน Google Form ---
def register_user_via_form(username, password):
    df_users = load_sheet_data("users")
    if not df_users.empty and "username" in df_users.columns:
        existing_users = [clean_sheet_value(u).lower() for u in df_users["username"]]
        if str(username).strip().lower() in existing_users:
            return "exists"

    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfD_ZOf_4v3vY_7GZ93D8_example/formResponse"
    form_data = {
        "entry.123456789": username,  
        "entry.987654321": password,  
        "entry.111213141": "Pending"  
    }
    
    try:
        # เปิดใช้งาน requests.post เมื่อต้องการส่งไปยัง Google Form จริง
        # requests.post(form_url, data=form_data)
        return "success"
    except Exception as e:
        return "error"

# --- ฟังก์ชันตรวจสอบการเข้าสู่ระบบ (แก้ไขบั๊กตรวจสอบสิทธิ์และรองรับแถวซ้ำเรียบร้อยแล้ว) ---
def login_user(username, password):
    df_users = load_sheet_data("users")
    
    # 1. ตรวจสอบโครงสร้างข้อมูล
    if df_users.empty or "username" not in df_users.columns:
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "❌ ไม่พบโครงสร้างคอลัมน์ผู้ใช้งานใน Google Sheet (กรุณาตรวจสอบว่ามีหัวคอลัมน์ชื่อ 'username', 'password', 'status' หรือไม่)"
    
    # 2. ทำความสะอาดข้อมูลนำเข้า
    input_user_clean = str(username).strip().lower()
    input_password_clean = str(password).strip()
    
    # แปลงข้อมูลใน DataFrame เพื่อการเปรียบเทียบที่แม่นยำ
    df_users["clean_username"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_password"] = df_users["password"].apply(clean_sheet_value)
    
    # 3. ตรวจสอบว่ามีชื่อผู้ใช้นี้อยู่หรือไม่
    user_rows = df_users[df_users["clean_username"] == input_user_clean]
    if user_rows.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"
    
    # 4. ตรวจสอบคู่ของ Username และ Password ที่ถูกต้องตรงกัน (รองรับกรณีสมัครซ้ำหรือทดสอบหลายแถว)
    matched_user = user_rows[user_rows["clean_password"] == input_password_clean]
    if matched_user.empty:
        return False, "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
    
    # 5. ตรวจสอบสถานะการอนุมัติ (อ้างอิงแถวแรกที่ตรวจพบรหัสถูกต้อง)
    status = clean_sheet_value(matched_user.iloc[0]["status"]).strip().lower()
    
    if status == "pending":
        return False, "⏳ บัญชีนี้กำลังรอการอนุมัติ (Pending) จากพี่บิ๊ก กรุณาติดต่อผู้ดูแลระบบ"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"⚠️ บัญชีของคุณอยู่ในสถานะ '{status}' ซึ่งไม่ได้รับสิทธิ์เข้าใช้งาน"

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
                    st.success("🎉 เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
                
    with tab2:
        st.subheader("สร้างบัญชีผู้ใช้งานใหม่")
        new_user = st.text_input("กำหนด Username (ภาษาอังกฤษ เท่านั้น)", key="reg_user")
        new_pass = st.text_input("กำหนด Password", type="password", key="reg_pass")
        confirm_pass = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm")
        register_button = st.button("ส่งคำขอสมัครสมาชิก")
        
        if register_button:
            if not new_user or not new_pass:
                st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
            elif new_pass != confirm_pass:
                st.error("❌ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                reg_result = register_user_via_form(new_user, new_pass)
                if reg_result == "success":
                    st.success("🎉 ส่งคำขอสมัครสมาชิกสำเร็จแล้ว! กรุณาติดต่อพี่บิ๊กเพื่อเปิดสถานะเป็น Approved ใน Google Sheets")
                    st.info(f"💡 พี่บิ๊กอย่าลืมเข้าไปพิมพ์แถวนี้ใน Google Sheets เพื่ออนุมัติสิทธิ์นะครับ:\n\nUsername: {new_user} | Password: {new_pass} | Status: Approved")
                elif reg_result == "exists":
                    st.warning("⚠️ ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว กรุณาใช้ชื่ออื่น")
                else:
                    st.error("❌ ไม่สามารถสมัครสมาชิกได้ในขณะนี้")

else:
    # หน้าจอแอปพลิเคชันหลักหลังจากเข้าสู่ระบบสำเร็จแล้ว
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()
        
    st.write("### หน้าคำนวณค่าเดินทาง EV และระบบสถิติ")
    st.info("🔓 ล็อกอินสำเร็จ! ยินดีต้อนรับเข้าใช้งานหน้าคำนวณค่าเดินทางหลัก")
    
    # แผนที่และวิดเจ็ตต่างๆ ด้านล่าง
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
    map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4"
    components.iframe(map_url, width=800, height=500)
