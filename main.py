import base64
from datetime import datetime, timezone
import os
import pandas as pd
from flask import Flask, Response, jsonify, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import json
import paho.mqtt.client as mqtt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai
from google_auth_oauthlib.flow import Flow
import openpyxl

# ********************* CONEXÃO BANCO DE DADOS *********************************

app = Flask('registro')
server_name = 'Mysql@127.0.0.1'
port='3306'
username = 'jessica'
password = 'senai%40134'
database = 'medidor'


# Caminho para o certificado CA (neste exemplo, assumindo que está no diretório raiz do projeto)
ca_certificate_path = 'DigiCertGlobalRootCA.crt.pem'

# Construção da URI com SSL
uri = f"mysql://{username}:{password}@{server_name}:3306/{database}"
ssl_options = f"?ssl_ca={ca_certificate_path}"

app.config['SQLALCHEMY_DATABASE_URI'] = uri + ssl_options

mybd = SQLAlchemy(app)

# Configuração do OAuth
GOOGLE_CLIENT_ID = '412370899624-ni4sblaieivnco1m3rlstm8mn4gf98t1.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'
REDIRECT_URI = 'https://projetointegrador.com'

flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=["https://www.googleapis.com/auth/gmail.send"],
)

# Variável global para armazenar credenciais
global_credentials = None

@app.route('/')
def index():
    return 'Welcome to the Gmail API Demo! <a href="/login">Login with Google</a>'

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    global global_credentials
    flow.fetch_token(authorization_response=request.url)

    if not flow.credentials:
        print("Falha na autenticação: Nenhuma credencial recebida.")
        return "Authentication failed", 401

    # Armazenar as credenciais globalmente
    global_credentials = flow.credentials
    print("Credenciais armazenadas com sucesso.")

    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if global_credentials is None:
        print("Credenciais não encontradas, redirecionando para login.")
        return redirect(url_for('login'))

    service = build('gmail', 'v1', credentials=global_credentials)

    # Obter uma lista de e-mails
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='').execute()
    messages = results.get('messages', [])

    if not messages:
        return 'No messages found.'

    # Pegue o primeiro e-mail e seus detalhes
    message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
    snippet = message['snippet']

    return f'First message snippet: {snippet}'

# ********************* CONEXÃO SENSORES *********************************

mqtt_data = {}

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with result code " + str(rc))
    client.subscribe("projeto_integrado/SENAI134/Cienciadedados/GrupoX")

def on_message(client, userdata, msg):
    global mqtt_data
    payload = msg.payload.decode('utf-8')
    mqtt_data = json.loads(payload)
    print(f"Received message: {mqtt_data}")

    with app.app_context():
        try:
            temperatura = mqtt_data.get('temperature')
            pressao = mqtt_data.get('pressure')
            altitude = mqtt_data.get('altitude')
            umidade = mqtt_data.get('humidity')
            co2 = mqtt_data.get('CO2')
            timestamp_unix = mqtt_data.get('timestamp')

            if timestamp_unix is None:
                print("Timestamp não encontrado no payload")
                return

            try:
                timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            except (ValueError, TypeError) as e:
                print(f"Erro ao converter timestamp: {str(e)}")
                return

            # Cria o objeto Registro com os dados
            new_data = Registro(
                temperatura=temperatura,
                pressao=pressao,
                altitude=altitude,
                umidade=umidade,
                co2=co2,
                tempo_registro=timestamp
            )

            # Adicionar o novo registro ao banco de dados
            mybd.session.add(new_data)
            mybd.session.commit()

            print("Dados inseridos no banco de dados com sucesso")

            # Verifica a temperatura e envia e-mails se necessário
            if temperatura and float(temperatura) > 20:
                print(temperatura)
                send_temperature_alert_email(float(temperatura))

        except Exception as e:
            print(f"Erro ao processar os dados do MQTT: {str(e)}")
            mybd.session.rollback()

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("test.mosquitto.org", 1883, 60)

def start_mqtt():
    mqtt_client.loop_start()

# Função para gerar sugestões com base na temperatura
genai.configure(api_key='AIzaSyC0a1N4pY4YBtkf2muBb4cXhppf4ToS-0w')

def get_email_list_from_excel(file_path):
    df = pd.read_excel(file_path)
    email_list = df['Email'].tolist()
    return email_list

def send_temperature_alert_email(temperatura):
    global global_credentials
    if global_credentials is None:
        print("Credenciais não encontradas")
        return
    
    service = build('gmail', 'v1', credentials=global_credentials)

    # Obtenha a lista de e-mails a partir do arquivo Excel
    file_path = 'emails.xlsx'
    to_list = get_email_list_from_excel(file_path)

    subject = 'Alerta de Temperatura Alta'
    body = f'A temperatura está acima do limite! A temperatura atual é {temperatura}°C.'

    for recipient in to_list:
        try:
            message = {
                'raw': base64.urlsafe_b64encode(f"To: {recipient}\r\nSubject: {subject}\r\n\r\n{body}".encode('utf-8')).decode('utf-8')
            }
            service.users().messages().send(userId='me', body=message).execute()
            print(f'Email enviado para {recipient}')
        except Exception as e:
            print(f'Erro ao enviar e-mail para {recipient}: {e}')

@app.route('/data', methods=['POST'])
def post_data():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Nenhum dado fornecido"}), 400

        # Adiciona logs para depuração
        print(f"Dados recebidos: {data}")

        temperatura = data.get('temperatura')
        pressao = data.get('pressao')
        altitude = data.get('altitude')
        umidade = data.get('umidade')
        co2 = data.get('co2')
        timestamp_unix = data.get('tempo_registro')

        # Converte timestamp Unix para datetime
        try:
            timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
        except ValueError as e:
            print(f"Erro no timestamp: {str(e)}")
            return jsonify({"error": "Timestamp inválido"}), 400

        # Cria o objeto Registro com os dados
        new_data = Registro(
            temperatura=temperatura,
            pressao=pressao,
            altitude=altitude,
            umidade=umidade,
            co2=co2,
            tempo_registro=timestamp
        )

        # Adiciona o novo registro ao banco de dados
        mybd.session.add(new_data)
        mybd.session.commit()

        return jsonify({"message": "Dados recebidos e armazenados com sucesso"}), 201

    except Exception as e:
        mybd.session.rollback()
        print(f"Erro ao armazenar os dados: {str(e)}")
        return jsonify({"error": "Erro ao armazenar os dados"}), 500

class Registro(mybd.Model):
    __tablename__ = 'registro'
    id = mybd.Column(mybd.Integer, primary_key=True)
    temperatura = mybd.Column(mybd.Float)
    pressao = mybd.Column(mybd.Float)
    altitude = mybd.Column(mybd.Float)
    umidade = mybd.Column(mybd.Float)
    co2 = mybd.Column(mybd.Float)
    tempo_registro = mybd.Column(mybd.DateTime)

# Iniciar o cliente MQTT
start_mqtt()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
