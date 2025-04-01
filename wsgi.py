# wsgi.py
import sys
import os

# Ajouter le répertoire racine au chemin Python
sys.path.insert(0, os.path.dirname(__file__))

# Ajouter le dossier src/ au chemin Python pour que les imports absolus fonctionnent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Créer une fonction pour l'application Flask
def get_app():
    # Import ici pour éviter les erreurs de référence circulaire
    from src.news_aggregator.app import app as flask_app
    return flask_app

# Exposer l'application pour Gunicorn
application = get_app()

# Pour les tests locaux
if __name__ == "__main__":
    application.run()