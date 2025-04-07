/**
 * Enhanced Category Split Functionality for Edit Transaction Form
 * Fixes:
 * 1. Properly loads existing category splits when editing a transaction
 * 2. Improves visibility of split information with better text contrast
 */

// Wait for DOM elements to be available
function waitForElement(selector, maxTime = 5000) {
    return new Promise((resolve, reject) => {
        // Check if element already exists
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }

        // Set up mutation observer to watch for the element
        const observer = new MutationObserver(() => {
            const element = document.querySelector(selector);
            if (element) {
                observer.disconnect();
                resolve(element);
            }
        });

        // Observe the entire document
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });

        // Timeout after maxTime
        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Element ${selector} not found within ${maxTime}ms`));
        }, maxTime);
    });
}

// Main function to fix edit transaction form
async function enhanceEditTransactionForm() {
    console.log("Starting edit transaction form enhancement...");

    try {
        // Wait for form elements to be loaded
        const form = await waitForElement('#editTransactionForm');
        console.log("Edit transaction form found, initializing enhancements...");

        // Fix 1: Improved category splits display and loading
        fixCategorySplits();
        
        // Fix 2: Fix text contrast for better visibility
        fixTextContrast();
        
        console.log("Edit transaction form enhancement complete");
    } catch (error) {
        console.error("Error enhancing edit transaction form:", error);
    }
}

// Fix for category splits loading and display
function fixCategorySplits() {
    // Find the enable category split checkbox
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    const categorySplitsData = document.getElementById('category_splits_data');
    
    if (!enableCategorySplitCheck || !categorySplitsContainer || !categorySplitsData) {
        console.warn("Category split elements not found, cannot fix splits");
        return;
    }
    
    // Check if we have pre-existing split data
    if (categorySplitsData.value) {
        try {
            const splitData = JSON.parse(categorySplitsData.value);
            
            if (Array.isArray(splitData) && splitData.length > 0) {
                console.log("Found existing split data, enabling category splits");
                
                // Enable category splits
                enableCategorySplitCheck.checked = true;
                categorySplitsContainer.style.display = 'block';
                
                // Disable main category select
                const categorySelect = document.getElementById('edit_category_id');
                if (categorySelect) {
                    categorySelect.disabled = true;
                    categorySelect.parentElement.classList.add('opacity-50');
                }
                
                // Clear existing splits
                const splitsList = document.getElementById('category_splits_list');
                if (splitsList) {
                    splitsList.innerHTML = '';
                    
                    // Create a split row for each item in the data
                    splitData.forEach(split => {
                        addCategorySplitWithData(split.category_id, split.amount);
                    });
                    
                    // Update totals
                    updateSplitTotals();
                }
            }
        } catch (e) {
            console.error("Error parsing split data:", e);
        }
    }
    
    // Override the existing toggle function to fix its behavior
    if (enableCategorySplitCheck) {
        enableCategorySplitCheck.addEventListener('change', function() {
            const isChecked = this.checked;
            
            // Show/hide splits container
            if (categorySplitsContainer) {
                categorySplitsContainer.style.display = isChecked ? 'block' : 'none';
            }
            
            // Disable/enable main category field
            const categorySelect = document.getElementById('edit_category_id');
            if (categorySelect) {
                categorySelect.disabled = isChecked;
                categorySelect.parentElement.classList.toggle('opacity-50', isChecked);
            }
            
            if (isChecked) {
                // Clear existing splits first
                const categorySpitsList = document.getElementById('category_splits_list');
                if (categorySpitsList) {
                    categorySpitsList.innerHTML = '';
                }
                
                // Add a new split with the full amount
                const amountInput = document.getElementById('edit_amount');
                const totalAmount = parseFloat(amountInput?.value) || 0;
                addCategorySplit(totalAmount);
                updateSplitTotals();
            } else {
                // Clear split data
                const categorySpitsList = document.getElementById('category_splits_list');
                if (categorySpitsList) {
                    categorySpitsList.innerHTML = '';
                }
                
                if (categorySplitsData) {
                    categorySplitsData.value = '';
                }
            }
        });
    }
    
    // Make sure the "Add Split" button works correctly
    const addSplitBtn = document.getElementById('add_split_btn');
    if (addSplitBtn) {
        addSplitBtn.addEventListener('click', function() {
            addCategorySplit(0);
            updateSplitTotals();
        });
    }
}

// Fix for text contrast
function fixTextContrast() {
    // Fix transaction view split details
    const splitDetails = document.querySelectorAll('[id^="split-categories-"]');
    splitDetails.forEach(detail => {
        // Add a strong contrast class
        detail.classList.add('text-high-contrast');
        
        // Add inline styles for immediate effect
        detail.style.color = '#ffffff';
        detail.style.backgroundColor = '#2d3748';
        detail.style.padding = '8px';
        detail.style.borderRadius = '4px';
        detail.style.marginTop = '5px';
    });
    
    // Fix edit form split details
    const splitRows = document.querySelectorAll('.split-row');
    splitRows.forEach(row => {
        const inputs = row.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.classList.add('text-high-contrast');
            input.style.color = '#ffffff';
        });
    });
    
    // Add CSS to ensure high contrast
    const style = document.createElement('style');
    style.textContent = `
        .text-high-contrast {
            color: #ffffff !important;
        }
        .split-row select, .split-row input {
            color: #ffffff !important;
            background-color: #2d3748 !important;
        }
        .split-row .input-group-text {
            color: #ffffff !important;
            background-color: #374151 !important;
        }
        #category_splits_container {
            background-color: #1f2937;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        #split_total, #transaction_total, #split_status {
            color: #ffffff !important;
            font-weight: bold;
        }
        .badge {
            color: #ffffff !important;
        }
    `;
    document.head.appendChild(style);
}

// Function to add a category split with a specified amount
function addCategorySplit(amount) {
    const splitsList = document.getElementById('category_splits_list');
    if (!splitsList) return;
    
    const splitId = Date.now(); // Unique ID for this split
    
    const splitRow = document.createElement('div');
    splitRow.className = 'row mb-3 split-row';
    splitRow.dataset.splitId = splitId;
    
    // Create the split HTML with category dropdown and amount input
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
    
    // Apply high contrast styling
    const inputs = splitRow.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.classList.add('text-high-contrast');
        input.style.color = '#ffffff';
    });
    
    // Add event listeners to the new elements
    splitRow.querySelector('.split-amount').addEventListener('input', updateSplitTotals);
    splitRow.querySelector('.split-category').addEventListener('change', updateSplitTotals);
    splitRow.querySelector('.remove-split').addEventListener('click', function() {
        splitRow.remove();
        updateSplitTotals();
    });
    
    return splitRow;
}

// Function to add a split with predefined category and amount
function addCategorySplitWithData(categoryId, amount) {
    const splitRow = addCategorySplit(amount);
    if (!splitRow) return;
    
    // Set the category value
    const categorySelect = splitRow.querySelector('.split-category');
    if (categorySelect && categoryId) {
        categorySelect.value = categoryId;
    }
}

// Update split totals and validate
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
        // Get the amount
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

// Function to fix the visible transaction splits in the transaction list
function fixTransactionSplitsDisplay() {
    console.log("Fixing transaction splits display...");
    
    // Find all transactions with category splits
    const splitElements = document.querySelectorAll('[data-has-splits="true"]');
    console.log(`Found ${splitElements.length} transactions with splits`);
    
    splitElements.forEach(element => {
        const expenseId = element.getAttribute('data-expense-id');
        console.log(`Processing expense ID: ${expenseId}`);
        
        // Find the toggle element within this transaction row
        const toggle = element.querySelector('.split-toggle');
        if (toggle) {
            console.log(`Toggle found for expense ID: ${expenseId}`);
            
            // Improve visibility
            toggle.style.color = '#38bdf8'; // A bright blue for visibility
            toggle.style.border = '1px solid #38bdf8';
            toggle.style.borderRadius = '4px';
            toggle.style.padding = '2px 6px';
            toggle.style.margin = '2px 0';
            toggle.style.display = 'inline-block';
            toggle.style.cursor = 'pointer';
            
            // Remove any existing event listeners (to prevent duplicates)
            const newToggle = toggle.cloneNode(true);
            toggle.parentNode.replaceChild(newToggle, toggle);
            
            // Add the new click handler
            newToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log(`Toggle clicked for expense ID: ${expenseId}`);
                
                // Find the detail container
                const detailElement = document.getElementById(`split-categories-${expenseId}`);
                console.log(`Detail element found: ${!!detailElement}`);
                
                if (detailElement) {
                    // Toggle visibility
                    const isHidden = detailElement.style.display === 'none' || !detailElement.style.display;
                    console.log(`Detail element is currently ${isHidden ? 'hidden' : 'visible'}`);
                    
                    detailElement.style.display = isHidden ? 'block' : 'none';
                    
                    // Update icon
                    const icon = this.querySelector('i');
                    if (icon) {
                        if (isHidden) {
                            icon.classList.remove('fa-chevron-down');
                            icon.classList.add('fa-chevron-up');
                        } else {
                            icon.classList.remove('fa-chevron-up');
                            icon.classList.add('fa-chevron-down');
                        }
                    }
                    
                    if (isHidden) {
                        // Improve text contrast
                        detailElement.style.color = '#ffffff';
                        detailElement.style.backgroundColor = '#2d3748';
                        detailElement.style.padding = '8px';
                        detailElement.style.borderRadius = '4px';
                        detailElement.style.marginTop = '5px';
                        
                        // Check if we need to load the data
                        if (detailElement.querySelector('.loading') || detailElement.innerHTML.trim() === '') {
                            console.log(`Loading category splits for expense ID: ${expenseId}`);
                            loadCategorySplits(expenseId, detailElement);
                        }
                    }
                } else {
                    console.error(`Could not find detail element for split-categories-${expenseId}`);
                }
            });
            
            console.log(`Click handler added for expense ID: ${expenseId}`);
        } else {
            console.warn(`No toggle found for expense ID: ${expenseId}`);
        }
    });
}

function loadCategorySplits(expenseId, detailElement) {
    // Show loading indicator
    detailElement.innerHTML = '<div class="text-white text-center"><i class="fas fa-spinner fa-spin me-2"></i>Loading split details...</div>';
    
    fetch(`/get_category_splits/${expenseId}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.success && data.splits && data.splits.length > 0) {
          // Create split detail UI with guaranteed white text
          let html = '<div class="list-group list-group-flush" style="background-color: #374151; border-radius: 6px; color: white;">';
          
          data.splits.forEach(split => {
            // Get category details
            const categoryName = split.category?.name || 'Unknown';
            const categoryColor = split.category?.color || '#6c757d';
            const categoryIcon = split.category?.icon || 'fa-tag';
            const amount = parseFloat(split.amount) || 0;
            
            html += `
              <div class="list-group-item py-2" style="background-color: #374151; border-color: #4b5563; color: white !important;">
                <div class="d-flex justify-content-between align-items-center" style="color: white !important;">
                  <div style="color: white !important;">
                    <span class="badge me-2" style="background-color: ${categoryColor}; color: white;">
                      <i class="fas ${categoryIcon}"></i>
                    </span>
                    <span style="color: white !important;">${categoryName}</span>
                  </div>
                  <span class="badge" style="background-color: #3b82f6; color: white; font-weight: bold; font-size: 0.9em;">
                    ${window.baseCurrencySymbol || '$'}${amount.toFixed(2)}
                  </span>
                </div>
              </div>
            `;
          });
          
          html += '</div>';
          detailElement.innerHTML = html;
        } else {
          detailElement.innerHTML = '<div class="text-white p-2">No split categories found</div>';
        }
      })
      .catch(error => {
        console.error('Error loading category splits:', error);
        detailElement.innerHTML = `<div class="text-danger p-2">Error loading splits: ${error.message}</div>`;
      });
  }

// Setup category split toggle for a specific transaction
function setupCategorySplitToggle(expenseId) {
    console.log(`Setting up category split toggle for expense ID: ${expenseId}`);
    
    // Find the toggle element
    const toggle = document.querySelector(`[data-expense-id="${expenseId}"] .split-toggle`);
    if (!toggle) {
        console.warn(`No toggle found for expense ID: ${expenseId}`);
        return;
    }
    
    // Make toggle more visible
    toggle.style.color = '#38bdf8';
    toggle.style.border = '1px solid #38bdf8';
    toggle.style.borderRadius = '4px';
    toggle.style.padding = '2px 6px';
    toggle.style.margin = '2px 0';
    toggle.style.display = 'inline-block';
    toggle.style.cursor = 'pointer';
    
    // Remove existing event listeners
    const newToggle = toggle.cloneNode(true);
    toggle.parentNode.replaceChild(newToggle, toggle);
    
    // Add click event listener
    newToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`Toggle clicked for expense ID: ${expenseId}`);
        
        // Get the detail container
        const detailElement = document.getElementById(`split-categories-${expenseId}`);
        if (!detailElement) {
            console.error(`Detail element not found for expense ID: ${expenseId}`);
            return;
        }
        
        // Toggle visibility
        const isHidden = detailElement.style.display === 'none' || !detailElement.style.display;
        detailElement.style.display = isHidden ? 'block' : 'none';
        
        // Update icon
        const icon = this.querySelector('i');
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
            // Style the container
            detailElement.style.color = '#ffffff';
            detailElement.style.backgroundColor = '#2d3748';
            detailElement.style.padding = '8px';
            detailElement.style.borderRadius = '4px';
            detailElement.style.marginTop = '5px';
            
            // Check if we need to load data
            if (detailElement.querySelector('.loading') || detailElement.innerHTML.trim() === '') {
                loadCategorySplits(expenseId, detailElement);
            }
        }
    });
    
    console.log(`Category split toggle setup complete for expense ID: ${expenseId}`);
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded - initializing split functionality");
    
    // Fix transaction list displays
    setTimeout(fixTransactionSplitsDisplay, 100);
    
    // Set up manual toggle click handlers for all transactions with splits
    document.querySelectorAll('[data-has-splits="true"]').forEach(element => {
        const expenseId = element.getAttribute('data-expense-id');
        if (expenseId) {
            setupCategorySplitToggle(expenseId);
        }
    });
    
    // Watch for form loading
    document.addEventListener('click', function(e) {
        // Check if user clicked on edit button
        if (e.target.closest('.edit-expense-btn')) {
            const button = e.target.closest('.edit-expense-btn');
            const expenseId = button.getAttribute('data-expense-id');
            console.log(`Edit button clicked for expense ID: ${expenseId}`);
            
            // Wait for the form to be loaded
            setTimeout(enhanceEditTransactionForm, 500);
        }
        
        // Also handle clicks on split toggle buttons directly
        if (e.target.closest('.split-toggle')) {
            const toggle = e.target.closest('.split-toggle');
            const expenseId = toggle.getAttribute('data-expense-id');
            console.log(`Direct click on split toggle for expense ID: ${expenseId}`);
        }
    });
});

// For dynamically loaded forms
if (document.getElementById('editTransactionForm')) {
    console.log("Edit form already present - enhancing immediately");
    enhanceEditTransactionForm();
}

// Add a global helper for debugging in the console
window.debugSplits = function() {
    console.log("Split toggles found:", document.querySelectorAll('.split-toggle').length);
    console.log("Transactions with splits:", document.querySelectorAll('[data-has-splits="true"]').length);
    
    document.querySelectorAll('[data-has-splits="true"]').forEach(el => {
        const id = el.getAttribute('data-expense-id');
        console.log(`Transaction ${id}:`, {
            hasToggle: !!el.querySelector('.split-toggle'),
            detailElement: document.getElementById(`split-categories-${id}`)
        });
    });
};