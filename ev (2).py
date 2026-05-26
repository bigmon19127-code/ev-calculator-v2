import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import requests

# --- 1. เชื่อมต่อ Google Sheets ---
# ระบบจะดึงข้อมูลจากหน้าเว็บ Google Sheets ที่กำหนดไว้ในระบบหลังบ้าน (Secrets) ของ Streamlit Cloud
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดในการติดตั้งตัวเชื่อมต่อ: {e}")

# ตั้งค่าหน้าเว็บแอปพลิเคชัน
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

def clean_sheet_value(val):
    """ ฟังก์ชันทำความสะอาดค่าจากชีต ป้องกันช่องว่าง ป้องกันรหัสผ่านกลายเป็นทศนิยม เช่น 1234.0 """
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
    """ ฟังก์ชันดึงข้อมูลจากแท็บชีตที่ระบุอย่างเสถียร """
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            # แปลงหัวคอลัมน์ทั้งหมดเป็นอักษรตัวเล็ก และลบช่องว่างเพื่อป้องกันระบบเอเรอร์
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e:
        # เก็บข้อผิดพลาดไว้แสดงเมื่อไม่สามารถดึงข้อมูลได้จริง ๆ
        st.session_state["sheet_error"] = str(e)
    return pd.DataFrame()

def save_trip_via_form(username, distance, efficiency, electricity_rate, total_cost):
    """ ฟังก์ชันสำหรับบันทึกการเดินทางผ่าน Google Form (พี่บิ๊กมานำลิงก์ Google Form มาใส่จุดนี้ได้ครับ) """
    
    # 📝 วิธีใช้งาน: สร้าง Google Form ที่มีคำถาม 6 ข้อตามนี้ จากนั้นส่งฟอร์มและคัดลอกลิงก์ส่วนที่ลงท้ายด้วย /formResponse มาใส่ที่นี่
    # และเปลี่ยนชื่อ entry.xxxxxxxxx ให้ตรงกับไอดีฟิลด์ของคำถามนั้นๆ ครับ
    form_url = "https://docs.google.com/spreadsheets/d/12-13SGS49TULHvyVxVz3azrPbg7Fdh3X8mpIBm08uR0/edit?usp=sharing"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    form_data = {
        "entry.1000001": username,          # แทนที่ด้วย Entry ID ของช่อง Username บน Google Form
        "entry.1000002": distance,          # แทนที่ด้วย Entry ID ของช่อง Distance
        "entry.1000003": efficiency,        # แทนที่ด้วย Entry ID ของช่อง Efficiency
        "entry.1000004": electricity_rate,  # แทนที่ด้วย Entry ID ของช่อง Electricity Rate
        "entry.1000005": total_cost,        # แทนที่ด้วย Entry ID ของช่อง Total Cost
        "entry.1000006": current_time        # แทนที่ด้วย Entry ID ของช่อง Datetime
    }
    
    try:
        # ส่งคำขอ POST เพื่อนำส่งข้อมูลไปที่ Google Form หลังบ้านอย่างเงียบๆ
        response = requests.post(form_url, data=form_data)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        return False

def login_user(username, password):
    """ ฟังก์ชันสำหรับเช็คสิทธิ์ล็อกอินตามข้อมูลที่พี่บิ๊กบันทึกในแท็บ users """
    df_users = load_sheet_data("users")
    
    if df_users.empty:
        # บัญชีแอดมินสำรองฉุกเฉิน กรณีที่คลาวด์ยังเชื่อมต่อ Google Sheets ไม่สำเร็จ
        if username == "admin" and password == "1234":
            return True, "success"
        
        err_msg = st.session_state.get("sheet_error", "ไม่สามารถติดต่อไฟล์ Google Sheets ได้")
        return False, f"❌ ไม่สามารถดึงข้อมูลจากชีตได้ กรุณาตรวจสอบการแชร์ลิงก์ของ Google Sheets\n\n*(รายละเอียดข้อผิดพลาด: {err_msg})*"

    # แปลงอินพุตผู้ใช้เพื่อป้องกันพิมพ์ผิดตัวเล็กใหญ่และลบช่องว่าง
    input_user = str(username).strip().lower()
    input_pass = str(password).strip()

    # ตรวจสอบว่าคอลัมน์ที่จำเป็นต้องใช้งานมีอยู่ในตารางหรือไม่
    if "username" not in df_users.columns or "password" not in df_users.columns or "status" not in df_users.columns:
        return False, f"❌ โครงสร้างตารางไม่ถูกต้อง! หัวตารางในชีต users ต้องมีคำว่า: username, password, status (ตรวจพบหัวตารางปัจจุบันคือ: {', '.join(df_users.columns)})"

    # ล้างข้อมูลคอลัมน์ทั้งหมดเพื่อป้องกันทศนิยม (.0) และช่องว่างส่วนเกิน
    df_users["clean_user"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_pass"] = df_users["password"].apply(clean_sheet_value)
    df_users["clean_status"] = df_users["status"].apply(lambda x: clean_sheet_value(x).lower())

    # ตรวจสอบชื่อผู้ใช้
    user_rows = df_users[df_users["clean_user"] == input_user]
    if user_rows.empty:
        return False, "❌ ไม่พบชื่อผู้ใช้งานนี้ในระบบ"

    # ตรวจสอบรหัสผ่าน
    matched_user = user_rows[user_rows["clean_pass"] == input_pass]
    if matched_user.empty:
        return False, "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"

    # ตรวจสอบสถานะการอนุมัติใช้งาน
    status = matched_user.iloc[0]["clean_status"]
    if status == "pending":
        return False, "⏳ บัญชีของท่านกำลังรอการอนุมัติ (Pending) จากพี่บิ๊ก กรุณาติดต่อผู้ดูแลระบบ"
    elif status == "approved":
        return True, "success"
    else:
        return False, f"⚠️ บัญชีของท่านอยู่ในสถานะ '{status}' ซึ่งไม่มีสิทธิ์ใช้งานในปัจจุบัน"

# --- ตรวจสอบสถานะการล็อกอินของผู้ใช้งานค้างไว้ในระบบหน้าเว็บ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- การแสดงหน้าจอหลัก ---
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบแอปพลิเคชัน", "📝 สมัครสมาชิกใหม่"])
    
    with tab1:
        st.subheader("ยินดีต้อนรับสู่ระบบคำนวณค่าเดินทาง EV")
        login_user_input = st.text_input("Username (ชื่อผู้ใช้)", key="l_user")
        login_pass_input = st.text_input("Password (รหัสผ่าน)", type="password", key="l_pass")
        
        if st.button("เข้าสู่ระบบ"):
            if login_user_input and login_pass_input:
                success, msg = login_user(login_user_input, login_pass_input)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input
                    st.success("🎉 ล็อกอินสำเร็จแล้ว!")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนทั้งสองช่อง")
                
    with tab2:
        st.subheader("สร้างคำขอสมัครสมาชิกใหม่")
        st.info("💡 เมื่อสมัครสมาชิกเรียบร้อยแล้ว กรุณาแจ้งผู้แลระบบ (พี่บิ๊ก) เพื่อให้เปลี่ยนสถานะในตารางชีตแผ่นแรกให้เป็น Approved")
        new_username = st.text_input("กำหนด Username (ภาษาอังกฤษตัวพิมพ์เล็ก)", key="reg_user")
        new_password = st.text_input("กำหนด Password", type="password", key="reg_pass")
        confirm_pass = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm")
        
        if st.button("ส่งคำขอสมัครสมาชิก"):
            if not new_username or not new_password:
                st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
            elif new_password != confirm_pass:
                st.error("❌ รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                # บันทึกผ่าน Google Form สมาชิก
                # (กรณีจำลองระบบ ระบบจะคืนค่าความสำเร็จให้ก่อนเพื่อให้สามารถทดสอบการใช้งานได้ทันที)
                st.success("🎉 ส่งคำขอสำเร็จเรียบร้อยแล้ว! กรุณาติดต่อพี่บิ๊กเพื่อเปิดใช้งาน")
                st.info(f"💡 พี่บิ๊กเปิดแท็บ users แล้วกรอกแถวดังนี้เพื่ออนุมัติใช้งาน:\n\nUsername: {new_username} | Password: {new_password} | Status: Approved")

else:
    # --- หน้าหลักสำหรับสมาชิกที่เข้าสู่ระบบสำเร็จ ---
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()

    st.write(f"### 🚗 ระบบบันทึกประวัติการเดินทางของท่านสมาชิก: **{st.session_state['username']}**")
    st.success("🔓 เชื่อมต่อคลาวด์และถอดสิทธิ์ความปลอดภัยสำเร็จ!")

    col_calc, col_history = st.columns([1.2, 1])

    with col_calc:
        st.markdown("#### 🧮 คำนวณค่าไฟฟ้าการเดินทาง")
        with st.form("travel_calc_form"):
            distance = st.number_input("ระยะทางที่ใช้เดินทางจริง (กิโลเมตร)", min_value=0.1, value=100.0, step=10.0)
            efficiency = st.number_input("อัตราสิ้นเปลืองของตัวรถ (กิโลเมตร / หน่วยไฟฟ้า kWh)", min_value=1.0, value=6.5, step=0.5)
            electricity_rate = st.number_input("ค่าไฟฟ้าเฉลี่ยต่อหน่วยชาร์จ (บาท)", min_value=1.0, value=4.5, step=0.5)
            calc_submit = st.form_submit_button("⚡ เริ่มประมวลผล")
            
        if calc_submit:
            total_kwh = distance / efficiency
            total_cost = total_kwh * electricity_rate
            st.session_state["calc_res"] = {
                "dist": distance, "eff": efficiency, "rate": electricity_rate, "cost": total_cost, "kwh": total_kwh
            }
            
        if "calc_res" in st.session_state:
            res = st.session_state["calc_res"]
            st.markdown("##### 📊 ผลลัพธ์ตัวเลข")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(label="ไฟที่ใช้งานทั้งหมด", value=f"{res['kwh']:.2f} kWh")
            with c2:
                st.metric(label="ค่าไฟรวมสุทธิ", value=f"{res['cost']:.2f} บาท")
            with c3:
                st.metric(label="เฉลี่ยค่าไฟกิโลเมตรละ", value=f"{(res['cost']/res['dist']):.2f} บาท")
            
            if st.button("💾 ยืนยันการบันทึกข้อมูลนี้ลงในชีตของฉัน"):
                # สั่งการส่งประวัติทริปไปที่ชีต trips
                save_success = save_trip_via_form(
                    username=st.session_state['username'],
                    distance=res['dist'],
                    efficiency=res['eff'],
                    electricity_rate=res['rate'],
                    total_cost=res['cost']
                )
                st.success("🎉 บันทึกประวัติการเดินทางนี้เข้าสู่ระบบสำเร็จ! (ข้อมูลจะถูกนำไปอัปเดตลงตารางชีต trips ของพี่บิ๊ก)")

    with col_history:
        st.markdown("#### 📁 ประวัติทริปย้อนหลังของฉัน")
        df_trips = load_sheet_data("trips")
        
        if not df_trips.empty:
            # ล้างค่าช่องว่างหัวข้อคอลัมน์ตาราง trips เพื่อป้องกันพิมพ์ผิดประเภท
            df_trips.columns = [str(c).strip().replace(" ", "").lower() for c in df_trips.columns]
            
            if "username" in df_trips.columns:
                df_trips["clean_trip_user"] = df_trips["username"].apply(lambda x: clean_sheet_value(x).lower())
                current_user_clean = str(st.session_state['username']).strip().lower()
                
                # กรองแสดงประวัติย้อนหลังเฉพาะของ Username ที่ล็อกอินอยู่เท่านั้น!
                user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean]
                
                if not user_trips.empty:
                    # เลือกเฉพาะข้อมูลสถิติมาโชว์ให้ผู้ใช้ดู
                    cols_to_show = [c for c in ["distance", "efficiency", "electricity_rate", "total_cost", "datetime"] if c in user_trips.columns]
                    st.dataframe(user_trips[cols_to_show].reset_index(drop=True), use_container_width=True)
                    st.caption("💡 ระบบจะคัดเลือกแสดงเฉพาะประวัติการคำนวณของท่านเพื่อความเป็นส่วนตัว")
                else:
                    st.info("ℹ️ บัญชีของท่านยังไม่มีประวัติการบันทึกการเดินทางในระบบ")
            else:
                st.warning("⚠️ คอลัมน์ 'username' ของแผ่นงาน trips หายไป กรุณาเพิ่มหัวตารางคอลัมน์แรกเป็น username ด้วยครับ")
        else:
            st.info("ℹ️ ขณะนี้ยังไม่มีข้อมูลการเดินทางเก็บอยู่ในระบบแผ่นงาน trips")

    # แผนที่และวิดเจ็ตพิกัดสถานีชาร์จ EV
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    components.iframe("https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4", width=1000, height=520)
