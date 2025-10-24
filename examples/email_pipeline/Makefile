.PHONY: dev test clean

dev:
	python -m email_pipeline.service

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
