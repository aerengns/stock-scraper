build:
	docker build -t stock-scraper .

clean:
	docker stop stock-scraper
	docker rm stock-scraper

run: clean
	docker run -d --name stock-scraper -p 5000:5000 stock-scraper

local:
	python -m flask run
