// stats.js - Fixed Statistics Dashboard for Dollar Dollar Bill Y'all
document.addEventListener('DOMContentLoaded', function() {
    // Get currency symbol from the page or use default
    const baseCurrencySymbol = document.querySelector('meta[name="currency-symbol"]')?.content || 
                             document.getElementById('totalIncome')?.textContent?.match(/^[^\d]+/)[0] || '$';
    
    // Make currency symbol globally available
    window.baseCurrencySymbol = baseCurrencySymbol;
    
    // Initialize components
    initializeDateFilters();
    setupFilterHandlers();
    initializeCharts();
    animateCards();
    initializeGaugeCharts();
    setupComparisonTab();
    
    // Fetch accounts for populating account filter
    fetchUserAccounts();
});

// ===== INITIALIZATION FUNCTIONS =====

/**
 * Initialize date filter inputs with sensible defaults
 */
function initializeDateFilters() {
    const today = new Date();
    
    // Default to last 6 months
    const endDate = today.toISOString().split('T')[0];
    const startDate = new Date();
    startDate.setMonth(today.getMonth() - 6);
    const startDateStr = startDate.toISOString().split('T')[0];
    
    // Set default values if not already set by URL params
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    
    if (startDateInput && !startDateInput.value) {
        startDateInput.value = startDateStr;
    }
    
    if (endDateInput && !endDateInput.value) {
        endDateInput.value = endDate;
    }
}

/**
 * Set up event handlers for filter controls
 */
function setupFilterHandlers() {
    const filterBtn = document.getElementById('applyFilters');
    if (filterBtn) {
        filterBtn.addEventListener('click', applyFilters);
        
        // Add hover effects
        filterBtn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 6px 10px -1px rgba(99, 102, 241, 0.3)';
        });
        
        filterBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 6px -1px rgba(99, 102, 241, 0.2)';
        });
    }
    
    // Handle tab changes to hide/show filter panel
    const analyticsTab = document.getElementById('analyticsTab');
    if (analyticsTab) {
        analyticsTab.addEventListener('shown.bs.tab', function(event) {
            const customizeViewPanel = document.getElementById('customizeViewPanel');
            if (customizeViewPanel) {
                // Hide customize view when comparison tab is active
                customizeViewPanel.style.display = (event.target.id === 'comparison-tab') ? 'none' : 'block';
            }
        });
    }
}

/**
 * Initialize all dashboard charts
 */
function initializeCharts() {
    // Common Chart.js options for dark theme
    setupChartDefaults();
    
    // Create all the charts
    createIncomeExpenseChart();
    createTransactionTypeChart();
    createCategoryChart();
    createTagChart();
}

/**
 * Set up Chart.js defaults for consistent styling
 */
function setupChartDefaults() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = '#fff';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
        
        // Define common tooltip styling
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.8)';
        Chart.defaults.plugins.tooltip.titleColor = '#38bdf8';
        Chart.defaults.plugins.tooltip.bodyColor = '#f8fafc';
        Chart.defaults.plugins.tooltip.borderColor = '#1e40af';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        
        // Define common animation settings
        Chart.defaults.animation.duration = 2000;
        Chart.defaults.animation.easing = 'easeOutQuart';
    }
}

/**
 * Add fade-in animation to dashboard cards
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

// ===== FILTER FUNCTIONS =====

/**
 * Fetch user accounts and populate the account dropdown
 */
function fetchUserAccounts() {
    // Ideally, this would be an API call. For now, we'll just check for data
    // attributes on the select element
    const accountSelect = document.getElementById('accountFilter');
    if (!accountSelect) return;
    
    const accountsData = accountSelect.getAttribute('data-accounts');
    if (accountsData) {
        try {
            const accounts = JSON.parse(accountsData);
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = account.name;
                accountSelect.appendChild(option);
            });
        } catch (e) {
            console.error('Error parsing account data:', e);
        }
    }
}

/**
 * Apply selected filters and reload the page
 */
function applyFilters() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const groupId = document.getElementById('groupFilter').value;
    const transactionType = document.getElementById('transactionTypeFilter').value;
    const accountId = document.getElementById('accountFilter').value;
    
    // Construct query string
    const params = new URLSearchParams();
    if (startDate) params.set('startDate', startDate);
    if (endDate) params.set('endDate', endDate);
    if (groupId !== 'all') params.set('groupId', groupId);
    if (transactionType !== 'all') params.set('transactionType', transactionType);
    if (accountId !== 'all') params.set('accountId', accountId);
    
    // Reload with filtered parameters
    window.location.href = `${window.location.pathname}?${params.toString()}`;
}

// ===== CHART CREATION FUNCTIONS =====

/**
 * Create the income vs expense chart
 */
function createIncomeExpenseChart() {
    const ctx = document.getElementById('incomeExpenseChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    // Extract data from global variables exposed by Flask template
    let months = [], incomeData = [], expenseData = [];
    
    if (typeof monthly_labels !== 'undefined' && typeof monthly_amounts !== 'undefined') {
        months = monthly_labels;
        expenseData = monthly_amounts;
        
        // Generate sample income data if none provided
        if (typeof total_income !== 'undefined') {
            // Create synthetic income data based on total income
            const totalIncome = parseFloat(document.getElementById('totalIncome').textContent.replace(/[^0-9.-]+/g, ""));
            incomeData = months.map((_, index) => {
                // Distribute total income somewhat evenly with some randomness
                return totalIncome / months.length * (0.8 + Math.random() * 0.4);
            });
        } else {
            incomeData = expenseData.map(exp => exp * (1 + Math.random() * 0.5));
        }
    }
    
    // Calculate net cash flow
    const netData = months.map((_, i) => {
        const income = incomeData[i] || 0;
        const expense = expenseData[i] || 0;
        return income - expense;
    });
    
    // Get currency symbol
    const baseCurrencySymbol = getCurrencySymbol();
    
    // Create the chart
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Income',
                    data: incomeData,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 2
                },
                {
                    label: 'Expenses',
                    data: expenseData,
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
                            return baseCurrencySymbol + value;
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
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                label += baseCurrencySymbol + context.parsed.y.toFixed(2);
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
 * Create the transaction type distribution chart
 */
function createTransactionTypeChart() {
    const ctx = document.getElementById('transactionTypeChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    // Get data from the page - clean up the values to ensure we have numbers
    const totalIncome = parseFloat(document.getElementById('totalIncome')?.textContent.replace(/[^0-9.-]+/g, '') || 0);
    const totalExpenses = parseFloat(document.getElementById('totalExpenses')?.textContent.replace(/[^0-9.-]+/g, '') || 0);
    const totalTransfers = parseFloat(document.getElementById('transferStat')?.textContent.replace(/[^0-9.-]+/g, '') || 0);
    
    // Get currency symbol
    const baseCurrencySymbol = getCurrencySymbol();
    
    // Create the chart
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Income', 'Expenses', 'Transfers'],
            datasets: [{
                data: [totalIncome, totalExpenses, totalTransfers],
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
                            return `${label}: ${baseCurrencySymbol}${value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create the category distribution chart
 */
function createCategoryChart() {
    const ctx = document.getElementById('categoryChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    // Get data from global variables
    let categoryNames = [], categoryTotals = [];
    
    if (typeof category_names !== 'undefined' && typeof category_totals !== 'undefined') {
        categoryNames = category_names;
        categoryTotals = category_totals;
    } else {
        // Fallback with sample data if global variables are not available
        categoryNames = ['Food', 'Housing', 'Transportation', 'Entertainment', 'Shopping', 'Health', 'Other'];
        categoryTotals = [350, 1200, 250, 180, 320, 150, 100];
    }
    
    // Get currency symbol
    const baseCurrencySymbol = getCurrencySymbol();
    
    // Create the chart
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
                            return `${context.label}: ${baseCurrencySymbol}${value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create the tag distribution chart
 */
function createTagChart() {
    const ctx = document.getElementById('tagChart');
    if (!ctx || typeof Chart === 'undefined') return;
    
    // Get data from global variables
    let tagNames = [], tagTotals = [], tagColors = [];
    
    if (typeof tag_names !== 'undefined' && typeof tag_totals !== 'undefined') {
        tagNames = tag_names;
        tagTotals = tag_totals;
        tagColors = tag_colors || tagNames.map(() => `#${Math.floor(Math.random()*16777215).toString(16)}`);
    } else {
        // Fallback with sample data if global variables are not available
        tagNames = ['Groceries', 'Dining', 'Bills', 'Rent', 'Gas', 'Coffee'];
        tagTotals = [280, 320, 150, 950, 120, 75];
        tagColors = ['#f43f5e', '#fb7185', '#f97316', '#fb923c', '#f59e0b', '#fbbf24'];
    }
    
    // Get currency symbol
    const baseCurrencySymbol = getCurrencySymbol();
    
    // Create the chart
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
                            return `${baseCurrencySymbol}${context.raw.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return baseCurrencySymbol + value;
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
            }
        }
    });
}

// ===== GAUGE CHARTS =====

/**
 * Initialize gauge charts for financial health indicators
 */
function initializeGaugeCharts() {
    // Set up savings rate gauge
    const savingsRateValue = parseFloat(document.getElementById('savingsRateDisplay')?.textContent) || 0;
    updateGaugeValue('savingsRateGauge', savingsRateValue, 100);
    
    // Set up expense-to-income ratio gauge
    const expenseRatioValue = parseFloat(document.getElementById('expenseIncomeRatioDisplay')?.textContent) || 0;
    updateGaugeValue('expenseIncomeRatioGauge', expenseRatioValue, 100);
    
    // Set up liquidity gauge
    const liquidityValue = parseFloat(document.getElementById('liquidityDisplay')?.textContent) || 0;
    updateGaugeValue('liquidityGauge', liquidityValue, 12);
    
    // Set up account growth gauge
    const growthValue = parseFloat(document.getElementById('accountGrowthDisplay')?.textContent) || 0;
    updateGaugeValue('accountGrowthGauge', growthValue, 30);
}

/**
 * Update gauge chart with value
 * @param {string} gaugeId - ID of the gauge element
 * @param {number} value - Value to display
 * @param {number} maxValue - Maximum value for scaling
 */
function updateGaugeValue(gaugeId, value, maxValue) {
    const displayElement = document.getElementById(gaugeId);
    if (!displayElement) return;
    
    // Calculate percentage for gauge fill
    let percentage = Math.min((value / maxValue) * 100, 100);
    
    // Ensure percentage is positive for display purpose
    if (isNaN(percentage) || percentage < 0) percentage = 0;
    
    // Determine color based on value
    let color;
    if (gaugeId === 'expenseIncomeRatioGauge') {
        // For this gauge, lower is better
        color = percentage < 60 ? '#10b981' : (percentage < 80 ? '#f59e0b' : '#ef4444');
    } else {
        // For other gauges, higher is better
        color = percentage > 60 ? '#10b981' : (percentage > 30 ? '#f59e0b' : '#ef4444');
    }
    
    // Apply styling to create gauge effect
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
    const displayValueElement = document.getElementById(`${gaugeId.replace('Gauge', 'Display')}`);
    let displayText = '';
    
    if (displayValueElement) {
        displayText = displayValueElement.textContent;
    } else {
        // Format based on gauge type
        if (gaugeId.includes('Rate') || gaugeId.includes('Ratio')) {
            displayText = `${value.toFixed(1)}%`;
        } else {
            displayText = value.toFixed(1);
        }
    }
    
    innerCircle.textContent = displayText;
    displayElement.appendChild(innerCircle);
}

// ===== COMPARISON TAB FUNCTIONALITY =====

/**
 * Set up the comparison tab functionality
 */
function setupComparisonTab() {
    // Button event handlers
    const runComparisonBtn = document.getElementById('runComparisonBtn');
    const setDefaultPeriodsBtn = document.getElementById('setDefaultPeriodsBtn');
    
    if (runComparisonBtn) {
        runComparisonBtn.addEventListener('click', runComparison);
    }
    
    if (setDefaultPeriodsBtn) {
        setDefaultPeriodsBtn.addEventListener('click', setDefaultComparisonPeriods);
    }
    
    // Initialize with default dates
    initializeComparisonDates();
    
    // Add hover effects to comparison buttons
    document.querySelectorAll('#comparison button').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 6px 10px -1px rgba(139, 92, 246, 0.3)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 6px -1px rgba(139, 92, 246, 0.2)';
        });
    });
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
    
    // Only set if not already set by URL params
    if (!primaryStartDate.value || !primaryEndDate.value || !comparisonStartDate.value || !comparisonEndDate.value) {
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
}

/**
 * Format date as YYYY-MM-DD for input fields
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Set default periods and run comparison
 */
function setDefaultComparisonPeriods() {
    initializeComparisonDates();
    runComparison();
}

/**
 * Run the comparison analysis
 */
function runComparison() {
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
        updateComparisonChartTitle(metric);
        
        // Update summary data
        updateComparisonSummary(data);
        
        // Generate comparison chart based on metric
        generateComparisonChart(data, metric);
        
        // Show detailed comparison table for categories and tags
        showDetailedComparisonTable(data, metric);
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
 * Update the comparison chart title based on metric
 */
function updateComparisonChartTitle(metric) {
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
 * Update comparison summary with data
 */
function updateComparisonSummary(data) {
    const baseCurrencySymbol = getCurrencySymbol();
    
    // Update primary period summary
    updateElementText('primaryTotalSpending', baseCurrencySymbol + data.primary.totalSpending.toFixed(2));
    updateElementText('primaryTransactionCount', data.primary.transactionCount);
    updateElementText('primaryTopCategory', data.primary.topCategory);
    
    // Update comparison period summary
    updateElementText('comparisonTotalSpending', baseCurrencySymbol + data.comparison.totalSpending.toFixed(2));
    updateElementText('comparisonTransactionCount', data.comparison.transactionCount);
    updateElementText('comparisonTopCategory', data.comparison.topCategory);
    
    // Calculate differences
    const spendingDiff = data.primary.totalSpending - data.comparison.totalSpending;
    const spendingDiffPercent = data.comparison.totalSpending !== 0 
        ? (spendingDiff / data.comparison.totalSpending) * 100 
        : 0;
    
    const transactionDiff = data.primary.transactionCount - data.comparison.transactionCount;
    const transactionDiffPercent = data.comparison.transactionCount !== 0 
        ? (transactionDiff / data.comparison.transactionCount) * 100 
        : 0;
    
    // Calculate daily averages
    const primaryDays = getDaysInRange(
        document.getElementById('primaryStartDate').value,
        document.getElementById('primaryEndDate').value
    );
    const comparisonDays = getDaysInRange(
        document.getElementById('comparisonStartDate').value,
        document.getElementById('comparisonEndDate').value
    );
    
    const primaryDailyAvg = data.primary.totalSpending / primaryDays;
    const comparisonDailyAvg = data.comparison.totalSpending / comparisonDays;
    const dailyAvgDiff = primaryDailyAvg - comparisonDailyAvg;
    const dailyAvgDiffPercent = comparisonDailyAvg !== 0 
        ? (dailyAvgDiff / comparisonDailyAvg) * 100 
        : 0;
    
    // Update difference card
    updateDifferenceElement('spendingDifference', 'spendingChangePercent', spendingDiff, spendingDiffPercent, true);
    updateDifferenceElement('transactionDifference', 'transactionChangePercent', transactionDiff, transactionDiffPercent, false);
    updateDifferenceElement('avgDailyDifference', 'avgDailyChangePercent', dailyAvgDiff, dailyAvgDiffPercent, true);