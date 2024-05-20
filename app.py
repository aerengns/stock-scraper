from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)
# Initialize the WebDriver globally
options = Options()
options.add_argument('--headless')  # Uncomment if you want to run in headless mode
options.add_argument('--no-sandbox')  # Required for running as root in some environments
options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
driver = webdriver.Chrome(options=options)

BASE_URL = "https://finance.yahoo.com/quote/{}.IS/history"


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


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/stocks', methods=['POST'])
def fetch_stock_history():
    data = request.json
    stock_code = data.get('stock_code')
    if not stock_code:
        return jsonify({"error": "stock_code is required"}), 400

    driver.get(BASE_URL.format(stock_code))
    driver.implicitly_wait(1)

    xpath = '/html/body/div[1]/main/section/section/section/article/section[1]/div[2]/div[1]/section/div/section/div[1]/fin-streamer[1]/span'
    current_value_element = driver.find_element('xpath', xpath)
    current_value = current_value_element.text

    table_xpath = "/html/body/div[1]/main/section/section/section/article/div[1]/div[3]/table/tbody"
    table = driver.find_element('xpath', table_xpath)
    rows = table.find_elements('tag name', 'tr')
    history_data = [parse_row(row) for row in rows]

    return jsonify({'current_price': current_value, 'history_data': history_data})


@app.route('/shutdown', methods=['POST'])
def shutdown():
    driver.quit()
    return 'WebDriver has been shut down'


if __name__ == '__main__':
    app.run()
