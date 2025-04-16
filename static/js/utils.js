/**
 * Utility functions for the application
 */

/**
 * Opens a slide panel
 * @param {string} panelId - The ID for the panel
 * @param {object} options - Panel options (title, icon, iconColor, content, loadingContent)
 * @returns {HTMLElement} The panel element
 */
function openSlidePanel(panelId, options = {}) {
    // Check if panel already exists
    let panel = document.getElementById(panelId);
    
    
    // Create panel if it doesn't exist
    if (!panel) {
        panel = document.createElement('div');
        panel.id = panelId;
        panel.className = 'slide-panel';
        
        // Create panel header
        const header = document.createElement('div');
        header.className = 'slide-panel-header';
        header.innerHTML = `
            <h4 class="mb-0">
                <i class="fas ${options.icon || 'fa-info-circle'} me-2" style="color: ${options.iconColor || '#15803d'}"></i>
                ${options.title || 'Panel'}
            </h4>
            <button type="button" class="btn-close btn-close-white" onclick="closeSlidePanel('${panelId}')"></button>
        `;
        
        // Create panel content
        const content = document.createElement('div');
        content.className = 'slide-panel-content';
        
        // Add loading content if provided
        if (options.loadingContent) {
            content.innerHTML = options.loadingContent;
        } else if (options.content) {
            content.innerHTML = options.content;
        }
        
        // Assemble panel
        panel.appendChild(header);
        panel.appendChild(content);
        
        // Add to DOM
        document.body.appendChild(panel);
    }
    
    // Show overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.classList.add('active');
        overlay.onclick = function() {
            closeSlidePanel(panelId);
        };
    }
    
    // Show panel with animation
    setTimeout(() => {
        panel.classList.add('active');
    }, 10);
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    return panel;
}

/**
 * Closes a slide panel
 * @param {string} panelId - The ID of the panel to close
 */
function closeSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.classList.remove('active');
    }
    
    // Hide overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

/**
 * Function to initialize a select without requiring Ctrl+click for multiple selection
 * @param {string} selectId - The ID of the select element
 */
function initializeSelectWithoutCtrl(selectId) {
    const select = document.getElementById(selectId);
    if (!select || !select.multiple) return;
    
    // Replace the standard multiple select with a custom one
    const wrapper = document.createElement('div');
    wrapper.className = 'custom-multiselect-wrapper';
    wrapper.style.maxHeight = '200px';
    wrapper.style.overflowY = 'auto';
    wrapper.style.border = '1px solid #444';
    wrapper.style.borderRadius = '0.25rem';
    wrapper.style.backgroundColor = '#2d2d2d';
    
    // Hide the original select
    select.style.display = 'none';
    select.parentNode.insertBefore(wrapper, select.nextSibling);
    
    // Create checkbox options for each option in the select
    Array.from(select.options).forEach(option => {
        if (option.disabled) return;
        
        const item = document.createElement('div');
        item.className = 'custom-multiselect-item';
        item.style.padding = '0.5rem 1rem';
        item.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
        item.style.cursor = 'pointer';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.checked = option.selected;
        checkbox.value = option.value;
        
        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.style.cursor = 'pointer';
        label.style.userSelect = 'none';
        label.style.marginLeft = '8px';
        label.textContent = option.textContent;
        
        item.appendChild(checkbox);
        item.appendChild(label);
        wrapper.appendChild(item);
        
        // Add event listener to update the original select when checkbox is clicked
        checkbox.addEventListener('change', function() {
            option.selected = checkbox.checked;
            // Trigger change event on original select
            const event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        });
        
        // Also make the whole item clickable
        item.addEventListener('click', function(e) {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
                option.selected = checkbox.checked;
                // Trigger change event on original select
                const event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
            }
        });
    });
}

/**
 * Show a message toast
 * @param {string} message - The message to display
 * @param {string} type - Message type (success, error, warning, info)
 * @param {object} options - Additional options (autoHide, delay, actionButtons, onClose)
 * @returns {object|null} - The toast instance if created
 */
function showMessage(message, type = 'success', options = {}) {
    // Default options
    const defaultOptions = {
        autoHide: true,
        delay: 5000,
        actionButtons: [],
        onClose: null
    };
    
    // Merge options
    const finalOptions = {...defaultOptions, ...options};
    
    // Check if we can use Bootstrap toast
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toastId = `toast-${Date.now()}`;
        const iconClass = type === 'error' ? 'fa-exclamation-circle' : 
                          type === 'warning' ? 'fa-exclamation-triangle' : 
                          type === 'info' ? 'fa-info-circle' : 'fa-check-circle';
        const bgColor = type === 'error' ? 'bg-danger' : 
                        type === 'warning' ? 'bg-warning text-dark' : 
                        type === 'info' ? 'bg-info text-dark' : 'bg-success';
        
        // Create action buttons HTML if provided
        let actionButtonsHtml = '';
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
            actionButtonsHtml = `
                <div class="mt-2 pt-2 border-top d-flex justify-content-end">
                    ${finalOptions.actionButtons.map(btn => 
                        `<button type="button" class="btn ${btn.class || 'btn-secondary'} btn-sm me-2 action-btn" 
                            data-action="${btn.text}">${btn.text}</button>`
                    ).join('')}
                </div>
            `;
        }
        
        // Create toast HTML
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" 
                ${finalOptions.autoHide ? `data-bs-delay="${finalOptions.delay}"` : 'data-bs-autohide="false"'}>
                <div class="toast-header ${bgColor} ${type !== 'warning' && type !== 'info' ? 'text-white' : ''}">
                    <i class="fas ${iconClass} me-2"></i>
                    <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <button type="button" class="btn-close ${type !== 'warning' && type !== 'info' ? 'btn-close-white' : ''}" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                    ${actionButtonsHtml}
                </div>
            </div>
        `;
        
        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Get toast element
        const toastEl = document.getElementById(toastId);
        
        // Add action button event listeners
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
            const actionBtns = toastEl.querySelectorAll('.action-btn');
            actionBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const actionText = this.getAttribute('data-action');
                    const actionBtn = finalOptions.actionButtons.find(b => b.text === actionText);
                    
                    if (actionBtn && typeof actionBtn.onClick === 'function') {
                        // Create toast instance reference to pass to handlers
                        const bsToast = bootstrap.Toast.getInstance(toastEl);
                        actionBtn.onClick(bsToast);
                    }
                });
            });
        }
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Handle close event
        toastEl.addEventListener('hidden.bs.toast', function() {
            if (typeof finalOptions.onClose === 'function') {
                finalOptions.onClose();
            }
            // Remove toast from DOM
            toastEl.remove();
        });
        
        return toast;
    } else {
        // Fallback to alert
        alert(message);
        
        // Call onClose if provided
        if (typeof finalOptions.onClose === 'function') {
            finalOptions.onClose();
        }
        
        return null;
    }
}

/**
 * Opens the Add Transaction panel
 * Function moved from add_transaction.js to ensure global availability
 */
function openAddTransactionPanel() {
    console.log("Opening Add Transaction Panel from utils.js");
    
    // Create the slide panel first
    const panel = openSlidePanel('addTransactionPanel', {
        title: 'Add New Transaction',
        icon: 'fa-plus',
        iconColor: '#0ea5e9',
        loadingContent: '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>'
    });
    
    // Then fetch the form contents
    fetch('/get_transaction_form_html')
        .then(response => response.text())
        .then(html => {
            const contentDiv = panel.querySelector('.slide-panel-content');
            if (contentDiv) {
                contentDiv.innerHTML = html;
                
                // Initialize date with today's date
                const dateInput = document.getElementById('date');
                if (dateInput) {
                    dateInput.value = new Date().toISOString().split('T')[0];
                }
                
                // INLINE IMPLEMENTATION OF CRITICAL FUNCTIONS
                // Add multi-select styles
                const addStyles = function() {
                    if (document.getElementById('enhanced-multi-select-styles')) return;
                    
                    const styleEl = document.createElement('style');
                    styleEl.id = 'enhanced-multi-select-styles';
                    styleEl.textContent = `
                        .custom-multi-select-container {
                            position: relative;
                        }
                        
                        .custom-multi-select-display {
                            cursor: pointer;
                            min-height: 38px;
                            white-space: normal;
                            display: flex;
                            flex-wrap: wrap;
                            align-items: center;
                            gap: 4px;
                            padding: 6px 10px;
                        }
                        
                        .custom-multi-select-display .placeholder {
                            color: #6c757d;
                        }
                        
                        .custom-multi-select-dropdown {
                            position: absolute;
                            width: 100%;
                            max-height: 250px;
                            overflow-y: auto;
                            z-index: 1050;
                            border: 1px solid #444;
                            border-radius: 0.25rem;
                            padding: 8px;
                            margin-top: 2px;
                            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
                        }
                        
                        .custom-multi-select-option {
                            display: flex;
                            align-items: center;
                            padding: 6px 10px;
                            cursor: pointer;
                            color: #fff;
                            border-radius: 0.25rem;
                            transition: background-color 0.15s ease;
                        }
                        
                        .custom-multi-select-option:hover {
                            background-color: #2d3748;
                        }
                        
                        .enhanced-multi-select {
                            display: none;
                        }
                    `;
                    document.head.appendChild(styleEl);
                    console.log("Multi-select styles added inline");
                };
                
                // Initialize enhanced multi-select
                const initializeMultiSelect = function(selector) {
                    const multiSelects = document.querySelectorAll(selector);
                    console.log(`Found ${multiSelects.length} multi-select elements with selector: ${selector}`);
                    
                    multiSelects.forEach(select => {
                        // Skip if already initialized
                        if (select.getAttribute('data-enhanced') === 'true') return;
                        
                        // Mark as enhanced to prevent duplicate initialization
                        select.setAttribute('data-enhanced', 'true');
                        
                        // Create wrapper container
                        const container = document.createElement('div');
                        container.className = 'custom-multi-select-container';
                        select.parentNode.insertBefore(container, select);
                        container.appendChild(select);
                        
                        // Create display element
                        const displayBox = document.createElement('div');
                        displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
                        displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
                        container.insertBefore(displayBox, select);
                        
                        // Create dropdown menu container
                        const dropdownMenu = document.createElement('div');
                        dropdownMenu.className = 'custom-multi-select-dropdown bg-dark';
                        dropdownMenu.style.display = 'none';
                        container.appendChild(dropdownMenu);
                        
                        // Add search input
                        const searchInput = document.createElement('input');
                        searchInput.type = 'text';
                        searchInput.className = 'form-control form-control-sm bg-dark text-light mb-2 custom-multi-select-search';
                        searchInput.placeholder = 'Search...';
                        dropdownMenu.appendChild(searchInput);
                        
                        // Create option list
                        const optionList = document.createElement('div');
                        optionList.className = 'custom-multi-select-options';
                        dropdownMenu.appendChild(optionList);
                        
                        // Populate options
                        Array.from(select.options).forEach(option => {
                            const optionItem = document.createElement('div');
                            optionItem.className = 'custom-multi-select-option';
                            optionItem.setAttribute('data-value', option.value);
                            
                            const checkbox = document.createElement('input');
                            checkbox.type = 'checkbox';
                            checkbox.className = 'form-check-input me-2';
                            checkbox.checked = option.selected;
                            
                            const label = document.createElement('label');
                            label.className = 'form-check-label';
                            label.textContent = option.textContent;
                            
                            optionItem.appendChild(checkbox);
                            optionItem.appendChild(label);
                            optionList.appendChild(optionItem);
                            
                            // Handle option click
                            optionItem.addEventListener('click', (e) => {
                                e.stopPropagation();
                                checkbox.checked = !checkbox.checked;
                                
                                // Update the original select element
                                option.selected = checkbox.checked;
                                
                                // Dispatch change event on the original select
                                const event = new Event('change', { bubbles: true });
                                select.dispatchEvent(event);
                                
                                // Update display box
                                updateDisplayBox();
                            });
                        });
                        
                        // Function to update display box
                        function updateDisplayBox() {
                            const selectedOptions = Array.from(select.selectedOptions);
                            
                            if (selectedOptions.length === 0) {
                                displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
                            } else {
                                displayBox.innerHTML = selectedOptions
                                    .map(opt => `<span class="badge bg-primary me-1">${opt.textContent}</span>`)
                                    .join(' ');
                            }
                        }
                        
                        // Initial update of display box
                        updateDisplayBox();
                        
                        // Toggle dropdown on display box click
                        displayBox.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const isVisible = dropdownMenu.style.display === 'block';
                            dropdownMenu.style.display = isVisible ? 'none' : 'block';
                            
                            if (!isVisible) {
                                searchInput.focus();
                                
                                // Position dropdown
                                const rect = displayBox.getBoundingClientRect();
                                dropdownMenu.style.width = rect.width + 'px';
                                
                                // Adjust top position if near bottom of screen
                                const spaceBelow = window.innerHeight - rect.bottom;
                                if (spaceBelow < 300) {
                                    dropdownMenu.style.top = 'auto';
                                    dropdownMenu.style.bottom = rect.height + 'px';
                                } else {
                                    dropdownMenu.style.top = rect.height + 'px';
                                    dropdownMenu.style.bottom = 'auto';
                                }
                            }
                        });
                        
                        // Handle search
                        searchInput.addEventListener('input', (e) => {
                            const searchText = e.target.value.toLowerCase();
                            
                            Array.from(optionList.children).forEach(optionItem => {
                                const optionText = optionItem.querySelector('label').textContent.toLowerCase();
                                optionItem.style.display = optionText.includes(searchText) ? 'block' : 'none';
                            });
                        });
                        
                        // Close dropdown when clicking outside
                        document.addEventListener('click', (e) => {
                            if (!container.contains(e.target)) {
                                dropdownMenu.style.display = 'none';
                            }
                        });
                        
                        // Sync original select with our custom one when it changes externally
                        select.addEventListener('change', () => {
                            Array.from(optionList.children).forEach(optionItem => {
                                const value = optionItem.getAttribute('data-value');
                                const option = select.querySelector(`option[value="${value}"]`);
                                const checkbox = optionItem.querySelector('input[type="checkbox"]');
                                
                                if (option && checkbox) {
                                    checkbox.checked = option.selected;
                                }
                            });
                            
                            updateDisplayBox();
                        });
                        
                        console.log(`Enhanced multi-select initialized for element with ID: ${select.id}`);
                    });
                };
                
                // Function to auto-select the paid by user
                const autoSelectPaidBy = function() {
                    const paidBySelect = document.getElementById('paid_by');
                    const splitWithSelect = document.getElementById('split_with');
                    
                    if (!paidBySelect || !splitWithSelect) {
                        console.log("Could not find paid_by or split_with elements");
                        return;
                    }
                    
                    const paidById = paidBySelect.value;
                    if (!paidById) return;
                    
                    console.log(`Auto-selecting paid by user: ${paidById}`);
                    
                    // If there are no existing selections yet
                    if (Array.from(splitWithSelect.selectedOptions).length === 0) {
                        // Find the option for the paid by user and select it
                        const option = splitWithSelect.querySelector(`option[value="${paidById}"]`);
                        if (option) {
                            option.selected = true;
                            // Trigger change event to update the UI
                            splitWithSelect.dispatchEvent(new Event('change'));
                            console.log("Paid by user auto-selected successfully");
                        }
                    }
                };
                
                // Function to handle split options toggle
                const toggleSplitOptions = function() {
                    const splitMethodSelect = document.getElementById('split_method');
                    if (!splitMethodSelect) return;
                    
                    const splitMethod = splitMethodSelect.value;
                    const customSplitContainer = document.getElementById('custom_split_container');
                    const personalExpenseCheck = document.getElementById('personal_expense');
                    
                    if (!customSplitContainer) return;
                    
                    // Don't show custom split container for personal expenses
                    if (personalExpenseCheck && personalExpenseCheck.checked) {
                        customSplitContainer.style.display = 'none';
                        return;
                    }
                    
                    if (splitMethod === 'equal') {
                        customSplitContainer.style.display = 'none';
                    } else {
                        customSplitContainer.style.display = 'block';
                        
                        // Update the split values UI
                        updateSplitValues();
                    }
                };
                
                // Function to update split values UI
                const updateSplitValues = function() {
                    // Get currency symbol
                    let baseCurrencySymbol = window.baseCurrencySymbol || '$';
                    
                    const splitMethodSelect = document.getElementById('split_method');
                    if (!splitMethodSelect) return;
                    
                    const splitMethod = splitMethodSelect.value;
                    if (splitMethod === 'equal') return;
                    
                    // Skip if personal expense is checked
                    const personalExpenseCheck = document.getElementById('personal_expense');
                    if (personalExpenseCheck && personalExpenseCheck.checked) return;
                    
                    const amountInput = document.getElementById('amount');
                    const paidBySelect = document.getElementById('paid_by');
                    const splitWithSelect = document.getElementById('split_with');
                    const splitTotalEl = document.getElementById('split_total');
                    const splitValuesContainer = document.getElementById('split_values_container');
                    const splitDetailsInput = document.getElementById('split_details');
                    
                    if (!amountInput || !paidBySelect || !splitWithSelect || !splitTotalEl || !splitValuesContainer) return;
                    
                    const totalAmount = parseFloat(amountInput.value) || 0;
                    const paidById = paidBySelect.value;
                    
                    // Get selected users to split with
                    const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
                    
                    // If no participants, show a message
                    if (splitWithIds.length === 0) {
                        splitValuesContainer.innerHTML = '<p class="text-center text-warning">Please select people to split with</p>';
                        return;
                    }
                    
                    // Get all participant IDs (include payer only if they aren't already in the split list)
                    const allParticipantIds = [...splitWithIds];
                    if (!allParticipantIds.includes(paidById)) {
                        allParticipantIds.unshift(paidById);
                    }
                    
                    splitValuesContainer.innerHTML = '';
                    let splitValues = {};
                    
                    if (splitMethod === 'percentage') {
                        // Equal percentage for all participants
                        const equalPercentage = allParticipantIds.length ? (100 / allParticipantIds.length) : 0;
                        
                        allParticipantIds.forEach(userId => {
                            const userName = Array.from(paidBySelect.options)
                                .find(opt => opt.value === userId)?.text || userId;
                            
                            const isPayerId = userId === paidById;
                            
                            // Create row for this user
                            const row = document.createElement('div');
                            row.className = 'row mb-2 align-items-center';
                            row.innerHTML = `
                                <div class="col-md-6">
                                    <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                                        ${isPayerId ? '💰' : ''} ${userName}
                                    </span>
                                    ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
                                </div>
                                <div class="col-md-6">
                                    <div class="input-group">
                                        <input type="number" class="form-control bg-dark text-light split-value-input"
                                            data-user-id="${userId}" step="0.1" min="0" max="100" 
                                            value="${equalPercentage.toFixed(1)}">
                                        <span class="input-group-text bg-dark text-light">%</span>
                                    </div>
                                </div>
                            `;
                            splitValuesContainer.appendChild(row);
                            
                            // Save the initial value
                            splitValues[userId] = equalPercentage;
                        });
                    } else { // Custom amount
                        // Equal amounts
                        const equalAmount = allParticipantIds.length ? (totalAmount / allParticipantIds.length) : 0;
                        
                        allParticipantIds.forEach(userId => {
                            const userName = Array.from(paidBySelect.options)
                                .find(opt => opt.value === userId)?.text || userId;
                            
                            const isPayerId = userId === paidById;
                            
                            // Create row for this user
                            const row = document.createElement('div');
                            row.className = 'row mb-2 align-items-center';
                            row.innerHTML = `
                                <div class="col-md-6">
                                    <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                                        ${isPayerId ? '💰' : ''} ${userName}
                                    </span>
                                    ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
                                </div>
                                <div class="col-md-6">
                                    <div class="input-group">
                                        <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                                        <input type="number" class="form-control bg-dark text-light split-value-input"
                                            data-user-id="${userId}" step="0.01" min="0" 
                                            value="${equalAmount.toFixed(2)}">
                                    </div>
                                </div>
                            `;
                            splitValuesContainer.appendChild(row);
                            
                            // Save the initial value
                            splitValues[userId] = equalAmount;
                        });
                    }
                    
                    // Add event listeners to inputs and update split details
                    setupSplitInputListeners(splitMethod, splitValues, totalAmount);
                };
                
                // Setup input listeners for split values
                const setupSplitInputListeners = function(splitMethod, splitValues, totalAmount) {
                    const splitDetailsInput = document.getElementById('split_details');
                    const splitTotalEl = document.getElementById('split_total');
                    const splitStatusEl = document.getElementById('split_status');
                    
                    document.querySelectorAll('.split-value-input').forEach(input => {
                        input.addEventListener('input', function() {
                            const userId = this.getAttribute('data-user-id');
                            const value = parseFloat(this.value) || 0;
                            splitValues[userId] = value;
                            
                            // Calculate total
                            const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
                            
                            // Update UI
                            if (splitTotalEl) {
                                if (splitMethod === 'percentage') {
                                    splitTotalEl.textContent = total.toFixed(1) + '%';
                                    
                                    // Update status
                                    if (splitStatusEl) {
                                        if (Math.abs(total - 100) < 0.1) {
                                            splitStatusEl.textContent = 'Balanced';
                                            splitStatusEl.className = 'badge bg-success';
                                        } else if (total < 100) {
                                            splitStatusEl.textContent = 'Underfunded';
                                            splitStatusEl.className = 'badge bg-warning';
                                        } else {
                                            splitStatusEl.textContent = 'Overfunded';
                                            splitStatusEl.className = 'badge bg-danger';
                                        }
                                    }
                                } else { // Custom amount
                                    splitTotalEl.textContent = total.toFixed(2);
                                    
                                    // Update status
                                    if (splitStatusEl) {
                                        if (Math.abs(total - totalAmount) < 0.01) {
                                            splitStatusEl.textContent = 'Balanced';
                                            splitStatusEl.className = 'badge bg-success';
                                        } else if (total < totalAmount) {
                                            splitStatusEl.textContent = 'Underfunded';
                                            splitStatusEl.className = 'badge bg-warning';
                                        } else {
                                            splitStatusEl.textContent = 'Overfunded';
                                            splitStatusEl.className = 'badge bg-danger';
                                        }
                                    }
                                }
                            }
                            
                            // Update hidden split details field
                            if (splitDetailsInput) {
                                splitDetailsInput.value = JSON.stringify({
                                    type: splitMethod,
                                    values: splitValues
                                });
                            }
                        });
                        
                        // Trigger input event to initialize values
                        input.dispatchEvent(new Event('input'));
                    });
                };
                
                // Toggle personal expense mode
                const togglePersonalExpense = function() {
                    const personalExpenseCheck = document.getElementById('personal_expense');
                    if (!personalExpenseCheck) return;
                    
                    const splitWithSelect = document.getElementById('split_with');
                    const splitMethodContainer = document.getElementById('split_method')?.parentNode;
                    const customSplitContainer = document.getElementById('custom_split_container');
                    
                    console.log("Personal expense toggled:", personalExpenseCheck.checked);
                    
                    if (personalExpenseCheck.checked) {
                        // This is a personal expense - simplify the form
                        if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
                        if (customSplitContainer) customSplitContainer.style.display = 'none';
                        
                        // Clear any existing split_with selections
                        if (splitWithSelect) {
                            for (let i = 0; i < splitWithSelect.options.length; i++) {
                                splitWithSelect.options[i].selected = false;
                            }
                            splitWithSelect.disabled = true;
                            
                            // Also disable the custom multi-select
                            const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
                            if (customMultiSelect) {
                                customMultiSelect.style.opacity = '0.5';
                                customMultiSelect.style.pointerEvents = 'none';
                            } else {
                                splitWithSelect.parentNode.style.opacity = '0.5';
                            }
                        }
                    } else {
                        // This is a shared expense - enable the split options
                        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
                        
                        if (splitWithSelect) {
                            splitWithSelect.disabled = false;
                            
                            // Re-enable the custom multi-select
                            const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
                            if (customMultiSelect) {
                                customMultiSelect.style.opacity = '1';
                                customMultiSelect.style.pointerEvents = 'auto';
                            } else {
                                splitWithSelect.parentNode.style.opacity = '1';
                            }
                            
                            // Auto-select the paid_by user
                            autoSelectPaidBy();
                        }
                        
                        // Show custom split container if needed
                        const splitMethodSelect = document.getElementById('split_method');
                        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
                            customSplitContainer.style.display = 'block';
                        }
                    }
                    
                    // Update split values if needed
                    updateSplitValues();
                    
                    // Trigger change event to update UI
                    if (splitWithSelect) {
                        splitWithSelect.dispatchEvent(new Event('change'));
                    }
                };
                
                // Execute our inline implementations
                try {
                    // Add styles
                    addStyles();
                    
                    // Setup transaction type change handler
                    const transactionTypeSelect = document.getElementById('transaction_type');
                    if (transactionTypeSelect) {
                        transactionTypeSelect.addEventListener('change', function() {
                            const transactionType = this.value;
                            const expenseOnlyFields = document.querySelectorAll('.expense-only-fields');
                            const toAccountContainer = document.getElementById('to_account_container');
                            const accountLabel = document.getElementById('account_label');
                            const personalExpenseCheck = document.getElementById('personal_expense');
                            
                            // Show/hide fields based on transaction type
                            if (transactionType === 'expense') {
                                // Show splitting options for expenses
                                expenseOnlyFields.forEach(el => el.style.display = 'block');
                                if (toAccountContainer) toAccountContainer.style.display = 'none';
                                
                                // Update account label
                                if (accountLabel) accountLabel.textContent = 'Payment Account';
                                
                                // Enable personal expense toggle
                                if (personalExpenseCheck) {
                                    personalExpenseCheck.disabled = false;
                                    const switchContainer = personalExpenseCheck.closest('.form-check');
                                    if (switchContainer) switchContainer.style.opacity = '1';
                                }
                            } 
                            else if (transactionType === 'income') {
                                // Hide splitting options for income
                                expenseOnlyFields.forEach(el => el.style.display = 'none');
                                if (toAccountContainer) toAccountContainer.style.display = 'none';
                                
                                // Update account label
                                if (accountLabel) accountLabel.textContent = 'Deposit Account';
                            }
                            else if (transactionType === 'transfer') {
                                // Hide splitting options for transfers
                                expenseOnlyFields.forEach(el => el.style.display = 'none');
                                
                                // Show destination account
                                if (toAccountContainer) toAccountContainer.style.display = 'block';
                                
                                // Update account label
                                if (accountLabel) accountLabel.textContent = 'From Account';
                            }
                        });
                        
                        // Initialize UI based on default transaction type
                        transactionTypeSelect.dispatchEvent(new Event('change'));
                    }
                    
                    // Setup personal expense toggle
                    const personalExpenseCheck = document.getElementById('personal_expense');
                    if (personalExpenseCheck) {
                        personalExpenseCheck.addEventListener('change', togglePersonalExpense);
                    }
                    
                    // Setup split method change handler
                    const splitMethodSelect = document.getElementById('split_method');
                    if (splitMethodSelect) {
                        splitMethodSelect.addEventListener('change', toggleSplitOptions);
                    }
                    
                    // Setup amount field change handler
                    const amountField = document.getElementById('amount');
                    if (amountField) {
                        amountField.addEventListener('input', function() {
                            // Only update split values if a split method is selected
                            const splitMethod = document.getElementById('split_method')?.value;
                            if (splitMethod && splitMethod !== 'equal') {
                                updateSplitValues();
                            }
                        });
                    }
                    
                    // Setup paid by change handler
                    const paidBySelect = document.getElementById('paid_by');
                    if (paidBySelect) {
                        paidBySelect.addEventListener('change', function() {
                            // Auto-select the paid by user
                            autoSelectPaidBy();
                            
                            // Only update split values if a split method is selected
                            const splitMethod = document.getElementById('split_method')?.value;
                            if (splitMethod && splitMethod !== 'equal') {
                                updateSplitValues();
                            }
                        });
                    }
                    
                    // Initialize split with selector
                    initializeMultiSelect('#split_with');
                    
                    // Setup split with change handler
                    const splitWithSelect = document.getElementById('split_with');
                    if (splitWithSelect) {
                        splitWithSelect.addEventListener('change', function() {
                            // Only update split values if a split method is selected
                            const splitMethod = document.getElementById('split_method')?.value;
                            if (splitMethod && splitMethod !== 'equal') {
                                updateSplitValues();
                            }
                        });
                    }
                    
                    // Auto-select the paid by user
                    autoSelectPaidBy();
                    
                    console.log("Add transaction panel setup complete");
                } catch (error) {
                    console.error("Error setting up add transaction panel:", error);
                }
            }
        })
        .catch(error => {
            console.error('Error loading form:', error);
            showMessage('Error loading transaction form. Please try again.', 'error');
        });
}