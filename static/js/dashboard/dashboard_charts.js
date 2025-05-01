/**
 * Dashboard Charts Module - Dollar Dollar Bill Y'all
 * 
 * This module handles all charting functionality for the dashboard
 * and ensures it's properly isolated from other JavaScript modules.
 */
const DashboardCharts = (function() {
    // Store chart instances to enable updates
    let categoryChart = null;
    let assetDebtChart = null;
    
    // Initialize the module
    function init() {
        console.log("DashboardCharts module initializing...");
        
        // Set up event listeners for chart initialization
        document.addEventListener('DOMContentLoaded', function() {
            console.log("DOM loaded, setting up charts...");
            setupCharts();
        });
        
        // Return public API
        return {
            setupCategoryDonutChart,
            setupAssetDebtChart,
            refreshCharts: setupCharts
        };
    }
    
    // Main function to set up all charts
    function setupCharts() {
        try {
            console.log("Setting up dashboard charts...");
            setupCategoryDonutChart();
            setupAssetDebtChart();
            setupSettlementFunctions();
            console.log("Charts setup complete");
        } catch (error) {
            console.error("Error setting up charts:", error);
        }
    }
    
    // Set up the category donut chart
    function setupCategoryDonutChart() {
        console.log("Setting up category donut chart...");
        const ctx = document.getElementById('categoryDonutChart');
        if (!ctx) {
            console.warn("Category donut chart element not found");
            return;
        }
        
        // If Chart.js is not loaded, report error and return
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded. Cannot create category donut chart.");
            return;
        }
        
        // Clear any existing chart
        if (categoryChart instanceof Chart) {
            categoryChart.destroy();
        }
        
        try {
            // Get category data from the page
            const categoryData = window.categoryData || [];
            
            // If no data or empty array, show placeholder message
            if (!categoryData || categoryData.length === 0) {
                ctx.height = 150;
                const noDataMsg = document.createElement('div');
                noDataMsg.className = 'text-center py-4';
                noDataMsg.innerHTML = '<p class="text-muted">No category spending data available yet. Add transactions with categories to see your spending breakdown.</p>';
                ctx.parentNode.insertBefore(noDataMsg, ctx);
                ctx.style.display = 'none';
                
                // Clear the legend area
                const legendContainer = document.getElementById('categoryLegend');
                if (legendContainer) {
                    legendContainer.innerHTML = '';
                }
                return;
            }
            
            const categoryNames = categoryData.map(c => c.name);
            const categoryValues = categoryData.map(c => c.amount);
            const categoryColors = categoryData.map(c => c.color);
            
            // Create the donut chart
            categoryChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: categoryNames,
                    datasets: [{
                        data: categoryValues,
                        backgroundColor: categoryColors,
                        borderColor: 'rgba(0, 0, 0, 0.1)',
                        borderWidth: 2,
                        borderRadius: 2,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw;
                                    const total = categoryValues.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    const currencySymbol = window.baseCurrencySymbol || '$';
                                    return `${label}: ${currencySymbol}${value.toFixed(2)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
            
            // Create custom legend
            createCategoryLegend(categoryData);
            console.log("Category donut chart created successfully");
        } catch (error) {
            console.error("Error creating category donut chart:", error);
        }
    }
    
    // Create custom category legend
    function createCategoryLegend(categories) {
        const legendContainer = document.getElementById('categoryLegend');
        if (!legendContainer) {
            console.warn("Category legend container not found");
            return;
        }
        
        // Clear existing content
        legendContainer.innerHTML = '';
        
        // Calculate total
        const total = categories.reduce((sum, category) => sum + category.amount, 0);
        
        // Create scrollable container
        const scrollContainer = document.createElement('div');
        scrollContainer.className = 'legend-container';
        scrollContainer.style.maxHeight = '200px';
        scrollContainer.style.overflowY = 'auto';
        
        // Get currency symbol
        const currencySymbol = window.baseCurrencySymbol || '$';
        
        // Add each category to legend
        categories.forEach(category => {
            const percentage = ((category.amount / total) * 100).toFixed(1);
            
            const item = document.createElement('div');
            item.className = 'd-flex justify-content-between align-items-center mb-2';
            
            const leftSide = document.createElement('div');
            leftSide.className = 'd-flex align-items-center';
            
            const colorDot = document.createElement('div');
            colorDot.className = 'rounded-circle me-2';
            colorDot.style.width = '12px';
            colorDot.style.height = '12px';
            colorDot.style.backgroundColor = category.color;
            
            const nameElem = document.createElement('div');
            nameElem.className = 'small';
            nameElem.textContent = category.name;
            
            leftSide.appendChild(colorDot);
            leftSide.appendChild(nameElem);
            
            const rightSide = document.createElement('div');
            rightSide.className = 'd-flex justify-content-end';
            
            const amountElem = document.createElement('small');
            amountElem.className = 'text-muted me-2';
            amountElem.textContent = `${currencySymbol}${category.amount.toFixed(2)}`;
            
            const percentElem = document.createElement('small');
            percentElem.className = 'badge bg-info';
            percentElem.textContent = `${percentage}%`;
            
            rightSide.appendChild(amountElem);
            rightSide.appendChild(percentElem);
            
            item.appendChild(leftSide);
            item.appendChild(rightSide);
            
            scrollContainer.appendChild(item);
        });
        
        legendContainer.appendChild(scrollContainer);
    }
    
    // Set up the asset vs debt chart
    function setupAssetDebtChart() {
        console.log("Setting up asset debt chart...");
        const ctx = document.getElementById('assetDebtChart');
        if (!ctx) {
            console.warn("Asset debt chart element not found");
            return;
        }
        
        // If Chart.js is not loaded, report error and return
        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded. Cannot create asset debt chart.");
            return;
        }
        
        // Clear any existing chart
        if (assetDebtChart instanceof Chart) {
            assetDebtChart.destroy();
        }
        
        try {
            // Get trend data from the window object
            const months = window.assetTrendsMonths || [];
            const assetData = window.assetTrends || [];
            const debtData = window.debtTrends || [];
            
            // Check if we have actual data
            if (!months || months.length === 0 || assetData.length === 0) {
                // No data - show message instead of chart
                ctx.height = 150;
                const noDataMsg = document.createElement('div');
                noDataMsg.className = 'text-center py-4';
                noDataMsg.innerHTML = '<p class="text-muted">No asset or debt data available yet. Add accounts to see your financial trends.</p>';
                ctx.parentNode.insertBefore(noDataMsg, ctx);
                ctx.style.display = 'none';
                return;
            }
            
            // Check if we have investment data
            const hasInvestments = window.investmentTotal > 0;
            
            // Prepare datasets
            const datasets = [
                {
                    label: 'Assets',
                    data: assetData,
                    borderColor: 'rgba(46, 213, 115, 0.8)',  // Green for assets
                    backgroundColor: 'rgba(46, 213, 115, 0.2)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Debts',
                    data: debtData,
                    borderColor: 'rgba(255, 71, 87, 0.8)',  // Red for debts
                    backgroundColor: 'rgba(255, 71, 87, 0.2)',
                    fill: true,
                    tension: 0.4
                }
            ];
            
            // Get currency symbol
            const currencySymbol = window.baseCurrencySymbol || '$';
            
            // Create the chart with actual data
            assetDebtChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += currencySymbol + context.parsed.y.toFixed(2);
                                    }
                                    return label;
                                },
                                // Add a footer to the tooltip for investment information
                                footer: function(tooltipItems) {
                                    if (hasInvestments) {
                                        const total = tooltipItems[0].parsed.y;
                                        const investmentTotal = window.investmentTotal || 0;
                                        const investmentPercent = (investmentTotal / total * 100).toFixed(1);
                                        return `Investments: ${currencySymbol}${investmentTotal.toFixed(2)} (${investmentPercent}%)`;
                                    }
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return currencySymbol + value;
                                }
                            }
                        }
                    }
                }
            });
            
            console.log("Asset debt chart created successfully");
        } catch (error) {
            console.error("Error creating asset debt chart:", error);
        }
    }
    
    // Set up settlement functions
    function setupSettlementFunctions() {
        console.log("Setting up settlement functions...");
        
        try {
            // Add listeners for showing/hiding settlement form
            document.querySelectorAll('.record-settlement-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const userId = this.getAttribute('data-user-id');
                    const userName = this.getAttribute('data-user-name');
                    const amount = parseFloat(this.getAttribute('data-amount')) || 0;
                    const iOwe = this.getAttribute('data-i-owe') === 'true';
                    
                    prepareSettlement(userId, userName, amount, iOwe);
                });
            });
            
            console.log("Settlement functions setup complete");
        } catch (error) {
            console.error("Error setting up settlement functions:", error);
        }
    }
    
    // Prepare Settlement Form
    function prepareSettlement(userId, userName, amount, iOwe) {
        const payerSelect = document.getElementById('payer_id');
        const receiverSelect = document.getElementById('receiver_id');
        const amountInput = document.getElementById('settlement_amount');
        const dateInput = document.getElementById('settlement_date');
        
        if (!payerSelect || !receiverSelect || !amountInput || !dateInput) {
            console.error("Settlement form elements not found");
            return;
        }
        
        // Logic to set payer and receiver based on iOwe
        if (iOwe) {
            // Current user pays the selected user
            payerSelect.value = document.querySelector('meta[name="current-user-id"]')?.content || "";
            receiverSelect.value = userId;
        } else {
            // Selected user pays the current user
            payerSelect.value = userId;
            receiverSelect.value = document.querySelector('meta[name="current-user-id"]')?.content || "";
        }
        
        amountInput.value = amount;
        dateInput.value = new Date().toISOString().split('T')[0];
        
        toggleSettlementForm();
    }
    
    // Toggle settlement form visibility
    function toggleSettlementForm() {
        const form = document.getElementById('settlementFormContainer');
        
        if (form) {
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
            
            // Scroll to the form if showing
            if (form.style.display === 'block') {
                form.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }
    
    // Make settlement functions available globally
    window.prepareSettlement = prepareSettlement;
    window.toggleSettlementForm = toggleSettlementForm;
    
    // Return initialized module
    return init();
})();

// Create global references for backward compatibility
window.setupCategoryDonutChart = DashboardCharts.setupCategoryDonutChart;
window.setupAssetDebtChart = DashboardCharts.setupAssetDebtChart;
window.setupSettlementFunctions = DashboardCharts.setupSettlementFunctions;