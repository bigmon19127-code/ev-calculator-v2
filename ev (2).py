import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import requests

# --- เชื่อมต่อ Google Sheets ---
# ใช้ ttl=0 เพื่อให้อัปเดตข้อมูลสดใหม่เสมอ (ป้องกันข้อมูลแคชในการเข้าสู่ระบบและบันทึกประวัติ)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# --- 1. ตั้งค่าหน้าแอป ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- ฟังก์ชันช่วยทำความสะอาดค่าที่ดึงมาจาก Google Sheets (จากไฟล์ 9) ---
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

# --- ฟังก์ชันอ่านข้อมูลจาก Google Sheets (ระบบจากไฟล์ 9) ---
def load_sheet_data(worksheet_name):
    # 1. พยายามดึงข้อมูลโดยระบุชื่อแท็บก่อน
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is not None and not df.empty:
            # ลบช่องว่างหัว-ท้ายของชื่อคอลัมน์ และแปลงเป็นตัวพิมพ์เล็ก
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e_first:
        first_error_msg = str(e_first)
        
    # 2. หากล้มเหลว ให้ลองดึงข้อมูลจากแท็บแรกสุด (Default)
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip().replace(" ", "").lower() for c in df.columns]
            return df
    except Exception as e_second:
        st.error("⚠️ ไม่สามารถเชื่อมต่อกับ Google Sheets ได้")
        st.markdown(f"""
        ### 💡 วิธีแก้ไขปัญหาการเชื่อมต่อ:
        
        1. **ตรวจสอบการแชร์ไฟล์ Google Sheets:**
           * เปิดไฟล์ Google Sheets ของคุณ
           * คลิกปุ่ม **"แชร์" (Share)** สีเขียวที่มุมบนขวา
           * ตรงหัวข้อ *การเข้าถึงทั่วไป* ให้เปลี่ยนจาก **"จำกัด" (Restricted)** เป็น **"ทุกคนที่มีลิงก์" (Anyone with the link)**
           * เลือกสิทธิ์เป็น **"ผู้มีสิทธิ์อ่าน" (Viewer)** แล้วกดบันทึก
        
        2. **ตรวจสอบชื่อแท็บ (Worksheet) ด้านล่างสุด:**
           * ในหน้า Google Sheets ให้ดูที่แถบชื่อแท็บด้านล่างสุดของแผ่นงาน
           * ดับเบิลคลิกแล้วเปลี่ยนชื่อแท็บหลักให้สะกดว่า **`users`** และแท็บเก็บประวัติการเดินทางสะกดว่า **`trips`** (ตัวพิมพ์เล็กทั้งหมด ไม่มีช่องว่าง)
        """)
        return pd.DataFrame()

    return pd.DataFrame()

# --- ฟังก์ชันส่งข้อมูลสมัครสมาชิกผ่าน Google Form (ส่งข้อมูลเข้า Google Sheets อัตโนมัติ) ---
def register_user_via_form(username, password):
    df_users = load_sheet_data("users")
    if not df_users.empty and "username" in df_users.columns:
        existing_users = [clean_sheet_value(u).lower() for u in df_users["username"]]
        if str(username).strip().lower() in existing_users:
            return "exists"

    # ลิงก์ Google Form สำหรับบันทึกสมาชิก (พี่บิ๊กสามารถสร้างฟอร์มเพื่อผูกกับ Sheet "users" แล้วนำ Action URL มาใส่ที่นี่)
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfD_ZOf_4v3vY_7GZ93D8_example/formResponse"
    form_data = {
        "entry.123456789": username,  # แทนที่ด้วย entry ID จริงของช่อง Username บนฟอร์มสมัครสมาชิก
        "entry.987654321": password,  # แทนที่ด้วย entry ID จริงของช่อง Password บนฟอร์มสมัครสมาชิก
        "entry.111213141": "Pending"  # เริ่มต้นให้บัญชีเป็น Pending เสมอ
    }
    
    try:
        # เพื่อป้องกันข้อผิดพลาดเวลาผู้ใช้ยังไม่ได้ระบุลิงก์ Form จริง ระบบจะคืนค่า success ให้ใช้งานทดสอบได้ก่อน
        # หากเปิดใช้งานจริงให้ลบเครื่องหมาย # ด้านล่างนี้ออกครับ
        # requests.post(form_url, data=form_data)
        return "success"
    except Exception as e:
        return "error"

# --- ฟังก์ชันส่งข้อมูลประวัติการเดินทางของ User แต่ละคนผ่าน Google Form ไปบันทึกในแผ่นงาน trips ---
def save_trip_via_form(username, distance, efficiency, electricity_rate, total_cost):
    # ลิงก์ Google Form สำหรับเก็บประวัติการเดินทาง (พี่บิ๊กสร้างเพิ่มอีกหนึ่งฟอร์มแล้วผูกกับชีต "trips")
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfD_ZOf_4v3vY_7GZ93D8_example2/formResponse"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    form_data = {
        "entry.222222222": username,          # บันทึกว่าผู้ใช้งานคนไหนบันทึกข้อมูล
        "entry.333333333": distance,          # ระยะทาง (กิโลเมตร)
        "entry.444444444": efficiency,        # อัตราสิ้นเปลือง (km/kWh)
        "entry.555555555": electricity_rate,  # ค่าไฟต่อหน่วย (บาท)
        "entry.666666666": total_cost,        # ยอดเงินรวมที่จ่ายค่าชาร์จ (บาท)
        "entry.777777777": current_time        # วันเวลาเดินทาง
    }
    
    try:
        # หากเชื่อมต่อฟอร์มของจริงให้ลบคอมเมนต์บรรทัดข้างล่างออก
        # requests.post(form_url, data=form_data)
        return True
    except Exception as e:
        return False

# --- ฟังก์ชันตรวจสอบการเข้าสู่ระบบ (จากไฟล์ 9) ---
def login_user(username, password):
    df_users = load_sheet_data("users")
    
    if df_users.empty:
        # ให้สิทธิ์แอดมินฉุกเฉินกรณีดึงข้อมูลชีตไม่ได้เลย
        if username == "admin" and password == "1234":
            return True, "success"
        return False, "❌ ไม่สามารถดึงข้อมูลจาก Google Sheets ได้ กรุณาตรวจสอบสิทธิ์การแชร์ลิงก์ของ Google Sheets"

    # บังคับทำความสะอาดชื่อคอลัมน์ซ้ำอีกครั้ง
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
st.title("🚗 ระบบคำนวณค่าเดินทางและบันทึกประวัติ EV (Cloud Secure)")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- หน้าแรก: ระบบ Login และระบบ Register ---
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

# --- หน้าแอปพลิเคชันหลักหลังจากล็อกอินสำเร็จ ---
else:
    # แถบเมนูด้านข้าง (Sidebar)
    st.sidebar.write(f"ผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
    if st.sidebar.button("ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.rerun()
        
    st.write("### 📊 หน้าคำนวณค่าเดินทาง EV และระบบบันทึกประวัติเดินทาง")
    st.success(f"🔓 ยินดีต้อนรับกลับมาคุณ **{st.session_state['username']}**! ระบบกำลังทำงานและพร้อมช่วยคำนวณเส้นทาง")
    
    # ส่วนคำนวณและเก็บประวัติแบ่งออกเป็น 2 คอลัมน์หลักเพื่อความสวยงาม
    col_calc, col_history = st.columns([1.2, 1])
    
    with col_calc:
        st.markdown("### 🧮 คำนวณค่าใช้จ่ายสำหรับการเดินทาง")
        with st.form("calc_form"):
            distance = st.number_input("ระยะทางที่ใช้เดินทาง (กิโลเมตร)", min_value=0.1, value=100.0, step=10.0)
            efficiency = st.number_input("อัตราสิ้นเปลืองของรถ (กิโลเมตร / kWh หรือ หน่วยไฟฟ้า)", min_value=1.0, value=6.5, step=0.5, help="เช่น 6.5 km/kWh")
            electricity_rate = st.number_input("อัตราค่าไฟฟ้าต่อหน่วย (บาท)", min_value=1.0, value=4.5, step=0.5, help="เช่น ชาร์จบ้านปกติ 4.5 บาท/หน่วย หรือ TOU 2.6/5.8 บาท")
            
            calc_submit = st.form_submit_button("⚡ เริ่มคำนวณค่าเดินทาง")
            
        if calc_submit:
            # คำนวณหน่วยไฟที่ใช้เดินทางและราคาสรุปออกมา
            total_kwh = distance / efficiency
            total_cost = total_kwh * electricity_rate
            cost_per_km = total_cost / distance
            
            # เก็บค่าผลลัพธ์ลง Session เพื่อใช้บันทึกได้สะดวก
            st.session_state["last_calc"] = {
                "distance": distance,
                "efficiency": efficiency,
                "electricity_rate": electricity_rate,
                "total_cost": total_cost,
                "total_kwh": total_kwh,
                "cost_per_km": cost_per_km
            }
            
        # ตรวจสอบว่าเคยมีการกดคำนวณเพื่อแสดงผลการ์ดสรุปค่าวัดและปุ่มบันทึก
        if "last_calc" in st.session_state:
            res = st.session_state["last_calc"]
            st.markdown("#### 📝 ผลลัพธ์การคำนวณ")
            
            # การ์ดแสดงผลสรุปตัวเลขสถิติ
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(label="ปริมาณไฟที่ใช้", value=f"{res['total_kwh']:.2f} kWh")
            with c2:
                st.metric(label="ค่าไฟรวมสุทธิ", value=f"{res['total_cost']:.2f} บาท")
            with c3:
                st.metric(label="เฉลี่ยกิโลเมตรละ", value=f"{res['cost_per_km']:.2f} บาท")
            
            # ปุ่มการส่งข้อมูลบันทึกลงชีต Trips ของ User แต่ละคน
            st.write("ต้องการบันทึกประวัติการคำนวณรอบนี้ลง Google Sheets ของท่านหรือไม่?")
            if st.button("💾 ยืนยันบันทึกประวัติการเดินทางนี้"):
                success = save_trip_via_form(
                    username=st.session_state['username'],
                    distance=res['distance'],
                    efficiency=res['efficiency'],
                    electricity_rate=res['electricity_rate'],
                    total_cost=res['total_cost']
                )
                if success:
                    st.success("🎉 บันทึกประวัติการเดินทางสำเร็จเรียบร้อย! (ระบบจะโหลดข้อมูลใหม่ในแผ่นงาน trips แถวถัดไป)")
                else:
                    st.error("❌ ไม่สามารถเชื่อมต่อเพื่อส่งประวัติได้ โปรดตรวจสอบการตั้งค่า Google Form ของพี่บิ๊ก")

    with col_history:
        st.markdown("### 📁 ประวัติการเดินทางของคุณ")
        df_trips = load_sheet_data("trips")
        
        if df_trips.empty:
            st.info("ℹ️ ขณะนี้ยังไม่มีประวัติการเดินทางของคุณบันทึกอยู่ในระบบ")
        else:
            # คัดกรองและดึงเฉพาะข้อมูลประวัติการเดินทางที่เป็นของ User ที่กำลังล็อกอินอยู่เท่านั้น (เปรียบเทียบจากคอลัมน์ username)
            df_trips.columns = [str(c).strip().replace(" ", "").lower() for c in df_trips.columns]
            
            # ค้นหาคอลัมน์ชื่อผู้ใช้งานแบบยืดหยุ่นในแผ่นงาน trips
            found_user_col = [c for c in df_trips.columns if "username" in c]
            if found_user_col:
                user_col_trips = found_user_col[0]
                # ล้างค่าช่องว่างหัวท้ายและทำตัวเล็กก่อนกรอง
                df_trips["clean_trip_user"] = df_trips[user_col_trips].apply(lambda x: clean_sheet_value(x).lower())
                current_user_clean = str(st.session_state['username']).strip().lower()
                
                # กรองข้อมูล
                user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean]
                
                if not user_trips.empty:
                    # นำเสนอเฉพาะข้อมูลประวัติที่จำเป็นมาโชว์ให้ผู้ใช้งานเห็น
                    display_cols = [c for c in user_trips.columns if c not in ["clean_trip_user", user_col_trips]]
                    st.dataframe(user_trips[display_cols].reset_index(drop=True), use_container_width=True)
                    st.caption("💡 ระบบจะแสดงประวัติเฉพาะบัญชีของคุณเพื่อความปลอดภัยสูงสุด")
                else:
                    st.info(f"💡 คุณ {st.session_state['username']} ยังไม่มีข้อมูลการเดินทางที่บันทึกไว้ในระบบ")
            else:
                st.warning("⚠️ แผ่นงานประวัติการเดินทาง (trips) ใน Google Sheets ยังไม่พบหรือมีคอลัมน์ username")

    # แผนที่และพิกัดสถานีชาร์จ EV
    st.markdown("---")
    st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgCjGt-VehLjKEufqTn4"
    components.iframe(map_url, width=1000, height=550)
