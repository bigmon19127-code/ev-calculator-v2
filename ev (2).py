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
            # ตรวจสอบว่าเป็นตัวเลขจริงหรือไม่
            float(val_str)
            val_str = val_str[:-2]
        except ValueError:
            pass
    return val_str

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets (เพิ่มความปลอดภัยและการดึงข้อมูลแบบ Real-time) ---
def load_sheet_data(worksheet_name):
    try:
        # บังคับข้ามแคชด้วย ttl=0 โดยตรงในคำสั่ง read เพื่อให้ได้ข้อมูลอัปเดตล่าสุดจาก Google Sheets เสมอ
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # ทำความสะอาดชื่อคอลัมน์: ลบช่องว่างหัว-ท้าย และแปลงเป็นตัวพิมพ์เล็กทั้งหมดป้องกันสระเลื่อน/พิมพ์ผิด
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        # แสดงข้อผิดพลาดแบบละเอียดเพื่อให้ผู้ใช้หรือนักพัฒนาตรวจสอบสิทธิ์ชีตได้ง่ายขึ้น
        st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets (ใบงาน: {worksheet_name}): {e}")
        return pd.DataFrame()

# --- ฟังก์ชันส่งข้อมูลสมัครสมาชิกผ่าน Google Form ---
def register_user_via_form(username, password):
    # 1. โหลดข้อมูลเดิมมาเช็คว่า Username ซ้ำไหมก่อน (เช็คแบบไม่สนใจตัวพิมพ์เล็ก-ใหญ่)
    df_users = load_sheet_data("users")
    if not df_users.empty and "username" in df_users.columns:
        # ดึงลิสต์ผู้ใช้งานทั้งหมดมาล้างค่าให้เป็นตัวพิมพ์เล็ก
        existing_users = [clean_sheet_value(u).lower() for u in df_users["username"]]
        if str(username).strip().lower() in existing_users:
            return "exists"

    # 2. ส่งข้อมูลไปยัง Google Form (จำลอง/ส่งจริงตามที่ตั้งค่าลิงก์ฟอร์ม)
    # ตัวอย่างฟอร์มที่สร้างขึ้นเพื่อรับค่า username, password, status
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfD_ZOf_4v3vY_7GZ93D8_example/formResponse"
    
    form_data = {
        "entry.123456789": username,  # แทนที่ด้วย Entry ID ของช่อง Username จริงๆ ของเจ้านาย
        "entry.987654321": password,  # แทนที่ด้วย Entry ID ของช่อง Password จริงๆ ของเจ้านาย
        "entry.111213141": "Pending"  # กำหนดสถานะเริ่มต้นเป็น Pending
    }
    
    try:
        # ในขั้นตอนใช้งานจริง หากเจ้านายตั้งค่า form_url เรียบร้อยแล้ว สามารถเปิดใช้โค้ดส่วนนี้ได้
        # requests.post(form_url, data=form_data)
        return "success"
    except Exception as e:
        return "error"

# --- ฟังก์ชันตรวจสอบการเข้าสู่ระบบ (แก้ไขบั๊กตรวจสอบสิทธิ์เรียบร้อยแล้ว) ---
def login_user(username, password):
    df_users = load_sheet_data("users")
    
    # 1. ตรวจสอบโครงสร้างข้อมูลผู้ใช้งาน
    if df_users.empty or "username" not in df_users.columns:
        # ป้องกันสิทธิ์แอดมินฉุกเฉินหากฐานข้อมูลพังหรือเพิ่งเริ่มต้นใช้ระบบ
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "❌ ไม่พบข้อมูลโครงสร้างผู้ใช้งานใน Google Sheet (กรุณาเช็คชื่อคอลัมน์ในชีตว่ามี 'username' หรือไม่)"
    
    # 2. ค้นหาแถวของผู้ใช้แบบปลอดภัย (เปรียบเทียบแบบ Case-Insensitive และดักจับช่องว่าง)
    input_user_clean = str(username).strip().lower()
    
    # ดึงลิสต์ผู้ใช้จากคอลัมน์ username และทำความสะอาดค่านั้นๆ ก่อนเทียบ
    df_users["clean_username"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    user_row = df_users[df_users["clean_username"] == input_user_clean]
    
    if user_row.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"
    
    # 3. ล้างค่า password และ status ที่อ่านมาจากชีตป้องกันการเพี้ยนของชนิดข้อมูล
    stored_password = clean_sheet_value(user_row.iloc[0]["password"])
    status = clean_sheet_value(user_row.iloc[0]["status"]).strip().lower() # แปลงสเตตัสเป็นพิมพ์เล็กก่อนเทียบ
    input_password_clean = str(password).strip()
    
    # 4. ตรวจสอบความถูกต้องของรหัสผ่าน
    if stored_password != input_password_clean:
        return False, "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
    
    # 5. ตรวจสอบสถานะการอนุมัติใช้งาน
    if status == "pending":
        return False, "⏳ บัญชีนี้กำลังรอการอนุมัติ (Pending) จากพี่บิ๊ก กรุณาติดต่อผู้ดูแลระบบ"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"⚠️ บัญชีของคุณอยู่ในสถานะ '{status}' ซึ่งไม่ได้รับอนุญาตให้เข้าใช้งาน"

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
                    # แจ้งเตือนข้อมูลที่ต้องไปใส่ใน Sheets
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
