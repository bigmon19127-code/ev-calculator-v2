# ระบบคำนวณค่าเดินทาง EV และจัดการสิทธิ์ผู้ใช้งานผ่าน Google Sheets
:โค้ดแอปพลิเคชันระบบคำนวณค่าเดินทาง EV (ปรับปรุงระบบบันทึกข้อมูล):ev (3).py
import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import requests

# เชื่อมต่อ Google Sheets โดยตั้งค่า ttl=0 เพื่อให้อ่านข้อมูลล่าสุดเสมอ
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 1. ตั้งค่าหน้าแอป ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets ---
def load_sheet_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name)
        if df is None:
            return pd.DataFrame()
        # ล้างช่องว่างที่อาจติดมากับชื่อคอลัมน์
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจากชีต '{worksheet_name}': {e}")
        return pd.DataFrame()

# --- ฟังก์ชันสมัครสมาชิก ---
def register_user(username, password, method="direct"):
    """
    ฟังก์ชันสำหรับลงทะเบียนผู้ใช้ใหม่
    method='direct': เขียนข้อมูลตรงเข้า Google Sheet (ต้องการสิทธิ์ Editor ของ Service Account ใน Secrets)
    method='form': ส่งผ่าน Google Form (ต้องระบุ Form URL และ Entry ID ของจริง)
    """
    # 1. โหลดข้อมูลผู้ใช้เดิมมาตรวจสอบว่าชื่อซ้ำหรือไม่
    df_users = load_sheet_data("users")
    if not df_users.empty and "username" in df_users.columns:
        existing_users = df_users["username"].astype(str).str.strip().tolist()
        if username.strip() in existing_users:
            return "exists"

    # --- วิธีที่ 1: เขียนข้อมูลเข้า Google Sheet ตรงๆ (แนะนำและเสถียรที่สุด) ---
    if method == "direct":
        try:
            # สร้างแถวข้อมูลใหม่
            new_row = pd.DataFrame([{
                "username": username.strip(),
                "password": str(password).strip(),
                "status": "Pending"  # เริ่มต้นสถานะเป็นรออนุมัติ
            }])
            
            # รวมข้อมูลเดิมเข้ากับข้อมูลใหม่
            if df_users.empty:
                updated_df = new_row
            else:
                updated_df = pd.concat([df_users, new_row], ignore_index=True)
            
            # บันทึกกลับลงในชีต users
            conn.update(worksheet="users", data=updated_df)
            return "success"
        except Exception as e:
            # หากเขียนตรงไม่สำเร็จ (อาจเพราะไม่มีสิทธิ์เขียน) จะแจ้งข้อผิดพลาดกลับมา
            st.error(f"ไม่สามารถเขียนข้อมูลลง Google Sheets โดยตรงได้ (โปรดตรวจสอบการตั้งค่าสิทธิ์ Service Account ของคุณ): {e}")
            return "error"

    # --- วิธีที่ 2: ส่งข้อมูลผ่าน Google Form (หากใช้วิธีเดิมกรุณาแก้ไขค่า XXXXX ด้านล่างนี้เป็นค่าจริง) ---
    elif method == "form":
        # ตรวจสอบก่อนว่ามีการกรอก URL จริงเข้ามาหรือยัง
        form_url = "https://docs.google.com/forms/d/e/XXXXXXXXXXXXX/formResponse"  # <--- แก้ไขจุดนี้เป็น URL ฟอร์มจริงของคุณ
        entry_username = "entry.11111111"  # <--- แก้ไขจุดนี้เป็น Entry ID ของช่องกรอกชื่อ
        entry_password = "entry.22222222"  # <--- แก้ไขจุดนี้เป็น Entry ID ของช่องกรอกรหัสผ่าน
        
        if "XXXXXXXXXXXXX" in form_url or "11111111" in entry_username:
            st.error("⚠️ ไม่สามารถสมัครผ่านระบบ Google Form ได้ เนื่องจากค่า URL หรือ Entry ID ในระบบหลังบ้านยังไม่ได้เปลี่ยนเป็นค่าจริงของคุณ")
            return "setup_required"

        form_data = {
            entry_username: username,
            entry_password: password
        }
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.post(form_url, data=form_data, headers=headers, timeout=10)
            if response.status_code == 200:
                return "success"
            else:
                st.error(f"Google Form ปฏิเสธการบันทึกข้อมูล (Status Code: {response.status_code})")
                return "error"
        except Exception as e:
            st.error(f"ไม่สามารถเชื่อมต่อไปยัง Google Form ได้: {e}")
            return "error"

# --- 2. ตรวจสอบสถานะการเข้าสู่ระบบ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- หน้าแรกสำหรับการเข้าสู่ระบบและการสมัครสมาชิก ---
if not st.session_state['logged_in']:
    st.title("🚗 ระบบคำนวณค่าเดินทาง EV และจัดการสถิติ")
    
    tab_login, tab_register = st.tabs(["🔐 เข้าสู่ระบบ", "📝 สมัครสมาชิก"])
    
    # 2.1 หน้าล็อกอิน
    with tab_login:
        st.subheader("เข้าสู่ระบบผู้ใช้งาน")
        username_input = st.text_input("ชื่อผู้ใช้งาน (Username)", key="login_user").strip()
        password_input = st.text_input("รหัสผ่าน (Password)", type="password", key="login_pass").strip()
        
        if st.button("เข้าสู่ระบบ", type="primary", key="login_btn"):
            if not username_input or not password_input:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
                df_users = load_sheet_data("users")
                if not df_users.empty and "username" in df_users.columns:
                    # ค้นหาผู้ใช้งานที่ตรงกัน
                    user_record = df_users[df_users["username"].astype(str).str.strip() == username_input]
                    
                    if not user_record.empty:
                        db_pass = str(user_record.iloc[0]["password"]).strip()
                        db_status = str(user_record.iloc[0]["status"]).strip()
                        
                        if db_pass == password_input:
                            if db_status == "Approved":
                                st.session_state['logged_in'] = True
                                st.session_state['username'] = username_input
                                st.success("เข้าสู่ระบบสำเร็จ!")
                                st.rerun()
                            else:
                                st.warning("⚠️ บัญชีของคุณยังไม่ได้รับการอนุมัติ (Pending) กรุณาติดต่อพี่บิ๊กเพื่อเปิดสถานะเป็น Approved")
                        else:
                            st.error("รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                    else:
                        st.error("ไม่พบชื่อผู้ใช้งานนี้ในระบบ")
                else:
                    st.error("ไม่สามารถตรวจสอบข้อมูลสมาชิกได้ในขณะนี้")
                    
    # 2.2 หน้าสมัครสมาชิก
    with tab_register:
        st.subheader("สมัครสมาชิกใหม่")
        new_user = st.text_input("ตั้งชื่อผู้ใช้งาน (Username)", key="reg_user").strip()
        new_pass = st.text_input("ตั้งรหัสผ่าน (Password)", type="password", key="reg_pass").strip()
        confirm_pass = st.text_input("ยืนยันรหัสผ่านอีกครั้ง", type="password", key="reg_confirm").strip()
        
        # ให้ผู้ใช้เลือกว่าต้องการทดสอบส่งด้วยวิธีใด (หลังจากตั้งค่าระบบแล้ว)
        reg_method = st.radio(
            "เลือกวิธีการบันทึกข้อมูลสมาชิกไปยัง Google Sheet", 
            ["บันทึกตรงเข้า Google Sheets (ต้องการสิทธิ์เขียน/Service Account)", "ยิงข้อมูลผ่าน Google Form"],
            index=0
        )
        
        method_key = "direct" if reg_method.startswith("บันทึกตรง") else "form"
        
        if st.button("ลงชื่อสมัครสมาชิก", type="primary", key="reg_btn"):
            if not new_user or not new_pass or not confirm_pass:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            elif new_pass != confirm_pass:
                st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                with st.spinner("กำลังทำรายการ..."):
                    reg_result = register_user(new_user, new_pass, method=method_key)
                
                if reg_result == "success":
                    st.success("🎉 ส่งคำขอสมัครสมาชิกสำเร็จแล้ว!")
                    st.info(f"💡 กรุณาแจ้งผู้ดูแลระบบเพื่อเปิดสถานะสิทธิ์ใช้งาน (Status: Approved) ของชื่อผู้ใช้: **{new_user}** บน Google Sheets ก่อนจะสามารถนำไปใช้เข้าสู่ระบบได้นะครับ")
                elif reg_result == "exists":
                    st.warning("⚠️ ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว กรุณาเลือกใช้ชื่ออื่น")
                elif reg_result == "setup_required":
                    st.info("💡 คำแนะนำสำหรับวิธีเขียนข้อมูลตรง: หากต้องการให้ระบบสมัครสมาชิกทำงานได้ทันทีโดยไม่ต้องเชื่อม Google Form คุณสามารถสร้างสิทธิ์เขียนไฟล์ให้กับระบบ แล้วเลือกส่งแบบ 'บันทึกตรงเข้า Google Sheets' ได้เลยครับ")
                else:
                    st.error("❌ ไม่สามารถสมัครสมาชิกได้เนื่องจากระบบเชื่อมโยงมีปัญหา กรุณาตรวจสอบสิทธิ์การเขียนไฟล์ของคุณ")

else:
    # หน้าจอแอปพลิเคชันหลักหลังจากเข้าสู่ระบบสำเร็จแล้ว
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()
        
    st.write("### หน้าคำนวณค่าเดินทาง EV และระบบสถิติ")
    st.info(f"ยินดีต้อนรับคุณ **{st.session_state['username']}** เข้าสู่ระบบเรียบร้อยแล้ว!")
    
    # --- ฟังก์ชันบันทึกทริปการเดินทาง ---
    st.subheader("📌 บันทึกข้อมูลทริปการเดินทางใหม่")
    with st.form("trip_form"):
        col1, col2 = st.columns(2)
        with col1:
            distance = st.number_input("ระยะทางที่วิ่งได้ (กิโลเมตร - km)", min_value=0.1, step=1.0)
            efficiency = st.number_input("อัตราการกินไฟเฉลี่ยของรถ (km/kWh)", min_value=0.1, step=0.1)
        with col2:
            electricity_rate = st.number_input("อัตราค่าไฟฟ้าต่อหน่วย (บาท/หน่วย - THB/kWh)", min_value=1.0, step=0.1, value=4.5)
            
        submit_trip = st.form_submit_button("บันทึกข้อมูลทริปการเดินทาง")
        
        if submit_trip:
            # คำนวณค่าใช้จ่าย
            used_energy = distance / efficiency
            total_cost = used_energy * electricity_rate
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ดึงข้อมูลการเดินทางเดิมมาตรวจสอบก่อน
            df_trips = load_sheet_data("trips")
            
            new_trip_data = pd.DataFrame([{
                "username": st.session_state['username'],
                "distance": distance,
                "efficiency": efficiency,
                "electricity_rate": electricity_rate,
                "total_cost": round(total_cost, 2),
                "datetime": now_str
            }])
            
            try:
                if df_trips.empty:
                    updated_trips = new_trip_data
                else:
                    updated_trips = pd.concat([df_trips, new_trip_data], ignore_index=True)
                
                # เขียนข้อมูลใหม่กลับเข้าไปยังชีต trips
                conn.update(worksheet="trips", data=updated_trips)
                st.success(f"🚙 บันทึกข้อมูลทริปสำเร็จ! ค่าไฟฟ้าทริปนี้เฉลี่ยคือ {round(total_cost, 2)} บาท")
            except Exception as e:
                st.error(f"ไม่สามารถบันทึกข้อมูลทริปลง Google Sheet ได้: {e} (โปรดตรวจสอบสิทธิ์ในการเขียนไฟล์)")

    # --- แสดงประวัติและสถิติ ---
    st.subheader("📊 ประวัติการเดินทางของคุณ")
    df_history = load_sheet_data("trips")
    if not df_history.empty and "username" in df_history.columns:
        user_trips = df_history[df_history["username"].astype(str).str.strip() == st.session_state['username']]
        if not user_trips.empty:
            st.dataframe(user_trips, use_container_width=True)
            
            # การสรุปผลเบื้องต้น
            total_dist = user_trips["distance"].astype(float).sum()
            total_spend = user_trips["total_cost"].astype(float).sum()
            avg_rate = user_trips["total_cost"].astype(float).mean()
            
            metric1, metric2, metric3 = st.columns(3)
            metric1.metric("ระยะทางรวมสะสม", f"{round(total_dist, 2)} กม.")
            metric2.metric("ค่าไฟรวมที่จ่ายไป", f"{round(total_spend, 2)} บาท")
            metric3.metric("เฉลี่ยต่อทริป", f"{round(avg_rate, 2)} บาท")
        else:
            st.info("ยังไม่มีข้อมูลทริปการเดินทางที่ถูกบันทึกสำหรับผู้ใช้งานรายนี้")
    else:
        st.info("ยังไม่มีข้อมูลประวัติทริปการเดินทางในฐานข้อมูล")


### สรุปสิ่งที่ได้ทำการแก้ไขและคำแนะนำในการนำไปใช้:
1.  **คอลัมน์ถูกต้อง:** ตรวจสอบแล้วว่าชื่อคอลัมน์ในโค้ดสะกดตรงกับในไฟล์ CSV ทั้งหมด (`username`, `password`, `status` เป็นตัวพิมพ์เล็กทั้งหมด ตรงกัน 100%)
2.  **ปรับปรุงโค้ดแจ้งเตือน:** ปรับฟังก์ชันส่งข้อมูลเป็นสองวิธี และหากส่งข้อมูลไม่ผ่านจริงด้วยวิธี Google Form (เช่น URL ผิด หรือติดปัญหาอื่นๆ) ระบบจะฟ้อง Error ขึ้นหน้าจอทันที ไม่ปล่อยให้แสดงข้อความสำเร็จเหมือนเดิม
3.  **มีระบบเขียนข้อมูลตรง (Direct Write):** เพิ่มตัวเลือกบันทึกข้อมูลตรงเข้าสู่ Google Sheets โดยตรง หากคุณได้ทำการแชร์สิทธิ์ให้กับ Service Account ของ Google Cloud แล้ว คุณสามารถเลือกช่องแรกเพื่อข้ามความยุ่งยากของ Google Form และทำให้ข้อมูลเข้าไปรวมในชีตได้ทันทีครับ
4.  **เพิ่มความแข็งแกร่งในระบบบันทึกทริปการเดินทาง:** จัดรูปแบบตารางและล้างชื่อช่องว่างที่คอลัมน์เพื่อความแม่นยำยิ่งขึ้นครับ

คุณสามารถคัดลอกส่วนของโค้ดปรับปรุงใหม่นี้ไปแทนที่ไฟล์เดิมของคุณ และอัปโหลดขึ้นทดสอบบนระบบโฮสของ Streamlit ได้ทันทีเลยครับ! สำหรับความช่วยเหลือเกี่ยวกับการสมัครและรับส่งข้อมูลผ่าน Google Sheets เพิ่มเติม วิดีโอแนะนำนี้เป็นประโยชน์มากครับ

* [วิดีโอคู่มือการเชื่อมต่อและเขียนข้อมูลไปยัง Google Sheets](https://www.youtube.com/watch?v=_G5f7og_Dpo): วิดีโอนี้สอนวิธีการตั้งค่าการเข้าถึง Google Sheets ด้วย Streamlit และจัดทำแบบฟอร์มเพื่อบันทึกข้อมูลย้อนกลับเข้าไปยังตารางแบบละเอียด ช่วยให้เข้าใจถึงความสำคัญของระบบสิทธิ์ความปลอดภัย (Credentials) และการจัดการเขียนไฟล์ได้อย่างดีครับ



http://googleusercontent.com/youtube_content/0
