# wsgi.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.news_aggregator.app import app as application

if __name__ == "__main__":
    application.run()