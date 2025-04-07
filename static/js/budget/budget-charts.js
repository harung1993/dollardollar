/**
 * Budget chart functions for visualizing budget data
 */

import { formatCurrency } from '../common/utils.js';

/**
 * Initialize the donut chart using budget data
 */
function initializeDonutChart() {
    const chartContainer = document.getElementById('budget-donut-container');
    if (!chartContainer) return;
    
    // Clear container
    chartContainer.innerHTML = '';
    
    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.id = 'budget-donut-chart';
    chartContainer.appendChild(canvas);
    
    // Get all budget rows to extract data and colors
    const budgetRows = document.querySelectorAll('.budget-row');
    
    // Prepare data for the chart
    const budgetData = [];
    const budgetColors = [];
    const budgetLabels = [];
    
    // Get totals from the summary elements
    const totalBudgetElement = document.getElementById('total-month-budget');
    const totalSpentElement = document.getElementById('total-month-spent');
    
    let totalMonthlyBudget = 0;
    let totalMonthlySpent = 0;
    
    if (totalBudgetElement && totalSpentElement) {
        // Parse the values from the elements (removing currency symbol and commas)
        totalMonthlyBudget = parseFloat(totalBudgetElement.textContent.replace(/[^0-9.-]+/g, ""));
        totalMonthlySpent = parseFloat(totalSpentElement.textContent.replace(/[^0-9.-]+/g, ""));
    }
    
    // Process each budget
    budgetRows.forEach(row => {
        // Only process monthly budgets
        const periodElement = row.querySelector('td:nth-child(2) small');
        if (!periodElement || !periodElement.textContent.includes('Monthly')) {
            return;
        }
        
        // Get budget amount
        const budgetCell = row.querySelector('td:nth-child(2)');
        if (!budgetCell) return;
        
        const budgetText = budgetCell.textContent;
        const budgetAmount = parseFloat(budgetText.replace(/[^0-9.-]+/g, ""));
        
        if (isNaN(budgetAmount)) return;
        
        // Get budget name
        const nameElement = row.querySelector('.budget-name');
        const budgetName = nameElement ? nameElement.textContent : 'Unknown';
        
        // Get budget color
        const badgeElement = row.querySelector('.badge');
        const budgetColor = badgeElement ? badgeElement.style.backgroundColor : '#6c757d';
        
        // Add to chart data
        budgetData.push(budgetAmount);
        budgetColors.push(budgetColor);
        budgetLabels.push(budgetName);
    });
    
    // If no budgets found, show empty chart message
    if (budgetData.length === 0) {
        chartContainer.innerHTML = '<p class="text-center text-muted my-5">No monthly budgets available</p>';
        return;
    }
    
    // Create chart
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: budgetLabels,
            datasets: [{
                data: budgetData,
                backgroundColor: budgetColors,
                borderWidth: 0,
                cutout: '70%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const percentage = Math.round((value / totalMonthlyBudget) * 100);
                            return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                        }
                    }
                }
            }
        },
        plugins: [{
            id: 'donutText',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                ctx.save();
                ctx.textAlign = 'center';
                
                // Percentage in the middle
                const percentage = Math.round((totalMonthlySpent / totalMonthlyBudget) * 100) || 0;
                ctx.font = 'bold 28px Arial';
                ctx.fillStyle = 'white';
                ctx.textBaseline = 'middle';
                ctx.fillText(`${percentage}%`, width / 2, height / 2 - 10);
                
                // "used" text below
                ctx.font = '12px Arial';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
                ctx.fillText('used', width / 2, height / 2 + 15);
                
                ctx.restore();
            }
        }]
    });
    
    // Update budget summary values
    updateBudgetSummary(totalMonthlyBudget, totalMonthlySpent);
}

/**
 * Update the budget summary display
 * @param {number} totalBudget - Total budget amount
 * @param {number} totalSpent - Total spent amount
 */
function updateBudgetSummary(totalBudget, totalSpent) {
    const budgetElement = document.getElementById('total-month-budget');
    const spentElement = document.getElementById('total-month-spent');
    const remainingElement = document.getElementById('total-month-remaining');
    const remainingAmount = totalBudget - totalSpent;
    
    if (budgetElement) {
        budgetElement.textContent = formatCurrency(totalBudget);
    }
    if (spentElement) {
        spentElement.textContent = formatCurrency(totalSpent);
    }
    if (remainingElement) {
        remainingElement.textContent = formatCurrency(Math.abs(remainingAmount));
        
        // Add visual indicators based on remaining amount
        if (remainingAmount < 0) {
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
}

/**
 * Initialize bar chart for budget trends
 * @param {string|null} selectedBudgetId - Optional ID of selected budget
 */
function initializeBarChart(selectedBudgetId = null) {
    const chartContainer = document.getElementById('budget-chart-container');
    if (!chartContainer) return;
    
    // Show loading spinner
    chartContainer.innerHTML = `
        <div class="d-flex justify-content-center align-items-center h-100">
            <div class="spinner-border text-secondary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    // Create the URL for the endpoint
    let url = '/budgets/trends-data';
    if (selectedBudgetId) {
        url += `?budget_id=${selectedBudgetId}`;
    }
    
    // Get chart data from server
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load budget trend data');
            }
            return response.json();
        })
        .then(data => {
            createBudgetChart(chartContainer, data);
        })
        .catch(error => {
            console.error('Error fetching budget trends:', error);
            chartContainer.innerHTML = `
                <div class="alert alert-warning text-center m-3">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Unable to load budget trends data. Please try again later.
                </div>
            `;
        });
}

/**
 * Create budget chart from data
 * @param {HTMLElement} container - Container element for the chart
 * @param {Object} data - Chart data
 */
function createBudgetChart(container, data) {
    // Clear container
    container.innerHTML = '';
    
    // Check if we have data
    if (!data || !data.labels || data.labels.length === 0) {
        container.innerHTML = '<p class="text-center text-muted my-5">No budget trend data available</p>';
        return;
    }
    
    // Create canvas for chart
    const canvas = document.createElement('canvas');
    canvas.id = 'budget-bar-chart';
    container.appendChild(canvas);
    
    // Create chart
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Actual Spending',
                    data: data.actual,
                    backgroundColor: data.colors || data.actual.map(value => {
                        // Calculate color based on whether spending exceeds budget
                        const index = data.actual.indexOf(value);
                        return value > data.budget[index] ? '#ef4444' : '#22c55e';
                    }),
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    barPercentage: 0.6
                },
                {
                    label: 'Budget',
                    data: data.budget,
                    type: 'line',
                    fill: false,
                    borderColor: '#ffffff',
                    borderDash: [5, 5],
                    pointBackgroundColor: '#ffffff',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatCurrency(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Refresh the donut chart with updated data
 */
function refreshDonutChart() {
    const chartContainer = document.getElementById('budget-donut-container');
    if (!chartContainer) return;
    
    // Get existing chart if available
    const existingChart = Chart.getChart('budget-donut-chart');
    if (existingChart) {
        existingChart.destroy();
    }
    
    // Re-initialize the chart
    initializeDonutChart();
}

// Export chart functions
export {
    initializeDonutChart,
    initializeBarChart,
    updateBudgetSummary,
    refreshDonutChart
};