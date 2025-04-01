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

    // Mettre à jour régulièrement les informations de statut 
    if (document.querySelector('.status-container')) {
        // Premier appel après 5 secondes
        setTimeout(refreshStatus, 5000);
        // Ensuite toutes les 30 secondes
        setInterval(refreshStatus, 30000);
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

    // Gestion du bouton Stop Monitoring
    const stopButton = document.querySelector('form[action="/stop"] button');
    if (stopButton) {
        stopButton.addEventListener('click', function() {
            stopButton.disabled = true;
            stopButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Arrêt en cours...';
        });
    }

    // Gestion de la visibilité des mots de passe
    initPasswordToggles();
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

// Fonction pour initialiser les toggles de mots de passe
function initPasswordToggles() {
    document.querySelectorAll('.input-group .btn-outline-secondary').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.closest('.input-group').querySelector('input[type="password"], input[type="text"]');
            const icon = this.querySelector('i');
            
            if (input.type === "password") {
                input.type = "text";
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = "password";
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

// Fonction pour mettre à jour le statut
function refreshStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            console.log("Status update received:", data);
            
            // Si le monitoring n'est plus actif, recharger la page
            if (document.querySelector('.status-container') && !data.active) {
                window.location.reload();
                return;
            }
            
            // Mettre à jour le prochain temps d'exécution
            updateTimerWithData(data);
        })
        .catch(error => {
            console.error("Error fetching status:", error);
        });
}

// Fonction pour mettre à jour le timer avec les données reçues
function updateTimerWithData(data) {
    if (!data || !data.next_execution) return;
    
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Mettre à jour l'attribut data
    nextUpdateElement.dataset.nextExecution = data.next_execution;
    
    // Si le timer affiche NaN, redémarrer le compte à rebours
    if (nextUpdateElement.textContent.includes('NaN')) {
        startCountdown();
    } else if (data.time_remaining) {
        // Sinon, simplement mettre à jour le texte
        nextUpdateElement.textContent = data.time_remaining;
    }
}

// Fonction pour le compte à rebours jusqu'à la prochaine mise à jour
function startCountdown() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Obtenir le temps de référence
    let nextUpdate = null;
    
    if (nextUpdateElement.dataset.nextExecution) {
        try {
            // Essayer de parser la date ISO
            nextUpdate = new Date(nextUpdateElement.dataset.nextExecution);
            console.log("Next execution parsed:", nextUpdate);
            
            // Vérifier si la date est valide
            if (isNaN(nextUpdate.getTime())) {
                console.log("Invalid date format, using fallback");
                nextUpdate = null;
            }
        } catch(e) {
            console.error("Error parsing date:", e);
            nextUpdate = null;
        }
    }
    
    // Si pas de date valide, utiliser maintenant + 1 heure comme fallback
    if (!nextUpdate) {
        const now = new Date();
        nextUpdate = new Date(now.getTime() + 60 * 60 * 1000);
        console.log("Using fallback next execution:", nextUpdate);
    }
    
    // Fonction pour mettre à jour le compte à rebours
    function updateTimer() {
        const now = new Date();
        const diffMs = nextUpdate - now;
        
        // Si le temps est dépassé
        if (diffMs <= 0) {
            nextUpdateElement.textContent = "très bientôt";
            
            // Recharger le statut après 10 secondes
            setTimeout(refreshStatus, 10000);
            return;
        }
        
        // Calculer minutes et secondes
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
        
        // Afficher le temps restant
        nextUpdateElement.textContent = `${minutes} min ${seconds} sec`;
        
        // Mettre à jour chaque seconde
        setTimeout(updateTimer, 1000);
    }
    
    // Démarrer le compte à rebours
    updateTimer();
}

// Ajouter une fonction pour basculer la visibilité du mot de passe
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const icon = input.parentNode.querySelector('.fa-eye, .fa-eye-slash');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}