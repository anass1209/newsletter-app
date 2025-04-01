// src/news_aggregator/static/js/app.js

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after a few seconds
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
    
    // Initialize countdown for next update
    if (document.getElementById('nextUpdate')) {
        startCountdown();
    }

    // Update status information regularly
    if (document.querySelector('.status-container')) {
        // First call after 5 seconds
        setTimeout(refreshStatus, 5000);
        // Then every 30 seconds
        setInterval(refreshStatus, 30000);
    }

    // Add event listeners for toggle buttons
    const toggleConfigBtn = document.querySelector('[onclick="toggleConfigForm()"]');
    if (toggleConfigBtn) {
        toggleConfigBtn.addEventListener('click', toggleConfigForm);
    }

    const toggleTopicBtn = document.querySelector('[onclick="toggleTopicForm()"]');
    if (toggleTopicBtn) {
        toggleTopicBtn.addEventListener('click', toggleTopicForm);
    }

    // Handle Stop Monitoring button
    const stopButton = document.querySelector('form[action="/stop"] button');
    if (stopButton) {
        stopButton.addEventListener('click', function(e) {
            // Show processing state
            stopButton.disabled = true;
            stopButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Stopping...';
            
            // Submit form normally - no need to prevent default
        });
    }

    // Initialize password toggles
    initPasswordToggles();
});

// Function to toggle configuration form display
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

// Function to toggle topic form display
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

// Function to initialize password toggles
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

// Function to refresh status via API
function refreshStatus() {
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log("Status update received:", data);
            
            // If monitoring is no longer active but page shows active, reload
            if (document.querySelector('.status-container') && !data.active) {
                window.location.reload();
                return;
            }
            
            // Update next execution time
            updateTimerWithData(data);
        })
        .catch(error => {
            console.error("Error fetching status:", error);
        });
}

// Function to update timer with received data
function updateTimerWithData(data) {
    if (!data || !data.next_execution) return;
    
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Update data attribute
    nextUpdateElement.dataset.nextExecution = data.next_execution;
    
    // If timer shows NaN, restart countdown
    if (nextUpdateElement.textContent.includes('NaN')) {
        startCountdown();
    } else if (data.time_remaining) {
        // Otherwise just update the text
        nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${data.time_remaining}`;
    }
}

// Function for countdown to next update
function startCountdown() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Get reference time
    let nextUpdate = null;
    
    if (nextUpdateElement.dataset.nextExecution) {
        try {
            // Try to parse ISO date
            nextUpdate = new Date(nextUpdateElement.dataset.nextExecution);
            console.log("Next execution parsed:", nextUpdate);
            
            // Check if date is valid
            if (isNaN(nextUpdate.getTime())) {
                console.log("Invalid date format, using fallback");
                nextUpdate = null;
            }
        } catch(e) {
            console.error("Error parsing date:", e);
            nextUpdate = null;
        }
    }
    
    // If no valid date, use now + 24 hours as fallback (for daily updates)
    if (!nextUpdate) {
        const now = new Date();
        nextUpdate = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        console.log("Using fallback next execution:", nextUpdate);
    }
    
    // Function to update countdown
    function updateTimer() {
        const now = new Date();
        const diffMs = nextUpdate - now;
        
        // If time has passed
        if (diffMs <= 0) {
            nextUpdateElement.innerHTML = '<i class="fas fa-clock me-1"></i> very soon';
            
            // Reload status after 10 seconds
            setTimeout(refreshStatus, 10000);
            return;
        }
        
        // Calculate hours, minutes and seconds - better for daily updates
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
        
        // Display remaining time in format that shows hours
        nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${hours}h ${minutes}m ${seconds}s`;
        
        // Update every second
        setTimeout(updateTimer, 1000);
    }
    
    // Start countdown
    updateTimer();
}

// Function to toggle password visibility
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