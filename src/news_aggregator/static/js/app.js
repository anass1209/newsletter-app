document.addEventListener('DOMContentLoaded', function() {
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
            statusElement.scrollIntoView({ behavior: 'smooth' });
        }
    }
});

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
        })
        .catch(error => {
            console.error("Error fetching status:", error);
        });
}

// Update timer display with data from API
function updateTimerWithData(data) {
    if (!data || !data.next_execution) return;
    
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Update data attribute
    nextUpdateElement.dataset.nextExecution = data.next_execution;
    
    // Check if timer shows NaN, restart countdown if it does
    if (nextUpdateElement.textContent.includes('NaN')) {
        startCountdown();
    } else if (data.time_remaining) {
        // Otherwise just update the text
        nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${data.time_remaining}`;
    }
    
    // Update the formatted next execution time if available
    const nextExecutionElement = document.querySelector('.next-update-time');
    if (nextExecutionElement && data.formatted_next) {
        nextExecutionElement.textContent = data.formatted_next;
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
    
    // If no valid date, use now + 24 hours as fallback
    if (!nextUpdate) {
        const now = new Date();
        nextUpdate = new Date(now.getTime() + 24 * 60 * 60 * 1000); // 24 hours in ms
        console.log("Using fallback next execution:", nextUpdate);
    }
    
    // Timer update function
    function updateTimer() {
        const now = new Date();
        const diffMs = nextUpdate - now;
        
        // If time has passed
        if (diffMs <= 0) {
            nextUpdateElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
            
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
        
        // Update display
        nextUpdateElement.innerHTML = `<i class="fas fa-hourglass-half me-1"></i>${displayText}`;
        
        // Update each second
        setTimeout(updateTimer, 1000);
    }
    
    // Start countdown
    updateTimer();
}