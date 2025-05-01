/**
 * Edit Transaction Module - Dollar Dollar Bill Y'all
 * 
 * This module handles all functionality related to editing existing transactions.
 * It provides a clean API for opening the edit panel, loading transaction data,
 * and handling form submission.
 */
const EditTransactionModule = (function() {
    // Private module variables
    let baseCurrencySymbol = '$';
    
    // Initialize the module
    function init() {
        // Set base currency symbol from global variable if available
        if (window.baseCurrencySymbol) {
            baseCurrencySymbol = window.baseCurrencySymbol;
        }
        
        console.log("EditTransactionModule initialized with currency symbol:", baseCurrencySymbol);
        
        // Set up global event listeners
        setupEventListeners();
        
        // Return public API
        return {
            openEditPanel,
            closePanel: closeSlidePanel,
            showMessage
        };
    }
    
    // Setup event listeners for edit buttons
    function setupEventListeners() {
        // Use event delegation for edit buttons
        document.addEventListener('click', function(event) {
            const editBtn = event.target.closest('.edit-expense-btn');
            if (editBtn) {
                event.preventDefault();
                const expenseId = editBtn.getAttribute('data-expense-id');
                if (expenseId) {
                    openEditPanel(expenseId);
                }
            }
        });
    }
    
    /**
     * Open the edit transaction panel for a specific transaction
     * @param {string} expenseId - ID of the expense to edit
     */
    function openEditPanel(expenseId) {
        console.log("Opening edit panel for expense ID:", expenseId);
        
        // Show loading panel
        const panel = openSlidePanel('editTransactionPanel', {
            title: 'Edit Transaction',
            icon: 'fa-edit',
            iconColor: '#0ea5e9'
        });
        
        // Load edit form from server
        fetch(`/get_expense_edit_form/${expenseId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(html => {
                // Update panel content
                panel.querySelector('.slide-panel-content').innerHTML = html;
                
                // Wait for DOM to update
                setTimeout(() => {
                    console.log('Setting up edit form...');
                    setupEditForm();
                    
                    // Trigger the split method change handler to update display
                    const splitMethodSelect = document.getElementById('edit_split_method');
                    if (splitMethodSelect) {
                        console.log('Triggering split method change:', splitMethodSelect.value);
                        splitMethodSelect.dispatchEvent(new Event('change'));
                    }
                }, 100);
            })
            .catch(error => {
                console.error('Error loading edit form:', error);
                showMessage('Error loading edit form. Please try again.', 'error');
                closeSlidePanel('editTransactionPanel');
            });
    }
    
    /**
     * Set up the edit form event handlers and initial state
     */
    function setupEditForm() {
        console.log("Setting up edit transaction form");
        
        // Setup transaction type change handlers
        setupTransactionTypeHandlers();
        
        // Setup personal expense toggle
        setupPersonalExpenseToggle();
        
        // Setup group selection change handler
        setupGroupChangeHandler();
        
        // Setup split method change handler
        setupSplitMethodChangeHandler();
        
        // Setup category split toggle
        setupCategorySplitToggle();
        
        // Setup form submission
        setupFormSubmission();
        
        // Setup split values toggle
        setupSplitValuesToggle();
        
        // If split method is not equal, show the split values container and initialize values
        const splitMethod = document.getElementById('edit_split_method')?.value;
        const splitValuesContainer = document.getElementById('edit_split_values_container');
        
        if (splitMethod && splitMethod !== 'equal' && splitValuesContainer) {
            splitValuesContainer.classList.remove('d-none');
            
            // Initialize split values
            setTimeout(() => {
                initializeSplitValues();
            }, 100);
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
            const personalCheck = document.getElementById('edit_personal_expense');
            if (personalCheck) {
                personalExpenseToggled(personalCheck.checked);
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
        const personalExpenseCheck = document.getElementById('edit_personal_expense');
        if (!personalExpenseCheck) return;
        
        personalExpenseCheck.addEventListener('change', function() {
            personalExpenseToggled(this.checked);
        });
    }
    
    /**
     * Handle personal expense toggle change
     */
    function personalExpenseToggled(isPersonal) {
        const splitSection = document.querySelector('.expense-split-section');
        if (splitSection) {
            splitSection.style.display = isPersonal ? 'none' : 'block';
        }
    }
    
    /**
     * Set up group change handler
     */
    function setupGroupChangeHandler() {
        const groupSelect = document.getElementById('edit_group_id');
        if (!groupSelect) return;
        
        groupSelect.addEventListener('change', function() {
            const groupId = this.value;
            const splitMethodSelect = document.getElementById('edit_split_method');
            
            console.log("Group changed to:", groupId);
            
            // If split method is group_default, update the display
            if (splitMethodSelect && splitMethodSelect.value === 'group_default') {
                console.log("Updating group default display because method is group_default");
                updateGroupDefaultDisplay(groupId);
            }
        });
    }
    
    /**
     * Setup split method change handler
     */
    function setupSplitMethodChangeHandler() {
        const splitMethodSelect = document.getElementById('edit_split_method');
        if (!splitMethodSelect) return;
        
        splitMethodSelect.addEventListener('change', function() {
            const method = this.value;
            const container = document.getElementById('edit_split_values_container');
            const methodDisplay = document.getElementById('split_method_display') || 
                                  document.createElement('span'); // Create a dummy element if not found
            
            console.log("Split method changed to:", method);
            
            if (container) {
                if (method === 'group_default') {
                    // For group_default, use the group's default method
                    const groupId = document.getElementById('edit_group_id')?.value;
                    console.log("Using group default with group ID:", groupId);
                    updateGroupDefaultDisplay(groupId);
                } else {
                    // For other methods, just toggle container visibility
                    container.classList.toggle('d-none', method === 'equal');
                    
                    // Update method display
                    methodDisplay.textContent = 
                        method === 'equal' ? 'Equal Split' : 
                        method === 'percentage' ? 'Percentage Split' : 
                        method === 'custom' ? 'Custom Split' : 
                        method;
                    
                    // Log the updated display text
                    console.log("Updated method display to:", methodDisplay.textContent);
                    
                    // Initialize split values if not equal and container is visible
                    if (method !== 'equal' && !container.classList.contains('d-none')) {
                        initializeSplitValues();
                    }
                }
            }
        });
    }
    
    /**
     * Update display for group default split method
     */
    function updateGroupDefaultDisplay(groupId) {
        const container = document.getElementById('edit_split_values_container');
        const methodDisplay = document.getElementById('split_method_display');
        const splitDetailsInput = document.getElementById('split_details');
        
        console.log("Updating group default display for group ID:", groupId);
        
        if (!container) {
            console.error("Split values container not found");
            return;
        }
        
        // Create a method display element if it doesn't exist
        let displayElement = methodDisplay;
        if (!displayElement) {
            console.log("Method display element not found, creating one");
            displayElement = document.createElement('span');
            displayElement.id = 'split_method_display';
            displayElement.className = 'badge bg-primary';
            
            // Try to find a good place to insert it
            const headerElement = container.querySelector('.card-header');
            if (headerElement) {
                headerElement.appendChild(displayElement);
            } else {
                // If no good place found, at least set a variable so we can use it
                console.warn("No suitable location found to insert method display element");
            }
        }
        
        if (!groupId || !window.groupsData || !window.groupsData[groupId]) {
            console.log("No group data found for ID:", groupId);
            displayElement.textContent = 'Group Default (Equal)';
            container.classList.add('d-none');
            return;
        }
        
        // Get group data
        const groupData = window.groupsData[groupId];
        console.log("Found group data:", groupData);
        
        // Get actual split method
        const actualMethod = groupData.defaultSplitMethod || 'equal';
        console.log("Actual split method from group:", actualMethod);
        
        // Update method display
        displayElement.textContent = 
            actualMethod === 'equal' ? 'Group Default (Equal)' : 
            actualMethod === 'percentage' ? 'Group Default (Percentage)' : 
            'Group Default (Custom)';
        
        console.log("Set method display to:", displayElement.textContent);
        
        // Show/hide container based on actual method
        container.classList.toggle('d-none', actualMethod === 'equal');
        
        // Use group's default split values if available
        if (actualMethod !== 'equal' && groupData.defaultSplitValues && splitDetailsInput) {
            // Handle both string and object formats for defaultSplitValues
            let valueData = groupData.defaultSplitValues;
            
            // Parse if it's a string (JSON) representation
            if (typeof valueData === 'string') {
                try {
                    valueData = JSON.parse(valueData);
                    console.log("Parsed string split values:", valueData);
                } catch(e) {
                    console.error("Error parsing defaultSplitValues string:", e);
                    valueData = {};
                }
            }
            
            console.log("Debug - valueData:", valueData);
            
            // Verify we have valid data - ensure each value is a number
            let processedValues = {};
            let valueDataIsValid = false;
            
            try {
                if (typeof valueData === 'object' && valueData !== null) {
                    // Process each value to ensure it's a number
                    for (const userId in valueData) {
                        if (valueData.hasOwnProperty(userId)) {
                            processedValues[userId] = parseFloat(valueData[userId]) || 0;
                        }
                    }
                    valueDataIsValid = Object.keys(processedValues).length > 0;
                }
            } catch (e) {
                console.error("Error processing valueData:", e);
                valueDataIsValid = false;
            }
            
            if (!valueDataIsValid) {
                console.warn("Invalid valueData, creating new split values");
                // Fallback: create equal split values for all participants
                processedValues = createDefaultSplitValues(actualMethod);
            }
            
            // Save group's default values
            const splitDetails = {
                type: actualMethod,
                values: processedValues
            };
            
            console.log("Final split details:", splitDetails);
            splitDetailsInput.value = JSON.stringify(splitDetails);
            
            // Initialize values in UI with the actual method
            setTimeout(() => {
                initializeSplitValues(actualMethod);
            }, 100);
        }
    }
    
    /**
     * Create default split values for all participants
     */
    function createDefaultSplitValues(method) {
        const paidById = document.getElementById('edit_paid_by')?.value;
        const splitWithSelect = document.getElementById('edit_split_with');
        if (!splitWithSelect) return {};
        
        const splitWith = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
        
        // All participants (include payer if not in splits)
        const allParticipants = [...splitWith];
        if (paidById && !allParticipants.includes(paidById)) {
            allParticipants.push(paidById);
        }
        
        const values = {};
        
        if (method === 'percentage') {
            // Equal percentages
            const equalPercentage = allParticipants.length ? (100 / allParticipants.length) : 100;
            allParticipants.forEach(userId => {
                values[userId] = equalPercentage;
            });
        } else {
            // Custom amounts - use 10.00 for each
            allParticipants.forEach(userId => {
                values[userId] = 10.00;
            });
        }
        
        return values;
    }
    
    /**
     * Setup category split toggle
     */
    function setupCategorySplitToggle() {
        const categorySplitToggle = document.getElementById('enable_category_split');
        if (!categorySplitToggle) return;
        
        categorySplitToggle.addEventListener('change', function() {
            const container = document.getElementById('category_splits_container');
            const categorySelect = document.getElementById('edit_category_id');
            
            if (container) {
                container.classList.toggle('d-none', !this.checked);
            }
            
            if (categorySelect) {
                categorySelect.disabled = this.checked;
            }
            
            // Initialize splits if needed
            if (this.checked && document.querySelectorAll('.split-row').length === 0) {
                addCategorySplitRow();
            }
            
            updateCategorySplitTotals();
        });
        
        // Setup add split button
        const addSplitBtn = document.getElementById('add_split_btn');
        if (addSplitBtn) {
            addSplitBtn.addEventListener('click', function() {
                addCategorySplitRow();
            });
        }
        
        // Setup existing split rows
        document.querySelectorAll('.split-row').forEach(row => {
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
        });
        
        // Initial update of category split totals
        updateCategorySplitTotals();
    }
    
    /**
     * Initialize form submission handler
     */
    function setupFormSubmission() {
        const form = document.getElementById('editTransactionForm');
        if (!form) return;
        
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            submitForm(this);
        });
    }
    
    /**
     * Setup split values toggle button
     */
    function setupSplitValuesToggle() {
        const splitValuesToggle = document.getElementById('edit_split_values_toggle');
        if (!splitValuesToggle) return;
        
        splitValuesToggle.addEventListener('click', function() {
            const container = document.getElementById('edit_split_values_container');
            if (container) {
                const isVisible = !container.classList.contains('d-none');
                container.classList.toggle('d-none', isVisible);
                
                // Initialize split values if showing
                if (!isVisible) {
                    initializeSplitValues();
                }
            }
        });
    }
    
    /**
     * Initialize split values with existing data or defaults
     * @param {string} forcedMethod - Optional method to override selected value
     */
    function initializeSplitValues(forcedMethod) {
        console.log("Initializing edit split values", forcedMethod ? `with forced method: ${forcedMethod}` : "");
        
        const splitMethodSelect = document.getElementById('edit_split_method');
        if (!splitMethodSelect) {
            console.error("Split method select element not found");
            return;
        }
        
        // Get selected split method or use forced method if provided
        let splitMethod = forcedMethod || splitMethodSelect.value;
        console.log("Using split method:", splitMethod);
        
        // Special handling for group_default
        if (splitMethod === 'group_default' && !forcedMethod) {
            const groupId = document.getElementById('edit_group_id')?.value;
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                splitMethod = groupData.defaultSplitMethod || 'equal';
                console.log("Group default method resolved to:", splitMethod);
            } else {
                splitMethod = 'equal';
                console.log("No group data found, defaulting to equal split");
            }
        }
        
        // Get required elements
        const splitDetailsInput = document.getElementById('split_details');
        const splitValuesContainer = document.getElementById('split_values_rows');
        const totalAmountInput = document.getElementById('edit_amount');
        const totalDisplayElement = document.getElementById('split_total_display');
        const statusDisplayElement = document.getElementById('split_status');
        
        if (!splitValuesContainer || !totalAmountInput) {
            console.error("Required elements not found");
            return;
        }
        
        // If split method is equal, don't need to show or initialize
        if (splitMethod === 'equal') {
            splitValuesContainer.innerHTML = '<div class="text-center">Equal splits - each person pays the same amount.</div>';
            
            // Update displays
            if (totalDisplayElement) totalDisplayElement.textContent = 'Equal';
            if (statusDisplayElement) {
                statusDisplayElement.textContent = 'Balanced';
                statusDisplayElement.className = 'badge bg-success';
            }
            
            return;
        }
        
        // Clear container
        splitValuesContainer.innerHTML = '';
        
        // Get total amount
        const totalAmount = parseFloat(totalAmountInput.value) || 0;
        
        // Get paid by and split with
        const paidById = document.getElementById('edit_paid_by').value;
        const splitWithSelect = document.getElementById('edit_split_with');
        
        if (!splitWithSelect) {
            console.error("Split with select element not found");
            return;
        }
        
        const splitWith = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
        
        if (splitWith.length === 0) {
            splitValuesContainer.innerHTML = '<div class="alert alert-warning">Please select users to split with</div>';
            return;
        }
        
        // Get existing split values if available
        let splitValues = {};
        try {
            if (splitDetailsInput && splitDetailsInput.value) {
                const details = JSON.parse(splitDetailsInput.value);
                if (details && details.values) {
                    splitValues = details.values;
                    console.log("Found existing split values:", splitValues);
                }
            }
        } catch (error) {
            console.error('Error parsing split details:', error);
        }
        
        // All participants (include payer if not in splits)
        const allParticipants = [...splitWith];
        if (paidById && !allParticipants.includes(paidById)) {
            allParticipants.push(paidById);
        }
        
        console.log("All participants:", allParticipants);
        
        // Create UI based on split method
        if (splitMethod === 'percentage') {
            // Equal percentages if not defined
            const equalPercent = 100 / allParticipants.length;
            
            allParticipants.forEach(userId => {
                const isPayerId = userId === paidById;
                const userName = getUserName(userId);
                const value = splitValues[userId] !== undefined ? splitValues[userId] : equalPercent;
                
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
                            <input type="number" class="form-control bg-dark text-light split-value-input"
                                   data-user-id="${userId}" step="0.1" min="0" max="100" value="${value.toFixed(1)}">
                            <span class="input-group-text bg-dark text-light">%</span>
                        </div>
                    </div>
                `;
                
                splitValuesContainer.appendChild(row);
                
                // Ensure value is in splitValues
                if (splitValues[userId] === undefined) {
                    splitValues[userId] = value;
                }
            });
        } else {
            // Custom amounts - use equal distribution if not defined
            const equalAmount = totalAmount / allParticipants.length;
            
            allParticipants.forEach(userId => {
                const isPayerId = userId === paidById;
                const userName = getUserName(userId);
                const value = splitValues[userId] !== undefined ? splitValues[userId] : equalAmount;
                
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
                            <input type="number" class="form-control bg-dark text-light split-value-input"
                                   data-user-id="${userId}" step="0.01" min="0" value="${value.toFixed(2)}">
                        </div>
                    </div>
                `;
                
                splitValuesContainer.appendChild(row);
                
                // Ensure value is in splitValues
                if (splitValues[userId] === undefined) {
                    splitValues[userId] = value;
                }
            });
        }
        
        // Add event listeners to inputs
        document.querySelectorAll('.split-value-input').forEach(input => {
            input.addEventListener('input', function() {
                updateSplitValues(splitMethod, totalAmount);
            });
        });
        
        // Update displays immediately
        updateSplitValues(splitMethod, totalAmount);
        
        // Update method display
        const methodDisplay = document.getElementById('split_method_display');
        if (methodDisplay) {
            methodDisplay.textContent = 
                splitMethod === 'equal' ? 'Equal Split' : 
                splitMethod === 'percentage' ? 'Percentage Split' : 
                splitMethod === 'custom' ? 'Custom Split' : 
                splitMethod;
            
            console.log("Updated method display to:", methodDisplay.textContent);
        } else {
            console.warn("Method display element not found");
        }
    }
    
    /**
     * Update split values display and hidden field
     */
    function updateSplitValues(splitMethod, totalAmount) {
        console.log("Updating split values for method:", splitMethod);
        
        if (!totalAmount) {
            totalAmount = parseFloat(document.getElementById('edit_amount')?.value) || 0;
        }
        
        // Handle group_default by getting actual method
        if (splitMethod === 'group_default') {
            const groupId = document.getElementById('edit_group_id')?.value;
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                splitMethod = groupData.defaultSplitMethod || 'equal';
                console.log("Group default resolved to actual method:", splitMethod);
            } else {
                splitMethod = 'equal';
            }
        }
        
        const splitDetailsInput = document.getElementById('split_details');
        const totalDisplay = document.getElementById('split_total_display') || 
                             document.getElementById('split_values_total');
        const statusDisplay = document.getElementById('split_status');
        
        if (!splitDetailsInput || !totalDisplay || !statusDisplay) {
            console.warn("Required elements not found for updating split values");
            return;
        }
        
        // Get values from all inputs
        const values = {};
        let total = 0;
        
        document.querySelectorAll('.split-value-input').forEach(input => {
            const userId = input.getAttribute('data-user-id');
            const value = parseFloat(input.value) || 0;
            values[userId] = value;
            total += value;
        });
        
        // Update split details - use the resolved method, not just what's selected
        const splitDetails = {
            type: splitMethod,
            values: values
        };
        
        // Save to hidden input
        splitDetailsInput.value = JSON.stringify(splitDetails);
        console.log("Updated split details:", splitDetails);
        
        // Update display based on split method
        if (splitMethod === 'percentage') {
            totalDisplay.textContent = total.toFixed(1) + '%';
            
            // Update status
            if (Math.abs(total - 100) < 0.1) {
                statusDisplay.textContent = 'Balanced';
                statusDisplay.className = 'badge bg-success';
            } else if (total < 100) {
                statusDisplay.textContent = 'Underfunded';
                statusDisplay.className = 'badge bg-warning';
            } else {
                statusDisplay.textContent = 'Overfunded';
                statusDisplay.className = 'badge bg-danger';
            }
        } else {
            // For custom amount split
            totalDisplay.textContent = baseCurrencySymbol + total.toFixed(2);
            
            // Update status
            if (Math.abs(total - totalAmount) < 0.01) {
                statusDisplay.textContent = 'Balanced';
                statusDisplay.className = 'badge bg-success';
            } else if (total < totalAmount) {
                statusDisplay.textContent = 'Underfunded';
                statusDisplay.className = 'badge bg-warning';
            } else {
                statusDisplay.textContent = 'Overfunded';
                statusDisplay.className = 'badge bg-danger';
            }
        }
    }
    
    /**
     * Add a new category split row 
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
        let categorySelect = document.getElementById('edit_category_id') || document.getElementById('category_id');
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
        const totalEl = document.getElementById('split_total') || document.getElementById('category_split_total');
        const targetEl = document.getElementById('transaction_total') || document.getElementById('category_split_target');
        const statusEl = document.getElementById('split_status') || document.getElementById('category_split_status');
        const dataInput = document.getElementById('category_splits_data');
        
        if (!totalEl || !dataInput) {
            console.error("Required elements not found for updating category split totals");
            return;
        }
        
        // Get total amount from form
        const totalAmount = parseFloat(document.getElementById('edit_amount')?.value || 
                                        document.getElementById('amount')?.value || 
                                        '0');
        
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
     * Helper function to get user name from ID
     */
    function getUserName(userId) {
        // Try to find in edit_paid_by select
        const paidBySelect = document.getElementById('edit_paid_by');
        if (paidBySelect) {
            const option = Array.from(paidBySelect.options).find(opt => opt.value === userId);
            if (option) return option.textContent;
        }
        
        // Try to find in edit_split_with select
        const splitWithSelect = document.getElementById('edit_split_with');
        if (splitWithSelect) {
            const option = Array.from(splitWithSelect.options).find(opt => opt.value === userId);
            if (option) return option.textContent;
        }
        
        // Fallback to using ID
        return userId;
    }
    
    /**
     * Submit form with AJAX
     */
    function submitForm(form) {
        if (!form) {
            console.error("Form element not found");
            return;
        }
        
        // Process form data with special handling for group defaults
        const formData = new FormData(form);
        
        // Check if we're using group default split method
        const splitMethod = formData.get('split_method');
        if (splitMethod === 'group_default') {
            const groupId = formData.get('group_id');
            
            // If we have a valid group and group data
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                
                // Get the actual method from the group data
                const actualMethod = groupData.defaultSplitMethod || 'equal';
                console.log("Using actual split method from group:", actualMethod);
                
                // Get the split details from the form
                let splitDetails = {};
                try {
                    const splitDetailsValue = document.getElementById('split_details')?.value;
                    if (splitDetailsValue) {
                        splitDetails = JSON.parse(splitDetailsValue);
                        
                        // Update the split details to use the actual method
                        splitDetails.type = actualMethod;
                        
                        // Update the hidden input
                        document.getElementById('split_details').value = JSON.stringify(splitDetails);
                        
                        console.log("Updated split details with actual method:", splitDetails);
                    }
                } catch (e) {
                    console.error("Error parsing split details:", e);
                }
            }
        }
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn?.innerHTML || 'Save Changes';
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
        }
        
        // Log the form data for debugging
        console.log("Form data being sent:");
        for (const [key, value] of formData.entries()) {
            console.log(`${key}: ${value}`);
        }
        
        // Submit the form
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
                showMessage(data.message || 'Transaction updated successfully!');
                
                // Close panel and refresh page
                closeSlidePanel('editTransactionPanel');
                
                // Reload page after a delay to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                throw new Error(data.message || 'Failed to update transaction');
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
     */
    function showMessage(message, type = 'success') {
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
            const toastId = `toast-${Date.now()}`;
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
window.EditTransactionModule = EditTransactionModule;