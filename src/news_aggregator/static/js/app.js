document.addEventListener('DOMContentLoaded', function() {
    // Détection et stockage du fuseau horaire
    try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        document.cookie = `timezone=${encodeURIComponent(timezone)}; path=/; max-age=86400; SameSite=Lax`;
        console.log("Set timezone cookie to:", timezone);
    } catch(e) {
        console.warn("Could not detect timezone:", e);
    }

    // Hide alerts automatically after a few seconds (except fixed ones)
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
    
    // Initialize countdown timer for next update
    if (document.getElementById('nextUpdate')) {
        startCountdown();
    }

    // Refresh status information regularly
    if (document.querySelector('.status-container')) {
        // First call after 5 seconds
        setTimeout(refreshStatus, 5000);
        // Then every 30 seconds
        setInterval(refreshStatus, 30000);
    }

    // Initialize password toggle functionality
    initPasswordToggles();
    
    // Scroll to status section if URL has the status anchor
    if (window.location.hash === '#status') {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            // Scroll avec délai pour s'assurer que la page est chargée
            setTimeout(function() {
                statusElement.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        }
    }
    
    // CORRECTION: Attacher les écouteurs pour la visibilité du mot de passe
    const toggleBtns = document.querySelectorAll('.input-group .btn-outline-secondary');
    toggleBtns.forEach(btn => {
        // Vérifier si le bouton contient une icône d'oeil pour être plus spécifique
        if (btn.querySelector('.fa-eye, .fa-eye-slash')) {
            btn.addEventListener('click', function() {
                performTogglePassword(this); // Appeler la fonction dédiée
            });
        }
    });

    // Bouton "Start Monitoring"
    const startButton = document.getElementById('startMonitoringBtn');
    if (startButton) {
        startButton.addEventListener('click', function(event) {
            const form = this.closest('form');
            if (!form.checkValidity()) {
                // Si invalide, empêcher la soumission par défaut et laisser le navigateur afficher les erreurs
                event.preventDefault();
                form.reportValidity();
            } else {
                // Si valide, afficher l'état de chargement (la soumission se fera normalement)
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
                this.disabled = true;
            }
        });
        
        // S'assurer que le formulaire est bien soumis même si JS est activé
        const startForm = startButton.closest('form');
        if (startForm) {
            startForm.addEventListener('submit', function() {
                // Désactiver le bouton quand la soumission commence réellement
                if(startButton.disabled == false) { // Éviter double exécution
                    startButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
                    startButton.disabled = true;
                }
            });
        }
    }

    // Bouton "Stop Monitoring"
    const stopButton = document.getElementById('stopMonitoringBtn');
    if (stopButton) {
        // Utiliser l'événement submit du formulaire est plus fiable
        const stopForm = stopButton.closest('form');
        if (stopForm) {
            stopForm.addEventListener('submit', function() {
                stopButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Stopping...';
                stopButton.disabled = true;
            });
        }
    }
});

// Function to toggle password visibility
function performTogglePassword(button) {
    const inputGroup = button.closest('.input-group');
    if (!inputGroup) return; // Sécurité
    const input = inputGroup.querySelector('input');
    const icon = button.querySelector('i');
    if (!input || !icon) return; // Sécurité

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

// Initialize password toggle buttons
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

// Refresh status information via API
function refreshStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            console.log("Status update received:", data);
            
            // If monitoring is no longer active, reload the page
            if (document.querySelector('.status-container') && !data.active) {
                window.location.reload();
                return;
            }
            
            // Update timer with new data
            updateTimerWithData(data);
            
            // Also update last execution time if provided
            if (data.last_execution) {
                const lastUpdateElement = document.getElementById('lastUpdate');
                if (lastUpdateElement) {
                    lastUpdateElement.textContent = data.formatted_last || "Recently";
                }
            }
        })
        .catch(error => {
            console.error("Error fetching status:", error);
        });
}

// Update timer display with data from API
function updateTimerWithData(data) {
    if (!data) return;
    
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Update display for next execution time
    const nextExecutionElement = document.querySelector('.next-update-time');
    if (nextExecutionElement && data.formatted_next) {
        nextExecutionElement.textContent = data.formatted_next;
    } else if (nextExecutionElement) {
        nextExecutionElement.innerHTML = `<span class="badge bg-warning text-dark">None scheduled</span>`;
    }
    
    // Update the countdown badge
    if (data.next_execution) {
        // Update data attribute for next execution
        nextUpdateElement.dataset.nextExecution = data.next_execution;
        
        // Check if we already have a countdown running
        if (nextUpdateElement.textContent.includes('NaN')) {
            // Restart countdown if formatting is broken
            startCountdown();
        } else if (data.time_remaining) {
            // Otherwise just update the text
            nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${data.time_remaining}`;
            nextUpdateElement.classList.remove('bg-warning', 'text-dark', 'bg-danger');
            nextUpdateElement.classList.add('bg-primary');
        }
    } else {
        // No next execution scheduled
        nextUpdateElement.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>No upcoming update`;
        nextUpdateElement.classList.remove('bg-primary', 'bg-danger');
        nextUpdateElement.classList.add('bg-warning', 'text-dark');
        nextUpdateElement.removeAttribute('data-next-execution');
    }
}

// Countdown timer for next update
function startCountdown() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Get reference time
    let nextUpdate = null;
    
    if (nextUpdateElement.dataset.nextExecution) {
        try {
            // Try parsing ISO date
            nextUpdate = new Date(nextUpdateElement.dataset.nextExecution);
            console.log("Next execution parsed:", nextUpdate);
            
            // Verify valid date
            if (isNaN(nextUpdate.getTime())) {
                console.log("Invalid date format, using fallback");
                nextUpdate = null;
            }
        } catch(e) {
            console.error("Error parsing date:", e);
            nextUpdate = null;
        }
    }
    
    // If no valid date, display message and don't start countdown
    if (!nextUpdate) {
        nextUpdateElement.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>No scheduled update';
        nextUpdateElement.classList.remove('bg-primary', 'bg-danger');
        nextUpdateElement.classList.add('bg-warning', 'text-dark');
        return;
    }
    
    // Timer update function
    function updateTimer() {
        const now = new Date();
        const diffMs = nextUpdate - now;
        
        // If time has passed
        if (diffMs <= 0) {
            nextUpdateElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
            nextUpdateElement.classList.remove('bg-warning', 'text-dark', 'bg-danger');
            nextUpdateElement.classList.add('bg-primary');
            
            // Reload status after 10 seconds
            setTimeout(refreshStatus, 10000);
            return;
        }
        
        // Calculate time components
        const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
        
        // Format display text
        let displayText = '';
        if (days > 0) {
            displayText = `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            displayText = `${hours}h ${minutes}m ${seconds}s`;
        } else {
            displayText = `${minutes}m ${seconds}s`;
        }
        
        // Update display with consistent styling
        nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${displayText}`;
        nextUpdateElement.classList.remove('bg-warning', 'text-dark', 'bg-danger');
        nextUpdateElement.classList.add('bg-primary');
        
        // Update each second
        setTimeout(updateTimer, 1000);
    }
    
    // Start countdown
    updateTimer();
}