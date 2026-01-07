import requests
from selenium import webdriver
from selenium.webdriver.commom.by import by

driver = webdriver.Chrome()
driver.get('https://www.sofascore.com/pt/')

competicao = driver.find_elements(By.XPATH,"//bdi[@class='textStyle_display.micro c_neutrals.nLv1 hover:c_primary.default hover:td_underline trunc_true']")

input('')