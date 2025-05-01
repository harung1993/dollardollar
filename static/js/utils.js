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
 * Enhanced Multi-Select Dropdown Implementation
 * Creates a user-friendly dropdown for selecting multiple options
 */

/**
 * Initialize multi-select dropdowns for the given selector
 * @param {string} selector - CSS selector for multi-select elements
 */
function initializeMultiSelect(selector) {
    // Find all matching elements
    const elements = document.querySelectorAll(selector);
    console.log(`Found ${elements.length} elements matching selector: ${selector}`);
    
    // Process each element
    elements.forEach(select => {
        // Skip if not a select element or doesn't have multiple attribute
        if (select.tagName !== 'SELECT' || !select.multiple) {
            console.warn(`Element ${select.id || 'unknown'} is not a multiple select, skipping`);
            return;
        }
        
        // Skip if already enhanced
        if (select.getAttribute('data-enhanced') === 'true') {
            console.log(`Select ${select.id || 'unknown'} already enhanced, skipping`);
            return;
        }
        
        // Mark as enhanced
        select.setAttribute('data-enhanced', 'true');
        
        // Create the enhanced UI
        createEnhancedUI(select);
    });
}

/**
 * Create the enhanced UI for a select element
 * @param {HTMLSelectElement} select - The select element to enhance
 */
function createEnhancedUI(select) {
    console.log(`Creating enhanced UI for select: ${select.id || 'unnamed'}`);
    
    // Ensure styles are added
    addMultiSelectStyles();
    
    // Create wrapper container
    const container = document.createElement('div');
    container.className = 'enhanced-multiselect-container';
    select.parentNode.insertBefore(container, select);
    container.appendChild(select);
    
    // Create display box
    const displayBox = document.createElement('div');
    displayBox.className = 'enhanced-multiselect-display';
    displayBox.setAttribute('tabindex', '0'); // Make it focusable
    displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
    container.insertBefore(displayBox, select);
    
    // Create dropdown container
    const dropdown = document.createElement('div');
    dropdown.className = 'enhanced-multiselect-dropdown';
    dropdown.style.display = 'none';
    container.appendChild(dropdown);
    
    // Add search input
    const searchBox = document.createElement('div');
    searchBox.className = 'enhanced-multiselect-search-container';
    
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'enhanced-multiselect-search';
    searchInput.placeholder = 'Search...';
    
    searchBox.appendChild(searchInput);
    dropdown.appendChild(searchBox);
    
    // Add options list
    const optionsList = document.createElement('div');
    optionsList.className = 'enhanced-multiselect-options';
    dropdown.appendChild(optionsList);
    
    // Populate options
    populateOptions(select, optionsList);
    
    // Update display to show current selections
    updateDisplay(select, displayBox);
    
    // Add event listeners
    addEventListeners(select, displayBox, dropdown, searchInput, optionsList);
    
    console.log(`Enhanced UI created for select: ${select.id || 'unnamed'}`);
}

/**
 * Populate options in the dropdown
 * @param {HTMLSelectElement} select - The original select element
 * @param {HTMLElement} optionsList - The container for options
 */
function populateOptions(select, optionsList) {
    // Clear existing options
    optionsList.innerHTML = '';
    
    // Add each option
    Array.from(select.options).forEach(option => {
        // Skip if disabled
        if (option.disabled) return;
        
        // Create option element
        const optionItem = document.createElement('div');
        optionItem.className = 'enhanced-multiselect-option';
        optionItem.setAttribute('data-value', option.value);
        
        // Create checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'enhanced-multiselect-checkbox';
        checkbox.checked = option.selected;
        
        // Create label
        const label = document.createElement('label');
        label.className = 'enhanced-multiselect-label';
        label.textContent = option.textContent;
        
        // Add elements to option item
        optionItem.appendChild(checkbox);
        optionItem.appendChild(label);
        optionsList.appendChild(optionItem);
        
        // Handle option click
        optionItem.addEventListener('click', e => {
            e.stopPropagation();
            
            // Toggle checkbox
            checkbox.checked = !checkbox.checked;
            
            // Update original select
            option.selected = checkbox.checked;
            
            // Trigger change event on the original select
            const event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        });
    });
}

/**
 * Update the display box to show selected options
 * @param {HTMLSelectElement} select - The original select element
 * @param {HTMLElement} displayBox - The display box element
 */
function updateDisplay(select, displayBox) {
    // Get selected options
    const selectedOptions = Array.from(select.selectedOptions);
    
    // Show placeholder if nothing selected
    if (selectedOptions.length === 0) {
        displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
        return;
    }
    
    // Create badges for selected options
    displayBox.innerHTML = '';
    selectedOptions.forEach(option => {
        const badge = document.createElement('span');
        badge.className = 'enhanced-multiselect-badge';
        badge.textContent = option.textContent;
        
        // Add remove button
        const removeBtn = document.createElement('span');
        removeBtn.className = 'enhanced-multiselect-remove';
        removeBtn.innerHTML = '&times;';
        
        // Handle remove click
        removeBtn.addEventListener('click', e => {
            e.stopPropagation();
            
            // Deselect the option
            option.selected = false;
            
            // Trigger change event
            const event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        });
        
        badge.appendChild(removeBtn);
        displayBox.appendChild(badge);
    });
}

/**
 * Add event listeners to the enhanced select components
 * @param {HTMLSelectElement} select - The original select element
 * @param {HTMLElement} displayBox - The display box element
 * @param {HTMLElement} dropdown - The dropdown element
 * @param {HTMLInputElement} searchInput - The search input element
 * @param {HTMLElement} optionsList - The options list element
 */
function addEventListeners(select, displayBox, dropdown, searchInput, optionsList) {
    // Toggle dropdown when clicking on display box
    displayBox.addEventListener('click', e => {
        e.stopPropagation();
        toggleDropdown(dropdown, searchInput);
    });
    
    // Toggle with keyboard
    displayBox.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleDropdown(dropdown, searchInput);
        }
    });
    
    // Handle search input
    searchInput.addEventListener('input', () => {
        const searchText = searchInput.value.toLowerCase();
        filterOptions(optionsList, searchText);
    });
    
    // Prevent search clicks from closing dropdown
    searchInput.addEventListener('click', e => {
        e.stopPropagation();
    });
    
    // Update display when original select changes
    select.addEventListener('change', () => {
        // Update checkboxes
        Array.from(optionsList.querySelectorAll('.enhanced-multiselect-option')).forEach(optionEl => {
            const value = optionEl.getAttribute('data-value');
            const checkbox = optionEl.querySelector('.enhanced-multiselect-checkbox');
            const option = Array.from(select.options).find(opt => opt.value === value);
            
            if (option && checkbox) {
                checkbox.checked = option.selected;
            }
        });
        
        // Update display
        updateDisplay(select, displayBox);
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', () => {
        dropdown.style.display = 'none';
    });
}

/**
 * Toggle dropdown visibility
 * @param {HTMLElement} dropdown - The dropdown element
 * @param {HTMLInputElement} searchInput - The search input element
 */
function toggleDropdown(dropdown, searchInput) {
    const isVisible = dropdown.style.display === 'block';
    
    // Toggle visibility
    dropdown.style.display = isVisible ? 'none' : 'block';
    
    // Focus search input if showing dropdown
    if (!isVisible) {
        searchInput.focus();
        searchInput.value = '';
        
        // Trigger input event to reset filtering
        const event = new Event('input', { bubbles: true });
        searchInput.dispatchEvent(event);
    }
}

/**
 * Filter options based on search text
 * @param {HTMLElement} optionsList - The options list element
 * @param {string} searchText - The text to search for
 */
function filterOptions(optionsList, searchText) {
    // Get all options
    const options = optionsList.querySelectorAll('.enhanced-multiselect-option');
    
    // Show/hide based on match
    options.forEach(option => {
        const label = option.querySelector('.enhanced-multiselect-label');
        const text = label.textContent.toLowerCase();
        
        option.style.display = text.includes(searchText) ? 'flex' : 'none';
    });
}

/**
 * Add necessary styles for the enhanced multi-select
 */
function addMultiSelectStyles() {
    // Skip if already added
    if (document.getElementById('enhanced-multiselect-styles')) return;
    
    // Create style element
    const style = document.createElement('style');
    style.id = 'enhanced-multiselect-styles';
    
    // Add CSS
    style.textContent = `
        /* Container for the enhanced select */
        .enhanced-multiselect-container {
            position: relative;
            width: 100%;
        }
        
        /* Hide original select */
        .enhanced-multiselect-container select {
            display: none;
        }
        
        /* Display box styling */
        .enhanced-multiselect-display {
            min-height: 38px;
            padding: 6px 12px;
            background-color: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            cursor: pointer;
            color: #fff;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
        }
        
        .enhanced-multiselect-display:hover,
        .enhanced-multiselect-display:focus {
            border-color: rgba(14, 165, 233, 0.5);
            outline: none;
            box-shadow: 0 0 0 0.2rem rgba(14, 165, 233, 0.25);
        }
        
        /* Placeholder styling */
        .enhanced-multiselect-display .placeholder {
            color: #6c757d;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        /* Badge styling */
        .enhanced-multiselect-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            line-height: 1;
            color: #fff;
            background-color: #0ea5e9;
            border-radius: 9999px;
            white-space: nowrap;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Remove button styling */
        .enhanced-multiselect-remove {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-left: 4px;
            font-size: 1.25rem;
            line-height: 0.5;
            color: rgba(255, 255, 255, 0.7);
            cursor: pointer;
        }
        
        .enhanced-multiselect-remove:hover {
            color: #fff;
        }
        
        /* Dropdown styling */
        .enhanced-multiselect-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            width: 100%;
            max-height: 250px;
            margin-top: 4px;
            padding: 8px;
            background-color: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
            z-index: 9999;
            overflow-y: auto;
        }
        
        /* Search input styling */
        .enhanced-multiselect-search-container {
            margin-bottom: 8px;
            position: sticky;
            top: 0;
            background-color: #1e293b;
            padding: 2px 0;
            z-index: 1;
        }
        
        .enhanced-multiselect-search {
            width: 100%;
            padding: 0.375rem 0.75rem;
            font-size: 0.875rem;
            line-height: 1.5;
            color: #fff;
            background-color: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 0.25rem;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
        }
        
        .enhanced-multiselect-search:focus {
            border-color: rgba(14, 165, 233, 0.5);
            outline: none;
            box-shadow: 0 0 0 0.2rem rgba(14, 165, 233, 0.25);
        }
        
        /* Options list styling */
        .enhanced-multiselect-options {
            overflow-y: auto;
        }
        
        /* Option styling */
        .enhanced-multiselect-option {
            display: flex;
            align-items: center;
            padding: 0.5rem 0.75rem;
            cursor: pointer;
            border-radius: 0.25rem;
            transition: background-color 0.15s ease;
            margin-bottom: 2px;
        }
        
        .enhanced-multiselect-option:hover {
            background-color: rgba(30, 41, 59, 0.8);
        }
        
        /* Checkbox styling */
        .enhanced-multiselect-checkbox {
            margin-right: 8px;
        }
        
        /* Label styling */
        .enhanced-multiselect-label {
            color: #fff;
            margin-bottom: 0;
            cursor: pointer;
            user-select: none;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    `;
    
    // Add to document head
    document.head.appendChild(style);
    console.log("Enhanced multi-select styles added");
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
                
                // Function to auto-select the paid by user
                function autoSelectPaidBy() {
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
                }
                
                // Function to update split values UI
                function updateSplitValues() {
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
                    const splitTotalEl = document.getElementById('split_values_total');
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
                }
                
                // Setup input listeners for split values
                function setupSplitInputListeners(splitMethod, splitValues, totalAmount) {
                    const splitDetailsInput = document.getElementById('split_details');
                    const splitTotalEl = document.getElementById('split_values_total');
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
                }
                
                // Function to handle split options toggle
                function toggleSplitOptions() {
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
                }
                
                // Toggle personal expense mode
                function togglePersonalExpense() {
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
                            const customMultiSelect = splitWithSelect.closest('.enhanced-multiselect-container');
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
                            const customMultiSelect = splitWithSelect.closest('.enhanced-multiselect-container');
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
                }
                
                try {
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
                    
                    // Initialize multi-select for split_with
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

// Make functions available globally
window.openSlidePanel = openSlidePanel;
window.closeSlidePanel = closeSlidePanel;
window.showMessage = showMessage;
window.initializeMultiSelect = initializeMultiSelect;
window.openAddTransactionPanel = openAddTransactionPanel;