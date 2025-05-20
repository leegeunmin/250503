import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import streamlit as st
import matplotlib.ticker as ticker  # 추가

plt.rcParams['font.family'] = 'NanumGothic Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 음수 부호 깨짐 방지

# 1) 비밀번호 설정
PASSWORD = "knp12345"  # 원하는 비밀번호로 바꿔주세요

# 1) 인증 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 2) 인증 UI
if not st.session_state.authenticated:
    pwd = st.text_input("🔒 비밀번호를 입력하세요", type="password", key="pwd")
    if st.button("로그인"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.success("✅ 인증 완료되었습니다!")
            # 버튼 클릭 시 자동으로 rerun 되므로 따로 호출 불필요
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")
    # 인증 전에는 여기서 스크립트 종료
    st.stop()


st.set_page_config(
    page_title="고양경찰서 범죄 취약지 안내",
    page_icon="🚔",
    layout="centered"
)

CSV_FILE_PATH = "File.csv"

df = pd.read_csv(CSV_FILE_PATH)

def load_patrol_data_from_csv(file_path):
    df = pd.read_csv(file_path)

    # 필수 컬럼 확인
    required_columns = ["행정동", "죄명", "월", "발생시간대"]
    if not all(col in df.columns for col in required_columns):
        st.error(f"CSV 파일에 필수 열({', '.join(required_columns)})이 누락되었습니다.")
        return None

    patrol_summary = {}

    grouped = df.groupby("행정동")

    for dong, group in grouped:
        patrol_summary[dong] = {
            "총건수": len(group),
            "월별 건수": group["월"].value_counts().sort_index().to_dict(),  # 예: {1: 12, 2: 9, ...}
            "죄명 분포": group["죄명"].value_counts().to_dict(),  # 예: {'절도': 22, '폭력': 15}
            "시간대 분포": group["발생시간대"].value_counts().to_dict()  # 예: {'야간': 30, '오전': 12}
        }

    return patrol_summary


## 요일 생성 함수 정의하기
def get_day(day):
    mapping = {
        '2-월': '월요일',
        '3-화': '화요일',
        '4-수': '수요일',
        '5-목': '목요일',
        '6-금': '금요일',
        '7-토': '토요일',
        '1-일': '일요일'
    }
    # mapping에 없으면 '알 수 없음'이나 빈 문자열 반환
    return mapping.get(day, '')

def draw_bar_chart(df, x_col, y_col=None, y_type='count'):
    labels = sorted(df[x_col].dropna().astype(str).unique())
    numbers = []
    for label in labels:
        df_labels = df[df[x_col] == label]
        if y_type == 'count':
            numbers.append(df_labels.shape[0])
        elif y_type == 'sum':
            assert df_labels[y_col].dtype == 'int64'
            numbers.append(df_labels[y_col].sum())
    fig = plt.figure(figsize=(5, 4))
    sns.barplot(x=labels, y=numbers)
    plt.xticks(rotation=60)
    return fig

dark_mode_toggle = st.checkbox("다크모드 전환", value=False)
if dark_mode_toggle:
    text_color = "white"
    bg_color = "#333333"
else:
    text_color = "black"
    bg_color = "white"

# 2. 월 선택 박스
month_options = sorted(df['월'].dropna().astype(int).unique())
selected_month = st.selectbox(
    "📅 분석할 월을 선택하세요", 
    options=month_options,
    format_func=lambda x: f"{x}월"
)

# 3. 선택한 월 기준 필터링
df_month = df[df['월'] == selected_month]

# 4. 행정동 선택 박스
dong_options = sorted(df_month['행정동'].dropna().unique())
selected_dong = st.selectbox(
    "🏘️ 배치된 행정동을 선택하세요",
    options=dong_options
)

# 5. 선택된 월 + 행정동 기준으로 최종 필터링
df_filtered = df_month[df_month['행정동'] == selected_dong]

# ✅ 죄명 선택 (다중 선택 가능)
crime_types = ['강간/강제추행', '절도', '폭력']
selected_crimes = st.multiselect("🔍 분석할 범죄유형 선택", options=crime_types, default=crime_types)

# 🔍 선택된 죄명 필터링
df_final = df_filtered[df_filtered['죄명'].isin(selected_crimes)]

target_crimes = selected_crimes  # 유저가 선택한 범죄유형만 분석
peak_summaries = []

for crime in target_crimes:
    df_crime = df_final[df_final['죄명'] == crime]
    if not df_crime.empty:
        time_counts = df_crime['발생시간대'].value_counts()
        if not time_counts.empty:
            # 1) 최대 발생 건수 계산
            peak_count = time_counts.max()
            # 2) 최대 건수와 같은 모든 시간대 추출
            peak_times = time_counts[time_counts == peak_count].index.tolist()
            # 3) ["12시", "19시"] -> "12시, 19시"
            times_str = ", ".join(peak_times)
            # 4) 결과 문구 생성
            peak_summaries.append(
                f"- **{crime}**은 **{times_str}**에 가장 많이 발생 ({peak_count}건)"
            )

if peak_summaries:
    summary_text = (
        f"🕒 **{selected_month}월 {selected_dong}** 범죄 유형별 분석:\n"
        + "\n".join(peak_summaries)
    )
    st.info(summary_text)
else:
    st.info("0시를 제외한 시간대에는 선택한 범죄유형 데이터가 없습니다.")

# 🎨 시각화: 시간대별 범죄 건수 (죄명별 hue)
time_order = [f"{h:02d}시" for h in range(24)]

if not df_final.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.countplot(
        data=df_final,
        x='발생시간대',
        hue='죄명',
        hue_order=selected_crimes,
        order=time_order,  # ✅ x축 정렬
        palette='Set2',
        ax=ax
    )

    ax.set_title(f"{selected_month}월 {selected_dong} 범죄유형별 시간대 분포", fontsize=16)
    ax.set_xlabel("시간대")
    ax.set_ylabel("건수")
    ax.tick_params(axis='x', rotation=45)

    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))  # y축 정수 단위

    plt.tight_layout()
    st.pyplot(fig)
    
    st.subheader(f"📋 {selected_month}월 {selected_dong} {' / '.join(selected_crimes)} 데이터")
    # 인덱스 초기화, 필요 없는 컬럼이 있다면 여기에 추가로 drop()
    df_to_show = df_final.reset_index(drop=True)[['월', '행정동', '발생시간대', '죄명', '주소']]
    st.dataframe(df_to_show)
else:
    st.warning("해당 조건에 맞는 데이터가 없습니다.")
