import datetime
import time
import random
import pandas as pd
import json
import subprocess
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TOKEN = "8160564872:AAG15_ESy5lHDEg9q86JwRwhONPRc_JBh1s"
bot = telebot.TeleBot(TOKEN)
ID_USUARIO = None  

def configurar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ==========================================
# FUNÇÃO DE ATUALIZAÇÃO GITHUB (RESTAURADA)
# ==========================================
def atualizar_github():
    print("\n[GIT] Sincronizando dados com o repositório...")
    try:
        # Adiciona o arquivo JSON gerado
        subprocess.run(["git", "add", "dados_apostas.json"], check=True)
        
        # Cria a mensagem de commit com data e hora
        agora = datetime.datetime.now().strftime('%H:%M:%S')
        mensagem = f"Update_IA_{agora}"
        
        # Executa commit e push
        subprocess.run(["git", "commit", "-m", mensagem], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("[SUCESSO] Dados enviados para o GitHub Pages!")
    except Exception as e:
        print(f"[AVISO] Não foi possível atualizar o GitHub automaticamente: {e}")

# ==========================================
# IA: COLETA E ANÁLISE
# ==========================================
def buscar_links_jogos():
    competicoes_alvo = ["Brasileirão Série A", "Premier League", "Serie A", "Bundesliga", "Champions League", "Libertadores", "LaLiga"]
    driver = configurar_driver()
    url = f"https://www.sofascore.com/pt/futebol/{datetime.date.today()}"
    links = []
    try:
        print("\n[IA] Verificando lista de jogos das ligas principais...")
        driver.get(url)
        time.sleep(10)
        eventos = driver.find_elements(By.CSS_SELECTOR, 'div[group="event-list-group"]')
        for ev in eventos:
            if any(c.lower() in ev.text.lower() for c in competicoes_alvo):
                el_links = ev.find_elements(By.CSS_SELECTOR, 'a[href*="/event/"]')
                for el in el_links:
                    l = el.get_attribute('href')
                    if l: links.append({"Link": l})
        return pd.DataFrame(links).drop_duplicates(subset=['Link'])
    finally: 
        driver.quit()

def analisar_jogo(link):
    driver = configurar_driver()
    try:
        driver.get(link)
        time.sleep(8)
        try:
            btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-tabid="statistics"]')))
            btn.click()
            time.sleep(2)
        except: pass

        casa = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="home_team_container"]').text.split('\n')[0]
        fora = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="away_team_container"]').text.split('\n')[0]
        
        stats = {"Time Casa": casa, "Time Fora": fora, "AP_Casa": 0, "AP_Fora": 0, "Chutes": 0}
        rows = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="statistics_row"]')
        for r in rows:
            t = r.text.split('\n')
            if len(t) >= 3 and "Ataques perigosos" in t[1]:
                stats["AP_Casa"], stats["AP_Fora"] = int(t[0]), int(t[2])
            elif len(t) >= 3 and ("Finalizações" in t[1] or "chutes" in t[1].lower()):
                stats["Chutes"] = int(t[0]) + int(t[2])
        return stats
    finally: 
        driver.quit()

# ==========================================
# MONITORAMENTO E BOT
# ==========================================
@bot.message_handler(commands=['start'])
def boas_vindas(message):
    global ID_USUARIO
    ID_USUARIO = message.chat.id
    bot.reply_to(message, "🤖 IA Ativada! Monitorando ligas principais e site GitHub.")

def monitor_automatico():
    print("[SISTEMA] Monitoramento em Tempo Real Iniciado...")
    while True:
        try:
            df = buscar_links_jogos()
            palpites_dia = []
            
            for _, row in df.iterrows():
                res = analisar_jogo(row['Link'])
                
                # Alerta para o Telegram se houver alta pressão
                if (res['AP_Casa'] > 70 or res['AP_Fora'] > 70) and ID_USUARIO:
                    alerta = (f"🚨 *PRESSÃO IDENTIFICADA*\n\n"
                              f"⚽ {res['Time Casa']} {res['AP_Casa']} x {res['AP_Fora']} {res['Time Fora']}\n"
                              f"🔥 Nível de intensidade alto!")
                    bot.send_message(ID_USUARIO, alerta, parse_mode="Markdown")
                
                palpites_dia.append({
                    "Confronto": f"{res['Time Casa']} x {res['Time Fora']}",
                    "Sugestão": "Análise em Tempo Real",
                    "Confiança": "Alta" if (res['AP_Casa'] > 65 or res['AP_Fora'] > 65) else "Média",
                    "Motivo": f"Ataques Perigosos: {res['AP_Casa'] + res['AP_Fora']}"
                })

            # Salva o arquivo localmente
            with open("dados_apostas.json", "w", encoding="utf-8") as f:
                json.dump(palpites_dia, f, ensure_ascii=False, indent=4)
            
            # Tenta enviar para o GitHub
            atualizar_github()
            
            print(f"[SISTEMA] Varredura completa. Aguardando 15 minutos.")
            time.sleep(900) 
        except Exception as e:
            print(f"[ERRO] Falha no ciclo do monitor: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Inicia o monitoramento em segundo plano
    Thread(target=monitor_automatico).start()
    
    print("[SISTEMA] Bot de Telegram Online.")
    bot.infinity_polling()