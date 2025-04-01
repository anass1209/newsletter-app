// src/news_aggregator/static/js/app.js

/**
 * Newsletter App JavaScript
 * Handles UI interactions, automatic updates, and countdown timers
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialization
    initAlertAutoClose();
    initCountdownTimer();
    initToggleButtons();
    initFormValidation();
    initStatusRefresh();
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
 * Initialize the countdown timer for next update
 */
function initCountdownTimer() {
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (!nextUpdateElement) return;
    
    // Get next update time from data attribute or calculate it
    let nextUpdateTime;
    
    if (nextUpdateElement.dataset.nextExecution) {
        nextUpdateTime = new Date(nextUpdateElement.dataset.nextExecution);
    } else {
        // Default to 1 hour from now if not specified
        const now = new Date();
        nextUpdateTime = new Date(now.getTime() + 60 * 60 * 1000);
    }
    
    updateCountdown();
    
    function updateCountdown() {
        const now = new Date();
        const timeDiff = nextUpdateTime - now;
        
        if (timeDiff <= 0) {
            nextUpdateElement.innerHTML = '<span class="badge bg-warning">Very soon</span>';
            
            // Refresh the page after a delay to check for updates
            setTimeout(() => { 
                fetchStatusUpdate(); 
            }, 30000);
            return;
        }
        
        // Calculate minutes and seconds
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
        
        // Update with formatted time and styled span
        nextUpdateElement.innerHTML = `<span class="time-remaining">${minutes} min ${seconds} sec</span>`;
        
        // Update every second
        setTimeout(updateCountdown, 1000);
    }
}

/**
 * Initialize toggle buttons for forms
 */
function initToggleButtons() {
    // Handle configuration form toggle
    const configBtn = document.querySelector('[data-toggle="config-form"]');
    if (configBtn) {
        configBtn.addEventListener('click', function() {
            toggleFormVisibility('configForm');
        });
    }
    
    // Handle topic form toggle
    const topicBtn = document.querySelector('[data-toggle="topic-form"]');
    if (topicBtn) {
        topicBtn.addEventListener('click', function() {
            toggleFormVisibility('topicForm');
        });
    }
}

/**
 * Toggle form visibility with smooth animation
 * @param {string} formId - The ID of the form to toggle
 */
function toggleFormVisibility(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    if (form.classList.contains('d-none')) {
        // Show form
        form.classList.remove('d-none');
        setTimeout(() => {
            form.classList.add('form-transition');
            form.style.opacity = 1;
        }, 10);
    } else {
        // Hide form
        form.style.opacity = 0;
        setTimeout(() => {
            form.classList.add('d-none');
            form.classList.remove('form-transition');
        }, 300);
    }
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
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
 * Initialize status refresh for active monitoring
 */
function initStatusRefresh() {
    if (!document.querySelector('.status-container')) return;
    
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
            updateStatusDisplay(data);
        })
        .catch(error => {
            console.error('Error fetching status update:', error);
        });
}

/**
 * Update the status display with new data
 * @param {Object} data - The status data from the server
 */
function updateStatusDisplay(data) {
    // Update time remaining display if available
    const nextUpdateElement = document.getElementById('nextUpdate');
    if (nextUpdateElement && data.time_remaining) {
        nextUpdateElement.innerHTML = `<span class="time-remaining">${data.time_remaining}</span>`;
    }
    
    // If monitoring is no longer active, reload the page
    if (document.querySelector('.status-container') && !data.active) {
        window.location.reload();
    }
}