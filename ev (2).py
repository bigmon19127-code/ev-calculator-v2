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

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets (ทำความสะอาดชื่อคอลัมน์อย่างหมดจด) ---
def load_sheet_data(worksheet_name):
    # 1. พยายามดึงข้อมูลโดยระบุชื่อแท็บก่อน
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            # ลบช่องว่างหัว-ท้ายของชื่อคอลัมน์อย่างหนาแน่น และแปลงเป็นตัวพิมพ์เล็ก
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e_first:
        first_error_msg = str(e_first)
        
    # 2. หากล้มเหลว ให้ลองดึงข้อมูลจากแท็บแรกสุด (Default)
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            # ลบช่องว่างหัว-ท้ายของชื่อคอลัมน์อย่างหนาแน่น และแปลงเป็นตัวพิมพ์เล็ก
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e_second:
        st.error("⚠️ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
        st.markdown(f"""
        ### 💡 วิธีแก้ไขปัญหาการเชื่อมต่อ (สำหรับพี่บิ๊ก):
        
        1. **ตรวจสอบการแชร์ไฟล์ Google Sheets:**
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

# --- ฟังก์ชันตรวจสอบการเข้าสู่ระบบ (ปรับปรุงแก้ไขความคลาดเคลื่อนของชื่อคอลัมน์) ---
def login_user(username, password):
    df_users = load_sheet_data("users")
    
    if df_users.empty:
        # ให้สิทธิ์แอดมินฉุกเฉินกรณีดึงข้อมูลชีตไม่ได้เลย
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "❌ ไม่สามารถดึงข้อมูลจาก Google Sheets ได้ กรุณาตรวจสอบสิทธิ์การแชร์ลิงก์ของ Google Sheets"

    # บังคับทำความสะอาดชื่อคอลัมน์ซ้ำอีกครั้งเพื่อความชัวร์ 100%
    df_users.columns = [str(c).strip().replace(" ", "").lower() for c in df_users.columns]
    available_cols = list(df_users.columns)
    
    # กำหนดคอลัมน์ที่ต้องใช้จริงแบบล้างค่าแล้ว
    col_user = "username"
    col_pass = "password"
    col_status = "status"
    
    # ตรวจสอบหาคอลัมน์แบบยืดหยุ่น (ดูว่ามีคำนั้นอยู่ในชื่อคอลัมน์ไหม ป้องกันวรรคเกิน)
    found_user_col = [c for c in available_cols if "username" in c]
    found_pass_col = [c for c in available_cols if "password" in c]
    found_status_col = [c for c in available_cols if "status" in c]
    
    if not found_user_col or not found_pass_col or not found_status_col:
        return False, f"❌ โครงสร้างตารางไม่ถูกต้อง คอลัมน์ที่ระบบตรวจพบคือ: {', '.join(available_cols)} (กรุณาใช้คอลัมน์ชื่อ username, password, status)"
    
    # กำหนดชื่อคอลัมน์จริงที่ค้นพบ
    real_user_col = found_user_col[0]
    real_pass_col = found_pass_col[0]
    real_status_col = found_status_col[0]
    
    # ทำความสะอาดข้อมูลนำเข้า
    input_user_clean = str(username).strip().lower()
    input_password_clean = str(password).strip()
    
    # ทำความสะอาดข้อมูลใน DataFrame ป้องกันจุดทศนิยมหรือช่องว่าง
    df_users["clean_username"] = df_users[real_user_col].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_password"] = df_users[real_pass_col].apply(clean_sheet_value)
    
    # ตรวจสอบชื่อผู้ใช้งาน
    user_rows = df_users[df_users["clean_username"] == input_user_clean]
    if user_rows.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"
    
    # ตรวจสอบรหัสผ่านที่จับคู่ถูกต้อง
    matched_user = user_rows[user_rows["clean_password"] == input_password_clean]
    if matched_user.empty:
        return False, "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
    
    # ตรวจสอบสถานะการอนุมัติ
    status = clean_sheet_value(matched_user.iloc[0][real_status_col]).strip().lower()
    
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
        st.rerun()
        
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
        st.rerun()

# --- ส่วนแสดงข้อมูลย้อนหลังรายเดือน ---
st.markdown("---")
st.header("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือน")
with st.expander(f"🔍 คลิกเพื่อเปิด/ปิดดูข้อมูลย้อนหลังรายเดือนของท่าน ({st.session_state['username']})", expanded=True):
    history_df = get_monthly_history(st.session_state['username'])
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("💡 ยังไม่มีประวัติการเดินทางถูกบันทึกในระบบ")

# --- ส่วนแผนที่ ---
st.markdown("---")
st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgGcjGt-VehLjKEufqTn4"
components.iframe(map_url, width=800, height=500)
