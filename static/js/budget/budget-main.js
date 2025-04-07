/**
 * Budget page main initialization
 */

import { addCardHoverEffects } from '../common/utils.js';
import { initializeDonutChart, initializeBarChart } from './budget-charts.js';
import { setupBudgetTableInteraction, updateBudgetProgressBars, resetBudgetSelection } from './budget-utils.js';
import { toggleBudgetForm } from './budget-forms.js';
import { toggleTransactionDetails, editTransaction, confirmDeleteTransaction } from './budget-transactions.js';

/**
 * Initialize the budget page
 */
function initializeBudgetPage() {
    // Initialize today's date for the start date field
    const today = new Date().toISOString().split('T')[0];
    const startDateInput = document.getElementById('start_date');
    if (startDateInput) {
        startDateInput.value = today;
    }
    
    // Add toggle for budget form
    const toggleButton = document.getElementById('toggleBudgetForm');
    if (toggleButton) {
        toggleButton.addEventListener('click', toggleBudgetForm);
    }
    
    // Initialize charts
    initializeDonutChart();
    initializeBarChart();
    
    // Make budget rows clickable
    setupBudgetTableInteraction();
    
    // Add refresh button
    addRefreshButton();
    
    // Initialize reset button
    const resetButton = document.getElementById('reset-budget-selection');
    if (resetButton) {
        resetButton.addEventListener('click', resetBudgetSelection);
    }
    
    // Add hover effects to all cards
    addCardHoverEffects();
    
    // Add auto-refresh interval (every 30 seconds)
    setInterval(updateBudgetProgressBars, 30000);
    
    // Expose functions needed by inline event handlers
    window.toggleTransactionDetails = toggleTransactionDetails;
    window.editTransaction = editTransaction;
    window.confirmDeleteTransaction = confirmDeleteTransaction;
    window.toggleBudgetForm = toggleBudgetForm;
}

/**
 * Add refresh button to budget header
 */
function addRefreshButton() {
    const refreshButton = document.createElement('button');
    refreshButton.className = 'btn btn-sm btn-outline-secondary ms-2 refresh-budget-button';
    refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
    refreshButton.title = 'Refresh budget data';
    refreshButton.addEventListener('click', updateBudgetProgressBars);
    
    // Add to current month budget header
    const budgetHeader = document.querySelector('.card-header:has(#current-month)');
    if (budgetHeader) {
        const headerDiv = budgetHeader.querySelector('div');
        if (headerDiv) {
            headerDiv.appendChild(refreshButton);
        }
    }
}

// Initialize the page when DOM is ready
document.addEventListener('DOMContentLoaded', initializeBudgetPage);

// Export main initialization for direct use
export { initializeBudgetPage };