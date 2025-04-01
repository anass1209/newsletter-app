/**
 * Newsletter Monitor - Professional JavaScript
 * Enhanced user interactions and UI effects
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeTooltips();
    initializePopovers();
    storeUserTimezone();
    setupAutoDismissAlerts();
    initPasswordToggles();
    initFormSubmitHandlers();
    handleHashScroll();
    setupButtonEventListeners();
    applyAnimations();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl, {
            animation: true,
            delay: { show: 100, hide: 100 }
        }));
    }
}

/**
 * Initialize Bootstrap popovers
 */
function initializePopovers() {
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl, {
            html: true,
            animation: true
        }));
    }
}

/**
 * Store user's timezone in a cookie for server-side use
 */
function storeUserTimezone() {
    try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        document.cookie = `timezone=${encodeURIComponent(timezone)}; path=/; max-age=86400; SameSite=Lax`;
        console.log(`Timezone detected: ${timezone}`);
    } catch(e) {
        console.warn("Could not detect timezone:", e);
    }
}

/**
 * Set up automatic dismissal of non-error alerts after delay
 */
function setupAutoDismissAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-danger):not(.alert-warning):not(.alert-persistent)');
        alerts.forEach(function(alert) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                // Fade out before closing
                alert.style.transition = 'opacity 0.5s ease-out';
                alert.style.opacity = '0';
                setTimeout(() => bsAlert.close(), 500);
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
                
                // Auto-hide after 5 seconds for security
                setTimeout(() => {
                    if (input.type === "text") {
                        input.type = "password";
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                }, 5000);
            } else {
                input.type = "password";
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

/**
 * Set up form submission handlers with validation and loading states
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
                
                // Shake the first invalid field to draw attention
                const firstInvalid = this.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.classList.add('shake-animation');
                    setTimeout(() => firstInvalid.classList.remove('shake-animation'), 500);
                    firstInvalid.focus();
                }
            } else if (generateBtn) {
                // Show loading state
                generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Generating...';
                generateBtn.disabled = true;
                
                // Add visual feedback
                this.classList.add('opacity-75');
                
                // Show info toast for longer operations
                showToast('Generating your newsletter...', 'info');
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
                
                // Apply success animation to form container
                const formContainer = this.closest('.form-container');
                if (formContainer) {
                    formContainer.style.transition = 'transform 0.3s ease';
                    formContainer.style.transform = 'scale(0.98)';
                    setTimeout(() => {
                        formContainer.style.transform = 'scale(1)';
                    }, 300);
                }
            }
        });
    }
    
    // Settings form
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        const updateBtn = document.getElementById('update-settings-btn');
        
        settingsForm.addEventListener('submit', function(event) {
            if (!this.checkValidity()) {
                event.preventDefault();
                highlightInvalidFields(this);
                this.reportValidity();
            } else if (updateBtn) {
                updateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Updating...';
                updateBtn.disabled = true;
                showToast('Updating your settings...', 'info');
            }
        });
    }
}

/**
 * Set up button event listeners for better UX
 */
function setupButtonEventListeners() {
    // Settings button
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function() {
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading...';
            this.classList.add('disabled');
        });
    }
    
    // Back buttons
    document.querySelectorAll('a.btn-outline-secondary').forEach(btn => {
        if (btn.innerHTML.includes('Back') || btn.innerHTML.includes('Cancel')) {
            btn.addEventListener('click', function(e) {
                // Only show loading state if actually navigating (not canceling)
                if (!btn.getAttribute('href').includes('#')) {
                    this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Going back...';
                    this.classList.add('disabled');
                }
            });
        }
    });
    
    // Add ripple effect to all buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', createRippleEffect);
    });
}

/**
 * Handle scrolling to hash elements with smooth animation
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
    
    // Handle in-page anchor links
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                smoothScrollTo(targetElement);
                // Update URL without reloading
                history.pushState(null, null, targetId);
            }
        });
    });
}

/**
 * Apply animations to page elements for a more dynamic feel
 */
function applyAnimations() {
    // Fade in the main content
    const mainContent = document.querySelector('main .container');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Animate steps on scroll
    const steps = document.querySelectorAll('.step');
    if (steps.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        steps.forEach(step => observer.observe(step));
    }
}

/**
 * Highlight invalid fields in a form
 * @param {HTMLFormElement} form - The form to check
 */
function highlightInvalidFields(form) {
    // Remove any previous invalid states
    form.querySelectorAll('.is-invalid').forEach(field => {
        field.classList.remove('is-invalid');
    });
    
    // Add invalid class to invalid fields
    const invalidFields = form.querySelectorAll(':invalid');
    invalidFields.forEach(field => {
        field.classList.add('is-invalid');
        
        // Add event listener to remove the invalid class once corrected
        field.addEventListener('input', function() {
            if (this.validity.valid) {
                this.classList.remove('is-invalid');
            }
        });
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
    
    // Add highlight effect that fades after animation
    element.classList.add('highlight-effect');
    setTimeout(() => {
        element.classList.remove('highlight-effect');
    }, 1000);
}

/**
 * Create a ripple effect on button click
 * @param {Event} e - Click event
 */
function createRippleEffect(e) {
    const button = e.currentTarget;
    
    // Remove any existing ripple
    const existingRipple = button.querySelector('.ripple');
    if (existingRipple) {
        existingRipple.remove();
    }
    
    // Create ripple element
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    button.appendChild(ripple);
    
    // Get button dimensions
    const rect = button.getBoundingClientRect();
    
    // Calculate ripple size (make it bigger than the button)
    const size = Math.max(rect.width, rect.height) * 2;
    ripple.style.width = ripple.style.height = `${size}px`;
    
    // Position the ripple
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    
    // Remove ripple after animation
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Bootstrap color type (success, danger, warning, info)
 * @param {number} duration - Duration in milliseconds
 */
function showToast(message, type = 'info', duration = 5000) {
    // Create toast container if not exists
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    // Get appropriate icon for the type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'danger') icon = 'exclamation-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    
    // Toast content
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${icon} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toastEl);
    
    // Initialize and show
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: duration
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