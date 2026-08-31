"""
Configuração do Firebase — PREENCHE isso com os dados do SEU projeto
Firebase (gratuito), depois renomeia esse arquivo pra
'firebase_config.py' (sem o '_exemplo').

Como conseguir esses valores:
  1. Vai em https://console.firebase.google.com
  2. Cria um projeto novo (gratuito, sem cartão de crédito pedido)
  3. No menu lateral: Build > Authentication > Sign-in method >
     habilita "E-mail/senha"
  4. No menu lateral: Build > Realtime Database > Criar banco de
     dados (escolhe qualquer região) > começa em modo de teste por
     enquanto (depois a gente aperta a segurança com regras)
  5. Ícone de engrenagem > Configurações do projeto > rola até
     "Seus aplicativos" > ícone "</>" (Web) > registra um app (só dá
     um nome qualquer) > ele mostra um bloco "firebaseConfig" com os
     valores abaixo — copia de lá pra cá.
"""

FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCfRlHce-3T9E4oQ64kvgj8plGsx3YMFUA",
    "authDomain": "assistente-ikuromimy.firebaseapp.com",
    "databaseURL": "https://assistente-ikuromimy-default-rtdb.firebaseio.com",
    "projectId": "assistente-ikuromimy",
    "storageBucket": "assistente-ikuromimy.firebasestorage.app",
    "messagingSenderId": "182408050210",
    "appId": "1:182408050210:web:3d174a362195040d547c7b",
}
