/**
 * src/news_aggregator/static/js/app.js
 * Frontend JavaScript enhancements for the Newsletter Monitor app.
 */

document.addEventListener('DOMContentLoaded', function() {

    // --- Initialize Bootstrap Features ---
    initializeTooltips();
    autoDismissAlerts();

    // --- Status Page Specific Logic ---
    if (document.getElementById('countdownTimer')) {
        initializeStatusUpdates();
    }

    // --- General Form Logic ---
    initializePasswordToggles();
    initializeStopFormConfirmation();

    console.log("App JS initialized."); // Log initialization
});

/**
 * Initializes Bootstrap tooltips.
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    console.debug("Tooltips initialized.");
}

/**
 * Automatically dismisses non-persistent alerts after a delay.
 */
function autoDismissAlerts() {
    const autoDismissDelay = 7000; // 7 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-danger):not(.alert-warning)'); // Exclude error/warning alerts

    alerts.forEach(function(alert) {
        // Ensure it's dismissible
        if (alert.querySelector('.btn-close')) {
            setTimeout(() => {
                // Use Bootstrap's Alert class to dismiss
                 try {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    if (bsAlert) {
                        bsAlert.close();
                        console.debug("Auto-dismissed alert:", alert.textContent.substring(0, 50) + "...");
                    }
                 } catch (e) {
                     console.warn("Could not auto-dismiss alert using Bootstrap:", e);
                     // Fallback: hide manually
                     alert.style.display = 'none';
                 }

            }, autoDismissDelay);
        }
    });
}


/**
 * Initializes password visibility toggle buttons.
 */
function initializePasswordToggles() {
    // Use event delegation on a parent container if forms are dynamic,
    // otherwise direct binding is fine.
    document.querySelectorAll('button[onclick^="togglePasswordVisibility"]').forEach(button => {
        // The onclick attribute handles the call, just ensure elements exist.
        // We could add the listener purely via JS instead of onclick:
        // button.addEventListener('click', function() {
        //     const inputId = this.getAttribute('onclick').match(/'([^']+)'/)[1];
        //     togglePasswordVisibility(inputId, this);
        // });
    });
    console.debug("Password visibility toggles ready.");
}

/**
 * Adds a confirmation dialog to the "Stop Monitoring" form.
 */
function initializeStopFormConfirmation() {
    const stopForm = document.getElementById('stopForm');
    if (stopForm) {
        stopForm.addEventListener('submit', function(event) {
            const confirmation = confirm('Are you sure you want to stop monitoring this topic?');
            if (!confirmation) {
                event.preventDefault(); // Stop submission if cancelled
                console.debug("Stop monitoring cancelled by user.");
            } else {
                // Optional: Provide visual feedback that it's submitting
                const stopButton = stopForm.querySelector('button[type="submit"]');
                if (stopButton) {
                    stopButton.disabled = true;
                    stopButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Stopping...';
                    console.debug("Stop monitoring confirmed, submitting form.");
                }
            }
        });
    }
}

// ========================================
// Status Update and Countdown Logic
// ========================================

let statusUpdateIntervalId = null; // To store the interval ID
let countdownIntervalId = null;    // To store the countdown interval ID

/**
 * Initializes periodic status updates and the countdown timer.
 */
function initializeStatusUpdates() {
    console.debug("Initializing status updates and countdown timer.");
    // Initial fetch and countdown start
    fetchAndUpdateStatus();
    startOrUpdateCountdown();

    // Set interval for periodic updates (e.g., every 30 seconds)
    const updateFrequency = 30 * 1000; // 30 seconds
    if (statusUpdateIntervalId) clearInterval(statusUpdateIntervalId); // Clear previous interval if any
    statusUpdateIntervalId = setInterval(fetchAndUpdateStatus, updateFrequency);
}

/**
 * Fetches the latest status from the API and updates relevant UI elements.
 */
function fetchAndUpdateStatus() {
    console.debug("Fetching API status...");
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`API request failed with status ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.debug("API Status Response:", data);

             // Check if monitoring is still active on the server
            const monitoringIsActive = document.body.contains(document.getElementById('countdownTimer'));
            if (monitoringIsActive && !data.active) {
                // Server says inactive, but UI shows active. Reload to sync.
                console.warn("Server status is inactive, reloading page to sync UI.");
                window.location.reload();
                return; // Stop further processing
            }
             if (!monitoringIsActive && data.active) {
                // Server says active, but UI shows inactive. Reload.
                console.warn("Server status is active, reloading page to sync UI.");
                window.location.reload();
                return; // Stop further processing
            }

             // Update UI elements if monitoring is active
            if (data.active) {
                updateElementText('lastUpdateDisplay', formatISODate(data.last_execution_utc, 'No updates yet'));
                updateElementText('nextUpdateDisplay', formatISODate(data.next_execution_utc, 'Calculating...'));
                updateElementText('schedulerStatus', data.status_message || 'Status unavailable');

                // Update the hidden input used by the countdown timer
                const nextExecInput = document.getElementById('nextExecutionUTC');
                if (nextExecInput) {
                    nextExecInput.value = data.next_execution_utc || '';
                }

                // Update countdown display immediately with API data
                 updateCountdownText(data.time_until_next_str);

                // Restart countdown timer based on potentially updated next execution time
                startOrUpdateCountdown();
            }
        })
        .catch(error => {
            console.error("Error fetching or processing API status:", error);
            // Optionally update UI to show an error state
            updateElementText('schedulerStatus', 'Error fetching status.');
            updateElementText('countdownText', 'Error');
        });
}

/**
 * Starts or updates the countdown timer based on the hidden input field.
 */
function startOrUpdateCountdown() {
    if (countdownIntervalId) clearInterval(countdownIntervalId); // Clear existing timer

    const nextExecInput = document.getElementById('nextExecutionUTC');
    const countdownTextElement = document.getElementById('countdownText');

    if (!nextExecInput || !nextExecInput.value || !countdownTextElement) {
        console.debug("Countdown elements not found or no next execution time set. Stopping countdown.");
        updateElementText('countdownText', 'N/A');
        return;
    }

    const nextExecutionUTCString = nextExecInput.value;
    try {
        const nextExecutionDate = new Date(nextExecutionUTCString);
        // Validate date parsing
        if (isNaN(nextExecutionDate.getTime())) {
             throw new Error("Invalid date format received from server.");
        }

        console.debug(`Starting countdown to: ${nextExecutionDate.toISOString()}`);

        const updateTimer = () => {
            const now = new Date();
            const diffMs = nextExecutionDate - now;

            if (diffMs <= 0) {
                countdownTextElement.textContent = "Due now / Running...";
                clearInterval(countdownIntervalId); // Stop timer when time is reached
                // Optionally trigger an immediate status refresh after a short delay
                setTimeout(fetchAndUpdateStatus, 5000); // Refresh status after 5s
                return;
            }

            // Calculate remaining time
            const totalSeconds = Math.floor(diffMs / 1000);
            const days = Math.floor(totalSeconds / (3600 * 24));
            const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = Math.floor(totalSeconds % 60);

            // Format the output string
            let timeString = '';
            if (days > 0) timeString += `${days}d `;
            if (hours > 0 || days > 0) timeString += `${hours}h `; // Show hours if days>0 or hours>0
            if (minutes > 0 || hours > 0 || days > 0) timeString += `${minutes}m `;
            timeString += `${seconds}s`;

            countdownTextElement.textContent = timeString.trim();
        };

        updateTimer(); // Run immediately
        countdownIntervalId = setInterval(updateTimer, 1000); // Update every second

    } catch (error) {
        console.error("Error parsing next execution date or starting countdown:", error, `Input string: ${nextExecutionUTCString}`);
        countdownTextElement.textContent = "Error";
    }
}

/**
 * Updates the text content of a DOM element by its ID.
 * @param {string} elementId The ID of the element.
 * @param {string} text The text to set.
 */
function updateElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text || ''; // Use empty string if text is null/undefined
    } else {
         console.warn(`Element with ID '${elementId}' not found for updating text.`);
    }
}

/**
 * Updates the countdown text specifically. Handles the case where API provides pre-formatted string.
 */
function updateCountdownText(apiTimeString) {
     const countdownTextElement = document.getElementById('countdownText');
     if (countdownTextElement) {
        countdownTextElement.textContent = apiTimeString || 'Calculating...';
     }
}


/**
 * Formats an ISO date string into a user-friendly local time string.
 * @param {string | null} isoDateString The ISO 8601 date string (UTC).
 * @param {string} fallbackText Text to return if date is invalid or null.
 * @returns {string} Formatted date string or fallback text.
 */
function formatISODate(isoDateString, fallbackText = 'N/A') {
    if (!isoDateString) {
        return fallbackText;
    }
    try {
        const date = new Date(isoDateString);
        if (isNaN(date.getTime())) {
             return fallbackText; // Invalid date
        }
        // Format to local time using Intl.DateTimeFormat for better localization
        const options = {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: 'numeric', minute: '2-digit', /* second: '2-digit', */
            timeZoneName: 'short'
        };
        return new Intl.DateTimeFormat(navigator.language || 'en-US', options).format(date);
    } catch (e) {
        console.error("Error formatting date:", isoDateString, e);
        return fallbackText;
    }
}

// Make togglePasswordVisibility globally accessible if called via onclick attribute
window.togglePasswordVisibility = function(inputId, buttonElement) {
     const input = document.getElementById(inputId);
     const icon = buttonElement.querySelector('i');
     if (input && icon) {
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
 };