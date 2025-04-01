/**
 * Newsletter Monitoring Application
 * Professional UX Enhancement
 * 
 * Gère les interactions utilisateur, la validation des formulaires,
 * les animations et les mises à jour automatiques des statuts.
 */

"use strict";

// Namespace pour éviter les conflits
const NewsletterApp = {
    // Configuration
    config: {
        alertAutoCloseDelay: 5000,
        statusRefreshInterval: 30000,
        animationDuration: 300,
        progressBarUpdateInterval: 1000
    },
    
    // Initialisation de l'application
    init: function() {
        this.setupEventListeners();
        this.setupAlerts();
        this.setupCountdown();
        this.setupFormValidation();
        this.setupStatusUpdates();
    },
    
    // Mise en place des écouteurs d'événements
    setupEventListeners: function() {
        // Gestionnaires pour les toggles de formulaires
        document.querySelectorAll('[data-toggle]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = btn.getAttribute('data-toggle');
                if (target) {
                    this.toggleElement(document.getElementById(target));
                }
            });
        });
        
        // Gestionnaires pour les boutons de visibilité des mots de passe
        document.querySelectorAll('.btn-outline-secondary').forEach(btn => {
            if (btn.onclick && btn.onclick.toString().includes('togglePassword')) {
                // Remplacement par notre fonction
                btn.onclick = null;
                btn.addEventListener('click', (e) => {
                    const inputId = btn.closest('.input-group').querySelector('input').id;
                    this.togglePasswordVisibility(inputId);
                });
            }
        });
    },
    
    // Gestion des alertes
    setupAlerts: function() {
        setTimeout(() => {
            document.querySelectorAll('.alert:not(.fixed)').forEach(alert => {
                this.fadeOutElement(alert);
            });
        }, this.config.alertAutoCloseDelay);
        
        // Ajouter des gestionnaires pour les boutons de fermeture des alertes
        document.querySelectorAll('.alert .btn-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.fadeOutElement(e.target.closest('.alert'));
            });
        });
    },
    
    // Animer la disparition d'un élément
    fadeOutElement: function(element) {
        if (!element) return;
        
        element.style.transition = `opacity ${this.config.animationDuration}ms ease-out`;
        element.style.opacity = '0';
        
        setTimeout(() => {
            if (element.parentNode) {
                element.style.display = 'none';
                // Optionnel: supprimer complètement du DOM
                // element.parentNode.removeChild(element);
            }
        }, this.config.animationDuration);
    },
    
    // Basculer la visibilité d'un élément
    toggleElement: function(element) {
        if (!element) return;
        
        if (element.classList.contains('d-none')) {
            // Afficher l'élément
            element.classList.remove('d-none');
            element.style.opacity = '0';
            
            // Déclencher le reflow pour que la transition fonctionne
            element.offsetHeight;
            
            element.style.transition = `opacity ${this.config.animationDuration}ms ease-in`;
            element.style.opacity = '1';
        } else {
            // Masquer l'élément
            element.style.transition = `opacity ${this.config.animationDuration}ms ease-out`;
            element.style.opacity = '0';
            
            setTimeout(() => {
                element.classList.add('d-none');
            }, this.config.animationDuration);
        }
    },
    
    // Basculer la visibilité d'un mot de passe
    togglePasswordVisibility: function(inputId) {
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
    },
    
    // Configurer le compte à rebours pour la prochaine mise à jour
    setupCountdown: function() {
        const countdownElement = document.getElementById('nextUpdate');
        if (!countdownElement) return;
        
        let nextUpdateTime;
        
        // Obtenir le temps de la prochaine mise à jour
        if (countdownElement.dataset.nextExecution) {
            nextUpdateTime = new Date(countdownElement.dataset.nextExecution);
        } else {
            // Par défaut, dans une heure
            const now = new Date();
            nextUpdateTime = new Date(now.getTime() + 60 * 60 * 1000);
        }
        
        const updateCountdown = () => {
            const now = new Date();
            const remainingMs = nextUpdateTime - now;
            
            if (remainingMs <= 0) {
                countdownElement.innerHTML = '<span class="badge bg-warning">Très bientôt</span>';
                
                // Vérifier l'état après un délai
                setTimeout(() => {
                    this.fetchStatusUpdate();
                }, 30000);
                return;
            }
            
            // Calculer les minutes et secondes restantes
            const minutes = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((remainingMs % (1000 * 60)) / 1000);
            
            // Mettre à jour l'affichage
            countdownElement.innerHTML = `<span class="time-remaining">${minutes} min ${seconds} sec</span>`;
            
            // Mettre à jour toutes les secondes
            setTimeout(updateCountdown, 1000);
        };
        
        // Démarrer le compte à rebours
        updateCountdown();
    },
    
    // Configurer la validation des formulaires
    setupFormValidation: function() {
        const forms = document.querySelectorAll('.needs-validation');
        
        forms.forEach(form => {
            // Validation à la soumission
            form.addEventListener('submit', event => {
                if (!this.validateForm(form)) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            });
            
            // Validation en temps réel
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
            inputs.forEach(input => {
                // Valider lors de la perte de focus
                input.addEventListener('blur', () => {
                    this.validateInput(input);
                });
                
                // Réinitialiser les erreurs lors de la saisie
                input.addEventListener('input', () => {
                    input.classList.remove('is-invalid');
                    
                    // Supprimer les messages d'erreur personnalisés
                    const feedbackEl = input.parentNode.querySelector('.validation-message.invalid');
                    if (feedbackEl) {
                        feedbackEl.remove();
                    }
                });
            });
        });
    },
    
    // Valider un champ de formulaire
    validateInput: function(input) {
        let isValid = input.checkValidity();
        
        // Validations personnalisées supplémentaires
        if (input.type === 'email' && input.value) {
            const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
            isValid = emailPattern.test(input.value);
            
            if (!isValid) {
                this.showValidationError(input, "Veuillez saisir une adresse email valide");
                return false;
            }
        }
        
        if (input.id === 'tavily_api_key' && input.value) {
            if (input.value.length < 20) {
                this.showValidationError(input, "La clé API semble trop courte");
                return false;
            }
        }
        
        if (input.id === 'gemini_api_key' && input.value) {
            if (input.value.length < 20) {
                this.showValidationError(input, "La clé API semble trop courte");
                return false;
            }
        }
        
        // Appliquer les classes CSS appropriées
        if (isValid) {
            input.classList.add('is-valid');
            input.classList.remove('is-invalid');
        } else {
            input.classList.add('is-invalid');
            input.classList.remove('is-valid');
            
            // Afficher un message d'erreur générique si aucun n'a été défini
            if (!input.parentNode.querySelector('.validation-message.invalid')) {
                this.showValidationError(input, "Ce champ est requis");
            }
        }
        
        return isValid;
    },
    
    // Afficher un message d'erreur de validation personnalisé
    showValidationError: function(input, message) {
        // Supprimer tout message d'erreur existant
        const existingMsg = input.parentNode.querySelector('.validation-message.invalid');
        if (existingMsg) {
            existingMsg.remove();
        }
        
        // Créer un nouvel élément pour le message d'erreur
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'validation-message invalid';
        feedbackEl.textContent = message;
        
        // Ajouter après l'input ou à la fin du parent
        const formText = input.parentNode.querySelector('.form-text');
        if (formText) {
            input.parentNode.insertBefore(feedbackEl, formText);
        } else {
            input.parentNode.appendChild(feedbackEl);
        }
        
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
    },
    
    // Valider un formulaire entier
    validateForm: function(form) {
        let isValid = true;
        
        // Valider tous les champs requis
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        inputs.forEach(input => {
            if (!this.validateInput(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    },
    
    // Configurer les mises à jour automatiques du statut
    setupStatusUpdates: function() {
        if (!document.querySelector('.status-container')) return;
        
        // Mettre à jour le statut périodiquement
        setInterval(() => {
            this.fetchStatusUpdate();
        }, this.config.statusRefreshInterval);
    },
    
    // Récupérer les mises à jour de statut depuis le serveur
    fetchStatusUpdate: function() {
        // Afficher un indicateur de mise à jour
        const statusContainer = document.querySelector('.status-container');
        if (statusContainer) {
            statusContainer.classList.add('status-updating');
        }
        
        fetch('/api/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau lors de la récupération du statut');
                }
                return response.json();
            })
            .then(data => {
                this.updateStatusDisplay(data);
                // Supprimer l'indicateur de mise à jour
                if (statusContainer) {
                    statusContainer.classList.remove('status-updating');
                }
            })
            .catch(error => {
                console.error('Erreur de récupération du statut:', error);
                // Supprimer l'indicateur de mise à jour en cas d'erreur également
                if (statusContainer) {
                    statusContainer.classList.remove('status-updating');
                }
            });
    },
    
    // Mettre à jour l'affichage du statut avec les nouvelles données
    updateStatusDisplay: function(data) {
        // Mettre à jour le temps restant s'il est disponible
        const nextUpdateElement = document.getElementById('nextUpdate');
        if (nextUpdateElement && data.time_remaining) {
            nextUpdateElement.innerHTML = `<span class="time-remaining">${data.time_remaining}</span>`;
        }
        
        // Si le monitoring n'est plus actif, recharger la page
        const statusContainer = document.querySelector('.status-container');
        if (statusContainer && !data.active) {
            // Afficher un message de chargement
            statusContainer.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                    <p class="mt-2">Rechargement de la page...</p>
                </div>
            `;
            
            // Recharger la page après un court délai
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }
};

// Initialiser l'application au chargement du document
document.addEventListener('DOMContentLoaded', function() {
    NewsletterApp.init();
});