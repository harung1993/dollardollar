/**
 * Global Currency Helper
 * This script ensures the base currency symbol is consistently 
 * available across all JavaScript files.
 * 
 * Place this in a new file called currency_helper.js in your static/js directory
 */

// Initialize global currency symbol
window.initCurrencySymbol = function(symbol) {
    // Set the global variable
    window.baseCurrencySymbol = symbol || '$';
    
    // Also expose it through a consistent API
    window.CurrencyHelper = {
        getSymbol: function() {
            return window.baseCurrencySymbol;
        },
        formatAmount: function(amount) {
            return window.baseCurrencySymbol + parseFloat(amount).toFixed(2);
        }
    };
    
    console.log('Currency symbol initialized:', window.baseCurrencySymbol);
};

// If there's a currency symbol in a data attribute, use it
document.addEventListener('DOMContentLoaded', function() {
    // Look for currency data in various places
    const currencyElement = document.getElementById('currency-data');
    if (currencyElement && currencyElement.dataset.symbol) {
        window.initCurrencySymbol(currencyElement.dataset.symbol);
    } else if (typeof baseCurrencySymbol !== 'undefined') {
        // If it was already set in a script tag, use that
        window.initCurrencySymbol(baseCurrencySymbol);
    } else {
        // Default fallback
        window.initCurrencySymbol('$');
    }
    
    // Dispatch an event that other scripts can listen for
    document.dispatchEvent(new CustomEvent('currencySymbolReady'));
});