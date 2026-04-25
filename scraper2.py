from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def get_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"  # 🔥 CLAVE

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    service = Service("/usr/bin/chromedriver")  # 🔥 CLAVE

    return webdriver.Chrome(service=service, options=options)

# =========================
# CONFIG
# =========================
CARPETA = "datos"
os.makedirs(CARPETA, exist_ok=True)

ARCHIVO = os.path.join(CARPETA, "volumen_emmsa.csv")

# =========================
# UTILIDADES
# =========================
def escribir_fecha(input_element, fecha):
    input_element.click()
    input_element.send_keys(Keys.CONTROL, "a")
    input_element.send_keys(Keys.BACKSPACE)
    input_element.send_keys(fecha)
    time.sleep(0.2)


def cargar_iframe(driver):
    WebDriverWait(driver, 30).until(
        EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, "//iframe[contains(@src,'emmsa')]")
        )
    )


# =========================
# SCRAPER
# =========================
def scraper_volumenes(driver, fecha):

    print(f"🔎 Scraping {fecha}")

    driver.get("https://www.emmsa.com.pe/index.php/precios-diarios/")

    cargar_iframe(driver)

    fecha_input = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "txtfecha1"))
    )

    escribir_fecha(fecha_input, fecha)
    fecha_input.send_keys(Keys.ESCAPE)

    # activar checkbox
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "chkChanging"))
        ).click()
    except:
        pass

    # botón consultar
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Consultar')]"))
    ).click()

    time.sleep(2)

    driver.switch_to.default_content()
    cargar_iframe(driver)

    # =========================
    # TABLA
    # =========================
    try:
        tbody = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".dataTables_scrollBody tbody")
            )
        )
    except:
        print("⚠ No hay tabla")
        return None

    headers = [
        th.text.strip()
        for th in driver.find_elements(By.CSS_SELECTOR, ".dataTables_scrollHead th")
    ]

    filas = tbody.find_elements(By.XPATH, ".//tr[td]")

    datos = []
    for fila in filas:
        celdas = [td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td")]
        if len(celdas) == len(headers):
            datos.append(celdas)

    if not datos:
        print("⚠ tabla vacía")
        return None

    df = pd.DataFrame(datos, columns=headers)
    df["Fecha"] = fecha

    print(f"✅ filas: {len(df)}")

    return df


# =========================
# FECHAS
# =========================
def fechas_ayer_hoy():
    hoy = datetime.now()
    ayer = hoy - timedelta(days=1)

    return [
        ayer.strftime("%d/%m/%Y"),
        hoy.strftime("%d/%m/%Y")
    ]


# =========================
# MAIN
# =========================
def main():

    print("📡 EMMSA SCRAPER VOLUMEN")

    # historial
    if os.path.exists(ARCHIVO):
        df_old = pd.read_csv(ARCHIVO)
    else:
        df_old = pd.DataFrame()

    driver = get_driver()

    nuevos = []

    for fecha in fechas_ayer_hoy():

        if not df_old.empty and fecha in df_old["Fecha"].astype(str).values:
            print(f"✔ {fecha} ya existe")
            continue

        df = scraper_volumenes(driver, fecha)

        if df is not None:
            nuevos.append(df)

    driver.quit()

    # =========================
    # GUARDAR
    # =========================
    if nuevos:

        df_final = pd.concat([df_old] + nuevos, ignore_index=True)

        df_final = df_final.drop_duplicates()

        df_final.to_csv(ARCHIVO, index=False, encoding="utf-8-sig")

        print("\n💾 Guardado OK")
        print(f"📁 {ARCHIVO}")
        print(df_final.tail())

    else:
        print("ℹ No hay nuevos datos")


if __name__ == "__main__":
    main()
