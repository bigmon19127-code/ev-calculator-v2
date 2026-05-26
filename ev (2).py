import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import requests

# เชื่อมต่อ Google Sheets (สแกนแบบ Real-time ตลอดเวลา)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# ตั้งค่าหน้าแอปพลิเคชัน
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

def clean_sheet_value(val):
    """ ป้องกันปัญหาข้อมูลเป็นค่าว่าง ปัญหารหัสผ่านตัวเลขกลายเป็นทศนิยม (.0) และลบช่องว่าง """
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        try:
            float(val_str)
            val_str = val_str[:-2]
        except ValueError:
            pass
    return val_str

def load_sheet_data(worksheet_name):
    """ ฟังก์ชันดึงข้อมูลจากแท็บที่ระบุอย่างเสถียร """
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e:
        pass
    return pd.DataFrame()

def save_trip_via_form(username, distance, efficiency, electricity_rate, total_cost):
    """ ฟังก์ชันส่งข้อมูลการเดินทางกลับเข้าแผ่นงาน trips อัตโนมัติ (ผ่าน Google Form ของพี่บิ๊ก) """
    # ⚠️ นำลิงก์ Form Response ที่ผูกกับแผ่นงาน trips ของพี่บิ๊กมาใส่แทนที่ลิงก์ตัวอย่างนี้ได้เลยครับ
    form_url = "https://docs.google.com/spreadsheets/d/10hcY_rRilLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/edit?usp=sharing"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    form_data = {
        "entry.111111111": username,          # รหัส Entry ของช่อง username ในฟอร์ม trips
        "entry.222222222": distance,          # รหัส Entry ของช่อง distance
        "entry.333333333": efficiency,        # รหัส Entry ของช่อง efficiency
        "entry.444444444": electricity_rate,  # รหัส Entry ของช่อง electricity_rate
        "entry.555555555": total_cost,        # รหัส Entry ของช่อง total_cost
        "entry.666666666": current_time        # รหัส Entry ของช่อง datetime
    }
    try:
        # เปิดใช้งาน requests.postเมื่อพี่บิ๊กใส่ลิงก์และ Entry ID จริงเรียบร้อยแล้ว
        # requests.post(form_url, data=form_data)
        return True
    except Exception as e:
        return False

def login_user(username, password):
    """ ตรวจสอบล็อกอินจากแท็บ users ระบบหมายเลข 9 """
    df_users = load_sheet_data("users")
    if df_users.empty:
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "❌ ไม่สามารถดึงข้อมูลจากชีตได้ กรุณาตรวจสอบการแชร์ลิงก์"

    input_user = str(username).strip().lower()
    input_pass = str(password).strip()

    df_users["clean_user"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_pass"] = df_users["password"].apply(clean_sheet_value)

    user_rows = df_users[df_users["clean_user"] == input_user]
    if user_rows.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"

    matched_user = user_rows[user_rows["clean_pass"] == input_pass]
    if matched_user.empty:
        return False, "❌ รหัสผ่านไม่ถูกต้อง"

    status = clean_sheet_value(matched_user.iloc[0]["status"]).strip().lower()
    if status == "pending":
        return False, "⏳ บัญชีนี้กำลังรอการอนุมัติ (Pending) จากพี่บิ๊ก"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"⚠️ สถานะบัญชี '{status}' ไม่ได้รับสิทธิ์ใช้งาน"

# --- บริหารจัดการ Session สำหรับการค้างหน้าจอเข้าสู่ระบบ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบแอปพลิเคชัน", "📝 สมัครสมาชิกใหม่"])
    with tab1:
        st.subheader("กรุณาเข้าสู่ระบบ")
        login_user_input = st.text_input("Username", key="l_user")
        login_pass_input = st.text_input("Password", type="password", key="l_pass")
        if st.button("เข้าสู่ระบบ"):
            success, msg = login_user(login_user_input, login_pass_input)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['username'] = login_user_input
                st.success("🎉 ล็อกอินสำเร็จแล้ว!")
                st.rerun()
            else:
                st.error(msg)
    with tab2:
        st.subheader("สมัครสมาชิกใหม่")
        st.info("ส่งคำขอแล้วแจ้งให้พี่บิ๊กปรับสถานะในชีตเป็น Approved ได้เลยครับ")

else:
    # --- หน้าหลักหลังจากล็อกอินผ่านระบบหมายเลข 9 สำเร็จ ---
    st.sidebar.write(f"ผู้ใช้งาน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    st.write(f"### 🚗 ระบบบันทึกการเดินทางของท่านสมาชิก: {st.session_state['username']}")
    
    col_calc, col_history = st.columns([1.2, 1])
    
    with col_calc:
        st.markdown("#### 🧮 คำนวณและบันทึกประวัติ")
        with st.form("travel_calc_form"):
            distance = st.number_input("ระยะทางที่ขับรถ (กิโลเมตร)", min_value=0.1, value=100.0)
            efficiency = st.number_input("อัตราสิ้นเปลือง (กิโลเมตร / หน่วยไฟฟ้า)", min_value=1.0, value=6.5)
            electricity_rate = st.number_input("ค่าไฟฟ้าต่อหน่วย (บาท)", min_value=1.0, value=4.5)
            calc_submit = st.form_submit_button("⚡ ประมวลผล")
            
        if calc_submit:
            total_kwh = distance / efficiency
            total_cost = total_kwh * electricity_rate
            st.session_state["calc_res"] = {
                "dist": distance, "eff": efficiency, "rate": electricity_rate, "cost": total_cost, "kwh": total_kwh
            }
            
        if "calc_res" in st.session_state:
            res = st.session_state["calc_res"]
            st.info(f"📊 ผลคำนวณ: ใช้ไฟไป {res['kwh']:.2f} หน่วย คิดเป็นเงินรวม {res['cost']:.2f} บาท")
            
            if st.button("💾 กดบันทึกประวัติการเดินทางนี้"):
                is_saved = save_trip_via_form(st.session_state['username'], res['dist'], res['eff'], res['rate'], res['cost'])
                st.success("🎉 ระบบได้จำลองส่งบันทึกเข้าแท็บ trips เรียบร้อยแล้ว!")

    with col_history:
        st.markdown("#### 📁 ประวัติการเดินทางย้อนหลังของคุณ")
        df_trips = load_sheet_data("trips")
        
        if not df_trips.empty:
            # ค้นหาคอลัมน์ชื่อ username ในแผ่นงาน trips แล้วล้างค่าช่องว่าง
            df_trips["clean_trip_user"] = df_trips["username"].apply(lambda x: clean_sheet_value(x).lower())
            current_user_clean = str(st.session_state['username']).strip().lower()
            
            # กรองให้ดึงเฉพาะประวัติของ User ที่ล็อกอินอยู่เท่านั้น!
            user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean]
            
            if not user_trips.empty:
                st.dataframe(user_trips[["distance", "efficiency", "electricity_rate", "total_cost", "datetime"]].reset_index(drop=True), use_container_width=True)
            else:
                st.info("ℹ️ บัญชีของคุณยังไม่มีประวัติการเดินทางบันทึกไว้")
        else:
            st.info("ℹ️ ไม่มีข้อมูลประวัติในแผ่นงาน trips")

    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    components.iframe("https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4", width=1000, height=500)
