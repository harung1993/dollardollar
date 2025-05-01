/**
 * Transaction Form Fix - Simple Solution
 * 
 * This script fixes specific issues with the transaction forms:
 * 1. Provides a global openEditTransactionPanel function
 * 2. Fixes split_with selection not being saved to the database
 * 3. Ensures split method options display correctly
 * 
 * Add this file to your template after all other JS files.
 */

// Ensure we have a global openEditTransactionPanel function
if (typeof openEditTransactionPanel !== 'function') {
    console.log("Defining global openEditTransactionPanel function");
    
    // Define the global function that delegates to TransactionModule if available
    window.openEditTransactionPanel = function(expenseId) {
      if (window.TransactionModule && typeof TransactionModule.openEditTransactionPanel === 'function') {
        console.log("Using TransactionModule to open edit form");
        TransactionModule.openEditTransactionPanel(expenseId);
      } else {
        console.error("TransactionModule not available for edit form");
        alert("Error loading edit form. Please refresh the page and try again.");
      }
    };
  }
  
  // Fix specific issues with transaction forms
  document.addEventListener('DOMContentLoaded', function() {
    console.log("Transaction Form Fix loaded");
    
    // Fix add transaction button
    const addTransactionBtn = document.getElementById('openAddTransactionBtn');
    if (addTransactionBtn) {
      console.log("Fixing add transaction button");
      addTransactionBtn.addEventListener('click', function() {
        if (window.TransactionModule && typeof TransactionModule.openAddTransactionPanel === 'function') {
          TransactionModule.openAddTransactionPanel();
        } else if (typeof openAddTransactionPanel === 'function') {
          openAddTransactionPanel();
        } else {
          console.error("No function available to open add form");
        }
      });
    }
    
    // Observe for edit transaction forms being added to the DOM
    const observer = new MutationObserver(function(mutations) {
      for (const mutation of mutations) {
        if (mutation.type === 'childList' && mutation.addedNodes.length) {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === 1 && (
                node.id === 'editTransactionPanel' || 
                node.querySelector('#editTransactionForm'))) {
              console.log("Edit transaction form detected, applying fixes");
              setTimeout(fixEditForm, 100);
            } else if (node.nodeType === 1 && (
                node.id === 'addTransactionPanel' || 
                node.querySelector('#newTransactionForm'))) {
              console.log("Add transaction form detected, applying fixes");
              setTimeout(fixAddForm, 100);
            }
          }
        }
      }
    });
    
    // Start observing
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
  
  /**
   * Fix the add transaction form
   */
  function fixAddForm() {
    // Fix the split_with multi-select to ensure values are submitted
    const splitWithSelect = document.getElementById('split_with');
    if (splitWithSelect) {
      fixSplitWith(splitWithSelect);
    }
    
    // Fix the form submission
    const form = document.getElementById('newTransactionForm');
    if (form) {
      const originalSubmit = form.onsubmit;
      form.onsubmit = function(e) {
        // Make sure split_with is enabled before submission
        if (splitWithSelect) {
          splitWithSelect.disabled = false;
        }
        
        // Ensure split details are updated
        ensureSplitDetails();
        
        // Call original submit handler if it exists
        if (typeof originalSubmit === 'function') {
          return originalSubmit.call(this, e);
        }
      };
    }
    
    // Fix personal expense toggling
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (personalExpenseCheck) {
      personalExpenseCheck.addEventListener('change', function() {
        const splitWithSelect = document.getElementById('split_with');
        if (!splitWithSelect) return;
        
        // Clear selections and disable when personal
        if (this.checked) {
          for (let i = 0; i < splitWithSelect.options.length; i++) {
            splitWithSelect.options[i].selected = false;
          }
          splitWithSelect.disabled = true;
          
          // Hide custom split container
          const customSplitContainer = document.getElementById('custom_split_container');
          if (customSplitContainer) customSplitContainer.style.display = 'none';
        } else {
          // Enable split with
          splitWithSelect.disabled = false;
          
          // Show custom split container if needed
          const splitMethod = document.getElementById('split_method')?.value;
          if (splitMethod && splitMethod !== 'equal') {
            const customSplitContainer = document.getElementById('custom_split_container');
            if (customSplitContainer) customSplitContainer.style.display = 'block';
            
            // Update split values
            setTimeout(updateSplitValues, 100);
          }
        }
      });
    }
    
    // Fix split method toggle
    const splitMethodSelect = document.getElementById('split_method');
    if (splitMethodSelect) {
      splitMethodSelect.addEventListener('change', function() {
        const personalExpenseCheck = document.getElementById('personal_expense');
        const isPersonal = personalExpenseCheck?.checked || false;
        
        // Only show custom split container if not personal and not equal
        const customSplitContainer = document.getElementById('custom_split_container');
        if (customSplitContainer) {
          if (this.value !== 'equal' && !isPersonal) {
            customSplitContainer.style.display = 'block';
            setTimeout(updateSplitValues, 100);
          } else {
            customSplitContainer.style.display = 'none';
          }
        }
      });
    }
  }
  
  /**
   * Fix the edit transaction form
   */
  function fixEditForm() {
    // Fix the split_with multi-select to ensure values are submitted
    const splitWithSelect = document.getElementById('edit_split_with');
    if (splitWithSelect) {
      fixSplitWith(splitWithSelect);
    }
    
    // Fix the form submission
    const form = document.getElementById('editTransactionForm');
    if (form) {
      const originalSubmit = form.onsubmit;
      form.onsubmit = function(e) {
        // Make sure split_with is enabled before submission
        if (splitWithSelect) {
          splitWithSelect.disabled = false;
        }
        
        // Ensure split details are updated
        ensureSplitDetails('edit_');
        
        // Call original submit handler if it exists
        if (typeof originalSubmit === 'function') {
          return originalSubmit.call(this, e);
        }
      };
    }
    
    // Fix personal expense toggling
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (personalExpenseCheck) {
      personalExpenseCheck.addEventListener('change', function() {
        const splitWithSelect = document.getElementById('edit_split_with');
        if (!splitWithSelect) return;
        
        // Clear selections and disable when personal
        if (this.checked) {
          for (let i = 0; i < splitWithSelect.options.length; i++) {
            splitWithSelect.options[i].selected = false;
          }
          splitWithSelect.disabled = true;
          
          // Hide custom split container
          const customSplitContainer = document.getElementById('edit_custom_split_container');
          if (customSplitContainer) customSplitContainer.style.display = 'none';
        } else {
          // Enable split with
          splitWithSelect.disabled = false;
          
          // Show custom split container if needed
          const splitMethod = document.getElementById('edit_split_method')?.value;
          if (splitMethod && splitMethod !== 'equal') {
            const customSplitContainer = document.getElementById('edit_custom_split_container');
            if (customSplitContainer) customSplitContainer.style.display = 'block';
            
            // Update split values
            setTimeout(updateEditSplitValues, 100);
          }
        }
      });
    }
    
    // Fix split method toggle
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (splitMethodSelect) {
      splitMethodSelect.addEventListener('change', function() {
        const personalExpenseCheck = document.getElementById('edit_personal_expense');
        const isPersonal = personalExpenseCheck?.checked || false;
        
        // Only show custom split container if not personal and not equal
        const customSplitContainer = document.getElementById('edit_custom_split_container');
        if (customSplitContainer) {
          if (this.value !== 'equal' && !isPersonal) {
            customSplitContainer.style.display = 'block';
            setTimeout(updateEditSplitValues, 100);
          } else {
            customSplitContainer.style.display = 'none';
          }
        }
      });
    }
    
    // Ensure category splits work
    fixCategorySplits();
  }
  
  /**
   * Fix a split_with multi-select element
   */
  function fixSplitWith(selectElement) {
    if (!selectElement) return;
    
    console.log("Fixing split_with element:", selectElement.id);
    
    // Make sure it's not hidden by CSS
    selectElement.style.position = '';
    selectElement.style.opacity = '';
    selectElement.style.left = '';
    selectElement.style.height = '';
    
    // Ensure the original select isn't hidden when the form is submitted
    const parentForm = selectElement.closest('form');
    if (parentForm) {
      parentForm.addEventListener('submit', function() {
        selectElement.style.display = '';
        selectElement.style.opacity = '1';
        selectElement.style.position = 'static';
        selectElement.disabled = false;
        
        console.log("Submitting with values:", 
                   Array.from(selectElement.selectedOptions).map(opt => opt.value));
      }, true); // Use capture to ensure this runs before other handlers
    }
  }
  
  /**
   * Ensure split details are properly formatted before submission
   */
  function ensureSplitDetails(prefix = '') {
    const splitMethodSelect = document.getElementById(`${prefix}split_method`);
    const splitDetailsInput = document.getElementById(`${prefix}split_details`);
    const personalExpense = document.getElementById(`${prefix}personal_expense`);
    
    // Skip if personal expense or equal split
    if ((personalExpense && personalExpense.checked) || 
        !splitMethodSelect || 
        splitMethodSelect.value === 'equal' ||
        !splitDetailsInput) {
      return;
    }
    
    // Verify we have valid split details
    let splitDetails;
    try {
      splitDetails = JSON.parse(splitDetailsInput.value);
      console.log("Current split details:", splitDetails);
      
      // Verify the structure is correct
      if (!splitDetails || 
          !splitDetails.type || 
          !splitDetails.values || 
          Object.keys(splitDetails.values).length === 0) {
        throw new Error("Invalid split details structure");
      }
      
      // Update the type to match the selected method
      if (splitDetails.type !== splitMethodSelect.value) {
        splitDetails.type = splitMethodSelect.value;
        splitDetailsInput.value = JSON.stringify(splitDetails);
      }
    } catch(e) {
      console.warn("Invalid split details, regenerating:", e);
      
      // Create basic split details
      const splitWithSelect = document.getElementById(`${prefix}split_with`);
      const paidBySelect = document.getElementById(`${prefix}paid_by`);
      const amountInput = document.getElementById(`${prefix}amount`);
      
      if (!splitWithSelect || !paidBySelect || !amountInput) {
        console.error("Missing required elements for regenerating split details");
        return;
      }
      
      // Create basic split values
      const splitValues = {};
      const totalAmount = parseFloat(amountInput.value) || 0;
      const paidById = paidBySelect.value;
      const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
      
      // Payer pays zero by default
      if (paidById) {
        splitValues[paidById] = 0;
      }
      
      // Others split the amount
      if (splitMethodSelect.value === 'percentage') {
        // Equal percentage for all participants except payer
        const perPerson = splitWithIds.length > 0 ? (100 / splitWithIds.length) : 100;
        splitWithIds.forEach(id => {
          splitValues[id] = perPerson;
        });
      } else { // Custom amount
        // Equal amounts for all participants except payer
        const perPerson = splitWithIds.length > 0 ? (totalAmount / splitWithIds.length) : totalAmount;
        splitWithIds.forEach(id => {
          splitValues[id] = perPerson;
        });
      }
      
      // Update the input value
      const newDetails = {
        type: splitMethodSelect.value,
        values: splitValues
      };
      splitDetailsInput.value = JSON.stringify(newDetails);
      console.log("Regenerated split details:", newDetails);
    }
  }
  
  /**
   * Update split values for the add form
   */
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
      // For percentage split
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
          .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        
        // Default distribution: payer pays 0%, others split 100% equally
        let userPercentage = 0;
        if (isPayerId) {
          userPercentage = 0;
        } else {
          userPercentage = splitWithIds.length > 0 ? (100 / splitWithIds.length) : 100;
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
        
        // Default distribution: payer pays $0, others split the total equally
        let userAmount = 0;
        if (isPayerId) {
          userAmount = 0;
        } else {
          userAmount = splitWithIds.length > 0 ? (totalAmount / splitWithIds.length) : totalAmount;
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
              <span class="input-group-text bg-dark text-light">${window.baseCurrencySymbol || '$'}</span>
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
    document.querySelectorAll('.split-value-input').forEach(input => {
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
          const splitStatusEl = document.getElementById('split_status');
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
          const splitStatusEl = document.getElementById('split_status');
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
        
        // Update hidden split details field
        if (splitDetailsInput) {
          splitDetailsInput.value = JSON.stringify({
            type: splitMethod,
            values: splitValues
          });
        }
      });
    });
    
    // Initially trigger an input event on the first input to update totals
    const firstInput = document.querySelector('.split-value-input');
    if (firstInput) {
      firstInput.dispatchEvent(new Event('input'));
    }
  }
  
  /**
   * Update split values for the edit form
   */
  function updateEditSplitValues() {
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (personalExpenseCheck && personalExpenseCheck.checked) return;
    
    const amountInput = document.getElementById('edit_amount');
    const paidBySelect = document.getElementById('edit_paid_by');
    const splitWithSelect = document.getElementById('edit_split_with');
    const splitTotalEl = document.getElementById('edit_split_total');
    const splitValuesContainer = document.getElementById('edit_split_values_container');
    const splitDetailsInput = document.getElementById('edit_split_details');
    
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
    
    // Try to load existing split details
    let existingSplitValues = {};
    try {
      if (splitDetailsInput && splitDetailsInput.value) {
        const details = JSON.parse(splitDetailsInput.value);
        if (details && details.values) {
          existingSplitValues = details.values;
        }
      }
    } catch (e) {
      console.warn('Could not parse existing split details', e);
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
        
        // Use existing value if available, otherwise set defaults
        let userPercentage;
        if (existingSplitValues[userId] !== undefined) {
          userPercentage = existingSplitValues[userId];
        } else if (isPayerId) {
          // Default payer percentage to 0
          userPercentage = 0;
        } else {
          // Split 100% evenly among non-payers
          userPercentage = splitWithIds.length > 0 ? (100 / splitWithIds.length) : 100;
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
              <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                data-user-id="${userId}" step="0.1" min="0" max="100" 
                value="${userPercentage.toFixed(1)}">
              <span class="input-group-text bg-dark text-light">%</span>
            </div>
          </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Save the value
        splitValues[userId] = userPercentage;
      });
    } else { // Custom amount
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
          .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        
        // Use existing value if available, otherwise set defaults
        let userAmount;
        if (existingSplitValues[userId] !== undefined) {
          userAmount = existingSplitValues[userId];
        } else if (isPayerId) {
          // Default payer amount to 0
          userAmount = 0;
        } else {
          // Split total evenly among non-payers
          userAmount = splitWithIds.length > 0 ? (totalAmount / splitWithIds.length) : totalAmount;
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
              <span class="input-group-text bg-dark text-light">${window.baseCurrencySymbol || '$'}</span>
              <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                data-user-id="${userId}" step="0.01" min="0" 
                value="${userAmount.toFixed(2)}">
            </div>
          </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Save the value
        splitValues[userId] = userAmount;
      });
    }
    
    // Add event listeners to inputs
    document.querySelectorAll('.edit-split-value-input').forEach(input => {
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
          const splitStatusEl = document.getElementById('edit_split_status');
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
          const splitStatusEl = document.getElementById('edit_split_status');
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
        
        // Update hidden split details field with proper structure
        if (splitDetailsInput) {
          splitDetailsInput.value = JSON.stringify({
            type: splitMethod,
            values: splitValues
          });
          console.log("Updated split details:", JSON.parse(splitDetailsInput.value));
        }
      });
    });
    
    // Initially trigger an input event on the first input to update totals
    const firstInput = document.querySelector('.edit-split-value-input');
    if (firstInput) {
      firstInput.dispatchEvent(new Event('input'));
    }
  }
  
  /**
   * Fix category splits in the edit form
   */
  function fixCategorySplits() {
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    const categorySplitsData = document.getElementById('category_splits_data');
    
    if (!enableCategorySplitCheck || !categorySplitsContainer) {
      console.warn("Category split elements not found");
      return;
    }
    
    console.log("Fixing category splits, current check state:", enableCategorySplitCheck.checked);
    
    // Ensure the container is visible if checked
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
    }
    
    // Add split button functionality
    const addSplitBtn = document.getElementById('add_split_btn');
    if (addSplitBtn) {
      addSplitBtn.addEventListener('click', function() {
        const categorySpitsList = document.getElementById('category_splits_list');
        if (!categorySpitsList) return;
        
        // Create a unique ID for this split
        const splitId = Date.now();
        
        // Create the split row
        const splitRow = document.createElement('div');
        splitRow.className = 'row mb-3 split-row';
        splitRow.dataset.splitId = splitId;
        
        // Create the HTML content
        splitRow.innerHTML = `
          <div class="col-md-5">
            <select class="form-select bg-dark text-light split-category" data-split-id="${splitId}">
              <option value="">Select category</option>
              ${document.getElementById('edit_category_id')?.innerHTML || ''}
            </select>
          </div>
          <div class="col-md-5">
            <div class="input-group">
              <span class="input-group-text bg-dark text-light">${window.baseCurrencySymbol || '$'}</span>
              <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                    data-split-id="${splitId}" value="0.00">
            </div>
          </div>
          <div class="col-md-2">
            <button type="button" class="btn btn-outline-danger remove-split" data-split-id="${splitId}">
              <i class="fas fa-times"></i>
            </button>
          </div>
        `;
        
        // Add to the list
        categorySpitsList.appendChild(splitRow);
        
        // Add event listeners
        const categorySelect = splitRow.querySelector('.split-category');
        if (categorySelect) {
          categorySelect.addEventListener('change', updateSplitTotals);
        }
        
        const amountInput = splitRow.querySelector('.split-amount');
        if (amountInput) {
          amountInput.addEventListener('input', updateSplitTotals);
        }
        
        const removeButton = splitRow.querySelector('.remove-split');
        if (removeButton) {
          removeButton.addEventListener('click', function() {
            splitRow.remove();
            updateSplitTotals();
          });
        }
        
        // Update totals
        updateSplitTotals();
      });
    }
    
    // Make sure update totals works
    function updateSplitTotals() {
      const transactionTotal = parseFloat(document.getElementById('edit_amount')?.value) || 0;
      let splitTotal = 0;
      let allCategoriesSelected = true;
      
      // Collect split data
      const splitData = [];
      document.querySelectorAll('.split-row').forEach(row => {
        const categorySelect = row.querySelector('.split-category');
        const amountInput = row.querySelector('.split-amount');
        
        if (categorySelect && amountInput) {
          const categoryId = categorySelect.value;
          const amount = parseFloat(amountInput.value) || 0;
          
          // Add to total
          splitTotal += amount;
          
          // Check if category is selected
          if (!categoryId) {
            allCategoriesSelected = false;
          } else if (amount > 0) {
            // Add to split data if valid
            splitData.push({
              category_id: categoryId,
              amount: amount
            });
          }
        }
      });
      
      // Update UI
      const splitTotalEl = document.getElementById('split_total');
      const transactionTotalEl = document.getElementById('transaction_total');
      
      if (splitTotalEl) splitTotalEl.textContent = splitTotal.toFixed(2);
      if (transactionTotalEl) transactionTotalEl.textContent = transactionTotal.toFixed(2);
      
      // Update status
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
      
      // Update hidden input with split data JSON
      if (categorySplitsData) {
        categorySplitsData.value = JSON.stringify(splitData);
        console.log("Updated category splits data:", splitData);
      }
    }
    
    // Initialize category splits from existing data
    if (categorySplitsData && categorySplitsData.value) {
      try {
        const splitData = JSON.parse(categorySplitsData.value);
        console.log("Initializing from category splits data:", splitData);
        
        if (Array.isArray(splitData) && splitData.length > 0) {
          // Clear existing splits
          const categorySpitsList = document.getElementById('category_splits_list');
          if (categorySpitsList) {
            categorySpitsList.innerHTML = '';
            
            // Add each split
            splitData.forEach(split => {
              // Create a unique ID for this split
              const splitId = Date.now() + Math.random() * 1000;
              
              // Create the split row
              const splitRow = document.createElement('div');
              splitRow.className = 'row mb-3 split-row';
              splitRow.dataset.splitId = splitId;
              
              // Create the HTML content
              splitRow.innerHTML = `
                <div class="col-md-5">
                  <select class="form-select bg-dark text-light split-category" data-split-id="${splitId}">
                    <option value="">Select category</option>
                    ${document.getElementById('edit_category_id')?.innerHTML || ''}
                  </select>
                </div>
                <div class="col-md-5">
                  <div class="input-group">
                    <span class="input-group-text bg-dark text-light">${window.baseCurrencySymbol || '$'}</span>
                    <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                          data-split-id="${splitId}" value="${split.amount.toFixed(2)}">
                  </div>
                </div>
                <div class="col-md-2">
                  <button type="button" class="btn btn-outline-danger remove-split" data-split-id="${splitId}">
                    <i class="fas fa-times"></i>
                  </button>
                </div>
              `;
              
              // Add to the list
              categorySpitsList.appendChild(splitRow);
              
              // Set the category
              const categorySelect = splitRow.querySelector('.split-category');
              if (categorySelect && split.category_id) {
                categorySelect.value = split.category_id;
              }
              
              // Add event listeners
              if (categorySelect) {
                categorySelect.addEventListener('change', updateSplitTotals);
              }
              
              const amountInput = splitRow.querySelector('.split-amount');
              if (amountInput) {
                amountInput.addEventListener('input', updateSplitTotals);
              }
              
              const removeButton = splitRow.querySelector('.remove-split');
              if (removeButton) {
                removeButton.addEventListener('click', function() {
                  splitRow.remove();
                  updateSplitTotals();
                });
              }
            });
            
            // Update totals
            updateSplitTotals();
          }
        }
      } catch (e) {
        console.error("Error parsing category splits data:", e);
      }
    }
  }