/**
 * Enhanced Transaction Module 
 * 
 * A consolidated module that handles both adding and editing transactions
 * with support for category splits, expense splits, and multi-select dropdowns.
 */

const TransactionModule = (function() {
    // Private variables
    let baseCurrencySymbol = '$'; // Default fallback
  
    /**
     * Initialize the module and set up global event handlers
     */
    function init() {
      // Set base currency symbol from various potential sources
      baseCurrencySymbol = window.baseCurrencySymbol || 
                           document.querySelector('meta[name="base-currency-symbol"]')?.content || 
                           document.getElementById('currency-data')?.getAttribute('data-symbol') || 
                           '$';
      
      console.log("Transaction module initialized with currency symbol:", baseCurrencySymbol);
      
      // Set up global event delegation
      setupGlobalEventHandlers();
      
      // Initialize multi-select functionality globally
      addMultiSelectStyles();
      
      // First initialization of relevant forms if they're already in the DOM
      if (document.getElementById('editTransactionForm')) {
        console.log("Found edit form during init");
        enhanceEditTransactionForm();
      }
      
      return {
        // Public methods
        openAddTransactionPanel,
        openEditTransactionPanel,
        initializeMultiSelect: enhanceMultiSelects,
        showMessage,
        closeSlidePanel,
        // Add the submitEditForm to the public API
        submitEditForm
      };
    }
  
    /**
     * Set up global event handlers using event delegation
     */
    function setupGlobalEventHandlers() {
      // Handle clicks on edit buttons
      document.addEventListener('click', function(e) {
        // Edit expense button click
        if (e.target.closest('.edit-expense-btn')) {
          const button = e.target.closest('.edit-expense-btn');
          const expenseId = button.getAttribute('data-expense-id');
          console.log("Edit button clicked for expense ID:", expenseId);
          openEditTransactionPanel(expenseId);
        }
        
        // Add transaction button click
        else if (e.target.closest('#openAddTransactionBtn')) {
          console.log("Add transaction button clicked");
          openAddTransactionPanel();
        }
        
        // Category split toggle click
        else if (e.target.closest('.split-toggle')) {
          const toggle = e.target.closest('.split-toggle');
          const expenseId = toggle.getAttribute('data-expense-id');
          console.log("Split toggle clicked for ID:", expenseId);
          handleSplitToggleClick(toggle, expenseId);
        }
      });
  
      // Initialize transaction list UI enhancements once the DOM is ready
      document.addEventListener('DOMContentLoaded', function() {
        console.log("DOM loaded - enhancing transaction UI");
        fixTransactionSplitsDisplay();
        enhanceMultiSelects();
      });
    }
    
    /**
     * Handle click on category split toggle
     */
    function handleSplitToggleClick(toggle, expenseId) {
      if (!toggle || !expenseId) return;
      
      // Find detail element
      const detailElement = document.getElementById(`split-categories-${expenseId}`);
      if (!detailElement) {
        console.error(`Detail element not found for expense ID: ${expenseId}`);
        return;
      }
      
      // Toggle visibility
      const isHidden = detailElement.style.display === 'none' || !detailElement.style.display;
      detailElement.style.display = isHidden ? 'block' : 'none';
      
      // Update icon
      const icon = toggle.querySelector('i');
      if (icon) {
        if (isHidden) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        } else {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
      }
      
      // Load data if necessary
      if (isHidden) {
        // Style the container for better visibility
        detailElement.style.color = '#ffffff';
        detailElement.style.backgroundColor = '#2d3748';
        detailElement.style.padding = '8px';
        detailElement.style.borderRadius = '4px';
        detailElement.style.marginTop = '5px';
        
        // Check if we need to load data
        if (detailElement.querySelector('.loading') || detailElement.innerHTML.trim() === '') {
          loadCategorySplits(expenseId, detailElement);
        }
      }
    }
  
    /**
     * Load category splits via AJAX
     */
    function loadCategorySplits(expenseId, detailElement) {
      // Show loading indicator
      detailElement.innerHTML = '<div class="text-white text-center"><i class="fas fa-spinner fa-spin me-2"></i>Loading split details...</div>';
      
      fetch(`/get_category_splits/${expenseId}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data.success && data.splits && data.splits.length > 0) {
            // Create split detail UI with guaranteed white text
            let html = '<div class="list-group list-group-flush" style="background-color: #374151; border-radius: 6px; color: white !important;">';
            
            data.splits.forEach(split => {
              // Get category details
              const categoryName = split.category?.name || 'Unknown';
              const categoryColor = split.category?.color || '#6c757d';
              const categoryIcon = split.category?.icon || 'fa-tag';
              const amount = parseFloat(split.amount) || 0;
              
              html += `
                <div class="list-group-item py-2" style="background-color: #374151; border-color: #4b5563; color: white !important;">
                  <div class="d-flex justify-content-between align-items-center" style="color: white !important;">
                    <div style="color: white !important;">
                      <span class="badge me-2" style="background-color: ${categoryColor}; color: white;">
                        <i class="fas ${categoryIcon}"></i>
                      </span>
                      <span class="category-name-text" style="color: white !important;">${categoryName}</span>
                    </div>
                    <span class="badge" style="background-color: #3b82f6; color: white; font-weight: bold; font-size: 0.9em;">
                      ${baseCurrencySymbol}${amount.toFixed(2)}
                    </span>
                  </div>
                </div>
              `;
            });
            
            html += '</div>';
            detailElement.innerHTML = html;
            
            // Add additional style to ensure text is visible
            const style = document.createElement('style');
            style.textContent = `
              #split-categories-${expenseId} .list-group-item,
              #split-categories-${expenseId} .category-name-text,
              #split-categories-${expenseId} .list-group-item * {
                color: white !important;
              }
            `;
            document.head.appendChild(style);
          } else {
            detailElement.innerHTML = '<div class="text-white p-2">No split categories found</div>';
          }
        })
        .catch(error => {
          console.error('Error loading category splits:', error);
          detailElement.innerHTML = `<div class="text-danger p-2">Error loading splits: ${error.message}</div>`;
        });
    }
  
    /**
     * Fix the display of category splits in the transaction list
     */
    function fixTransactionSplitsDisplay() {
      console.log("Fixing transaction splits display...");
      
      // Find all transactions with category splits
      const splitElements = document.querySelectorAll('[data-has-splits="true"]');
      console.log(`Found ${splitElements.length} transactions with splits`);
      
      splitElements.forEach(element => {
        const expenseId = element.getAttribute('data-expense-id');
        console.log(`Processing expense ID: ${expenseId}`);
        
        // Find the toggle element within this transaction row
        const toggle = element.querySelector('.split-toggle');
        if (toggle) {
          console.log(`Toggle found for expense ID: ${expenseId}`);
          
          // Improve visibility
          toggle.style.color = '#38bdf8'; // A bright blue for visibility
          toggle.style.border = '1px solid #38bdf8';
          toggle.style.borderRadius = '4px';
          toggle.style.padding = '2px 6px';
          toggle.style.margin = '2px 0';
          toggle.style.display = 'inline-block';
          toggle.style.cursor = 'pointer';
          
          // Make sure we don't duplicate click handlers
          // by using a data attribute to mark as enhanced
          if (!toggle.hasAttribute('data-enhanced')) {
            toggle.setAttribute('data-enhanced', 'true');
          }
        } else {
          console.warn(`No toggle found for expense ID: ${expenseId}`);
        }
      });
    }
  


function enhanceMultiSelects(selector = '.enhanced-multi-select, #edit_split_with, #split_with') {
  const selects = document.querySelectorAll(selector);
  
  console.log(`Found ${selects.length} multi-select elements to enhance`);
  
  selects.forEach(select => {
    // Skip if not a multi-select or already enhanced
    if (!select.multiple || select.getAttribute('data-enhanced') === 'true') {
      return;
    }
    
    console.log(`Enhancing multi-select: ${select.id || select.name}`);
    
    // Mark as enhanced to prevent duplicate initialization
    select.setAttribute('data-enhanced', 'true');
    
    // Create wrapper container
    const container = document.createElement('div');
    container.className = 'custom-multi-select-container';
    select.parentNode.insertBefore(container, select);
    
    // Add the select to the container but properly hide it
    // This is the critical fix: we need to explicitly hide the original select
    container.appendChild(select);
    select.style.display = 'none'; // Explicitly hide the select element
    select.style.position = 'absolute'; // Position it absolutely to take it out of the flow
    select.style.opacity = '0'; // Make it fully transparent
    select.style.pointerEvents = 'none'; // Disable pointer events
    
    // Create display element
    const displayBox = document.createElement('div');
    displayBox.className = 'form-control bg-dark text-light custom-multi-select-display';
    displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
    container.insertBefore(displayBox, select);
    
    // Create dropdown menu container
    const dropdownMenu = document.createElement('div');
    dropdownMenu.className = 'custom-multi-select-dropdown bg-dark';
    dropdownMenu.style.display = 'none';
    container.appendChild(dropdownMenu);
    
    // Add search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control form-control-sm bg-dark text-light mb-2 custom-multi-select-search';
    searchInput.placeholder = 'Search...';
    dropdownMenu.appendChild(searchInput);
    
    // Create option list
    const optionList = document.createElement('div');
    optionList.className = 'custom-multi-select-options';
    dropdownMenu.appendChild(optionList);
    
    // Populate options
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
      optionList.appendChild(optionItem);
      
      // Handle option click
      optionItem.addEventListener('click', (e) => {
        e.stopPropagation();
        checkbox.checked = !checkbox.checked;
        
        // Update the original select element
        option.selected = checkbox.checked;
        
        // Dispatch change event on the original select
        select.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Update display box
        updateDisplayBox();
      });
    });
    
    // Function to update display box
    function updateDisplayBox() {
      const selectedOptions = Array.from(select.selectedOptions);
      
      if (selectedOptions.length === 0) {
        displayBox.innerHTML = '<span class="placeholder">Select options...</span>';
      } else {
        displayBox.innerHTML = selectedOptions
          .map(opt => `<span class="badge bg-primary me-1">${opt.textContent}</span>`)
          .join(' ');
      }
    }
    
    // Initial update of display box
    updateDisplayBox();
    
    // Toggle dropdown on display box click
    displayBox.addEventListener('click', (e) => {
      // If the select is disabled, don't allow opening the dropdown
      if (select.disabled) {
        return;
      }
      
      e.stopPropagation();
      const isVisible = dropdownMenu.style.display === 'block';
      dropdownMenu.style.display = isVisible ? 'none' : 'block';
      
      if (!isVisible) {
        searchInput.focus();
        
        // Position dropdown
        dropdownMenu.style.width = '100%';
        
        // Position dropdown above or below based on available space
        const rect = displayBox.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        if (spaceBelow < 300 && rect.top > 300) {
          dropdownMenu.style.bottom = displayBox.offsetHeight + 'px';
          dropdownMenu.style.top = 'auto';
        } else {
          dropdownMenu.style.top = displayBox.offsetHeight + 'px';
          dropdownMenu.style.bottom = 'auto';
        }
      }
    });
    
    // Handle search
    searchInput.addEventListener('input', (e) => {
      const searchText = e.target.value.toLowerCase();
      
      Array.from(optionList.children).forEach(optionItem => {
        const optionText = optionItem.querySelector('label').textContent.toLowerCase();
        optionItem.style.display = optionText.includes(searchText) ? 'block' : 'none';
      });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!container.contains(e.target)) {
        dropdownMenu.style.display = 'none';
      }
    });
    
    // Sync original select with our custom one when it changes externally
    select.addEventListener('change', () => {
      Array.from(optionList.children).forEach(optionItem => {
        const value = optionItem.getAttribute('data-value');
        const option = select.querySelector(`option[value="${value}"]`);
        const checkbox = optionItem.querySelector('input[type="checkbox"]');
        
        if (option && checkbox) {
          checkbox.checked = option.selected;
        }
      });
      
      updateDisplayBox();
    });
    
    // Also add a CSS rule to hide all enhanced multi-selects
    const style = document.createElement('style');
    style.textContent = `
      select[data-enhanced="true"] {
        display: none !important;
        position: absolute !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
      }
    `;
    document.head.appendChild(style);
    
    console.log(`Enhanced multi-select initialized for element with ID: ${select.id}`);
  });
}

// Also, make sure the styles are properly added
function addMultiSelectStyles() {
  // Check if styles are already added
  if (document.getElementById('enhanced-multi-select-styles')) return;
  
  const styleEl = document.createElement('style');
  styleEl.id = 'enhanced-multi-select-styles';
  styleEl.textContent = `
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
      
      /* This is critical - properly hide the original select */
      select[data-enhanced="true"],
      .enhanced-multi-select[data-enhanced="true"] {
          display: none !important;
          position: absolute !important;
          opacity: 0 !important;
          pointer-events: none !important;
          height: 0 !important;
          width: 0 !important;
          overflow: hidden !important;
      }
  `;
  document.head.appendChild(styleEl);
  console.log("Added enhanced multi-select styles");
}
  
    /**
     * Opens a slide panel with the specified options
     */
    function openSlidePanel(panelId, options = {}) {
      // Check if panel already exists
      let panel = document.getElementById(panelId);
      
      // Create panel if it doesn't exist
      if (!panel) {
        panel = document.createElement('div');
        panel.id = panelId;
        panel.className = 'slide-panel';
        
        // Create panel header
        const header = document.createElement('div');
        header.className = 'slide-panel-header';
        header.innerHTML = `
            <h4 class="mb-0">
                <i class="fas ${options.icon || 'fa-info-circle'} me-2" style="color: ${options.iconColor || '#15803d'}"></i>
                ${options.title || 'Panel'}
            </h4>
            <button type="button" class="btn-close btn-close-white" onclick="TransactionModule.closeSlidePanel('${panelId}')"></button>
        `;
        
        // Create panel content
        const content = document.createElement('div');
        content.className = 'slide-panel-content';
        
        // Add loading content if provided
        if (options.loadingContent) {
          content.innerHTML = options.loadingContent;
        } else if (options.content) {
          content.innerHTML = options.content;
        }
        
        // Assemble panel
        panel.appendChild(header);
        panel.appendChild(content);
        
        // Add to DOM
        document.body.appendChild(panel);
      }
      
      // Ensure overlay exists
      let overlay = document.getElementById('slide-panel-overlay');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'slide-panel-overlay';
        overlay.className = 'slide-panel-overlay';
        document.body.appendChild(overlay);
      }
      
      // Show overlay
      overlay.classList.add('active');
      overlay.onclick = function() {
        closeSlidePanel(panelId);
      };
      
      // Show panel with animation
      setTimeout(() => {
        panel.classList.add('active');
      }, 10);
      
      // Prevent body scrolling
      document.body.style.overflow = 'hidden';
      
      return panel;
    }
  
    /**
     * Closes a slide panel
     */
    function closeSlidePanel(panelId) {
      const panel = document.getElementById(panelId);
      if (panel) {
        panel.classList.remove('active');
      }
      
      // Hide overlay
      const overlay = document.getElementById('slide-panel-overlay');
      if (overlay) {
        overlay.classList.remove('active');
      }
      
      // Re-enable body scrolling
      document.body.style.overflow = '';
    }
  
    /**
     * Shows a message toast
     */
    function showMessage(message, type = 'success', options = {}) {
      // Default options
      const defaultOptions = {
        autoHide: true,
        delay: 5000,
        actionButtons: [],
        onClose: null
      };
      
      // Merge options
      const finalOptions = {...defaultOptions, ...options};
      
      // Check if we can use Bootstrap toast
      if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
          toastContainer = document.createElement('div');
          toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
          document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toastId = `toast-${Date.now()}`;
        const iconClass = type === 'error' ? 'fa-exclamation-circle' : 
                          type === 'warning' ? 'fa-exclamation-triangle' : 
                          type === 'info' ? 'fa-info-circle' : 'fa-check-circle';
        const bgColor = type === 'error' ? 'bg-danger' : 
                        type === 'warning' ? 'bg-warning text-dark' : 
                        type === 'info' ? 'bg-info text-dark' : 'bg-success';
        
        // Create action buttons HTML if provided
        let actionButtonsHtml = '';
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
          actionButtonsHtml = `
              <div class="mt-2 pt-2 border-top d-flex justify-content-end">
                  ${finalOptions.actionButtons.map(btn => 
                    `<button type="button" class="btn ${btn.class || 'btn-secondary'} btn-sm me-2 action-btn" 
                      data-action="${btn.text}">${btn.text}</button>`
                  ).join('')}
              </div>
          `;
        }
        
        // Create toast HTML
        const toastHtml = `
          <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" 
              ${finalOptions.autoHide ? `data-bs-delay="${finalOptions.delay}"` : 'data-bs-autohide="false"'}>
              <div class="toast-header ${bgColor} ${type !== 'warning' && type !== 'info' ? 'text-white' : ''}">
                  <i class="fas ${iconClass} me-2"></i>
                  <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                  <button type="button" class="btn-close ${type !== 'warning' && type !== 'info' ? 'btn-close-white' : ''}" 
                      data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
              <div class="toast-body">
                  ${message}
                  ${actionButtonsHtml}
              </div>
          </div>
        `;
        
        // Add toast to container
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Get toast element
        const toastEl = document.getElementById(toastId);
        
        // Add action button event listeners
        if (finalOptions.actionButtons && finalOptions.actionButtons.length > 0) {
          const actionBtns = toastEl.querySelectorAll('.action-btn');
          actionBtns.forEach(btn => {
            btn.addEventListener('click', function() {
              const actionText = this.getAttribute('data-action');
              const actionBtn = finalOptions.actionButtons.find(b => b.text === actionText);
              
              if (actionBtn && typeof actionBtn.onClick === 'function') {
                // Create toast instance reference to pass to handlers
                const bsToast = bootstrap.Toast.getInstance(toastEl);
                actionBtn.onClick(bsToast);
              }
            });
          });
        }
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Handle close event
        toastEl.addEventListener('hidden.bs.toast', function() {
          if (typeof finalOptions.onClose === 'function') {
            finalOptions.onClose();
          }
          // Remove toast from DOM
          toastEl.remove();
        });
        
        return toast;
      } else {
        // Fallback to alert
        alert(message);
        
        // Call onClose if provided
        if (typeof finalOptions.onClose === 'function') {
          finalOptions.onClose();
        }
        
        return null;
      }
    }
  
    /**
     * Opens the Add Transaction panel
     */
    function openAddTransactionPanel() {
      console.log("Opening Add Transaction Panel");
      
      // Create the slide panel first
      const panel = openSlidePanel('addTransactionPanel', {
        title: 'Add New Transaction',
        icon: 'fa-plus',
        iconColor: '#0ea5e9',
        loadingContent: '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>'
      });
      
      // Then fetch the form contents
      fetch('/get_transaction_form_html')
        .then(response => response.text())
        .then(html => {
          const contentDiv = panel.querySelector('.slide-panel-content');
          if (contentDiv) {
            contentDiv.innerHTML = html;
            
            // Initialize date with today's date
            const dateInput = document.getElementById('date');
            if (dateInput) {
              dateInput.value = new Date().toISOString().split('T')[0];
            }
            
            // Initialize enhanced multi-select for split_with
            enhanceMultiSelects('#split_with');
            
            // Setup form event handlers
            setupAddTransactionEventHandlers();
          }
        })
        .catch(error => {
          console.error('Error loading form:', error);
          showMessage('Error loading transaction form. Please try again.', 'error');
        });
    }
  
    /**
     * Set up event handlers for the add transaction form
     */
    function setupAddTransactionEventHandlers() {
      // Add transaction type change handler
      const transactionTypeSelect = document.getElementById('transaction_type');
      if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', function() {
          const expenseOnlyFields = document.querySelectorAll('.expense-only-fields');
          const toAccountContainer = document.getElementById('to_account_container');
          const accountLabel = document.getElementById('account_label');
          
          // Show/hide fields based on transaction type
          if (this.value === 'expense') {
            // Show splitting options for expenses
            expenseOnlyFields.forEach(el => el.style.display = 'block');
            if (toAccountContainer) toAccountContainer.style.display = 'none';
            
            // Update account label
            if (accountLabel) accountLabel.textContent = 'Payment Account';
          } 
          else if (this.value === 'income') {
            // Hide splitting options for income
            expenseOnlyFields.forEach(el => el.style.display = 'none');
            if (toAccountContainer) toAccountContainer.style.display = 'none';
            
            // Update account label
            if (accountLabel) accountLabel.textContent = 'Deposit Account';
          }
          else if (this.value === 'transfer') {
            // Hide splitting options for transfers
            expenseOnlyFields.forEach(el => el.style.display = 'none');
            
            // Show destination account
            if (toAccountContainer) toAccountContainer.style.display = 'block';
            
            // Update account label
            if (accountLabel) accountLabel.textContent = 'From Account';
          }
        });
        
        // Initialize UI based on default transaction type
        transactionTypeSelect.dispatchEvent(new Event('change'));
        setupFormSubmission();
      }
      
      // Personal expense toggle
      const personalExpenseCheck = document.getElementById('personal_expense');
      if (personalExpenseCheck) {
        personalExpenseCheck.addEventListener('change', function() {
          const splitWithSelect = document.getElementById('split_with');
          const splitMethodContainer = document.getElementById('split_method')?.parentNode;
          const customSplitContainer = document.getElementById('custom_split_container');
          
          if (this.checked) {
            // This is a personal expense - disable split options
            if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
            if (customSplitContainer) customSplitContainer.style.display = 'none';
            
            // Clear any existing split_with selections
            if (splitWithSelect) {
              for (let i = 0; i < splitWithSelect.options.length; i++) {
                splitWithSelect.options[i].selected = false;
              }
              splitWithSelect.disabled = true;
              
              // Handle enhanced multi-select if present
              const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
              if (multiSelectContainer) {
                multiSelectContainer.style.opacity = '0.5';
                multiSelectContainer.style.pointerEvents = 'none';
              } else {
                splitWithSelect.parentNode.style.opacity = '0.5';
              }
            }
          } else {
            // This is a shared expense - enable split options
            if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
            if (splitWithSelect) {
              splitWithSelect.disabled = false;
              


              // Handle enhanced multi-select if present
            const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
            if (multiSelectContainer) {
              multiSelectContainer.style.opacity = '1';
              multiSelectContainer.style.pointerEvents = 'auto';
            } else {
              splitWithSelect.parentNode.style.opacity = '1';
            }
            
            // Auto-select the paid_by user
            autoSelectPaidByUser();
          }
          
          // Show custom split container if needed
          const splitMethodSelect = document.getElementById('split_method');
          if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
            customSplitContainer.style.display = 'block';
          }
        }
        
        // Update split values if needed
        updateSplitValues();
      });
    }
    
    // Split method change handler
    const splitMethodSelect = document.getElementById('split_method');
    if (splitMethodSelect) {
      splitMethodSelect.addEventListener('change', function() {
        const customSplitContainer = document.getElementById('custom_split_container');
        const personalExpenseCheck = document.getElementById('personal_expense');
        
        if (!customSplitContainer) return;
        
        // Don't show custom split container for personal expenses
        if (personalExpenseCheck && personalExpenseCheck.checked) {
          customSplitContainer.style.display = 'none';
          return;
        }
        
        if (this.value === 'equal') {
          customSplitContainer.style.display = 'none';
        } else {
          customSplitContainer.style.display = 'block';
          
          // Update the split values UI
          updateSplitValues();
        }
      });
    }
    
    // Amount field change handler
    const amountField = document.getElementById('amount');
    if (amountField) {
      amountField.addEventListener('input', function() {
        // Only update split values if a split method is selected
        const splitMethod = document.getElementById('split_method')?.value;
        if (splitMethod && splitMethod !== 'equal') {
          updateSplitValues();
        }
      });
    }
    
    // Paid by change handler
    const paidBySelect = document.getElementById('paid_by');
    if (paidBySelect) {
      paidBySelect.addEventListener('change', function() {
        // Auto-select the paid by user
        autoSelectPaidByUser();
        
        // Only update split values if a split method is selected
        const splitMethod = document.getElementById('split_method')?.value;
        if (splitMethod && splitMethod !== 'equal') {
          updateSplitValues();
        }
      });
    }
    
    // Setup form submission
    const form = document.getElementById('newTransactionForm');
    if (form) {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitAddTransaction(this);
      });
    }
  }
  
  /**
   * Auto-select the paid by user in the split_with dropdown
   */
  function autoSelectPaidByUser() {
    const paidBySelect = document.getElementById('paid_by');
    const splitWithSelect = document.getElementById('split_with');
    
    if (!paidBySelect || !splitWithSelect) return;
    
    const paidById = paidBySelect.value;
    if (!paidById) return;
    
    // If there are no existing selections yet
    if (Array.from(splitWithSelect.selectedOptions).length === 0) {
      // Find the option for the paid by user and select it
      const option = splitWithSelect.querySelector(`option[value="${paidById}"]`);
      if (option) {
        option.selected = true;
        // Trigger change event to update the UI
        splitWithSelect.dispatchEvent(new Event('change'));
      }
    }
  }
  
  function updateSplitValues() {
    const splitMethodSelect = document.getElementById('split_method');
    if (!splitMethodSelect) return;
    
    const splitMethod = splitMethodSelect.value;
    if (splitMethod === 'equal') return;
    
    // Skip if personal expense is checked
    const personalExpenseCheck = document.getElementById('personal_expense');
    if (personalExpenseCheck && personalExpenseCheck.checked) return;
    
    const amountInput = document.getElementById('amount');
    const paidBySelect = document.getElementById('paid_by');
    const splitWithSelect = document.getElementById('split_with');
    const splitTotalEl = document.getElementById('split_total');
    const splitValuesContainer = document.getElementById('split_values_container');
    const splitDetailsInput = document.getElementById('split_details');
    
    if (!amountInput || !paidBySelect || !splitWithSelect || !splitTotalEl || !splitValuesContainer) return;
    
    const totalAmount = parseFloat(amountInput.value) || 0;
    const paidById = paidBySelect.value;
    
    // Get selected users to split with
    const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
    
    // If no participants, show a message
    if (splitWithIds.length === 0) {
      splitValuesContainer.innerHTML = '<p class="text-center text-warning">Please select people to split with</p>';
      return;
    }
    
    // Get all participant IDs (include payer only if they aren't already in the split list)
    const allParticipantIds = [...splitWithIds];
    if (!allParticipantIds.includes(paidById)) {
      allParticipantIds.unshift(paidById);
    }
    
    splitValuesContainer.innerHTML = '';
    let splitValues = {};
    
    // Try to load existing split details
    try {
      if (splitDetailsInput && splitDetailsInput.value) {
        const details = JSON.parse(splitDetailsInput.value);
        if (details && details.values) {
          splitValues = details.values;
          console.log("Loaded existing split values:", splitValues);
        }
      }
    } catch (e) {
      console.warn('Could not parse existing split details', e);
    }
    
    // Check if we have values for the current participants
    const existingParticipants = Object.keys(splitValues);
    const newParticipants = allParticipantIds.filter(id => !existingParticipants.includes(id));
    
    // If we have new participants or no existing values, initialize with defaults
    if (newParticipants.length > 0 || existingParticipants.length === 0) {
      if (splitMethod === 'percentage') {
        // Equal percentage for all participants
        const equalPercentage = allParticipantIds.length ? (100 / allParticipantIds.length) : 0;
        
        allParticipantIds.forEach(userId => {
          // Only set default values for new participants
          if (!splitValues[userId]) {
            splitValues[userId] = equalPercentage;
          }
        });
      } else { // Custom amount
        // Equal amounts
        const equalAmount = allParticipantIds.length ? (totalAmount / allParticipantIds.length) : 0;
        
        allParticipantIds.forEach(userId => {
          // Only set default values for new participants
          if (!splitValues[userId]) {
            splitValues[userId] = equalAmount;
          }
        });
      }
    }
    
    // Build the UI with the values
    if (splitMethod === 'percentage') {
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
            .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        // Use stored value or default to equal percentage
        const userPercentage = splitValues[userId] || (100 / allParticipantIds.length);
        
        // Create row for this user
        const row = document.createElement('div');
        row.className = 'row mb-2 align-items-center';
        row.innerHTML = `
            <div class="col-md-6">
                <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                    ${isPayerId ? '💰' : ''} ${userName}
                </span>
                ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
            </div>
            <div class="col-md-6">
                <div class="input-group">
                    <input type="number" class="form-control bg-dark text-light split-value-input"
                        data-user-id="${userId}" step="0.1" min="0" max="100" 
                        value="${userPercentage.toFixed(1)}">
                    <span class="input-group-text bg-dark text-light">%</span>
                </div>
            </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Ensure the value is in the splitValues object
        splitValues[userId] = userPercentage;
      });
    } else { // Custom amount
      allParticipantIds.forEach(userId => {
        const userName = Array.from(paidBySelect.options)
            .find(opt => opt.value === userId)?.text || userId;
        
        const isPayerId = userId === paidById;
        // Use stored value or default to equal amount
        const userAmount = splitValues[userId] || (totalAmount / allParticipantIds.length);
        
        // Create row for this user
        const row = document.createElement('div');
        row.className = 'row mb-2 align-items-center';
        row.innerHTML = `
            <div class="col-md-6">
                <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                    ${isPayerId ? '💰' : ''} ${userName}
                </span>
                ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
            </div>
            <div class="col-md-6">
                <div class="input-group">
                    <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                    <input type="number" class="form-control bg-dark text-light split-value-input"
                        data-user-id="${userId}" step="0.01" min="0" 
                        value="${userAmount.toFixed(2)}">
                </div>
            </div>
        `;
        splitValuesContainer.appendChild(row);
        
        // Ensure the value is in the splitValues object
        splitValues[userId] = userAmount;
      });
    }
    
    // Add event listeners to inputs and update split details
    setupSplitInputListeners(splitMethod, splitValues, totalAmount);
    
    // Ensure split details are updated initially
    updateSplitDetailsInput();
  }

  function setupSplitInputListeners(splitMethod, splitValues, totalAmount) {
    const splitDetailsInput = document.getElementById('split_details');
    const splitTotalEl = document.getElementById('split_total');
    const splitStatusEl = document.getElementById('split_status');
    
    // Initialize split details right away
    if (splitDetailsInput) {
      splitDetailsInput.value = JSON.stringify({
        type: splitMethod,
        values: splitValues
      });
      console.log("Initial split details set:", splitDetailsInput.value);
    }
    
    document.querySelectorAll('.split-value-input').forEach(input => {
      input.addEventListener('input', function() {
        const userId = this.getAttribute('data-user-id');
        const value = parseFloat(this.value) || 0;
        splitValues[userId] = value;
        
        // Calculate total
        const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
        
        // Update UI
        if (splitTotalEl) {
          if (splitMethod === 'percentage') {
            splitTotalEl.textContent = total.toFixed(1) + '%';
            
            // Update status
            if (splitStatusEl) {
              if (Math.abs(total - 100) < 0.1) {
                splitStatusEl.textContent = 'Balanced';
                splitStatusEl.className = 'badge bg-success';
              } else if (total < 100) {
                splitStatusEl.textContent = 'Underfunded';
                splitStatusEl.className = 'badge bg-warning';
              } else {
                splitStatusEl.textContent = 'Overfunded';
                splitStatusEl.className = 'badge bg-danger';
              }
            }
          } else { // Custom amount
            splitTotalEl.textContent = total.toFixed(2);
            
            // Update status
            if (splitStatusEl) {
              if (Math.abs(total - totalAmount) < 0.01) {
                splitStatusEl.textContent = 'Balanced';
                splitStatusEl.className = 'badge bg-success';
              } else if (total < totalAmount) {
                splitStatusEl.textContent = 'Underfunded';
                splitStatusEl.className = 'badge bg-warning';
              } else {
                splitStatusEl.textContent = 'Overfunded';
                splitStatusEl.className = 'badge bg-danger';
              }
            }
          }
        }
        
        // Update hidden split details field - CRITICAL PART
        updateSplitDetailsInput();
      });
      
      // Trigger input event to initialize values
      input.dispatchEvent(new Event('input'));
    });
  }

  function updateSplitDetailsInput() {
    const splitMethodSelect = document.getElementById('split_method');
    const splitDetailsInput = document.getElementById('split_details');
    const splitInputs = document.querySelectorAll('.split-value-input');
    
    if (!splitMethodSelect || !splitDetailsInput || splitInputs.length === 0) {
      console.warn("Missing elements for updating split details");
      return;
    }
    
    const splitMethod = splitMethodSelect.value;
    const splitValues = {};
    
    splitInputs.forEach(input => {
      const userId = input.getAttribute('data-user-id');
      const value = parseFloat(input.value) || 0;
      splitValues[userId] = value;
    });
    
    const splitDetails = {
      type: splitMethod,
      values: splitValues
    };
    
    // Set the hidden input with stringified split details
    splitDetailsInput.value = JSON.stringify(splitDetails);
    
    console.log('Updated Split Details:', splitDetails);
  }
  function setupFormSubmission() {
    const form = document.getElementById('newTransactionForm');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
      // If this is a custom split, validate split details exist
      const splitMethod = document.getElementById('split_method')?.value;
      const personalExpense = document.getElementById('personal_expense')?.checked;
      
      if (!personalExpense && splitMethod && splitMethod !== 'equal') {
        // Force update split details one last time
        updateSplitDetailsInput();
        
        // Verify we have split details
        const splitDetailsInput = document.getElementById('split_details');
        if (!splitDetailsInput || !splitDetailsInput.value) {
          console.error("No split details for custom split");
          e.preventDefault();
          alert("Error with split details. Please try again.");
          return false;
        }
        
        console.log("Submitting form with split details:", splitDetailsInput.value);
      }
    });
  } 


  
  /**
   * Opens the Edit Transaction panel
   */
  function openEditTransactionPanel(expenseId) {
    // Show a loading panel first
    const panel = openSlidePanel('editTransactionPanel', {
      title: 'Edit Transaction',
      icon: 'fa-edit',
      iconColor: '#0ea5e9',
      loadingContent: '<div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>'
    });
    
    // Fetch expense data
    fetch(`/get_expense_edit_form/${expenseId}`)
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to retrieve expense data');
        }
        return response.text();
      })
      .then(html => {
        const contentDiv = panel.querySelector('.slide-panel-content');
        if (contentDiv) {
          contentDiv.innerHTML = html;
          
          // Call function to enhance the edit form with a short delay to ensure DOM is ready
          setTimeout(() => enhanceEditTransactionForm(), 50);
          
          // Setup form submission
          const editForm = document.getElementById('editTransactionForm');
          if (editForm) {
            editForm.addEventListener('submit', function(e) {
              e.preventDefault();
              submitEditForm(this, expenseId);
            });
          }
        }
      })
      .catch(error => {
        console.error('Error:', error);
        showMessage(`Error loading expense data: ${error.message}`, 'error');
        closeSlidePanel('editTransactionPanel');
      });
  }
  
  /**
   * Enhance the edit transaction form with additional functionality
   */
  function enhanceEditTransactionForm() {
    console.log("Enhancing edit transaction form...");
    
    try {
      // Initialize multi-select for split_with
      enhanceMultiSelects('#edit_split_with');
      
      // Initialize transaction type handler
      setupEditTransactionTypeHandler();
      
      // Set up personal expense toggle
      setupEditPersonalExpenseToggle();
      
      // Set up split method toggle
      setupEditSplitMethodToggle();
      
      // Fix category splits functionality first
      fixCategorySplits();
      
      // Then ensure they display correctly (after a short delay to let the DOM settle)
      setTimeout(ensureCategorySplitsDisplay, 100);
      
      console.log("Edit transaction form enhancement complete");
    } catch (error) {
      console.error("Error enhancing edit transaction form:", error);
    }
  }
  
  /**
   * Set up transaction type change handler for edit form
   */
  function setupEditTransactionTypeHandler() {
    const transactionTypeSelect = document.getElementById('edit_transaction_type');
    if (!transactionTypeSelect) return;
    
    transactionTypeSelect.addEventListener('change', function() {
      const transactionType = this.value;
      const expenseOnlyFields = document.querySelector('.edit-expense-only-fields');
      const toAccountContainer = document.getElementById('edit_to_account_container');
      const accountLabel = document.getElementById('edit_account_label');
      
      // Show/hide fields based on transaction type
      if (transactionType === 'expense') {
        // Show splitting options for expenses
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'block';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Payment Account';
        
        // Make sure the destination account is cleared
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        if (destinationAccountSelect) {
          destinationAccountSelect.value = '';
        }
      } 
      else if (transactionType === 'income') {
        // Hide splitting options for income
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'none';
        if (toAccountContainer) toAccountContainer.style.display = 'none';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'Deposit Account';
        
        // Make sure the destination account is cleared
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        if (destinationAccountSelect) {
          destinationAccountSelect.value = '';
        }
      }
      else if (transactionType === 'transfer') {
        // Hide splitting options for transfers
        if (expenseOnlyFields) expenseOnlyFields.style.display = 'none';
        
        // Show destination account
        if (toAccountContainer) toAccountContainer.style.display = 'block';
        
        // Update account label
        if (accountLabel) accountLabel.textContent = 'From Account';
        
        // Update destination account options
        updateEditDestinationAccountOptions();
      }
    });
    
    // Initialize UI based on current selection
    transactionTypeSelect.dispatchEvent(new Event('change'));
  }
  
  /**
   * Update destination account options for transfers in edit form
   */
  function updateEditDestinationAccountOptions() {
    const sourceAccountSelect = document.getElementById('edit_account_id');
    const destinationAccountSelect = document.getElementById('edit_destination_account_id');
    
    if (!sourceAccountSelect || !destinationAccountSelect) return;
    
    const sourceAccountId = sourceAccountSelect.value;
    
    // Enable all options first
    for (let i = 0; i < destinationAccountSelect.options.length; i++) {
      destinationAccountSelect.options[i].disabled = false;
    }
    
    // If a source account is selected, disable it in the destination select
    if (sourceAccountId) {
      for (let i = 0; i < destinationAccountSelect.options.length; i++) {
        if (destinationAccountSelect.options[i].value === sourceAccountId) {
          destinationAccountSelect.options[i].disabled = true;
          
          // If this was the selected destination, clear the selection
          if (destinationAccountSelect.options[i].selected) {
            destinationAccountSelect.value = '';
          }
          
          break;
        }
      }
    }
  }
  
  /**
   * Set up personal expense toggle for edit form
   */
  function setupEditPersonalExpenseToggle() {
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    if (!personalExpenseCheck) return;
    
    personalExpenseCheck.addEventListener('change', function() {
      const splitWithSelect = document.getElementById('edit_split_with');
      const splitMethodContainer = document.getElementById('edit_split_method')?.parentNode;
      const customSplitContainer = document.getElementById('edit_custom_split_container');
      
      if (personalExpenseCheck.checked) {
        // This is a personal expense - disable split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '0.5';
        if (customSplitContainer) customSplitContainer.style.display = 'none';
        
        // Clear any existing split_with selections
        if (splitWithSelect) {
          for (let i = 0; i < splitWithSelect.options.length; i++) {
            splitWithSelect.options[i].selected = false;
          }
          splitWithSelect.disabled = true;
          
          // Handle enhanced multi-select if present
          const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
          if (multiSelectContainer) {
            multiSelectContainer.style.opacity = '0.5';
            multiSelectContainer.style.pointerEvents = 'none';
          } else {
            splitWithSelect.parentNode.style.opacity = '0.5';
          }
        }
      } else {
        // This is a shared expense - enable split options
        if (splitMethodContainer) splitMethodContainer.style.opacity = '1';
        if (splitWithSelect) {
          splitWithSelect.disabled = false;
          
          // Handle enhanced multi-select if present
          const multiSelectContainer = splitWithSelect.closest('.custom-multi-select-container');
          if (multiSelectContainer) {
            multiSelectContainer.style.opacity = '1';
            multiSelectContainer.style.pointerEvents = 'auto';
          } else {
            splitWithSelect.parentNode.style.opacity = '1';
          }
        }
        
        // Show custom split container if needed
        const splitMethodSelect = document.getElementById('edit_split_method');
        if (splitMethodSelect && splitMethodSelect.value !== 'equal' && customSplitContainer) {
          customSplitContainer.style.display = 'block';
        }
      }
      
      // Update split values if needed
      updateEditSplitValues();
    });
    
    // Initialize UI based on current checked state
    personalExpenseCheck.dispatchEvent(new Event('change'));
  }
  /**
   * Set up split method toggle for edit form
   */
  function setupEditSplitMethodToggle() {
    const splitMethodSelect = document.getElementById('edit_split_method');
    if (!splitMethodSelect) return;
    
    splitMethodSelect.addEventListener('change', function() {
      const splitMethod = splitMethodSelect.value;
      const customSplitContainer = document.getElementById('edit_custom_split_container');
      const personalExpenseCheck = document.getElementById('edit_personal_expense');
      
      if (!customSplitContainer) return;
      
      // Don't show custom split container for personal expenses
      if (personalExpenseCheck && personalExpenseCheck.checked) {
        customSplitContainer.style.display = 'none';
        return;
      }
      
      if (splitMethod === 'equal') {
        customSplitContainer.style.display = 'none';
      } else {
        customSplitContainer.style.display = 'block';
        
        // Update the split values UI
        updateEditSplitValues();
      }
    });
    
    // Initialize UI based on current selection
    splitMethodSelect.dispatchEvent(new Event('change'));
  }
  
  /**
   * Fix category splits functionality
   */
  function fixCategorySplits() {
    console.log("Fixing category splits functionality...");
    
    // Find the enable category split checkbox
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    const categorySplitsData = document.getElementById('category_splits_data');
    
    if (!enableCategorySplitCheck || !categorySplitsContainer) {
      console.warn("Category split elements not found, cannot fix splits");
      return;
    }
    
    // Check if we have pre-existing split data
    if (categorySplitsData && categorySplitsData.value) {
      try {
        const splitData = JSON.parse(categorySplitsData.value);
        
        if (Array.isArray(splitData) && splitData.length > 0) {
          console.log("Found existing split data:", splitData);
          
          // Enable category splits
          enableCategorySplitCheck.checked = true;
          
          // Show the container immediately
          categorySplitsContainer.style.display = 'block';
          
          // Add visible class if using transition effects
          categorySplitsContainer.classList.add('visible');
          categorySplitsContainer.classList.remove('hidden');
          
          // Disable main category select
          const categorySelect = document.getElementById('edit_category_id');
          if (categorySelect) {
            categorySelect.disabled = true;
            categorySelect.parentElement.classList.add('opacity-50');
          }
          
          // Clear existing splits
          const splitsList = document.getElementById('category_splits_list');
          if (splitsList) {
            splitsList.innerHTML = '';
            
            // Create a split row for each item in the data
            splitData.forEach(split => {
              addCategorySplit(split.category_id, split.amount);
            });
            
            // Update totals
            updateSplitTotals();
          }
        }
      } catch (e) {
        console.error("Error parsing split data:", e);
      }
    }
    
    // Add a specific, direct click handler (not using addEventListener to avoid duplicates)
    enableCategorySplitCheck.onclick = function() {
      const isChecked = this.checked;
      console.log("Category split toggle clicked, checked =", isChecked);
      
      // Show/hide splits container - first set display style
      if (categorySplitsContainer) {
        categorySplitsContainer.style.display = isChecked ? 'block' : 'none';
        
        // Then handle CSS transitions if applicable
        if (isChecked) {
          categorySplitsContainer.classList.add('visible');
          categorySplitsContainer.classList.remove('hidden');
        } else {
          categorySplitsContainer.classList.add('hidden');
          categorySplitsContainer.classList.remove('visible');
        }
      }
      
      // Disable/enable main category field
      const categorySelect = document.getElementById('edit_category_id');
      if (categorySelect) {
        categorySelect.disabled = isChecked;
        categorySelect.parentElement.classList.toggle('opacity-50', isChecked);
      }
      
      if (isChecked) {
        // Clear existing splits first
        const categorySpitsList = document.getElementById('category_splits_list');
        if (categorySpitsList) {
          categorySpitsList.innerHTML = '';
        }
        
        // Add a new split with the full amount
        const amountInput = document.getElementById('edit_amount');
        const totalAmount = parseFloat(amountInput?.value) || 0;
        addCategorySplit(null, totalAmount);
        updateSplitTotals();
      } else {
        // Clear split data
        if (categorySplitsData) {
          categorySplitsData.value = '';
        }
      }
    };
    
    // Make sure the "Add Split" button works correctly
    const addSplitBtn = document.getElementById('add_split_btn');
    if (addSplitBtn) {
      // Remove any existing handlers to prevent duplicates
      const newBtn = addSplitBtn.cloneNode(true);
      addSplitBtn.parentNode.replaceChild(newBtn, addSplitBtn);
      
      newBtn.addEventListener('click', function() {
        console.log("Add split button clicked");
        addCategorySplit(null, 0);
        updateSplitTotals();
      });
    }
  
    console.log("Category splits functionality fixed");
  }
  
  // Helper function to ensure splits are properly displayed
  function ensureCategorySplitsDisplay() {
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    const categorySplitsContainer = document.getElementById('category_splits_container');
    
    if (enableCategorySplitCheck && categorySplitsContainer) {
      if (enableCategorySplitCheck.checked) {
        console.log("Ensuring category splits are displayed");
        categorySplitsContainer.style.display = 'block';
        categorySplitsContainer.classList.add('visible');
        categorySplitsContainer.classList.remove('hidden');
      }
    }
  }
  /**
   * Add a category split row with optional category and amount
   */
  function addCategorySplit(categoryId, amount) {
    const splitsList = document.getElementById('category_splits_list');
    if (!splitsList) return;
    
    const splitId = Date.now(); // Unique ID for this split
    
    const splitRow = document.createElement('div');
    splitRow.className = 'row mb-3 split-row';
    splitRow.dataset.splitId = splitId;
    
    // Create the split HTML with category dropdown and amount input
    splitRow.innerHTML = `
        <div class="col-md-5">
            <select class="form-select bg-dark text-light split-category" data-split-id="${splitId}">
                <option value="">Select category</option>
                ${document.getElementById('edit_category_id')?.innerHTML || ''}
            </select>
        </div>
        <div class="col-md-5">
            <div class="input-group">
                <span class="input-group-text bg-dark text-light">${baseCurrencySymbol || '$'}</span>
                <input type="number" step="0.01" class="form-control bg-dark text-light split-amount" 
                       data-split-id="${splitId}" value="${amount.toFixed(2)}">
            </div>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-outline-danger remove-split" data-split-id="${splitId}">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    splitsList.appendChild(splitRow);
    
    // Apply high contrast styling
    const inputs = splitRow.querySelectorAll('input, select');
    inputs.forEach(input => {
      input.classList.add('text-high-contrast');
      input.style.color = '#ffffff';
    });
    
    // Add event listeners to the new elements
    const amountInput = splitRow.querySelector('.split-amount');
    if (amountInput) {
      amountInput.addEventListener('input', updateSplitTotals);
    }
    
    const categorySelect = splitRow.querySelector('.split-category');
    if (categorySelect) {
      categorySelect.addEventListener('change', updateSplitTotals);
      
      // Set the category if provided
      if (categoryId) {
        categorySelect.value = categoryId;
      }
    }
    
    const removeButton = splitRow.querySelector('.remove-split');
    if (removeButton) {
      removeButton.addEventListener('click', function() {
        splitRow.remove();
        updateSplitTotals();
      });
    }
    
    return splitRow;
  }
  
  /**
   * Update split totals and validate
   */
  function updateSplitTotals() {
    const transactionTotal = parseFloat(document.getElementById('edit_amount')?.value) || 0;
    let splitTotal = 0;
    let allCategoriesSelected = true;
    
    // Calculate sum of all splits
    const splitRows = document.querySelectorAll('.split-row');
    
    // Don't validate if there are no splits
    if (splitRows.length === 0) {
      return;
    }
    
    splitRows.forEach(row => {
      // Get the amount
      const amountInput = row.querySelector('.split-amount');
      splitTotal += parseFloat(amountInput?.value) || 0;
      
      // Check if category is selected
      const categorySelect = row.querySelector('.split-category');
      if (!categorySelect?.value) {
        allCategoriesSelected = false;
      }
    });
    
    // Update UI
    const splitTotalEl = document.getElementById('split_total');
    const transactionTotalEl = document.getElementById('transaction_total');
    
    if (splitTotalEl) splitTotalEl.textContent = splitTotal.toFixed(2);
    if (transactionTotalEl) transactionTotalEl.textContent = transactionTotal.toFixed(2);
    
    // Validate total
    // Validate total
    const statusEl = document.getElementById('split_status');
    if (statusEl) {
      if (Math.abs(splitTotal - transactionTotal) < 0.01) {
        statusEl.textContent = allCategoriesSelected ? 'Balanced' : 'Select Categories';
        statusEl.className = allCategoriesSelected ? 'badge bg-success' : 'badge bg-warning';
      } else if (splitTotal < transactionTotal) {
        statusEl.textContent = 'Underfunded';
        statusEl.className = 'badge bg-warning';
      } else {
        statusEl.textContent = 'Overfunded';
        statusEl.className = 'badge bg-danger';
      }
    }
    
    // Update hidden input with split data
    const splitData = [];
    splitRows.forEach(row => {
      const categorySelect = row.querySelector('.split-category');
      const amountInput = row.querySelector('.split-amount');
      
      if (categorySelect && amountInput) {
        const categoryId = categorySelect.value;
        const amount = parseFloat(amountInput.value) || 0;
        
        if (categoryId && amount > 0) {
          splitData.push({
            category_id: categoryId,
            amount: amount
          });
        }
      }
    });
    
    const categorySplitsDataEl = document.getElementById('category_splits_data');
    if (categorySplitsDataEl) {
      categorySplitsDataEl.value = JSON.stringify(splitData);
    }
  }
  
  /**
   * Update split values UI for edit form
   */
  /**
 * Update split values UI for edit form
 * FIXED: Custom amount split now properly allows custom values
 */
function updateEditSplitValues() {
  const splitMethodSelect = document.getElementById('edit_split_method');
  if (!splitMethodSelect) return;
  
  const splitMethod = splitMethodSelect.value;
  if (splitMethod === 'equal') return;
  
  // Skip if personal expense is checked
  const personalExpenseCheck = document.getElementById('edit_personal_expense');
  if (personalExpenseCheck && personalExpenseCheck.checked) return;
  
  const amountInput = document.getElementById('edit_amount');
  const paidBySelect = document.getElementById('edit_paid_by');
  const splitWithSelect = document.getElementById('edit_split_with');
  const splitTotalEl = document.getElementById('edit_split_total');
  const splitValuesContainer = document.getElementById('edit_split_values_container');
  const splitDetailsInput = document.getElementById('edit_split_details');
  
  if (!amountInput || !paidBySelect || !splitWithSelect || !splitTotalEl || !splitValuesContainer) return;
  
  const totalAmount = parseFloat(amountInput.value) || 0;
  const paidById = paidBySelect.value;
  
  // Get selected users to split with
  const splitWithIds = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
  
  // If no participants, show a message
  if (splitWithIds.length === 0) {
      splitValuesContainer.innerHTML = '<p class="text-center text-warning">Please select people to split with</p>';
      return;
  }
  
  // Get all participant IDs (include payer only if they aren't already in the split list)
  const allParticipantIds = [...splitWithIds];
  if (!allParticipantIds.includes(paidById)) {
      allParticipantIds.unshift(paidById);
  }
  
  splitValuesContainer.innerHTML = '';
  let splitValues = {};
  
  // Try to load existing split details
  try {
      if (splitDetailsInput && splitDetailsInput.value) {
          const details = JSON.parse(splitDetailsInput.value);
          if (details && details.values) {
              splitValues = details.values;
              console.log("Loaded existing split values:", splitValues);
          }
      }
  } catch (e) {
      console.warn('Could not parse existing split details', e);
  }
  
  // Now build the UI with the values
  if (splitMethod === 'percentage') {
      allParticipantIds.forEach(userId => {
          const userName = Array.from(paidBySelect.options)
              .find(opt => opt.value === userId)?.text || userId;
          
          const isPayerId = userId === paidById;
          
          // Determine default percentage:
          // 1. Use existing value if available
          // 2. Otherwise use equal percentage as default
          
          let userPercentage;
          
          if (splitValues[userId] !== undefined) {
              userPercentage = splitValues[userId];
          } else {
              // Equal percentage as fallback
              userPercentage = allParticipantIds.length ? (100 / allParticipantIds.length) : 0;
              // Save to split values
              splitValues[userId] = userPercentage;
          }
          
          // Create row for this user
          const row = document.createElement('div');
          row.className = 'row mb-2 align-items-center';
          row.innerHTML = `
              <div class="col-md-6">
                  <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                      ${isPayerId ? '💰' : ''} ${userName}
                  </span>
                  ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
              </div>
              <div class="col-md-6">
                  <div class="input-group">
                      <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                          data-user-id="${userId}" step="0.1" min="0" max="100" 
                          value="${userPercentage.toFixed(1)}">
                      <span class="input-group-text bg-dark text-light">%</span>
                  </div>
              </div>
          `;
          splitValuesContainer.appendChild(row);
      });
  } else { // Custom amount
      allParticipantIds.forEach(userId => {
          const userName = Array.from(paidBySelect.options)
              .find(opt => opt.value === userId)?.text || userId;
          
          const isPayerId = userId === paidById;
          
          // Determine default amount:
          // 1. Use existing value if available
          // 2. If this is the payer, default to 0 (they're paying for others)
          // 3. Otherwise, calculate a fair share among non-payers
          
          let userAmount;
          
          if (splitValues[userId] !== undefined) {
              userAmount = splitValues[userId];
          } else if (isPayerId) {
              // Default payer amount to 0 (they're paying for others)
              userAmount = 0;
              // Save to split values
              splitValues[userId] = userAmount;
          } else {
              // For non-payers, split the total amount among them
              const nonPayerIds = allParticipantIds.filter(id => id !== paidById);
              userAmount = nonPayerIds.length ? (totalAmount / nonPayerIds.length) : 0;
              // Save to split values
              splitValues[userId] = userAmount;
          }
          
          // Create row for this user
          const row = document.createElement('div');
          row.className = 'row mb-2 align-items-center';
          row.innerHTML = `
              <div class="col-md-6">
                  <span class="badge ${isPayerId ? 'bg-primary' : 'bg-secondary'} me-1">
                      ${isPayerId ? '💰' : ''} ${userName}
                  </span>
                  ${isPayerId ? '<small class="text-muted">(Paid)</small>' : ''}
              </div>
              <div class="col-md-6">
                  <div class="input-group">
                      <span class="input-group-text bg-dark text-light">${baseCurrencySymbol}</span>
                      <input type="number" class="form-control bg-dark text-light edit-split-value-input"
                          data-user-id="${userId}" step="0.01" min="0" 
                          value="${userAmount.toFixed(2)}">
                  </div>
              </div>
          `;
          splitValuesContainer.appendChild(row);
      });
  }
  
  // Add event listeners to inputs and update split details
  setupEditSplitInputListeners(splitMethod, splitValues, totalAmount);
}
  
  /**
   * Setup input listeners for split values in edit form
   */
  function setupEditSplitInputListeners(splitMethod, splitValues, totalAmount) {
    const splitDetailsInput = document.getElementById('edit_split_details');
    const splitTotalEl = document.getElementById('edit_split_total');
    const splitStatusEl = document.getElementById('edit_split_status');
    
    document.querySelectorAll('.edit-split-value-input').forEach(input => {
        input.addEventListener('input', function() {
            const userId = this.getAttribute('data-user-id');
            const value = parseFloat(this.value) || 0;
            
            // Update the value for this user
            splitValues[userId] = value;
            
            // Calculate total
            const total = Object.values(splitValues).reduce((sum, val) => sum + val, 0);
            
            // Update UI
            if (splitTotalEl) {
                if (splitMethod === 'percentage') {
                    splitTotalEl.textContent = total.toFixed(1) + '%';
                    
                    // Update status
                    if (splitStatusEl) {
                        if (Math.abs(total - 100) < 0.1) {
                            splitStatusEl.textContent = 'Balanced';
                            splitStatusEl.className = 'badge bg-success';
                        } else if (total < 100) {
                            splitStatusEl.textContent = 'Underfunded';
                            splitStatusEl.className = 'badge bg-warning';
                        } else {
                            splitStatusEl.textContent = 'Overfunded';
                            splitStatusEl.className = 'badge bg-danger';
                        }
                    }
                } else { // Custom amount
                    splitTotalEl.textContent = total.toFixed(2);
                    
                    // Update status
                    if (splitStatusEl) {
                        if (Math.abs(total - totalAmount) < 0.01) {
                            splitStatusEl.textContent = 'Balanced';
                            splitStatusEl.className = 'badge bg-success';
                        } else if (total < totalAmount) {
                            splitStatusEl.textContent = 'Underfunded';
                            splitStatusEl.className = 'badge bg-warning';
                        } else {
                            splitStatusEl.textContent = 'Overfunded';
                            splitStatusEl.className = 'badge bg-danger';
                        }
                    }
                }
            }
            
            // Update hidden split details field with proper structure
            if (splitDetailsInput) {
                const detailsObj = {
                    type: splitMethod,
                    values: splitValues
                };
                splitDetailsInput.value = JSON.stringify(detailsObj);
                console.log("Updated split details:", detailsObj);
            }
        });
        
        // Trigger input event to initialize values
        input.dispatchEvent(new Event('input'));
    });
}

 /**
 * Submit the add transaction form
 */
function submitAddTransaction(form) {
  // Show loading state
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding...';
  }
  
  // Create FormData from the form
  const formData = new FormData(form);
  
  // Make AJAX request
  fetch(form.action, {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to add transaction');
    }
    return response.text();
  })
  .then(() => {
    // Success - close panel and reload
    closeSlidePanel('addTransactionPanel');
    showMessage('Transaction added successfully');
    
    // Reload the page to show the new transaction
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  })
  .catch(error => {
    console.error('Error:', error);
    showMessage(`Error adding transaction: ${error.message}`, 'error');
    
    // Reset button state
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Add Transaction';
    }
  });
}

// Enhanced submit function with additional data validation
function submitEditForm(form, expenseId) {
    // First, validate the split data if present
    const splitMethodSelect = document.getElementById('edit_split_method');
    const splitWithSelect = document.getElementById('edit_split_with');
    const splitDetailsInput = document.getElementById('edit_split_details');
    const personalExpenseCheck = document.getElementById('edit_personal_expense');
    
    let hasValidSplitData = true;
    
    // Only validate if this is a shared expense (not personal)
    if (splitMethodSelect && splitWithSelect && splitDetailsInput && 
        personalExpenseCheck && !personalExpenseCheck.checked) {
        
        const splitMethod = splitMethodSelect.value;
        const splitWithUsers = Array.from(splitWithSelect.selectedOptions).map(opt => opt.value);
        
        // Parse split details
        try {
            const splitDetails = JSON.parse(splitDetailsInput.value);
            
            // Make sure the values property exists and has data
            if (!splitDetails.values || Object.keys(splitDetails.values).length === 0) {
                console.error("Split details missing values property or it's empty");
                hasValidSplitData = false;
            }
            
            // Ensure the split method matches
            if (splitDetails.type !== splitMethod) {
                console.log("Correcting split method mismatch in details");
                splitDetails.type = splitMethod;
                splitDetailsInput.value = JSON.stringify(splitDetails);
            }
            
            // Make sure all selected users are in the values
            const missingUsers = splitWithUsers.filter(userId => !(userId in splitDetails.values));
            if (missingUsers.length > 0) {
                console.warn("Some users missing from split values:", missingUsers);
                
                // Add missing users with default values
                missingUsers.forEach(userId => {
                    splitDetails.values[userId] = splitMethod === 'percentage' ? 
                        (100 / splitWithUsers.length) : 
                        (parseFloat(document.getElementById('edit_amount')?.value || 0) / splitWithUsers.length);
                });
                
                // Update the input
                splitDetailsInput.value = JSON.stringify(splitDetails);
            }
            
        } catch (e) {
            console.error("Error validating split details:", e);
            hasValidSplitData = false;
        }
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    }
    
    // If split data validation failed, warn the user
    if (!hasValidSplitData) {
        // Show warning but proceed with submission
        console.warn("Split data validation failed, but proceeding with form submission");
        // You can choose to show a message to the user here if you want
    }
    
    // Create FormData from the form
    const formData = new FormData(form);
    
    // Handle destination_account_id for transfers
    const transactionTypeSelect = document.getElementById('edit_transaction_type');
    if (transactionTypeSelect && transactionTypeSelect.value === 'transfer') {
        const destinationAccountSelect = document.getElementById('edit_destination_account_id');
        // If destination account is empty or not selected, make it null instead of empty string
        if (!destinationAccountSelect || !destinationAccountSelect.value) {
            formData.delete('destination_account_id');
            formData.append('destination_account_id', 'null');
        }
    }
    
    // Explicitly add the category_id from the select element
    const categorySelect = document.getElementById('edit_category_id');
    if (categorySelect) {
        // Remove any existing category_id entries to avoid duplicates
        formData.delete('category_id');
        
        // Add the selected category_id, ensuring it's never sent as an empty string
        const categoryId = categorySelect.value || null;
        formData.append('category_id', categoryId);
    }
    
    // Handle category splits
    const enableCategorySplitCheck = document.getElementById('enable_category_split');
    if (enableCategorySplitCheck) {
        // Ensure enable_category_split is included properly
        formData.delete('enable_category_split');
        if (enableCategorySplitCheck.checked) {
            formData.append('enable_category_split', 'on');
            
            // Make sure category_splits_data is included
            const categorySplitsData = document.getElementById('category_splits_data');
            if (categorySplitsData) {
                formData.delete('category_splits_data');
                formData.append('category_splits_data', categorySplitsData.value);
            }
        }
    }
    
    // Add proper handling for transaction type
    if (transactionTypeSelect) {
        formData.delete('transaction_type');
        formData.append('transaction_type', transactionTypeSelect.value);
    }
    
    // Log the form data for debugging
    console.log("Submitting form data:");
    for (const [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
    }
    
    // Send AJAX request
    fetch(`/update_expense/${expenseId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to update transaction: ${response.status} ${response.statusText}`);
        }
        return response.text();
    })
    .then(() => {
        // Success - close panel and reload
        closeSlidePanel('editTransactionPanel');
        showMessage('Transaction updated successfully');
        window.location.reload();
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage(`Error updating transaction: ${error.message}`, 'error');
        
        // Reset button state
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Save Changes';
        }
    });
}
  // Return public API
  return init();
})();
 

// Enable global access
window.TransactionModule = TransactionModule;



