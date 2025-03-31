# wsgi.py
from src.news_aggregator.app import app as application

if __name__ == "__main__":
    application.run()