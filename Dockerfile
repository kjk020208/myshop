# 1. 파이썬 3.9 이미지 사용
FROM python:3.9-slim

# 2. 필수 시스템 도구 설치 (apt-key 없이 진행하기 위해 gpg 추가)
RUN apt-get update && apt-get install -y \
    unixodbc-dev \
    gcc \
    g++ \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 3. Microsoft 키를 보안 디렉토리에 직접 저장 (apt-key 미사용 방식)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# 4. MS SQL 드라이버 설치
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean

# 5. 작업 디렉토리 설정 및 소스 복사
WORKDIR /app
COPY . .

# 6. 라이브러리 설치 (requirements.txt의 버전 준수)
RUN pip install --no-cache-dir -r requirements.txt

# 7. 실행 설정
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]