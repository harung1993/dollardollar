/**
 * JavaScript for recurring transaction form
 */

// Store the base currency symbol
let baseCurrencySymbol = '$'; // Default fallback
let slidePanelOpen = false; // Global variable to track if a slide panel is open

// Try to get the symbol from multiple potential sources
function initBaseCurrencySymbol() {
    // Try window object first
    if (window.baseCurrencySymbol) {
        baseCurrencySymbol = window.baseCurrencySymbol;
        console.log("Currency symbol from window:", baseCurrencySymbol);
        return;
    }

    // Try data attribute
    const currencyDataEl = document.getElementById('currency-data');
    if (currencyDataEl) {
        const symbolFromData = currencyDataEl.getAttribute('data-symbol');
        if (symbolFromData) {
            baseCurrencySymbol = symbolFromData;
            console.log("Currency symbol from data attribute:", baseCurrencySymbol);
            return;
        }
    }

    // Try global variable
    if (typeof baseCurrencySymbol !== 'undefined') {
        console.log("Currency symbol from global variable:", baseCurrencySymbol);
        return;
    }

    console.warn("Could not find base currency symbol, using default: $");
}

/**
 * Initialize the recurring transaction form
 */
function initRecurringTransactionForm() {
    // Initialize currency symbol
    initBaseCurrencySymbol();
    
    // Set today's date for the start date if not already set
    const startDateInput = document.getElementById('start_date');
    if (startDateInput && !startDateInput.value) {
        startDateInput.value = new Date().toISOString().split('T')[0];
    }
    
    // Set up transaction type change listeners
    setupTransactionTypeListeners();
    
    // Handle personal expense toggle
    const personalExpenseCheck = document.getElementById('personal_expense_check');
    if (personalExpenseCheck) {
        personalExpenseCheck.addEventListener('change', togglePersonalExpense);
    }
    
    // Handle split method changes
    const splitMethodSelect = document.getElementById('split_method');
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', toggleSplitOptions);
    }
    
    // Handle amount field changes
    const amountInput = document.getElementById('amount');
    if (amountInput) {
        amountInput.addEventListener('input', updateSplitValues);
    }
    
    // Handle paid_by changes
    const paidBySelect = document.getElementById('paid_by');
    if (paidBySelect) {
        paidBySelect.addEventListener('change', function() {
            autoSelectPaidByUser();
            updateSplitValues();
        });
    }
    
    // Listen for split_with changes
    const splitWithSelect = document.getElementById('split_with');
    if (splitWithSelect) {
        splitWithSelect.addEventListener('change', updateSplitValues);
    }
    
    // Initialize enhanced multi-select for split_with
    if (typeof initializeEnhancedMultiSelect === 'function') {
        setTimeout(function() {
            initializeEnhancedMultiSelect();
        }, 100);
    }
    
    // Force initial transaction type UI setup
    handleTransactionTypeChange();
}

/**
 * Set up listeners for transaction type changes
 */
function setupTransactionTypeListeners() {
    const transactionTypeInputs = document.querySelectorAll('input[name="transaction_type"]');
    transactionTypeInputs.forEach(input => {
        input.addEventListener('change', handleTransactionTypeChange);
    });
}

/**
 * Handle transaction type changes to show/hide relevant fields
 */
function handleTransactionTypeChange() {
    const transactionType = document.querySelector('input[name="transaction_type"]:checked')?.value || 'expense';
    const expenseFields = document.getElementById('expense_specific_fields');
    const categoryContainer = document.getElementById('category_container');
    const destinationAccountContainer = document.getElementById('destination_account_container');
    const accountLabel = document.getElementById('account_label');
    const submitButton = document.getElementById('submit_button');
    
    // Update submit button text
    if (submitButton) {
        submitButton.textContent = `Add Recurring ${transactionType.charAt(0).toUpperCase() + transactionType.slice(1)}`;
    }
    
    switch (transactionType) {
        case 'expense':
            // Show expense-specific fields
            if (expenseFields) expenseFields.style.display = 'block';
            // Show category selection
            if (categoryContainer) categoryContainer.style.display = 'block';
            // Hide destination account
            if (destinationAccountContainer) destinationAccountContainer.style.display = 'none';
            // Update account label
            if (accountLabel) accountLabel.textContent = 'Account';
            break;
            
        case 'income':
            // Hide expense-specific fields
            if (expenseFields) expenseFields.style.display = 'none';
            // Show category selection
            if (categoryContainer) categoryContainer.style.display = 'block';
            // Hide destination account
            if (destinationAccountContainer) destinationAccountContainer.style.display = 'none';
            // Update account label
            if (accountLabel) accountLabel.textContent = 'Deposit Account';
            break;
            
        case 'transfer':
            // Hide expense-specific fields
            if (expenseFields) expenseFields.style.display = 'none';
            // Show category selection for transfers now
            if (categoryContainer) categoryContainer.style.display = 'block';
            // Show destination account
            if (destinationAccountContainer) destinationAccountContainer.style.display = 'block';
            // Update account label
            if (accountLabel) accountLabel.textContent = 'From Account';
            break;
    }
}

/**
 * Auto-select the paid_by user in the split_with dropdown
 */
function autoSelectPaidByUser() {
    const paidBySelect = document.getElementById('paid_by');
    const splitWithSelect = document.getElementById('split_with');
    
    if (!paidBySelect || !splitWithSelect) return;
    
    const paidById = paidBySelect.value;
    if (!paidById) return;
    
    // If there are no existing selections yet
    if (Array.from(splitWithSelect.selectedOptions).length === 0) {
        // Find the option for the paid by user and select it
        const option = splitWithSelect.querySelector(`option[value="${paidById}"]`);
        if (option) {
            option.selected = true;
            // Trigger change event to update the UI
            splitWithSelect.dispatchEvent(new Event('change'));
        }
    }
}

/**
 * Toggle personal expense state
 */
function togglePersonalExpense() {
    const personalExpenseCheck = document.getElementById('personal_expense_check');
    if (!personalExpenseCheck) return;
    
    const splitWithSelect = document.getElementById('split_with');
    const splitMethodContainer = document.getElementById('split_method')?.parentNode;
    const customSplitContainer = document.getElementById('custom_split_container');
    
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
            autoSelectPaidByUser();
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

/**
 * Toggle split options based on method
 */
function toggleSplitOptions() {
    const splitMethodSelect = document.getElementById('split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    const customSplitContainer = document.getElementById('custom_split_container');
    const personalExpenseCheck = document.getElementById('personal_expense_check');
    
    // Don't show custom split container for personal expenses
    if (personalExpenseCheck && personalExpenseCheck.checked) {
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        return;
    }
    
    if (splitMethod === 'equal') {
        if (customSplitContainer) customSplitContainer.style.display = 'none';
    } else {
        if (customSplitContainer) customSplitContainer.style.display = 'block';
        
        // Update the split values UI
        updateSplitValues();
    }
}

/**
 * Update split values UI
 */
function updateSplitValues() {
    const splitMethodSelect = document.getElementById('split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById('personal_expense_check');
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
}

/**
 * Setup input listeners for split values
 */
function setupSplitInputListeners(splitMethod, splitValues, totalAmount) {
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
}

/**
 * Edit an existing recurring transaction
 */
function editRecurringTransaction(recurringId) {
    // Open the panel first
    openRecurringTransactionPanel();
    
    // After panel is open, fetch the recurring transaction data
    fetch(`/get_recurring/${recurringId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update panel title
                const panelHeader = document.querySelector('#recurringTransactionPanel .slide-panel-header h3');
                if (panelHeader) {
                    panelHeader.textContent = 'Edit Recurring Transaction';
                }
                
                // Wait for form to be fully loaded
                setTimeout(() => populateRecurringForm(data.recurring), 200);
                
                // Change form action to update endpoint
                const form = document.getElementById('recurringTransactionForm');
                if (form) {
                    form.action = `/update_recurring/${recurringId}`;
                    
                    // Update submit button
                    const submitButton = form.querySelector('button[type="submit"]');
                    if (submitButton) {
                        submitButton.textContent = 'Update Recurring Transaction';
                    }
                }
            } else {
                console.error('Error fetching recurring transaction:', data.message);
                alert('Could not load transaction data. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error fetching recurring transaction:', error);
            alert('Could not load transaction data. Please try again.');
        });
}

/**
 * Populate the recurring transaction form with data
 */
function populateRecurringForm(data) {
    // Set transaction type
    const transactionType = data.transaction_type || 'expense';
    const typeRadio = document.getElementById(`type_${transactionType}`);
    if (typeRadio) {
        typeRadio.checked = true;
        handleTransactionTypeChange();
    }
    
    // Populate basic fields
    document.getElementById('description').value = data.description || '';
    document.getElementById('amount').value = data.amount || 0;
    
    if (data.currency_code) {
        const currencySelect = document.getElementById('currency_code');
        if (currencySelect) currencySelect.value = data.currency_code;
    }
    
    if (data.frequency) {
        const frequencySelect = document.getElementById('frequency');
        if (frequencySelect) frequencySelect.value = data.frequency;
    }
    
    // Handle account based on transaction type
    if (data.account_id) {
        const accountSelect = document.getElementById('account_id');
        if (accountSelect) accountSelect.value = data.account_id;
    }
    
    if (data.destination_account_id && transactionType === 'transfer') {
        const destAccountSelect = document.getElementById('destination_account_id');
        if (destAccountSelect) destAccountSelect.value = data.destination_account_id;
    }
    
    // Set dates
    if (data.start_date) {
        document.getElementById('start_date').value = data.start_date;
    }
    
    if (data.end_date) {
        document.getElementById('end_date').value = data.end_date;
    }
    
    // Handle expense-specific fields
    if (transactionType === 'expense') {
        // Set paid by
        const paidBySelect = document.getElementById('paid_by');
        if (paidBySelect && data.paid_by) {
            paidBySelect.value = data.paid_by;
        }
        
        // Handle split with
        const splitWithSelect = document.getElementById('split_with');
        if (splitWithSelect && data.split_with) {
            // Clear existing selections
            Array.from(splitWithSelect.options).forEach(opt => opt.selected = false);
            
            // Select the appropriate options
            data.split_with.forEach(userId => {
                const option = splitWithSelect.querySelector(`option[value="${userId}"]`);
                if (option) option.selected = true;
            });
            
            // Update the enhanced-multi-select if it exists
            if (typeof updateMultiselectDisplay === 'function') {
                updateMultiselectDisplay();
            }
            
            // Set personal expense checkbox - it's personal if split_with is empty
            const personalExpenseCheck = document.getElementById('personal_expense_check');
            if (personalExpenseCheck) {
                personalExpenseCheck.checked = !data.split_with.length;
                togglePersonalExpense();
            }
        } else {
            // No split with data - check personal expense
            const personalExpenseCheck = document.getElementById('personal_expense_check');
            if (personalExpenseCheck) {
                personalExpenseCheck.checked = true;
                togglePersonalExpense();
            }
        }
        
        // Set split method
        const splitMethodSelect = document.getElementById('split_method');
        if (splitMethodSelect && data.split_method) {
            splitMethodSelect.value = data.split_method;
            toggleSplitOptions();
        }
        
        // Handle split details if available
        if (data.split_details) {
            const splitDetailsInput = document.getElementById('split_details');
            if (splitDetailsInput) {
                splitDetailsInput.value = JSON.stringify(data.split_details);
                
                // Update UI for custom splits
                if (data.split_method !== 'equal') {
                    updateSplitValues();
                }
            }
        }
        
        // Set group if available
        if (data.group_id) {
            const groupSelect = document.getElementById('group_id');
            if (groupSelect) groupSelect.value = data.group_id;
        }
    }
    
    // Set category if available - now for all transaction types
    if (data.category_id) {
        const categorySelect = document.getElementById('category_id');
        if (categorySelect) categorySelect.value = data.category_id;
    }
}

/**
 * SLIDE PANEL MANAGEMENT 
 * These functions handle opening and closing the slide panel with proper cleanup
 */

/**
 * Open a slide panel
 */
function openSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // Create backdrop if it doesn't exist
    let backdrop = document.getElementById('slide-panel-backdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.id = 'slide-panel-backdrop';
        backdrop.className = 'slide-panel-backdrop';
        document.body.appendChild(backdrop);
        
        // Close panel when backdrop is clicked
        backdrop.addEventListener('click', function() {
            closeAllSlidePanels();
        });
    }
    
    // Open the panel and backdrop
    panel.classList.add('open');
    backdrop.classList.add('open');
    backdrop.style.display = 'block';
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    // Set global tracking variable
    slidePanelOpen = true;
}

/**
 * Close a specific slide panel
 */
function closeSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // Close the panel
    panel.classList.remove('open');
    
    // Check if any other panels are still open
    const openPanels = document.querySelectorAll('.slide-panel.open');
    if (openPanels.length === 0) {
        // No more open panels, remove backdrop and restore body
        removeBackdropAndRestoreBody();
    }
}

/**
 * Close all open slide panels
 */
function closeAllSlidePanels() {
    // Close all panels
    const openPanels = document.querySelectorAll('.slide-panel.open');
    openPanels.forEach(panel => {
        panel.classList.remove('open');
    });
    
    // Remove backdrop and restore body
    removeBackdropAndRestoreBody();
}

/**
 * Helper function to remove backdrop and restore body state
 */
function removeBackdropAndRestoreBody() {
    // Remove backdrop
    const backdrop = document.getElementById('slide-panel-backdrop');
    if (backdrop) {
        backdrop.classList.remove('open');
        backdrop.style.display = 'none';
        
        // Remove from DOM completely
        if (backdrop.parentNode) {
            backdrop.parentNode.removeChild(backdrop);
        }
    }
    
    // Restore body styles
    document.body.style.overflow = '';
    
    // Reset global tracking variable
    slidePanelOpen = false;
}

/**
 * Open the recurring transaction form as slide panel
 */
function openRecurringTransactionPanel() {
    // Initialize panel slide container if needed
    if (!document.getElementById('recurringTransactionPanel')) {
        const panelContainer = document.createElement('div');
        panelContainer.id = 'recurringTransactionPanel';
        panelContainer.className = 'slide-panel';
        panelContainer.innerHTML = `
            <div class="slide-panel-header">
                <h3>Add Recurring Transaction</h3>
                <button type="button" class="btn-close text-light" onclick="closeSlidePanel('recurringTransactionPanel')"></button>
            </div>
            <div class="slide-panel-body">
                <div class="slide-panel-content">
                    <!-- Form will be loaded here -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-light" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(panelContainer);
    }
    
    // Open the panel
    openSlidePanel('recurringTransactionPanel');
    
    // Load the form content via AJAX
    fetch('/get_recurring_form_html')
        .then(response => response.text())
        .then(html => {
            const contentContainer = document.querySelector('#recurringTransactionPanel .slide-panel-content');
            contentContainer.innerHTML = html;
            
            // Initialize form
            initRecurringTransactionForm();
        })
        .catch(error => {
            console.error('Error loading recurring transaction form:', error);
            const contentContainer = document.querySelector('#recurringTransactionPanel .slide-panel-content');
            contentContainer.innerHTML = '<div class="alert alert-danger">Error loading form. Please try again.</div>';
        });
}

// Add event listeners for global click handling and page unload
document.addEventListener('DOMContentLoaded', function() {
    // Add click handler to close panels when clicking outside
    document.addEventListener('click', function(event) {
        // Skip if no panel is open
        if (!slidePanelOpen) return;
        
        // Check if we clicked outside any open panels
        const openPanels = document.querySelectorAll('.slide-panel.open');
        if (openPanels.length > 0) {
            let clickedInsidePanel = false;
            
            // Check if click was inside any panel
            for (const panel of openPanels) {
                if (panel.contains(event.target)) {
                    clickedInsidePanel = true;
                    break;
                }
            }
            
            // If click was outside panels and not on a panel-related button
            if (!clickedInsidePanel && 
                !event.target.closest('[onclick*="RecurringTransaction"]') &&
                !event.target.closest('#addRecurringBtn') &&
                !event.target.closest('.slide-panel-backdrop')) {
                
                // Close all open panels
                closeAllSlidePanels();
            }
        }
    });

    // Ensure cleanup on page unload
    window.addEventListener('beforeunload', function() {
        removeBackdropAndRestoreBody();
    });
    
    // Add CSS for slide panel if not already added
    if (!document.getElementById('slide-panel-styles')) {
        const styleSheet = document.createElement('style');
        styleSheet.id = 'slide-panel-styles';
        styleSheet.textContent = `
            .slide-panel {
                position: fixed;
                top: 0;
                right: -100%;
                width: 90%;
                max-width: 550px;
                height: 100%;
                background-color: #212529;
                z-index: 1050;
                transition: right 0.3s ease;
                display: flex;
                flex-direction: column;
                box-shadow: -5px 0 15px rgba(0, 0, 0, 0.3);
            }
            
            .slide-panel.open {
                right: 0;
            }
            
            .slide-panel-header {
                padding: 1rem;
                border-bottom: 1px solid #2d2d3a;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .slide-panel-body {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
            }
            
            .slide-panel-backdrop {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                z-index: 1040;
                display: none;
            }
            
            .slide-panel-backdrop.open {
                display: block;
            }
        `;
        document.head.appendChild(styleSheet);
    }
    
    // Add keyboard shortcut to close panel with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && slidePanelOpen) {
            closeAllSlidePanels();
        }
    });
});