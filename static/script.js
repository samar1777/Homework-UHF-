window.onload = function() {
    // Check if popup has been shown before
    if (!localStorage.getItem('disclaimerShown')) {
        document.getElementById('disclaimer-popup').style.display = 'flex';
    }

    // Check for update notifications
    checkForUpdates();

    // Check for request count if on admin page (polling)
    if (document.getElementById('pending-requests-badge')) {
        setInterval(checkPendingRequests, 30000); // Check every 30 seconds
        checkPendingRequests(); // Check immediately
    }
};

function closePopup() {
    document.getElementById('disclaimer-popup').style.display = 'none';
    if (document.getElementById('dont-show-again').checked) {
        localStorage.setItem('disclaimerShown', 'true');
    }
}

function closeUpdatePopup() {
    const updatePopup = document.getElementById('update-popup');
    if (updatePopup) {
        // Add exit animation
        updatePopup.classList.add('fade-out-down');
        
        // Remove after animation completes
        setTimeout(() => {
            updatePopup.style.display = 'none';
        }, 500);
        
        // Mark this update as seen
        const updateId = updatePopup.getAttribute('data-update-id');
        if (updateId) {
            localStorage.setItem('lastSeenUpdateId', updateId);
        }
    }
}

function checkForUpdates() {
    const updatePopup = document.getElementById('update-popup');
    if (updatePopup) {
        const updateId = updatePopup.getAttribute('data-update-id');
        const lastSeenUpdateId = localStorage.getItem('lastSeenUpdateId');
        
        // Only show if this update hasn't been seen AND there's no other notification visible
        if (updateId && updateId !== lastSeenUpdateId && !document.querySelector('.notification:not(.fade-out)')) {
            // Add entrance animation class
            updatePopup.classList.add('fade-in-up');
            updatePopup.style.display = 'flex';
        }
    }
}

function showRequestForm() {
    const requestFormContainer = document.getElementById('request-form-container');
    requestFormContainer.style.display = 'flex';
    
    // Disable body scrolling when form is open
    document.body.style.overflow = 'hidden';
    
    // On mobile, scroll to top to ensure form is in view
    if (window.innerWidth <= 768) {
        window.scrollTo(0, 0);
    }
}

function closeRequestForm() {
    document.getElementById('request-form-container').style.display = 'none';
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

function submitRequest() {
    const form = document.getElementById('request-form');
    const formData = new FormData(form);
    
    fetch('/submit_request', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            document.getElementById('request-form-container').style.display = 'none';
            
            // Hide any existing notifications first
            hideAllNotifications();
            
            // Re-enable body scrolling
            document.body.style.overflow = '';
            
            // Show success notification
            const notification = document.createElement('div');
            notification.className = 'notification success';
            notification.innerHTML = `
                <div class="notification-content">
                    <p>Your request has been submitted successfully!</p>
                </div>
            `;
            document.body.appendChild(notification);
            
            // Clear form
            form.reset();
            
            // Remove notification after 3 seconds
            setTimeout(() => {
                notification.classList.add('fade-out');
                setTimeout(() => {
                    if (document.body.contains(notification)) {
                        document.body.removeChild(notification);
                    }
                }, 500);
            }, 3000);
        } else {
            // Show error message
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    });
    
    return false; // Prevent form submission
}

function checkPendingRequests() {
    fetch('/get_pending_requests')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('pending-requests-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'flex';
                    
                    // If count increased since last check and not first load, show notification
                    const lastCount = parseInt(badge.getAttribute('data-last-count') || '0');
                    if (lastCount < data.count && lastCount > 0) {
                        showAdminNotification('New Request', 'You have a new request waiting');
                    }
                    
                    badge.setAttribute('data-last-count', data.count);
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error checking requests:', error));
}

function showAdminNotification(title, message) {
    // Create an in-app notification instead of browser notification
    const notification = document.createElement('div');
    notification.className = 'notification admin-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <strong>${title}:</strong> ${message}
        </div>
    `;
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const cards = document.querySelectorAll('.subject-card, .chapter-card');

    // Fix card colors on load
    fixCardColors();

    if (searchInput && cards) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();

            cards.forEach(card => {
                const text = card.querySelector('h2').textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
    
    // Call our function to enforce green cards
    enforceGreenCards();
    
    // Add MutationObserver to handle dynamically added content
    const observer = new MutationObserver(function(mutations) {
        enforceGreenCards();
    });
    
    // Start observing the document for added nodes
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Check for server notifications periodically
    setInterval(checkForServerNotifications, 60000); // Check every minute
    // Also check immediately
    checkForServerNotifications();
});

// Function to fix card colors
function fixCardColors() {
    // Force all cards to have the primary color
    document.querySelectorAll('.subject-card, .chapter-card').forEach(card => {
        card.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color');
        card.style.color = 'white';
        
        // Make sure the heading is white
        const heading = card.querySelector('h2');
        if (heading) {
            heading.style.color = 'white';
        }
    });
    
    // Fix search input appearance
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // Check if in dark mode
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            searchInput.style.backgroundColor = '#2d2d2d';
            searchInput.style.color = 'white';
        } else {
            searchInput.style.backgroundColor = 'white';
            searchInput.style.color = '#333';
        }
    }
}

// Enhanced function to specifically ensure green cards
function enforceGreenCards() {
    // Force all cards to have the primary color (green)
    document.querySelectorAll('.subject-card, .chapter-card').forEach(card => {
        // Get the primary color value from CSS variables
        const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim();
        
        // Apply !important inline styles to force green background
        card.style.setProperty('background-color', primaryColor, 'important');
        card.style.setProperty('color', 'white', 'important');
        
        // Make sure the heading is white
        const heading = card.querySelector('h2');
        if (heading) {
            heading.style.setProperty('color', 'white', 'important');
        }
    });
}

// Periodically check for new notifications to broadcast
function checkForServerNotifications() {
    fetch('/check_notifications')
        .then(response => response.json())
        .then(data => {
            if (data.id && data.title && data.content) {
                // Display an in-app notification instead of browser notification
                displaySiteNotification(data.title, data.content);
            }
        })
        .catch(error => console.error('Error checking for notifications:', error));
}

// Function to display site notifications
function displaySiteNotification(title, content) {
    const notification = document.createElement('div');
    notification.className = 'notification site-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <strong>${title}</strong>
            <p>${content}</p>
        </div>
        <button class="notification-close">×</button>
    `;
    document.body.appendChild(notification);
    
    // Add close functionality
    const closeButton = notification.querySelector('.notification-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 500);
        });
    }
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 10000);
}

// Listen for dark mode changes
if (window.matchMedia) {
    const darkModeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    darkModeMediaQuery.addEventListener('change', fixCardColors);
}

// Call the fix function on window resize too
window.addEventListener('resize', fixCardColors);

// Call after any page interactions
document.addEventListener('click', function() {
    setTimeout(fixCardColors, 100);
});

// Run regularly to catch any styling changes
setInterval(enforceGreenCards, 1000);

// Add a new function to handle potentially multiple notifications
function hideAllNotifications() {
    const notifications = document.querySelectorAll('.notification, #update-popup');
    notifications.forEach(notification => {
        if (notification.style.display !== 'none') {
            notification.classList.add('fade-out-down');
            setTimeout(() => {
                notification.style.display = 'none';
            }, 500);
        }
    });
}
