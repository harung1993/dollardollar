/**
 * Budget form handling and slide panel functions
 */

import { formatCurrency, showToast } from '../common/utils.js';
import { updateBudgetProgressBars } from './budget-utils.js';

/**
 * Toggle budget form visibility
 */
function toggleBudgetForm() {
    openAddBudgetPanel();
}

/**
 * Open add budget slide panel
 */
function openAddBudgetPanel() {
    // Create or get the slide panel if it already exists
    let slidePanel = document.getElementById('add-budget-slide-panel');
    
    if (!slidePanel) {
        // Create the panel
        slidePanel = document.createElement('div');
        slidePanel.id = 'add-budget-slide-panel';
        slidePanel.className = 'budget-slide-panel';
        
        // Create overlay if it doesn't exist
        let overlay = document.getElementById('slide-panel-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'slide-panel-overlay';
            overlay.id = 'slide-panel-overlay';
            overlay.addEventListener('click', closeAddBudgetPanel);
            document.body.appendChild(overlay);
        }
        
        // Add to DOM
        document.body.appendChild(slidePanel);
    }
    
    // Get today's date for the form
    const today = new Date().toISOString().split('T')[0];
    
    // Show the panel with form
    slidePanel.innerHTML = `
        <div class="slide-panel-header">
            <h4 class="mb-0">
                <i class="fas fa-plus me-2" style="color: #15803d;"></i>
                Add New Budget
            </h4>
            <button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="closeAddBudgetPanel()"></button>
        </div>
        <div class="slide-panel-content">
            <form id="add-budget-form" action="/budgets/add" method="POST">
                <div class="p-4">
                    <!-- Form Fields -->
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="slide_add_name" class="form-label">Budget Name (Optional)</label>
                            <input type="text" class="form-control bg-dark text-light" id="slide_add_name" name="name" 
                                   placeholder="E.g., Monthly Groceries">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="slide_add_amount" class="form-label">Budget Amount</label>
                            <div class="input-group">
                                <span class="input-group-text bg-dark text-light border-secondary">$</span>
                                <input type="number" step="0.01" class="form-control bg-dark text-light" id="slide_add_amount" 
                                       name="amount" required>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="slide_add_period" class="form-label">Budget Period</label>
                            <select class="form-select bg-dark text-light" id="slide_add_period" name="period" required>
                                <option value="weekly">Weekly</option>
                                <option value="monthly" selected>Monthly</option>
                                <option value="yearly">Yearly</option>
                            </select>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="slide_add_start_date" class="form-label">Start Date</label>
                            <input type="date" class="form-control bg-dark text-light" id="slide_add_start_date" 
                                   name="start_date" value="${today}" required>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="slide_add_category_id" class="form-label">Category</label>
                        <select class="form-select bg-dark text-light" id="slide_add_category_id" name="category_id" required>
                            <option value="">Select a category</option>
                            <!-- Category options will be populated via JavaScript -->
                        </select>
                    </div>
                    
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="slide_add_include_subcategories" 
                                       name="include_subcategories" checked>
                                <label class="form-check-label" for="slide_add_include_subcategories">
                                    Include subcategories in budget
                                </label>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="slide_add_is_recurring" 
                                       name="is_recurring" checked>
                                <label class="form-check-label" for="slide_add_is_recurring">
                                    Recurring budget
                                </label>
                            </div>
                        </div>
                    </div>
                    
                    <div class="d-flex justify-content-end">
                        <button type="button" class="btn btn-secondary me-2" onclick="closeAddBudgetPanel()">
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save me-1"></i> Add Budget
                        </button>
                    </div>
                </div>
            </form>
        </div>
    `;
    
    // Show the panel and overlay
    document.getElementById('slide-panel-overlay').classList.add('active');
    slidePanel.classList.add('active');
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    // Populate category select dropdown
    populateCategoryOptions('slide_add_category_id');
    
    // Add form submit handler
    const form = document.getElementById('add-budget-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch(this.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to add budget');
            return response.text();
        })
        .then(() => {
            // Show success notification
            showToast('Budget added successfully!', 'success');
            
            // Close the panel
            closeAddBudgetPanel();
            
            // Refresh the page after a delay to show updated data
            setTimeout(() => window.location.reload(), 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error adding budget: ' + error.message, 'error');
        });
    });
}

/**
 * Close the add budget panel
 */
function closeAddBudgetPanel() {
    // Get the panel and overlay
    const slidePanel = document.getElementById('add-budget-slide-panel');
    const overlay = document.getElementById('slide-panel-overlay');
    
    if (slidePanel) slidePanel.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

/**
 * Open slide panel to edit budget
 * @param {string} budgetId - Budget ID to edit
 */
function editBudget(budgetId) {
    openBudgetSlidePanel(budgetId);
}

/**
 * Open budget edit slide panel
 * @param {string} budgetId - Budget ID to edit
 */
function openBudgetSlidePanel(budgetId) {
    // Create or get the slide panel if it already exists
    let slidePanel = document.getElementById('budget-slide-panel');
    
    if (!slidePanel) {
        // Create the panel
        slidePanel = document.createElement('div');
        slidePanel.id = 'budget-slide-panel';
        slidePanel.className = 'budget-slide-panel';
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'slide-panel-overlay';
        overlay.id = 'slide-panel-overlay';
        overlay.addEventListener('click', closeBudgetSlidePanel);
        
        // Add to DOM
        document.body.appendChild(overlay);
        document.body.appendChild(slidePanel);
    }
    
    // Show loading state
    slidePanel.innerHTML = `
        <div class="slide-panel-header">
            <h4 class="mb-0">
                <i class="fas fa-edit me-2" style="color: #0ea5e9;"></i>
                Edit Budget
            </h4>
            <button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="closeBudgetSlidePanel()"></button>
        </div>
        <div class="slide-panel-content">
            <div class="d-flex justify-content-center align-items-center p-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-3">Loading budget details...</span>
            </div>
        </div>
    `;
    
    // Show the panel and overlay
    document.getElementById('slide-panel-overlay').classList.add('active');
    slidePanel.classList.add('active');
    
    // Prevent body scrolling
    document.body.style.overflow = 'hidden';
    
    // Fetch budget data
    fetch(`/budgets/get/${budgetId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch budget details');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                populateBudgetSlidePanel(data.budget);
            } else {
                showSlidePanelError(data.message || 'Error fetching budget details');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showSlidePanelError('Failed to fetch budget details: ' + error.message);
        });
}

/**
 * Close the budget edit slide panel
 */
function closeBudgetSlidePanel() {
    // Get the panel and overlay
    const slidePanel = document.getElementById('budget-slide-panel');
    const overlay = document.getElementById('slide-panel-overlay');
    
    if (slidePanel) slidePanel.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    
    // Re-enable body scrolling
    document.body.style.overflow = '';
}

/**
 * Show error in slide panel
 * @param {string} message - Error message to display
 */
function showSlidePanelError(message) {
    const slidePanel = document.getElementById('budget-slide-panel');
    if (!slidePanel) return;
    
    const contentDiv = slidePanel.querySelector('.slide-panel-content');
    if (contentDiv) {
        contentDiv.innerHTML = `
            <div class="alert alert-danger m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
            <div class="text-center mt-3">
                <button type="button" class="btn btn-secondary" onclick="closeBudgetSlidePanel()">
                    Close
                </button>
            </div>
        `;
    }
}

/**
 * Populate the budget slide panel with budget data
 * @param {Object} budget - Budget data
 */
function populateBudgetSlidePanel(budget) {
    const slidePanel = document.getElementById('budget-slide-panel');
    if (!slidePanel) return;
    
    const contentDiv = slidePanel.querySelector('.slide-panel-content');
    if (!contentDiv) return;
    
    // Create form HTML
    contentDiv.innerHTML = `
        <form id="slide-panel-edit-form" action="/budgets/edit/${budget.id}" method="POST">
            <div class="p-4">
                <!-- Budget Info Summary -->
                <div class="card bg-dark mb-4">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <span class="badge me-2" style="background-color: ${budget.category_color || '#6c757d'};">
                                <i class="fas ${budget.category_icon || 'fa-tag'}"></i>
                            </span>
                            <h5 class="mb-0">${budget.category_name || 'Budget'}</h5>
                        </div>
                        
                        <div class="progress" style="height: 8px; width: 100%;">
                            <div class="progress-bar 
                                ${budget.status === 'over' ? 'bg-danger' : 
                                 budget.status === 'approaching' ? 'bg-warning' : 'bg-success'}" 
                                role="progressbar" 
                                style="width: ${budget.percentage}%;" 
                                aria-valuenow="${budget.percentage}" 
                                aria-valuemin="0" 
                                aria-valuemax="100"></div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-4 text-center">
                                <small class="d-block text-muted">Budget</small>
                                <div class="fw-bold">${formatCurrency(budget.amount)}</div>
                            </div>
                            <div class="col-4 text-center">
                                <small class="d-block text-muted">Spent</small>
                                <div class="fw-bold">${formatCurrency(budget.spent)}</div>
                            </div>
                            <div class="col-4 text-center">
                                <small class="d-block text-muted">Remaining</small>
                                <div class="fw-bold ${budget.remaining < 0 ? 'text-danger' : 'text-success'}">
                                    ${formatCurrency(Math.abs(budget.remaining))}
                                    ${budget.remaining < 0 ? '<i class="fas fa-arrow-down"></i>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Form Fields -->
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="slide_edit_name" class="form-label">Budget Name (Optional)</label>
                        <input type="text" class="form-control bg-dark text-light" id="slide_edit_name" name="name" 
                               value="${budget.name || ''}" placeholder="E.g., Monthly Groceries">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="slide_edit_amount" class="form-label">Budget Amount</label>
                        <div class="input-group">
                            <span class="input-group-text bg-dark text-light border-secondary">$</span>
                            <input type="number" step="0.01" class="form-control bg-dark text-light" id="slide_edit_amount" 
                                   name="amount" value="${budget.amount}" required>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="slide_edit_period" class="form-label">Budget Period</label>
                        <select class="form-select bg-dark text-light" id="slide_edit_period" name="period" required>
                            <option value="weekly" ${budget.period === 'weekly' ? 'selected' : ''}>Weekly</option>
                            <option value="monthly" ${budget.period === 'monthly' ? 'selected' : ''}>Monthly</option>
                            <option value="yearly" ${budget.period === 'yearly' ? 'selected' : ''}>Yearly</option>
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="slide_edit_start_date" class="form-label">Start Date</label>
                        <input type="date" class="form-control bg-dark text-light" id="slide_edit_start_date" 
                               name="start_date" value="${budget.start_date}">
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="slide_edit_category_id" class="form-label">Category</label>
                    <select class="form-select bg-dark text-light" id="slide_edit_category_id" name="category_id" required>
                        <option value="">Select a category</option>
                        <!-- Category options will be populated via JavaScript -->
                    </select>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="slide_edit_include_subcategories" 
                                   name="include_subcategories" ${budget.include_subcategories ? 'checked' : ''}>
                            <label class="form-check-label" for="slide_edit_include_subcategories">
                                Include subcategories in budget
                            </label>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="slide_edit_is_recurring" 
                                   name="is_recurring" ${budget.is_recurring ? 'checked' : ''}>
                            <label class="form-check-label" for="slide_edit_is_recurring">
                                Recurring budget
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="d-flex justify-content-end">
                    <button type="button" class="btn btn-secondary me-2" onclick="closeBudgetSlidePanel()">
                        Cancel
                    </button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save me-1"></i> Save Changes
                    </button>
                </div>
            </div>
        </form>
    `;
    
    // Populate category select dropdown
    populateCategoryOptions('slide_edit_category_id', budget.category_id);
    
    // Add form submit handler
    const form = document.getElementById('slide-panel-edit-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch(this.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to update budget');
            return response.text();
        })
        .then(() => {
            // Show success notification
            showToast('Budget updated successfully!', 'success');
            
            // Close the panel
            closeBudgetSlidePanel();
            
            // Refresh the budget data
            updateBudgetProgressBars();
            
            // Refresh the page after a delay to show updated data
            setTimeout(() => window.location.reload(), 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error updating budget: ' + error.message, 'error');
        });
    });
}

/**
 * Delete a budget
 * @param {string} budgetId - Budget ID to delete
 */
function deleteBudget(budgetId) {
    if (confirm('Are you sure you want to delete this budget? This action cannot be undone.')) {
        // Create a form dynamically to submit the delete request
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/budgets/delete/${budgetId}`;
        document.body.appendChild(form);
        form.submit();
    }
}

/**
 * Populate category options
 * @param {string} selectId - ID of select element to populate
 * @param {string} selectedCategoryId - ID of category to select
 */
function populateCategoryOptions(selectId, selectedCategoryId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Get categories from the existing page dropdown
    const existingCategorySelect = document.getElementById('edit_category_id');
    if (existingCategorySelect) {
        // Clone options from existing select
        select.innerHTML = existingCategorySelect.innerHTML;
        
        // Set selected option
        if (selectedCategoryId) {
            const option = select.querySelector(`option[value="${selectedCategoryId}"]`);
            if (option) option.selected = true;
        }
    }
}

// Export form functions
export {
    toggleBudgetForm,
    openAddBudgetPanel,
    closeAddBudgetPanel,
    editBudget,
    openBudgetSlidePanel,
    closeBudgetSlidePanel,
    deleteBudget,
    populateCategoryOptions
};
