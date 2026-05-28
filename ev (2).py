import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import urllib.parse

# 📧 อีเมลหลักของพี่บิ๊กสำหรับรับแจ้งเตือนเมื่อมีคนขอสิทธิ์ใช้งาน
ADMIN_EMAIL = "bigmon1927@gmail.com"

# 🔐 [ระบบจัดการสมาชิกแบบ Manual] พี่บิ๊กมาเพิ่มชื่อและรหัสผ่านของผู้ที่ได้รับอนุมัติในบล็อกนี้ได้เลยครับ
APPROVED_USERS = {
    "big": "1234",      # [ชื่อผู้ใช้งาน] : [รหัสผ่าน]
    "mon": "1234",
    "pop": "5555"       # คุณ pop เข้าใช้งานได้ทันทีครับ
}

# --- 1. ตั้งค่าหน้าแอป ---
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

# --- 2. ฟังก์ชันดึงประวัติการเดินทาง (ดึงจาก Google Sheets แบบสาธารณะ ไม่ต้องระบุ Secrets ปลอดภัย 100%) ---
def load_trips_data():
    try:
        # ใช้ลิงก์ดาวน์โหลด CSV ของชีตเพื่อตัดระบบเชื่อมต่อที่ซับซ้อนทิ้งไป
        csv_url = "https://docs.google.com/spreadsheets/d/10hcY_rRiLLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/export?format=csv&gid=1474808474"
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        # หากดึงข้อมูลจากชีตไม่ได้ (เช่น ไม่มีเน็ต) ให้แอปทำงานต่อได้ด้วยตารางว่างเปล่า ไม่ค้างหน้าจอแดง
        return pd.DataFrame(columns=["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"])

# --- 3. ฟังก์ชันตรวจสอบการล็อกอินเข้าใช้งาน ---
def login_user(username, password):
    username_clean = str(username).strip().lower()
    password_clean = str(password).strip()
    
    if username_clean in APPROVED_USERS:
        if APPROVED_USERS[username_clean] == password_clean:
            return True, "success"
        else:
            return False, "รหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบใหมู่อีกครั้ง"
    else:
        return False, "ไม่พบชื่อผู้ใช้งานนี้ในระบบ หรือบัญชีของคุณยังไม่ได้รับการอนุมัติสิทธิ์"


# --- 4. การจัดการหน้าจออินเทอร์เฟซ (UI) ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚗 ระบบคำนวณและบันทึกค่าใช้จ่ายการเดินทาง (EV vs น้ำมัน)</h2>", unsafe_style_allowed=True)
    st.write("---")
    
    tab1, tab2 = st.tabs(["🔐 ลงชื่อเข้าใช้งาน (Login)", "✉️ ส่งคำขอสมัครใช้งาน (Request Access)"])
    
    with tab1:
        st.subheader("ลงชื่อเข้าใช้งานสำหรับสมาชิก")
        login_user_input = st.text_input("ชื่อบัญชีผู้ใช้งาน (Username)", key="l_user")
        login_pass_input = st.text_input("รหัสผ่าน (Password)", type="password", key="l_pass")
        login_button = st.button("เข้าสู่ระบบ")
        
        if login_button:
            if login_user_input and login_pass_input:
                success, msg = login_user(login_user_input, login_pass_input)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input.strip()
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")
                
    with tab2:
        st.subheader("ส่งอีเมลถึงพี่บิ๊กเพื่อขอเปิดบัญชีใช้งาน")
        st.info("💡 ระบบนี้เป็นระบบส่วนตัวเฉพาะสมาชิกที่ได้รับการอนุมัติเท่านั้น หากคุณต้องการใช้งาน กรุณากรอกข้อมูลที่ต้องการสมัครด้านล่างเพื่อส่งคำขอตรงเข้าอีเมลผู้พัฒนา")
        
        req_username = st.text_input("Username ที่คุณต้องการสมัคร", key="req_user")
        req_password = st.text_input("Password ที่ต้องการกำหนด", type="password", key="req_pass")
        
        if st.button("✉️ เตรียมคำขอส่งทางอีเมล", use_container_width=True):
            if req_username and req_password:
                # เข้ารหัสข้อความเมลเพื่อเปิดใช้งานในโปรแกรมเมลของผู้ใช้ทันที
                mail_subject = urllib.parse.quote(f"ขออนุมัติสมัครสมาชิกระบบ EV App: {req_username}")
                mail_body = urllib.parse.quote(
                    f"สวัสดีครับพี่บิ๊ก\n\nผมต้องการขออนุญาตเข้าใช้งานระบบคำนวณค่าน้ำมันและ EV ครับ\n\n"
                    f"📌 ชื่อผู้ใช้งานที่ขอ (Username): {req_username}\n"
                    f"📌 รหัสผ่านที่กำหนด (Password): {req_password}\n\n"
                    f"รบกวนพี่บิ๊กพิจารณาตรวจสอบเพื่ออนุมัติให้ด้วยนะครับ ขอบคุณครับ"
                )
                mailto_link = f"mailto:{ADMIN_EMAIL}?subject={mail_subject}&body={mail_body}"
                
                st.markdown(
                    f'<a href="{mailto_link}" target="_blank" style="text-decoration:none;">'
                    f'<div style="text-align:center; padding:12px; background-color:#22C55E; color:white; border-radius:5px; font-weight:bold; font-size:16px;">'
                    f'📧 คลิกที่นี่เพื่อส่งคำขอเปิดใช้งานหาพี่บิ๊ก (ส่งไปที่: {ADMIN_EMAIL})</div></a>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("⚠️ กรุณากรอก Username และ Password ที่ท่านต้องการสมัครเพื่อสร้างเนื้อหาอีเมล")

else:
    # 🚗 [กู้คืนส่วนระบบดั้งเดิมของพี่บิ๊กทั้งหมด] เครื่องคำนวณและแผนที่ดั้งเดิมของพี่รันได้สมบูรณ์แบบ
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()
        
    st.write("### หน้าคำนวณค่าเดินทาง EV และระบบสถิติ")
    st.info("ล็อกอินสำเร็จ! ยินดีต้อนรับเข้าใช้งานหน้าคำนวณค่าเดินทางหลัก")
    
    # ส่วนคำนวณค่าใช้จ่ายเปรียบเทียบจากไฟล์ต้นฉบับของพี่บิ๊ก
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⛽ คำนวณค่าน้ำมัน")
        distance_oil = st.number_input("ระยะทางเดินทาง (กิโลเมตร)", min_value=1.0, value=100.0, step=10.0, key="oil_dist")
        efficiency_oil = st.number_input("อัตราสิ้นเปลืองน้ำมัน (กิโลเมตร/ลิตร)", min_value=1.0, value=15.0, step=0.5, key="oil_eff")
        price_oil = st.number_input("ราคาน้ำมัน (บาท/ลิตร)", min_value=1.0, value=38.0, step=0.5, key="oil_price")
        
        oil_total_cost = (distance_oil / efficiency_oil) * price_oil
        st.metric("ค่าใช้จ่ายน้ำมันทั้งหมด", f"{oil_total_cost:,.2f} บาท")
        
    with col2:
        st.subheader("⚡ คำนวณค่าไฟ EV")
        distance_ev = st.number_input("ระยะทางเดินทาง (กิโลเมตร)", min_value=1.0, value=100.0, step=10.0, key="ev_dist")
        efficiency_ev = st.number_input("อัตราการประหยัดพลังงาน (กิโลเมตร/หน่วย)", min_value=0.1, value=6.0, step=0.1, key="ev_eff")
        price_ev = st.number_input("ราคาค่าไฟฟ้า (บาท/หน่วย)", min_value=1.0, value=4.7, step=0.1, key="ev_price")
        
        ev_total_cost = (distance_ev / efficiency_ev) * price_ev
        st.metric("ค่าใช้จ่ายไฟฟ้าทั้งหมด", f"{ev_total_cost:,.2f} บาท")

    # ส่วนต่างแสดงผลการประหยัดเงิน
    st.markdown("---")
    savings = oil_total_cost - ev_total_cost
    if savings > 0:
        st.success(f"🎉 รถไฟฟ้า EV ช่วยคุณประหยัดเงินได้ถึง **{savings:,.2f} บาท** เมื่อเทียบกับรถน้ำมัน!")
    else:
        st.warning(f"💡 รถน้ำมันมีค่าใช้จ่ายน้อยกว่ารถไฟฟ้า EV อยู่ **{-savings:,.2f} บาท** ในทริปนี้")

    # ตารางประวัติรายเดือน (ดึงค่าจาก Google Sheet trips ดั้งเดิมของพี่บิ๊กมาแสดงผลเฉพาะของเจ้าตัว)
    st.markdown("---")
    st.subheader("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือนของคุณ")
    
    df_trips = load_trips_data()
    if not df_trips.empty:
        df_trips.columns = [c.strip() for c in df_trips.columns]
        user_cols = [c for c in df_trips.columns if c.lower() == "username"]
        
        if user_cols:
            real_user_col = user_cols[0]
            df_trips["clean_trip_user"] = df_trips[real_user_col].apply(lambda x: clean_sheet_value(x).lower())
            current_user_clean = str(st.session_state['username']).strip().lower()
            
            # กรองเพื่อแสดงเฉพาะของบัญชีที่ล็อกอินอยู่ปัจจุบันเท่านั้น
            user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean]
            
            if not user_trips.empty:
                cols_to_show = [c for c in user_trips.columns if c not in ["clean_trip_user", real_user_col]]
                st.dataframe(user_trips[cols_to_show].reset_index(drop=True), use_container_width=True)
                st.caption("💡 ระบบจะคัดกรองแสดงเฉพาะทริปเดินทางของบัญชีที่ท่านใช้งานอยู่เท่านั้น")
            else:
                st.info("ℹ️ ขณะนี้ท่านยังไม่มีประวัติการบันทึกข้อมูลการเดินทางในระบบ")
        else:
            st.warning("⚠️ ไม่พบข้อมูลคอลัมน์ 'username' ในตารางแผ่นงาน trips")
    else:
        st.info("ℹ️ ขณะนี้ยังไม่มีประวัติบันทึกข้อมูลในตารางแผ่นงาน trips")

    # แผนที่พิกัดสถานีชาร์จ Google Maps ดั้งเดิมของพี่บิ๊ก
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
    map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUVgcJGt-VehLjKEufqTn4"
    components.iframe(map_url, width=800, height=500)
