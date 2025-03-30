// comparison_tab.js - JavaScript for the comparison tab functionality

/**
 * Initialize the comparison tab when the document is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize comparison tab functionality
    initializeComparisonTab();
    
    // Handle tab switching to hide/show the customize view panel
    const analyticsTab = document.getElementById('analyticsTab');
    if (analyticsTab) {
        analyticsTab.addEventListener('shown.bs.tab', function(event) {
            const customizeViewPanel = document.getElementById('customizeViewPanel');
            if (customizeViewPanel) {
                // Hide customize view when comparison tab is active
                if (event.target.id === 'comparison-tab') {
                    customizeViewPanel.style.display = 'none';
                } else {
                    customizeViewPanel.style.display = 'block';
                }
            }
        });
    }
});

/**
 * Initialize the comparison tab functionality
 */
function initializeComparisonTab() {
    // Set up button event handlers
    const runComparisonBtn = document.getElementById('runComparisonBtn');
    const setDefaultPeriodsBtn = document.getElementById('setDefaultPeriodsBtn');
    const thisMonthVsLastBtn = document.getElementById('thisMonthVsLastBtn');
    const thisQuarterVsLastBtn = document.getElementById('thisQuarterVsLastBtn');
    const thisYearVsLastBtn = document.getElementById('thisYearVsLastBtn');
    const customRangeBtn = document.getElementById('customRangeBtn');
    
    // Chart view toggle buttons
    const lineChartToggle = document.getElementById('lineChartToggle');
    const barChartToggle = document.getElementById('barChartToggle');
    const tableToggle = document.getElementById('tableToggle');
    
    // Detailed table buttons
    const exportCSVBtn = document.getElementById('exportCSVBtn');
    const sortByDiffBtn = document.getElementById('sortByDiffBtn');
    
    // Add event listeners to buttons
    if (runComparisonBtn) {
        runComparisonBtn.addEventListener('click', runComparison);
    }
    
    if (setDefaultPeriodsBtn) {
        setDefaultPeriodsBtn.addEventListener('click', setDefaultComparisonPeriods);
    }
    
    // Quick period selection buttons
    if (thisMonthVsLastBtn) {
        thisMonthVsLastBtn.addEventListener('click', () => setPresetPeriod('month'));
    }
    
    if (thisQuarterVsLastBtn) {
        thisQuarterVsLastBtn.addEventListener('click', () => setPresetPeriod('quarter'));
    }
    
    if (thisYearVsLastBtn) {
        thisYearVsLastBtn.addEventListener('click', () => setPresetPeriod('year'));
    }
    
    if (customRangeBtn) {
        customRangeBtn.addEventListener('click', () => {
            // Just highlight this button to show custom ranges are being used
            highlightButton(customRangeBtn);
        });
    }
    
    // Chart view toggle event listeners
    if (lineChartToggle && barChartToggle && tableToggle) {
        lineChartToggle.addEventListener('click', () => toggleChartView('line'));
        barChartToggle.addEventListener('click', () => toggleChartView('bar'));
        tableToggle.addEventListener('click', () => toggleChartView('table'));
    }
    
    // Detail table button event listeners
    if (exportCSVBtn) {
        exportCSVBtn.addEventListener('click', exportTableToCSV);
    }
    
    if (sortByDiffBtn) {
        sortByDiffBtn.addEventListener('click', toggleTableSort);
    }
    
    // Initialize with default dates
    initializeComparisonDates();
    
    // Add hover effects to buttons
    addButtonHoverEffects();
}

/**
 * Highlight a single button in a group
 */
function highlightButton(activeButton) {
    // Find all buttons in the same group
    const buttonGroup = activeButton.closest('.btn-group');
    if (!buttonGroup) return;
    
    // Remove active class from all buttons
    buttonGroup.querySelectorAll('.btn').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'rgba(99, 102, 241, 0.1)';
    });
    
    // Add active class to the clicked button
    activeButton.classList.add('active');
    activeButton.style.background = 'rgba(99, 102, 241, 0.2)';
}

/**
 * Toggle between line chart, bar chart and table views
 */
function toggleChartView(viewType) {
    const chartView = document.getElementById('chartView');
    const tableView = document.getElementById('tableView');
    const lineToggle = document.getElementById('lineChartToggle');
    const barToggle = document.getElementById('barChartToggle');
    const tableToggle = document.getElementById('tableToggle');
    
    if (!chartView || !tableView) return;
    
    // Reset all toggle buttons
    [lineToggle, barToggle, tableToggle].forEach(btn => {
        if (btn) {
            btn.classList.remove('active');
            btn.style.background = 'rgba(99, 102, 241, 0.1)';
        }
    });
    
    // Handle different view types
    if (viewType === 'table') {
        chartView.style.display = 'none';
        tableView.style.display = 'block';
        if (tableToggle) {
            tableToggle.classList.add('active');
            tableToggle.style.background = 'rgba(99, 102, 241, 0.2)';
        }
        
        // Make sure we have a table to show
        populateDataTable();
    } else {
        chartView.style.display = 'block';
        tableView.style.display = 'none';
        
        // Set appropriate chart type
        updateChartType(viewType);
        
        // Highlight the correct toggle
        if (viewType === 'line' && lineToggle) {
            lineToggle.classList.add('active');
            lineToggle.style.background = 'rgba(99, 102, 241, 0.2)';
        } else if (viewType === 'bar' && barToggle) {
            barToggle.classList.add('active');
            barToggle.style.background = 'rgba(99, 102, 241, 0.2)';
        }
    }
}

/**
 * Update the chart type (line or bar)
 */
function updateChartType(chartType) {
    if (window.comparisonChart) {
        window.comparisonChart.config.type = chartType;
        window.comparisonChart.update();
    }
}

/**
 * Populate the data table view with the current chart data
 */
function populateDataTable() {
    if (!window.comparisonChart) return;
    
    const tableBody = document.querySelector('#comparisonTable tbody');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Get data from chart
    const labels = window.comparisonChart.data.labels;
    const datasets = window.comparisonChart.data.datasets;
    
    if (!labels || !datasets || datasets.length < 2) return;
    
    // Add a row for each label
    labels.forEach((label, index) => {
        const primaryValue = datasets[0].data[index] || 0;
        const comparisonValue = datasets[1].data[index] || 0;
        
        // Calculate difference and percentage
        const difference = primaryValue - comparisonValue;
        const percentChange = comparisonValue !== 0 
            ? (difference / comparisonValue) * 100 
            : 0;
        
        // Determine color based on value
        const colorClass = difference < 0 ? 'text-success' : 'text-danger';
        
        // Create row
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${label}</td>
            <td style="text-align: right;">${baseCurrencySymbol}${primaryValue.toFixed(2)}</td>
            <td style="text-align: right;">${baseCurrencySymbol}${comparisonValue.toFixed(2)}</td>
            <td style="text-align: right; color: ${difference < 0 ? '#10b981' : '#ef4444'};">
                ${difference < 0 ? '-' : '+'}${baseCurrencySymbol}${Math.abs(difference).toFixed(2)}
            </td>
            <td style="text-align: right; color: ${difference < 0 ? '#10b981' : '#ef4444'};">
                ${difference < 0 ? '-' : '+'}${Math.abs(percentChange).toFixed(1)}%
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add total row
    const primaryTotal = datasets[0].data.reduce((sum, val) => sum + val, 0);
    const comparisonTotal = datasets[1].data.reduce((sum, val) => sum + val, 0);
    const totalDifference = primaryTotal - comparisonTotal;
    const totalPercentChange = comparisonTotal !== 0 
        ? (totalDifference / comparisonTotal) * 100 
        : 0;
    
    const totalRow = document.createElement('tr');
    totalRow.style.fontWeight = 'bold';
    totalRow.style.borderTop = '2px solid rgba(148, 163, 184, 0.3)';
    
    totalRow.innerHTML = `
        <td>TOTAL</td>
        <td style="text-align: right;">${baseCurrencySymbol}${primaryTotal.toFixed(2)}</td>
        <td style="text-align: right;">${baseCurrencySymbol}${comparisonTotal.toFixed(2)}</td>
        <td style="text-align: right; color: ${totalDifference < 0 ? '#10b981' : '#ef4444'};">
            ${totalDifference < 0 ? '-' : '+'}${baseCurrencySymbol}${Math.abs(totalDifference).toFixed(2)}
        </td>
        <td style="text-align: right; color: ${totalDifference < 0 ? '#10b981' : '#ef4444'};">
            ${totalDifference < 0 ? '-' : '+'}${Math.abs(totalPercentChange).toFixed(1)}%
        </td>
    `;
    
    tableBody.appendChild(totalRow);
}

/**
 * Export the comparison table to CSV
 */
function exportTableToCSV() {
    const table = document.getElementById('detailedComparisonTable');
    if (!table) return;
    
    // Get table headers
    const headers = [];
    table.querySelectorAll('thead th').forEach(th => {
        headers.push(th.textContent.trim());
    });
    
    // Get table rows
    const rows = [];
    table.querySelectorAll('tbody tr').forEach(tr => {
        const row = [];
        tr.querySelectorAll('td').forEach(td => {
            // Strip HTML and get just the text
            row.push(td.textContent.trim());
        });
        rows.push(row);
    });
    
    // Combine headers and rows
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // Set attributes and trigger download
    link.setAttribute('href', url);
    link.setAttribute('download', 'comparison_data.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Toggle the sort order of the detailed comparison table
 */
function toggleTableSort() {
    const table = document.getElementById('detailedComparisonTable');
    const tbody = table?.querySelector('tbody');
    const button = document.getElementById('sortByDiffBtn');
    
    if (!table || !tbody || !button) return;
    
    // Check current sort state (default is alphabetical)
    const currentState = button.getAttribute('data-sort') || 'alpha';
    const newState = currentState === 'alpha' ? 'diff' : 'alpha';
    
    // Get all rows except the total row (last one)
    const rows = Array.from(tbody.querySelectorAll('tr:not(:last-child)'));
    
    // Sort the rows based on the new state
    if (newState === 'diff') {
        // Sort by absolute difference (column 3) descending
        rows.sort((a, b) => {
            const aValue = parseFloat(a.cells[3].textContent.replace(/[^0-9.-]+/g, ""));
            const bValue = parseFloat(b.cells[3].textContent.replace(/[^0-9.-]+/g, ""));
            return Math.abs(bValue) - Math.abs(aValue);
        });
        
        // Update button text
        button.innerHTML = '<i class="fas fa-sort-alpha-down me-1"></i>Sort Alphabetically';
    } else {
        // Sort alphabetically by first column
        rows.sort((a, b) => {
            return a.cells[0].textContent.localeCompare(b.cells[0].textContent);
        });
        
        // Update button text
        button.innerHTML = '<i class="fas fa-sort-amount-down me-1"></i>Sort by Difference';
    }
    
    // Store the new state
    button.setAttribute('data-sort', newState);
    
    // Re-append rows in new order
    rows.forEach(row => tbody.appendChild(row));
    
    // Keep the total row at the bottom
    const totalRow = tbody.querySelector('tr:last-child');
    if (totalRow) {
        tbody.appendChild(totalRow);
    }
}

/**
 * Initialize the comparison tab date fields with default values
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
 * Set preset time periods for comparison
 */
function setPresetPeriod(periodType) {
    const primaryStartDate = document.getElementById('primaryStartDate');
    const primaryEndDate = document.getElementById('primaryEndDate');
    const comparisonStartDate = document.getElementById('comparisonStartDate');
    const comparisonEndDate = document.getElementById('comparisonEndDate');
    
    if (!primaryStartDate || !primaryEndDate || !comparisonStartDate || !comparisonEndDate) {
        return;
    }
    
    const today = new Date();
    
    // Highlight the appropriate button
    const buttonId = `this${periodType.charAt(0).toUpperCase() + periodType.slice(1)}VsLastBtn`;
    const button = document.getElementById(buttonId);
    if (button) {
        highlightButton(button);
    }
    
    switch (periodType) {
        case 'month':
            // Current month vs previous month
            const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            
            primaryStartDate.value = formatDate(firstDayOfMonth);
            primaryEndDate.value = formatDate(lastDayOfMonth);
            
            const firstDayOfLastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const lastDayOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
            
            comparisonStartDate.value = formatDate(firstDayOfLastMonth);
            comparisonEndDate.value = formatDate(lastDayOfLastMonth);
            break;
            
        case 'quarter':
            // Current quarter vs previous quarter
            const currentQuarter = Math.floor(today.getMonth() / 3);
            
            const firstDayOfQuarter = new Date(today.getFullYear(), currentQuarter * 3, 1);
            const lastDayOfQuarter = new Date(today.getFullYear(), (currentQuarter + 1) * 3, 0);
            
            primaryStartDate.value = formatDate(firstDayOfQuarter);
            primaryEndDate.value = formatDate(lastDayOfQuarter);
            
            const firstDayOfLastQuarter = new Date(
                currentQuarter === 0 ? today.getFullYear() - 1 : today.getFullYear(), 
                currentQuarter === 0 ? 9 : (currentQuarter - 1) * 3, 
                1
            );
            const lastDayOfLastQuarter = new Date(
                currentQuarter === 0 ? today.getFullYear() - 1 : today.getFullYear(), 
                currentQuarter === 0 ? 12 : currentQuarter * 3, 
                0
            );
            
            comparisonStartDate.value = formatDate(firstDayOfLastQuarter);
            comparisonEndDate.value = formatDate(lastDayOfLastQuarter);
            break;
            
        case 'year':
            // Current year vs previous year
            const firstDayOfYear = new Date(today.getFullYear(), 0, 1);
            const lastDayOfYear = new Date(today.getFullYear(), 11, 31);
            
            primaryStartDate.value = formatDate(firstDayOfYear);
            primaryEndDate.value = formatDate(lastDayOfYear);
            
            const firstDayOfLastYear = new Date(today.getFullYear() - 1, 0, 1);
            const lastDayOfLastYear = new Date(today.getFullYear() - 1, 11, 31);
            
            comparisonStartDate.value = formatDate(firstDayOfLastYear);
            comparisonEndDate.value = formatDate(lastDayOfLastYear);
            break;
    }
}

/**
 * Set default comparison periods
 */
function setDefaultComparisonPeriods() {
    // Set default periods (current month vs previous month)
    setPresetPeriod('month');
    
    // Run the comparison automatically
    runComparison();
}

/**
 * Format a date as YYYY-MM-DD for input fields
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Format a date for display (Month DD, YYYY)
 */
function formatDateForDisplay(dateStr) {
    const date = new Date(dateStr);
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

/**
 * Add hover animations to buttons
 */
function addButtonHoverEffects() {
    // Add hover animations to all buttons in comparison tab
    const buttons = document.querySelectorAll('#comparison .btn');
    
    buttons.forEach(btn => {
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
 * Run the comparison based on form inputs
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
    
    // Update period badges
    document.getElementById('primaryPeriodBadge').textContent = 
        `${formatDateForDisplay(primaryStart)} - ${formatDateForDisplay(primaryEnd)}`;
    document.getElementById('comparisonPeriodBadge').textContent = 
        `${formatDateForDisplay(comparisonStart)} - ${formatDateForDisplay(comparisonEnd)}`;
    
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
        updateComparisonSummary(data);
        
        // Generate comparison chart based on metric
        generateComparisonChart(data, metric);
        
        // Show detailed comparison table for categories and tags
        showDetailedComparisonTable(data, metric);
        
        // Calculate and display advanced metrics
        calculateAdvancedMetrics(data);
        
        // Update circular progress indicator
        updateDifferenceIndicator(data);
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
 * Update the circular progress indicator for difference visualization
 */
function updateDifferenceIndicator(data) {
    const percentageDifference = document.getElementById('percentageDifference');
    const spendingDifference = document.getElementById('spendingDifference');
    
    if (!percentageDifference || !spendingDifference) return;
    
    // Calculate spending difference and percentage
    const primaryTotal = data.primary.totalSpending;
    const comparisonTotal = data.comparison.totalSpending;
    const difference = primaryTotal - comparisonTotal;
    const differencePercent = comparisonTotal !== 0 
        ? (difference / comparisonTotal) * 100 
        : 0;
    
    // Determine color based on value (for expenses, negative is good)
    const color = difference < 0 ? '#10b981' : '#ef4444';
    
    // Update percentage pie chart
    const absPercentage = Math.min(Math.abs(differencePercent), 100);
    const conic = `conic-gradient(${color} 0% ${absPercentage}%, transparent ${absPercentage}% 100%)`;
    percentageDifference.style.background = conic;
    
    // Update inner text with percentage
    const innerDiv = percentageDifference.querySelector('div');
    if (innerDiv) {
        innerDiv.textContent = `${differencePercent > 0 ? '+' : ''}${differencePercent.toFixed(1)}%`;
        innerDiv.style.color = color;
    }
    
    // Update difference amount text
    spendingDifference.textContent = `${baseCurrencySymbol}${Math.abs(difference).toFixed(2)}`;
    spendingDifference.style.color = color;
    
    // Update icon
    const iconContainer = spendingDifference.nextElementSibling;
    if (iconContainer) {
        const icon = iconContainer.querySelector('i');
        if (icon) {
            icon.className = difference < 0 ? 'fas fa-arrow-down me-1' : 'fas fa-arrow-up me-1';
            icon.style.color = color;
        }
    }
}

/**
 * Calculate advanced metrics for comparison display
 */
function calculateAdvancedMetrics(data) {
    try {
        // Get date ranges
        const primaryStart = document.getElementById('primaryStartDate').value;
        const primaryEnd = document.getElementById('primaryEndDate').value;
        const comparisonStart = document.getElementById('comparisonStartDate').value;
        const comparisonEnd = document.getElementById('comparisonEndDate').value;
        
        // Calculate days in each period
        const primaryDays = getDaysInRange(primaryStart, primaryEnd);
        const comparisonDays = getDaysInRange(comparisonStart, comparisonEnd);
        
        // Daily average spending
        const primaryDailyAvg = data.primary.totalSpending / primaryDays;
        const comparisonDailyAvg = data.comparison.totalSpending / comparisonDays;
        const dailyAvgDiff = primaryDailyAvg - comparisonDailyAvg;
        const dailyAvgDiffPercent = comparisonDailyAvg !== 0 
            ? (dailyAvgDiff / comparisonDailyAvg) * 100 
            : 0;
        
        // Average transaction size
        const primaryAvgTransaction = data.primary.transactionCount > 0 
            ? data.primary.totalSpending / data.primary.transactionCount
            : 0;
        const comparisonAvgTransaction = data.comparison.transactionCount > 0 
            ? data.comparison.totalSpending / data.comparison.transactionCount
            : 0;
        const avgTransactionDiff = primaryAvgTransaction - comparisonAvgTransaction;
        const avgTransactionDiffPercent = comparisonAvgTransaction !== 0 
            ? (avgTransactionDiff / comparisonAvgTransaction) * 100 
            : 0;
        
        // Transaction frequency (per day)
        const primaryFrequency = data.primary.transactionCount / primaryDays;
        const comparisonFrequency = data.comparison.transactionCount / comparisonDays;
        const frequencyDiff = primaryFrequency - comparisonFrequency;
        const frequencyDiffPercent = comparisonFrequency !== 0 
            ? (frequencyDiff / comparisonFrequency) * 100 
            : 0;
        
        // Update UI elements with calculated metrics
        // Daily average
        document.getElementById('primaryDailyAvg').textContent = `${baseCurrencySymbol}${primaryDailyAvg.toFixed(2)}`;
        document.getElementById('comparisonDailyAvg').textContent = `${baseCurrencySymbol}${comparisonDailyAvg.toFixed(2)}`;
        updateMetricChangeIndicator('avgDailyChangePercent', dailyAvgDiffPercent);
        
        // Average transaction
        document.getElementById('primaryAvgTransaction').textContent = `${baseCurrencySymbol}${primaryAvgTransaction.toFixed(2)}`;
        document.getElementById('comparisonAvgTransaction').textContent = `${baseCurrencySymbol}${comparisonAvgTransaction.toFixed(2)}`;
        updateMetricChangeIndicator('avgTransactionChangePercent', avgTransactionDiffPercent);
        
        // Transaction frequency
        document.getElementById('primaryFrequency').textContent = `${primaryFrequency.toFixed(1)}/day`;
        document.getElementById('comparisonFrequency').textContent = `${comparisonFrequency.toFixed(1)}/day`;
        updateMetricChangeIndicator('frequencyChangePercent', frequencyDiffPercent);
        
        // Calculate savings rate if we have income data
        if (data.primary.income !== undefined && data.comparison.income !== undefined) {
            const primarySavingsRate = data.primary.income > 0 
                ? ((data.primary.income - data.primary.totalSpending) / data.primary.income * 100)
                : 0;
            const comparisonSavingsRate = data.comparison.income > 0 
                ? ((data.comparison.income - data.comparison.totalSpending) / data.comparison.income * 100)
                : 0;
            const savingsRateDiff = primarySavingsRate - comparisonSavingsRate;
            const savingsRateDiffPercent = comparisonSavingsRate !== 0 
                ? (savingsRateDiff / comparisonSavingsRate * 100)
                : 0;
            
            document.getElementById('primaryCustomMetric').textContent = `${primarySavingsRate.toFixed(1)}%`;
            document.getElementById('comparisonCustomMetric').textContent = `${comparisonSavingsRate.toFixed(1)}%`;
            updateMetricChangeIndicator('customMetricChangePercent', savingsRateDiffPercent);
            document.getElementById('customMetricLabel').textContent = 'Savings Rate';
        }
        
        // Update progress bars
        // Update progress bars
        updateProgressBars(data);
    } catch (error) {
        console.error('Error calculating advanced metrics:', error);
    }
}

/**
 * Update progress bars based on comparison data
 */
function updateProgressBars(data) {
    // Get the container elements
    const primaryBars = document.querySelectorAll('.primary-progress');
    const comparisonBars = document.querySelectorAll('.comparison-progress');
    
    if (!primaryBars.length || !comparisonBars.length) return;
    
    // Calculate the primary percentage 
    const primarySpending = data.primary.totalSpending;
    const comparisonSpending = data.comparison.totalSpending;
    
    // Maximum will be the higher of the two, with a 20% buffer
    const maxSpending = Math.max(primarySpending, comparisonSpending) * 1.2;
    
    // Set width percentages of progress bars
    primaryBars.forEach(bar => {
        const width = (primarySpending / maxSpending) * 100;
        bar.style.width = `${width}%`;
        // Set color based on comparison (for expenses, lower is better)
        bar.style.backgroundColor = primarySpending <= comparisonSpending ? '#10b981' : '#ef4444';
    });
    
    comparisonBars.forEach(bar => {
        const width = (comparisonSpending / maxSpending) * 100;
        bar.style.width = `${width}%`;
        // Set color based on comparison (for expenses, higher is worse)
        bar.style.backgroundColor = comparisonSpending >= primarySpending ? '#ef4444' : '#10b981';
    });
}

/**
 * Update the indicator for metric changes
 */
function updateMetricChangeIndicator(elementId, percentChange) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // For expenses, negative change is good
    const isNegative = percentChange < 0;
    const metric = document.getElementById('comparisonMetric')?.value || 'spending';
    
    // Determine color (for expenses, negative is good; for income, positive is good)
    const color = metric === 'income' 
        ? (isNegative ? '#ef4444' : '#10b981')
        : (isNegative ? '#10b981' : '#ef4444');
    
    // Update text and icon
    element.innerHTML = `<i class="fas ${isNegative ? 'fa-arrow-down' : 'fa-arrow-up'} me-1"></i> ${Math.abs(percentChange).toFixed(1)}%`;
    element.style.color = color;
}

/**
 * Update the chart title based on the selected metric
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
            case 'income':
                chartTitleElement.textContent = 'Income Comparison';
                break;
            default:
                chartTitleElement.textContent = 'Spending Comparison';
        }
    }
}

/**
 * Update comparison summary with the data from server
 */
function updateComparisonSummary(data) {
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
    updateDifferenceElement(spendingDiffElem, spendingChangeElem, spendingDiff, spendingDiffPercent, true);
    
    const transactionDiffElem = document.getElementById('transactionDifference');
    const transactionChangeElem = document.getElementById('transactionChangePercent');
    updateDifferenceElement(transactionDiffElem, transactionChangeElem, transactionDiff, transactionDiffPercent, false);
    
    const avgDailyDiffElem = document.getElementById('avgDailyDifference');
    const avgDailyChangeElem = document.getElementById('avgDailyChangePercent');
    updateDifferenceElement(avgDailyDiffElem, avgDailyChangeElem, dailyAvgDiff, dailyAvgDiffPercent, true);
    
    // Update metrics summary cards
    if (document.getElementById('totalDifference')) {
        document.getElementById('totalDifference').textContent = baseCurrencySymbol + Math.abs(spendingDiff).toFixed(2);
        
        // Set color and icon
        const icon = document.getElementById('totalDifferenceIcon');
        if (icon) {
            icon.className = spendingDiff < 0 ? 'fas fa-arrow-down me-2 text-success' : 'fas fa-arrow-up me-2 text-danger';
        }
        
        // Set direction text
        const direction = document.getElementById('totalDifferenceDirection');
        if (direction) {
            direction.textContent = spendingDiff < 0 ? 'decrease' : 'increase';
            direction.className = spendingDiff < 0 ? 'text-success' : 'text-danger';
        }
    }
}

/**
 * Update difference element with formatted values and styling
 */
function updateDifferenceElement(diffElement, percentElement, difference, percentChange, isCurrency) {
    if (!diffElement || !percentElement) return;
    
    // For expense metrics, negative values (decrease) are good
    const isNegative = difference < 0;
    const formattedDiff = isCurrency 
        ? baseCurrencySymbol + Math.abs(difference).toFixed(2) 
        : Math.abs(difference);
    
    diffElement.textContent = formattedDiff;
    percentElement.textContent = (isNegative ? 'Decreased by ' : 'Increased by ') + Math.abs(percentChange).toFixed(1) + '%';
    
    // For expenses, red for increase, green for decrease (for income it would be the opposite)
    const metric = document.getElementById('comparisonMetric').value;
    
    if (metric === 'income') {
        diffElement.style.color = isNegative ? '#ef4444' : '#10b981';
        percentElement.style.color = isNegative ? '#ef4444' : '#10b981';
    } else {
        diffElement.style.color = isNegative ? '#10b981' : '#ef4444';
        percentElement.style.color = isNegative ? '#10b981' : '#ef4444';
    }
}

/**
 * Count days between two date strings
 */
function getDaysInRange(startDateStr, endDateStr) {
    const startDate = new Date(startDateStr);
    const endDate = new Date(endDateStr);
    const diffTime = Math.abs(endDate - startDate);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // +1 to include both start and end days
}

/**
 * Generate comparison chart based on the provided data and selected metric
 */
function generateComparisonChart(data, metric) {
    // Get the canvas context
    const ctx = document.getElementById('comparisonChart');
    
    // Destroy existing chart if any
    if (window.comparisonChart) {
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
                            label += baseCurrencySymbol + context.parsed.y.toFixed(2);
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
                            return baseCurrencySymbol + value;
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
                            return baseCurrencySymbol + value;
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
                            return baseCurrencySymbol + value;
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
                            return baseCurrencySymbol + value;
                        }
                    }
                }
            };
            break;
            
        case 'income':
            // Income comparison
            chartData.labels = data.incomeDateLabels || data.dateLabels || [];
            
            chartData.datasets = [
                {
                    label: 'Primary Period',
                    data: data.primary.incomeAmounts || [],
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Comparison Period',
                    data: data.comparison.incomeAmounts || [],
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: '#3b82f6',
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
                            return baseCurrencySymbol + value;
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
    
    // Update the table view if it's currently showing
    if (document.getElementById('tableView').style.display === 'block') {
        populateDataTable();
    }
}

/**
 * Show detailed comparison table for categories, tags, and payment methods
 */
function showDetailedComparisonTable(data, metric) {
    // Get table container and set visibility
    const tableContainer = document.getElementById('categoryTagComparison');
    const tableTitle = document.getElementById('comparisonTableTitle');
    const itemTypeHeader = document.getElementById('itemTypeHeader');
    const tableBody = document.getElementById('detailedComparisonBody');
    
    if (!tableContainer || !tableTitle || !tableBody) return;
    
    // Only show detailed table for categories, tags, and payment methods
    if (['categories', 'tags', 'payment', 'income'].includes(metric)) {
        tableContainer.style.display = 'block';
        
        // Update table title
        if (metric === 'categories') {
            tableTitle.textContent = 'Category Breakdown';
            itemTypeHeader.textContent = 'Category';
        } else if (metric === 'tags') {
            tableTitle.textContent = 'Tag Breakdown';
            itemTypeHeader.textContent = 'Tag';
        } else if (metric === 'income') {
            tableTitle.textContent = 'Income Sources Breakdown';
            itemTypeHeader.textContent = 'Source';
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
            // For income, positive difference (increase) is good
            const isPositive = difference > 0;
            const colorClass = metric === 'income' 
                ? (isPositive ? 'text-success' : 'text-danger')
                : (isPositive ? 'text-danger' : 'text-success');
                
            const differenceColor = metric === 'income'
                ? (isPositive ? '#10b981' : '#ef4444')
                : (isPositive ? '#ef4444' : '#10b981');
            
            row.innerHTML = `
                <td>${label}</td>
                <td style="text-align: right;">${baseCurrencySymbol}${primaryAmount.toFixed(2)}</td>
                <td style="text-align: right;">${baseCurrencySymbol}${comparisonAmount.toFixed(2)}</td>
                <td style="text-align: right; color: ${differenceColor};">${isPositive ? '+' : '-'}${baseCurrencySymbol}${Math.abs(difference).toFixed(2)}</td>
                <td style="text-align: right; color: ${differenceColor};">${isPositive ? '+' : '-'}${Math.abs(percentChange).toFixed(1)}%</td>
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
            
        const isPositiveTotal = totalDifference > 0;
        const totalDifferenceColor = metric === 'income'
            ? (isPositiveTotal ? '#10b981' : '#ef4444')
            : (isPositiveTotal ? '#ef4444' : '#10b981');
        
        const totalRow = document.createElement('tr');
        totalRow.style.borderTop = '2px solid rgba(148, 163, 184, 0.3)';
        totalRow.style.fontWeight = 'bold';
        
        totalRow.innerHTML = `
            <td>TOTAL</td>
            <td style="text-align: right;">${baseCurrencySymbol}${totalPrimary.toFixed(2)}</td>
            <td style="text-align: right;">${baseCurrencySymbol}${totalComparison.toFixed(2)}</td>
            <td style="text-align: right; color: ${totalDifferenceColor};">${isPositiveTotal ? '+' : '-'}${baseCurrencySymbol}${Math.abs(totalDifference).toFixed(2)}</td>
            <td style="text-align: right; color: ${totalDifferenceColor};">${isPositiveTotal ? '+' : '-'}${Math.abs(totalPercentChange).toFixed(1)}%</td>
        `;
        
        tableBody.appendChild(totalRow);
        
    } else {
        tableContainer.style.display = 'none';
    }
}

// Add a function to generate a downloadable report
function generateComparisonReport() {
    // Check if we have comparison data
    if (!window.comparisonChart || !document.getElementById('comparisonResults').style.display === 'block') {
        alert('Please run a comparison first to generate a report.');
        return;
    }
    
    try {
        // Gather report data
        const primaryPeriod = document.getElementById('primaryPeriodBadge').textContent;
        const comparisonPeriod = document.getElementById('comparisonPeriodBadge').textContent;
        const metric = document.getElementById('comparisonMetric').value;
        
        // Primary data
        const primaryTotal = document.getElementById('primaryTotalSpending').textContent;
        const primaryCount = document.getElementById('primaryTransactionCount').textContent;
        const primaryTop = document.getElementById('primaryTopCategory').textContent;
        
        // Comparison data
        const comparisonTotal = document.getElementById('comparisonTotalSpending').textContent;
        const comparisonCount = document.getElementById('comparisonTransactionCount').textContent;
        const comparisonTop = document.getElementById('comparisonTopCategory').textContent;
        
        // Differences
        const spendingDiff = document.getElementById('spendingDifference').textContent;
        const spendingChange = document.getElementById('spendingChangePercent').textContent;
        
        // Create report content
        const reportContent = `
            # Financial Comparison Report
            
            ## Periods Compared
            - Primary Period: ${primaryPeriod}
            - Comparison Period: ${comparisonPeriod}
            
            ## Summary
            
            | Metric | Primary Period | Comparison Period | Difference |
            |--------|---------------|-------------------|------------|
            | Total Spending | ${primaryTotal} | ${comparisonTotal} | ${spendingDiff} (${spendingChange}) |
            | Transaction Count | ${primaryCount} | ${comparisonCount} | - |
            | Top Category | ${primaryTop} | ${comparisonTop} | - |
            
            ## Analysis
            
            The data shows a ${spendingChange.toLowerCase()} in spending between the two periods.
            
            ### Recommendations
            
            ${generateRecommendations(spendingChange)}
            
            *Report generated on ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}*
        `;
        
        // Create a blob and download link
        const blob = new Blob([reportContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        link.href = url;
        link.download = `financial_comparison_${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
    } catch (error) {
        console.error('Error generating report:', error);
        alert('An error occurred while generating the report. Please try again.');
    }
}

// Generate simple recommendations based on spending trends
function generateRecommendations(spendingChange) {
    if (spendingChange.includes('Decreased')) {
        return `
        - Continue the positive trend of reduced spending
        - Consider setting up automatic savings for the difference amount
        - Review categories where spending increased to identify opportunities for further savings
        `;
    } else {
        return `
        - Review top spending categories to identify areas for potential savings
        - Consider setting a budget for categories with the biggest increases
        - Look for recurring expenses that could be reduced or eliminated
        `;
    }
}