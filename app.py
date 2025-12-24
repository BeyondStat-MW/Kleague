import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# --- Page Config ---
st.set_page_config(
    page_title="Kleague Solution",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed" # 사이드바 숨김
)

# --- CSS Styling for "Rounded Box" & Layout ---
st.markdown("""
<style>
    /* 상단 헤더 숨기기 (옵션) */
    header {visibility: hidden;}
    
    /* 메인 컨테이너 상단 여백 제거 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    
    /* 둥근 테두리 박스 스타일 */
    .round-box {
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 20px;
        background-color: #ffffff;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #ff4b4b;
    }
    
    /* 필터 영역 스타일 */
    .filter-container {
        border: 1px solid #f0f0f0;
        border-radius: 10px;
        padding: 15px;
        background-color: #f9f9f9;
        margin-bottom: 20px;
    }
    
    /* Metric & Chart Titles */
    .chart-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 10px;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- Login Logic ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    password = st.session_state['password_input']
    if password == "team1234":
        st.session_state['logged_in'] = True

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("## 🔒 BeyondStat Team Login")
        st.text_input("비밀번호", type="password", key="password_input", on_change=check_login)
        st.button("로그인", on_click=check_login)
    st.stop()

# Define SERVICE_ACCOUNT_FILE for BigQuery authentication
# This should point to your service account key file
SERVICE_ACCOUNT_FILE = "service-account-key.json" 

# --- Custom Navbar Styles ---
custom_css = """
<style>
    /* [Custom Navbar Styles] Radio Button을 텍스트 배너로 변환 */
    /* 1. 라디오 버튼 컨테이너 중앙 정렬 */
    [data-testid="stRadio"] > div {
        display: flex;
        justify-content: center;
        gap: 30px; /* 메뉴 사이 간격 넓게 */
        background-color: transparent;
    }

    /* 2. 라디오 버튼의 '원(Circle)' 숨기기 - 이게 핵심 */
    [data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* 3. 라벨 텍스트 스타일링 (배너 느낌) */
    [data-testid="stRadio"] label {
        background-color: transparent !important;
        border: none !important;
        cursor: pointer !important;
        padding: 5px 10px !important;
        transition: all 0.2s;
    }
    
    /* 4. 마우스 오버 시 효과 */
    [data-testid="stRadio"] label:hover {
        transform: scale(1.05); /* 살짝 커짐 */
        color: #000040 !important;
    }

    /* 5. 텍스트 폰트 설정 (24px, Bold) */
    [data-testid="stRadio"] p {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #888888; /* 기본은 회색 */
    }

    /* 6. 선택된 항목 강조 (Bold & Black) */
    /* Streamlit 라디오 선택 상태 감지 Trick: 
       div[role="radiogroup"] 내부의 aria-checked="true"인 요소 타겟팅이 필요함.
       하지만 CSS만으로 상위 p태그 색상을 바꾸긴 어려우므로, 
       기본적으로 '선택된 느낌'은 텍스트 색상 차이로 줌.
       (Streamlit은 선택된 input의 형제 p태그에 색상을 자동으로 입히지 않음. 
        대신 테마 Primary Color가 적용됨. 여기서는 회색->검정/남색 변화 유도)
    */ 
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Data Loading (Detect Project ID) ---
@st.cache_data(ttl=600)
def load_data(data_project, dataset, table):
    credentials = None
    project_id = None
    
    # 1. Try Loading from Secrets (for Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        try:
            scopes = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/drive"]
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )
            project_id = credentials.project_id
        except Exception as e:
            pass # Fallback to file

    # 2. Try Loading from Local File (for Local Development)
    if not credentials:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
            project_id = credentials.project_id
        else:
            raise FileNotFoundError(f"인증 파일(\'{SERVICE_ACCOUNT_FILE}\')을 찾을 수 없고, Secrets 설정도 없습니다.")
    
    # Client 생성
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    # 데이터 조회
    query = f"SELECT * FROM `{data_project}.{dataset}.{table}`"
    
    try:
        query_job = client.query(query)
        df = query_job.to_dataframe()
        return df
    except Exception as e:
        raise Exception(f"Query failed for `{data_project}.{dataset}.{table}`: {str(e)}")

# 사이드바에서 프로젝트 ID 입력 받기 (옵션)
# st.sidebar.header("Configuration")
# custom_project_id = st.sidebar.text_input("BigQuery Project ID", value="kleague-482106") # Default value updated

# Load Data
try:
    # Use custom ID if provided, otherwise default to None (load_data handles it)
    df_raw = load_data("kleague-482106", "Kleague_db", "measurements")
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

# --- Data Processing ---
def process_data(df):
    df_clean = df.copy()
    
    # 컬럼명 정규화 (BigQuery 결과가 'Birth_Date' 또는 'Birth_date'로 올 수 있음)
    if 'Birth_Date' in df_clean.columns:
        df_clean.rename(columns={'Birth_Date': 'Birth_date'}, inplace=True)
    
    # 숫자 변환
    numeric_cols = [
        'Height', 'Weight', 'Age', 'APHV', 
        '_5m_sec_', '_10m_sec_', '_30m_sec_', 
        'CMJ_Height_cm_', 'Flex', 'HamECC_L_N_', 'HamECC_R_N_'
    ]
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # 날짜 변환
    if 'Date' in df_clean.columns:
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')

    if 'Birth_date' in df_clean.columns:
        df_clean['Birth_date'] = pd.to_datetime(df_clean['Birth_date'], errors='coerce')
        df_clean['Birth_Year'] = df_clean['Birth_date'].dt.year
        df_clean['Birth_Month'] = df_clean['Birth_date'].dt.month
        
        # Quarter 계산
        df_clean['Birth_Quarter'] = df_clean['Birth_Month'].apply(lambda x: (x-1)//3 + 1 if pd.notnull(x) else 0)
        
        # 숫자형 변환 (오류 방지)
        df_clean['Birth_Year_Int'] = df_clean['Birth_Year'].fillna(0).astype(int)
    else:
        # 컬럼이 없을 경우 에러 방지를 위해 기본값 채움
        df_clean['Birth_Year_Int'] = 0
        df_clean['Birth_Quarter'] = 0
        
    return df_clean

df = process_data(df_raw)

# --- Navigation (Top Bar) ---

# 레이아웃 조정: 좌측(로고) - 중앙(메뉴) - 우측(계정)
# 중앙 정렬을 위해 비율 배분
header_col1, header_col2, header_col3 = st.columns([0.3, 0.45, 0.25])

with header_col1:
    # 로고와 타이틀
    c_img, c_txt = st.columns([0.25, 0.75]) 
    with c_img:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=70) # 너비 약간 조정
        else:
            st.write("⚽")
    with c_txt:
        # 타이틀 (26px)
        st.markdown("<h3 style='margin: 10px 0 0 -10px; font-size: 26px; white-space: nowrap;'><b>K League Youth Data Platform</b></h3>", unsafe_allow_html=True)

with header_col2:
    # 중앙 메뉴 (배너 스타일, 24px)
    # 라디오 버튼의 동그라미를 숨기고 텍스트만 표시하여 탭처럼 구현
    st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
    selected_tab = st.radio("Nav", ["K League", "Team", "Insight"], horizontal=True, label_visibility="collapsed")

with header_col3:
    # 우측 계정 정보
    st.markdown("<div style='text-align: right; padding-top: 15px;'>", unsafe_allow_html=True)
    st.markdown(f"""
        <span style='font-size: 14px; color: #555; margin-right: 15px;'>
            👤 <b>Admin</b> (Team1234)
        </span>
        <button style='
            background-color: transparent; border: 1px solid #ccc; border-radius: 4px; 
            padding: 5px 10px; cursor: pointer; font-size: 12px;'>
            ⚙️ 설정
        </button>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---") # 헤더와 본문 구분선

# ==========================================
# Tab: K League
# ==========================================
if selected_tab == "K League":
    # --- Filter Section ---
    with st.expander("🔻 Search Filters", expanded=True):
        with st.form("kleague_filter_form"):
            c1, c2, c3, c4, c5 = st.columns(5)
            
            # Helper to add "Select All" logic implicitly (Empty = All)
            
            # 1. Test_ID
            test_ids = sorted([x for x in df['Test_ID'].unique() if pd.notna(x)])
            sel_test_id = c1.multiselect("Test ID", test_ids, help="비워두면 전체 선택")
            
            # 2. Team
            teams = sorted([x for x in df['Team'].unique() if pd.notna(x)])
            sel_team = c2.multiselect("Team", teams)
            
            # 3. Under (U18, etc - needs explicit col check if exists, assuming 'Under' exists)
            unders = []
            if 'Under' in df.columns:
                unders = sorted([x for x in df['Under'].unique() if pd.notna(x)])
            sel_under = c3.multiselect("Under", unders)
            
            # 4. Birth_date (Year range)
            # Date range picker for birth date is specific. 
            # Let's use Year range for simplicity or allow Date Input
            min_date = df['Birth_Date'].min() if 'Birth_Date' in df.columns else None
            max_date = df['Birth_Date'].max() if 'Birth_Date' in df.columns else None
            sel_birth_date = c4.date_input("Birth Date Range", value=[]) # Empty by default
            
            # 5. Grade
            grades = sorted([x for x in df['Grade'].unique() if pd.notna(x)])
            sel_grade = c5.multiselect("Grade", grades)
            
            # 6. Apply Button
            col_apply = st.columns([6, 1])
            submitted = col_apply[1].form_submit_button("적용 (Apply)", type="primary")

    # --- Filter Logic ---
    df_filtered = df.copy()
    if submitted:
        if sel_test_id:
            df_filtered = df_filtered[df_filtered['Test_ID'].isin(sel_test_id)]
        if sel_team:
            df_filtered = df_filtered[df_filtered['Team'].isin(sel_team)]
        if sel_under:
            df_filtered = df_filtered[df_filtered['Under'].isin(sel_under)]
        if sel_grade:
            df_filtered = df_filtered[df_filtered['Grade'].isin(sel_grade)]
        # Birth Date Logic (if range selected)
        if isinstance(sel_birth_date, tuple) and len(sel_birth_date) == 2:
            start_d, end_d = sel_birth_date
            # Ensure proper datetime comparison
            df_filtered = df_filtered[
                (df_filtered['Birth_Date'].dt.date >= start_d) & 
                (df_filtered['Birth_Date'].dt.date <= end_d)
            ]

    # --- Dashboard Layout (Top) ---
    st.markdown("Results Found: **{}** Players".format(df_filtered['Player'].nunique()))
    
    # Layout: Left (Chart 1) | Right (Chart 2 & 3)
    # Using columns. Height alignment is tricky in raw Streamlit without custom components,
    # but we can try to render them in containers.
    
    # Layout: Outer Container for all 3 charts
    # 1. 2. 3. 차트를 모두 감싸는 큰 둥근 박스
    with st.container(border=True):
        
        # 3단 컬럼: [차트1 (좌)]  [구분선 (중)]  [차트2&3 (우)]
        col_left, col_sep, col_right = st.columns([1, 0.05, 1.4])
        
        # [1번 차트] 전체 측정선수 수 (좌측)
        with col_left:
            # 개별 border 제거
            st.markdown("<div class='chart-title' style='margin-bottom: 10px;'>1. 전체 측정선수 수</div>", unsafe_allow_html=True)
            
            total_players = df_filtered['Player'].nunique()
            grade_counts = df_filtered.groupby('Grade')['Player'].nunique().reset_index()
            if grade_counts.empty:
                grade_counts = pd.DataFrame({'Grade': ['None'], 'Player': [0]})

            fig1 = px.pie(grade_counts, values='Player', names='Grade', hole=0.6)
            fig1.update_layout(
                annotations=[dict(text=str(total_players), x=0.5, y=0.5, font_size=40, showarrow=False)],
                showlegend=True,
                margin=dict(t=20, b=20, l=20, r=20),
                height=500 # 높이 유지
            )
            st.plotly_chart(fig1, use_container_width=True)

        # [중앙 구분선]
        with col_sep:
            # 높이 500px 정도의 수직선 그리기
            st.markdown(
                """
                <div style='
                    border-left: 1px solid #e0e0e0; 
                    height: 520px; 
                    margin: auto; 
                    width: 1px;
                '></div>
                """, 
                unsafe_allow_html=True
            )

        # [2번 & 3번 차트] (우측)
        with col_right:
            
            # [2번] RAE
            # 개별 border 제거
            st.markdown("<div class='chart-title' style='margin-bottom: 5px;'>2. Relative Age Effect (RAE)</div>", unsafe_allow_html=True)
            
            if not df_filtered.empty and 'Birth_Year_Int' in df_filtered.columns and 'Birth_Quarter' in df_filtered.columns:
                rae_df = df_filtered[df_filtered['Birth_Year_Int'] > 0]
                
                # 데이터가 있는지 확인
                if not rae_df.empty:
                    # Pivot: Index=Birth_Quarter(Q1~Q4), Columns=Birth_Year
                    rae_pivot = rae_df.groupby(['Birth_Quarter', 'Birth_Year_Int'])['Player'].nunique().reset_index()
                    rae_pivot = rae_pivot.pivot(index='Birth_Quarter', columns='Birth_Year_Int', values='Player').fillna(0).astype(int)
                    
                    # 인덱스 이름 변경
                    rae_pivot.index = ['Q' + str(i) for i in rae_pivot.index]
                    
                    max_val = rae_pivot.max().max()
                    
                    # HTML 테이블 생성
                    html = """
                    <style>
                        .rae-table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }
                        .rae-table th { background-color: #f0f2f6; padding: 8px; border-bottom: 2px solid #ddd; font-weight: bold; text-align: center;}
                        .rae-table td { padding: 5px; border-bottom: 1px solid #eee; position: relative; vertical-align: middle; height: 30px;}
                        .rae-bar-bg { position: absolute; top: 10%; left: 0; height: 80%; opacity: 0.3; z-index: 0; border-radius: 3px; }
                        .rae-val { position: relative; z-index: 1; padding-left: 5px; font-weight: 500;}
                    </style>
                    <table class="rae-table">
                        <thead>
                            <tr>
                                <th style="width: 50px;"></th>
                    """
                    for col in rae_pivot.columns:
                        html += f"<th>{col}</th>"
                    html += "</tr></thead><tbody>"
                    
                    row_colors = {'Q1': '#4c78a8', 'Q2': '#f58518', 'Q3': '#bab0ac', 'Q4': '#8c564b'}
                    
                    for idx_name in rae_pivot.index:
                        color = row_colors.get(str(idx_name)[:2], '#333')
                        html += f"<tr><td style='font-weight:bold; color:{color}; text-align:center;'>{idx_name}</td>"
                        for col in rae_pivot.columns:
                            val = rae_pivot.loc[idx_name, col]
                            if val > 0:
                                pct = (val / max_val) * 100
                                bar_html = f"<div class='rae-bar-bg' style='width: {pct}%; background-color: {color};'></div>"
                                val_html = f"<span class='rae-val'>{val}</span>"
                                html += f"<td>{bar_html}{val_html}</td>"
                            else:
                                html += "<td></td>"
                        html += "</tr>"
                    html += "</tbody></table>"
                    
                    # border=False 설정 (스크롤 컨테이너는 유지하되 박스는 안 보이게)
                    with st.container(height=250, border=False):
                        st.markdown(html, unsafe_allow_html=True)
                else:
                    st.info("No Data for RAE (Filtered)")
            else:
                st.info("No Data for RAE (Missing Columns)")

            st.write("") # 간격

            # [3번] 신체성숙도 (Maturity)
            # 개별 border 제거
            st.markdown("<div class='chart-title' style='margin-bottom: 5px;'>3. 신체성숙도 (APHV)</div>", unsafe_allow_html=True)
            
            if 'APHV' in df_filtered.columns and not df_filtered.empty:
                aphv_df = df_filtered[['Player', 'APHV']].drop_duplicates().dropna()
                
                def get_aphv_color(val):
                    if val < 13.1: return 'Early (<13.1)'
                    elif val <= 15.1: return 'Average (13.1-15.1)'
                    else: return 'Late (>15.1)'
                
                aphv_df['Category'] = aphv_df['APHV'].apply(get_aphv_color)
                
                fig3 = px.strip(
                    aphv_df, x="APHV", color="Category",
                    color_discrete_map={
                        'Early (<13.1)': '#ff4b4b',
                        'Average (13.1-15.1)': '#20c997',
                        'Late (>15.1)': '#fcc419'
                    },
                    stripmode='overlay'
                )
                
                fig3.add_vline(x=13.1, line_dash="dash", line_color="gray", annotation_text="13.1")
                fig3.add_vline(x=15.1, line_dash="dash", line_color="gray", annotation_text="15.1")
                
                fig3.update_layout(
                    height=190, 
                    margin=dict(t=30, b=10, l=10, r=10),
                    showlegend=True,
                    yaxis=dict(visible=False),
                    xaxis=dict(title="APHV (Years)"),
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=1,
                        title=None
                    ) 
                )
                fig3.update_traces(jitter=0.5) 
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No APHV Data")

# ==========================================
# Tab: Team
# ==========================================
elif selected_tab == "Team":
    st.header("Team Analysis")
    st.info("준비 중입니다. (Phase 3)")
    
    # Team Filter Logic Skeleton
    # sel_team_tab = st.selectbox("Team Select", teams)
    # players_in_team = df[df['Team'] == sel_team_tab]['Player'].unique()
    # sel_player_tab = st.selectbox("Player Select", players_in_team)
    # ...

# ==========================================
# Tab: Insight
# ==========================================
elif selected_tab == "Insight":
    st.header("Insight")
    st.info("준비 중입니다.")
