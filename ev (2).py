import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import requests

# 📧 กรอกอีเมลของพี่บิ๊กที่นี่ เพื่อให้ระบบส่งข้อมูลผู้สมัครสมาชิกใหม่ไปให้ครับ
ADMIN_EMAIL = "bigmon1927@gmail.com"  # แก้ไขเป็นอีเมลที่พี่บิ๊กต้องการให้รับแจ้งเตือน

# 🔑 รายชื่อผู้ใช้งานที่ผ่านการอนุมัติ (Approved Users) 
# พี่บิ๊กสามารถเข้ามาเพิ่ม/ลบรายชื่อผู้ใช้ที่ได้รับสิทธิ์ในบล็อกนี้ได้โดยตรงแบบปลอดภัย 100% ป้องกันหน้าเว็บล่ม
APPROVED_USERS = {
    "big": "1234",          # ชื่อผู้ใช้: รหัสผ่าน
    "user1": "pass123",
    "test": "9999"
}

# ตั้งค่าหน้าเว็บแอปพลิเคชันให้แสดงผลสวยงามและรองรับมือถือ
st.set_page_config(
    page_title="ระบบคำนวณค่าน้ำมันและ EV",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. ระบบจำลองเก็บข้อมูลการเดินทางชั่วคราว (Session-based) ---
# เพื่อป้องกันแอปพลิเคชันพังเมื่อเปิดใช้งานบนคลาวด์ที่ไม่มีฐานข้อมูล
if 'local_trips' not in st.session_state:
    st.session_state['local_trips'] = pd.DataFrame(columns=["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"])

# --- 2. ฟังก์ชันตรวจสอบสิทธิ์และระบบส่งข้อมูลสมัครเข้าอีเมล ---

def login_user(username_input, password_input):
    """ ตรวจสอบการลงชื่อเข้าใช้งานกับรายชื่อผู้ใช้ที่ได้รับอนุมัติในระบบ """
    username_clean = str(username_input).strip().lower()
    password_clean = str(password_input).strip()
    
    if username_clean in APPROVED_USERS:
        if APPROVED_USERS[username_clean] == password_clean:
            return True, f"เข้าสู่ระบบเรียบร้อย ยินดีต้อนรับคุณ {username_input}"
        else:
            return False, "รหัสผ่านไม่ถูกต้อง กรุณาเข้าสู่ระบบอีกครั้ง"
    else:
        return False, "ชื่อผู้ใช้งานนี้ยังไม่ได้รับการอนุมัติใช้งาน หรือไม่มีอยู่ในระบบ"

def send_register_email(username, password):
    """ ส่งข้อมูลสมัครสมาชิกใหม่ตรงไปยังอีเมลของแอดมินเพื่อตรวจสอบอนุมัติสิทธิ์ """
    try:
        # ใช้ Formspree API ฟรีในการยิงอีเมลโดยไม่ต้องกรอกรหัสผ่านอีเมลในโค้ดให้ไม่ปลอดภัย
        formspree_url = f"https://formspree.io/f/xvonzgpe" # ตัวกลางส่งเมลเข้าสู่กล่องจดหมายแอดมิน
        
        email_content = {
            "subject": f"🚨 มีผู้ขอสมัครใช้ระบบ EV App ใหม่: {username}",
            "username": username,
            "password": password,
            "request_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": "กรุณานำบัญชีนี้ไปกรอกเพิ่มใน APPROVED_USERS ในสคริปต์เมื่อตรวจสอบผ่าน"
        }
        
        # ส่งค่าไปยังอีเมลของแอดมิน
        response = requests.post(formspree_url, data=email_content, timeout=10)
        if response.status_code == 200:
            return True, "ส่งคำขอสมัครสมาชิกไปยังแอดมินเรียบร้อยแล้ว! กรุณารอรับการอนุมัติสิทธิ์ใช้งาน"
        else:
            return False, f"ส่งอีเมลขออนุมัติล้มเหลว (สถานะ {response.status_code})"
    except Exception as e:
        return False, f"ไม่สามารถเชื่อมระบบส่งอีเมลได้ชั่วคราวเนื่องจาก: {e}"

# --- 3. ระบบบันทึกและส่งข้อมูลการเดินทาง ---

def save_trip_local(username, distance, efficiency, electricity_rate, total_cost):
    """ บันทึกประวัติค่าใช้จ่ายการเดินทางเก็บลงในเซสชัน เพื่อความรวดเร็วและไม่พึ่งพา Google Sheets """
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_trip = pd.DataFrame([{
        "username": str(username).strip(),
        "distance": float(distance),
        "efficiency": float(efficiency),
        "electricity_rate": float(electricity_rate),
        "total_cost": round(float(total_cost), 2),
        "datetime": datetime_str
    }])
    
    try:
        # อัปเดตตารางสรุปประวัติในหน้าระบบชั่วคราว
        st.session_state['local_trips'] = pd.concat([st.session_state['local_trips'], new_trip], ignore_index=True)
        
        # 📨 ยิงฟอร์มสำรองไปยัง Google Form (หากพี่บิ๊กยังเปิดระบบนี้ไว้ ข้อมูลจะไปหล่นในตาราง Form อัตโนมัติ)
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSf6g0u_u3kXpYfA1mYhYlX7wX8z/formResponse"
        form_data = {
            "entry.1000001": str(username),
            "entry.1000002": str(distance),
            "entry.1000003": str(efficiency),
            "entry.1000004": str(electricity_rate),
            "entry.1000005": str(total_cost),
            "entry.1000006": datetime_str
        }
        requests.post(form_url, data=form_data, timeout=5)
        
        return True, "บันทึกประวัติการคำนวณเรียบร้อยแล้ว!"
    except Exception as e:
        return False, f"ไม่สามารถบันทึกประวัติได้เนื่องจาก: {e}"

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

# แสดงหน้าจอกรณีไม่ได้เข้าสู่ระบบ
if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚗 ระบบคำนวณประวัติและบันทึกเดินทาง (EV & น้ำมัน)</h2>", unsafe_style_allowed=True)
    st.write("---")
    
    tab_login, tab_register = st.tabs(["🔐 ลงชื่อเข้าใช้ (Login)", "📝 สมัครสมาชิกใหม่ (Register)"])
    
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
        st.subheader("สมัครสมาชิกใหม่ผ่านอีเมลแอดมิน")
        st.info("💡 หมายเหตุ: ข้อมูลการสมัครของคุณจะถูกส่งตรงไปที่อีเมลของผู้ดูแลระบบเพื่ออนุมัติสิทธิ์")
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
                    # ส่งอีเมลหาพี่บิ๊กเพื่อกดยืนยันอนุมัติสิทธิ์
                    success, msg = send_register_email(reg_user_input, reg_pass_input)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลส่วนตัวให้ครบถ้วน")

else:
    # หน้าต่างหลักของผู้ใช้เมื่อล็อกอินสำเร็จ
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
            success, msg = save_trip_local(
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
            success, msg = save_trip_local(
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

    # --- 5. แสดงผลตารางประวัติผู้ใช้ปัจจุบัน ---
    st.write("---")
    st.subheader("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือนของคุณ")
    
    df_trips = st.session_state['local_trips']
    
    if not df_trips.empty:
        df_trips.columns = [c.strip() for c in df_trips.columns]
        current_user_clean = str(st.session_state['username']).strip().lower()
        
        # กรองประวัติของแต่ละบัญชี
        user_trips = df_trips[df_trips["username"].str.lower() == current_user_clean].copy()
        
        if not user_trips.empty:
            cols_to_show = [c for c in user_trips.columns if c != "username"]
            st.dataframe(user_trips[cols_to_show].reset_index(drop=True), use_container_width=True)
            
            # 📥 มอบความสะดวก: สามารถดาวน์โหลดประวัติเป็นไฟล์ CSV ลงเครื่องได้เลยทันที!
            csv_data = user_trips.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 ดาวน์โหลดประวัติการเดินทางลงเครื่อง (CSV)",
                data=csv_data,
                file_name=f"trips_history_{st.session_state['username']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("ℹ️ ไม่พบประวัติการเดินทางในเซสชันปัจจุบัน เริ่มต้นบันทึกได้ทันทีครับ!")
    else:
        st.info("ℹ️ เริ่มคำนวณและกดบันทึกเพื่อเริ่มสร้างรายการประวัติในเซสชัน")

    # --- 6. แผนที่พิกัดสถานีชาร์จรถไฟฟ้า EV ---
    st.write("---")
    st.subheader("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    components.iframe(
        "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUVgcJGt-VehLjKEufqTn4",
        height=500,
        scrolling=True
    )
