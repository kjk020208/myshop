# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from azure.storage.blob import BlobServiceClient
import uuid
import requests
from urllib.parse import quote  # [추가] 특수문자 포함 주소를 안전하게 변환하기 위해 필요

# Azure Application Insights 모니터링 라이브러리
from azure.monitor.opentelemetry import configure_azure_monitor

app = Flask(__name__)

# [1] Application Insights 활성화
configure_azure_monitor(
    connection_string="InstrumentationKey=ea5dbbca-e80c-4fc2-963d-828364c43586;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=e701c570-f5e0-4011-a427-ba6602564e1a",
    enable_live_metrics=True
)

# [2] Azure Computer Vision AI 설정
VISION_KEY = "8jwLUwIDgH8GXGgcZdVEsD61sdDBetp2CGM0KETKaBsrypAzwxHAJQQJ99BLACNns7RXJ3w3AAAFACOGCTxd"
VISION_ENDPOINT = "https://shop-computervision.cognitiveservices.azure.com/"

# [3] Azure SQL Database 설정
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://kjk020208:Gmail0com02*@myshop-sql-server.database.windows.net/myshop-database?driver=ODBC+Driver+17+for+SQL+Server&Charset=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# [4] Azure Blob Storage 설정
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=myshopstorage;AccountKey=Ep3ZG/ATzxhVv4Pm6QbOeIGocpX2KRvy0eLz7z0En8j9RstTQKUy8ODLYjPK18y/xYEOF2PYzeay+AStiISr9A==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "product"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(200), nullable=False)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    description = db.Column(db.UnicodeText, nullable=True)
    category = db.Column(db.Unicode(50), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)


# [수정] 400 에러 해결을 위한 URL 인코딩 및 3단 분석 로직
def generate_ai_description(image_url):
    if not image_url:
        return u"매력적인 디자인의 신규 상품입니다."
    try:
        # [핵심] 주소의 특수문자를 인코딩하여 400 에러를 방지합니다.
        safe_url = quote(image_url, safe=':/?=')

        analyze_url = VISION_ENDPOINT.rstrip('/') + "/vision/v3.2/analyze"
        params = {'visualFeatures': 'Description,Tags', 'language': 'ko'}
        headers = {'Ocp-Apim-Subscription-Key': VISION_KEY, 'Content-Type': 'application/json'}
        data = {'url': safe_url}

        response = requests.post(analyze_url, headers=headers, params=params, json=data, timeout=15)

        # 400 에러가 난다면 로그를 출력하여 확인합니다.
        if response.status_code != 200:
            print(f"AI API Error Log: {response.status_code} - {response.text}")
            return u"AI가 이미지를 정밀 분석 중입니다."

        result = response.json()

        # 1순위: 문장형 설명 (Captions)
        if 'description' in result and result['description']['captions']:
            return u"AI 분석: " + result['description']['captions'][0]['text']

        # 2순위: 핵심 태그 (Tags)
        if 'tags' in result and len(result['tags']) > 0:
            top_tags = [tag['name'] for tag in result['tags'][:2]]
            return u"AI 인식 단어: " + ", ".join(top_tags)

        return u"AI가 사물을 인식했습니다."
    except Exception as e:
        print(f"Exception: {e}")
        return u"추천 베스트셀러 아이템입니다."


@app.route('/')
def home():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        user_desc = request.form.get('description', '')
        image_file = request.files.get('image')

        image_url = ""
        if image_file:
            # 파일 업로드 시 UUID를 사용하여 유니크한 주소 생성
            filename = str(uuid.uuid4()) + "_" + image_file.filename
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            blob_client.upload_blob(image_file)
            image_url = blob_client.url

        ai_msg = generate_ai_description(image_url)
        final_description = u"{} {}".format(ai_msg, user_desc).strip()

        new_product = Product(name=name, price=price, category=category, description=final_description,
                              image_url=image_url)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_product.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)