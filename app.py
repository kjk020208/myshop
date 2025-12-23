# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from azure.storage.blob import BlobServiceClient
import uuid
import random
import requests  # [추가] AI API 호출을 위해 필요합니다.

# [추가] Azure Application Insights 모니터링 라이브러리
from azure.monitor.opentelemetry import configure_azure_monitor

app = Flask(__name__)

# [수정] Application Insights 설정
configure_azure_monitor(
    connection_string="InstrumentationKey=ea5dbbca-e80c-4fc2-963d-828364c43586;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=e701c570-f5e0-4011-a427-ba6602564e1a",
    enable_live_metrics=True
)

# [추가] Azure Computer Vision 설정 (주신 정보 적용)
VISION_KEY = "8jwLUwIDgH8GXGgcZdVEsD61sdDBetp2CGM0KETKaBsrypAzwxHAJQQJ99BLACNns7RXJ3w3AAAFACOGCTxd"
VISION_ENDPOINT = "https://shop-computervision.cognitiveservices.azure.com/"

# 1. Azure SQL Database 설정
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://kjk020208:Gmail0com02*@myshop-sql-server.database.windows.net/myshop-database?driver=ODBC+Driver+17+for+SQL+Server&Charset=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Azure Blob Storage 설정
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


# [수정] 진짜 AI 서비스를 호출하는 함수로 변경
def generate_ai_description(image_url):
    if not image_url:
        return u"매력적인 디자인의 신규 상품입니다."

    try:
        # Azure Computer Vision API 엔드포인트 조립
        analyze_url = VISION_ENDPOINT.rstrip('/') + "/vision/v3.2/analyze"

        # 분석 옵션: 설명(Description)을 한글(ko)로 요청
        params = {'visualFeatures': 'Description', 'language': 'ko'}
        headers = {'Ocp-Apim-Subscription-Key': VISION_KEY, 'Content-Type': 'application/json'}
        data = {'url': image_url}

        # AI 서버에 분석 요청
        response = requests.post(analyze_url, headers=headers, params=params, json=data)
        response.raise_for_status()

        analysis = response.json()

        # AI가 만든 설명 추출
        if 'description' in analysis and analysis['description']['captions']:
            caption = analysis['description']['captions'][0]['text']
            return u"AI 이미지 분석 결과: {}".format(caption)

        return u"AI가 분석 중인 특별한 상품입니다."

    except Exception as e:
        print(f"AI Error: {e}")
        return u"많은 사랑을 받는 베스트셀러 아이템입니다."


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
            filename = str(uuid.uuid4()) + "_" + image_file.filename
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            blob_client.upload_blob(image_file)
            image_url = blob_client.url

        # [수정] 업로드된 이미지 URL을 AI에게 전달하여 설명을 생성합니다.
        ai_msg = generate_ai_description(image_url)
        final_description = u"{} {}".format(ai_msg, user_desc).strip()

        new_product = Product(
            name=name,
            price=price,
            category=category,
            description=final_description,
            image_url=image_url
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('add_product.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)