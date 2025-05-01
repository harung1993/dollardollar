/**
 * Enhanced Unified Transaction Module with Group Default Fix
 * For Dollar Dollar Bill Y'all Application
 */
const TransactionModule = (function() {
    // Private module variables
    let baseCurrencySymbol = '$';
    
    // Initialize the module
    function init() {
        // Set base currency symbol
        if (window.baseCurrencySymbol) {
            baseCurrencySymbol = window.baseCurrencySymbol;
        }
        
        console.log("TransactionModule initialized with currency symbol:", baseCurrencySymbol);
        
        // Set up global event listeners
        setupEventListeners();
        
        // Return public API
        return {
            openAddTransactionPanel,
            openEditTransactionPanel,
            closePanel: closeSlidePanel,
            showMessage,
            // Compatibility with transactions.js
            openEditForm: openEditTransactionPanel
        };
    }
    
    // Setup event listeners for transaction buttons
    function setupEventListeners() {
        // Click handler for add transaction button
        document.addEventListener('click', function(event) {
            const addBtn = event.target.closest('#openAddTransactionBtn');
            if (addBtn) {
                event.preventDefault();
                openAddTransactionPanel();
            }
        });
        
        // Click handler for edit expense buttons
        document.addEventListener('click', function(event) {
            const editBtn = event.target.closest('.edit-expense-btn');
            if (editBtn) {
                event.preventDefault();
                const expenseId = editBtn.getAttribute('data-expense-id');
                if (expenseId) {
                    openEditTransactionPanel(expenseId);
                }
            }
        });
        
        // Click handler for delete expense buttons
        document.addEventListener('click', function(event) {
            const deleteBtn = event.target.closest('.delete-expense-btn');
            if (deleteBtn) {
                event.preventDefault();
                const expenseId = deleteBtn.getAttribute('data-expense-id');
                if (expenseId && confirm('Are you sure you want to delete this transaction?')) {
                    deleteTransaction(expenseId);
                }
            }
        });
    }
    
    // Open panel to add a new transaction
    function openAddTransactionPanel(groupData) {
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
    
    // Setup the add transaction form
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
    
    // Open panel to edit an existing transaction
    function openEditTransactionPanel(expenseId) {
        console.log("Opening edit transaction panel for expense ID:", expenseId);
        
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
    
    // Setup the edit form
    function setupEditForm() {
        console.log("Setting up edit transaction form");
        
        // Setup transaction type change handlers
        setupEditTransactionTypeHandlers();
        
        // Setup personal expense toggle
        setupEditPersonalExpenseToggle();
        
        // Setup group selection change handler
        setupEditGroupChangeHandler();
        
        // Setup category split toggle
        const categorySplitToggle = document.getElementById('enable_category_split');
        if (categorySplitToggle) {
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
        }
        
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
        
        // Setup form submission
        const form = document.getElementById('editTransactionForm');
        if (form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                submitEditForm(form);
            });
        }
        
        // Setup split values toggle
        const splitValuesToggle = document.getElementById('edit_split_values_toggle');
        if (splitValuesToggle) {
            splitValuesToggle.addEventListener('click', function() {
                const container = document.getElementById('edit_split_values_container');
                if (container) {
                    const isVisible = !container.classList.contains('d-none');
                    container.classList.toggle('d-none', isVisible);
                    
                    // Initialize split values if showing
                    if (!isVisible) {
                        initializeEditSplitValues();
                    }
                }
            });
        }
        
        // Setup split method change handler
        setupEditSplitMethodChangeHandler();
        
        // If split method is not equal, show the split values container and initialize values
        const splitMethod = document.getElementById('edit_split_method')?.value;
        const splitValuesContainer = document.getElementById('edit_split_values_container');
        
        if (splitMethod && splitMethod !== 'equal' && splitValuesContainer) {
            splitValuesContainer.classList.remove('d-none');
            
            // Initialize split values
            setTimeout(() => {
                initializeEditSplitValues();
            }, 100);
        }
    }
    
    /**
     * Setup edit group change handler
     */
    function setupEditGroupChangeHandler() {
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
     * Setup edit split method change handler
     */
    function setupEditSplitMethodChangeHandler() {
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
                        initializeEditSplitValues();
                    }
                }
            }
        });
    }
    
    /**
     * Update display for group default split method - ENHANCED VERSION
     * This function correctly displays the actual split method from the group
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
        
        // Get actual split method
        const actualMethod = groupData.defaultSplitMethod || 'equal';
        
        // Update method display with capitalized method name
        displayElement.textContent = 'Group Default (' + actualMethod.charAt(0).toUpperCase() + actualMethod.slice(1) + ')';
        
        // Use a different badge color based on method type
        if (actualMethod === 'equal') {
            displayElement.className = 'badge bg-success';
        } else if (actualMethod === 'percentage') {
            displayElement.className = 'badge bg-info';
        } else {
            displayElement.className = 'badge bg-primary';
        }
        
        // Show/hide container based on actual method
        container.classList.toggle('d-none', actualMethod === 'equal');
        
        // Use group's default split values if available
        if (actualMethod !== 'equal' && 
            groupData.defaultSplitValues && 
            Object.keys(groupData.defaultSplitValues).length > 0 &&
            splitDetailsInput) {
            
            // Save group's default values
            const splitDetails = {
                type: actualMethod,
                values: groupData.defaultSplitValues
            };
            splitDetailsInput.value = JSON.stringify(splitDetails);
            
            // Initialize values in UI
            initializeEditSplitValues();
        }
    }
    
    // Initialize split values in edit form with improved group_default handling
    function initializeEditSplitValues() {
        console.log("Initializing edit split values");
        
        const splitMethodSelect = document.getElementById('edit_split_method');
        if (!splitMethodSelect) {
            console.error("Split method select element not found");
            return;
        }
        
        // Get selected split method
        let splitMethod = splitMethodSelect.value;
        console.log("Split method:", splitMethod);
        
        // Handle group_default method
        if (splitMethod === 'group_default') {
            const groupId = document.getElementById('edit_group_id')?.value;
            
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                splitMethod = groupData.defaultSplitMethod || 'equal';
                console.log("Using actual method from group:", splitMethod);
            } else {
                // Fallback to equal split if no group data
                splitMethod = 'equal';
                console.log("No group data, falling back to equal split");
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
    
    // Update split values display and hidden field
    function updateSplitValues(splitMethod, totalAmount) {
        console.log("Updating split values for method:", splitMethod);
        
        if (!totalAmount) {
            totalAmount = parseFloat(document.getElementById('edit_amount')?.value) || 
                          parseFloat(document.getElementById('amount')?.value) || 0;
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
        
        // Update split details
        const splitDetails = {
            type: splitMethod,
            values: values
        };
        
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
    
    // Setup transaction type handlers for add form
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
    
    // Update UI based on transaction type
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
    
    // Setup personal expense toggle for add form
    function setupPersonalExpenseToggle() {
        const personalExpenseCheck = document.getElementById('personal_expense');
        if (!personalExpenseCheck) return;
        
        personalExpenseCheck.addEventListener('change', function() {
            const isPersonal = this.checked;
            const splitSection = document.querySelector('.split-section');
            
            if (splitSection) {
                splitSection.classList.toggle('d-none', isPersonal);
            }
        });
        
        // Trigger change event to initialize state
        personalExpenseCheck.dispatchEvent(new Event('change'));
    }
    
    // Enhanced version of setupSplitMethodHandlers to better handle group defaults
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
            console.log("Split method changed to:", this.value);
            const method = this.value;
            
            // If "Group Default" is selected and a group is active
            if (method === 'group_default') {
                const groupId = document.getElementById('group_id')?.value;
                console.log("Group ID:", groupId);
                
                if (groupId && window.groupsData && window.groupsData[groupId]) {
                    const groupData = window.groupsData[groupId];
                    console.log("Group data found:", groupData);
                    
                    // Check if the group has a default split method
                    if (groupData.defaultSplitMethod) {
                        // Apply group's default split method logic
                        const actualMethod = groupData.defaultSplitMethod;
                        console.log("Actual split method:", actualMethod);
                        
                        // Update method display
                        const methodDisplay = document.getElementById('split_method_display');
                        if (methodDisplay) {
                            methodDisplay.textContent = 
                                actualMethod === 'equal' ? 'Group Default (Equal)' : 
                                actualMethod === 'percentage' ? 'Group Default (Percentage)' : 
                                'Group Default (Custom)';
                            console.log("Updated method display to:", methodDisplay.textContent);
                        } else {
                            console.warn("Method display element not found");
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
                                    console.error("Error parsing default split values:", e);
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
                                console.log("Set split details input with group defaults:", splitDetails);
                                
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
                        console.warn("No default split method found in group data");
                    }
                } else {
                    console.warn("No group data found for group ID:", groupId);
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
                    
                    // Initialize values if not equal
                    if (method !== 'equal' && !customSplitContainer.classList.contains('d-none')) {
                        updateSplitValueInputs(method);
                    }
                }
            }
        });
    }
    
    // Setup edit transaction type handlers
    function setupEditTransactionTypeHandlers() {
        const transactionTypes = document.querySelectorAll('input[name="transaction_type"]');
        
        transactionTypes.forEach(input => {
            input.addEventListener('change', function() {
                updateEditTransactionTypeUI(this.value);
            });
        });
        
        // Initialize UI based on selected type
        const selectedType = document.querySelector('input[name="transaction_type"]:checked')?.value || 'expense';
        updateEditTransactionTypeUI(selectedType);
    }
    
    // Update edit form UI based on transaction type
    function updateEditTransactionTypeUI(type) {
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
    
    // Setup personal expense toggle for edit form
    function setupEditPersonalExpenseToggle() {
        const personalExpenseCheck = document.getElementById('edit_personal_expense');
        if (!personalExpenseCheck) return;
        
        personalExpenseCheck.addEventListener('change', function() {
            personalExpenseToggled(this.checked);
        });
    }
    
    // Handle personal expense toggle change
    function personalExpenseToggled(isPersonal) {
        const splitSection = document.querySelector('.expense-split-section');
        if (splitSection) {
            splitSection.style.display = isPersonal ? 'none' : 'block';
        }
    }

    function updateSplitValueInputs(forcedMethod) {
        const splitMethodSelect = document.getElementById('split_method');
        if (!splitMethodSelect) {
            console.error("Split method select not found");
            return;
        }
        
        // Get selected split method or use forced method if provided
        let splitMethod = forcedMethod || splitMethodSelect.value;
        console.log("Updating split values for method:", splitMethod);
        
        // Handle group_default by getting actual method from group
        if (splitMethod === 'group_default') {
            const groupId = document.getElementById('group_id')?.value;
            console.log("Group ID for group_default:", groupId);
            
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                const groupData = window.groupsData[groupId];
                splitMethod = groupData.defaultSplitMethod || 'equal';
                console.log("Using actual method from group:", splitMethod);
            } else {
                splitMethod = 'equal';
                console.log("No group data found, falling back to equal");
            }
        }
        
        // Skip if equal split since we don't need to show/initialize split values
        if (splitMethod === 'equal') {
            console.log("Equal split - nothing to initialize");
            return;
        }
        
        // Get container and required form elements
        const container = document.getElementById('split_values_container');
        const totalAmount = parseFloat(document.getElementById('amount').value) || 0;
        const paidById = document.getElementById('paid_by').value;
        const splitDetailsInput = document.getElementById('split_details');
        
        if (!container || !splitDetailsInput) {
            console.error("Required elements not found");
            return;
        }
        
        // Clear container
        container.innerHTML = '';
        
        // Get selected users
        const splitWithSelect = document.getElementById('split_with');
        if (!splitWithSelect) {
            console.error("Split with select not found");
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
        
        console.log("All participants:", allParticipants);
        
        // Try to get existing values if available
        let splitValues = {};
        try {
            if (splitDetailsInput.value) {
                const details = JSON.parse(splitDetailsInput.value);
                if (details && details.values) {
                    splitValues = details.values;
                    console.log("Found existing split values:", splitValues);
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
                
                console.log(`User ${userName}: ${percentage}%`);
                
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
                
                console.log(`User ${userName}: ${amount.toFixed(2)}`);
                
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
        console.log("Updated split details:", splitDetails);
        
        // Update totals
        updateSplitTotals(splitMethod, totalAmount);
    }
    
    // Update split totals display
    function updateSplitTotals(splitMethod, totalAmount) {
        if (!totalAmount) {
            totalAmount = parseFloat(document.getElementById('amount')?.value) || 0;
        }
        
        const totalEl = document.getElementById('split_values_total');
        const statusEl = document.getElementById('split_status');
        const splitDetailsInput = document.getElementById('split_details');
        
        if (!totalEl || !statusEl || !splitDetailsInput) {
            console.error("Required elements not found for updating split totals");
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
    
    // Apply group defaults to the add form
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
                    // Use capitalized method name for better readability
                    const methodDisplayText = 'Group Default (' + 
                        groupData.defaultSplitMethod.charAt(0).toUpperCase() + 
                        groupData.defaultSplitMethod.slice(1) + ')';
                    
                    methodDisplay.textContent = methodDisplayText;
                    
                    // Use color to indicate method type
                    if (groupData.defaultSplitMethod === 'equal') {
                        methodDisplay.className = 'badge bg-success';
                    } else if (groupData.defaultSplitMethod === 'percentage') {
                        methodDisplay.className = 'badge bg-info';
                    } else {
                        methodDisplay.className = 'badge bg-primary';
                    }
                }
                
                // Apply default split values if they exist and it's not an equal split
                if (groupData.defaultSplitMethod !== 'equal' && 
                    groupData.defaultSplitValues && 
                    Object.keys(groupData.defaultSplitValues).length > 0) {
                    
                    // Create split details from defaults
                    const splitDetailsInput = document.getElementById('split_details');
                    if (splitDetailsInput) {
                        // Handle whether defaultSplitValues is a string or object
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
                        console.log("Applied default split values:", splitDetails);
                        
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
    
    // Setup category split toggle
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
    
    // Add a category split row to the form
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
    
    // Update category split totals display and data
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
    
    // Get user name from ID
    function getUserName(userId) {
        // Try to find in edit paid_by select first, then regular paid_by
        const paidBySelect = document.getElementById('edit_paid_by') || document.getElementById('paid_by');
        if (paidBySelect) {
            const option = Array.from(paidBySelect.options).find(opt => opt.value === userId);
            if (option) return option.textContent;
        }
        
        // Try to find in split_with select
        const splitWithSelect = document.getElementById('edit_split_with') || document.getElementById('split_with');
        if (splitWithSelect) {
            const option = Array.from(splitWithSelect.options).find(opt => opt.value === userId);
            if (option) return option.textContent;
        }
        
        // Fallback to using ID
        return userId;
    }
    
    // Submit add transaction form
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
    
    // Submit edit transaction form
    function submitEditForm(form) {
        if (!form) {
            console.error("Edit form element not found");
            return;
        }
        
        const formData = new FormData(form);
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn?.innerHTML || 'Save Changes';
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
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
    
    // Delete a transaction
    \function deleteTransaction(expenseId) {
        // Check if transactions.js is active and handling deletion
        if (typeof window.deleteExpense === 'function') {
            // Let transactions.js handle it
            window.deleteExpense(expenseId);
            return;
        }
        
        // If not, use our own implementation
        fetch(`/delete_expense/${expenseId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('Transaction deleted successfully');
                
                // Remove row or reload page
                const row = document.querySelector(`tr[data-expense-id="${expenseId}"]`);
                if (row) {
                    row.style.opacity = '0.5';
                    row.style.backgroundColor = 'rgba(220, 53, 69, 0.1)';
                    
                    setTimeout(() => {
                        row.remove();
                    }, 300);
                } else {
                    // If row not found, reload the page
                    window.location.reload();
                }
            } else {
                throw new Error(data.message || 'Failed to delete transaction');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage(error.message, 'error');
        });
    }
    
    // Open a slide panel
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
    
    // Close a slide panel
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
    
    // Show a message toast
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
    
    // Compatibility with transactions.js
    // This function ensures smooth integration with existing code
    function setupTransactionsJsCompatibility() {
        // Add compatibility with how transactions.js expects to interact
        // with the transaction module
        if (window.TransactionModule) {
            // Ensure openEditForm alias exists
            if (!window.TransactionModule.openEditForm && window.TransactionModule.openEditTransactionPanel) {
                window.TransactionModule.openEditForm = window.TransactionModule.openEditTransactionPanel;
            }
            
            // Add a global utility function for formatting split methods
            window.formatSplitMethod = function(methodName, groupId) {
                // For group_default, look up the actual method
                if (methodName === 'group_default') {
                    if (groupId && window.groupsData && window.groupsData[groupId]) {
                        const actualMethod = window.groupsData[groupId].defaultSplitMethod || 'equal';
                        return `Group Default (${actualMethod.charAt(0).toUpperCase() + actualMethod.slice(1)})`;
                    }
                    return 'Group Default';
                }
                
                // For regular methods, just capitalize
                return methodName.charAt(0).toUpperCase() + methodName.slice(1);
            }
        }
    }
    
    // Call the compatibility setup
    setupTransactionsJsCompatibility();
    
    // Return public API
    return init();
})();

// Make the module available globally
window.TransactionModule = TransactionModule;

// Add an additional enhancement to fix group_default display in existing transactions
document.addEventListener('DOMContentLoaded', function() {
    // Find all elements that might show split method
    document.querySelectorAll('.split-method-display, .mb-1').forEach(element => {
        const text = element.textContent;
        if (text && text.toLowerCase().includes('group_default')) {
            // Try to find the group ID
            let groupId = null;
            
            // Check for data attribute
            if (element.hasAttribute('data-group-id')) {
                groupId = element.getAttribute('data-group-id');
            }
            
            // Or check parent elements
            if (!groupId) {
                const row = element.closest('tr[data-expense-id]');
                if (row && row.hasAttribute('data-group-id')) {
                    groupId = row.getAttribute('data-group-id');
                }
            }
            
            if (groupId && window.groupsData && window.groupsData[groupId]) {
                // Get the actual method used by the group
                const groupData = window.groupsData[groupId];
                const actualMethod = groupData.defaultSplitMethod || 'equal';
                const methodDisplayText = `Group Default (${actualMethod.charAt(0).toUpperCase() + actualMethod.slice(1)})`;
                
                // Update the element text
                if (text.startsWith('Split:')) {
                    element.textContent = `Split: ${methodDisplayText}`;
                } else {
                    element.textContent = methodDisplayText;
                }
            }
        }
    });
});