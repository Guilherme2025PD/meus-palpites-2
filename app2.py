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
# CONFIGURAÇÕES (INSIRA SEUS DADOS AQUI)
# ==========================================
TOKEN = "8160564872:AAG15_ESy5lHDEg9q86JwRwhONPRc_JBh1s"
bot = telebot.TeleBot(TOKEN)
ID_USUARIO = None  # Capturado automaticamente no /start

def configurar_driver():
    options = Options()
    options.add_argument("--headless=new") # Roda em segundo plano
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--blink-settings=imagesEnabled=false") # Mais rápido
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ==========================================
# FUNÇÃO GITHUB
# ==========================================
def atualizar_github():
    print("\n[GIT] Sincronizando com GitHub Pages...")
    try:
        subprocess.run(["git", "add", "dados_apostas.json"], check=True)
        mensagem = f"Update_{datetime.datetime.now().strftime('%H:%M')}"
        subprocess.run(["git", "commit", "-m", mensagem], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("[SUCESSO] Site atualizado!")
    except Exception as e:
        print(f"[AVISO] GitHub não atualizado: {e}")

# ==========================================
# CORE DA IA: SCRAPING E ANÁLISE
# ==========================================
def buscar_links_jogos():
    competicoes_alvo = ["Brasileirão Série A", "Premier League", "Serie A", "Bundesliga", "Champions League", "Libertadores", "LaLiga"]
    driver = configurar_driver()
    url = f"https://www.sofascore.com/pt/futebol/{datetime.date.today()}"
    links = []
    try:
        print("\n[IA] Mapeando jogos do dia...")
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
    finally: driver.quit()

def analisar_jogo(link):
    driver = configurar_driver()
    try:
        driver.get(link)
        time.sleep(8)
        try: # Tenta abrir aba de estatísticas
            btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-tabid="statistics"]')))
            btn.click()
            time.sleep(2)
        except: pass

        casa = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="home_team_container"]').text.split('\n')[0]
        fora = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="away_team_container"]').text.split('\n')[0]
        
        stats = {"Time Casa": casa, "Time Fora": fora, "AP_Casa": 0, "AP_Fora": 0, "Chutes": 0, "Link": link}
        rows = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="statistics_row"]')
        for r in rows:
            t = r.text.split('\n')
            if len(t) >= 3 and "Ataques perigosos" in t[1]:
                stats["AP_Casa"], stats["AP_Fora"] = int(t[0]), int(t[2])
            elif len(t) >= 3 and ("Finalizações" in t[1] or "chutes" in t[1].lower()):
                stats["Chutes"] = int(t[0]) + int(t[2])
        return stats
    finally: driver.quit()

# ==========================================
# INTERFACE DO TELEGRAM
# ==========================================
@bot.message_handler(commands=['start'])
def boas_vindas(message):
    global ID_USUARIO
    ID_USUARIO = message.chat.id
    bot.reply_to(message, "🤖 IA Ligada!\n\nEstou monitorando os jogos e o seu site. Se eu achar um jogo quente, te aviso aqui!")

@bot.message_handler(func=lambda m: "sofascore.com" in m.text)
def analise_manual(message):
    bot.reply_to(message, "🔎 Analisando esse link agora...")
    res = analisar_jogo(message.text)
    msg = (f"⚽ *{res['Time Casa']} x {res['Time Fora']}*\n"
           f"🔥 AP: {res['AP_Casa']} - {res['AP_Fora']}\n"
           f"🚀 Chutes Totais: {res['Chutes']}")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# ==========================================
# MONITOR AUTOMÁTICO (THREAD)
# ==========================================
def monitor_loop():
    print("[SISTEMA] Monitor de Jogos iniciado.")
    while True:
        try:
            df = buscar_links_jogos()
            dados_site = []
            
            for _, row in df.iterrows():
                res = analisar_jogo(row['Link'])
                
                # Critério de Alerta (Ex: Mais de 70 ataques perigosos de um lado)
                if (res['AP_Casa'] > 70 or res['AP_Fora'] > 70) and ID_USUARIO:
                    alerta = (f"🚨 *OPORTUNIDADE DETECTADA*\n\n"
                              f"⚽ {res['Time Casa']} {res['AP_Casa']} x {res['AP_Fora']} {res['Time Fora']}\n"
                              f"📈 Muita pressão ofensiva no momento!")
                    bot.send_message(ID_USUARIO, alerta, parse_mode="Markdown")
                
                dados_site.append({
                    "Confronto": f"{res['Time Casa']} x {res['Time Fora']}",
                    "Sugestão": "Monitorado Live",
                    "Confiança": "Alta" if (res['AP_Casa'] > 60 or res['AP_Fora'] > 60) else "Média",
                    "Motivo": f"AP Totais: {res['AP_Casa'] + res['AP_Fora']}"
                })

            # Atualiza arquivos e site
            with open("dados_apostas.json", "w", encoding="utf-8") as f:
                json.dump(dados_site, f, ensure_ascii=False, indent=4)
            
            atualizar_github()
            
            print(f"[SISTEMA] Varredura feita às {datetime.datetime.now()}. Próxima em 15min.")
            time.sleep(900) # 15 minutos
        except Exception as e:
            print(f"Erro no monitor: {e}")
            time.sleep(60)

# ==========================================
# INÍCIO DO PROGRAMA
# ==========================================
if __name__ == "__main__":
    # Inicia o monitor em segundo plano para não travar o bot
    t = Thread(target=monitor_loop)
    t.daemon = True
    t.start()
    
    print("Bot rodando... Mande /start no Telegram.")
    bot.infinity_polling()