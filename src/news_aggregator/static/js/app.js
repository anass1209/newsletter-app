// src/news_aggregator/static/js/app.js

/**
 * Newsletter App JavaScript
 * Handles UI interactions, automatic updates, and countdown timers
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialization
    initAlertAutoClose();
    initFormValidation();
    initMonitoringDashboard();
    initPasswordToggle();
});

/**
 * Close success and info alerts automatically after a delay
 */
function initAlertAutoClose() {
    const autoCloseDelay = 5000; // 5 seconds
    
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert.alert-info, .alert.alert-success:not(.fixed)');
        alerts.forEach(function(alert) {
            fadeOutElement(alert);
        });
    }, autoCloseDelay);
}

/**
 * Fade out an element and remove it from DOM when complete
 * @param {HTMLElement} element - The element to fade out
 */
function fadeOutElement(element) {
    let opacity = 1;
    const timer = setInterval(function() {
        if (opacity <= 0.1) {
            clearInterval(timer);
            element.style.display = 'none';
            
            // Optional: remove from DOM after animation
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }
        element.style.opacity = opacity;
        opacity -= opacity * 0.1;
    }, 20);
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(form)) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
        
        // Add input event listeners for real-time validation feedback
        const inputs = form.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                validateInput(input);
            });
        });
    });
}

/**
 * Validate a specific form input
 * @param {HTMLInputElement} input - The input element to validate
 * @returns {boolean} - Whether the input is valid
 */
function validateInput(input) {
    const isValid = input.checkValidity();
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
    }
    
    return isValid;
}

/**
 * Validate an entire form
 * @param {HTMLFormElement} form - The form to validate
 * @returns {boolean} - Whether the form is valid
 */
function validateForm(form) {
    let isValid = true;
    
    // Check each required input
    const inputs = form.querySelectorAll('input[required]');
    inputs.forEach(input => {
        if (!validateInput(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

/**
 * Initialize password toggle for API key fields
 */
function initPasswordToggle() {
    // Function is implemented inline in the HTML for simplicity
    // See the togglePassword function in the index.html script block
}

/**
 * Initialize all monitoring dashboard features
 */
function initMonitoringDashboard() {
    const monitoringActive = document.querySelector('.status-container');
    if (!monitoringActive) return;
    
    // Initialize components
    initCountdownTimer();
    initStatusRefresh();
    initInfoCardAnimations();
    initActivityLogInteractions();
    
    // Display welcome toast
    showWelcomeToast();
}

/**
 * Initialize enhanced countdown timer with visual feedback
 */
function initCountdownTimer() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Get next update time from data attribute
    let nextUpdateTime;
    
    if (nextUpdateElement.dataset.nextExecution) {
        nextUpdateTime = new Date(nextUpdateElement.dataset.nextExecution);
    } else {
        // Default to 1 hour from now if not specified
        const now = new Date();
        nextUpdateTime = new Date(now.getTime() + 60 * 60 * 1000);
    }
    
    function updateCountdown() {
        const now = new Date();
        const timeDiff = nextUpdateTime - now;
        
        if (timeDiff <= 0) {
            nextUpdateElement.innerHTML = '<span class="badge bg-warning">Coming soon</span>';
            
            // Refresh status
            setTimeout(() => { 
                fetchStatusUpdate(); 
            }, 15000);
            return;
        }
        
        // Calculate minutes and seconds
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
        
        // Calculate percentage of hour completed for progress indicator
        const hourInMs = 60 * 60 * 1000;
        const percentComplete = 100 - ((timeDiff / hourInMs) * 100);
        
        // Update with formatted time and progress bar
        nextUpdateElement.innerHTML = `
            <span class="time-remaining">${minutes} min ${seconds} sec</span>
            <div class="progress mt-2" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: ${percentComplete}%"></div>
            </div>
        `;
        
        // Update every second
        setTimeout(updateCountdown, 1000);
    }
    
    // Start countdown
    updateCountdown();
}

/**
 * Initialize automatic status refresh
 */
function initStatusRefresh() {
    // Refresh status every 30 seconds
    setInterval(fetchStatusUpdate, 30000);
}

/**
 * Fetch updated status from the server
 */
function fetchStatusUpdate() {
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateDashboardWithNewData(data);
        })
        .catch(error => {
            console.error('Error fetching status update:', error);
        });
}

/**
 * Update dashboard with new data from server
 */
function updateDashboardWithNewData(data) {
    // Update time remaining display if available
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (nextUpdateElement && data.time_remaining) {
        // Leave the update to the countdown timer function
        nextUpdateElement.dataset.nextExecution = data.next_execution_iso || '';
    }
    
    // If monitoring is no longer active, reload the page
    if (document.querySelector('.status-container') && !data.active) {
        window.location.reload();
    }
    
    // Refresh the activity log if there's new activity
    if (data.last_activity_time && data.last_activity_time !== lastActivityTime) {
        lastActivityTime = data.last_activity_time;
        updateActivityLog(data.activities || []);
    }
}

// Global variable to track last activity time
let lastActivityTime = '';

/**
 * Update activity log with new activities
 */
function updateActivityLog(activities) {
    const timelineContainer = document.querySelector('.timeline');
    if (!timelineContainer || !activities.length) return;
    
    // Create HTML for new activities
    const newActivitiesHTML = activities.map(activity => `
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <p class="timeline-date">${activity.time}</p>
                <p class="timeline-text">${activity.message}</p>
            </div>
        </div>
    `).join('');
    
    // Add new activities with animation
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = newActivitiesHTML;
    
    // Add each new activity with animation
    while (tempDiv.firstChild) {
        const newItem = tempDiv.firstChild;
        newItem.style.opacity = '0';
        newItem.style.transform = 'translateY(-10px)';
        timelineContainer.insertBefore(newItem, timelineContainer.firstChild);
        
        // Trigger animation
        setTimeout(() => {
            newItem.style.transition = 'opacity 0.5s, transform 0.5s';
            newItem.style.opacity = '1';
            newItem.style.transform = 'translateY(0)';
        }, 10);
    }
}

/**
 * Initialize info card animations
 */
function initInfoCardAnimations() {
    const infoCards = document.querySelectorAll('.info-card');
    
    infoCards.forEach((card, index) => {
        // Staggered entrance animation
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s, transform 0.5s';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });
}

/**
 * Initialize activity log interactions
 */
function initActivityLogInteractions() {
    const timelineItems = document.querySelectorAll('.timeline-item');
    
    timelineItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.querySelector('.timeline-dot').style.transform = 'scale(1.2)';
            item.querySelector('.timeline-dot').style.transition = 'transform 0.3s';
        });
        
        item.addEventListener('mouseleave', () => {
            item.querySelector('.timeline-dot').style.transform = 'scale(1)';
        });
    });
}

/**
 * Show welcome toast message
 */
function showWelcomeToast() {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast HTML
    const topic = document.querySelector('.lead strong')?.textContent || 'your chosen topic';
    const toastHTML = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="fas fa-satellite-dish me-2 text-primary"></i>
                <strong class="me-auto">Newsletter Monitoring</strong>
                <small>Just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <i class="fas fa-check-circle text-success me-2"></i>
                Monitoring active for "${topic}". You'll receive hourly updates via email.
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.innerHTML += toastHTML;
    
    // Initialize and show toast
    const toastElement = toastContainer.querySelector('.toast:last-child');
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    toast.show();
}