/**
 * Add Transaction Module - Dollar Dollar Bill Y'all
 * 
 * This module handles all functionality related to adding new transactions.
 * It provides a clean API for opening the add panel, handling form interactions,
 * and processing form submission.
 */
const AddTransactionModule = (function() {
    // Private module variables
    let baseCurrencySymbol = '$';
    
    // Initialize the module
    function init() {
        // Check if EditTransactionModule is already loaded to avoid conflicts
        if (window.EditTransactionModule) {
            console.log("EditTransactionModule detected, ensuring compatibility");
        }
        
        // Set base currency symbol from global variable if available
        if (window.baseCurrencySymbol) {
            baseCurrencySymbol = window.baseCurrencySymbol;
        }
        
        console.log("AddTransactionModule initialized with currency symbol:", baseCurrencySymbol);
        
        // Set up global event listeners
        setupEventListeners();
        
        // Return public API
        return {
            openAddPanel,
            closePanel: closeSlidePanel,
            showMessage,
            // Include version info for debugging
            _version: "1.0.0",
            _name: "AddTransactionModule"
        };
    }
    
    // Setup event listeners for add transaction buttons
    function setupEventListeners() {
        // Use event delegation for add buttons
        document.addEventListener('click', function(event) {
            const addBtn = event.target.closest('#openAddTransactionBtn, .add-transaction-btn');
            if (addBtn) {
                event.preventDefault();
                
                // Check if there's group data in the button
                const groupId = addBtn.getAttribute('data-group-id');
                let groupData = null;
                
                if (groupId && window.groupsData && window.groupsData[groupId]) {
                    groupData = window.groupsData[groupId];
                }
                
                openAddPanel(groupData);
            }
        });
    }
    
    /**
     * Open panel to add a new transaction
     * @param {Object} groupData - Optional group data if adding from a group page
     */
    function openAddPanel(groupData) {
        console.log("Opening add transaction panel", groupData ? "with group data" : "without group data");
        
        // Open a slide panel
        const panel = openSlidePanel('addTransactionPanel', {
            title: 'Add Transaction',
            icon: 'fa-plus',
            iconColor: '#0ea5e9'
        });
        
        // Load form content from server
        fetch('/get_transaction_form_html')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(html => {
                // Update panel content
                panel.querySelector('.slide-panel-content').innerHTML = html;
                
                // Initialize form
                setupAddForm(groupData);
            })
            .catch(error => {
                console.error('Error loading form:', error);
                showMessage('Error loading transaction form. Please try again.', 'error');
                closeSlidePanel('addTransactionPanel');
            });
    }
    
    /**
     * Set up the add transaction form
     * @param {Object} groupData - Optional group data for pre-filling
     */
    function setupAddForm(groupData) {
        console.log("Setting up add transaction form");
        
        // Set today's date
        const dateInput = document.getElementById('date');
        if (dateInput && !dateInput.value) {
            dateInput.value = new Date().toISOString().split('T')[0];
        }
        
        // Setup transaction type change handlers
        setupTransactionTypeHandlers();
        
        // Setup personal expense toggle
        setupPersonalExpenseToggle();
        
        // Setup split method handlers
        setupSplitMethodHandlers();
        
        // Setup form submission
        const form = document.getElementById('newTransactionForm');
        if (form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                submitAddForm(form);
            });
        }
        
        // Setup category split toggle if present
        setupCategorySplitToggle();
        
        // Apply group data if present
        if (groupData && groupData.id) {
            applyGroupDefaults(groupData);
        }
    }
    
    /**
     * Set up transaction type radio buttons
     */
    function setupTransactionTypeHandlers() {
        const transactionTypes = document.querySelectorAll('input[name="transaction_type"]');
        
        transactionTypes.forEach(input => {
            input.addEventListener('change', function() {
                updateTransactionTypeUI(this.value);
            });
        });
        
        // Initialize UI based on selected type
        const selectedType = document.querySelector('input[name="transaction_type"]:checked')?.value || 'expense';
        updateTransactionTypeUI(selectedType);
    }
    
    /**
     * Update UI based on transaction type
     */
    function updateTransactionTypeUI(type) {
        const expenseOnlyFields = document.querySelectorAll('.expense-only-fields');
        const toAccountContainer = document.getElementById('to_account_container');
        const accountLabel = document.getElementById('account_label');
        
        if (type === 'expense') {
            // Show expense fields
            expenseOnlyFields.forEach(el => {
                el.style.display = 'block';
            });
            
            // Hide to_account
            if (toAccountContainer) {
                toAccountContainer.classList.add('d-none');
            }
            
            // Update label
            if (accountLabel) {
                accountLabel.textContent = 'Payment Account';
            }
            
            // Check personal expense toggle
            const personalCheck = document.getElementById('personal_expense');
            if (personalCheck) {
                const splitSection = document.querySelector('.split-section');
                if (splitSection) {
                    splitSection.classList.toggle('d-none', personalCheck.checked);
                }
            }
        } 
        else if (type === 'income') {
            // Hide expense fields
            expenseOnlyFields.forEach(el => {
                el.style.display = 'none';
            });
            
            // Hide to_account
            if (toAccountContainer) {
                toAccountContainer.classList.add('d-none');
            }
            
            // Update label
            if (accountLabel) {
                accountLabel.textContent = 'Deposit Account';
            }
        }
        else if (type === 'transfer') {
            // Hide expense fields
            expenseOnlyFields.forEach(el => {
                el.style.display = 'none';
            });
            
            // Show to_account
            if (toAccountContainer) {
                toAccountContainer.classList.remove('d-none');
            }
            
            // Update label
            if (accountLabel) {
                accountLabel.textContent = 'From Account';
            }
        }
    }
    
    /**
     * Set up personal expense toggle
     */
    function setupPersonalExpenseToggle() {
        const personalExpenseCheck = document.getElementById('personal_expense');
        if (!personalExpenseCheck) return;
        
        personalExpenseCheck.addEventListener('change', function() {
            const splitSection = document.querySelector('.split-section');
            
            if (splitSection) {
                splitSection.classList.toggle('d-none', this.checked);
            }
        });
        
        // Trigger initial state
        personalExpenseCheck.dispatchEvent(new Event('change'));
    }
    
    /**
     * Set up split method handlers
     */
    function setupSplitMethodHandlers() {
        const splitMethodSelect = document.getElementById('split_method');
        if (!splitMethodSelect) return;
        
        const splitValuesToggle = document.getElementById('split_values_toggle');
        const customSplitContainer = document.getElementById('custom_split_container');
        
        // Enable toggle button
        if (splitValuesToggle) {
            splitValuesToggle.disabled = false;
            
            splitValuesToggle.addEventListener('click', function() {
                if (customSplitContainer) {
                    const isVisible = !customSplitContainer.classList.contains('d-none');
                    customSplitContainer.classList.toggle('d-none', isVisible);
                    
                    // Update button text
                    this.innerHTML = isVisible ? 
                        '<i class="fas fa-calculator me-2"></i>Show Split Values' : 
                        '<i class="fas fa-calculator me-2"></i>Hide Split Values';
                    
                    // Initialize split values if showing
                    if (!isVisible) {
                        updateSplitValueInputs();
                    }
                }
            });
        }
        
        // Handle split method changes
        splitMethodSelect.addEventListener('change', function() {
            const method = this.value;
            
            // If "Group Default" is selected and a group is active
            if (method === 'group_default') {
                const groupId = document.getElementById('group_id')?.value;
                
                if (groupId && window.groupsData && window.groupsData[groupId]) {
                    const groupData = window.groupsData[groupId];
                    
                    // Check if the group has a default split method
                    if (groupData.defaultSplitMethod) {
                        // Apply group's default split method logic
                        const actualMethod = groupData.defaultSplitMethod;
                        
                        // Update method display
                        const methodDisplay = document.getElementById('split_method_display');
                        if (methodDisplay) {
                            methodDisplay.textContent = 
                                actualMethod === 'equal' ? 'Group Default (Equal)' : 
                                actualMethod === 'percentage' ? 'Group Default (Percentage)' : 
                                'Group Default (Custom)';
                        }
                        
                        // Show/hide custom split container based on the actual method
                        if (customSplitContainer) {
                            customSplitContainer.classList.toggle('d-none', actualMethod === 'equal');
                        }
                        
                        // Apply the group's default split values if they exist
                        if (actualMethod !== 'equal' && 
                            groupData.defaultSplitValues && 
                            Object.keys(groupData.defaultSplitValues).length > 0) {
                            
                            // Handle string vs object defaultSplitValues
                            let splitValues;
                            if (typeof groupData.defaultSplitValues === 'string') {
                                try {
                                    splitValues = JSON.parse(groupData.defaultSplitValues);
                                } catch (e) {
                                    splitValues = {};
                                }
                            } else {
                                splitValues = groupData.defaultSplitValues;
                            }
                            
                            // Create split details from group defaults and store in hidden field
                            const splitDetailsInput = document.getElementById('split_details');
                            if (splitDetailsInput) {
                                const splitDetails = {
                                    type: actualMethod, 
                                    values: splitValues
                                };
                                splitDetailsInput.value = JSON.stringify(splitDetails);
                                
                                // Show split values UI
                                if (splitValuesToggle && customSplitContainer) {
                                    customSplitContainer.classList.remove('d-none');
                                    splitValuesToggle.innerHTML = '<i class="fas fa-calculator me-2"></i>Hide Split Values';
                                }
                                
                                // Update the UI with the group defaults
                                setTimeout(() => {
                                    updateSplitValueInputs(actualMethod);
                                }, 100);
                            }
                        }
                    } else {
                        // No default split method found in group data
                        if (customSplitContainer) {
                            customSplitContainer.classList.add('d-none');
                        }
                    }
                } else {
                    // No group selected, fall back to equal split
                    this.value = 'equal';
                    // Trigger change event to update UI
                    this.dispatchEvent(new Event('change'));
                }
            } else {
                // Regular split method handling
                // Update method display
                const methodDisplay = document.getElementById('split_method_display');
                if (methodDisplay) {
                    methodDisplay.textContent = 
                        method === 'equal' ? 'Equal Split' : 
                        method === 'percentage' ? 'Percentage Split' : 
                        'Custom Amount Split';
                }
                
                // Show/hide custom split container based on method
                if (customSplitContainer) {
                    customSplitContainer.classList.toggle('d-none', method === 'equal');
                    
                    // Initialize values if not equal and container is showing
                    if (method !== 'equal' && !customSplitContainer.classList.contains('d-none')) {
                        updateSplitValueInputs(method);
                    }
                }
            }
        });
    }
    
    /**
     * Update split value inputs based on method
     */
    function updateSplitValueInputs(forcedMethod) {
        const splitMethodSelect = document.getElementById('split_method');
        if (!splitMethodSelect) {
            return;
        }
        
        // Get selected split method or use forced method if provided
        let splitMethod = forcedMethod || splitMethodSelect.value;
        
        // Handle group_default by getting actual method from group
        if (splitMethod === 'group_default') {
            const groupId = document.getElementById('group_id')?.value;
            
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                splitMethod = groupData.defaultSplitMethod || 'equal';
            } else {
                splitMethod = 'equal';
            }
        }
        
        // Skip if equal split since we don't need to show/initialize split values
        if (splitMethod === 'equal') {
            return;
        }
        
        // Get container and required form elements
        const container = document.getElementById('split_values_container');
        const totalAmount = parseFloat(document.getElementById('amount').value) || 0;
        const paidById = document.getElementById('paid_by').value;
        const splitDetailsInput = document.getElementById('split_details');
        
        if (!container || !splitDetailsInput) {
            return;
        }
        
        // Clear container
        container.innerHTML = '';
        
        // Get selected users
        const splitWithSelect = document.getElementById('split_with');
        if (!splitWithSelect) {
            return;
        }
        
        const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(option => option.value);
        if (splitWithIds.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">Please select people to split with</div>';
            return;
        }
        
        // All participants (include payer if not in splits)
        const allParticipants = [...splitWithIds];
        if (paidById && !allParticipants.includes(paidById)) {
            allParticipants.push(paidById);
        }
        
        // Try to get existing values if available
        let splitValues = {};
        try {
            if (splitDetailsInput.value) {
                const details = JSON.parse(splitDetailsInput.value);
                if (details && details.values) {
                    splitValues = details.values;
                }
            }
        } catch (error) {
            console.warn('Error parsing split details:', error);
        }
        
        // Create UI based on split method
        if (splitMethod === 'percentage') {
            // Create percentage inputs
            const defaultPercentage = 100 / allParticipants.length;
            
            allParticipants.forEach(userId => {
                const userOption = Array.from(document.querySelectorAll('#paid_by option, #split_with option'))
                                    .find(option => option.value === userId);
                const userName = userOption ? userOption.textContent : userId;
                const isPayerId = userId === paidById;
                
                // Use existing value or default
                const percentage = splitValues[userId] !== undefined ? 
                                splitValues[userId] : defaultPercentage;
                
                // Create row
                const row = document.createElement('div');
                row.className = 'row mb-2 align-items-center';
                row.innerHTML = `
                    <div class="col-md-6">
                        <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                            ${isPayerId ? '💰 ' : ''}${userName}
                        </span>
                    </div>
                    <div class="col-md-6">
                        <div class="input-group">
                            <input type="number" class="form-control bg-dark text-light split-value"
                                data-user-id="${userId}" step="0.1" min="0" value="${percentage.toFixed(1)}">
                            <span class="input-group-text bg-dark text-light">%</span>
                        </div>
                    </div>
                `;
                
                container.appendChild(row);
                splitValues[userId] = percentage;
            });
        }
        else { // Custom amount
            // Create amount inputs
            const defaultAmount = totalAmount / allParticipants.length;
            
            allParticipants.forEach(userId => {
                const userOption = Array.from(document.querySelectorAll('#paid_by option, #split_with option'))
                                    .find(option => option.value === userId);
                const userName = userOption ? userOption.textContent : userId;
                const isPayerId = userId === paidById;
                
                // Use existing value or default
                const amount = splitValues[userId] !== undefined ? 
                            splitValues[userId] : defaultAmount;
                
                // Create row
                const row = document.createElement('div');
                row.className = 'row mb-2 align-items-center';
                row.innerHTML = `
                    <div class="col-md-6">
                        <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                            ${isPayerId ? '💰 ' : ''}${userName}
                        </span>
                    </div>
                    <div class="col-md-6">
                        <div class="input-group">
                            <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                            <input type="number" class="form-control bg-dark text-light split-value"
                                data-user-id="${userId}" step="0.01" min="0" value="${amount.toFixed(2)}">
                        </div>
                    </div>
                `;
                
                container.appendChild(row);
                splitValues[userId] = amount;
            });
        }
        
        // Add event listeners to split value inputs
        document.querySelectorAll('.split-value').forEach(input => {
            input.addEventListener('input', function() {
                updateSplitTotals(splitMethod, totalAmount);
            });
            
            // Trigger input event to initialize
            input.dispatchEvent(new Event('input'));
        });
        
        // Update hidden field with complete values
        const splitDetails = {
            type: splitMethod,
            values: splitValues
        };
        
        splitDetailsInput.value = JSON.stringify(splitDetails);
        
        // Update totals
        updateSplitTotals(splitMethod, totalAmount);
    }
    
    /**
     * Update split totals display
     */
    function updateSplitTotals(splitMethod, totalAmount) {
        if (!totalAmount) {
            totalAmount = parseFloat(document.getElementById('amount')?.value) || 0;
        }
        
        const totalEl = document.getElementById('split_values_total');
        const statusEl = document.getElementById('split_status');
        const splitDetailsInput = document.getElementById('split_details');
        
        if (!totalEl || !statusEl || !splitDetailsInput) {
            return;
        }
        
        // Collect values from inputs
        const values = {};
        let total = 0;
        
        document.querySelectorAll('.split-value').forEach(input => {
            const userId = input.getAttribute('data-user-id');
            const value = parseFloat(input.value) || 0;
            
            values[userId] = value;
            total += value;
        });
        
        // Save to hidden input
        splitDetailsInput.value = JSON.stringify({
            type: splitMethod,
            values: values
        });
        
        // Update total display
        if (splitMethod === 'percentage') {
            totalEl.textContent = total.toFixed(1) + '%';
            
            // Update status
            if (Math.abs(total - 100) < 0.1) {
                statusEl.textContent = 'Balanced';
                statusEl.className = 'badge bg-success';
            } else if (total < 100) {
                statusEl.textContent = 'Underfunded';
                statusEl.className = 'badge bg-warning';
            } else {
                statusEl.textContent = 'Overfunded';
                statusEl.className = 'badge bg-danger';
            }
        } else {
            totalEl.textContent = `${baseCurrencySymbol}${total.toFixed(2)}`;
            
            // Update status
            if (Math.abs(total - totalAmount) < 0.01) {
                statusEl.textContent = 'Balanced';
                statusEl.className = 'badge bg-success';
            } else if (total < totalAmount) {
                statusEl.textContent = 'Underfunded';
                statusEl.className = 'badge bg-warning';
            } else {
                statusEl.textContent = 'Overfunded';
                statusEl.className = 'badge bg-danger';
            }
        }
    }
    
    /**
     * Apply group defaults to the add form
     */
    function applyGroupDefaults(groupData) {
        console.log("Applying group defaults:", groupData);
        
        // Set group ID
        const groupSelect = document.getElementById('group_id');
        if (groupSelect) {
            groupSelect.value = groupData.id;
        }
        
        // Set personal expense to false
        const personalExpenseCheck = document.getElementById('personal_expense');
        if (personalExpenseCheck && personalExpenseCheck.checked) {
            personalExpenseCheck.checked = false;
            personalExpenseCheck.dispatchEvent(new Event('change'));
        }
        
        // Apply default payer if specified
        if (groupData.defaultPayer) {
            const paidBySelect = document.getElementById('paid_by');
            if (paidBySelect) {
                paidBySelect.value = groupData.defaultPayer;
            }
        }
        
        // Apply auto-include all members if enabled
        if (groupData.autoIncludeAll) {
            const splitWithSelect = document.getElementById('split_with');
            if (splitWithSelect) {
                // Get payer ID
                const paidBySelect = document.getElementById('paid_by');
                const payerId = paidBySelect ? paidBySelect.value : null;
                
                // Select all members except payer
                Array.from(splitWithSelect.options).forEach(option => {
                    if (groupData.members.includes(option.value)) {
                        option.selected = option.value !== payerId;
                    }
                });
                
                // Trigger change event
                splitWithSelect.dispatchEvent(new Event('change'));
            }
        }
        
        // Apply default split method if specified
        if (groupData.defaultSplitMethod) {
            const splitMethodSelect = document.getElementById('split_method');
            if (splitMethodSelect) {
                // Use group_default as the selection
                splitMethodSelect.value = 'group_default';
                
                // Set up custom split container visibility based on the actual method
                const customSplitContainer = document.getElementById('custom_split_container');
                if (customSplitContainer) {
                    // Only show if the actual split method is not 'equal'
                    customSplitContainer.classList.toggle('d-none', groupData.defaultSplitMethod === 'equal');
                }
                
                // Set up split method display
                const methodDisplay = document.getElementById('split_method_display');
                if (methodDisplay) {
                    methodDisplay.textContent = 
                        groupData.defaultSplitMethod === 'equal' ? 'Group Default (Equal)' : 
                        groupData.defaultSplitMethod === 'percentage' ? 'Group Default (Percentage)' : 
                        'Group Default (Custom)';
                }
                
                // Apply default split values if they exist and it's not an equal split
                if (groupData.defaultSplitMethod !== 'equal' && 
                    groupData.defaultSplitValues && 
                    Object.keys(groupData.defaultSplitValues).length > 0) {
                    
                    // Create split details from defaults
                    const splitDetailsInput = document.getElementById('split_details');
                    if (splitDetailsInput) {
                        // Handle different types of defaultSplitValues
                        let splitValues;
                        if (typeof groupData.defaultSplitValues === 'string') {
                            try {
                                splitValues = JSON.parse(groupData.defaultSplitValues);
                            } catch (e) {
                                console.error("Error parsing default split values:", e);
                                splitValues = {};
                            }
                        } else {
                            splitValues = groupData.defaultSplitValues;
                        }
                        
                        // Create and store the split details
                        const splitDetails = {
                            type: groupData.defaultSplitMethod,
                            values: splitValues
                        };
                        
                        splitDetailsInput.value = JSON.stringify(splitDetails);
                        
                        // Show split values UI
                        const splitValuesToggle = document.getElementById('split_values_toggle');
                        if (splitValuesToggle && customSplitContainer) {
                            customSplitContainer.classList.remove('d-none');
                            splitValuesToggle.innerHTML = '<i class="fas fa-calculator me-2"></i>Hide Split Values';
                            splitValuesToggle.disabled = false;
                        }
                        
                        // Update the UI with actual values
                        setTimeout(() => {
                            updateSplitValueInputs(groupData.defaultSplitMethod);
                        }, 100);
                    }
                }
                
                // Manually trigger the change event to update UI
                splitMethodSelect.dispatchEvent(new Event('change'));
            }
        }
    }
    
    /**
     * Setup category split toggle
     */
    function setupCategorySplitToggle() {
        const enableSplitCheck = document.getElementById('enable_category_split');
        if (!enableSplitCheck) return;
        
        enableSplitCheck.addEventListener('change', function() {
            const container = document.getElementById('category_splits_container');
            const categorySelect = document.getElementById('category_id');
            
            if (container) {
                container.classList.toggle('d-none', !this.checked);
            }
            
            if (categorySelect) {
                categorySelect.disabled = this.checked;
            }
            
            // Initialize with first row if enabling
            if (this.checked && document.querySelectorAll('.split-category').length === 0) {
                addCategorySplitRow();
            }
            
            // Update totals
            updateCategorySplitTotals();
        });
        
        // Add category split button handler
        const addSplitBtn = document.getElementById('add_category_split');
        if (addSplitBtn) {
            addSplitBtn.addEventListener('click', function() {
                addCategorySplitRow();
            });
        }
    }
    
    /**
     * Add a category split row to the form
     */
    function addCategorySplitRow(categoryId, amount) {
        const container = document.getElementById('category_splits_list');
        if (!container) {
            console.error("Category splits list container not found");
            return;
        }
        
        // Create a unique ID for this row
        const rowId = Date.now() + Math.floor(Math.random() * 1000);
        
        // Get category options from main category select
        let categorySelect = document.getElementById('category_id');
        const categoryOptions = categorySelect ? categorySelect.innerHTML : '';
        
        // Create HTML for the row
        const rowHTML = `
            <div class="row mb-3 split-row" data-split-id="${rowId}">
                <div class="col-md-5">
                    <select class="form-select bg-dark text-light split-category" name="split_category_${rowId}">
                        <option value="">Select category</option>
                        ${categoryOptions}
                    </select>
                </div>
                <div class="col-md-5">
                    <div class="input-group">
                        <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                        <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                                name="split_amount_${rowId}" value="${amount || ''}">
                    </div>
                </div>
                <div class="col-md-2">
                    <button type="button" class="btn btn-outline-danger remove-split">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Add row to container
        container.insertAdjacentHTML('beforeend', rowHTML);
        
        // Get the row we just added
        const row = container.lastElementChild;
        
        // Set category if provided
        if (categoryId) {
            const select = row.querySelector('.split-category');
            if (select) select.value = categoryId;
        }
        
        // Add event listeners
        const removeBtn = row.querySelector('.remove-split');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                row.remove();
                updateCategorySplitTotals();
            });
        }
        
        const amountInput = row.querySelector('.split-amount');
        if (amountInput) {
            amountInput.addEventListener('input', updateCategorySplitTotals);
        }
        
        // Update totals
        updateCategorySplitTotals();
    }
    
    /**
     * Update category split totals display and data
     */
    function updateCategorySplitTotals() {
        const totalEl = document.getElementById('category_split_total');
        const targetEl = document.getElementById('category_split_target');
        const statusEl = document.getElementById('category_split_status');
        const dataInput = document.getElementById('category_splits_data');
        
        if (!totalEl || !dataInput) {
            return;
        }
        
        // Get total amount from form
        const totalAmount = parseFloat(document.getElementById('amount')?.value || '0');
        
        // Calculate total from splits
        let splitTotal = 0;
        const splits = [];
        
        document.querySelectorAll('.split-row').forEach(row => {
            const category = row.querySelector('.split-category')?.value;
            const amount = parseFloat(row.querySelector('.split-amount')?.value) || 0;
            
            if (category && amount > 0) {
                splits.push({
                    category_id: category,
                    amount: amount
                });
                splitTotal += amount;
            }
        });
        
        // Update totals display
        if (totalEl) totalEl.textContent = splitTotal.toFixed(2);
        if (targetEl) targetEl.textContent = totalAmount.toFixed(2);
        
        // Update status
        if (statusEl) {
            if (Math.abs(splitTotal - totalAmount) < 0.01) {
                statusEl.textContent = 'Balanced';
                statusEl.className = 'badge bg-success';
            } else if (splitTotal < totalAmount) {
                statusEl.textContent = 'Underfunded';
                statusEl.className = 'badge bg-warning';
            } else {
                statusEl.textContent = 'Overfunded';
                statusEl.className = 'badge bg-danger';
            }
        }
        
        // Update hidden data field
        dataInput.value = JSON.stringify(splits);
    }
    
    /**
     * Submit the add transaction form
     */
    function submitAddForm(form) {
        if (!form) {
            console.error("Form element not found");
            return;
        }
        
        const formData = new FormData(form);
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn?.innerHTML || 'Save';
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
        }
        
        // Submit the form with AJAX
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showMessage(data.message || 'Transaction added successfully!');
                
                // Close panel and refresh page
                closeSlidePanel('addTransactionPanel');
                
                // Reload page after a delay to show new data
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                throw new Error(data.message || 'Failed to add transaction');
            }
        })
        .catch(error => {
            console.error('Error submitting form:', error);
            showMessage(error.message, 'error');
            
            // Reset submit button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }
    
    /**
     * Open a slide panel
     */
    function openSlidePanel(panelId, options = {}) {
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
            closeBtn.addEventListener('click', () => closeSlidePanel(panelId));
        }
        
        // Create or get overlay
        let overlay = document.getElementById('slide-panel-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'slide-panel-overlay';
            overlay.className = 'slide-panel-overlay';
            overlay.addEventListener('click', () => closeSlidePanel(panelId));
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
     */
    function closeSlidePanel(panelId) {
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
     * Show a message toast
     * Check if EditTransactionModule.showMessage exists and use it if available
     */
    function showMessage(message, type = 'success') {
        // Use EditTransactionModule's showMessage if available
        if (window.EditTransactionModule && typeof window.EditTransactionModule.showMessage === 'function') {
            return window.EditTransactionModule.showMessage(message, type);
        }
        
        // Otherwise, use shared UI helper if available
        if (window.UIHelpers && typeof window.UIHelpers.showToast === 'function') {
            return window.UIHelpers.showToast(message, type);
        }
        
        // Fallback to our own implementation
        // Check if Bootstrap is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            // Create toast container if needed
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            // Create toast with unique ID
            const toastId = `add-toast-${Date.now()}`; // Prefixed to avoid conflicts
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = 'toast';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            // Set toast content
            toast.innerHTML = `
                <div class="toast-header ${type === 'error' ? 'bg-danger' : 'bg-success'} text-white">
                    <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 'fa-check-circle'} me-2"></i>
                    <strong class="me-auto">${type === 'error' ? 'Error' : 'Success'}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">${message}</div>
            `;
            
            // Add to container
            toastContainer.appendChild(toast);
            
            // Show toast with Bootstrap
            const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
            bsToast.show();
            
            // Remove from DOM after hiding
            toast.addEventListener('hidden.bs.toast', function() {
                if (toast.parentNode) {
                    toast.remove();
                }
            });
        } else {
            // Fallback to alert if Bootstrap not available
            if (type === 'error') {
                alert(`Error: ${message}`);
            } else {
                alert(message);
            }
        }
    }
    
    // Return public API
    return init();
})();

// Make the module available globally
window.AddTransactionModule = AddTransactionModule;