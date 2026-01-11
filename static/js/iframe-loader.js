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

// Edit mode functionality
let isEditMode = false;

function toggleEditMode() {
    isEditMode = !isEditMode;
    
    if (isEditMode) {
        // Show edit UI
        document.getElementById('readOnlyView').style.display = 'none';
        document.getElementById('readOnlyFeatures').style.display = 'none';
        document.getElementById('readOnlyDescription').style.display = 'none';
        document.getElementById('readOnlyFeaturesList').style.display = 'none';
        
        document.getElementById('editView').style.display = 'block';
        document.getElementById('editFeatures').style.display = 'block';
        document.getElementById('editDescription').style.display = 'block';
        document.getElementById('editFeaturesList').style.display = 'block';
        document.getElementById('editControls').style.display = 'block';
        
        // Change edit button to cancel
        const editBtn = document.getElementById('editBtn');
        editBtn.textContent = 'Cancel Edit';
        editBtn.className = 'btn btn-danger';
        
    } else {
        // Show read-only UI
        document.getElementById('readOnlyView').style.display = 'block';
        document.getElementById('readOnlyFeatures').style.display = 'block';
        document.getElementById('readOnlyDescription').style.display = 'block';
        document.getElementById('readOnlyFeaturesList').style.display = 'block';
        
        document.getElementById('editView').style.display = 'none';
        document.getElementById('editFeatures').style.display = 'none';
        document.getElementById('editDescription').style.display = 'none';
        document.getElementById('editFeaturesList').style.display = 'none';
        document.getElementById('editControls').style.display = 'none';
        
        // Change cancel button back to edit
        const editBtn = document.getElementById('editBtn');
        editBtn.textContent = 'Edit Listing';
        editBtn.className = 'btn btn-warning';
    }
}

function cancelPropertyEdits() {
    toggleEditMode();
}

function savePropertyEdits(propertyId) {
    // Collect all edit field values
    const updateData = {
        title: document.getElementById('editTitle').value,
        price: document.getElementById('editPrice').value,
        contract_type: document.getElementById('editContractType').value,
        city: document.getElementById('editCity').value,
        neighborhood: document.getElementById('editNeighborhood').value,
        description: document.getElementById('editDescriptionText').value,
        bedrooms: document.getElementById('editBedrooms').value,
        bathrooms: document.getElementById('editBathrooms').value,
        square_meters: document.getElementById('editSquareMeters').value,
        year_built: document.getElementById('editYearBuilt').value,
        floor: document.getElementById('editFloor').value,
        has_elevator: document.getElementById('editHasElevator').value,
        heating: document.getElementById('editHeating').value,
        energy_class: document.getElementById('editEnergyClass').value,
        address: document.getElementById('editAddress').value,
        rooms: document.getElementById('editRooms').value,
        energy_consumption: document.getElementById('editEnergyConsumption').value,
        has_air_conditioning: document.getElementById('editHasAirConditioning').checked,
        has_garage: document.getElementById('editHasGarage').checked,
        is_furnished: document.getElementById('editIsFurnished').checked,
        features: document.getElementById('editFeaturesText').value,
        publication_date: document.getElementById('editPublicationDate').value,
        agency_listing_id: document.getElementById('editAgencyListingId').value,
        raw_html_file: document.getElementById('editRawHtmlFile').value
    };
    
    // Filter out empty values (except for false boolean values)
    const filteredData = {};
    for (const [key, value] of Object.entries(updateData)) {
        if (value !== '' && value !== null && value !== undefined) {
            filteredData[key] = value;
        }
    }
    
    // Disable save buttons and show loading state
    const saveBtns = [document.getElementById('saveEditsBtn'), document.getElementById('saveEditsBtnBottom')];
    saveBtns.forEach(btn => {
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        }
    });
    
    // Send PUT request to update property
    fetch(`/properties/${propertyId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(filteredData)
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
            saveBtns.forEach(btn => {
                if (btn) {
                    btn.innerHTML = '✓ Saved Successfully';
                    btn.className = 'btn btn-success';
                }
            });
            
            // Exit edit mode after 2 seconds
            setTimeout(() => {
                toggleEditMode();
                
                // Reload page to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            }, 2000);
        } else {
            // Show error message
            saveBtns.forEach(btn => {
                if (btn) {
                    btn.innerHTML = '✗ Save Failed';
                    btn.className = 'btn btn-danger';
                }
            });
            
            // Re-enable buttons after 3 seconds
            setTimeout(() => {
                saveBtns.forEach(btn => {
                    if (btn) {
                        btn.innerHTML = 'Save Changes';
                        btn.className = 'btn btn-primary';
                        btn.disabled = false;
                    }
                });
            }, 3000);
        }
    })
    .catch(error => {
        console.error('Error saving property edits:', error);
        
        // Show error message
        saveBtns.forEach(btn => {
            if (btn) {
                btn.innerHTML = '✗ Error';
                btn.className = 'btn btn-danger';
            }
        });
        
        // Re-enable buttons after 3 seconds
        setTimeout(() => {
            saveBtns.forEach(btn => {
                if (btn) {
                    btn.innerHTML = 'Save Changes';
                    btn.className = 'btn btn-primary';
                    btn.disabled = false;
                }
            });
        }, 3000);
    });
}