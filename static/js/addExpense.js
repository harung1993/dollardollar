// static/js/addExpense.js
baseCurrencySymbol = '{{ base_currency.symbol }}';

// Initialize form based on transaction type
function initializeFormState() {
    // Set default date to today
    const dateInput = document.getElementById('date');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
    
    // Initialize all form fields based on the selected transaction type
    handleTransactionTypeChange();
    
    // Make sure labels are up to date
    updateFormLabels();
}

// Handle Transaction Type Change
function handleTransactionTypeChange() {
    const transactionType = document.getElementById('transaction_type').value;
    const splitSection = document.querySelector('.expense-only-fields');
    const customSplitContainer = document.getElementById('custom_split_container');
    const accountLabel = document.querySelector('label[for="account_id"]');
    const toAccountContainer = document.getElementById('to_account_container');
    
    // Show/hide fields based on transaction type
    if (transactionType === 'expense') {
        // Show splitting options for expenses
        if (splitSection) splitSection.style.display = 'block';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
    } 
    else if (transactionType === 'income') {
        // Hide splitting options for income
        if (splitSection) splitSection.style.display = 'none';
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Deposit Account';
    }
    else if (transactionType === 'transfer') {
        // Hide splitting options for transfers
        if (splitSection) splitSection.style.display = 'none';
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        
        // Show destination account for transfers
        if (toAccountContainer) toAccountContainer.style.display = 'block';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'From Account';
    }
    
    // Update form title and button text
    updateFormLabels();
}

// Toggle personal expense mode
function togglePersonalExpense() {
    const personalExpenseCheck = document.getElementById('personal_expense');
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
            splitWithSelect.parentNode.style.opacity = '0.5';
        }
    } else {
        // This is a shared expense - enable the split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        if (splitWithSelect) {
            splitWithSelect.disabled = false;
            splitWithSelect.parentNode.style.opacity = '1';
        }
        
        // Show custom split container if needed
        const splitMethodSelect = document.getElementById('split_method');
        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
            customSplitContainer.style.display = 'block';
        }
    }
    
    // Update split values if needed
    updateSplitValues();
}

// Toggle split options based on selected method
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

// Update form labels based on transaction type
function updateFormLabels() {
    const transactionType = document.getElementById('transaction_type')?.value;
    if (!transactionType) return;
    
    const submitButton = document.querySelector('button[type="submit"]');
    
    if (submitButton) {
        submitButton.textContent = 'Add ' + capitalizeFirstLetter(transactionType);
    }
}

// Helper function for capitalization
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Update split values when fields change
function updateSplitValues() {
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
    const splitStatusEl = document.getElementById('split_status');
    
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
                        <span class="input-group-text bg-dark text-light">$</span>
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
    
    // Set up listener on all value inputs
    document.querySelectorAll('.split-value-input').forEach(input => {
        input.addEventListener('input', function() {
            const userId = this.getAttribute('data-user-id');
            const value = parseFloat(this.value) || 0;
            
            // Update the values
            splitValues[userId] = value;
            
            // Calculate total
            const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
            
            // Update UI
            if (splitMethod === 'percentage') {
                splitTotalEl.textContent = total.toFixed(1) + '%';
                
                // Update status
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
            } else {
                splitTotalEl.textContent = total.toFixed(2);
                
                // Update status
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
            
            // Update hidden field with JSON
            splitDetailsInput.value = JSON.stringify({
                type: splitMethod === 'percentage' ? 'percentage' : 'amount',
                values: splitValues
            });
        });
    });
    
    // Trigger input events to initialize all fields
    document.querySelectorAll('.split-value-input').forEach(input => {
        input.dispatchEvent(new Event('input'));
    });
}

// Set up event listeners when the form is loaded
function setupAddTransactionForm() {
    // Transaction type change handler
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', handleTransactionTypeChange);
    }
    
    // Personal expense toggle
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (personalExpenseCheck) {
        personalExpenseCheck.addEventListener('change', togglePersonalExpense);
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById('split_method');
    if (splitMethodSelect) {
        splitMethodSelect.addEventListener('change', toggleSplitOptions);
    }
    
    // Amount field change handler
    const amountInput = document.getElementById('amount');
    if (amountInput) {
        amountInput.addEventListener('input', updateSplitValues);
    }
    
    // Paid by change handler
    const paidBySelect = document.getElementById('paid_by');
    if (paidBySelect) {
        paidBySelect.addEventListener('change', updateSplitValues);
    }
    
    // Split with change handler
    const splitWithSelect = document.getElementById('split_with');
    if (splitWithSelect) {
        splitWithSelect.addEventListener('change', updateSplitValues);
    }
    
    // Initialize form state
    initializeFormState();
}

// Initialize select elements to be user-friendly (no need for Ctrl+click)
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
        
        // Add event listener
        checkbox.addEventListener('change', function() {
            option.selected = checkbox.checked;
            // Trigger change event on original select
            const event = new Event('change', { bubbles: true });
            select.dispatchEvent(event);
        });
        
        // Make the whole item clickable
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

// For the transactions page - Slide panel functionality
let slidePanel = null;

// Open a slide panel with transaction form
function openAddTransactionPanel() {
    // Create the slide panel
    slidePanel = openSlidePanel('addTransactionPanel', {
        title: 'Add New Transaction',
        icon: 'fa-plus',
        iconColor: '#0ea5e9'
    });
    
    // Fetch the form HTML
    fetch('/get_transaction_form_html')
        .then(response => response.text())
        .then(html => {
            const contentDiv = slidePanel.querySelector('.slide-panel-content');
            if (contentDiv) {
                contentDiv.innerHTML = html;
                
                // Initialize form elements
                setupAddTransactionForm();
                
                // Make split_with select user-friendly (no need for Ctrl+click)
                initializeSelectWithoutCtrl('split_with');
            }
        })
        .catch(error => {
            console.error('Error loading form:', error);
            showMessage('Error loading transaction form. Please try again.', 'error');
        });
}

// Create and display a slide panel (for transactions page)
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
        } else {
            content.innerHTML = '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        }
        
        // Assemble panel
        panel.appendChild(header);
        panel.appendChild(content);
        
        // Add to DOM
        document.body.appendChild(panel);
    }
    
    // Create and show overlay if needed
    let overlay = document.getElementById('slide-panel-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'slide-panel-overlay';
        overlay.className = 'slide-panel-overlay';
        overlay.onclick = function() {
            closeSlidePanel(panelId);
        };
        document.body.appendChild(overlay);
    }
    
    // Show overlay
    overlay.classList.add('active');
    
    // Show panel with animation
    setTimeout(() => {
        panel.classList.add('active');
    }, 10);
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    return panel;
}

// Close slide panel
function closeSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.classList.remove('active');
        
        // Remove panel after animation
        setTimeout(() => {
            panel.remove();
        }, 300);
    }
    
    // Hide overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        
        // Remove overlay after animation
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

// For the dashboard - Form toggle functionality
function toggleExpenseForm() {
    const form = document.getElementById('expenseFormContainer');
    const toggleButton = document.getElementById('toggleExpenseForm');
    
    if (form && toggleButton) {
        if (form.style.display === 'none' || form.style.display === '') {
            form.style.display = 'block';
            toggleButton.innerHTML = '<i class="fas fa-times me-2"></i>Cancel';
            toggleButton.classList.replace('btn-primary', 'btn-secondary');
            
            // Initialize form based on default transaction type
            setupAddTransactionForm();
        } else {
            form.style.display = 'none';
            toggleButton.innerHTML = '<i class="fas fa-plus me-2"></i>Add New Transaction';
            toggleButton.classList.replace('btn-secondary', 'btn-primary');
            
            // Reset form fields when closing
            const formElement = form.querySelector('form');
            if (formElement) formElement.reset();
        }
    }
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with the add transaction button
    const addTransactionBtn = document.getElementById('openAddTransactionBtn');
    if (addTransactionBtn) {
        addTransactionBtn.addEventListener('click', openAddTransactionPanel);
    }
    
    // Check if we're on the dashboard with the toggle button
    const toggleExpenseBtn = document.getElementById('toggleExpenseForm');
    if (toggleExpenseBtn) {
        toggleExpenseBtn.addEventListener('click', toggleExpenseForm);
    }
    
    // Check if we have a visible form to initialize
    const visibleForm = document.getElementById('expenseFormContainer');
    if (visibleForm && visibleForm.style.display !== 'none') {
        setupAddTransactionForm();
    }
});