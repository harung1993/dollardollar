/**
 * Budget utility functions
 */

import { formatCurrency, showToast } from '../common/utils.js';
import { refreshDonutChart } from './budget-charts.js';

/**
 * Update the budget progress bars for each budget
 */
function updateBudgetProgressBars() {
    // Show refresh indicator on button if it exists
    const refreshButton = document.querySelector('.refresh-budget-button');
    if (refreshButton) {
        refreshButton.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
        refreshButton.disabled = true;
    }
    
    // Get all budget rows
    const budgetRows = document.querySelectorAll('.budget-row');
    
    // Create an array of promises for each budget update
    const updatePromises = Array.from(budgetRows).map(row => {
        const budgetId = row.getAttribute('data-budget-id');
        if (!budgetId) return Promise.resolve();
        
        // Fetch updated budget data
        return fetch(`/budgets/get/${budgetId}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success) return;
                
                // Update the progress bar
                const progressBar = row.querySelector('.progress-bar');
                if (progressBar) {
                    // Set width
                    progressBar.style.width = `${data.budget.percentage}%`;
                    progressBar.setAttribute('aria-valuenow', data.budget.percentage);
                    
                    // Update color based on status
                    progressBar.classList.remove('bg-success', 'bg-warning', 'bg-danger');
                    if (data.budget.status === 'over') {
                        progressBar.classList.add('bg-danger');
                    } else if (data.budget.status === 'approaching') {
                        progressBar.classList.add('bg-warning');
                    } else {
                        progressBar.classList.add('bg-success');
                    }
                }
                
                // Update the percentage text
                const percentageText = row.querySelector('small.d-block.mt-1');
                if (percentageText) {
                    percentageText.textContent = `${data.budget.percentage.toFixed(1)}% (${formatCurrency(data.budget.spent)})`;
                }
            })
            .catch(error => {
                console.error(`Error updating budget ${budgetId}:`, error);
            });
    });
    
    // Wait for all updates to complete, then refresh summary data
    Promise.all(updatePromises)
        .then(() => {
            // First refresh the summary data from the server
            return refreshBudgetSummary();
        })
        .then(() => {
            // Then refresh the donut chart with the updated data
            refreshDonutChart();
            
            // Also refresh the bar chart if a budget is selected
            const selectedBudget = document.querySelector('.budget-row.selected-budget');
            if (selectedBudget) {
                const selectedBudgetId = selectedBudget.getAttribute('data-budget-id');
                if (selectedBudgetId) {
                    import('./budget-charts.js').then(module => {
                        module.initializeBarChart(selectedBudgetId);
                    });
                }
            } else {
                // If no budget is selected, refresh the overall trends
                import('./budget-charts.js').then(module => {
                    module.initializeBarChart();
                });
            }
            
            // Reset refresh button
            if (refreshButton) {
                refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
                refreshButton.disabled = false;
            }
            
            showToast('Budgets refreshed successfully!', 'success', 2000);
        })
        .catch(error => {
            console.error('Error updating budgets:', error);
            
            // Reset refresh button
            if (refreshButton) {
                refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
                refreshButton.disabled = false;
            }
            
            showToast('Error refreshing budgets. Please try again.', 'error');
        });
}
/**
 * Refresh the overall budget summary data
 */
function refreshBudgetSummary() {
    // Add a small delay to ensure backend has processed updates
    return new Promise(resolve => setTimeout(resolve, 300))
        .then(() => {
            return fetch('/budgets/summary-data?_=' + new Date().getTime());;``
        })
        .then(response => response.json())
        .then(data => {
            
            if (!data.success) {
                throw new Error(data.message || 'Failed to fetch budget summary data');
            }
            
            // Update total budget
            const totalBudgetElement = document.getElementById('total-month-budget');
            if (totalBudgetElement) {
                totalBudgetElement.textContent = formatCurrency(data.total_budget);
            }
            
            // Update total spent
            const totalSpentElement = document.getElementById('total-month-spent');
            if (totalSpentElement) {
                totalSpentElement.textContent = formatCurrency(data.total_spent);
            }
            
            // Update remaining
            const remainingElement = document.getElementById('total-month-remaining');
            if (remainingElement) {
                const remaining = data.total_budget - data.total_spent;
                remainingElement.textContent = formatCurrency(Math.abs(remaining));
                
                // Add visual indicators based on remaining amount
                if (remaining < 0) {
                    remainingElement.classList.add('text-danger');
                    remainingElement.classList.remove('text-success');
                    if (!remainingElement.querySelector('.fa-arrow-down')) {
                        remainingElement.innerHTML += ' <i class="fas fa-arrow-down text-danger"></i>';
                    }
                } else {
                    remainingElement.classList.remove('text-danger');
                    remainingElement.classList.add('text-success');
                    // Remove any existing arrow icons
                    const arrow = remainingElement.querySelector('.fa-arrow-down');
                    if (arrow) {
                        arrow.remove();
                    }
                }
            }
            
            // Refresh the donut chart only after we've updated the summary data
            refreshDonutChart();
            
            return data;
        })
        .catch(error => {
            console.error('Error refreshing budget summary:', error);
            showToast('Error refreshing budget data', 'error');
            throw error;
        });
}

/**
 * Setup budget table interaction
 */
function setupBudgetTableInteraction() {
    const budgetRows = document.querySelectorAll('.budget-row');
    
    budgetRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger when clicking action buttons
            if (e.target.closest('.dropdown') || e.target.tagName === 'INPUT') {
                return;
            }
            
            // Get budget ID and name
            const budgetId = this.getAttribute('data-budget-id');
            const nameElement = this.querySelector('.budget-name');
            const budgetName = nameElement ? nameElement.textContent : 'Selected Budget';
            
            // Mark this row as selected
            selectBudgetRow(this, budgetId, budgetName);
            
            // Load transactions for this budget
            import('./budget-transactions.js').then(module => {
                module.loadBudgetTransactions(budgetId);
            });
        });
    });
}

/**
 * Select a budget row and update related elements
 * @param {HTMLElement} row - Row element to select
 * @param {string} budgetId - Budget ID
 * @param {string} budgetName - Budget name
 */
function selectBudgetRow(row, budgetId, budgetName) {
    // Remove selection from all rows
    const allRows = document.querySelectorAll('.budget-row');
    allRows.forEach(r => r.classList.remove('selected-budget'));
    
    // Add selection to this row
    row.classList.add('selected-budget');
    
    // Update selection info
    const selectionElement = document.getElementById('selected-budget-name');
    const resetButton = document.getElementById('reset-budget-selection');
    
    if (selectionElement) {
        selectionElement.textContent = budgetName;
    }
    
    if (resetButton) {
        resetButton.style.display = 'inline-block';
    }
    
    // Update bar chart for selected budget
    import('./budget-charts.js').then(module => {
        module.initializeBarChart(budgetId);
    });
}

/**
 * Reset budget selection
 */
function resetBudgetSelection() {
    // Remove selection from all rows
    const allRows = document.querySelectorAll('.budget-row');
    allRows.forEach(r => r.classList.remove('selected-budget'));
    
    // Reset selection info
    const selectionElement = document.getElementById('selected-budget-name');
    const resetButton = document.getElementById('reset-budget-selection');
    
    if (selectionElement) {
        selectionElement.textContent = 'All Budgets';
    }
    
    if (resetButton) {
        resetButton.style.display = 'none';
    }
    
    // Reset charts to show all budgets
    import('./budget-charts.js').then(module => {
        module.initializeBarChart();
    });
    
    // Clear transactions view
    const transactionsContainer = document.getElementById('budget-transactions-container');
    if (transactionsContainer) {
        transactionsContainer.innerHTML = `
            <div class="text-center py-4">
                <p class="text-muted">Select a budget to view related transactions.</p>
            </div>
        `;
    }
    
    // Reset transaction count
    const countBadge = document.getElementById('transaction-count-badge');
    if (countBadge) {
        countBadge.textContent = '0 transactions';
    }
}

// Export utility functions
export {
    updateBudgetProgressBars,
    refreshBudgetSummary,
    setupBudgetTableInteraction,
    selectBudgetRow,
    resetBudgetSelection
};