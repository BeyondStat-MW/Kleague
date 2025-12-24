#!/bin/bash
# BeyondStat Dashboard 실행 스크립트

echo "🚀 BeyondStat Dashboard를 시작합니다..."

# 디렉토리 이동
cd "$(dirname "$0")"

# 라이브러리 설치 확인 및 설치
echo "📦 필요한 라이브러리를 확인 중입니다..."
python3 -m pip install -r requirements.txt

# Streamlit 실행
echo "🌐 웹 브라우저에서 대시보드를 엽니다..."
python3 -m streamlit run app.py
