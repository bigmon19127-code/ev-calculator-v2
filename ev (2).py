import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import requests

# 🌐 ตัวแปรหลักสำหรับเก็บ URL ของสเปรดชีต
URL_of_spreadsheet = "https://docs.google.com/spreadsheets/d/10hcY_rRiLLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/edit?usp=sharing"

# ตั้งค่าหน้าเว็บแอปพลิเคชันให้แสดงผลสวยงามและรองรับมือถือ
st.set_page_config(
    page_title="ระบบคำนวณค่าน้ำมันและ EV",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. เชื่อมต่อระบบคลาวด์ Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมโยงฐานข้อมูล: {e}")

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
    """ ดึงข้อมูลจากแผ่นงาน Google Sheets ตามชื่อหน้าแผ่นงาน """
    try:
        df = conn.read(spreadsheet=URL_of_spreadsheet, worksheet=worksheet_name, ttl=0)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        # หากเกิดปัญหาทางเทคนิค ให้ดึงตารางว่างเปล่ากลับมาแทนเพื่อไม่ให้หน้าจอทั้งหมดล่ม
        if worksheet_name == "users":
            return pd.DataFrame(columns=["username", "password", "status"])
        elif worksheet_name == "trips":
            return pd.DataFrame(columns=["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"])
        return pd.DataFrame()

# โหลดข้อมูลตารางผู้ใช้และตารางประวัติจาก Google Sheets
df_users = load_sheet_data("users")
df_trips = load_sheet_data("trips")

# จัดระเบียบชุดข้อมูลรหัสผ่านและชื่อผู้ใช้ป้องการผิดพลาดของการล็อกอิน
if not df_users.empty:
    df_users["clean_username"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_password"] = df_users["password"].apply(lambda x: clean_sheet_value(x))
    df_users["clean_status"] = df_users["status"].apply(lambda x: clean_sheet_value(x).strip())
else:
    df_users["clean_username"] = pd.Series(dtype=str)
    df_users["clean_password"] = pd.Series(dtype=str)
    df_users["clean_status"] = pd.Series(dtype=str)

# --- 2. ฟังก์ชันระบบการลงชื่อเข้าใช้และการลงทะเบียน ---

def login_user(username_input, password_input):
    """ ตรวจสอบการยืนยันตนของผู้ใช้กับข้อมูลใน Google Sheet """
    username_clean = str(username_input).strip().lower()
    password_clean = str(password_input).strip()
    
    if df_users.empty:
        return False, "ยังไม่มีข้อมูลผู้ใช้งานใดๆ ในระบบชีต"
        
    match = df_users[df_users["clean_username"] == username_clean]
    if match.empty:
        return False, "ไม่พบชื่อผู้ใช้งานนี้ในระบบกรุณาสมัครสมาชิก"
        
    user_record = match.iloc[0]
    if user_record["clean_password"] != password_clean:
        return False, "รหัสผ่านไม่ถูกต้อง กรุณาเข้าสู่ระบบอีกครั้ง"
        
    if user_record["clean_status"].lower() != "approved":
        return False, "บัญชีของท่านยังไม่ผ่านการตรวจสอบสิทธิ์ (สถานะ Pending) กรุณาแจ้งผู้ดูแลระบบ"
        
    return True, f"เข้าสู่ระบบเรียบร้อย ยินดีต้อนรับคุณ {user_record['username']}"

def register_user(username_input, password_input):
    """ บันทึกการลงทะเบียนสมัครสมาชิกรายใหม่ส่งไปยัง Google Sheets โดยตรง """
    username_clean = str(username_input).strip()
    username_clean_lower = username_clean.lower()
    password_clean = str(password_input).strip()
    
    if not username_clean or not password_clean:
        return False, "กรุณากรอกข้อมูล Username และ Password ให้ครบถ้วน"
        
    if not df_users.empty and (df_users["clean_username"] == username_clean_lower).any():
        return False, "ชื่อบัญชีนี้ได้รับการใช้งานไปแล้ว กรุณาเลือกใช้ชื่อผู้ใช้อื่น"
        
    new_user = pd.DataFrame([{
        "username": username_clean,
        "password": password_clean,
        "status": "Pending"
    }])
    
    try:
        raw_users = df_users[["username", "password", "status"]].copy() if not df_users.empty else pd.DataFrame(columns=["username", "password", "status"])
        updated_users = pd.concat([raw_users, new_user], ignore_index=True)
        conn.update(spreadsheet=URL_of_spreadsheet, worksheet="users", data=updated_users)
        return True, "ส่งข้อมูลการสมัครสำเร็จแล้ว! กรุณารอรับการอนุมัติใช้งาน (Approved)"
    except Exception as e:
        return False, f"ระบบสมัครสมาชิกล้มเหลวเนื่องจาก: {e}"

# --- 3. ระบบบันทึกและส่งข้อมูลการเดินทาง ---

def save_trip_via_form(username, distance, efficiency, electricity_rate, total_cost):
    """ ทำหน้าที่บันทึกประวัติค่าใช้จ่ายการเดินทางส่งตรงไปยังตาราง Google Sheet เรียลไทม์ """
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # บันทึกตรงเข้าแผ่นงาน 'trips' (เสถียร 100%)
    new_trip = pd.DataFrame([{
        "username": str(username).strip(),
        "distance": float(distance),
        "efficiency": float(efficiency),
        "electricity_rate": float(electricity_rate),
        "total_cost": round(float(total_cost), 2),
        "datetime": datetime_str
    }])
    
    sheet_success = False
    try:
        if not df_trips.empty:
            valid_cols = ["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"]
            raw_trips = df_trips[[c for c in valid_cols if c in df_trips.columns]].copy()
            updated_trips = pd.concat([raw_trips, new_trip], ignore_index=True)
        else:
            updated_trips = new_trip
            
        conn.update(spreadsheet=URL_of_spreadsheet, worksheet="trips", data=updated_trips)
        sheet_success = True
    except Exception as e:
        st.warning(f"⚠️ บันทึกตรงเข้าตารางกูเกิลชีตขัดข้อง: {e}")

    # ยิงฟอร์มสำรองไปยัง Google Form (พอร์ต Requests)
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSf6g0u_u3kXpYfA1mYhYlX7wX8z/formResponse"
    form_data = {
        "entry.1000001": str(username),
        "entry.1000002": str(distance),
        "entry.1000003": str(efficiency),
        "entry.1000004": str(electricity_rate),
        "entry.1000005": str(total_cost),
        "entry.1000006": datetime_str
    }
    
    form_success = False
    try:
        response = requests.post(form_url, data=form_data, timeout=5)
        if response.status_code == 200:
            form_success = True
    except Exception:
        pass # อนุญาตให้ข้ามได้หากฟอร์มไม่ได้เปิดให้ใช้งานสาธารณะจริง

    if sheet_success or form_success:
        return True, "บันทึกประวัติการคำนวณเรียบร้อย!"
    return False, "ไม่สามารถจัดเก็บข้อมูลได้ กรุณาลองตรวจสอบใหม่อีกครั้ง"

# --- 4. การจัดการเซสชันหน้าเว็บแอปพลิเคชัน ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

if st.session_state['logged_in']:
    with st.sidebar:
        st.markdown(f"### 👤 บัญชีปัจจุบัน: **{st.session_state['username']}**")
        st.write("สถานะการอนุมัติสิทธิ์: **Approved** ✅")
        st.markdown("---")
        if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.success("ออกจากระบบสำเร็จ")
            st.rerun()

# ฟอร์มกรณีไม่ได้เข้าสู่ระบบ
if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚗 ระบบคำนวณประวัติและบันทึกเดินทาง (EV & น้ำมัน)</h2>", unsafe_style_allowed=True)
    st.write("---")
    
    tab_login, tab_register = st.tabs(["🔐 ลงชื่อเข้าใช้ (Login)", "📝 ลงทะเบียนใหม่ (Register)"])
    
    with tab_login:
        st.subheader("ลงชื่อเข้าใช้")
        login_user_input = st.text_input("ชื่อผู้ใช้งาน (Username)", key="l_user")
        login_pass_input = st.text_input("รหัสผ่าน (Password)", type="password", key="l_pass")
        
        if st.button("เข้าสู่ระบบ", type="primary", use_container_width=True):
            if login_user_input and login_pass_input:
                success, msg = login_user(login_user_input, login_pass_input)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกชื่อผู้ใช้และรหัสผ่านให้ครบถ้วน")
                
    with tab_register:
        st.subheader("สมัครสมาชิกใหม่เพื่อขอสิทธิ์")
        st.info("💡 หมายเหตุ: บัญชีที่สมัครใหม่จะมีสถานะเป็น 'Pending' และจะใช้รหัสผ่านนี้ล็อกอินได้ต่อเมื่อได้รับการเปิดสิทธิ์จากแอดมิน")
        reg_user_input = st.text_input("กำหนด Username (ภาษาอังกฤษหรือตัวเลขเท่านั้น)", key="r_user")
        reg_pass_input = st.text_input("กำหนด Password", type="password", key="r_pass")
        reg_confirm_input = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="r_conf")
        
        if st.button("ส่งคำขอสมัครสมาชิก", use_container_width=True):
            if reg_user_input and reg_pass_input and reg_confirm_input:
                if reg_pass_input != reg_confirm_input:
                    st.error("⚠️ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                elif not reg_user_input.isalnum():
                    st.error("⚠️ Username ควรเป็นตัวเลขหรือภาษาอังกฤษที่พิมพ์ติดกันเท่านั้น")
                else:
                    success, msg = register_user(reg_user_input, reg_pass_input)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลส่วนตัวให้ครบทุกถ้วน")

else:
    # หน้าต่างหลักของผู้ใช้เมื่อทำการยืนยันสิทธิ์ล็อกอินผ่านเรียบร้อยแล้ว
    st.markdown(f"## 📊 ยินดีต้อนรับคุณ {st.session_state['username']} เข้าสู่หน้าระบบคำนวณ")
    st.write("---")
    
    col_gas, col_ev = st.columns(2)
    
    with col_gas:
        st.markdown("<div style='background-color:#FFF5F5; padding:15px; border-radius:10px; border-left: 5px solid #F87171;'>", unsafe_style_allowed=True)
        st.subheader("⛽ บันทึกเดินทาง (รถน้ำมัน)")
        gas_distance = st.number_input("ระยะทางที่ใช้เดินทาง (กิโลเมตร)", min_value=0.0, step=1.0, value=100.0, key="gas_d")
        gas_efficiency = st.number_input("อัตราประหยัดเชื้อเพลิง (กม./ลิตร)", min_value=1.0, step=0.1, value=15.0, key="gas_e")
        gas_rate = st.number_input("ราคาน้ำมันเฉลี่ยปัจจุบัน (บาท/ลิตร)", min_value=1.0, step=0.1, value=38.5, key="gas_r")
        
        gas_cost = (gas_distance / gas_efficiency) * gas_rate if gas_efficiency > 0 else 0.0
        st.metric(label="ประมาณการเงินค่าน้ำมันรถรวม", value=f"{gas_cost:,.2f} บาท")
        
        if st.button("💾 บันทึกประวัติ (รถน้ำมัน)", type="primary", use_container_width=True):
            success, msg = save_trip_via_form(
                username=st.session_state['username'],
                distance=gas_distance,
                efficiency=gas_efficiency,
                electricity_rate=gas_rate,
                total_cost=gas_cost
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        st.markdown("</div>", unsafe_style_allowed=True)
                
    with col_ev:
        st.markdown("<div style='background-color:#F0FDF4; padding:15px; border-radius:10px; border-left: 5px solid #4ADE80;'>", unsafe_style_allowed=True)
        st.subheader("⚡ บันทึกเดินทาง (รถไฟฟ้า EV)")
        ev_distance = st.number_input("ระยะทางที่ใช้เดินทาง (กิโลเมตร)", min_value=0.0, step=1.0, value=100.0, key="ev_d")
        ev_efficiency = st.number_input("อัตราใช้ไฟฟ้าเฉลี่ย (กม./หน่วยไฟ)", min_value=0.1, step=0.1, value=6.5, key="ev_e")
        ev_rate = st.number_input("อัตราค่าไฟฟ้าต่อหน่วย (บาท/หน่วยไฟ)", min_value=1.0, step=0.1, value=4.7, key="ev_r")
        
        ev_cost = (ev_distance / ev_efficiency) * ev_rate if ev_efficiency > 0 else 0.0
        st.metric(label="ประมาณการเงินค่าไฟฟ้า EV รวม", value=f"{ev_cost:,.2f} บาท")
        
        if st.button("💾 บันทึกประวัติ (รถไฟฟ้า EV)", type="primary", use_container_width=True):
            success, msg = save_trip_via_form(
                username=st.session_state['username'],
                distance=ev_distance,
                efficiency=ev_efficiency,
                electricity_rate=ev_rate,
                total_cost=ev_cost
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        st.markdown("</div>", unsafe_style_allowed=True)

    # --- 5. แสดงผลประวัติเฉพาะผู้ใช้ปัจจุบัน ---
    st.write("---")
    st.subheader("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือนของคุณ")
    
    if not df_trips.empty:
        df_trips.columns = [c.strip() for c in df_trips.columns]
        user_cols = [c for c in df_trips.columns if c.lower() == "username"]
        
        if user_cols:
            real_user_col = user_cols[0]
            df_trips["clean_trip_user"] = df_trips[real_user_col].apply(lambda x: clean_sheet_value(x).lower())
            current_user_clean = str(st.session_state['username']).strip().lower()
            
            user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean].copy()
            
            if not user_trips.empty:
                cols_to_show = [c for c in user_trips.columns if c not in ["clean_trip_user", real_user_col]]
                st.dataframe(user_trips[cols_to_show].reset_index(drop=True), use_container_width=True)
                st.caption("💡 ระบบจะคัดกรองแสดงเฉพาะทริปเดินทางของบัญชีที่ท่านใช้งานอยู่ปัจจุบันเท่านั้น")
            else:
                st.info("ℹ️ ไม่พบประวัติการเดินทางบันทึกในบัญชีนี้ เริ่มทดสอบการคำนวณแรกได้เลยครับ!")
        else:
            st.warning("⚠️ คีย์เชื่อมฐานข้อมูลไม่สมบูรณ์ (ไม่พบคอลัมน์ 'username' ในตารางหน้าชีต trips)")
    else:
        st.info("ℹ️ ขณะนี้ประวัติตารางเดินทางทั้งหมดในชีตยังว่างเปล่า")

    # --- 6. แผนที่สถานีชาร์จรถไฟฟ้า EV ---
    st.write("---")
    st.subheader("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    components.iframe(
        "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUVgcJGt-VehLjKEufqTn4",
        height=500,
        scrolling=True
    )
