/**
 * Newsletter Monitor - Enhanced JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();

    // Store user timezone for better time display
    storeUserTimezone();

    // Automatically hide non-error alerts after 5 seconds
    setupAutoDismissAlerts();

    // Password toggle functionality
    initPasswordToggles();
    
    // Form submission handlers
    initFormSubmitHandlers();
    
    // Animated scroll to elements with ID if specified in hash
    handleHashScroll();
    
    // Ensure proper form submission and button handling
    setupButtonEventListeners();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

/**
 * Store user's timezone in a cookie
 */
function storeUserTimezone() {
    try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        document.cookie = `timezone=${encodeURIComponent(timezone)}; path=/; max-age=86400; SameSite=Lax`;
    } catch(e) {
        console.warn("Could not detect timezone:", e);
    }
}

/**
 * Set up automatic dismissal of success alerts
 */
function setupAutoDismissAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-danger):not(.alert-warning)');
        alerts.forEach(function(alert) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.display = 'none';
            }
        });
    }, 5000);
}

/**
 * Initializes toggle password visibility functionality
 */
function initPasswordToggles() {
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.closest('.input-group').querySelector('input');
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

/**
 * Set up form submission handlers with enhanced validation and feedback
 */
function initFormSubmitHandlers() {
    // Newsletter generation form
    const newsletterForm = document.getElementById('newsletter-form');
    if (newsletterForm) {
        const generateBtn = document.getElementById('generateBtn');
        
        newsletterForm.addEventListener('submit', function(event) {
            if (!this.checkValidity()) {
                event.preventDefault();
                highlightInvalidFields(this);
                this.reportValidity();
            } else if (generateBtn) {
                generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Generating...';
                generateBtn.disabled = true;
                // Add subtle animation to button
                generateBtn.classList.add('animate-pulse');
            }
        });
    }
    
    // Configuration form
    const configForm = document.getElementById('config-form');
    if (configForm) {
        const saveBtn = document.getElementById('save-config-btn');
        
        configForm.addEventListener('submit', function(event) {
            if (!this.checkValidity()) {
                event.preventDefault();
                highlightInvalidFields(this);
                this.reportValidity();
            } else if (saveBtn) {
                saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Saving...';
                saveBtn.disabled = true;
            }
        });
    }
}

/**
 * Set up specific event listeners for buttons
 */
function setupButtonEventListeners() {
    // Modify Configuration Button
    const modifyBtn = document.getElementById('modify-config-btn');
    if (modifyBtn) {
        modifyBtn.addEventListener('click', function() {
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading...';
            this.classList.add('disabled');
            window.location.href = this.getAttribute('href');
        });
    }
    
    // Generate Newsletter Button - add direct click handler
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', function(event) {
            const form = this.closest('form');
            if (form && !form.checkValidity()) {
                event.preventDefault();
                highlightInvalidFields(form);
                form.reportValidity();
            } else {
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Generating...';
                this.disabled = true;
                form.submit();
            }
        });
    }
}

/**
 * Handle scrolling to hash elements
 */
function handleHashScroll() {
    if (window.location.hash) {
        const targetElement = document.querySelector(window.location.hash);
        if (targetElement) {
            setTimeout(function() {
                smoothScrollTo(targetElement);
            }, 300);
        }
    }
}

/**
 * Highlight invalid fields in a form
 * @param {HTMLFormElement} form - The form to check
 */
function highlightInvalidFields(form) {
    const invalidFields = form.querySelectorAll(':invalid');
    invalidFields.forEach(field => {
        field.classList.add('is-invalid');
        
        // Add event listener to remove the invalid class once corrected
        field.addEventListener('input', function() {
            if (this.validity.valid) {
                this.classList.remove('is-invalid');
            }
        }, { once: true });
    });
}

/**
 * Smooth scroll to specified element
 * @param {HTMLElement} element - Target element to scroll to
 */
function smoothScrollTo(element) {
    if (!element) return;
    
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
    
    // Add highlight effect that fades after 1 second
    element.classList.add('highlight-effect');
    setTimeout(() => {
        element.classList.remove('highlight-effect');
    }, 1000);
}

/**
 * Show a nice toast notification
 * @param {string} message - Message to display
 * @param {string} type - Notification type (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    // Check if Bootstrap Toast is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Create toast container if not exists
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        // Toast content
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add to container
        toastContainer.appendChild(toastEl);
        
        // Initialize and show
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Remove from DOM after hiding
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    } else {
        // Fallback if Bootstrap not available
        alert(message);
    }
}