import datetime
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
options.page_load_strategy = 'eager'
driver = webdriver.Chrome(options=options)
BASE_URL = "https://finance.yahoo.com/quote/{}.IS/history/?period1={}&period2={}&guccounter=1"


def parse_row(row):
    cells = row.find_elements('tag name', 'td')
    try:
        if len(cells) == 7:
            return {
                'date': cells[0].text,
                'open': cells[1].text,
                'high': cells[2].text,
                'low': cells[3].text,
                'close': cells[4].text,
                'adj_close': cells[5].text,
                'volume': cells[6].text,
                'type': 'price'
            }
        elif len(cells) == 2:
            split_values = cells[1].text.split()
            value, event = split_values[0], split_values[1:]
            event = ' '.join(event)
            return {
                'date': cells[0].text,
                'value': value,
                'event': event,
                'type': 'event'
            }
        else:
            print('Unexpected number of cells in the row')
            for cell in cells:
                print(cell.text)
            return None
    except Exception as e:
        print(f'Error while parsing the row: {e}')
        return None


def fetch_stock_history(stock_code, start_date, end_date):
    driver.get(BASE_URL.format(stock_code, start_date, end_date))

    xpath = '/html/body/div[1]/main/section/section/section/article/section[1]/div[2]/div[1]/section/div/section/div[1]/fin-streamer[1]/span'
    try:
        current_value_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
        current_value = current_value_element.text
    except Exception as e:
        print(f'Error while fetching the current value: {e}')
        return {'current_price': None, 'history_data': []}

    table_xpath = "//table/tbody"
    table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, table_xpath)))
    rows = table.find_elements(By.TAG_NAME, 'tr')
    history_data = [parse_row(row) for row in rows]

    return {'current_price': current_value, 'history_data': history_data}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/currency', methods=['POST'])
def currency_converter():
    data = request.json
    from_currency = data.get('from_currency')
    to_currency = data.get('to_currency')
    amount = data.get('amount')
    date = data.get('date')

    url = 'https://www.oanda.com/currency-converter/en/?from={}&to={}&amount={}'.format(from_currency, to_currency,
                                                                                        amount)
    driver.get(url)
    time.sleep(2)

    if date is not None:
        date_xpath = '/html/body/div/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[3]/div[1]/div[2]/div/div/input'
        date_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, date_xpath)))
        try:
            date_obj = datetime.datetime.fromisoformat(date)
            formatted_date = date_obj.strftime('%d %B %Y')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Expected format is YYYY-MM-DD.'}), 400

        cookie_consent_button_xpath = '//*[@id="onetrust-accept-btn-handler"]'
        try:
            cookie_consent_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, cookie_consent_button_xpath)))
            cookie_consent_button.click()
        except Exception as e:
            print(f'Cookie consent button not found or not clickable: {e}')

        date_element.click()
        driver.execute_script("arguments[0].value = '';", date_element)
        date_element.send_keys(formatted_date)
        date_element.send_keys(u'\ue007')
        time.sleep(1)

    value_xpath = '/html/body/div/main/div[1]/div/div/div[3]/div/div[1]/div[1]/div/div[2]/div[3]/div[2]/div[1]/div/input'
    value_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, value_xpath)))
    value = value_element.get_attribute('value')

    return jsonify({'converted_amount': float(value)})


@app.route('/api/stocks', methods=['POST'])
def fetch_stock_history_handler():
    data = request.json
    stock_code = data.get('stock_code')
    start_date = data.get('start_date', datetime.datetime(datetime.datetime.now().year, 1,
                                                          1).timestamp())  # 1st January of the current year
    end_date = data.get('end_date', int(time.time()))

    if not stock_code:
        return jsonify({"error": "stock_code is required"}), 400
    history_data = fetch_stock_history(stock_code, start_date, end_date)
    if history_data['current_price'] is None:
        return jsonify({"error": "Failed to fetch the data"}), 500
    return jsonify(history_data)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    driver.quit()
    return 'WebDriver has been shut down'


if __name__ == '__main__':
    app.run()
