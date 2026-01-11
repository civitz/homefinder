// Function to create and load iframe dynamically
function loadOriginalListingIframe(propertyUrl) {
    // Get the iframe container and card
    const container = document.getElementById('iframe-container');
    const card = document.getElementById('iframe-card');
    
    // Clear any existing content
    container.innerHTML = '';
    
    // Create iframe element
    const iframe = document.createElement('iframe');
    iframe.src = propertyUrl;
    iframe.width = '100%';
    iframe.height = '600px';
    iframe.style.border = 'none';
    iframe.style.borderRadius = '5px';
    
    // Set sandbox attributes for security
    iframe.sandbox = 'allow-same-origin allow-scripts allow-forms';
    
    // Add error handling
    iframe.onerror = function() {
        container.innerHTML = '';
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.innerHTML = 'Failed to load the original listing. Please use the "View Original Listing" button to open it in a new tab.';
        container.appendChild(errorDiv);
        container.style.display = 'block';
    };
    
    // Add iframe to container
    container.appendChild(iframe);
    
    // Show the card and container
    card.style.display = 'block';
    container.style.display = 'block';
}

// Function to save property as example
function saveAsExample(propertyId) {
    const button = document.getElementById('saveExampleBtn');
    const originalText = button.innerHTML;
    
    // Disable button and show loading state
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    // Call the API endpoint
    fetch(`/properties/${propertyId}/save_as_example`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success message
            button.innerHTML = '✓ Saved Successfully';
            button.className = 'btn btn-success';
            
            // Reset button after 3 seconds
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
        } else {
            // Show error message
            button.innerHTML = '✗ Save Failed';
            button.className = 'btn btn-danger';
            
            // Reset button after 3 seconds
            setTimeout(() => {
                button.innerHTML = originalText;
                button.className = 'btn btn-success';
                button.disabled = false;
            }, 3000);
        }
    })
    .catch(error => {
        console.error('Error saving as example:', error);
        
        // Show error message
        button.innerHTML = '✗ Error';
        button.className = 'btn btn-danger';
        
        // Reset button after 3 seconds
        setTimeout(() => {
            button.innerHTML = originalText;
            button.className = 'btn btn-success';
            button.disabled = false;
        }, 3000);
    });
}