import datetime
import time
import json
import subprocess
import telebot
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from threading import Thread

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TOKEN = "8160564872:AAG15_ESy5lHDEg9q86JwRwhONPRc_JBh1s"
bot = telebot.TeleBot(TOKEN)
ID_USUARIO = None  
GIT_EXE = r"C:\Program Files\Git\bin\git.exe"

def configurar_driver():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ==========================================
# FUNÇÃO GITHUB (ADICIONADA)
# ==========================================
def atualizar_github():
    print("\n[GIT] Sincronizando dados com o GitHub Pages...")
    try:
        # Adiciona, commita e envia os dados
        subprocess.run([GIT_EXE, "add", "dados_apostas.json"], check=True)
        mensagem = f"AutoUpdate_{datetime.datetime.now().strftime('%H:%M')}"
        subprocess.run([GIT_EXE, "commit", "-m", mensagem], check=True)
        subprocess.run([GIT_EXE, "push", "origin", "main"], check=True)
        print("[SUCESSO] Site atualizado com novo lote de jogos!")
    except Exception as e:
        print(f"[AVISO] Sem mudanças pendentes ou erro no Git: {e}")

# ==========================================
# EXTRAÇÃO DE DADOS PROFUNDA
# ==========================================
def extrair_medias_time(link_time, driver):
    dados = {"Gols": "0", "Escanteios": "0", "Cartoes": "0", "Chutes": "0"}
    try:
        driver.get(link_time)
        time.sleep(4)
        corpo = driver.find_element(By.TAG_NAME, "body").text
        linhas = corpo.split('\n')
        for i, linha in enumerate(linhas):
            if "Gols por partida" in linha: dados["Gols"] = linhas[i+1]
            if "Escanteios por jogo" in linha: dados["Escanteios"] = linhas[i+1]
            if "Total de finalizações por jogo" in linha: dados["Chutes"] = linhas[i+1]
            if "Cartões amarelos por partida" in linha: dados["Cartoes"] = linhas[i+1]
        return dados
    except:
        return dados

def analisar_confronto(link_jogo):
    driver = configurar_driver()
    try:
        driver.get(link_jogo)
        time.sleep(5)
        links_times = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/team/futebol/"]')
        if len(links_times) < 2: return None
        
        link_casa = links_times[0].get_attribute('href')
        link_fora = links_times[1].get_attribute('href')
        nome_casa = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="home_team_container"]').text.split('\n')[0]
        nome_fora = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="away_team_container"]').text.split('\n')[0]

        print(f"🔍 Analisando: {nome_casa} x {nome_fora}")
        medias_casa = extrair_medias_time(link_casa, driver)
        medias_fora = extrair_medias_time(link_fora, driver)

        return {
            "Confronto": f"{nome_casa} x {nome_fora}",
            "Gols_Media": f"C: {medias_casa['Gols']} | F: {medias_fora['Gols']}",
            "Escanteios": f"C: {medias_casa['Escanteios']} | F: {medias_fora['Escanteios']}",
            "Cartoes": f"C: {medias_casa['Cartoes']} | F: {medias_fora['Cartoes']}",
            "Chutes": f"C: {medias_casa['Chutes']} | F: {medias_fora['Chutes']}"
        }
    except:
        return None
    finally:
        driver.quit()

# ==========================================
# TELEGRAM (COMANDO START)
# ==========================================
@bot.message_handler(commands=['start'])
def ligar_ia(message):
    global ID_USUARIO
    ID_USUARIO = message.chat.id
    bot.reply_to(message, "✅ Sistema Pré-Jogo Online!\nAnalisando todos os jogos da rodada e enviando para o site.")

# ==========================================
# MONITOR SEM LIMITES
# ==========================================
def monitor_loop():
    while True:
        try:
            print("\n🚀 INICIANDO VARREDURA COMPLETA...")
            driver_busca = configurar_driver()
            driver_busca.get(f"https://www.sofascore.com/pt/futebol/{datetime.date.today()}")
            time.sleep(10)
            
            elementos = driver_busca.find_elements(By.CSS_SELECTOR, 'a[href*="/event/"]')
            links_totais = []
            for el in elementos:
                l = el.get_attribute('href')
                if l and "/event/" in l and l not in links_totais:
                    links_totais.append(l)
            driver_busca.quit()

            print(f"✅ Encontrados {len(links_totais)} jogos para processar.")
            
            dados_site = []
            for i, link in enumerate(links_totais):
                print(f"[{i+1}/{len(links_totais)}] Processando...")
                res = analisar_confronto(link)
                if res:
                    dados_site.append(res)
                
                # Atualiza o site a cada 5 jogos para não demorar
                if len(dados_site) > 0 and len(dados_site) % 5 == 0:
                    with open("dados_apostas.json", "w", encoding="utf-8") as f:
                        json.dump(dados_site, f, ensure_ascii=False, indent=4)
                    atualizar_github()

            # Finalização da rodada completa
            with open("dados_apostas.json", "w", encoding="utf-8") as f:
                json.dump(dados_site, f, ensure_ascii=False, indent=4)
            atualizar_github()
            
            print("🏁 Varredura finalizada. Próxima em 2 horas.")
            time.sleep(7200) 
            
        except Exception as e:
            print(f"❌ Erro no monitor: {e}")
            time.sleep(60)

if __name__ == "__main__":
    t = Thread(target=monitor_loop)
    t.daemon = True
    t.start()
    print("🤖 Bot iniciado! Mande /start no Telegram.")
    bot.infinity_polling()