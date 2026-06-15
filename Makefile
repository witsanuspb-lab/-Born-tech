.PHONY: install run web chat test docker-build docker-run

install:
	pip install -r requirements.txt

run:
	python main.py

chat:
	python main.py --chat

web:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

docker-build:
	docker build -t ai-team .

docker-run:
	docker run -p 8000:8000 --env-file .env ai-team
