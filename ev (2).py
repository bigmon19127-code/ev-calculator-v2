import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# --- 1. ตั้งค่าหน้าแอป ---
st.set_page_config(page_title="ระบบคำนวณค่าเดินทาง EV", page_icon="🚗", layout="wide")

# --- 2. การเชื่อมต่อ Google Sheets ผ่าน Streamlit Connection ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("🔒 กรุณาตั้งค่าข้อมูล Secrets [connections.gsheets] บนหน้าแดชบอร์ด Streamlit ก่อนใช้งาน")
    st.stop()

# ฟังก์ชันอ่านข้อมูลจากชีต (ดึงข้อมูลล่าสุดเสมอ)
def load_sheet_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl="0")
    except Exception:
        # หากยังไม่มีหน้าชีตนี้ ให้ส่งตารางเปล่ากลับไป
        return pd.DataFrame()

# ฟังก์ชันสร้างตารางเริ่มต้นใน Google Sheets (กรณีชีตว่างเปล่า)
def init_google_sheets():
    # ตรวจสอบและสร้างหน้า users
    df_users = load_sheet_data("users")
    if df_users.empty or "username" not in df_users.columns:
        default_users = pd.DataFrame([
            {"username": "vip", "password": "1234", "status": "Approved"},
            {"username": "admin", "password": "9999", "status": "Approved"}
        ])
        conn.update(worksheet="users", data=default_users)
        
    # ตรวจสอบและสร้างหน้า trips
    df_trips = load_sheet_data("trips")
    if df_trips.empty or "user_id" not in df_trips.columns:
        default_trips = pd.DataFrame(columns=["user_id", "trip_date", "vehicle_type", "distance", "total_cost"])
        conn.update(worksheet="trips", data=default_trips)

init_google_sheets()

# ฟังก์ชันลงทะเบียนสมาชิกใหม่ (บันทึกลงชีตหน้า users)
def register_user(username, password):
    df_users = load_sheet_data("users")
    
    # ตรวจสอบชื่อผู้ใช้งานซ้ำ
    if not df_users.empty and username in df_users["username"].values:
        return "exists"
        
    new_row = pd.DataFrame([{"username": username, "password": str(password), "status": "Pending"}])
    df_updated = pd.concat([df_users, new_row], ignore_index=True)
    conn.update(worksheet="users", data=df_updated)
    return "success"

# ฟังก์ชันตรวจสอบสิทธิ์การล็อกอินและสถานะการอนุมัติ
def check_user_credentials(username, password):
    df_users = load_sheet_data("users")
    if df_users.empty:
        return "not_found"
        
    # ค้นหาแถวของผู้ใช้งาน
    user_row = df_users[(df_users["username"] == username) & (df_users["password"].astype(str) == str(password))]
    
    if user_row.empty:
        return "wrong_credentials"
        
    status = user_row.iloc[0]["status"]
    if status != "Approved":
        return "pending_approval"
        
    return "approved"

# ฟังก์ชันบันทึกประวัติการเดินทาง (บันทึกลงชีตหน้า trips)
def save_trip(user_id, vehicle_type, distance, total_cost):
    df_trips = load_sheet_data("trips")
    new_row = pd.DataFrame([{
        "user_id": user_id,
        "trip_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vehicle_type": vehicle_type,
        "distance": float(distance),
        "total_cost": round(float(total_cost), 2)
    }])
    df_updated = pd.concat([df_trips, new_row], ignore_index=True)
    conn.update(worksheet="trips", data=df_updated)

# ฟังก์ชันดึงประวัติการเดินทางมาสรุปยอดรายเดือน
def get_monthly_history(user_id):
    df_trips = load_sheet_data("trips")
    if df_trips.empty or "user_id" not in df_trips.columns:
        return pd.DataFrame()
        
    # กรองเฉพาะทริปของยูสเซอร์รายนั้น
    user_trips = df_trips[df_trips["user_id"] == user_id].copy()
    if user_trips.empty:
        return pd.DataFrame()
        
    # จัดกลุ่มแยกตามเดือนและประเภทรถ
    user_trips["trip_date"] = pd.to_datetime(user_trips["trip_date"])
    user_trips["เดือนที่เดินทาง"] = user_trips["trip_date"].dt.strftime("%Y-%m")
    
    summary = user_trips.groupby(["เดือนที่เดินทาง", "vehicle_type"]).agg(
        จำนวนทริป_ครั้ง=("total_cost", "count"),
        ระยะทางรวม_กม=("distance", "sum"),
        ค่าใช้จ่ายรวม_บาท=("total_cost", "sum")
    ).reset_index()
    
    summary.columns = ["เดือนที่เดินทาง", "ประเภทรถ", "จำนวนทริป (ครั้ง)", "ระยะทางรวม (กม.)", "ค่าใช้จ่ายรวม (บาท)"]
    return summary.sort_values(by="เดือนที่เดินทาง", ascending=False)

# --- 3. ระบบจัดการหน้ากากล็อกอิน ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

def logout_user():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if not st.session_state['logged_in']:
    st.title("🚗 ยินดีต้อนรับสู่ระบบคำนวณค่าเดินทาง (Cloud Secure)")
    tab_login, tab_register = st.tabs(["🔒 เข้าสู่ระบบ", "📝 สมัครสมาชิกใหม่"])
    
    with tab_login:
        with st.form("login_form"):
            st.subheader("กรุณากรอกข้อมูลบัญชีเพื่อเข้าใช้งาน")
            user_input = st.text_input("Username", key="login_user")
            pass_input = st.text_input("Password", type="password", key="login_pass")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                result = check_user_credentials(user_input, pass_input)
                if result == "approved":
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user_input
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                elif result == "pending_approval":
                    st.warning("⚠️ บัญชีนี้กำลังรอผู้ดูแลระบบตรวจสอบอนุมัติสิทธิ์การใช้งาน (ยังล็อกอินไม่ได้)")
                else:
                    st.error("❌ Username หรือ Password ไม่ถูกต้อง")
                    
    with tab_register:
        with st.form("register_form"):
            st.subheader("สร้างบัญชีผู้ใช้งานใหม่")
            new_user = st.text_input("กำหนด Username (ภาษาอังกฤษ)", key="reg_user").strip()
            new_pass = st.text_input("กำหนด Password", type="password", key="reg_pass")
            confirm_pass = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm")
            register_button = st.form_submit_button("ส่งคำขอสมัครสมาชิก")
            
            if register_button:
                if not new_user or not new_pass:
                    st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                elif new_pass != confirm_pass:
                    st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                else:
                    reg_result = register_user(new_user, new_pass)
                    if reg_result == "success":
                        st.success("🎉 ส่งคำขอสำเร็จ! บัญชีของคุณถูกส่งเข้าระบบรอผู้ดูแลระบบกดอนุมัติสิทธิ์ (Approved) ก่อนจึงจะเข้าใช้ได้")
                    else:
                        st.error("❌ Username นี้มีผู้ใช้งานในระบบแล้ว กรุณาเลือกชื่ออื่น")
    st.stop()

# ==========================================
# --- 4. เนื้อหาโปรแกรมหลัก (เมื่ออนุมัติและ Login แล้ว) ---
# ==========================================
st.sidebar.button("🚪 ออกจากระบบ", on_click=logout_user)
st.sidebar.markdown(f"👤 สมาชิก: **{st.session_state['username']}**")

st.title(f'🚗 ระบบคำนวณค่าเดินทาง & แชร์พิกัด EV')

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
        st.info("✅ อัปเดตข้อมูลเข้า Google Sheets ถาวรเรียบร้อย")
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
        st.info("✅ อัปเดตข้อมูลเข้า Google Sheets ถาวรเรียบร้อย")
        st.rerun()

st.markdown("---")
st.header("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือน")
with st.expander(f"🔍 สรุปประวัติรายเดือนของท่าน ({st.session_state['username']})", expanded=True):
    history_df = get_monthly_history(st.session_state['username'])
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("💡 ยังไม่มีประวัติการเดินทางถูกบันทึก")

st.markdown("---")
st.header("🗺️ แผนที่พิกัดสถานีชาร์จ EV")
map_url = "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUYgGcjGt-VehLjKEufqTn4"
components.iframe(map_url, width=800, height=500)
