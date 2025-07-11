document.addEventListener('DOMContentLoaded', function() {
    const feedbackButton = document.getElementById('feedback-button');
    const feedbackModal = document.getElementById('feedback-modal');
    const modalClose = document.getElementById('modal-close');
    const feedbackForm = document.getElementById('feedback-form');
    const textarea = document.getElementById('feedbackTextarea');
    const charCounter = document.getElementById('charCounter');
    const maxLength = 1400;

    // Open modal
    feedbackButton.addEventListener('click', function() {
        feedbackModal.style.display = 'block';
        // Reset form and show form content
        feedbackForm.reset();
        feedbackForm.style.display = 'block';
    });

    // Close modal
    modalClose.addEventListener('click', function() {
        feedbackModal.style.display = 'none';
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === feedbackModal) {
            feedbackModal.style.display = 'none';
        }
    });

    // Handle form submission
    feedbackForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        const submitButton = feedbackForm.querySelector('.submit-button');
        if (!submitButton) {
            console.error('Submit button not found');
            return;
        }
        
        const originalButtonText = submitButton.textContent;

        try {
            const formData = new FormData(feedbackForm);
            
            // Get the current feedback description
            const originalDescription = formData.get('feedbackDescription');
            
            // Append the current page URL to the description
            const currentUrl = window.location.href;
            const updatedDescription = `${originalDescription}\n\nCheck In Url: ${currentUrl}`;
            
            // Update the FormData with the new description
            formData.set('feedbackDescription', updatedDescription);
            
            // Show loading state
            submitButton.textContent = 'Sending...';
            submitButton.disabled = true;

            // Send data to server
            const response = await fetch('/send-feedback', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.message);
            }

            // Hide the form and show thank you message
            feedbackForm.style.display = 'none';
            const thankYouMessage = document.createElement('div');
            thankYouMessage.className = 'thank-you-message text-center p-6';
            thankYouMessage.innerHTML = `
                <h2 class="text-2xl font-bold text-electric-lime mb-4">Thank You!</h2>
                <p class="text-gray-300 mb-4">Your feedback has been submitted successfully.</p>
                <div class="thank-you-icon text-4xl text-electric-lime">
                    <i class="fas fa-check-circle"></i>
                </div>
            `;
            
            // Append to the widget-card (parent of the form)
            const widgetCard = feedbackForm.closest('.widget-card');
            if (widgetCard) {
                widgetCard.appendChild(thankYouMessage);
            }

            // Close modal after 2 seconds
            setTimeout(() => {
                feedbackModal.style.display = 'none';
                // Remove thank you message and show form again
                thankYouMessage.remove();
                feedbackForm.style.display = 'block';
            }, 2000);

        } catch (error) {
            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'error-message text-center p-6';
            errorMessage.innerHTML = `
                <h2 class="text-2xl font-bold text-red-400 mb-4">Error</h2>
                <p class="text-gray-300 mb-4">Failed to send feedback. Please try again later.</p>
                <div class="error-icon text-4xl text-red-400">
                    <i class="fas fa-exclamation-circle"></i>
                </div>
            `;
            
            // Append to the widget-card (parent of the form)
            const widgetCard = feedbackForm.closest('.widget-card');
            if (widgetCard) {
                widgetCard.appendChild(errorMessage);
            }

            // Remove error message and show form after 3 seconds
            setTimeout(() => {
                errorMessage.remove();
                feedbackForm.style.display = 'block';
            }, 3000);

            console.error('Error sending feedback:', error);
        } finally {
            // Reset button state
            if (submitButton) {
                submitButton.textContent = originalButtonText;
                submitButton.disabled = false;
            }
        }
    });

    // Character counter functionality
    function updateCharCounter() {
        if (!textarea || !charCounter) return;
        
        const currentLength = textarea.value.length;
        charCounter.textContent = `${currentLength}/${maxLength}`;

        // Update counter color based on length
        charCounter.classList.remove('near-limit', 'at-limit');
        if (currentLength >= maxLength) {
            charCounter.classList.add('at-limit');
        } else if (currentLength >= maxLength * 0.9) { // When 90% full
            charCounter.classList.add('near-limit');
        }
    }

    // Add event listeners
    if (textarea) {
        textarea.addEventListener('input', updateCharCounter);
        textarea.addEventListener('keyup', updateCharCounter);
        textarea.addEventListener('paste', function(e) {
            setTimeout(updateCharCounter, 0);
        });

        // Initialize counter
        updateCharCounter();
    }
}); 