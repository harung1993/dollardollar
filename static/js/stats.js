/**
 * Financial Analytics Dashboard JavaScript
 * This file contains all the JavaScript functionality for the dashboard
 */

// Initialize the dashboard when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Fix JSON data in data attributes if needed
    fixDataAttributes();
    
    // Get base currency from the data attribute 
    const dashboardContainer = document.getElementById('dashboard-container');
    const baseCurrencySymbol = dashboardContainer ? (dashboardContainer.dataset.currency || '$') : '$';
    
    // Initialize all components
    initializeDashboard({
        baseCurrencySymbol: baseCurrencySymbol
    });
});
function populateAccountFilter() {
    const accountFilter = document.getElementById('accountFilter');
    if (!accountFilter) return;

    // First, ensure we have the default "All Accounts" option
    accountFilter.innerHTML = '<option value="all">All Accounts</option>';

    // Try to get account data from dashboard container
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;

    // This part assumes you have a way to pass account data, 
    // such as a data attribute or a global variable
    try {
        // Example method 1: Using a data attribute (you'd need to add this in your HTML template)
        const accountsData = dashboardContainer.dataset.accounts;
        if (accountsData) {
            const accounts = JSON.parse(accountsData);
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = account.name;
                accountFilter.appendChild(option);
            });
            return;
        }

        // Example method 2: If accounts are available globally
        if (window.userAccounts && Array.isArray(window.userAccounts)) {
            window.userAccounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = account.name;
                accountFilter.appendChild(option);
            });
            return;
        }

        // Fallback: you might want to fetch accounts via AJAX
        fetchUserAccounts();
    } catch (error) {
        console.error('Error populating account filter:', error);
    }
}

/**
 * Fetch user accounts via AJAX if not already available
 */
function fetchUserAccounts() {
    const accountFilter = document.getElementById('accountFilter');
    if (!accountFilter) return;

    fetch('/api/user/accounts', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(accounts => {
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.id;
            option.textContent = account.name;
            accountFilter.appendChild(option);
        });
    })
    .catch(error => {
        console.error('Error fetching accounts:', error);
        // Optionally show a user-friendly error message
    });
}

/**
 * Main initialization function for the dashboard
 * @param {Object} config - Configuration object
 */
function initializeDashboard(config) {
    // Initialize all components
    initializeDateRanges();
    setupEventListeners();
    initializeOverviewCharts(config);
    initializeGaugeCharts();
    initializeComparisonTab(config);
    
     // Add account population
     populateAccountFilter();
    // Apply animations
    animateCards();
    
    // Fix for recent transactions table display
    setTimeout(updateTransactionDisplay, 100);
}

/**
 * Initialize date range inputs with default values
 */
// Safe JSON parsing function with error handling
function safeJsonParse(jsonString, defaultValue = []) {
    if (!jsonString || typeof jsonString !== 'string') {
        console.warn('Invalid JSON string provided:', jsonString);
        return defaultValue;
    }
    
    try {
        return JSON.parse(jsonString);
    } catch (error) {
        console.warn('Error parsing JSON:', error, 'Input was:', jsonString);
        return defaultValue;
    }
}

function fixDataAttributes() {
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;
    
    // List of attributes that should contain JSON arrays
    const jsonArrayAttributes = [
        'months', 
        'incomeData', 
        'expenseData', 
        'categoryNames', 
        'categoryTotals',
        'tagNames',
        'tagTotals',
        'tagColors'
    ];
    
    // Fix each attribute
    jsonArrayAttributes.forEach(attr => {
        const attrName = `data-${attr.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
        const value = dashboardContainer.getAttribute(attrName);
        
        if (value) {
            try {
                // Test if it's valid JSON
                JSON.parse(value);
                // If no error, it's valid JSON, so we leave it as is
            } catch (error) {
                // Not valid JSON, try to fix it
                let fixedValue;
                
                // If it starts with a bracket but has issues
                if (value.startsWith('[') && !value.endsWith(']')) {
                    // Try to extract the valid part or create empty array
                    fixedValue = '[]';
                    console.warn(`Fixed malformed JSON in ${attrName}`);
                } else if (!value.startsWith('[')) {
                    // Not a JSON array at all
                    fixedValue = '[]';
                    console.warn(`Attribute ${attrName} is not a JSON array. Resetting.`);
                }
                
                if (fixedValue) {
                    dashboardContainer.setAttribute(attrName, fixedValue);
                }
            }
        } else {
            // Attribute missing, set default
            dashboardContainer.setAttribute(attrName, '[]');
            console.warn(`Added missing attribute ${attrName}`);
        }
    });
}


function initializeDateRanges() {
    // Get date elements
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    
    // Set default dates (last 6 months)
    if (startDateInput && endDateInput) {
        const today = new Date();
        const endDate = today.toISOString().split('T')[0];
        
        const startDate = new Date();
        startDate.setMonth(today.getMonth() - 6);
        
        startDateInput.value = startDate.toISOString().split('T')[0];
        endDateInput.value = endDate;
    }
}

/**
 * Set up all event listeners for the dashboard
 */
function setupEventListeners() {
    // Filter button handler
    const applyFiltersBtn = document.getElementById('applyFilters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
        addButtonHoverEffect(applyFiltersBtn);
    }
    
    // Tab switching handler
    const analyticsTab = document.getElementById('analyticsTab');
    if (analyticsTab) {
        analyticsTab.addEventListener('shown.bs.tab', function(event) {
            const customizeViewPanel = document.getElementById('customizeViewPanel');
            if (customizeViewPanel) {
                // Hide customize view when comparison tab is active
                customizeViewPanel.style.display = event.target.id === 'comparison-tab' ? 'none' : 'block';
            }
        });
    }
}

/**
 * Apply hover effect to a button
 * @param {HTMLElement} button - The button element
 */
function addButtonHoverEffect(button) {
    button.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 6px 10px -1px rgba(99, 102, 241, 0.3)';
    });
    button.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 4px 6px -1px rgba(99, 102, 241, 0.2)';
    });
}

/**
 * Apply filters and reload the page with selected filters
 */
function applyFilters() {
    // Get filter values
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const groupId = document.getElementById('groupFilter').value;
    const transactionType = document.getElementById('transactionTypeFilter').value;
    const accountId = document.getElementById('accountFilter').value;
    
    // Build the URL with query parameters
    const baseUrl = window.location.pathname;
    const queryParams = new URLSearchParams({
        startDate: startDate,
        endDate: endDate,
        groupId: groupId,
        transactionType: transactionType,
        accountId: accountId
    });
    
    // Reload the page with the selected filters
    window.location.href = `${baseUrl}?${queryParams.toString()}`;
}

/**
 * Animate all cards with a staggered entrance effect
 */
function animateCards() {
    document.querySelectorAll('.card').forEach((card, index) => {
        card.style.opacity = 0;
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            card.style.opacity = 1;
            card.style.transform = 'translateY(0)';
        }, 50 * index); // Stagger the animations
    });
}

/**
 * Fix display of transaction rows
 */
function updateTransactionDisplay() {
    const transactionRows = document.querySelectorAll('#recentTransactionsBody tr');
    
    transactionRows.forEach((row) => {
        // Get the transaction type from the badge in the third column
        const typeBadge = row.querySelector('td:nth-child(3) .badge');
        if (!typeBadge) return;
        
        const typeText = typeBadge.textContent.trim().toLowerCase();
        const amountCell = row.querySelector('td:nth-child(4)');
        if (!amountCell) return;
        
        // Get the current amount text and clean it up
        let amountText = amountCell.textContent.trim();
        // Remove any existing + or - signs
        amountText = amountText.replace(/^[+-]/, '');
        
        // Format based on transaction type
        if (typeText.includes('income')) {
            amountCell.textContent = '+' + amountText;
            amountCell.style.color = '#10b981'; // Green
            amountCell.style.fontWeight = 'bold';
        } 
        else if (typeText.includes('expense')) {
            amountCell.textContent = '-' + amountText;
            amountCell.style.color = '#ef4444'; // Red
            amountCell.style.fontWeight = 'bold';
        }
        else if (typeText.includes('transfer')) {
            // For transfers, don't add a sign but still style it
            amountCell.textContent = amountText;
            amountCell.style.color = '#a855f7'; // Purple
            amountCell.style.fontWeight = 'bold';
        }
    });
}

/**
 * Initialize gauge charts for financial health indicators
 */
function initializeGaugeCharts() {
    // Get gauge data from data attributes
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;
    
    const data = dashboardContainer.dataset;
    
    // Initialize the gauge charts for financial health
    const gauges = [
        { id: 'savingsRateGauge', value: parseFloat(data.savingsRate) || 0, maxValue: 100, type: 'percentage' },
        { id: 'expenseIncomeRatioGauge', value: parseFloat(data.expenseIncomeRatio) || 0, maxValue: 100, type: 'percentage' },
        { id: 'liquidityGauge', value: parseFloat(data.liquidityRatio) || 0, maxValue: 12, type: 'months' },
        { id: 'accountGrowthGauge', value: parseFloat(data.accountGrowth) || 0, maxValue: 30, type: 'percentage' }
    ];
    
    gauges.forEach(gauge => {
        const element = document.getElementById(gauge.id);
        if (element) {
            updateGaugeValue(gauge.id, gauge.value, gauge.maxValue);
        }
    });
}

/**
 * Update a gauge chart with the given value
 * @param {string} gaugeId - The ID of the gauge element
 * @param {number} value - The value to display
 * @param {number} maxValue - The maximum value for the gauge
 */
function updateGaugeValue(gaugeId, value, maxValue) {
    const displayElement = document.getElementById(gaugeId);
    if (!displayElement) return;
    
    // Check if value is missing or NaN
    if (value === null || value === undefined || isNaN(value)) {
        // Show N/A for missing values
        displayElement.innerHTML = '<div class="position-relative w-100 h-100 d-flex justify-content-center align-items-center" style="background-color: rgba(148, 163, 184, 0.2); border-radius: 50%;"><span style="color: #94a3b8; font-size: 1rem;">N/A</span></div>';
        return;
    }
    
    // Calculate percentage for gauge fill
    const percentage = Math.min((value / maxValue) * 100, 100);
    
    // Determine color based on value
    let color;
    if (gaugeId === 'expenseIncomeRatioGauge') {
        // For this gauge, lower is better
        color = percentage < 60 ? '#10b981' : (percentage < 80 ? '#f59e0b' : '#ef4444');
    } else {
        // For other gauges, higher is better
        color = percentage > 60 ? '#10b981' : (percentage > 30 ? '#f59e0b' : '#ef4444');
    }
    
    // Apply stylings to create gauge effect
    displayElement.style.background = `conic-gradient(${color} ${percentage}%, transparent ${percentage}%)`;
    displayElement.style.borderRadius = '50%';
    displayElement.style.width = '120px';
    displayElement.style.height = '120px';
    displayElement.style.display = 'flex';
    displayElement.style.justifyContent = 'center';
    displayElement.style.alignItems = 'center';
    displayElement.style.position = 'relative';
    displayElement.style.margin = '0 auto';
    
    // Create inner circle for gauge
    displayElement.innerHTML = '';
    const innerCircle = document.createElement('div');
    innerCircle.style.width = '90px';
    innerCircle.style.height = '90px';
    innerCircle.style.borderRadius = '50%';
    innerCircle.style.backgroundColor = 'rgba(15, 23, 42, 0.8)';
    innerCircle.style.display = 'flex';
    innerCircle.style.justifyContent = 'center';
    innerCircle.style.alignItems = 'center';
    innerCircle.style.fontSize = '1.5rem';
    innerCircle.style.fontWeight = 'bold';
    innerCircle.style.color = color;
    
    // Format the display value
    const displayValue = document.getElementById(`${gaugeId.replace('Gauge', 'Display')}`);
    if (displayValue) {
        displayValue.textContent = displayValue.textContent || 
            (gaugeId.includes('Ratio') ? `${value.toFixed(1)}` : (gaugeId.includes('Percentage') ? `${value.toFixed(1)}%` : value.toFixed(1)));
    }
    
    innerCircle.textContent = displayValue ? displayValue.textContent : (
        gaugeId.includes('Rate') || gaugeId.includes('Growth') ? `${value.toFixed(1)}%` : value.toFixed(1)
    );
    
    displayElement.appendChild(innerCircle);
}

/**
 * Initialize all overview tab charts
 * @param {Object} config - Configuration object
 */
function initializeOverviewCharts(config) {
    // Set common Chart.js options for dark theme
    Chart.defaults.color = '#fff';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
    
    // Add chart animations
    const chartAnimations = {
        duration: 2000,
        easing: 'easeOutQuart'
    };
    
    // Get chart data from container data attributes
    const dashboardContainer = document.getElementById('dashboard-container');
    if (!dashboardContainer) return;
    
    // Use empty arrays as default data
    const chartData = {
        months: [],
        incomeData: [],
        expenseData: [],
        categoryNames: [],
        categoryTotals: [],
        tagNames: [],
        tagTotals: [],
        tagColors: [],
        totalIncome: parseFloat(dashboardContainer.dataset.totalIncome || 0),
        totalExpenses: parseFloat(dashboardContainer.dataset.totalExpenses || 0),
        totalTransfers: parseFloat(dashboardContainer.dataset.totalTransfers || 0)
    };
    
    // Use safe parsing for each JSON attribute
    chartData.months = safeJsonParse(dashboardContainer.dataset.months, []);
    chartData.incomeData = safeJsonParse(dashboardContainer.dataset.incomeData, []);
    chartData.expenseData = safeJsonParse(dashboardContainer.dataset.expenseData, []);
    chartData.categoryNames = safeJsonParse(dashboardContainer.dataset.categoryNames, []);
    chartData.categoryTotals = safeJsonParse(dashboardContainer.dataset.categoryTotals, []);
    chartData.tagNames = safeJsonParse(dashboardContainer.dataset.tagNames, []);
    chartData.tagTotals = safeJsonParse(dashboardContainer.dataset.tagTotals, []);
    chartData.tagColors = safeJsonParse(dashboardContainer.dataset.tagColors, []);
    
    // Log parsed data for debugging
    console.log('Successfully parsed chart data:', chartData);
    
    // If missing months but have income/expense data, generate month labels
    if (chartData.months.length === 0 && (chartData.incomeData.length > 0 || chartData.expenseData.length > 0)) {
        const dataLength = Math.max(chartData.incomeData.length, chartData.expenseData.length);
        chartData.months = generateMonthLabels(dataLength);
        console.log('Generated month labels:', chartData.months);
    }
    
    // Create the charts with fallbacks
    createIncomeExpenseChart(chartData, chartAnimations, config);
    createTransactionTypeChart(chartData, chartAnimations, config);
    createCategoryChart(chartData, chartAnimations, config);
    createTagChart(chartData, chartAnimations, config);
}

/**
 * Generate month labels for the given number of months
 * @param {number} count - Number of months to generate
 * @returns {string[]} Array of month labels
/**
 * Create the Income vs Expense Chart
 * @param {Object} chartData - Data for the chart
 * @param {Object} chartAnimations - Animation configuration
 * @param {Object} config - General configuration
 */
function createIncomeExpenseChart(chartData, chartAnimations, config) {
    const ctx = document.getElementById('incomeExpenseChart');
    if (!ctx) return;
    
    // Check if we have valid data
    if (!chartData.months || !Array.isArray(chartData.months) || !chartData.months.length) {
        displayNoDataMessage(ctx, 'No income/expense data available');
        return;
    }
    
    // Ensure both income and expense data exist
    if (!chartData.incomeData || !Array.isArray(chartData.incomeData)) {
        chartData.incomeData = [];
    }
    
    if (!chartData.expenseData || !Array.isArray(chartData.expenseData)) {
        chartData.expenseData = [];
    }
    
    // Use server data
    const months = chartData.months;
    const expenseData = chartData.expenseData;
    const incomeData = chartData.incomeData;
    
    // Ensure both arrays are the same length as months
    const dataLength = months.length;
    const normalizedIncomeData = Array(dataLength).fill(0);
    const normalizedExpenseData = Array(dataLength).fill(0);
    
    // Fill with actual data
    for (let i = 0; i < dataLength; i++) {
        if (i < incomeData.length) normalizedIncomeData[i] = incomeData[i] || 0;
        if (i < expenseData.length) normalizedExpenseData[i] = expenseData[i] || 0;
    }
    
    // Calculate net data
    const netData = normalizedIncomeData.map((income, index) => 
        income - normalizedExpenseData[index]);
    
    // Destroy existing chart if any
    if (window.incomeExpenseChart instanceof Chart) {
        window.incomeExpenseChart.destroy();
    }
    
    // Create chart with actual data
    window.incomeExpenseChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Income',
                    data: normalizedIncomeData,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 2
                },
                {
                    label: 'Expenses',
                    data: normalizedExpenseData,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 3
                },
                {
                    label: 'Net Cash Flow',
                    data: netData,
                    type: 'line',
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#1d4ed8',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle'
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
                                label += config.baseCurrencySymbol + context.parsed.y.toFixed(2);
                            }
                            return label;
                        }
                    },
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    titleColor: '#38bdf8',
                    bodyColor: '#f8fafc',
                    borderColor: '#1e40af',
                    borderWidth: 1
                }
            },
            animation: chartAnimations
        }
    });
}

/**
 * Enhanced display of "No Data" message
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {string} message - The message to display
 */
function displayNoDataMessage(canvas, message) {
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const width = canvas.width || 300;
    const height = canvas.height || 150;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw background
    ctx.fillStyle = 'rgba(30, 41, 59, 0.5)';
    ctx.fillRect(0, 0, width, height);
    
    // Draw icon
    const centerX = width / 2;
    const centerY = height / 2 - 15;
    const radius = 20;
    
    // Chart icon
    ctx.beginPath();
    ctx.moveTo(centerX - radius, centerY + radius);
    ctx.lineTo(centerX - radius, centerY - radius/2);
    ctx.lineTo(centerX, centerY + radius/2);
    ctx.lineTo(centerX + radius/2, centerY - radius/3);
    ctx.lineTo(centerX + radius, centerY - radius);
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.8)';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Set up text style
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '16px Arial';
    ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
    
    // Draw message
    ctx.fillText(message || 'No data available', centerX, centerY + 30);
}
/**
 * Create the Transaction Type Distribution Chart
 * @param {Object} chartData - Data for the chart
 * @param {Object} chartAnimations - Animation configuration
 * @param {Object} config - General configuration
 */
function createTransactionTypeChart(chartData, chartAnimations, config) {
    const ctx = document.getElementById('transactionTypeChart');
    if (!ctx) return;
    
    // Transaction type data
    const transactionData = {
        income: chartData.totalIncome,
        expenses: chartData.totalExpenses,
        transfers: chartData.totalTransfers
    };
    
    // Update transaction summary statistics
    if (document.getElementById('incomeStat')) {
        document.getElementById('incomeStat').textContent = config.baseCurrencySymbol + transactionData.income.toFixed(2);
    }
    if (document.getElementById('expenseStat')) {
        document.getElementById('expenseStat').textContent = config.baseCurrencySymbol + transactionData.expenses.toFixed(2);
    }
    if (document.getElementById('transferStat')) {
        document.getElementById('transferStat').textContent = config.baseCurrencySymbol + transactionData.transfers.toFixed(2);
    }
    if (document.getElementById('netStat')) {
        document.getElementById('netStat').textContent = config.baseCurrencySymbol + (transactionData.income - transactionData.expenses).toFixed(2);
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Income', 'Expenses', 'Transfers'],
            datasets: [{
                data: [
                    transactionData.income,
                    transactionData.expenses,
                    transactionData.transfers
                ],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(168, 85, 247, 0.7)'
                ],
                borderColor: [
                    '#10b981',
                    '#ef4444',
                    '#a855f7'
                ],
                borderWidth: 1,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${config.baseCurrencySymbol}${value.toFixed(2)} (${percentage}%)`;
                        }
                    },
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    titleColor: '#38bdf8',
                    bodyColor: '#f8fafc',
                    borderColor: '#1e40af',
                    borderWidth: 1
                }
            },
            animation: chartAnimations
        }
    });
}

/**
 * Create the Spending by Category Chart
 * @param {Object} chartData - Data for the chart
 * @param {Object} chartAnimations - Animation configuration
 * @param {Object} config - General configuration
 */
function createCategoryChart(chartData, chartAnimations, config) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;
    
    const categoryNames = chartData.categoryNames;
    const categoryTotals = chartData.categoryTotals;
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: categoryNames,
            datasets: [{
                data: categoryTotals,
                backgroundColor: [
                    '#ec4899', '#d946ef', '#a855f7', '#8b5cf6', 
                    '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4',
                    '#14b8a6', '#10b981', '#22c55e', '#84cc16'
                ],
                borderColor: 'rgba(30, 41, 59, 0.7)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: {
                            size: 11
                        },
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${context.label}: ${config.baseCurrencySymbol}${value.toFixed(2)} (${percentage}%)`;
                        }
                    },
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    titleColor: '#ec4899',
                    bodyColor: '#f8fafc',
                    borderColor: '#1e40af',
                    borderWidth: 1,
                    padding: 10
                }
            },
            animation: chartAnimations
        }
    });
}

/**
 * Create the Tag Analysis Chart
 * @param {Object} chartData - Data for the chart
 * @param {Object} chartAnimations - Animation configuration
 * @param {Object} config - General configuration
 */
function createTagChart(chartData, chartAnimations, config) {
    const ctx = document.getElementById('tagChart');
    if (!ctx) return;
    
    const tagNames = chartData.tagNames;
    const tagTotals = chartData.tagTotals;
    const tagColors = chartData.tagColors;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: tagNames,
            datasets: [{
                label: 'Spending by Tag',
                data: tagTotals,
                backgroundColor: tagColors,
                borderColor: 'rgba(30, 41, 59, 0.7)',
                borderWidth: 2,
                borderRadius: 6,
                maxBarThickness: 35
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${config.baseCurrencySymbol}${context.raw.toFixed(2)}`;
                        }
                    },
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    titleColor: '#f43f5e',
                    bodyColor: '#f8fafc',
                    borderColor: '#1e40af',
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: chartAnimations
        }
    });
}

/**
 * Initialize the comparison tab functionality
 * @param {Object} config - Configuration object
 */
function initializeComparisonTab(config) {
    // Button event handlers for comparison tab
    const runComparisonBtn = document.getElementById('runComparisonBtn');
    const setDefaultPeriodsBtn = document.getElementById('setDefaultPeriodsBtn');
    
    if (runComparisonBtn) {
        runComparisonBtn.addEventListener('click', function() {
            runComparison(config);
        });
        addButtonHoverEffect(runComparisonBtn);
    }
    
    if (setDefaultPeriodsBtn) {
        setDefaultPeriodsBtn.addEventListener('click', function() {
            setDefaultComparisonPeriods(config);
        });
        addButtonHoverEffect(setDefaultPeriodsBtn);
    }
    
    // Initialize with default dates
    initializeComparisonDates();
}

/**
 * Initialize comparison date inputs with default values
 */
function initializeComparisonDates() {
    // Get date elements
    const primaryStartDate = document.getElementById('primaryStartDate');
    const primaryEndDate = document.getElementById('primaryEndDate');
    const comparisonStartDate = document.getElementById('comparisonStartDate');
    const comparisonEndDate = document.getElementById('comparisonEndDate');
    
    if (!primaryStartDate || !primaryEndDate || !comparisonStartDate || !comparisonEndDate) {
        return;
    }
    
    // Set default primary period (current month)
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    primaryStartDate.value = formatDate(firstDayOfMonth);
    primaryEndDate.value = formatDate(lastDayOfMonth);
    
    // Set default comparison period (previous month)
    const firstDayOfLastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const lastDayOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
    
    comparisonStartDate.value = formatDate(firstDayOfLastMonth);
    comparisonEndDate.value = formatDate(lastDayOfLastMonth);
}

/**
 * Format a date as YYYY-MM-DD
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Set default comparison periods and run comparison
 * @param {Object} config - Configuration object
 */
function setDefaultComparisonPeriods(config) {
    // Set default periods (current month vs previous month)
    initializeComparisonDates();
    
    // Run the comparison automatically
    runComparison(config);
}

/**
 * Run comparison between two time periods
 * @param {Object} config - Configuration object
 */
function runComparison(config) {
    // Get form values
    const primaryStart = document.getElementById('primaryStartDate').value;
    const primaryEnd = document.getElementById('primaryEndDate').value;
    const comparisonStart = document.getElementById('comparisonStartDate').value;
    const comparisonEnd = document.getElementById('comparisonEndDate').value;
    const metric = document.getElementById('comparisonMetric').value;
    
    // Validate inputs
    if (!primaryStart || !primaryEnd || !comparisonStart || !comparisonEnd) {
        alert('Please select all date ranges for comparison');
        return;
    }
    
    // Show loading state
    const runBtn = document.getElementById('runComparisonBtn');
    const originalBtnText = runBtn.innerHTML;
    runBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Comparing...';
    runBtn.disabled = true;
    
    // Fetch comparison data from server
    fetch(`${window.location.pathname}?compare=true&primaryStart=${primaryStart}&primaryEnd=${primaryEnd}&comparisonStart=${comparisonStart}&comparisonEnd=${comparisonEnd}&metric=${metric}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Hide no data message and show results
        document.getElementById('noComparisonData').style.display = 'none';
        document.getElementById('comparisonResults').style.display = 'block';
        
        // Update chart title based on metric
        updateChartTitle(metric);
        
        // Update summary data
        updateComparisonSummary(data, config);
        
        // Generate comparison chart based on metric
        generateComparisonChart(data, metric, config);
        
        // Show detailed comparison table for categories and tags
        showDetailedComparisonTable(data, metric, config);
    })
    .catch(error => {
        console.error('Error fetching comparison data:', error);
        alert('Error loading comparison data. Please try again.');
    })
    .finally(() => {
        // Reset button state
        runBtn.innerHTML = originalBtnText;
        runBtn.disabled = false;
    });
}
/**
 * Generate month labels for the given number of months
 * @param {number} count - Number of months to generate
 * @returns {string[]} Array of month labels
 */
function generateMonthLabels(count) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentDate = new Date();
    const currentMonth = currentDate.getMonth();
    const currentYear = currentDate.getFullYear();
    
    const labels = [];
    for (let i = count - 1; i >= 0; i--) {
        // Calculate the month index going backwards from current month
        const monthIndex = (currentMonth - i + 12) % 12;
        
        // Calculate the year offset correctly
        const yearOffset = Math.floor((i - currentMonth) / 12);
        const year = currentYear - yearOffset;
        
        labels.push(`${months[monthIndex]} ${year}`);
    }
    
    return labels;
}
/**
 * Update the comparison chart title based on metric
 * @param {string} metric - The selected comparison metric
 */
function updateChartTitle(metric) {
    const chartTitleElement = document.getElementById('comparisonChartTitle');
    
    if (chartTitleElement) {
        switch (metric) {
            case 'spending':
                chartTitleElement.textContent = 'Daily Spending Comparison';
                break;
            case 'categories':
                chartTitleElement.textContent = 'Category Spending Comparison';
                break;
            case 'tags':
                chartTitleElement.textContent = 'Tag Spending Comparison';
                break;
            case 'payment':
                chartTitleElement.textContent = 'Payment Method Comparison';
                break;
            default:
                chartTitleElement.textContent = 'Spending Comparison';
        }
    }
}

/**
 * Update the comparison summary with the data received from the server
 * @param {Object} data - Comparison data object
 * @param {Object} config - Configuration object
 */
function updateComparisonSummary(data, config) {
    const baseCurrencySymbol = config.baseCurrencySymbol;
    
    // Update primary period summary
    document.getElementById('primaryTotalSpending').textContent = baseCurrencySymbol + data.primary.totalSpending.toFixed(2);
    document.getElementById('primaryTransactionCount').textContent = data.primary.transactionCount;
    document.getElementById('primaryTopCategory').textContent = data.primary.topCategory;
    
    // Update comparison period summary
    document.getElementById('comparisonTotalSpending').textContent = baseCurrencySymbol + data.comparison.totalSpending.toFixed(2);
    document.getElementById('comparisonTransactionCount').textContent = data.comparison.transactionCount;
    document.getElementById('comparisonTopCategory').textContent = data.comparison.topCategory;
    
    // Calculate and update differences
    const spendingDiff = data.primary.totalSpending - data.comparison.totalSpending;
    const spendingDiffPercent = data.comparison.totalSpending !== 0 
        ? (spendingDiff / data.comparison.totalSpending) * 100 
        : 0;
    
    const transactionDiff = data.primary.transactionCount - data.comparison.transactionCount;
    const transactionDiffPercent = data.comparison.transactionCount !== 0 
        ? (transactionDiff / data.comparison.transactionCount) * 100 
        : 0;
    
    // Calculate daily averages
    const primaryDates = getDaysInRange(
        document.getElementById('primaryStartDate').value,
        document.getElementById('primaryEndDate').value
    );
    const comparisonDates = getDaysInRange(
        document.getElementById('comparisonStartDate').value,
        document.getElementById('comparisonEndDate').value
    );
    
    const primaryDailyAvg = data.primary.totalSpending / primaryDates;
    const comparisonDailyAvg = data.comparison.totalSpending / comparisonDates;
    const dailyAvgDiff = primaryDailyAvg - comparisonDailyAvg;
    const dailyAvgDiffPercent = comparisonDailyAvg !== 0 
        ? (dailyAvgDiff / comparisonDailyAvg) * 100 
        : 0;
    
    // Update difference card
    const spendingDiffElem = document.getElementById('spendingDifference');
    const spendingChangeElem = document.getElementById('spendingChangePercent');
    updateDifferenceElement(spendingDiffElem, spendingChangeElem, spendingDiff, spendingDiffPercent, true, config);
    
    const transactionDiffElem = document.getElementById('transactionDifference');
    const transactionChangeElem = document.getElementById('transactionChangePercent');
    updateDifferenceElement(transactionDiffElem, transactionChangeElem, transactionDiff, transactionDiffPercent, false, config);
    
    const avgDailyDiffElem = document.getElementById('avgDailyDifference');
    const avgDailyChangeElem = document.getElementById('avgDailyChangePercent');
    updateDifferenceElement(avgDailyDiffElem, avgDailyChangeElem, dailyAvgDiff, dailyAvgDiffPercent, true, config);
}

/**
 * Update a difference element with the given values
 * @param {HTMLElement} diffElement - The difference element
 * @param {HTMLElement} percentElement - The percent change element
 * @param {number} difference - The calculated difference
 * @param {number} percentChange - The calculated percent change
 * @param {boolean} isCurrency - Whether to format as currency
 * @param {Object} config - Configuration object
 */
function updateDifferenceElement(diffElement, percentElement, difference, percentChange, isCurrency, config) {
    if (!diffElement || !percentElement) return;
    
    // For expense metrics, negative values (decrease) are good
    const isNegative = difference < 0;
    const formattedDiff = isCurrency 
        ? config.baseCurrencySymbol + Math.abs(difference).toFixed(2) 
        : Math.abs(difference);
    
    diffElement.textContent = formattedDiff;
    percentElement.textContent = (isNegative ? 'Decreased by ' : 'Increased by ') + Math.abs(percentChange).toFixed(1) + '%';
    
    // For expenses, red for increase, green for decrease (for income it would be the opposite)
    const metric = document.getElementById('comparisonMetric').value;
    const isDarkMode = document.documentElement.classList.contains('dark');
    
    if (metric === 'income') {
        diffElement.style.color = isNegative ? '#ef4444' : '#10b981';
        percentElement.style.color = isNegative ? '#ef4444' : '#10b981';
    } else {
        diffElement.style.color = isNegative ? '#10b981' : '#ef4444';
        percentElement.style.color = isNegative ? '#10b981' : '#ef4444';
    }
}

/**
 * Calculate the number of days in a date range
 * @param {string} startDateStr - Start date string in YYYY-MM-DD format
 * @param {string} endDateStr - End date string in YYYY-MM-DD format
 * @returns {number} Number of days in the range
 */
function getDaysInRange(startDateStr, endDateStr) {
    const startDate = new Date(startDateStr);
    const endDate = new Date(endDateStr);
    const diffTime = Math.abs(endDate - startDate);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 to include both start and end days
}

/**
 * Generate a comparison chart based on the selected metric
 * @param {Object} data - Comparison data object
 * @param {string} metric - Selected comparison metric
 * @param {Object} config - Configuration object
 */
function generateComparisonChart(data, metric, config) {
    // Get the canvas context
    const ctx = document.getElementById('comparisonChart');
    
    // Safely destroy existing chart
    if (window.comparisonChart && typeof window.comparisonChart.destroy === 'function') {
        window.comparisonChart.destroy();
    }
    
    if (!ctx) return;
    
    // Prepare chart data based on metric
    let chartData = {
        labels: [],
        datasets: []
    };
    
    let chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    usePointStyle: true,
                    pointStyle: 'circle',
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) label += ': ';
                        if (context.parsed.y !== null) {
                            label += config.baseCurrencySymbol + context.parsed.y.toFixed(2);
                        }
                        return label;
                    }
                },
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                titleColor: '#38bdf8',
                bodyColor: '#f8fafc',
                borderColor: '#1e40af',
                borderWidth: 1
            }
        },
        animation: {
            duration: 2000,
            easing: 'easeOutQuart'
        }
    };
    
    switch(metric) {
        case 'spending':
            // Daily spending comparison
            chartData.labels = data.dateLabels || Array.from({length: 10}, (_, i) => `Day ${i+1}`);
            
            chartData.datasets = [
                {
                    label: 'Primary Period',
                    data: data.primary.dailyAmounts || [],
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.2)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#38bdf8',
                    pointBorderColor: '#0284c7',
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Comparison Period',
                    data: data.comparison.dailyAmounts || [],
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.2)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#a855f7',
                    pointBorderColor: '#7e22ce',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ];
            
            chartOptions.scales = {
                x: {
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    }
                }
            };
            break;
            
        case 'categories':
            // Category comparison
            chartData.labels = data.categoryLabels || [];
            
            chartData.datasets = [
                {
                    label: 'Primary Period',
                    data: data.primary.categoryAmounts || [],
                    backgroundColor: 'rgba(56, 189, 248, 0.7)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Comparison Period',
                    data: data.comparison.categoryAmounts || [],
                    backgroundColor: 'rgba(168, 85, 247, 0.7)',
                    borderColor: '#a855f7',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ];
            
            chartOptions.indexAxis = 'y';
            chartOptions.scales = {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    }
                },
                y: {
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            };
            break;
            
        case 'tags':
            // Tag comparison
            chartData.labels = data.tagLabels || [];
            
            chartData.datasets = [
                {
                    label: 'Primary Period',
                    data: data.primary.tagAmounts || [],
                    backgroundColor: 'rgba(56, 189, 248, 0.7)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Comparison Period',
                    data: data.comparison.tagAmounts || [],
                    backgroundColor: 'rgba(168, 85, 247, 0.7)',
                    borderColor: '#a855f7',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ];
            
            chartOptions.indexAxis = 'y';
            chartOptions.scales = {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    }
                },
                y: {
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            };
            break;
            
        case 'payment':
            // Payment method comparison
            chartData.labels = data.paymentLabels || [];
            
            chartData.datasets = [
                {
                    label: 'Primary Period',
                    data: data.primary.paymentAmounts || [],
                    backgroundColor: 'rgba(56, 189, 248, 0.7)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Comparison Period',
                    data: data.comparison.paymentAmounts || [],
                    backgroundColor: 'rgba(168, 85, 247, 0.7)',
                    borderColor: '#a855f7',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ];
            
            chartOptions.scales = {
                x: {
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: {
                        callback: function(value) {
                            return config.baseCurrencySymbol + value;
                        }
                    }
                }
            };
            break;
            
        default:
            chartData.labels = ['No data available'];
            chartData.datasets = [{
                label: 'No data',
                data: [0],
                backgroundColor: 'rgba(148, 163, 184, 0.2)'
            }];
    }
    
    // Create or update chart
    window.comparisonChart = new Chart(ctx, {
        type: metric === 'spending' ? 'line' : 'bar',
        data: chartData,
        options: chartOptions
    });
}

/**
 * Show the detailed comparison table for categories, tags, and payment methods
 * @param {Object} data - Comparison data object
 * @param {string} metric - Selected comparison metric
 * @param {Object} config - Configuration object
 */
function showDetailedComparisonTable(data, metric, config) {
    // Get table container and set visibility
    const tableContainer = document.getElementById('categoryTagComparison');
    const tableTitle = document.getElementById('comparisonTableTitle');
    const itemTypeHeader = document.getElementById('itemTypeHeader');
    const tableBody = document.getElementById('detailedComparisonBody');
    
    if (!tableContainer || !tableTitle || !tableBody) return;
    
    // Only show detailed table for categories, tags, and payment methods
    if (['categories', 'tags', 'payment'].includes(metric)) {
        tableContainer.style.display = 'block';
        
        // Update table title
        if (metric === 'categories') {
            tableTitle.textContent = 'Category Breakdown';
            itemTypeHeader.textContent = 'Category';
        } else if (metric === 'tags') {
            tableTitle.textContent = 'Tag Breakdown';
            itemTypeHeader.textContent = 'Tag';
        } else {
            tableTitle.textContent = 'Payment Method Breakdown';
            itemTypeHeader.textContent = 'Payment Method';
        }
        
        // Clear existing rows
        tableBody.innerHTML = '';
        
        // Get labels and amounts
        const labels = data[`${metric}Labels`] || [];
        const primaryAmounts = data.primary[`${metric}Amounts`] || [];
        const comparisonAmounts = data.comparison[`${metric}Amounts`] || [];
        
        // Generate detailed rows
        labels.forEach((label, index) => {
            const primaryAmount = primaryAmounts[index] || 0;
            const comparisonAmount = comparisonAmounts[index] || 0;
            const difference = primaryAmount - comparisonAmount;
            const percentChange = comparisonAmount !== 0 
                ? (difference / comparisonAmount) * 100 
                : 0;
            
            // Create row
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid rgba(148, 163, 184, 0.1)';
            
            // For expenses, negative difference (decrease) is good
            const isNegative = difference < 0;
            const colorClass = metric === 'income' 
                ? (isNegative ? 'text-danger' : 'text-success')
                : (isNegative ? 'text-success' : 'text-danger');
                
            const differenceColor = metric === 'income'
                ? (isNegative ? '#ef4444' : '#10b981')
                : (isNegative ? '#10b981' : '#ef4444');
            
            row.innerHTML = `
                <td>${label}</td>
                <td style="text-align: right;">${config.baseCurrencySymbol}${primaryAmount.toFixed(2)}</td>
                <td style="text-align: right;">${config.baseCurrencySymbol}${comparisonAmount.toFixed(2)}</td>
                <td style="text-align: right; color: ${differenceColor};">${isNegative ? '-' : '+'}${config.baseCurrencySymbol}${Math.abs(difference).toFixed(2)}</td>
                <td style="text-align: right; color: ${differenceColor};">${isNegative ? '-' : '+'}${Math.abs(percentChange).toFixed(1)}%</td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Add a total row
        const totalPrimary = primaryAmounts.reduce((sum, amount) => sum + amount, 0);
        const totalComparison = comparisonAmounts.reduce((sum, amount) => sum + amount, 0);
        const totalDifference = totalPrimary - totalComparison;
        const totalPercentChange = totalComparison !== 0 
            ? (totalDifference / totalComparison) * 100 
            : 0;
            
        const isNegativeTotal = totalDifference < 0;
        const totalDifferenceColor = metric === 'income'
            ? (isNegativeTotal ? '#ef4444' : '#10b981')
            : (isNegativeTotal ? '#10b981' : '#ef4444');
        
        const totalRow = document.createElement('tr');
        totalRow.style.borderTop = '2px solid rgba(148, 163, 184, 0.3)';
        totalRow.style.fontWeight = 'bold';
        
        totalRow.innerHTML = `
            <td>TOTAL</td>
            <td style="text-align: right;">${config.baseCurrencySymbol}${totalPrimary.toFixed(2)}</td>
            <td style="text-align: right;">${config.baseCurrencySymbol}${totalComparison.toFixed(2)}</td>
            <td style="text-align: right; color: ${totalDifferenceColor};">${isNegativeTotal ? '-' : '+'}${config.baseCurrencySymbol}${Math.abs(totalDifference).toFixed(2)}</td>
            <td style="text-align: right; color: ${totalDifferenceColor};">${isNegativeTotal ? '-' : '+'}${Math.abs(totalPercentChange).toFixed(1)}%</td>
        `;
        
        tableBody.appendChild(totalRow);
        
    } else {
        tableContainer.style.display = 'none';
    }
}
