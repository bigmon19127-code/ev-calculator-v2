import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# 🌐 ผูกโดยตรงกับ Google Sheets ID ของพี่บิ๊กเพื่อความรวดเร็วและปลอดภัย
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/10hcY_rRilLkaXE_YvDGUktxdeAAJquu51nEwjq9ZV0E/edit?usp=sharing"

# ตั้งค่าส่วนหัวของหน้าเว็บแอปพลิเคชันให้แสดงผลเต็มจอแบบสมดุล
st.set_page_config(
    page_title="ระบบคำนวณค่าเดินทาง EV & น้ำมัน",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. ตัวเชื่อมต่อ Google Sheets ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"⚠️ เกิดข้อผิดพลาดทางเทคนิคในการสร้างตัวเชื่อมต่อฐานข้อมูล: {e}")

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
    """ ดึงข้อมูลจากตาราง Google Sheets ของพี่บิ๊กตามชื่อเวิร์กชีต """
    try:
        # ดึงตารางข้อมูลสดๆ จากระบบคลาวด์ Google Sheets
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=0)
        # เคลียร์ค่าว่างที่ดึงมาเกินความจำเป็น
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.session_state["db_error"] = f"ไม่สามารถเปิดแผ่นงาน '{worksheet_name}' ได้เนื่องจาก: {e}"
        # คืนค่าเป็นโครงสร้างตารางเปล่ามาตรฐานป้องกันโปรแกรมค้าง
        if worksheet_name == "users":
            return pd.DataFrame(columns=["username", "password", "status"])
        elif worksheet_name == "trips":
            return pd.DataFrame(columns=["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"])
        return pd.DataFrame()

# โหลดข้อมูลสำคัญมาเก็บไว้ที่ฝั่งหน่วยความจำชั่วคราวของเซสชันก่อนทำงาน
df_users = load_sheet_data("users")
df_trips = load_sheet_data("trips")

# จัดทำความสะอาดฟิลด์ที่สุ่มเสี่ยงต่อการผิดพลาดตอนเช็ค Username/Password
if not df_users.empty:
    df_users["clean_username"] = df_users["username"].apply(lambda x: clean_sheet_value(x).lower())
    df_users["clean_password"] = df_users["password"].apply(lambda x: clean_sheet_value(x))
    df_users["clean_status"] = df_users["status"].apply(lambda x: clean_sheet_value(x).strip())
else:
    df_users["clean_username"] = pd.Series(dtype=str)
    df_users["clean_password"] = pd.Series(dtype=str)
    df_users["clean_status"] = pd.Series(dtype=str)

# --- 2. ฟังก์ชันตรวจสอบสิทธิ์และสมัครสมาชิกแบบเรียลไทม์ผ่าน Google Sheets ---

def login_user(username_input, password_input):
    """ ตรวจสอบการลงชื่อเข้าใช้งานของสมาชิก """
    username_clean = str(username_input).strip().lower()
    password_clean = str(password_input).strip()
    
    if df_users.empty:
        return False, "ยังไม่มีข้อมูลผู้ใช้งานใดๆ ในระบบฐานข้อมูลกูเกิลชีต"
        
    # ค้นหาแถวของข้อมูลที่ชื่อผู้ใช้งานตรงกัน
    match = df_users[df_users["clean_username"] == username_clean]
    if match.empty:
        return False, "ไม่พบชื่อบัญชีผู้ใช้งานนี้ในระบบ กรุณาสมัครสมาชิก"
        
    user_record = match.iloc[0]
    if user_record["clean_password"] != password_clean:
        return False, "รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
        
    if user_record["clean_status"].lower() != "approved":
        return False, "บัญชีของคุณอยู่ระหว่างการรออนุมัติสิทธิ์ (Pending) กรุณาติดต่อผู้ดูแลระบบ"
        
    return True, f"ยินดีต้อนรับคุณ {user_record['username']}"

def register_user(username_input, password_input):
    """ บันทึกการสมัครสมาชิกใหม่ลง Google Sheets โดยตรง """
    username_clean = str(username_input).strip()
    username_clean_lower = username_clean.lower()
    password_clean = str(password_input).strip()
    
    if not username_clean or not password_clean:
        return False, "กรุณากรอกข้อมูล Username และ Password ให้ครบถ้วน"
        
    # ตรวจสอบชื่อผู้ใช้งานซ้ำซ้อนในระบบ
    if not df_users.empty and (df_users["clean_username"] == username_clean_lower).any():
        return False, "ชื่อบัญชีผู้ใช้งานนี้ถูกใช้ไปแล้วในระบบ กรุณาเลือกชื่ออื่น"
    
    # จัดเตรียมข้อมูลผู้สมัครสมาชิกรายใหม่
    new_member = pd.DataFrame([{
        "username": username_clean,
        "password": password_clean,
        "status": "Pending"  # รอการอนุมัติสิทธิ์จากแอดมินก่อนใช้งาน
    }])
    
    try:
        # ดึงไฟล์ดิบมาต่อหัว (หลีกเลี่ยงคอลัมน์ทำความสะอาดชั่วคราว)
        raw_users_df = df_users[["username", "password", "status"]].copy() if not df_users.empty else pd.DataFrame(columns=["username", "password", "status"])
        updated_users_df = pd.concat([raw_users_df, new_member], ignore_index=True)
        
        # ยิงบันทึกตรงกลับเข้า Google Sheet เพื่อความแน่นอน 100%
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="users", data=updated_users_df)
        return True, "สมัครสมาชิกเรียบร้อยแล้ว! กรุณารอผู้ดูแลระบบอนุมัติการใช้งาน (Approved)"
    except Exception as e:
        return False, f"ไม่สามารถสมัครสมาชิกได้เนื่องจากระบบคลาวด์ขัดข้อง: {e}"

def save_trip_data(username, distance, efficiency, electricity_rate, total_cost):
    """ ฟังก์ชันหลัก: เขียนบันทึกข้อมูลการเดินทางตรงเข้าสู่หน้า 'trips' บน Google Sheets """
    new_trip = pd.DataFrame([{
        "username": str(username).strip(),
        "distance": float(distance),
        "efficiency": float(efficiency),
        "electricity_rate": float(electricity_rate),
        "total_cost": round(float(total_cost), 2),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    try:
        # เตรียมคอลัมน์ดั้งเดิมให้ตรงกับหัวตารางเพื่อไม่ให้โครงสร้างพัง
        if not df_trips.empty:
            valid_cols = ["username", "distance", "efficiency", "electricity_rate", "total_cost", "datetime"]
            # กรองเผื่อมีคอลัมน์ขยะติดมา
            raw_trips_df = df_trips[[c for c in valid_cols if c in df_trips.columns]].copy()
            updated_trips_df = pd.concat([raw_trips_df, new_trip], ignore_index=True)
        else:
            updated_trips_df = new_trip
            
        # สั่งอัปเดตข้อมูลขึ้นคลาวด์เรียลไทม์
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="trips", data=updated_trips_df)
        return True, "บันทึกประวัติการเดินทางของคุณลงสู่ระบบเรียบร้อยแล้ว!"
    except Exception as e:
        return False, f"ระบบไม่สามารถอัปเดตข้อมูลลงชีตได้เนื่องจาก: {e}"

# --- 3. การจัดการสถานะในหน้าจอแก้ไข (Session State) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""

# --- 4. การจัดการหน้าจอผู้ใช้ (User Interface) ---

# แถบเมนูด้านซ้ายสำหรับออกจากระบบ
if st.session_state['logged_in']:
    with st.sidebar:
        st.markdown(f"### 👤 บัญชีผู้ใช้งานปัจจุบัน: **{st.session_state['username']}**")
        st.write("สถานะการอนุมัติสิทธิ์: **Approved** ✅")
        st.markdown("---")
        if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.success("ออกจากระบบเรียบร้อยแล้ว")
            st.rerun()

# ตรวจสอบการเข้าสู่ระบบหลัก
if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚗 ระบบคำนวณและบันทึกค่าใช้จ่ายการเดินทาง (EV vs น้ำมัน)</h2>", unsafe_style_allowed=True)
    st.write("---")
    
    # ตารางจัดสรรทางเลือกระหว่างการลงชื่อเข้าใช้งาน กับ การเปิดบัญชีผู้ใช้รายใหม่
    tab_login, tab_register = st.tabs(["🔐 ลงชื่อเข้าใช้งาน (Login)", "📝 สมัครสมาชิกใหม่ (Register)"])
    
    with tab_login:
        st.subheader("ยินดีต้อนรับกลับเข้าสู่ระบบ")
        login_user_input = st.text_input("ชื่อบัญชีผู้ใช้งาน (Username)", key="login_user_field")
        login_pass_input = st.text_input("รหัสผ่าน (Password)", type="password", key="login_pass_field")
        
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
                st.warning("⚠️ กรุณากรอกชื่อผู้ใช้งานและรหัสผ่านให้ครบถ้วน")
                
    with tab_register:
        st.subheader("สร้างบัญชีผู้ใช้งานใหม่")
        st.info("💡 หมายเหตุ: การสมัครสมาชิกใหม่จะเข้าสู่สถานะ รอการตรวจสอบ (Pending) โดยผู้ดูแลระบบ")
        reg_user_input = st.text_input("กำหนด Username (ภาษาอังกฤษเท่านั้น)", key="reg_user_field")
        reg_pass_input = st.text_input("กำหนด Password", type="password", key="reg_pass_field")
        reg_confirm_input = st.text_input("ยืนยัน Password อีกครั้ง", type="password", key="reg_confirm_field")
        
        if st.button("ส่งคำขอสมัครสมาชิก", use_container_width=True):
            if reg_user_input and reg_pass_input and reg_confirm_input:
                if reg_pass_input != reg_confirm_input:
                    st.error("⚠️ รหัสผ่านทั้งสองช่องไม่ตรงกัน กรุณาตรวจสอบ")
                elif not reg_user_input.isalnum():
                    st.error("⚠️ ชื่อผู้ใช้ควรประกอบด้วยภาษาอังกฤษหรือตัวเลขเท่านั้น")
                else:
                    success, msg = register_user(reg_user_input, reg_pass_input)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลส่วนตัวให้ครบทุกช่อง")

else:
    # หน้าแสดงผลหลักเมื่อล็อกอินผ่านสำเร็จ
    st.markdown(f"## 📊 ยินดีต้อนรับผู้ใช้งาน:คุณ {st.session_state['username']} เข้าสู่ระบบคำนวณค่าเดินทาง")
    st.write("---")
    
    # แยกหน้าต่างคำนวณการเดินทางออกเป็น 2 ฝั่งเพื่อเปรียบเทียบผลลัพธ์
    col_gas, col_ev = st.columns(2)
    
    with col_gas:
        st.markdown("<div style='background-color:#FEE2E2; padding:15px; border-radius:10px; border-left: 5px solid #EF4444;'>", unsafe_style_allowed=True)
        st.subheader("⛽ คำนวณและบันทึก (ค่าน้ำมัน)")
        
        gas_distance = st.number_input("ระยะทางเดินทางของรถน้ำมัน (กิโลเมตร)", min_value=0.0, step=1.0, value=100.0, key="gas_dist")
        gas_efficiency = st.number_input("อัตราประหยัดน้ำมัน (กิโลเมตรต่อลิตร)", min_value=1.0, step=0.1, value=15.0, key="gas_eff")
        gas_rate = st.number_input("ราคาน้ำมัน ณ ปัจจุบัน (บาทต่อลิตร)", min_value=1.0, step=0.1, value=38.5, key="gas_rate_val")
        
        # อัตราคำนวณ: ค่าน้ำมันทั้งหมด = (ระยะทาง / อัตราสิ้นเปลือง) * ราคาน้ำมันต่อลิตร
        gas_cost = (gas_distance / gas_efficiency) * gas_rate if gas_efficiency > 0 else 0.0
        st.metric(label="ประมาณการค่าใช้จ่ายรวม (ค่าน้ำมัน)", value=f"{gas_cost:,.2f} บาท")
        
        if st.button("💾 บันทึกประวัติเดินทาง (รถน้ำมัน)", type="primary", use_container_width=True):
            success, msg = save_trip_data(
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
        st.markdown("<div style='background-color:#DCFCE7; padding:15px; border-radius:10px; border-left: 5px solid #22C55E;'>", unsafe_style_allowed=True)
        st.subheader("⚡ คำนวณและบันทึก (ค่าไฟฟ้า EV)")
        
        ev_distance = st.number_input("ระยะทางเดินทางของรถไฟฟ้า EV (กิโลเมตร)", min_value=0.0, step=1.0, value=100.0, key="ev_dist")
        ev_efficiency = st.number_input("อัตราประหยัดไฟ (กิโลเมตรต่อกิโลวัตต์ชั่วโมง /หน่วย)", min_value=0.1, step=0.1, value=6.5, key="ev_eff")
        ev_rate = st.number_input("ราคาค่าไฟฟ้า ณ ปัจจุบัน (บาทต่อหน่วย)", min_value=1.0, step=0.1, value=4.7, key="ev_rate_val")
        
        # อัตราคำนวณ: ค่าไฟฟ้าทั้งหมด = (ระยะทาง / อัตราประหยัดไฟ) * ค่าไฟฟ้าต่อหน่วย
        ev_cost = (ev_distance / ev_efficiency) * ev_rate if ev_efficiency > 0 else 0.0
        st.metric(label="ประมาณการค่าใช้จ่ายรวม (ค่าไฟฟ้า EV)", value=f"{ev_cost:,.2f} บาท")
        
        if st.button("💾 บันทึกประวัติเดินทาง (รถไฟฟ้า EV)", type="primary", use_container_width=True):
            success, msg = save_trip_data(
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

    # --- 5. แสดงผลประวัติการเดินทางเฉพาะบัญชีผู้ใช้ปัจจุบัน ---
    st.write("---")
    st.subheader("📊 ตารางสรุปประวัติค่าใช้จ่ายรายเดือนของคุณ")
    
    if not df_trips.empty:
        # ทำความสะอาดข้อมูลหัวตารางป้องการสับสนเคสกรณีมีเว้นวรรค
        df_trips.columns = [c.strip() for c in df_trips.columns]
        
        # เช็คว่ามีคอลัมน์ username หรือไม่เพื่อทำการกรองคัดแยกข้อมูลคนใช้งาน
        user_cols = [c for c in df_trips.columns if c.lower() == "username"]
        if user_cols:
            real_user_col = user_cols[0]
            df_trips["clean_trip_user"] = df_trips[real_user_col].apply(lambda x: clean_sheet_value(x).lower())
            current_user_clean = str(st.session_state['username']).strip().lower()
            
            # คัดแสดงเฉพาะประวัติที่เป็นของผู้ลงชื่อเข้าใช้ปัจจุบันเท่านั้น
            user_trips = df_trips[df_trips["clean_trip_user"] == current_user_clean].copy()
            
            if not user_trips.empty:
                # ลบคอลัมน์คำนวณระบบเบื้องหลังทิ้งเพื่อสุนทรียภาพที่สวยงามตอนโชว์ตาราง
                cols_to_show = [c for c in user_trips.columns if c not in ["clean_trip_user", real_user_col]]
                
                # โชว์ข้อมูลตารางหลักในหน้าแอปพลิเคชัน
                st.dataframe(
                    user_trips[cols_to_show].reset_index(drop=True),
                    use_container_width=True
                )
                st.caption("💡 ข้อมูลประวัติการคำนวณค่าเดินทางของคุณได้รับการกรองคัดแยกมาจากเซิร์ฟเวอร์แบบเรียลไทม์")
            else:
                st.info("ℹ️ บัญชีของคุณยังไม่เคยมีการบันทึกข้อมูลการเดินทางในระบบนี้ เริ่มสร้างรายการแรกได้ที่เมนูด้านบนเลยครับ!")
        else:
            st.warning("⚠️ คีย์เชื่อมฐานข้อมูลไม่สมบูรณ์ (ไม่พบชื่อหัวข้อ username ในระบบคลาวด์)")
    else:
        st.info("ℹ️ ขณะนี้ฐานข้อมูลประวัติการเดินทางยังว่างอยู่")

    # --- 6. แผนที่สถานีชาร์จรถยนต์ไฟฟ้า EV ทั่วประเทศ ---
    st.write("---")
    st.subheader("🗺️ แผนที่พิกัดสถานีชาร์จ EV ทั่วไทย")
    
    components.iframe(
        "https://www.google.com/maps/d/u/0/embed?mid=12ieBRQK2FUVgcJGt-VehLjKEufqTn4",
        height=500,
        scrolling=True
    )
```
eof

และนี่คือส่วนของไฟล์ `requirements.txt` ที่ต้องเอาไปแทนที่ตัวเก่าบนหน้า GitHub ของพี่บิ๊กเพื่อความแน่ใจว่าระบบคลาวด์จะสามารถดึงไลบรารีทุกตัวติดตั้งได้อย่างลื่นไหลไร้รอยต่อครับ:

```text
ไลบรารีสำหรับรันแอปบนคลาวด์:requirements.txt
streamlit
pandas
streamlit-gsheets-connection
