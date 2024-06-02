import time

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

app = Flask(__name__)
CORS(app)

# Initialize the WebDriver globally
options = Options()
options.add_argument('--headless')  # Uncomment if you want to run in headless mode
options.add_argument('--no-sandbox')  # Required for running as root in some environments
options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
options.add_argument("--disable-gpu")  # applicable to windows os only
options.page_load_strategy = 'none'
driver = webdriver.Chrome(options=options)

BASE_URL = "https://finance.yahoo.com/quote/{}.IS/history/?filter=history&frequency=1d&period1={}&period2={}"


def parse_row(row):
    cells = row.find_elements('tag name', 'td')
    if len(cells) == 7:
        return {
            'date': cells[0].text,
            'open': cells[1].text,
            'high': cells[2].text,
            'low': cells[3].text,
            'close': cells[4].text,
            'adj_close': cells[5].text,
            'volume': cells[6].text,
        }
    elif len(cells) == 2:
        return {
            'date': cells[0].text,
            'value': cells[1].text.split()[0],
            'event': cells[1].text.split()[1],
        }
    else:
        print('Unexpected number of cells in the row')
        for cell in cells:
            print(cell.text)
        return None


def fetch_stock_history(stock_code, start_date, end_date):
    driver.get(BASE_URL.format(stock_code, start_date, end_date))

    xpath = '//fin-streamer/span'
    current_value_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
    current_value = current_value_element.text

    table_xpath = "//table/tbody"
    table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, table_xpath)))
    rows = table.find_elements(By.TAG_NAME, 'tr')
    history_data = [parse_row(row) for row in rows]

    return {'current_price': current_value, 'history_data': history_data}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/stocks', methods=['POST'])
def fetch_stock_history_handler():
    data = request.json
    stock_code = data.get('stock_code')
    start_date = data.get('start_date', 1514764800)  # 1st January 2018
    end_date = data.get('end_date', int(time.time()))

    if not stock_code:
        return jsonify({"error": "stock_code is required"}), 400

    return jsonify(fetch_stock_history(stock_code, start_date, end_date))


@app.route('/shutdown', methods=['POST'])
def shutdown():
    driver.quit()
    return 'WebDriver has been shut down'


if __name__ == '__main__':
    app.run()
