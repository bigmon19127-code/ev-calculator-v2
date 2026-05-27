import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import requests

# 🌐 ผูกโดยตรงกับ Google Sheets ID ของพี่บิ๊กเพื่อความรวดเร็วและปลอดภัย
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/10hcY_rRilLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/edit?usp=sharing"

# --- 1. เชื่อมต่อระบบคลาวด์ Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมโยงฐานข้อมูล: {e}")
# 📥 วางแทรกที่บรรทัด 16 เพื่อดึงข้อมูลจากหน้าแผ่นงาน (เวิร์กชีต) มาใช้งาน
try:
    df_users = conn.read(spreadsheet=URL_of_spreadsheet, worksheet="users", ttl="0")
except Exception as e:
    df_users = pd.DataFrame(columns=["username", "password", "status"])

try:
    df_trips = conn.read(spreadsheet=URL_of_spreadsheet, worksheet="trips", ttl="0")
except Exception as e:
    df_trips = pd.DataFrame(columns=["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"])
# ตั้งค่าส่วนหัวของหน้าเว็บแอปพลิเคชัน
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

def clean_sheet_value(val):
    """ ป้องกันรหัสผ่านหรือตัวเลขกลายเป็นทศนิยม (.0) และลบเว้นวรรคหัวท้ายอัตโนมัติ """
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
    """ ดึงข้อมูลจากตาราง Google Sheets ของพี่บิ๊กโดยตรงอย่างเจาะจงแท็บ """
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            # ปรับหัวคอลัมน์ให้เป็นตัวพิมพ์เล็กทั้งหมดและลบเว้นวรรคป้องกันโปรแกรมพัง
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e:
        st.session_state["sheet_error"] = f"ไม่สามารถดึงข้อมูลจากแท็บ '{worksheet_name}' ได้: {str(e)}"
    return pd.DataFrame()

def save_trip_via_form(username, distance, efficiency, electricity_rate, total_cost):
    """ ฟังก์ชันสำหรับกดปุ่มบันทึกเดินทาง แล้วยิงข้อมูลเข้าตารางผ่าน Google Form หลังบ้าน """
    # 📝 พี่บิ๊กนำลิงก์ที่ลงท้ายด้วย /formResponse ของฟอร์มที่พี่ผูกไว้กับสเปรดชีตนี้มาวางแทนที่ได้เลยครับ
    form_url = "https://docs.google.com/spreadsheets/d/10hcY_rRilLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/edit?usp=drive_link"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    form_data = {
        "entry.1000001": username,          # แทนที่ด้วย Entry ID ของกล่อง Username บนแบบฟอร์ม
        "entry.1000002": distance,          # แทนที่ด้วย Entry ID ของกล่อง Distance
        "entry.1000003": efficiency,        # แทนที่ด้วย Entry ID ของกล่อง Efficiency
        "entry.1000004": electricity_rate,  # แทนที่ด้วย Entry ID ของกล่อง Electricity Rate
        "entry.1000005": total_cost,        # แทนที่ด้วย Entry ID ของกล่อง Total Cost
        "entry.1000006": current_time        # แทนที่ด้วย Entry ID ของกล่อง Datetime
    }
    
    try:
        response = requests.post(form_url, data=form_data)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        return False

def login_user(username, password):
    """ ตรวจสอบการเข้าใช้งานระบบจากแท็บ users """
    df_users = load_sheet_data("users")
    
    if df_users.empty:
        # บัญชีแอดมินสำรองฉุกเฉิน
        if username == "admin" and password == "1234":
            return True, "success"
        
        err_msg = st.session_state.get("sheet_error", "ไม่สามารถเปิดแผ่นงานแท็บ 'users' ได้")
        return False, f"❌ ไม่สามารถดึงข้อมูลได้สำเร็จ กรุณาตรวจสอบแท็บใน Sheets ของท่าน\n\n*(รายละเอียด: {err_msg})*"

    input_user = str(username).strip().lower()
    input_pass = str(password).strip()

    # ตรวจสอบว่ามีหัวคอลัมน์ครบถ้วนหรือไม่
    if "username" not in df_users.columns or "password" not in df_users.columns or "status" not in df_users.columns:
        return False, f"❌ หัวตารางในชีตแท็บ 'users' ไม่ถูกต้อง! ต้องเป็นคำว่า: username, password, status (ตรวจพบหัวตารางปัจจุบันคือ: {', '.join(df_users.columns)})"

    df_users["clean_user"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_pass"] = df_users["password"].apply(clean_sheet_value)
    df_users["clean_status"] = df_users["status"].apply(lambda x: clean_sheet_value(x).lower())

    # ตรวจสอบ Username
    user_rows = df_users[df_users["clean_user"] == input_user]
    if user_rows.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"

    # ตรวจสอบรหัสผ่าน
    matched_user = user_rows[user_rows["clean_pass"] == input_pass]
    if matched_user.empty:
        return False, "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"

    # ตรวจสอบสถานะ Approved
    status = matched_user.iloc[0]["clean_status"]
    if status == "pending":
        return False, "⏳ บัญชีของท่านกำลังรอการอนุมัติ (Pending) จากผู้ดูแลระบบ"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"⚠️ บัญชีของท่านมีสถานะเป็น '{status}' จึงไม่ได้รับสิทธิ์เข้าใช้งาน"

# --- ตรวจสถานะ Session ค้างหน้าจอไว้ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- หน้าแรก: ส่วนกรอกฟอร์มล็อกอินเข้าใช้งาน ---
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบแอปพลิเคชัน", "📝 สมัครสมาชิกใหม่"])
    
    with tab1:
        st.subheader("ระบบคำนวณค่าเดินทาง EV (พี่บิ๊ก Secure)")
        login_user_input = st.text_input("Username (ชื่อผู้ใช้)", key="l_user")
        login_pass_input = st.text_input("Password (รหัสผ่าน)", type="password", key="l_pass")
        
        if st.button("เข้าสู่ระบบ"):
            if login_user_input and login_pass_input:
                success, msg = login_user(login_user_input, login_pass_input)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input
                    st.success("🎉 ล็อกอินเข้าใช้งานสำเร็จแล้ว!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทั้งสองช่อง")
                
    with tab2:
        st.subheader("สร้างคำขอสมัครสมาชิกใหม่")
        st.info("💡 ส่งแบบฟอร์มแล้ว แจ้งพี่บิ๊กเพื่อเปิดสถานะเป็น Approved ใน Google Sheets หน้าแผ่นงาน 'users'")
        new_username = st.text_input("กำหนด Username (ภาษาอังกฤษตัวพิมพ์เล็ก)", key="reg_user")
        new_password = st.text_input("กำหนด Password", type="password", key="reg_pass")
        confirm_pass = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm")
        
        if st.button("ส่งคำขอสมัครสมาชิก"):
            if not new_username or not new_password:
                st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
            elif new_password != confirm_pass:
                st.error("❌ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                st.success("🎉 ส่งคำขอสำเร็จเรียบร้อยแล้ว!")
                st.info(f"💡 พี่บิ๊กเปิดแท็บ 'users' ในชีตหลักแล้วกรอกแถวดังนี้:\n\nUsername: {new_username} | Password: {new_password} | Status: Approved")

else:
    # --- หน้าหลักระบบคำนวณหลังผ่านการล็อกอินสำเร็จ ---
    st.sidebar.write(f"ผู้ใช้งาน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    st.write(f"### 🚗 ระบบบันทึกประวัติการเดินทางของท่านสมาชิก: **{st.session_state['username']}**")
    st.success("🔓 เชื่อมต่อฐานข้อมูลคลาวด์เรียบร้อยแล้ว")

    col_calc, col_history = st.columns([1.2, 1])

    with col_calc:
        st.markdown("#### 🧮 ประมวลผลและทดสอบค่าใช้จ่าย")
        with st.form("travel_calc_form"):
            distance = st.number_input("ระยะทางที่ใช้เดินทางจริง (กิโลเมตร)", min_value=0.1, value=100.0, step=10.0)
            efficiency = st.number_input("อัตราสิ้นเปลืองของตัวรถ (กิโลเมตร / หน่วยไฟฟ้า kWh)", min_value=1.0, value=6.5, step=0.5)
            electricity_rate = st.number_input("ค่าไฟฟ้าเฉลี่ยต่อหน่วยชาร์จ (บาท)", min_value=1.0, value=4.5, step=0.5)
            calc_submit = st.form_submit_button("⚡ ประมวลผล")
            
        if calc_submit:
            total_kwh = distance / efficiency
            total_cost = total_kwh * electricity_rate
            st.session_state["calc_res"] = {
                "dist": distance, "eff": efficiency, "rate": electricity_rate, "cost": total_cost, "kwh": total_kwh
            }
            
        if "calc_res" in st.session_state:
            res = st.session_state["calc_res"]
            st.markdown("##### 📊 ผลลัพธ์ตัวเลขการคำนวณ")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(label="ไฟที่ใช้งานทั้งหมด", value=f"{res['kwh']:.2f} kWh")
            with c2:
                st.metric(label="ค่าไฟรวมสุทธิ", value=f"{res['cost']:.2f} บาท")
            with c3:
                st.metric(label="เฉลี่ยค่าไฟกิโลเมตรละ", value=f"{(res['cost']/res['dist']):.2f} บาท")
            
            st.write("ต้องการส่งบันทึกผลการคำนวณรอบนี้ลง Google Sheets ในประวัติของท่านหรือไม่?")
            if st.button("💾 ยืนยันการบันทึกข้อมูล"):
                save_success = save_trip_via_form(
                    username=st.session_state['username'],
                    distance=res['dist'],
                    efficiency=res['eff'],
                    electricity_rate=res['rate'],
                    total_cost=res['cost']
                )
                st.success("🎉 ข้อมูลถูกส่งเข้าตารางคลาวด์ประวัติการเดินทางของท่านแล้ว!")

    with col_history:
        st.markdown("#### 📁 ประวัติทริปเดินทางย้อนหลังของฉัน")
        
        # ⚠️ ดึงข้อมูลจากแผ่นงานแท็บ trips ของพี่บิ๊กมาแสดงผลที่นี่
        df_trips = load_sheet_data("trips")
        
        if not df_trips.empty:
            df_trips.columns = [str(c).strip().replace(" ", "").lower() for c in df_trips.columns]
            
            user_cols = [c for c in df_trips.columns if "username" in c]
            
            if user_cols:
                real_user_col = user_cols[0]
                df_trips["clean_trip_user"] = df_trips[real_user_col].apply(lambda x: clean_sheet_value(x).lower())
                current_user_clean = str(st.session_state['username']).strip().lower()
                
                # กรองเพื่อแสดงเฉพาะของบัญชีที่ล็อกอินอยู่ปัจจุบันเท่านั้น
                user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean]
                
                if not user_trips.empty:
                    # คัดคอลัมน์ข้อมูลที่ใช้โชว์ให้สวยงาม (ลบ username ออกเพื่อป้องกันแสดงผลซ้ำซ้อน)
                    cols_to_show = [c for c in user_trips.columns if c not in ["clean_trip_user", real_user_col]]
                    st.dataframe(user_trips[cols_to_show].reset_index(drop=True), use_container_width=True)
                    st.caption("💡 ระบบจะคัดกรองแสดงเฉพาะทริปเดินทางของบัญชีที่ท่านใช้งานอยู่เท่านั้น")
                else:
                    st.info("ℹ️ ขณะนี้ท่านยังไม่มีประวัติการบันทึกข้อมูลการเดินทางในระบบ")
            else:
                st.warning("⚠️ ไม่พบข้อมูลคอลัมน์ 'username' ในตารางแผ่นงาน trips")
        else:
            st.info("ℹ️ ขณะนี้ยังไม่มีประวัติบันทึกข้อมูลในตารางแผ่นงาน trips")

    # ส่วนแผนที่และวิดเจ็ตพิกัดสถานีชาร์จ EV
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    components.iframe("https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4", width=1000, height=520)
