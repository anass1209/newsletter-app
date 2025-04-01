// src/news_aggregator/static/js/app.js

"use strict";

/**
 * Newsletter Monitoring Application
 * Version corrigée pour résoudre les problèmes de compteur et de mise à jour
 */

document.addEventListener('DOMContentLoaded', function() {
    initAlerts();
    initCountdownTimer();
    initStatusRefresh();
    initFormValidation();
});

/**
 * Initialise la fermeture automatique des alertes
 */
function initAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.fixed)');
        alerts.forEach(function(alert) {
            if (bootstrap && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                fadeOutElement(alert);
            }
        });
    }, 5000);
}

/**
 * Anime la disparition d'un élément
 */
function fadeOutElement(element) {
    let opacity = 1;
    const timer = setInterval(function() {
        if (opacity <= 0.1) {
            clearInterval(timer);
            element.style.display = 'none';
        }
        element.style.opacity = opacity;
        opacity -= opacity * 0.1;
    }, 20);
}

/**
 * Initialise le compte à rebours pour la prochaine mise à jour
 */
function initCountdownTimer() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Extraire l'heure de prochaine exécution
    const nextExecutionElement = document.querySelector('.next-execution-time');
    if (!nextExecutionElement) {
        nextUpdateElement.innerHTML = '<span class="time-remaining">Bientôt</span>';
        return;
    }
    
    const nextExecutionText = nextExecutionElement.textContent.trim();
    const timeParts = nextExecutionText.split(':');
    
    if (timeParts.length < 2 || isNaN(parseInt(timeParts[0]))) {
        nextUpdateElement.innerHTML = '<span class="time-remaining">Bientôt</span>';
        return;
    }
    
    // Créer une date pour la prochaine mise à jour
    const now = new Date();
    const nextExecution = new Date();
    nextExecution.setHours(
        parseInt(timeParts[0]), 
        parseInt(timeParts[1]) || 0, 
        parseInt(timeParts[2]) || 0, 
        0
    );
    
    // Si l'heure est déjà passée, c'est pour demain
    if (nextExecution < now) {
        nextExecution.setDate(nextExecution.getDate() + 1);
    }
    
    function updateCountdown() {
        const currentTime = new Date();
        const diffMs = nextExecution - currentTime;
        
        if (diffMs <= 0) {
            nextUpdateElement.innerHTML = '<span class="badge bg-warning">Très bientôt</span>';
            
            // Vérifier l'état après un délai
            setTimeout(() => {
                fetchStatusUpdate(true);
            }, 30000);
            return;
        }
        
        // Calculer les minutes et secondes
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
        
        // Mise à jour de l'affichage avec les valeurs correctes
        nextUpdateElement.innerHTML = `<span class="time-remaining">${minutes} min ${seconds} sec</span>`;
        
        // Mettre à jour chaque seconde
        setTimeout(updateCountdown, 1000);
    }
    
    // Démarrer le compte à rebours
    updateCountdown();
}

/**
 * Initialise les vérifications périodiques du statut
 */
function initStatusRefresh() {
    // Vérifier seulement si nous sommes sur une page avec monitoring actif
    if (!document.querySelector('.status-container')) return;
    
    // Vérifier toutes les 30 secondes
    setInterval(() => {
        fetchStatusUpdate(false);
    }, 30000);
    
    // Gestionnaire pour le bouton Stop Monitoring
    const stopButton = document.querySelector('button[type="submit"][class*="btn-danger"]');
    if (stopButton && stopButton.closest('form[action*="/stop"]')) {
        stopButton.addEventListener('click', function(event) {
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Arrêt en cours...';
            this.disabled = true;
        });
    }
}

/**
 * Récupère les mises à jour de statut depuis l'API
 */
function fetchStatusUpdate(forceReload) {
    fetch('/api/status')
        .then(response => {
            if (!response.ok) throw new Error('Erreur réseau');
            return response.json();
        })
        .then(data => {
            // Mise à jour du temps restant s'il est disponible et valide
            if (data.time_remaining && data.time_remaining !== "NaN min NaN sec") {
                const nextUpdateElement = document.getElementById('nextUpdate');
                if (nextUpdateElement) {
                    nextUpdateElement.innerHTML = `<span class="time-remaining">${data.time_remaining}</span>`;
                }
                
                // Mettre à jour l'heure de prochaine exécution si disponible
                if (data.next_execution) {
                    const nextExecutionElement = document.querySelector('.next-execution-time');
                    if (nextExecutionElement) {
                        nextExecutionElement.textContent = data.next_execution;
                    }
                }
            }
            
            // Si le monitoring n'est plus actif ou si un rechargement est forcé, recharger la page
            if ((forceReload || !data.active) && document.querySelector('.status-container')) {
                window.location.reload();
            }
        })
        .catch(error => console.error('Erreur de récupération du statut:', error));
}

/**
 * Initialise la validation des formulaires
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const requiredInputs = form.querySelectorAll('input[required]');
            let isValid = true;
            
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
            }
        });
        
        // Validation en temps réel
        const inputs = form.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (input.value.trim()) {
                    input.classList.remove('is-invalid');
                }
            });
        });
    });
}

// Fonction pour basculer la visibilité du mot de passe
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const icon = input.parentNode.querySelector('.fa-eye, .fa-eye-slash');
    
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}