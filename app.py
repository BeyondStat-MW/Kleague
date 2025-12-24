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
    
    /* 메인 컨테이너 상단 여백 제거 (최소화: 1rem -> 0.1rem) */
    .block-container {
        padding-top: 0.1rem !important;
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
        gap: 20px; /* 메뉴 사이 간격 축소 (30 -> 20) */
        background-color: transparent;
        margin-top: -10px; /* 위쪽 여백 강제 축소 */
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
        padding: 0px 5px !important; /* 패딩 축소 */
        transition: all 0.2s;
    }
    
    /* 4. 마우스 오버 시 효과 */
    [data-testid="stRadio"] label:hover {
        transform: scale(1.05); /* 살짝 커짐 */
        color: #000040 !important;
    }

    /* 5. 텍스트 폰트 설정 (축소: 24px -> 25px, Bold) */
    [data-testid="stRadio"] p {
        font-size: 25px !important;
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

# 레이아웃 조정: 좌측(로고+타이틀) - 중앙(메뉴) - 우측(계정)
# 중앙 정렬을 위해 비율 배분 (타이틀 길이 고려하여 좌우 비율 조정)
header_col1, header_col2, header_col3 = st.columns([0.35, 0.3, 0.35])

# 로고 base64 인코딩 함수 (이미지 broken 방지)
import base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

logo_path = "assets/logo.png"
logo_html = ""
if os.path.exists(logo_path):
    logo_base64 = get_base64_of_bin_file(logo_path)
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" width="70" style="vertical-align: middle;">'
else:
    logo_html = "⚽"

with header_col1:
    # 로고와 타이틀
    # st.image 대신 HTML로 직접 렌더링하여 패딩/마진 제어
    # Flexbox를 사용하여 수직 중앙 정렬
    st.markdown(f"""
    <div style="display: flex; align-items: center; height: 60px;">
        <div style="margin-right: 15px;">{logo_html}</div>
        <div style="font-size: 35px; font-weight: bold; white-space: nowrap; line-height: 1;">
            K League Youth Data Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    # 중앙 메뉴 (25px)
    # 수직 정렬: 타이틀(35px)과 시각적 중심을 맞춤
    # 타이틀이 커졌으므로 메뉴의 padding-top을 미세 조정 (12px -> 14px)
    st.markdown("<div style='padding-top: 14px;'></div>", unsafe_allow_html=True)
    selected_tab = st.radio("Nav", ["K League", "Team", "Insight"], horizontal=True, label_visibility="collapsed")

with header_col3:
    # 우측 계정 정보 (더 오른쪽으로 이동)
    # Spacer | User | Button 배분
    col_space, col_user, col_set = st.columns([0.2, 0.6, 0.2])
    
    # 텍스트 수직 위치 조정 (폰트 14px)
    # 타이틀 높이(60px) 고려하여 중앙 정렬 느낌 (padding-top: 22px)
    col_user.markdown("<div style='text-align:right; font-size:14px; padding-top:22px;'>👤 Admin (Team1234)</div>", unsafe_allow_html=True)
    
    # 버튼 위치 조정
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            margin-top: 12px; 
            height: 35px; /* 버튼 높이 고정 (선택 사항) */
        }
        </style>
        """, unsafe_allow_html=True)
    col_set.button("⚙️", key="settings_btn", help="Account Settings")

st.markdown("---") # 헤더와 본문 구분선

# ==========================================
# Tab: K League
# ==========================================
if selected_tab == "K League":
    # --- Filter Section ---
    # 기본적으로 접혀있도록 expanded=False 설정
    with st.expander("🔻 Search Filters", expanded=False):
        with st.form("kleague_filter_form"):
            # 가로 배치: Test ID | Team | Under | Birth Year | Grade | Apply
            # 비율 조정: 버튼은 작게
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 0.5])
            
            # 1. Test_ID
            test_ids = sorted([x for x in df['Test_ID'].unique() if pd.notna(x)])
            sel_test_id = c1.multiselect("Test ID", test_ids, help="비워두면 전체 선택")
            
            # 2. Team
            teams = sorted([x for x in df['Team'].unique() if pd.notna(x)])
            sel_team = c2.multiselect("Team", teams)
            
            # 3. Under
            unders = []
            if 'Under' in df.columns:
                unders = sorted([x for x in df['Under'].unique() if pd.notna(x)])
            sel_under = c3.multiselect("Under", unders)
            
            # 4. Birth Year (변경: Date Input -> Multiselect)
            birth_years = sorted([x for x in df['Birth_Year_Int'].unique() if x > 0])
            sel_birth_year = c4.multiselect("Birth Year", birth_years)
            
            # 5. Grade
            grades = sorted([x for x in df['Grade'].unique() if pd.notna(x)])
            sel_grade = c5.multiselect("Grade", grades)
            
            # 6. Apply Button (Grade 오른쪽에 배치)
            # 수직 정렬을 맞추기 위해 빈 공간 추가 (st.write("")로 조절하거나 Label을 안보이게 처리)
            c6.write("") 
            c6.write("")
            submitted = c6.form_submit_button("Apply", type="primary", use_container_width=True)

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
        # Birth Year Logic
        if sel_birth_year:
            df_filtered = df_filtered[df_filtered['Birth_Year_Int'].isin(sel_birth_year)]

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
            st.markdown("<div class='chart-title' style='margin-bottom: 10px;'>전체 측정선수 수</div>", unsafe_allow_html=True)
            
            total_players = df_filtered['Player'].nunique()
            grade_counts = df_filtered.groupby('Grade')['Player'].nunique().reset_index()
            if grade_counts.empty:
                grade_counts = pd.DataFrame({'Grade': ['None'], 'Player': [0]})

            fig1 = px.pie(grade_counts, values='Player', names='Grade', hole=0.6)
            fig1.update_layout(
                annotations=[dict(text=str(total_players), x=0.5, y=0.5, font_size=24, showarrow=False)], # 폰트 사이즈 축소
                showlegend=True,
                margin=dict(t=10, b=10, l=10, r=10),
                height=300 # 높이 조정 (350 -> 300)
            )
            st.plotly_chart(fig1, use_container_width=True)

        # [중앙 구분선]
        with col_sep:
            # 높이 조정 (360 -> 310)
            st.markdown(
                """
                <div style='
                    border-left: 1px solid #e0e0e0; 
                    height: 310px; 
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
            st.markdown("<div class='chart-title' style='margin-bottom: 5px; font-size: 14px;'>Relative Age Effect (RAE)</div>", unsafe_allow_html=True)
            
            if not df_filtered.empty and 'Birth_Year_Int' in df_filtered.columns and 'Birth_Quarter' in df_filtered.columns:
                rae_df = df_filtered[df_filtered['Birth_Year_Int'] > 0]
                
                # 데이터가 있는지 확인
                if not rae_df.empty:
                    # Pivot: Index=Birth_Quarter(Q1~Q4), Columns=Birth_Year
                    rae_pivot = rae_df.groupby(['Birth_Quarter', 'Birth_Year_Int'])['Player'].nunique().reset_index()
                    rae_pivot = rae_pivot.pivot(index='Birth_Quarter', columns='Birth_Year_Int', values='Player').fillna(0).astype(int)
                    
                    # 인덱스 이름 변경 (1.0 -> 1 -> Q1)
                    # int 변환 후 str 변환으로 소수점 제거
                    rae_pivot.index = ['Q' + str(int(i)) for i in rae_pivot.index]
                    
                    max_val = rae_pivot.max().max()
                    
                    # HTML 테이블 생성
                    # 높이 축소를 위해 td height 조정 (30px -> 22px)
                    html = """
                    <style>
                        .rae-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
                        .rae-table th { background-color: #f0f2f6; padding: 4px; border-bottom: 2px solid #ddd; font-weight: bold; text-align: center;}
                        .rae-table td { padding: 2px; border-bottom: 1px solid #eee; position: relative; vertical-align: middle; height: 20px;}
                        .rae-bar-bg { position: absolute; top: 15%; left: 0; height: 70%; opacity: 0.3; z-index: 0; border-radius: 2px; }
                        .rae-val { position: relative; z-index: 1; padding-left: 5px; font-weight: 500;}
                    </style>
                    <table class="rae-table">
                        <thead>
                            <tr>
                                <th style="width: 35px;"></th>
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
                    # 높이 축소 (160 -> 140)
                    with st.container(height=140, border=False):
                        st.markdown(html, unsafe_allow_html=True)
                else:
                    st.info("No Data for RAE (Filtered)")
            else:
                st.info("No Data for RAE (Missing Columns)")

            st.write("") # 간격

            # [3번] 신체성숙도 (Maturity)
            # 개별 border 제거
            st.markdown("<div class='chart-title' style='margin-bottom: 5px; font-size: 14px;'>신체성숙도 (APHV)</div>", unsafe_allow_html=True)
            
            if 'APHV' in df_filtered.columns and not df_filtered.empty:
                # [복구] 중복 제거 없이(또는 값 기준 중복 제거만) 모든 데이터 표시 요청
                aphv_df = df_filtered[['Player', 'APHV']].drop_duplicates().dropna()
                
                def get_aphv_color(val):
                    if val < 13.1: return 'Early'
                    elif val <= 15.1: return 'Average'
                    else: return 'Late'
                
                aphv_df['Category'] = aphv_df['APHV'].apply(get_aphv_color)
                
                # 통계 계산
                early_count = aphv_df[aphv_df['Category'] == 'Early'].shape[0]
                avg_count = aphv_df[aphv_df['Category'] == 'Average'].shape[0]
                late_count = aphv_df[aphv_df['Category'] == 'Late'].shape[0]
                
                # 위치 계산 (Annotation용) - 고객 요청에 따른 구간 중간값 고정
                # 1. Early: 11.8 ~ 13.1 -> (11.8 + 13.1) / 2 = 12.45
                # 2. Average: 13.1 ~ 15.1 -> (13.1 + 15.1) / 2 = 14.1
                # 3. Late: 15.1 ~ 15.5 -> (15.1 + 15.5) / 2 = 15.3
                early_pos = 12.45
                avg_pos = 14.1
                late_pos = 15.3
                
                fig3 = px.strip(
                    aphv_df, x="APHV", color="Category",
                    color_discrete_map={
                        'Early': '#d62728',   # Red
                        'Average': '#4db6ac', # Teal
                        'Late': '#f4c150'     # Yellow
                    },
                    stripmode='overlay'
                )
                
                # 수직선 (Reference Lines)
                fig3.add_vline(x=13.1, line_width=1, line_color="#333")
                fig3.add_vline(x=15.1, line_width=1, line_color="#333")
                
                # 텍스트 및 카운트 어노테이션 (이미지 참조)
                annotations = []
                
                # 1. Early
                if early_count > 0:
                    annotations.append(dict(x=early_pos, y=0.55, text=f"{early_count}명", showarrow=False, font=dict(color='#d62728', size=12, weight='bold')))
                    annotations.append(dict(x=early_pos, y=-0.55, text="Early", showarrow=False, font=dict(color='#d62728', size=12, weight='bold')))

                # 2. Average
                if avg_count > 0:
                    annotations.append(dict(x=avg_pos, y=0.55, text=f"{avg_count}명", showarrow=False, font=dict(color='#4db6ac', size=12, weight='bold')))
                    annotations.append(dict(x=avg_pos, y=-0.55, text="Average", showarrow=False, font=dict(color='#4db6ac', size=12, weight='bold')))
                    
                # 3. Late
                if late_count > 0:
                    annotations.append(dict(x=late_pos, y=0.55, text=f"{late_count}명", showarrow=False, font=dict(color='#f4c150', size=12, weight='bold')))
                    annotations.append(dict(x=late_pos, y=-0.55, text="Late", showarrow=False, font=dict(color='#f4c150', size=12, weight='bold')))
                
                # 기준선 텍스트 (13.1, 15.1) - 라인 아래쪽
                annotations.append(dict(x=13.15, y=-0.8, text="13.1", showarrow=False, xanchor="left", font=dict(size=9, color="black")))
                annotations.append(dict(x=15.15, y=-0.8, text="15.1", showarrow=False, xanchor="left", font=dict(size=9, color="black")))

                fig3.update_layout(
                    height=130, # 높이 조정 (190 -> 150 -> 130)
                    margin=dict(t=20, b=10, l=10, r=10), # 여백 미세 조정
                    showlegend=False, # 범례 숨김 (어노테이션으로 대체)
                    yaxis=dict(visible=False, range=[-1, 1]), # Y축 숨기고 Range 설정하여 텍스트 공간 확보
                    xaxis=dict(visible=False, range=[11.8, 15.5]), # X축 숨김 및 범위 고정
                    annotations=annotations,
                    plot_bgcolor='white'
                )
                
                # Bar 스타일과 유사하게 보이도록 Strip plot 설정
                fig3.update_traces(jitter=0.5, opacity=0.8, marker=dict(size=8, line=dict(width=0))) 
                
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
