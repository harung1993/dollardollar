/**
 * UI Helpers - Shared UI utilities for Dollar Dollar Bill Y'all
 * 
 * This module provides common UI functions used across different modules
 * to ensure consistent behavior and avoid code duplication.
 */
const UIHelpers = (function() {
    /**
     * Open a slide panel with content
     * @param {string} panelId - ID for the panel
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} - The panel element
     */
    function openPanel(panelId, options = {}) {
        // Default options
        const defaults = {
            title: 'Panel',
            icon: 'fa-info-circle',
            iconColor: '#15803d'
        };
        
        // Merge with provided options
        const settings = { ...defaults, ...options };
        
        // Check if panel already exists and remove it
        let existingPanel = document.getElementById(panelId);
        if (existingPanel) {
            existingPanel.remove();
        }
        
        // Create new panel
        const panel = document.createElement('div');
        panel.id = panelId;
        panel.className = 'slide-panel';
        
        panel.innerHTML = `
            <div class="slide-panel-header">
                <h4 class="mb-0">
                    <i class="fas ${settings.icon} me-2" style="color: ${settings.iconColor}"></i>
                    ${settings.title}
                </h4>
                <button type="button" class="btn-close btn-close-white" aria-label="Close"></button>
            </div>
            <div class="slide-panel-content">
                <div class="d-flex justify-content-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `;
        
        // Add to DOM
        document.body.appendChild(panel);
        
        // Setup close button
        const closeBtn = panel.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => closePanel(panelId));
        }
        
        // Create or get overlay
        let overlay = document.getElementById('slide-panel-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'slide-panel-overlay';
            overlay.className = 'slide-panel-overlay';
            overlay.addEventListener('click', () => closePanel(panelId));
            document.body.appendChild(overlay);
        }
        
        // Show with animation
        setTimeout(() => {
            overlay.classList.add('active');
            panel.classList.add('active');
            
            // Disable scrolling on main content
            document.body.style.overflow = 'hidden';
        }, 10);
        
        return panel;
    }
    
    /**
     * Close a slide panel
     * @param {string} panelId - ID of the panel to close
     */
    function closePanel(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;
        
        // Hide with animation
        panel.classList.remove('active');
        
        // Hide overlay if no other active panels
        const activeCount = document.querySelectorAll('.slide-panel.active').length;
        if (activeCount <= 1) {
            const overlay = document.getElementById('slide-panel-overlay');
            if (overlay) {
                overlay.classList.remove('active');
            }
            
            // Re-enable scrolling
            document.body.style.overflow = '';
        }
        
        // Remove after animation completes
        setTimeout(() => {
            if (panel.parentNode) {
                panel.remove();
            }
        }, 300);
    }
    
    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Message type (success, error, warning, info)
     * @param {Object} options - Additional options
     */
    function showToast(message, type = 'success', options = {}) {
        // Check if Bootstrap is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            // Default options
            const defaults = {
                delay: 5000,
                autoHide: true,
                actionButtons: []
            };
            
            // Merge with provided options
            const settings = { ...defaults, ...options };
            
            // Create toast container if needed
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            // Create toast with unique ID
            const toastId = `toast-${Date.now()}`;
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = 'toast';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            // Determine header color and icon
            let headerClass, iconClass;
            switch (type) {
                case 'error':
                case 'danger':
                    headerClass = 'bg-danger';
                    iconClass = 'fa-exclamation-circle';
                    break;
                case 'warning':
                    headerClass = 'bg-warning';
                    iconClass = 'fa-exclamation-triangle';
                    break;
                case 'info':
                    headerClass = 'bg-info';
                    iconClass = 'fa-info-circle';
                    break;
                case 'success':
                default:
                    headerClass = 'bg-success';
                    iconClass = 'fa-check-circle';
                    break;
            }
            
            // Build toast HTML
            let toastHTML = `
                <div class="toast-header ${headerClass} text-white">
                    <i class="fas ${iconClass} me-2"></i>
                    <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                    ${settings.actionButtons.length > 0 ? '<div class="mt-2 pt-2 border-top d-flex justify-content-end action-buttons"></div>' : ''}
                </div>
            `;
            
            // Set toast content
            toast.innerHTML = toastHTML;
            
            // Add action buttons if any
            if (settings.actionButtons.length > 0) {
                const buttonContainer = toast.querySelector('.action-buttons');
                
                settings.actionButtons.forEach(button => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = `btn btn-sm ${button.class || 'btn-secondary'} me-2`;
                    btn.textContent = button.text || 'Action';
                    
                    if (typeof button.onClick === 'function') {
                        btn.addEventListener('click', () => button.onClick(toast));
                    }
                    
                    buttonContainer.appendChild(btn);
                });
            }
            
            // Add to container
            toastContainer.appendChild(toast);
            
            // Create Bootstrap toast
            const bsToast = new bootstrap.Toast(toast, { 
                delay: settings.delay,
                autohide: settings.autoHide
            });
            
            // Show toast
            bsToast.show();
            
            // Store Bootstrap toast instance on DOM element for later reference
            toast._bsToast = bsToast;
            
            // Optional callback after toast is shown
            if (typeof settings.onShown === 'function') {
                toast.addEventListener('shown.bs.toast', () => settings.onShown(toast));
            }
            
            // Remove from DOM after hiding
            toast.addEventListener('hidden.bs.toast', function() {
                if (typeof settings.onClose === 'function') {
                    settings.onClose(toast);
                }
                
                if (toast.parentNode) {
                    toast.remove();
                }
            });
            
            // Return toast element for further manipulation
            return toast;
        } else {
            // Fallback to alert if Bootstrap not available
            alert(`${type.toUpperCase()}: ${message}`);
            return null;
        }
    }
    
    /**
     * Format currency value
     * @param {number} amount - The amount to format
     * @param {string} currencySymbol - Currency symbol to use
     * @param {number} decimals - Number of decimal places
     * @returns {string} - Formatted currency string
     */
    function formatCurrency(amount, currencySymbol = '$', decimals = 2) {
        if (typeof amount !== 'number') {
            amount = parseFloat(amount) || 0;
        }
        
        return `${currencySymbol}${amount.toFixed(decimals)}`;
    }
    
    /**
     * Dynamic form validation
     * @param {HTMLFormElement} form - The form to validate
     * @returns {boolean} - Whether the form is valid
     */
    function validateForm(form) {
        if (!form) return false;
        
        // Check if browser supports HTML5 validation
        if (typeof form.checkValidity === 'function') {
            const valid = form.checkValidity();
            
            // Add .was-validated class to show validation feedback
            if (!valid) {
                form.classList.add('was-validated');
                
                // Find first invalid field and focus it
                const invalidField = form.querySelector(':invalid');
                if (invalidField) {
                    invalidField.focus();
                }
            }
            
            return valid;
        }
        
        // Fallback validation
        let valid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                valid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        return valid;
    }
    
    // Return public API
    return {
        openPanel,
        closePanel,
        showToast,
        formatCurrency,
        validateForm
    };
})();

// Make available globally
window.UIHelpers = UIHelpers;