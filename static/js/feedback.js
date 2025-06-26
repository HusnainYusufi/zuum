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
        document.querySelector('.modal-content h2').textContent = 'Feedback Form';
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
        const originalButtonText = submitButton.textContent;

        try {
            const formData = new FormData(feedbackForm);
            
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
            const modalContent = document.querySelector('.modal-content');
            const thankYouMessage = document.createElement('div');
            thankYouMessage.className = 'thank-you-message';
            thankYouMessage.innerHTML = `
                <h2>Thank You!</h2>
                <p>Your feedback has been submitted successfully.</p>
                <div class="thank-you-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
            `;
            modalContent.appendChild(thankYouMessage);

            // Close modal after 2 seconds
            setTimeout(() => {
                feedbackModal.style.display = 'none';
                // Remove thank you message and show form again
                thankYouMessage.remove();
                feedbackForm.style.display = 'block';
            }, 2000);

        } catch (error) {
            // Show error message
            const modalContent = document.querySelector('.modal-content');
            const errorMessage = document.createElement('div');
            errorMessage.className = 'error-message';
            errorMessage.innerHTML = `
                <h2>Error</h2>
                <p>Failed to send feedback. Please try again later.</p>
                <div class="error-icon">
                    <i class="fas fa-exclamation-circle"></i>
                </div>
            `;
            modalContent.appendChild(errorMessage);

            // Remove error message and show form after 3 seconds
            setTimeout(() => {
                errorMessage.remove();
                feedbackForm.style.display = 'block';
            }, 3000);

            console.error('Error sending feedback:', error);
        } finally {
            // Reset button state
            submitButton.textContent = originalButtonText;
            submitButton.disabled = false;
        }
    });

    // Character counter functionality
    function updateCharCounter() {
        const currentLength = textarea.value.length;
        charCounter.textContent = `${currentLength}/${maxLength} characters`;

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