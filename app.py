import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Page Configuration
st.set_page_config(
    page_title="Kleague Dashboard",
    page_icon="⚽",
    layout="wide"
)

# --- Login Logic ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    password = st.session_state['password_input']
    if password == "team1234":
        st.session_state['logged_in'] = True
        st.success("로그인 성공!")
        # rerun은 더 이상 필요하지 않을 수 있으나, 확실한 화면 전환을 위해 사용
    else:
        st.error("비밀번호가 틀렸습니다.")

# 로그인 안 된 상태
if not st.session_state['logged_in']:
    st.markdown("## 🔒 BeyondStat Team Login")
    st.markdown("관계자 외 접근을 금지합니다.")
    
    st.text_input("비밀번호를 입력하세요:", type="password", key="password_input", on_change=check_login)
    st.button("로그인", on_click=check_login)
    st.stop()  # 여기서 코드 실행 중단

# --- Dashboard Logic (로그인 된 상태에서만 실행됨) ---

# BigQuery Settings
# SERVICE_ACCOUNT_FILE 변수 삭제 및 Secrets 사용 알림
DEFAULT_PROJECT_ID = "kleague-482106"
DEFAULT_DATASET_ID = "Kleague_db"
DEFAULT_TABLE_ID = "measurements"

# Sidebar - Settings
st.sidebar.header("🛠 Settings")
with st.sidebar.expander("BigQuery Config", expanded=False):
    DATA_PROJECT_ID = st.text_input("Project ID", value=DEFAULT_PROJECT_ID)
    DATASET_ID = st.text_input("Dataset ID", value=DEFAULT_DATASET_ID)
    TABLE_ID = st.text_input("Table ID", value=DEFAULT_TABLE_ID)

@st.cache_data(ttl=600)
def load_data(data_project, dataset, table):
    # Secrets 확인
    if "gcp_service_account" not in st.secrets:
        return None, "Streamlit Secrets에 'gcp_service_account' 정보가 없습니다. 배포 설정에서 Secrets를 입력해주세요."
    
    try:
        scopes = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/drive"]
        
        # from_service_account_info 사용 (Secrets는 딕셔너리처럼 동작)
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=scopes
        )
        
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        
        # Load all data as STRING first (safe mode)
        query = f"SELECT * FROM `{data_project}.{dataset}.{table}`"
        query_job = client.query(query)
        df = query_job.to_dataframe()
        return df, None
    except Exception as e:
        return None, str(e)

def process_data(df):
    """
    STRING으로 로드된 데이터를 분석 가능한 형태(숫자/날짜)로 변환합니다.
    """
    df_clean = df.copy()
    
    # 1. 숫자 변환 대상 컬럼
    numeric_cols = [
        'Height', 'Weight', 'Age', 
        '_5m_sec_', '_10m_sec_', '_30m_sec_', 
        'CMJ_Height_cm_', 'Flex', 'HamECC_L_N_', 'HamECC_R_N_'
    ]
    
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # 2. 날짜 변환
    if 'Date' in df_clean.columns:
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')
        
    return df_clean

# Main App
st.title("⚽ Kleague Player Dashboard")
st.markdown("---")

# Data Loading
df_raw, error = load_data(DATA_PROJECT_ID, DATASET_ID, TABLE_ID)

if error:
    st.error("데이터 로드 실패")
    st.error(error)
    st.stop()

if df_raw is None or df_raw.empty:
    st.warning("데이터가 없습니다.")
    st.stop()

# Data Processing
df = process_data(df_raw)

# Sidebar - Player Filter
st.sidebar.header("🔍 Player Filter")

# 선수 목록 추출 (None 제외, 가나다순)
player_list = sorted([p for p in df['Player'].unique() if p is not None and str(p) != 'nan'])

if not player_list:
    st.error("선수 데이터(Player 컬럼)를 찾을 수 없습니다.")
    st.stop()

selected_player = st.sidebar.selectbox("선수 선택 (Name)", player_list)

# Filter Data by Player
# 최신이 위로 오도록 정렬
player_df = df[df['Player'] == selected_player].sort_values(by='Date', ascending=False)

if player_df.empty:
    st.warning(f"'{selected_player}' 선수의 데이터가 없습니다.")
    st.stop()

# 최신 데이터 가져오기
latest_record = player_df.iloc[0]

# --- 1. Key Metrics ---
st.subheader(f"📌 {selected_player} 선수 프로필")
m1, m2, m3, m4 = st.columns(4)

team_name = latest_record.get('Team', '-')
measure_date = latest_record.get('Date', '-')
if pd.notnull(measure_date):
    measure_date = measure_date.strftime('%Y-%m-%d')

height = latest_record.get('Height', 0)
weight = latest_record.get('Weight', 0)

m1.metric("소속팀", team_name)
m2.metric("최근 측정일", str(measure_date))
m3.metric("신장 (Height)", f"{height:.1f} cm")
m4.metric("체중 (Weight)", f"{weight:.1f} kg")

st.markdown("---")

# --- 2. Charts ---
c1, c2 = st.columns([1, 1.5])

# Chart 1: Radar Chart (Physical Capability)
with c1:
    st.markdown("### 🕸️ 신체 능력 (Radar)")
    
    # 데이터 매핑 (없는 경우 0 처리)
    flex = latest_record.get('Flex', 0) if pd.notna(latest_record.get('Flex')) else 0
    jump = latest_record.get('CMJ_Height_cm_', 0) if pd.notna(latest_record.get('CMJ_Height_cm_')) else 0
    sprint = latest_record.get('_10m_sec_', 0) if pd.notna(latest_record.get('_10m_sec_')) else 0
    strength = latest_record.get('HamECC_R_N_', 0) if pd.notna(latest_record.get('HamECC_R_N_')) else 0
    weight_stat = weight
    
    categories = ['유연성(Flex)', '점프력(CMJ)', '순발력(10m)', '근력(Ham R)', '체중']
    values = [flex, jump, sprint, strength, weight_stat]
    
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=selected_player
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True)
        ),
        margin=dict(t=20, b=20, l=40, r=40)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# Chart 2: Line Chart (History)
with c2:
    st.markdown("### 📈 변화 추이 (History)")
    
    target_metric = st.selectbox("확인할 지표를 선택하세요:", 
                                 ['Weight', 'Height', 'Flex', 'CMJ_Height_cm_', '_10m_sec_'])
    
    # 과거 데이터 (오름차순 정렬)
    history_df = player_df.sort_values(by='Date')
    
    if target_metric in history_df.columns: 
        fig_line = px.line(history_df, x='Date', y=target_metric, markers=True, title=f"{target_metric} 변화")
        fig_line.update_layout(xaxis_title="측정 일자", yaxis_title="수치")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info(f"'{target_metric}' 데이터가 없습니다.")

# --- 3. Data Table ---
st.markdown("### 📋 상세 기록 (Data Table)")
st.dataframe(player_df, use_container_width=True)
