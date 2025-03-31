// src/news_aggregator/static/js/app.js

document.addEventListener('DOMContentLoaded', function() {
    // Masquer automatiquement les alertes après quelques secondes
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-info, .alert-success:not(.fixed)');
        alerts.forEach(function(alert) {
            if (bootstrap && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.display = 'none';
            }
        });
    }, 5000);
    
    // Initialiser le compteur pour la prochaine mise à jour
    if (document.getElementById('nextUpdate')) {
        startCountdown();
    }

    // Ajouter des écouteurs d'événements pour les boutons de bascule
    const toggleConfigBtn = document.querySelector('[onclick="toggleConfigForm()"]');
    if (toggleConfigBtn) {
        toggleConfigBtn.addEventListener('click', toggleConfigForm);
    }

    const toggleTopicBtn = document.querySelector('[onclick="toggleTopicForm()"]');
    if (toggleTopicBtn) {
        toggleTopicBtn.addEventListener('click', toggleTopicForm);
    }
});

// Fonction pour basculer l'affichage du formulaire de configuration
function toggleConfigForm() {
    const form = document.getElementById('configForm');
    if (form) {
        if (form.style.display === 'none') {
            form.style.display = 'block';
            form.classList.add('form-transition');
        } else {
            form.style.display = 'none';
        }
    }
}

// Fonction pour basculer l'affichage du formulaire de sujet
function toggleTopicForm() {
    const form = document.getElementById('topicForm');
    if (form) {
        if (form.style.display === 'none') {
            form.style.display = 'block';
            form.classList.add('form-transition');
        } else {
            form.style.display = 'none';
        }
    }
}

// Fonction pour le compte à rebours jusqu'à la prochaine mise à jour
function startCountdown() {
    // Récupérer l'heure de la dernière exécution (si disponible dans l'élément data)
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Par défaut, supposons que la mise à jour est dans 1 heure à partir de maintenant
    const now = new Date();
    let lastUpdate = null;
    
    if (nextUpdateElement.dataset.lastUpdate) {
        lastUpdate = new Date(nextUpdateElement.dataset.lastUpdate);
    }
    
    const nextHour = lastUpdate 
        ? new Date(lastUpdate.getTime() + 60*60*1000) 
        : new Date(now.getTime() + 60*60*1000);
    
    function updateCounter() {
        const currentTime = new Date();
        const diff = nextHour - currentTime;
        
        if (diff <= 0) {
            nextUpdateElement.textContent = "très bientôt";
            // Après un certain délai, on peut recharger la page pour voir si la mise à jour a été faite
            setTimeout(() => { window.location.reload(); }, 30000);
            return;
        }
        
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        
        nextUpdateElement.textContent = `dans ${minutes} min ${seconds} sec`;
        
        // Mettre à jour chaque seconde
        setTimeout(updateCounter, 1000);
    }
    
    // Démarrer le compteur
    updateCounter();
}   