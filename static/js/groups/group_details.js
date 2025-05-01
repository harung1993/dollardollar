/**
 * Complete Group Details Page Fix - Dollar Dollar Bill Y'all
 * 
 * This comprehensive fix addresses:
 * 1. CSS styling conflicts by using !important and more specific selectors
 * 2. Contribution calculation by properly handling expense splits 
 * 3. Non-working buttons through proper event binding
 */

// Store group data for use with Transaction Module
let groupData = {
    id: null,
    name: '',
    members: [],
    defaultSplitMethod: 'equal',
    defaultPayer: null,
    autoIncludeAll: true,
    defaultSplitValues: {}
};

// Store current expense ID for deletion
let currentExpenseId = null;
let deleteModalInitialized = false;

/**
 * Initialize everything when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Group details JS loading...');
    
    // Add CSS fixes first to prevent flicker
    addCSSFixes();
    
    // Init components
    loadGroupData();
    initializeComponents();
    setupEventListeners();
    
    console.log('Group details initialization complete');
});

/**
 * Add CSS fixes to override conflicting styles
 */
function addCSSFixes() {
    const style = document.createElement('style');
    style.id = 'group-details-fixes';
    style.innerHTML = `
        /* Fix table styles */
        .table-modern {
            width: 100% !important;
            border-collapse: separate !important;
            border-spacing: 0 !important;
        }
        
        .table-modern thead th {
            background-color: rgba(0, 0, 0, 0.2) !important;
            color: rgba(255, 255, 255, 0.75) !important;
            font-weight: 600 !important;
            padding: 12px 15px !important;
            font-size: 0.85rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        
        .table-modern tbody tr {
            transition: background-color 0.2s !important;
        }
        
        .table-modern tbody tr:hover {
            background-color: rgba(255, 255, 255, 0.05) !important;
        }
        
        .table-modern td {
            padding: 12px 15px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03) !important;
            vertical-align: middle !important;
            color: rgba(255, 255, 255, 0.85) !important;
        }
        
        /* Month row styling */
        .expense-month-row {
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            background-color: rgba(17, 24, 39, 0.8) !important;
        }
        
        .expense-month-row:hover {
            background-color: rgba(30, 41, 59, 0.8) !important;
        }
        
        .expense-month-row.active {
            background-color: rgba(59, 130, 246, 0.1) !important;
            border-left: 3px solid rgba(59, 130, 246, 0.8) !important;
        }
        
        /* Detail row styling - more subtle from dashboard */
        .expense-detail {
            background-color: rgba(30, 41, 59, 0.3) !important;
        }
        
        .expense-detail-container {
            padding: 1rem !important;
            border-radius: 8px !important;
        }
        
        /* Member list fixes */
        .member-item {
            background-color: rgba(23, 32, 42, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            margin-bottom: 0.5rem !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        
        /* Fix pill styling for contributors */
        .pill {
            display: inline-flex !important;
            align-items: center !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 50px !important;
            padding: 0.35rem 0.8rem !important;
            margin-right: 0.5rem !important;
            margin-bottom: 0.5rem !important;
            font-size: 0.8rem !important;
            white-space: nowrap !important;
            max-width: 100% !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        
        .pill-amount {
            margin-left: 0.4rem !important;
            opacity: 0.8 !important;
            font-size: 0.75rem !important;
            background-color: rgba(0, 0, 0, 0.2) !important;
            padding: 0.15rem 0.4rem !important;
            border-radius: 50px !important;
        }
        
        /* Fix color issues with category names */
        .list-group-item .category-name-text {
            color: white !important;
            -webkit-text-fill-color: white !important;
        }
        
        /* Fix for toggle button visibility */
        .btn-close {
            opacity: 0.8 !important;
        }
        
        /* Fix form inputs */
        .form-control.bg-dark {
            background-color: #1e293b !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }
        
        /* Fix for buttons to make them stand out */
        .btn {
            position: relative !important;
            overflow: hidden !important;
        }
        
        /* Make delete button more noticeable */
        .delete-expense-btn {
            background-color: rgba(220, 38, 38, 0.1) !important;
            border-color: rgba(220, 38, 38, 0.5) !important;
        }
        
        .delete-expense-btn:hover {
            background-color: rgba(220, 38, 38, 0.2) !important;
            border-color: rgba(220, 38, 38, 0.8) !important;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Load group data from the page
 */
function loadGroupData() {
    // Get group ID from URL
    const urlParts = window.location.pathname.split('/');
    const groupId = urlParts[urlParts.length - 1];
    
    // Extract group settings from page elements
    groupData = {
        id: groupId,
        name: document.querySelector('.card-header h4')?.textContent?.trim() || 'Group',
        defaultSplitMethod: document.querySelector('.default-split-badge')?.textContent?.trim().toLowerCase() || 'equal',
        defaultPayer: document.getElementById('default_payer')?.value || null,
        autoIncludeAll: document.querySelector('.default-split-item .form-check-input')?.checked || true,
        defaultSplitValues: {},
        members: []
    };
    
    // Extract member information
    document.querySelectorAll('.member-item').forEach(item => {
        const memberName = item.querySelector('.member-name')?.textContent?.trim().split('\n')[0] || 'Member';
        const memberId = item.querySelector('.member-email')?.textContent?.trim() || '';
        
        if (memberId) {
            groupData.members.push({
                id: memberId,
                name: memberName
            });
        }
    });
    
    // Try to parse default split values
    try {
        // Look for data attribute with split values
        const splitValuesData = document.querySelector('[data-split-values]')?.getAttribute('data-split-values');
        if (splitValuesData) {
            groupData.defaultSplitValues = JSON.parse(splitValuesData);
        }
    } catch (e) {
        console.warn('Error parsing default split values:', e);
    }
    
    console.log('Loaded group data:', groupData);
    
    // Make sure the data is available globally
    window.groupsData = window.groupsData || {};
    window.groupsData[groupId] = groupData;
}

/**
 * Initialize all components
 */
function initializeComponents() {
    // Initialize today's date for date inputs
    initializeDateInputs();
    
    // Initialize group settings modal
    setupGroupSettingsModal();
    
    // Initialize category split display
    initCategorySplitDisplay();
    
    // Initialize expense month rows
    initializeExpenseMonthRows();
    
    // Initialize delete confirmation modal
    initializeDeleteModal();
    
    // Fix contribution calculation 
    fixContributionCalculation();
}

/**
 * Initialize date inputs with today's date
 */
function initializeDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        if (!input.value) {
            input.value = today;
        }
    });
}

/**
 * Initialize the delete confirmation modal
 */
function initializeDeleteModal() {
    // Only initialize once
    if (deleteModalInitialized) return;
    
    const modal = document.getElementById('deleteConfirmModal');
    if (!modal) {
        console.error("Delete confirmation modal not found");
        
        // Create one if it doesn't exist
        const modalHTML = `
            <div class="modal fade" id="deleteConfirmModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content bg-dark text-light">
                        <div class="modal-header">
                            <h5 class="modal-title">Confirm Deletion</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p>Are you sure you want to delete this expense? This action cannot be undone.</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmDeleteBtn">Delete</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    // Initialize delete confirmation button
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            if (currentExpenseId) {
                deleteExpense(currentExpenseId);
            }
        });
        deleteModalInitialized = true;
    }
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    console.log("Setting up event listeners");
    
    // Toggle member form
    const toggleMemberBtn = document.getElementById('toggleMemberForm');
    if (toggleMemberBtn) {
        toggleMemberBtn.addEventListener('click', toggleMemberForm);
        console.log("Member form toggle button listener added");
    }
    
    // Add expense buttons
    document.querySelectorAll('.add-expense-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const groupId = this.getAttribute('data-group-id');
            if (window.AddTransactionModule) {
                window.AddTransactionModule.openAddPanel(window.groupsData[groupId]);
            } else {
                console.error('AddTransactionModule not found. Please include add_transaction.js');
                alert('Transaction module is not available. Please refresh the page and try again.');
            }
        });
    });
    
    // Delete expense buttons - use event delegation
    document.addEventListener('click', function(event) {
        // Check for delete button
        const deleteBtn = event.target.closest('.delete-expense-btn');
        if (deleteBtn) {
            event.preventDefault();
            const expenseId = deleteBtn.getAttribute('data-expense-id');
            if (expenseId) {
                currentExpenseId = expenseId;
                
                // Show deletion modal
                const modalEl = document.getElementById('deleteConfirmModal');
                if (modalEl && typeof bootstrap !== 'undefined') {
                    const modal = new bootstrap.Modal(modalEl);
                    modal.show();
                } else {
                    // Fallback if Bootstrap isn't available
                    if (confirm('Are you sure you want to delete this expense? This action cannot be undone.')) {
                        deleteExpense(expenseId);
                    }
                }
            }
        }
        
        // Check for edit button
        const editBtn = event.target.closest('.edit-expense-btn');
        if (editBtn) {
            event.preventDefault();
            const expenseId = editBtn.getAttribute('data-expense-id');
            if (expenseId && window.EditTransactionModule) {
                window.EditTransactionModule.openEditPanel(expenseId);
            }
        }
    });
}

/**
 * Delete an expense
 */
function deleteExpense(expenseId) {
    // Show loading state
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';
    }
    
    // Send AJAX request
    fetch(`/delete_expense/${expenseId}`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal
            const modalEl = document.getElementById('deleteConfirmModal');
            if (modalEl && typeof bootstrap !== 'undefined') {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                }
            }
            
            // Show success message
            showMessage('Expense deleted successfully!', 'success');
            
            // Reload page after a delay
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            throw new Error(data.message || 'Failed to delete expense');
        }
    })
    .catch(error => {
        console.error('Error deleting expense:', error);
        showMessage(error.message, 'error');
        
        // Reset button
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Delete';
        }
    });
}

/**
 * Toggle member form visibility
 */
function toggleMemberForm() {
    console.log("Toggling member form");
    
    const form = document.getElementById('memberFormContainer');
    const button = document.getElementById('toggleMemberForm');
    
    if (!form || !button) {
        console.error("Member form container or button not found");
        return;
    }
    
    if (form.style.display === 'none') {
        form.style.display = 'block';
        button.innerHTML = '<i class="fas fa-times"></i>';
        button.classList.replace('btn-primary', 'btn-secondary');
    } else {
        form.style.display = 'none';
        button.innerHTML = '<i class="fas fa-plus"></i>';
        button.classList.replace('btn-secondary', 'btn-primary');
    }
}

/**
 * Group Settings Modal
 */
function setupGroupSettingsModal() {
    // Open settings modal
    const editGroupSettingsBtn = document.getElementById('editGroupSettingsBtn');
    if (editGroupSettingsBtn) {
        editGroupSettingsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openGroupSettingsModal();
        });
    }
    
    // Open split settings directly
    const editSplitSettingsBtn = document.getElementById('editSplitSettingsBtn');
    if (editSplitSettingsBtn) {
        editSplitSettingsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openSplitSettingsModal();
        });
    }
    
    // Handle split method change
    const defaultSplitMethodSelect = document.getElementById('default_split_method');
    if (defaultSplitMethodSelect) {
        defaultSplitMethodSelect.addEventListener('change', toggleDefaultSplitOptions);
    }
    
    // Save settings button - use form submission instead of click handler
    const groupSettingsForm = document.getElementById('groupSettingsForm');
    if (groupSettingsForm) {
        groupSettingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveGroupSettings();
        });
    }
    
    // Cancel settings button
    const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
    if (cancelSettingsBtn) {
        cancelSettingsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSettingsForm(false);
        });
    }
}

function openGroupSettingsModal() {
    toggleSettingsForm(true);
    
    // Initialize default split options
    toggleDefaultSplitOptions();
}

function openSplitSettingsModal() {
    openGroupSettingsModal();
    
    // Focus on split method select
    setTimeout(() => {
        const defaultSplitMethodSelect = document.getElementById('default_split_method');
        if (defaultSplitMethodSelect) {
            defaultSplitMethodSelect.focus();
        }
    }, 300);
}

/**
 * Toggle the settings form display
 */
function toggleSettingsForm(show) {
    const infoDisplay = document.getElementById('group-info-display');
    const settingsForm = document.getElementById('group-settings-form');
    
    if (!infoDisplay || !settingsForm) return;
    
    // If show parameter is provided, use it; otherwise toggle current state
    const showForm = (show !== undefined) ? show : (settingsForm.style.display === 'none');
    
    if (showForm) {
        // Show settings form, hide info display
        infoDisplay.style.display = 'none';
        settingsForm.style.display = 'block';
        
        // Focus on first field
        document.getElementById('group_name')?.focus();
        
        // Initialize default split options
        toggleDefaultSplitOptions();
    } else {
        // Hide settings form, show info display
        settingsForm.style.display = 'none';
        infoDisplay.style.display = 'block';
    }
}

/**
 * Toggle visibility of default split options in settings modal
 */
function toggleDefaultSplitOptions() {
    const splitMethodSelect = document.getElementById('default_split_method');
    const splitContainer = document.getElementById('default_split_container');
    
    if (!splitMethodSelect || !splitContainer) return;
    
    const splitMethod = splitMethodSelect.value;
    
    if (splitMethod === 'equal') {
        splitContainer.style.display = 'none';
    } else {
        splitContainer.style.display = 'block';
        
        // Update instruction text
        const instructionEl = document.getElementById('default_split_instruction');
        if (instructionEl) {
            if (splitMethod === 'percentage') {
                instructionEl.textContent = 'Define what percentage each member pays by default';
            } else {
                instructionEl.textContent = 'Define custom amounts each member pays by default';
            }
        }
        
        // Update the split values UI
        updateDefaultSplitValues();
    }
}

/**
 * Update default split values UI in settings modal
 */
function updateDefaultSplitValues() {
    const splitMethodSelect = document.getElementById('default_split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    const container = document.getElementById('default_split_values_container');
    const valuesInput = document.getElementById('default_split_values');
    
    if (!container || !valuesInput) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Try to load existing split values from the page or from the input
    let splitValues = {};
    try {
        if (valuesInput.value) {
            splitValues = JSON.parse(valuesInput.value);
        } else if (groupData.defaultSplitValues && Object.keys(groupData.defaultSplitValues).length > 0) {
            splitValues = groupData.defaultSplitValues;
        }
    } catch (e) {
        console.warn('Error parsing existing split values:', e);
    }
    
    // Get all members from the page
    const members = [];
    document.querySelectorAll('.member-item').forEach(item => {
        const memberName = item.querySelector('.member-name')?.textContent?.trim() || 'Member';
        const memberId = item.querySelector('.member-email')?.textContent?.trim() || '';
        
        members.push({
            id: memberId,
            name: memberName.split('\n')[0].trim() // Get just the name part
        });
    });
    
    // Generate UI based on split method
    if (splitMethod === 'percentage') {
        // Equal percentages by default
        const equalPercentage = members.length ? (100 / members.length) : 0;
        
        members.forEach(member => {
            // Use existing value or default to equal percentage
            const percentage = splitValues[member.id] !== undefined ? 
                              splitValues[member.id] : equalPercentage;
            
            // Create UI row
            const row = document.createElement('div');
            row.className = 'row mb-2 align-items-center';
            row.innerHTML = `
                <div class="col-md-6">
                    <span class="badge bg-secondary me-1">${member.name}</span>
                </div>
                <div class="col-md-6">
                    <div class="input-group">
                        <input type="number" class="form-control bg-dark text-light default-split-input"
                               data-user-id="${member.id}" step="0.1" min="0" max="100" 
                               value="${percentage.toFixed(1)}">
                        <span class="input-group-text bg-dark text-light">%</span>
                    </div>
                </div>
            `;
            container.appendChild(row);
            
            // Ensure value is in splitValues
            splitValues[member.id] = percentage;
        });
    } else { // Custom amount
        // For custom amount, we'll use placeholder values (e.g. 10.00 for each)
        const baseCurrencySymbol = window.baseCurrencySymbol || '$';
        
        members.forEach(member => {
            // Use existing value or default to 10.00
            const amount = splitValues[member.id] !== undefined ? 
                          splitValues[member.id] : 10.00;
            
            // Create UI row
            const row = document.createElement('div');
            row.className = 'row mb-2 align-items-center';
            row.innerHTML = `
                <div class="col-md-6">
                    <span class="badge bg-secondary me-1">${member.name}</span>
                </div>
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                        <input type="number" class="form-control bg-dark text-light default-split-input"
                               data-user-id="${member.id}" step="0.01" min="0" 
                               value="${amount.toFixed(2)}">
                    </div>
                </div>
            `;
            container.appendChild(row);
            
            // Ensure value is in splitValues
            splitValues[member.id] = amount;
        });
    }
    
    // Add listeners to inputs
    setupDefaultSplitInputListeners(splitMethod, splitValues);
}

/**
 * Set up input listeners for default split values
 */
function setupDefaultSplitInputListeners(splitMethod, splitValues) {
    const valuesInput = document.getElementById('default_split_values');
    if (!valuesInput) return;
    
    document.querySelectorAll('.default-split-input').forEach(input => {
        input.addEventListener('input', function() {
            const userId = this.getAttribute('data-user-id');
            const value = parseFloat(this.value) || 0;
            splitValues[userId] = value;
            
            // Update hidden field
            valuesInput.value = JSON.stringify(splitValues);
            
            // For percentage splits, validate the total
            if (splitMethod === 'percentage') {
                const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
                const statusEl = document.getElementById('default_split_status');
                
                if (statusEl) {
                    if (Math.abs(total - 100) < 0.1) {
                        statusEl.textContent = 'Balanced (100%)';
                        statusEl.className = 'badge bg-success';
                    } else if (total < 100) {
                        statusEl.textContent = `Underfunded (${total.toFixed(1)}%)`;
                        statusEl.className = 'badge bg-warning';
                    } else {
                        statusEl.textContent = `Overfunded (${total.toFixed(1)}%)`;
                        statusEl.className = 'badge bg-danger';
                    }
                }
            }
        });
        
        // Initialize by triggering input event
        input.dispatchEvent(new Event('input'));
    });
}

/**
 * Save group settings
 */
function saveGroupSettings() {
    // Show loading state
    const saveBtn = document.getElementById('saveGroupSettingsBtn');
    if (!saveBtn) return;
    
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving...';
    
    // Get group ID
    const groupId = groupData.id;
    if (!groupId) {
        console.error('Group ID not found');
        return;
    }
    
    // Collect form data
    const formData = new FormData();
    
    const groupNameInput = document.getElementById('group_name');
    if (groupNameInput) {
        formData.append('group_name', groupNameInput.value);
    }
    
    const groupDescriptionInput = document.getElementById('group_description');
    if (groupDescriptionInput) {
        formData.append('group_description', groupDescriptionInput.value);
    }
    
    const autoIncludeAllInput = document.getElementById('auto_include_all');
    if (autoIncludeAllInput) {
        formData.append('auto_include_all', autoIncludeAllInput.checked ? 'true' : 'false');
    }
    
    const defaultPayerSelect = document.getElementById('default_payer');
    if (defaultPayerSelect) {
        formData.append('default_payer', defaultPayerSelect.value);
    }
    
    const defaultSplitMethodSelect = document.getElementById('default_split_method');
    if (defaultSplitMethodSelect) {
        formData.append('default_split_method', defaultSplitMethodSelect.value);
    }
    
    // Add split values if applicable
    const splitMethod = defaultSplitMethodSelect ? defaultSplitMethodSelect.value : 'equal';
    if (splitMethod !== 'equal') {
        const splitValuesInput = document.getElementById('default_split_values');
        if (splitValuesInput && splitValuesInput.value) {
            formData.append('default_split_values', splitValuesInput.value);
        }
    }
    
    // Send AJAX request
    fetch(`/update_group_settings/${groupId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save group settings');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success toast
            showMessage('Group settings saved successfully!', 'success');
            
            // Close the modal
            toggleSettingsForm(false);
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            throw new Error(data.message || 'Unknown error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Show error toast
        showMessage(`Error: ${error.message}`, 'error');
        
        // Reset button
        saveBtn.disabled = false;
        saveBtn.innerHTML = 'Save Changes';
    });
}

/**
 * Initialize category split display
 */
function initCategorySplitDisplay() {
    document.querySelectorAll('.category-split-container[data-has-splits="true"]').forEach(container => {
        const toggle = container.querySelector('.split-toggle');
        const expenseId = container.getAttribute('data-expense-id');
        
        if (toggle && expenseId) {
            toggle.addEventListener('click', function() {
                const detailElement = document.getElementById(`split-categories-${expenseId}`);
                
                if (detailElement) {
                    // Toggle visibility
                    if (detailElement.style.display === 'none') {
                        detailElement.style.display = 'block';
                        this.querySelector('i').classList.replace('fa-chevron-down', 'fa-chevron-up');
                        
                        // Load split details if needed
                        if (detailElement.querySelector('.loading')) {
                            loadCategorySplits(expenseId, detailElement);
                        }
                    } else {
                        detailElement.style.display = 'none';
                        this.querySelector('i').classList.replace('fa-chevron-up', 'fa-chevron-down');
                    }
                }
            });
        }
    });
}

/**
 * Load category splits via AJAX
 */
function loadCategorySplits(expenseId, detailElement) {
    // Show loading indicator
    detailElement.innerHTML = '<div class="text-center"><span class="spinner-border spinner-border-sm me-2"></span>Loading...</div>';
    
    fetch(`/get_category_splits/${expenseId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.splits && data.splits.length > 0) {
                // Create split detail UI
                let html = '<div class="list-group list-group-flush" style="background-color: #374151; border-radius: 6px; color: white !important;">';
                
                data.splits.forEach(split => {
                    // Get category details
                    const categoryName = split.category?.name || 'Unknown';
                    const categoryColor = split.category?.color || '#6c757d';
                    const categoryIcon = split.category?.icon || 'fa-tag';
                    const amount = parseFloat(split.amount) || 0;
                    const baseCurrencySymbol = window.baseCurrencySymbol || '$';
                    
                    html += `
                        <div class="list-group-item py-2" style="background-color: #374151; border-color: #4b5563; color: white !important;">
                            <div class="d-flex justify-content-between align-items-center">
                                <div style="color: white !important;">
                                    <span class="badge me-2" style="background-color: ${categoryColor};">
                                        <i class="fas ${categoryIcon}"></i>
                                    </span>
                                    <span class="category-name-text" style="color: white !important;">${categoryName}</span>
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
                
                // Add additional style to ensure text is visible
                const styleId = `style-category-${expenseId}`;
                const existingStyle = document.getElementById(styleId);
                if (existingStyle) existingStyle.remove();
                
                const style = document.createElement('style');
                style.id = styleId;
                style.textContent = `
                    #split-categories-${expenseId} .list-group-item,
                    #split-categories-${expenseId} .category-name-text,
                    #split-categories-${expenseId} .list-group-item * {
                        color: white !important;
                    }
                `;
                document.head.appendChild(style);
            } else {
                detailElement.innerHTML = '<div class="text-white p-2">No category splits found</div>';
            }
        })
        .catch(error => {
            console.error('Error loading category splits:', error);
            detailElement.innerHTML = `<div class="text-danger p-2">Error loading splits: ${error.message}</div>`;
        });
}

/**
 * Initialize expense month rows
 */
function initializeExpenseMonthRows() {
    // Add event listeners to toggle-details buttons
    document.querySelectorAll('.toggle-details').forEach(btn => {
        btn.addEventListener('click', function() {
            const monthRow = this.closest('tr');
            const monthId = this.getAttribute('data-bs-target');
            
            // Toggle active class
            if (monthRow) {
                monthRow.classList.toggle('active');
                
                // Update button icon
                const icon = this.querySelector('i');
                if (icon) {
                    if (monthRow.classList.contains('active')) {
                        icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                    } else {
                        icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                    }
                }
            }
        });
    });
}

/**
 * Fix contribution calculation to properly attribute split amounts
 * instead of attributing full expense amount to the payer
 */
function fixContributionCalculation() {
    // Find all months in the table
    const monthRows = document.querySelectorAll('.expense-month-row');
    if (!monthRows.length) {
        console.log("No month rows found for contribution calculation");
        return;
    }
    
    console.log(`Found ${monthRows.length} month rows to process`);
    
    // Process each month
    monthRows.forEach(monthRow => {
        const monthId = monthRow.getAttribute('data-month');
        if (!monthId) return;
        
        console.log(`Processing month: ${monthId}`);
        
        // Create a map to store the correct contribution amounts by user
        const correctContributions = {};
        
        // Find the collapse container for this month
        const collapseId = `month${monthId.replace('-', '')}`;
        const collapseContainer = document.getElementById(collapseId);
        
        if (!collapseContainer) {
            console.log(`Collapse container not found for month ${monthId}`);
            return;
        }
        
        // Find expense rows in the details table within this month's container
        const expenseRows = collapseContainer.querySelectorAll('tbody tr');
        console.log(`Found ${expenseRows.length} expense rows for month ${monthId}`);
        
        // Process each expense to get the actual split amounts
        expenseRows.forEach(row => {
            // Get the split cells - at 7th column (index 6) in the table
            const splitCell = row.querySelector('td:nth-child(7)');
            if (!splitCell) return;
            
            // Find all split entries (each is a small tag)
            const splitEntries = splitCell.querySelectorAll('small');
            splitEntries.forEach(splitEntry => {
                // Each split entry should have format: "User: $X.XX"
                const badgeEl = splitEntry.querySelector('.badge');
                if (!badgeEl) return;
                
                // Get user name from badge
                const userName = badgeEl.textContent.trim();
                
                // Get amount from text after badge (format: ": $X.XX")
                const amountText = splitEntry.textContent.split(':')[1]?.trim();
                if (!amountText) return;
                
                // Parse amount - remove currency symbol and convert to number
                const amount = parseFloat(amountText.replace(/[^0-9.-]+/g, '')) || 0;
                
                // Add to user's contribution total
                if (!correctContributions[userName]) {
                    correctContributions[userName] = 0;
                }
                correctContributions[userName] += amount;
            });
        });
        
        console.log(`Calculated contributions for month ${monthId}:`, correctContributions);
        
        // Update the monthly summary contributors display
        if (Object.keys(correctContributions).length > 0) {
            // Find the contributors cell (4th column, index 3)
            const contributorsCell = monthRow.querySelector('td:nth-child(4)');
            if (!contributorsCell) {
                console.log("Contributors cell not found");
                return;
            }
            
            // Create new HTML for the contributors display
            const sortedContributors = Object.entries(correctContributions)
                .sort((a, b) => b[1] - a[1]);
            
            let newHtml = '';
            
            // Show top contributors (up to 2)
            sortedContributors.slice(0, 2).forEach(([userName, amount]) => {
                // Try to find badge color for this user
                const userBadges = document.querySelectorAll('.badge');
                let bgColor = '#15803d'; // Default color
                
                // Look for badge with this user name
                for (const badge of userBadges) {
                    if (badge.textContent.trim() === userName) {
                        // Get the background color
                        const style = window.getComputedStyle(badge);
                        if (style.backgroundColor && style.backgroundColor !== 'transparent') {
                            bgColor = style.backgroundColor;
                            break;
                        }
                    }
                }
                
                // Create pill for this user
                newHtml += `
                    <div class="pill" style="background-color: ${bgColor};">
                        ${userName}
                        <span class="pill-amount">${window.baseCurrencySymbol || '$'}${amount.toFixed(2)}</span>
                    </div>
                `;
            });
            
            // Add "more" badge if there are additional contributors
            if (sortedContributors.length > 2) {
                newHtml += `<span class="badge bg-secondary">+${sortedContributors.length - 2} more</span>`;
            }
            
            // Update the contributors cell content
            if (newHtml) {
                contributorsCell.innerHTML = newHtml;
            } else {
                contributorsCell.innerHTML = '<span class="text-muted small">No contributors</span>';
            }
        }
    });
}

/**
 * Show a message toast
 */
function showMessage(message, type = 'success') {
    // If any Transaction module is available, use its showMessage function
    if (window.AddTransactionModule && typeof window.AddTransactionModule.showMessage === 'function') {
        return window.AddTransactionModule.showMessage(message, type);
    }
    
    if (window.EditTransactionModule && typeof window.EditTransactionModule.showMessage === 'function') {
        return window.EditTransactionModule.showMessage(message, type);
    }
    
    if (window.UIHelpers && typeof window.UIHelpers.showToast === 'function') {
        return window.UIHelpers.showToast(message, type);
    }
    
    // Fallback implementation
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create unique ID for this toast
    const toastId = `toast-${Date.now()}`;
    
    // Determine icon and colors based on type
    const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    const bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
    
    // Create toast HTML
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${bgClass} text-white">
                <i class="fas ${iconClass} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Get toast element and initialize Bootstrap toast
    const toastElement = document.getElementById(toastId);
    if (toastElement && typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();
        
        // Remove toast element when hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
        
        return toast;
    } else {
        // Simple fallback if Bootstrap is not available
        alert(`${type.toUpperCase()}: ${message}`);
        setTimeout(() => {
            toastElement?.remove();
        }, 5000);
        return null;
    }
}