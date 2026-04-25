import pandas as pd
from datetime import datetime, timedelta
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service


# =========================
# CONFIG
# =========================
CARPETA = "ArchBIV"
ARCHIVO = f"{CARPETA}/volumen_historico_emmsa.csv"

os.makedirs(CARPETA, exist_ok=True)


# =========================
# DRIVER (CORREGIDO PARA GITHUB ACTIONS)
# =========================
def get_driver():

    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"  # 🔥 CLAVE

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")

    service = Service("/usr/bin/chromedriver")  # 🔥 CLAVE

    driver = webdriver.Chrome(service=service, options=options)

    return driver


# =========================
# UTILIDADES
# =========================
def escribir_fecha(input_element, fecha):
    input_element.click()
    input_element.send_keys(Keys.CONTROL, "a")
    input_element.send_keys(Keys.BACKSPACE)
    input_element.send_keys(fecha)
    time.sleep(0.3)


def cambiar_iframe(driver):
    WebDriverWait(driver, 20).until(
        EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe"))
    )


def fechas_ayer_hoy():
    hoy = datetime.now()
    ayer = hoy - timedelta(days=1)

    return [
        ayer.strftime("%d/%m/%Y"),
        hoy.strftime("%d/%m/%Y")
    ]


# =========================
# SCRAPER
# =========================
def scraper_volumen(driver, fecha):

    print(f"🔎 Scraping {fecha}")

    url = "https://www.emmsa.com.pe/index.php/precios-diarios/"
    driver.get(url)

    cambiar_iframe(driver)

    # Fecha
    fecha_input = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "txtfecha1"))
    )

    escribir_fecha(fecha_input, fecha)
    fecha_input.send_keys(Keys.ESCAPE)

    # Checkbox
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "chkChanging"))
        ).click()
    except:
        pass

    # Botón consultar
    boton = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Consultar')]"))
    )
    boton.click()

    time.sleep(2)

    driver.switch_to.default_content()
    cambiar_iframe(driver)

    # Tabla
    try:
        tbody = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".dataTables_scrollBody tbody"))
        )
    except:
        print("⚠ No hay tabla")
        return None

    headers = [
        th.text.strip()
        for th in driver.find_elements(By.CSS_SELECTOR, ".dataTables_scrollHead th")
    ]

    filas = tbody.find_elements(By.TAG_NAME, "tr")

    data = []
    for fila in filas:
        celdas = [td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td")]
        if len(celdas) == len(headers):
            data.append(celdas)

    if not data:
        return None

    df = pd.DataFrame(data, columns=headers)
    df["Fecha"] = fecha

    return df


# =========================
# MAIN
# =========================
def main():

    print("📡 EMMSA SCRAPER VOLUMEN")

    # Cargar histórico
    if os.path.exists(ARCHIVO):
        df_old = pd.read_csv(ARCHIVO)
    else:
        df_old = pd.DataFrame()

    fechas_existentes = set(df_old["Fecha"].astype(str)) if not df_old.empty else set()

    driver = get_driver()

    nuevos = []

    for fecha in fechas_ayer_hoy():

        print(f"📅 {fecha}")

        if fecha in fechas_existentes:
            print("✔ ya existe, se omite")
            continue

        df = scraper_volumen(driver, fecha)

        if df is not None:
            print(f"✅ filas: {len(df)}")
            nuevos.append(df)
        else:
            print("⚠ sin datos")

        time.sleep(2)

    driver.quit()

    if nuevos:
        df_final = pd.concat([df_old] + nuevos, ignore_index=True)
        df_final.drop_duplicates(inplace=True)

        df_final.to_csv(ARCHIVO, index=False, encoding="utf-8-sig")

        print("💾 CSV actualizado")
        print(df_final.tail(10))
    else:
        print("ℹ No hubo nuevos datos")


if __name__ == "__main__":
    main()
