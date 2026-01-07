from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import time
import pandas as pd

def buscar_jogos_filtrados():
    # --- LISTA DE DESEJADOS ---
    # Coloquei termos que abrangem os nomes que o SofaScore usa em PT e EN
    competicoes_alvo = [
        "Brasileirão Série A", "Premier League", "Serie A", 
        "Bundesliga", "Champions League", "Libertadores", 
        "LaLiga", "Copa del Rey"
    ]

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(150)

    hoje = datetime.date.today().strftime('%Y-%m-%d')
    url = f"https://www.sofascore.com/pt/futebol/{hoje}"
    
    dados_finais = []

    try:
        print(f"Acessando SofaScore para filtrar ligas principais...")
        driver.get(url)
        time.sleep(10) # Tempo para carregar a lista de jogos

        # O SofaScore organiza os jogos em grupos (Header da Liga + Jogos)
        # Vamos buscar todos os blocos de eventos
        eventos = driver.find_elements(By.CSS_SELECTOR, 'div[group="event-list-group"]')

        for evento in eventos:
            try:
                # Tenta pegar o nome da liga dentro desse bloco
                nome_liga = evento.text.split('\n')[0] # Geralmente o primeiro texto é o nome da liga
                
                # Verifica se a liga atual está na nossa lista de interesse
                if any(comp.lower() in nome_liga.lower() for comp in competicoes_alvo):
                    print(f"Selecionando: {nome_liga}")
                    
                    # Busca todos os links de jogos dentro DESTE bloco específico
                    links_elementos = evento.find_elements(By.CSS_SELECTOR, 'a[href*="/event/"]')
                    
                    for el in links_elementos:
                        link = el.get_attribute('href')
                        if link:
                            dados_finais.append({
                                "Data": hoje,
                                "Competição": nome_liga,
                                "Link do Jogo": link
                            })
            except:
                continue

    except Exception as e:
        print(f"Erro na captura: {e}")
    finally:
        driver.quit()
        
    return dados_finais

# --- EXECUÇÃO ---
lista_jogos = buscar_jogos_filtrados()

if lista_jogos:
    df = pd.DataFrame(lista_jogos)
    # Remove duplicados (links que podem aparecer duas vezes no HTML)
    df = df.drop_duplicates(subset=['Link do Jogo'])
    
    df.to_excel("jogos_do_dia.xlsx", index=False)
    print(f"\nSucesso! {len(df)} jogos das ligas escolhidas salvos em 'jogos_do_dia.xlsx'")
else:
    print("\nNenhum jogo dessas competições foi encontrado para hoje.")