/**
 * Enhanced Multi-Select Dropdown
 * Replaces standard multi-select elements with user-friendly dropdowns with checkboxes
 */

// Add the required CSS styles
const style = document.createElement('style');
style.textContent = `
    .custom-multi-select-container {
        position: relative;
    }
    
    .custom-multi-select-display {
        cursor: pointer;
        min-height: 38px;
        white-space: normal;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px;
        padding: 6px 10px;
    }
    
    .custom-multi-select-display .placeholder {
        color: #6c757d;
    }
    
    .custom-multi-select-dropdown {
        position: absolute;
        top: 100%;
        left: 0;
        width: 100%;
        max-height: 250px;
        overflow-y: auto;
        z-index: 1050;
        border: 1px solid #444;
        border-radius: 0.25rem;
        padding: 8px;
        margin-top: 2px;
        background-color: #2d2d2d;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
    }
    
    .custom-multi-select-option {
        display: flex;
        align-items: center;
        padding: 6px 10px;
        cursor: pointer;
        color: #fff;
        border-radius: 0.25rem;
        transition: background-color 0.15s ease;
    }
    
    .custom-multi-select-option:hover {
        background-color: #3d4a5c;
    }
    
    .enhanced-multi-select {
        position: absolute;
        opacity: 0;
        pointer-events: none;
    }
`;

// Only add the style once
if (!document.getElementById('enhanced-multi-select-styles')) {
    style.id = 'enhanced-multi-select-styles';
    document.head.appendChild(style);
}

// Function to enhance all multi-selects
function enhanceMultiSelects() {
    // Find all elements with the enhanced-multi-select class or the edit_split_with id
    const selects = Array.from(document.querySelectorAll('.enhanced-multi-select')).concat(
        Array.from(document.querySelectorAll('#edit_split_with'))
    );
    
    selects.forEach(select => {
        // Skip if not a multi-select or already enhanced
        if (!select.multiple) return;
        if (select.getAttribute('data-enhanced') === 'true') return;
        
        console.log('Enhancing multi-select:', select.id || select.name);
        
        // Mark as enhanced
        select.setAttribute('data-enhanced', 'true');
        select.classList.add('enhanced-multi-select'); // Ensure it has the class
        
        // Create container
        const container = document.createElement('div');
        container.className = 'custom-multi-select-container';
        select.parentNode.insertBefore(container, select);
        
        // Move select into container
        container.appendChild(select);
        
        // Create display box
        const displayBox = document.createElement('div');
        displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
        displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
        container.insertBefore(displayBox, select);
        
        // Create dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'custom-multi-select-dropdown';
        dropdown.style.display = 'none';
        container.appendChild(dropdown);
        
        // Create search box
        const searchBox = document.createElement('input');
        searchBox.type = 'text';
        searchBox.className = 'form-control form-control-sm bg-dark text-light mb-2';
        searchBox.placeholder = 'Search...';
        dropdown.appendChild(searchBox);
        
        // Create options container
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-multi-select-options';
        dropdown.appendChild(optionsContainer);
        
        // Add options
        refreshOptions();
        
        // Function to refresh options
        function refreshOptions() {
            optionsContainer.innerHTML = '';
            
            Array.from(select.options).forEach(option => {
                // Skip disabled options
                if (option.disabled) return;
                
                const optionItem = document.createElement('div');
                optionItem.className = 'custom-multi-select-option';
                optionItem.setAttribute('data-value', option.value);
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'form-check-input me-2';
                checkbox.checked = option.selected;
                
                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.textContent = option.textContent;
                
                optionItem.appendChild(checkbox);
                optionItem.appendChild(label);
                optionsContainer.appendChild(optionItem);
                
                // Handle clicks
                optionItem.addEventListener('click', e => {
                    if (select.disabled) return;
                    
                    e.preventDefault();
                    e.stopPropagation();
                    
                    checkbox.checked = !checkbox.checked;
                    option.selected = checkbox.checked;
                    
                    // Trigger change event
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // Update display
                    updateDisplay();
                });
            });
        }
        
        // Update display
        function updateDisplay() {
            const selected = Array.from(select.selectedOptions);
            
            if (selected.length === 0) {
                displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
            } else {
                displayBox.innerHTML = selected
                    .map(option => `<span class="badge bg-primary me-1">${option.text}</span>`)
                    .join('');
            }
        }
        
        // Toggle dropdown
        displayBox.addEventListener('click', e => {
            if (select.disabled) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const isOpen = dropdown.style.display === 'block';
            
            // Close all other dropdowns
            document.querySelectorAll('.custom-multi-select-dropdown').forEach(d => {
                if (d !== dropdown) d.style.display = 'none';
            });
            
            dropdown.style.display = isOpen ? 'none' : 'block';
            
            if (!isOpen) {
                searchBox.value = '';
                searchBox.focus();
                
                // Show all options
                Array.from(optionsContainer.children).forEach(option => {
                    option.style.display = '';
                });
            }
        });
        
        // Search functionality
        searchBox.addEventListener('input', () => {
            const query = searchBox.value.toLowerCase();
            
            Array.from(optionsContainer.children).forEach(option => {
                const text = option.textContent.toLowerCase();
                option.style.display = text.includes(query) ? '' : 'none';
            });
        });
        
        // Close when clicking outside
        document.addEventListener('click', e => {
            if (!container.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
        
        // Update on change
        select.addEventListener('change', () => {
            refreshOptions();
            updateDisplay();
        });
        
        // Initialize display
        updateDisplay();
        
        // Handle disabled state
        if (select.disabled) {
            container.style.opacity = '0.5';
            container.style.pointerEvents = 'none';
        }
        
        // Watch for disabled changes
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                if (mutation.attributeName === 'disabled') {
                    if (select.disabled) {
                        container.style.opacity = '0.5';
                        container.style.pointerEvents = 'none';
                    } else {
                        container.style.opacity = '1';
                        container.style.pointerEvents = 'auto';
                    }
                }
            });
        });
        
        observer.observe(select, { attributes: true });
    });
}

// Run when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, enhancing multi-selects');
    enhanceMultiSelects();
});

// Also run when edit button is clicked
document.addEventListener('click', function(e) {
    if (e.target.closest('.edit-expense-btn')) {
        console.log('Edit button clicked, will enhance multi-selects');
        // Wait for form to load with multiple attempts
        setTimeout(enhanceMultiSelects, 300);
        setTimeout(enhanceMultiSelects, 600);
        setTimeout(enhanceMultiSelects, 1000);
    }
});

// Make global
window.enhanceMultiSelects = enhanceMultiSelects;

// Check for new elements periodically
setInterval(() => {
    const unenhanced = document.querySelectorAll('.enhanced-multi-select:not([data-enhanced="true"]), #edit_split_with:not([data-enhanced="true"])');
    if (unenhanced.length > 0) {
        console.log('Found unenhanced multi-selects, enhancing now');
        enhanceMultiSelects();
    }
}, 500);