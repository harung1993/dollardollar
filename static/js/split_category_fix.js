/**
 * Enhanced Toggle Function for Category Splits
 * This code fixes the issue where toggling "Split this transaction into multiple categories"
 * doesn't show the split UI for transactions without existing splits
 */

// Override the event listener for the enable_category_split checkbox
function fixCategorySplitToggle() {
    console.log("Applying fix for category split toggle...");
    
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    
    if (!enableCategorySplitCheck || !categorySplitsContainer) {
        console.warn("Category split elements not found, cannot apply fix");
        return;
    }
    
    // Remove any existing event listeners by cloning and replacing
    const newCheckbox = enableCategorySplitCheck.cloneNode(true);
    enableCategorySplitCheck.parentNode.replaceChild(newCheckbox, enableCategorySplitCheck);
    
    // Add our enhanced event listener
    newCheckbox.addEventListener('change', function() {
        console.log("Category split toggle changed:", this.checked);
        const isChecked = this.checked;
        
        // Show/hide the splits container
        categorySplitsContainer.style.display = isChecked ? 'block' : 'none';
        
        // Toggle transition class for smooth appearance
        if (isChecked) {
            categorySplitsContainer.classList.remove('hidden');
            categorySplitsContainer.classList.add('visible');
        } else {
            categorySplitsContainer.classList.remove('visible');
            categorySplitsContainer.classList.add('hidden');
        }
        
        // Disable/enable main category field
        const categorySelect = document.getElementById('edit_category_id');
        if (categorySelect) {
            categorySelect.disabled = isChecked;
            categorySelect.parentElement.classList.toggle('opacity-50', isChecked);
        }
        
        if (isChecked) {
            // Clear existing splits first
            const categorySplitsList = document.getElementById('category_splits_list');
            if (categorySplitsList) {
                categorySplitsList.innerHTML = '';
                
                // Add a new split with the full transaction amount
                const amountInput = document.getElementById('edit_amount');
                const totalAmount = parseFloat(amountInput?.value) || 0;
                
                console.log("Adding initial split with amount:", totalAmount);
                
                // Call the existing addCategorySplit function
                if (typeof addCategorySplit === 'function') {
                    addCategorySplit(totalAmount);
                    updateSplitTotals();
                } else {
                    // Fallback implementation if the function doesn't exist
                    createFallbackSplit(categorySplitsList, totalAmount);
                }
            }
        } else {
            // Clear split data
            const categorySplitsData = document.getElementById('category_splits_data');
            if (categorySplitsData) {
                categorySplitsData.value = '';
            }
        }
    });
    
    // Also fix the "Add Split" button to ensure it works properly
    const addSplitBtn = document.getElementById('add_split_btn');
    if (addSplitBtn) {
        // Remove existing listeners
        const newAddBtn = addSplitBtn.cloneNode(true);
        addSplitBtn.parentNode.replaceChild(newAddBtn, addSplitBtn);
        
        // Add our enhanced listener
        newAddBtn.addEventListener('click', function() {
            console.log("Add split button clicked");
            
            // Call the existing function if available
            if (typeof addCategorySplit === 'function') {
                addCategorySplit(0); // Add with zero amount
                updateSplitTotals();
            } else {
                // Fallback implementation
                const categorySplitsList = document.getElementById('category_splits_list');
                if (categorySplitsList) {
                    createFallbackSplit(categorySplitsList, 0);
                }
            }
        });
    }
    
    console.log("Category split toggle fix applied");
}

// Fallback implementation for adding a split (in case the original function isn't available)
function createFallbackSplit(container, amount) {
    console.log("Using fallback split creation with amount:", amount);
    
    const splitId = Date.now(); // Generate unique ID
    
    const splitRow = document.createElement('div');
    splitRow.className = 'row mb-3 split-row';
    splitRow.dataset.splitId = splitId;
    
    // Create category dropdown and amount input
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
    
    container.appendChild(splitRow);
    
    // Add event handlers
    splitRow.querySelector('.split-amount').addEventListener('input', function() {
        if (typeof updateSplitTotals === 'function') {
            updateSplitTotals();
        }
    });
    
    splitRow.querySelector('.split-category').addEventListener('change', function() {
        if (typeof updateSplitTotals === 'function') {
            updateSplitTotals();
        }
    });
    
    splitRow.querySelector('.remove-split').addEventListener('click', function() {
        splitRow.remove();
        if (typeof updateSplitTotals === 'function') {
            updateSplitTotals();
        }
    });
}

// Fallback implementation of updateSplitTotals (in case the original isn't available)
function fallbackUpdateSplitTotals() {
    const transactionTotal = parseFloat(document.getElementById('edit_amount')?.value) || 0;
    let splitTotal = 0;
    
    // Calculate sum of all splits
    document.querySelectorAll('.split-row').forEach(row => {
        const amountInput = row.querySelector('.split-amount');
        splitTotal += parseFloat(amountInput?.value) || 0;
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
            statusEl.textContent = 'Balanced';
            statusEl.className = 'badge bg-success';
        } else if (splitTotal < transactionTotal) {
            statusEl.textContent = 'Underfunded';
            statusEl.className = 'badge bg-warning';
        } else {
            statusEl.textContent = 'Overfunded';
            statusEl.className = 'badge bg-danger';
        }
    }
    
    // Update hidden input with split data
    updateSplitDataField();
}

// Helper function to update the hidden input with split data
function updateSplitDataField() {
    const splitRows = document.querySelectorAll('.split-row');
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

// Initialize the fix when the edit form appears in the DOM
function initializeSplitFix() {
    // Check if we're on a page with the edit form
    if (document.getElementById('editTransactionForm')) {
        console.log("Edit form found, applying category split fix");
        fixCategorySplitToggle();
    }
}

// Add listener to initialize when the edit panel is opened
document.addEventListener('click', function(e) {
    if (e.target.closest('.edit-expense-btn')) {
        console.log("Edit button clicked, scheduling split fix");
        // Wait for form to load
        setTimeout(initializeSplitFix, 500);
    }
});

// Initialize right away if the form is already in the DOM
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('editTransactionForm')) {
        console.log("Edit form already in DOM on page load, applying category split fix");
        fixCategorySplitToggle();
    }
});

// Additional fix for the global updateSplitTotals function
if (typeof window.updateSplitTotals !== 'function') {
    window.updateSplitTotals = fallbackUpdateSplitTotals;
}