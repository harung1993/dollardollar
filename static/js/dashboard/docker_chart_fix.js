/**
 * Docker Chart Fix - Ensures chart data is properly loaded in Docker environment
 *
 * This script should be included before any other scripts in your dashboard.html
 * to ensure data is correctly initialized for Chart.js
 */

// Immediately run when script loads
(function() {
    console.log("Docker chart fix initializing...");
    
    // Create a custom event that will trigger when data is ready
    const chartDataReadyEvent = new CustomEvent('chartDataReady');
    
    // Function to extract and initialize chart data from the page
    function initializeChartData() {
        console.log("Initializing chart data...");
        
        try {
            // Check if data is already initialized
            if (window.chartDataInitialized) {
                console.log("Chart data already initialized, skipping");
                return;
            }
            
            // Set default currency symbol
            if (!window.baseCurrencySymbol) {
                window.baseCurrencySymbol = '$';
                console.log("Set default base currency symbol");
            }
            
            // Extract category data if not already defined
            if (!window.categoryData) {
                console.log("Extracting category data from the page");
                window.categoryData = [];
                
                // Look for category data in script tags
                document.querySelectorAll('script').forEach(script => {
                    if (script.textContent.includes('categoryData')) {
                        try {
                            // Try to extract the array from the script content
                            const match = script.textContent.match(/window\.categoryData\s*=\s*(\[[\s\S]*?\]);/);
                            if (match && match[1]) {
                                // Safely evaluate the array string
                                const categoryDataStr = match[1].replace(/\\"/g, '"');
                                window.categoryData = JSON.parse(categoryDataStr);
                                console.log(`Extracted ${window.categoryData.length} category items`);
                            }
                        } catch (e) {
                            console.error("Error extracting category data:", e);
                        }
                    }
                });
            }
            
            // Extract asset/debt trend data if not already defined
            if (!window.assetTrendsMonths) {
                console.log("Extracting asset/debt trend data from the page");
                
                // Look for trend data in script tags
                document.querySelectorAll('script').forEach(script => {
                    if (script.textContent.includes('assetTrendsMonths')) {
                        try {
                            // Try to extract the arrays
                            let match = script.textContent.match(/window\.assetTrendsMonths\s*=\s*([^;]*);/);
                            if (match && match[1]) {
                                window.assetTrendsMonths = JSON.parse(match[1]);
                            }
                            
                            match = script.textContent.match(/window\.assetTrends\s*=\s*([^;]*);/);
                            if (match && match[1]) {
                                window.assetTrends = JSON.parse(match[1]);
                            }
                            
                            match = script.textContent.match(/window\.debtTrends\s*=\s*([^;]*);/);
                            if (match && match[1]) {
                                window.debtTrends = JSON.parse(match[1]);
                            }
                            
                            console.log("Extracted trend data");
                        } catch (e) {
                            console.error("Error extracting trend data:", e);
                        }
                    }
                });
            }
            
            // Mark as initialized
            window.chartDataInitialized = true;
            
            // Dispatch event to notify charts they can initialize
            document.dispatchEvent(chartDataReadyEvent);
            console.log("Chart data initialized successfully");
        } catch (error) {
            console.error("Error in chart data initialization:", error);
        }
    }
    
    // Initialize on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log("DOM loaded, initializing chart data");
        
        // Call immediately for the initial load
        initializeChartData();
        
        // Also, set a fallback timer in case some scripts load slowly
        setTimeout(function() {
            if (!window.chartDataInitialized) {
                console.log("Fallback initialization of chart data");
                initializeChartData();
            }
        }, 1000);
    });
    
    // Also run immediately in case the DOM is already loaded
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log("Document already interactive/complete, initializing immediately");
        initializeChartData();
    }
    
    // Create a global check function
    window.checkChartData = function() {
        console.log("Chart data check:", {
            initialized: window.chartDataInitialized || false,
            baseCurrencySymbol: window.baseCurrencySymbol,
            categoryData: window.categoryData ? `${window.categoryData.length} items` : 'Not found',
            assetTrendsMonths: window.assetTrendsMonths ? `${window.assetTrendsMonths.length} items` : 'Not found',
            assetTrends: window.assetTrends ? `${window.assetTrends.length} items` : 'Not found',
            debtTrends: window.debtTrends ? `${window.debtTrends.length} items` : 'Not found'
        });
    };
})();