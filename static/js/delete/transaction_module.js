/**
 * Optimized Transaction Module
 * 
 * A consolidated module that handles both adding and editing transactions
 * with improved handling of split functionality.
 */

const TransactionModule = (function() {
  // Private variables
  let baseCurrencySymbol = '$'; // Default fallback
  
  /**
   * Initialize the module and set up global event handlers
   */
  function init() {
    // Set base currency symbol from various potential sources
    initializeCurrencySymbol();
    
    // Setup global event delegation
    setupGlobalEventHandlers();
    
    // Initialize multi-select styles
    addMultiSelectStyles();
    
    // Return public API
    return {
      openAddTransactionPanel,
      openEditTransactionPanel,
      closeSlidePanel,
      enhanceMultiSelects
    };
  }
  
  /**
   * Initialize the currency symbol from various sources
   */
  function initializeCurrencySymbol() {
    // Try window object first (set in template)
    if (window.baseCurrencySymbol) {
      baseCurrencySymbol = window.baseCurrencySymbol;
      return;
    }
    
    // Try data attribute
    const currencyDataEl = document.getElementById('currency-data');
    if (currencyDataEl && currencyDataEl.getAttribute('data-symbol')) {
      baseCurrencySymbol = currencyDataEl.getAttribute('data-symbol');
      return;
    }
    
    // Try meta tag
    const metaTag = document.querySelector('meta[name="base-currency-symbol"]');
    if (metaTag && metaTag.content) {
      baseCurrencySymbol = metaTag.content;
      return;
    }
    
    console.warn("Could not find base currency symbol, using default: $");
  }
  
  /**
   * Set up global event handlers using event delegation
   */
  function setupGlobalEventHandlers() {
    // Handle clicks on edit/add buttons
    document.addEventListener('click', function(e) {
      // Edit expense button click
      if (e.target.closest('.edit-expense-btn')) {
        const button = e.target.closest('.edit-expense-btn');
        const expenseId = button.getAttribute('data-expense-id');
        if (expenseId) {
          openEditTransactionPanel(expenseId);
        }
      }
      
      // Add transaction button click
      else if (e.target.closest('#openAddTransactionBtn')) {
        openAddTransactionPanel();
      }
      
      // Category split toggle click
      else if (e.target.closest('.split-toggle')) {
        const toggle = e.target.closest('.split-toggle');
        const expenseId = toggle.getAttribute('data-expense-id');
        handleSplitToggleClick(toggle, expenseId);
      }
    });
  }
  
  /**
   * Opens the Add Transaction panel
   */
  function openAddTransactionPanel() {
    console.log("Opening Add Transaction Panel");
    
    // Create slide panel first
    const panel = openSlidePanel('addTransactionPanel', {
      title: 'Add New Transaction',
      icon: 'fa-plus',
      iconColor: '#0ea5e9'
    });
    
    // Then fetch the form contents
    fetch('/get_transaction_form_html')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.text();
      })
      .then(html => {
        const contentDiv = panel.querySelector('.slide-panel-content');
        if (contentDiv) {
          contentDiv.innerHTML = html;
          
          // Use a timeout to ensure DOM is fully processed
          setTimeout(() => {
            // Set today's date as default
            const dateInput = document.getElementById('date');
            if (dateInput && !dateInput.value) {
              dateInput.value = new Date().toISOString().split('T')[0];
            }
            
            // Initialize transaction type handler
            setupTransactionTypeHandler('transaction_type', true);
            
            // Enhance multi-select for split_with
            enhanceMultiSelects('#split_with');
            
            // Setup handlers for rest of the form
            setupFormEventListeners(true);
            
          }, 50);
        }
      })
      .catch(error => {
        console.error('Error loading form:', error);
        showMessage(`Error loading transaction form: ${error.message}`, 'error');
        closeSlidePanel('addTransactionPanel');
      });
  }
  
  /**
   * Opens the Edit Transaction panel
   */
  function openEditTransactionPanel(expenseId) {
    if (!expenseId) {
      console.error('No expense ID provided for editing');
      return;
    }
    
    console.log(`Opening edit panel for expense ID: ${expenseId}`);
    
    // Create slide panel first
    const panel = openSlidePanel('editTransactionPanel', {
      title: 'Edit Transaction',
      icon: 'fa-edit',
      iconColor: '#0ea5e9'
    });
    
    // Then fetch the form contents
    fetch(`/get_expense_edit_form/${expenseId}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.text();
      })
      .then(html => {
        const contentDiv = panel.querySelector('.slide-panel-content');
        if (contentDiv) {
          contentDiv.innerHTML = html;
          
          // Use a timeout to ensure DOM is fully processed
          setTimeout(() => {
            // Initialize transaction type handler
            setupTransactionTypeHandler('edit_transaction_type', false);
            
            // Enhance multi-select for split_with
            enhanceMultiSelects('#edit_split_with');
            
            // Setup handlers for rest of the form
            setupFormEventListeners(false);
            
            // Setup category splits if needed
            setupCategorySplits();
            
            // Setup form submission
            const editForm = document.getElementById('editTransactionForm');
            if (editForm) {
              editForm.addEventListener('submit', function(e) {
                e.preventDefault();
                submitEditTransactionForm(this, expenseId);
              });
            }
          }, 50);
        }
      })
      .catch(error => {
        console.error('Error loading edit form:', error);
        showMessage(`Error loading transaction form: ${error.message}`, 'error');
        closeSlidePanel('editTransactionPanel');
      });
  }
  
  /**
   * Set up transaction type change handler
   */
  function setupTransactionTypeHandler(selectId, isAddForm) {
    const transactionTypeSelect = document.getElementById(selectId);
    if (!transactionTypeSelect) return;
    
    const prefix = isAddForm ? '' : 'edit_';
    
    transactionTypeSelect.addEventListener('change', function() {
      const transactionType = this.value;
      const expenseOnlyFields = document.querySelectorAll(`.${prefix}expense-only-fields`);
      const toAccountContainer = document.getElementById(`${prefix}to_account_container`);
      const accountLabel = document.getElementById(`${prefix}account_label`);
      
      // Show/hide fields based on transaction type
      if (transactionType === 'expense') {
        // Show splitting options for expenses
        expenseOnlyFields.forEach(el => el.style.display = 'block');
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
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
        
        // Show destination account for transfers
        if (toAccountContainer) toAccountContainer.style.display = 'block';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'From Account';
      }
    });
    
    // Initialize UI based on current selection
    transactionTypeSelect.dispatchEvent(new Event('change'));
  }
  
  /**
   * Setup all form event listeners
   */
  function setupFormEventListeners(isAddForm) {
    const prefix = isAddForm ? '' : 'edit_';
    
    // Personal expense toggle
    const personalExpenseCheck = document.getElementById(`${prefix}personal_expense`);
    if (personalExpenseCheck) {
      personalExpenseCheck.addEventListener('change', function() {
        togglePersonalExpense(prefix);
      });
      
      // Initialize UI based on current state
      togglePersonalExpense(prefix);
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById(`${prefix}split_method`);
    if (splitMethodSelect) {
      splitMethodSelect.addEventListener('change', function() {
        toggleSplitOptions(prefix);
      });
      
      // Initialize UI based on current selection
      toggleSplitOptions(prefix);
    }
    
    // Amount field change handler
    const amountField = document.getElementById(`${prefix}amount`);
    if (amountField) {
      amountField.addEventListener('input', function() {
        // Only update split values if a split method is selected
        const splitMethod = document.getElementById(`${prefix}split_method`)?.value;
        if (splitMethod && splitMethod !== 'equal') {
          updateSplitValues(prefix);
        }
        
        // If using category splits, update those totals too
        if (prefix === 'edit_' && document.getElementById('enable_category_split')?.checked) {
          updateSplitTotals();
        }
      });
    }
    
    // Paid by change handler
    const paidBySelect = document.getElementById(`${prefix}paid_by`);
    if (paidBySelect) {
      paidBySelect.addEventListener('change', function() {
        // Auto-select the paid by user if needed
        autoSelectPaidByUser(prefix);
        
        // Only update split values if a split method is selected
        const splitMethod = document.getElementById(`${prefix}split_method`)?.value;
        if (splitMethod && splitMethod !== 'equal') {
          updateSplitValues(prefix);
        }
      });
    }
    
    // Split with change handler
    const splitWithSelect = document.getElementById(`${prefix}split_with`);
    if (splitWithSelect) {
      splitWithSelect.addEventListener('change', function() {
        // Only update split values if a split method is selected
        const splitMethod = document.getElementById(`${prefix}split_method`)?.value;
        if (splitMethod && splitMethod !== 'equal') {
          updateSplitValues(prefix);
        }
      });
    }
    
    // Setup add form submission if needed
    if (isAddForm) {
      const form = document.getElementById('newTransactionForm');
      if (form) {
        form.addEventListener('submit', function(e) {
          e.preventDefault();
          submitAddTransactionForm(this);
        });
      }
    }
  }
  
  /**
   * Toggle personal expense mode
   */
  function togglePersonalExpense(prefix) {
    const personalExpenseCheck = document.getElementById(`${prefix}personal_expense`);
    if (!personalExpenseCheck) return;
    
    const splitWithSelect = document.getElementById(`${prefix}split_with`);
    const splitMethodContainer = document.getElementById(`${prefix}split_method`)?.parentNode;
    const customSplitContainer = document.getElementById(`${prefix}custom_split_container`);
    
    if (personalExpenseCheck.checked) {
      // This is a personal expense - disable split options
      if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
      if (customSplitContainer) customSplitContainer.style.display = 'none';
      
      // Clear any existing split_with selections
      if (splitWithSelect) {
        for (let i = 0; i < splitWithSelect.options.length; i++) {
          splitWithSelect.options[i].selected = false;
        }
        splitWithSelect.disabled = true;
        
        // Handle enhanced multi-select container if present
        const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
        if (customMultiSelect) {
          customMultiSelect.style.opacity = '0.5';
          customMultiSelect.style.pointerEvents = 'none';
        } else {
          // Fallback to parent element
          splitWithSelect.parentNode.style.opacity = '0.5';
        }
        
        // Trigger change event to update UI
        splitWithSelect.dispatchEvent(new Event('change'));
      }
    } else {
      // This is a shared expense - enable split options
      if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
      
      if (splitWithSelect) {
        splitWithSelect.disabled = false;
        
        // Handle enhanced multi-select container if present
        const customMultiSelect = splitWithSelect.closest('.custom-multi-select-container');
        if (customMultiSelect) {
          customMultiSelect.style.opacity = '1';
          customMultiSelect.style.pointerEvents = 'auto';
        } else {
          // Fallback to parent element
          splitWithSelect.parentNode.style.opacity = '1';
        }
        
        // Auto-select the paid by user
        autoSelectPaidByUser(prefix);
        
        // Trigger change event to update UI
        splitWithSelect.dispatchEvent(new Event('change'));
      }
      
      // Show custom split container if needed
      const splitMethodSelect = document.getElementById(`${prefix}split_method`);
      if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
        customSplitContainer.style.display = 'block';
        
        // Update the split values
        updateSplitValues(prefix);
      }
    }
  }
  
  /**
   * Toggle split options based on method
   */
  function toggleSplitOptions(prefix) {
    const splitMethodSelect = document.getElementById(`${prefix}split_method`);
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    const customSplitContainer = document.getElementById(`${prefix}custom_split_container`);
    const personalExpenseCheck = document.getElementById(`${prefix}personal_expense`);
    
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
      updateSplitValues(prefix);
    }
  }
  
  /**
   * Auto-select the paid by user in the split with dropdown
   */
  function autoSelectPaidByUser(prefix) {
    const paidBySelect = document.getElementById(`${prefix}paid_by`);
    const splitWithSelect = document.getElementById(`${prefix}split_with`);
    
    if (!paidBySelect || !splitWithSelect) return;
    
    const paidById = paidBySelect.value;
    if (!paidById) return;
    
    // If there are no existing selections yet
    if (Array.from(splitWithSelect.selectedOptions).length === 0) {
      // Find the option for the paid by user and select it
      for (let i = 0; i < splitWithSelect.options.length; i++) {
        if (splitWithSelect.options[i].value === paidById) {
          splitWithSelect.options[i].selected = true;
          // Trigger change event to update any UI components
          splitWithSelect.dispatchEvent(new Event('change'));
          break;
        }
      }
    }
  }
  
  /**
   * Update split values UI with proper handling
   */
  function updateSplitValues(prefix) {
    const splitMethodSelect = document.getElementById(`${prefix}split_method`);
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById(`${prefix}personal_expense`);
    if (personalExpenseCheck && personalExpenseCheck.checked) return;
    
    const amountInput = document.getElementById(`${prefix}amount`);
    const paidBySelect = document.getElementById(`${prefix}paid_by`);
    const splitWithSelect = document.getElementById(`${prefix}split_with`);
    const splitTotalEl = document.getElementById(`${prefix}split_total`);
    const splitValuesContainer = document.getElementById(`${prefix}split_values_container`);
    const splitDetailsInput = document.getElementById(`${prefix}split_details`);
    const splitStatusEl = document.getElementById(`${prefix}split_status`);
    
    if (!amountInput || !paidBySelect || !splitWithSelect || !splitTotalEl || !splitValuesContainer) {
      console.warn("Missing required elements for split values");
      return;
    }
    
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
    
    // Try to retrieve existing split values from the hidden input
    let existingSplitValues = {};
    if (splitDetailsInput && splitDetailsInput.value) {
      try {
        const splitDetails = JSON.parse(splitDetailsInput.value);
        if (splitDetails && splitDetails.values) {
          existingSplitValues = splitDetails.values;
          console.log("Loaded existing split values:", existingSplitValues);
        }
      } catch (e) {
        console.warn('Could not parse existing split details', e);
      }
    }
    
    // Clear the container and prepare to build the UI
    splitValuesContainer.innerHTML = '';
    let splitValues = {};
    
    if (splitMethod === 'percentage') {
      // For percentage split
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
          .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        
        // Use existing value if available, otherwise fair distribution
        let userPercentage;
        if (existingSplitValues[userId] !== undefined) {
          userPercentage = existingSplitValues[userId];
        } else {
          // For payer, default to smaller percentage if not set
          if (isPayerId && allParticipantIds.length > 1) {
            userPercentage = 0;
          } else {
            // Otherwise distribute equally
            userPercentage = allParticipantIds.length > 0 ? 
              (100 / allParticipantIds.length) : 100;
          }
        }
        
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
                value="${userPercentage.toFixed(1)}">
              <span class="input-group-text bg-dark text-light">%</span>
            </div>
          </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Save the initial value
        splitValues[userId] = userPercentage;
      });
    } else { // Custom amount
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
          .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        
        // Determine the default amount to show:
        // 1. Use existing value if available
        // 2. If this is the payer, default to 0 (they're paying for others)
        // 3. Otherwise, calculate a fair share among non-payers
        let userAmount;
        if (existingSplitValues[userId] !== undefined) {
          userAmount = existingSplitValues[userId];
        } else if (isPayerId) {
          userAmount = 0;
        } else {
          // Calculate fair share for non-payers
          const nonPayerIds = allParticipantIds.filter(id => id !== paidById);
          userAmount = nonPayerIds.length > 0 ? (totalAmount / nonPayerIds.length) : totalAmount;
        }
        
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
                value="${userAmount.toFixed(2)}">
            </div>
          </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Save the initial value
        splitValues[userId] = userAmount;
      });
    }
    
    // Add event listeners to inputs
    document.querySelectorAll(`#${prefix}split_values_container .split-value-input`).forEach(input => {
      input.addEventListener('input', function() {
        const userId = this.getAttribute('data-user-id');
        const value = parseFloat(this.value) || 0;
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
        } else { // Custom amount
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
        
        // Update hidden split details field
        const splitDetails = {
          type: splitMethod,
          values: splitValues
        };
        splitDetailsInput.value = JSON.stringify(splitDetails);
        console.log("Updated split details:", splitDetails);
      });
      
      // Trigger input event to initialize UI
      input.dispatchEvent(new Event('input'));
    });
  }
  
  /**
   * Setup category splits functionality
   */
  function setupCategorySplits() {
    // Find the enable category split checkbox
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    
    if (!enableCategorySplitCheck || !categorySplitsContainer) return;
    
    // Setup toggle handler
    enableCategorySplitCheck.addEventListener('change', function() {
      const isChecked = this.checked;
      
      // Show/hide splits container
      categorySplitsContainer.style.display = isChecked ? 'block' : 'none';
      
      if (isChecked) {
        categorySplitsContainer.classList.add('visible');
        categorySplitsContainer.classList.remove('hidden');
      } else {
        categorySplitsContainer.classList.add('hidden');
        categorySplitsContainer.classList.remove('visible');
      }
      
      // Disable/enable main category field
      const categorySelect = document.getElementById('edit_category_id');
      if (categorySelect) {
        categorySelect.disabled = isChecked;
        categorySelect.parentElement.classList.toggle('opacity-50', isChecked);
      }
      
      // Initialize splits if enabling
      if (isChecked) {
        // Clear existing splits
        const categorySpitsList = document.getElementById('category_splits_list');
        if (categorySpitsList) {
          categorySpitsList.innerHTML = '';
        }
        
        // Add a new split with the full amount
        const amountInput = document.getElementById('edit_amount');
        const totalAmount = parseFloat(amountInput?.value) || 0;
        addCategorySplit(null, totalAmount);
        updateSplitTotals();
      } else {
        // Clear split data when disabling
        const categorySplitsData = document.getElementById('category_splits_data');
        if (categorySplitsData) {
          categorySplitsData.value = '';
        }
      }
    });
    
    // Make sure initial display state is correct
    if (enableCategorySplitCheck.checked) {
      categorySplitsContainer.style.display = 'block';
      categorySplitsContainer.classList.add('visible');
      categorySplitsContainer.classList.remove('hidden');
      
      // Disable main category select
      const categorySelect = document.getElementById('edit_category_id');
      if (categorySelect) {
        categorySelect.disabled = true;
        categorySelect.parentElement.classList.add('opacity-50');
      }
      
      // Initialize splits from existing data if available
      const categorySplitsData = document.getElementById('category_splits_data');
      if (categorySplitsData && categorySplitsData.value) {
        try {
          const splitData = JSON.parse(categorySplitsData.value);
          
          if (Array.isArray(splitData) && splitData.length > 0) {
            // Clear existing splits first
            const categorySpitsList = document.getElementById('category_splits_list');
            if (categorySpitsList) {
              categorySpitsList.innerHTML = '';
            }
            
            // Create a split row for each item
            splitData.forEach(split => {
              addCategorySplit(split.category_id, split.amount);
            });
            
            updateSplitTotals();
          }
        } catch (e) {
          console.error("Error parsing split data:", e);
        }
      }
    }
    
    // Setup add split button
    const addSplitBtn = document.getElementById('add_split_btn');
    if (addSplitBtn) {
      addSplitBtn.addEventListener('click', function() {
        addCategorySplit(null, 0);
        updateSplitTotals();
      });
    }
  }
  
  /**
   * Add a category split row with optional category and amount
   */
  function addCategorySplit(categoryId, amount) {
    const splitsList = document.getElementById('category_splits_list');
    if (!splitsList) return;
    
    const splitId = Date.now(); // Unique ID for this split
    
    const splitRow = document.createElement('div');
    splitRow.className = 'row mb-3 split-row';
    splitRow.dataset.splitId = splitId;
    
    // Create the split row HTML
    splitRow.innerHTML = `
      <div class="col-md-5">
        <select class="form-select bg-dark text-light split-category" data-split-id="${splitId}">
          <option value="">Select category</option>
          ${document.getElementById('edit_category_id')?.innerHTML || ''}
        </select>
      </div>
      <div class="col-md-5">
        <div class="input-group">
          <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
          <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                data-split-id="${splitId}" value="${amount.toFixed(2)}">
        </div>
      </div>
      <div class="col-md-2">
        <button type="button" class="btn btn-outline-danger remove-split" data-split-id="${splitId}">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;
    
    splitsList.appendChild(splitRow);
    
    // Add event listeners
    const amountInput = splitRow.querySelector('.split-amount');
    if (amountInput) {
      amountInput.addEventListener('input', updateSplitTotals);
    }
    
    const categorySelect = splitRow.querySelector('.split-category');
    if (categorySelect) {
      categorySelect.addEventListener('change', updateSplitTotals);
      
      // Set the category if provided
      if (categoryId) {
        categorySelect.value = categoryId;
      }
    }
    
    const removeButton = splitRow.querySelector('.remove-split');
    if (removeButton) {
      removeButton.addEventListener('click', function() {
        splitRow.remove();
        updateSplitTotals();
      });
    }
    
    return splitRow;
  }
  
  /**
   * Update split totals and validate
   */
  function updateSplitTotals() {
    const transactionTotal = parseFloat(document.getElementById('edit_amount')?.value) || 0;
    let splitTotal = 0;
    let allCategoriesSelected = true;
    
    // Calculate sum of all splits
    const splitRows = document.querySelectorAll('.split-row');
    
    // Don't validate if there are no splits
    if (splitRows.length === 0) {
      return;
    }
    
    splitRows.forEach(row => {
      // Add up amount
      const amountInput = row.querySelector('.split-amount');
      splitTotal += parseFloat(amountInput?.value) || 0;
      
      // Check if category is selected
      const categorySelect = row.querySelector('.split-category');
      if (!categorySelect?.value) {
        allCategoriesSelected = false;
      }
    });
    
    // Update UI
    const splitTotalEl = document.getElementById('split_total');
    const transactionTotalEl = document.getElementById('transaction_total');
    
    if (splitTotalEl) splitTotalEl.textContent = splitTotal.toFixed(2);
    if (transactionTotalEl) transactionTotalEl.textContent = transactionTotal.toFixed(2);
    
    // Validate total
    const statusEl = document.getElementById('split_status');
    if (statusEl) {
      if (Math.abs(splitTotal - transactionTotal) < 0.01) {
        statusEl.textContent = allCategoriesSelected ? 'Balanced' : 'Select Categories';
        statusEl.className = allCategoriesSelected ? 'badge bg-success' : 'badge bg-warning';
      } else if (splitTotal < transactionTotal) {
        statusEl.textContent = 'Underfunded';
        statusEl.className = 'badge bg-warning';
      } else {
        statusEl.textContent = 'Overfunded';
        statusEl.className = 'badge bg-danger';
      }
    }
    
    // Update hidden input with split data
    const splitData = [];
    splitRows.forEach(row => {
      const categorySelect = row.querySelector('.split-category');
      const amountInput = row.querySelector('.split-amount');
      
      if (categorySelect && amountInput) {
        const categoryId = categorySelect.value;
        const amount = parseFloat(amountInput.value) || 0;
        
        if (categoryId && amount > 0) {
          splitData.push({
            category_id: categoryId,
            amount: amount
          });
        }
      }
    });
    
    const categorySplitsDataEl = document.getElementById('category_splits_data');
    if (categorySplitsDataEl) {
      categorySplitsDataEl.value = JSON.stringify(splitData);
    }
  }
  
  /**
   * Handle split toggle click in transaction list
   */
  function handleSplitToggleClick(toggle, expenseId) {
    if (!toggle || !expenseId) return;
    
    // Find detail element
    const detailElement = document.getElementById(`split-categories-${expenseId}`);
    if (!detailElement) {
      console.error(`Detail element not found for expense ID: ${expenseId}`);
      return;
    }
    
    // Toggle visibility
    const isHidden = detailElement.style.display === 'none' || !detailElement.style.display;
    detailElement.style.display = isHidden ? 'block' : 'none';
    
    // Update icon
    const icon = toggle.querySelector('i');
    if (icon) {
      if (isHidden) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
      } else {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
      }
    }
    
    // Load data if necessary
    if (isHidden) {
      // Check if we need to load data
      if (detailElement.querySelector('.loading') || detailElement.innerHTML.trim() === '') {
        loadCategorySplits(expenseId, detailElement);
      }
    }
  }
  
  /**
   * Load category splits via AJAX
   */
  function loadCategorySplits(expenseId, detailElement) {
    detailElement.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin me-2"></i>Loading split details...</div>';
    
    fetch(`/get_category_splits/${expenseId}`)
      .then(response => response.json())
      .then(data => {
        if (data.success && data.splits && data.splits.length > 0) {
          // Create split detail UI
          let html = '<div class="list-group list-group-flush bg-dark">';
          
          data.splits.forEach(split => {
            // Get category details
            const categoryName = split.category?.name || 'Unknown';
            const categoryColor = split.category?.color || '#6c757d';
            const categoryIcon = split.category?.icon || 'fa-tag';
            const amount = parseFloat(split.amount) || 0;
            
            html += `
              <div class="list-group-item py-2 bg-dark border-secondary">
                <div class="d-flex justify-content-between align-items-center">
                  <div class="debug-category-name" style="color: white !important;">
                    <span class="badge me-2" style="background-color: ${categoryColor};">
                      <i class="fas ${categoryIcon}"></i>
                    </span>
                    <span class="text-white" style="color: white !important;">${categoryName}</span>
                  </div>
                  <span class="badge bg-info">
                    ${baseCurrencySymbol}${amount.toFixed(2)}
                  </span>
                </div>
              </div>
            `;
          });
          
          html += '</div>';
          detailElement.innerHTML = html;
          
          // Apply CSS fix to ensure white text is visible
          const style = document.createElement('style');
          style.textContent = `
            #split-categories-${expenseId} .list-group-item * {
              color: white !important;
            }
          `;
          document.head.appendChild(style);
          
        } else {
          detailElement.innerHTML = '<div class="text-muted p-2">No category splits found</div>';
        }
      })
      .catch(error => {
        console.error('Error loading category splits:', error);
        detailElement.innerHTML = '<div class="text-danger p-2">Error loading splits</div>';
      });
  }
  
  /**
   * Submit add transaction form
   */
  function submitAddTransactionForm(form) {
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding...';
    }
    
    // Create FormData from the form
    const formData = new FormData(form);
    
    // Validate form data and ensure proper split details
    ensureSplitDetails(formData, '');
    
    // Send AJAX request
    fetch(form.action, {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to add transaction');
      }
      return response.text();
    })
    .then(() => {
      // Success - close panel and reload
      closeSlidePanel('addTransactionPanel');
      showMessage('Transaction added successfully');
      
      // Reload the page after a short delay
      setTimeout(() => {
        window.location.reload();
      }, 500);
    })
    .catch(error => {
      console.error('Error:', error);
      showMessage(`Error adding transaction: ${error.message}`, 'error');
      
      // Reset button state
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Add Transaction';
      }
    });
  }
  
  /**
   * Submit edit transaction form
   */
  function submitEditTransactionForm(form, expenseId) {
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    }
    
    // Create FormData from the form
    const formData = new FormData(form);
    
    // Set expenseId as a parameter in case it's needed
    formData.set('expense_id', expenseId);
    
    // Validate form data and ensure proper split details
    ensureSplitDetails(formData, 'edit_');
    
    // Handle category splits
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    if (enableCategorySplitCheck) {
      if (enableCategorySplitCheck.checked) {
        formData.set('enable_category_split', 'on');
        
        // Ensure category_splits_data is valid JSON
        const categorySplitsData = document.getElementById('category_splits_data');
        if (categorySplitsData && categorySplitsData.value) {
          try {
            // Validate it's proper JSON
            JSON.parse(categorySplitsData.value);
          } catch (e) {
            console.error("Invalid category splits data:", e);
            
            // Reset to empty array if invalid
            formData.set('category_splits_data', '[]');
          }
        } else {
          // Ensure we have at least an empty array
          formData.set('category_splits_data', '[]');
        }
      } else {
        // Make sure we remove the parameter if not checked
        formData.delete('enable_category_split');
      }
    }
    
    // Send AJAX request
    fetch(`/update_expense/${expenseId}`, {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to update transaction');
      }
      return response.text();
    })
    .then(() => {
      // Success - close panel and reload
      closeSlidePanel('editTransactionPanel');
      showMessage('Transaction updated successfully');
      
      // Reload the page after a short delay
      setTimeout(() => {
        window.location.reload();
      }, 500);
    })
    .catch(error => {
      console.error('Error:', error);
      showMessage(`Error updating transaction: ${error.message}`, 'error');
      
      // Reset button state
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Save Changes';
      }
    });
  }
  
  /**
   * Ensure split details are properly formatted before submission
   */
  function ensureSplitDetails(formData, prefix) {
    // Check if this is a personal expense or equal split
    const personalExpenseCheck = document.getElementById(`${prefix}personal_expense`);
    const isPersExpense = personalExpenseCheck && personalExpenseCheck.checked;
    const splitMethodSelect = document.getElementById(`${prefix}split_method`);
    
    if (!isPersExpense && splitMethodSelect && splitMethodSelect.value !== 'equal') {
      const splitDetailsInput = document.getElementById(`${prefix}split_details`);
      
      if (splitDetailsInput && splitDetailsInput.value) {
        // Validate JSON format
        try {
          const details = JSON.parse(splitDetailsInput.value);
          
          // Ensure it has the right structure
          if (!details.type || !details.values || Object.keys(details.values).length === 0) {
            throw new Error("Invalid split details structure");
          }
          
          // Update type to match selected method
          details.type = splitMethodSelect.value;
          
          // Re-set the value with validated JSON
          formData.set(`${prefix}split_details`, JSON.stringify(details));
        } catch (e) {
          console.error("Error validating split details:", e);
          
          // For custom splits, we need valid details, so recreate them
          const splitValues = {};
          const amountInput = document.getElementById(`${prefix}amount`);
          const totalAmount = parseFloat(amountInput?.value) || 0;
          const splitWithSelect = document.getElementById(`${prefix}split_with`);
          const paidBySelect = document.getElementById(`${prefix}paid_by`);
          
          if (splitWithSelect && paidBySelect) {
            const paidById = paidBySelect.value;
            const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
            
            // Create basic split: payer pays 0, others split equally
            if (paidById) {
              splitValues[paidById] = 0;
            }
            
            // Distribute amount or percentage among participants
            if (splitMethodSelect.value === 'percentage') {
              const perPerson = splitWithIds.length > 0 ? (100 / splitWithIds.length) : 100;
              splitWithIds.forEach(id => {
                splitValues[id] = perPerson;
              });
            } else { // custom
              const perPerson = splitWithIds.length > 0 ? (totalAmount / splitWithIds.length) : totalAmount;
              splitWithIds.forEach(id => {
                splitValues[id] = perPerson;
              });
            }
            
            // Create fallback split details
            const fallbackDetails = {
              type: splitMethodSelect.value,
              values: splitValues
            };
            
            formData.set(`${prefix}split_details`, JSON.stringify(fallbackDetails));
          }
        }
      } else {
        console.warn("Split details missing for custom split");
      }
    }
  }
  
  /**
   * Advanced Multi-Select Enhancement
   */
  function enhanceMultiSelects(selector = '.enhanced-multi-select') {
    console.log(`Enhancing multi-selects with selector: ${selector}`);
    
    const selects = document.querySelectorAll(selector);
    
    selects.forEach(select => {
      // Skip if not a multi-select or already enhanced
      if (!select.multiple || select.getAttribute('data-enhanced') === 'true') {
        return;
      }
      
      console.log(`Enhancing multi-select: ${select.id || select.name}`);
      
      // Mark as enhanced
      select.setAttribute('data-enhanced', 'true');
      
      // Create wrapper container
      const container = document.createElement('div');
      container.className = 'custom-multi-select-container position-relative';
      select.parentNode.insertBefore(container, select);
      container.appendChild(select);
      
      // Create display element that shows selected items
      const displayBox = document.createElement('div');
      displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
      displayBox.innerHTML = '<span class="placeholder">Select people to split with</span>';
      container.appendChild(displayBox);
      
      // Create dropdown container
      const dropdown = document.createElement('div');
      dropdown.className = 'custom-multi-select-dropdown';
      dropdown.style.display = 'none';
      container.appendChild(dropdown);
      
      // Add search input to dropdown
      const searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'form-control form-control-sm bg-dark text-light mb-2';
      searchInput.placeholder = 'Search...';
      dropdown.appendChild(searchInput);
      
      // Create options container
      const optionsContainer = document.createElement('div');
      optionsContainer.className = 'custom-multi-select-options';
      dropdown.appendChild(optionsContainer);
      
      // Add options with checkboxes
      Array.from(select.options).forEach(option => {
        const item = document.createElement('div');
        item.className = 'custom-multi-select-option';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.id = `multiselect-${select.id}-${option.value}`;
        checkbox.checked = option.selected;
        
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.className = 'form-check-label ms-2';
        label.textContent = option.textContent;
        
        item.appendChild(checkbox);
        item.appendChild(label);
        optionsContainer.appendChild(item);
        
        // Handle checkbox change
        checkbox.addEventListener('change', function() {
          option.selected = checkbox.checked;
          updateDisplay();
          
          // Trigger change event on original select
          const event = new Event('change', { bubbles: true });
          select.dispatchEvent(event);
        });
        
        // Make the whole item clickable
        item.addEventListener('click', function(e) {
          if (e.target !== checkbox) {
            checkbox.checked = !checkbox.checked;
            option.selected = checkbox.checked;
            updateDisplay();
            
            // Trigger change event on original select
            select.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });
      });
      
      // Toggle dropdown on display box click
      displayBox.addEventListener('click', function() {
        // If select is disabled, don't show dropdown
        if (select.disabled) return;
        
        const isVisible = dropdown.style.display === 'block';
        dropdown.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
          searchInput.focus();
          searchInput.value = '';
          
          // Show all options when opening
          optionsContainer.querySelectorAll('.custom-multi-select-option').forEach(opt => {
            opt.style.display = 'block';
          });
        }
      });
      
      // Handle search functionality
      searchInput.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        
        optionsContainer.querySelectorAll('.custom-multi-select-option').forEach(opt => {
          const optText = opt.textContent.toLowerCase();
          opt.style.display = optText.includes(searchText) ? 'block' : 'none';
        });
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', function(e) {
        if (!container.contains(e.target)) {
          dropdown.style.display = 'none';
        }
      });
      
      // Function to update display box
      function updateDisplay() {
        const selectedOptions = Array.from(select.selectedOptions);
        
        if (selectedOptions.length === 0) {
          displayBox.innerHTML = '<span class="placeholder">Select people to split with</span>';
        } else {
          displayBox.innerHTML = selectedOptions
            .map(opt => `<span class="badge bg-primary me-1 mb-1">${opt.textContent.split(' (')[0]}</span>`)
            .join(' ');
        }
      }
      
      // Update display initially
      updateDisplay();
      
      // Update when the original select changes
      select.addEventListener('change', updateDisplay);
      
      // Handle disabled state
      function updateDisabledState() {
        if (select.disabled) {
          container.style.opacity = '0.5';
          container.style.pointerEvents = 'none';
        } else {
          container.style.opacity = '1';
          container.style.pointerEvents = 'auto';
        }
      }
      
      // Initial update of disabled state
      updateDisabledState();
      
      // Watch for changes to the disabled attribute
      const observer = new MutationObserver(() => {
        updateDisabledState();
      });
      
      observer.observe(select, { 
        attributes: true, 
        attributeFilter: ['disabled'] 
      });
    });
  }
  
  /**
   * Add necessary styles for the multi-select
   */
  function addMultiSelectStyles() {
    // Check if styles already exist
    if (document.getElementById('multi-select-styles')) return;
    
    const styleEl = document.createElement('style');
    styleEl.id = 'multi-select-styles';
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
        top: 100%;
        left: 0;
        width: 100%;
        max-height: 250px;
        overflow-y: auto;
        z-index: 1050;
        border: 1px solid #444;
        border-radius: 0.25rem;
        padding: 8px;
        margin-top: 2px;
        background-color: #2d2d2d;
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
        background-color: #3d4a5c;
      }
      
      /* Fix for category split display */
      .split-categories-detail .list-group-item * {
        color: white !important;
      }
      
      /* Improve color contrast for debugging */
      .debug-category-name, 
      .category-name-text {
        color: white !important;
        -webkit-text-fill-color: white !important;
      }
      
      /* Fix for hiding the original select */
      select[data-enhanced="true"] {
        position: absolute;
        opacity: 0;
        height: 0;
        width: 0;
        overflow: hidden;
      }
    `;
    
    document.head.appendChild(styleEl);
  }
  
  /**
   * Opens a slide panel with the specified options
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
        <button type="button" class="btn-close btn-close-white" onclick="TransactionModule.closeSlidePanel('${panelId}')"></button>
      `;
      
      // Create panel content
      const content = document.createElement('div');
      content.className = 'slide-panel-content';
      
      // Add loading spinner
      content.innerHTML = `
        <div class="d-flex justify-content-center py-5">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      `;
      
      // Add to panel
      panel.appendChild(header);
      panel.appendChild(content);
      
      // Add to DOM
      document.body.appendChild(panel);
    }
    
    // Create overlay if needed
    let overlay = document.getElementById('slide-panel-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'slide-panel-overlay';
      overlay.className = 'slide-panel-overlay';
      document.body.appendChild(overlay);
    }
    
    // Show overlay with animation
    setTimeout(() => {
      overlay.classList.add('active');
    }, 10);
    
    // Close panel when overlay is clicked
    overlay.onclick = function() {
      closeSlidePanel(panelId);
    };
    
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
   */
  function closeSlidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
      panel.classList.remove('active');
      
      // Remove panel after animation
      setTimeout(() => {
        if (panel.parentNode) {
          panel.parentNode.removeChild(panel);
        }
      }, 300);
    }
    
    // Hide overlay
    const overlay = document.getElementById('slide-panel-overlay');
    if (overlay) {
      overlay.classList.remove('active');
      
      // Remove overlay after animation
      setTimeout(() => {
        if (overlay.parentNode) {
          overlay.parentNode.removeChild(overlay);
        }
      }, 300);
    }
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
  }
  
  /**
   * Show a message toast
   */
  function showMessage(message, type = 'success', options = {}) {
    if (!message) return;
    
    // Default options
    const settings = Object.assign({
      autoHide: true,
      delay: 4000
    }, options);
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      document.body.appendChild(toastContainer);
    }
    
    // Generate unique ID for this toast
    const toastId = `toast-${Date.now()}`;
    
    // Determine background color based on type
    const bgColor = type === 'error' ? 'bg-danger' : 
                   type === 'warning' ? 'bg-warning text-dark' : 
                   type === 'info' ? 'bg-info text-dark' : 'bg-success';
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    if (settings.autoHide) {
      toastEl.setAttribute('data-bs-delay', settings.delay.toString());
    } else {
      toastEl.setAttribute('data-bs-autohide', 'false');
    }
    
    // Create toast content
    toastEl.innerHTML = `
      <div class="toast-header ${bgColor} ${type !== 'warning' && type !== 'info' ? 'text-white' : ''}">
        <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
        <button type="button" class="btn-close ${type !== 'warning' && type !== 'info' ? 'btn-close-white' : ''}" 
          data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toastEl);
    
    // Show the toast using Bootstrap if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
      const toast = new bootstrap.Toast(toastEl);
      toast.show();
    } else {
      // Fallback if Bootstrap is not available
      toastEl.style.display = 'block';
      toastEl.style.opacity = '1';
      
      if (settings.autoHide) {
        setTimeout(() => {
          toastEl.style.opacity = '0';
          setTimeout(() => {
            toastEl.remove();
          }, 300);
        }, settings.delay);
      }
    }
    
    // Auto-remove toast from DOM after hiding (if using Bootstrap)
    toastEl.addEventListener('hidden.bs.toast', function() {
      toastEl.remove();
    });
  }
  
  // Initialize the module and return the public API
  return init();
})();

// Make the module globally available
window.TransactionModule = TransactionModule;

// Auto-initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM loaded - initializing enhanced multi-selects");
  
  // Enhance any multi-selects that are already in the page
  TransactionModule.enhanceMultiSelects();
});