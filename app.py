# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from azure.storage.blob import BlobServiceClient
import uuid
import random

# [추가] Azure Application Insights 모니터링 라이브러리
from azure.monitor.opentelemetry import configure_azure_monitor

app = Flask(__name__)

# [수정] Application Insights 설정
# enable_live_metrics=True 옵션을 추가하여 실시간 대시보드를 활성화합니다.
configure_azure_monitor(
    connection_string="InstrumentationKey=ea5dbbca-e80c-4fc2-963d-828364c43586;IngestionEndpoint=https://koreacentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://koreacentral.livediagnostics.monitor.azure.com/;ApplicationId=e701c570-f5e0-4011-a427-ba6602564e1a",
    enable_live_metrics=True  # 이 한 줄이 추가되어야 실시간 그래프가 작동합니다!
)

# 1. Azure SQL Database 설정
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://kjk020208:Gmail0com02*@myshop-sql-server.database.windows.net/myshop-database?driver=ODBC+Driver+17+for+SQL+Server&Charset=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Azure Blob Storage 설정
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=myshopstorage;AccountKey=Ep3ZG/ATzxhVv4Pm6QbOeIGocpX2KRvy0eLz7z0En8j9RstTQKUy8ODLYjPK18y/xYEOF2PYzeay+AStiISr9A==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = "product"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# 한글 지원을 위해 Unicode 타입을 사용하는 기존 모델 유지
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(200), nullable=False)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    description = db.Column(db.UnicodeText, nullable=True)
    category = db.Column(db.Unicode(50), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)

def generate_ai_description(product_name):
    messages = [
        u"드디어 입고된 {}! 세련된 디자인으로 당신의 일상을 바꿔보세요.".format(product_name),
        u"선물용으로 인기 만점인 {}, 지금 바로 특별한 가격에 만나보세요.".format(product_name),
        u"누적 판매량 1위! {}은 품질부터 다릅니다. 놓치지 마세요.".format(product_name),
        u"감각적인 당신을 위한 {}. 오늘 주문하면 바로 배송됩니다.".format(product_name),
        u"품절 임박 상품인 {}, 오직 여기서만 구매 가능합니다!".format(product_name)
    ]
    return random.choice(messages)

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

        ai_msg = generate_ai_description(name)
        final_description = u"{} {}".format(ai_msg, user_desc).strip()

        image_url = ""
        if image_file:
            filename = str(uuid.uuid4()) + "_" + image_file.filename
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            blob_client.upload_blob(image_file)
            image_url = blob_client.url

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