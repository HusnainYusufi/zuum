class CheckInPage {
    constructor() {
        this.checkIn = null;
        this.checkInId = this.getCheckInIdFromUrl();
        this.isDarkMode = true;
        this.init();
    }

    getCheckInIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    async init() {
        // Always apply dark mode
        document.querySelector('.App').classList.add('dark-mode');
        document.querySelector('.transcript-page').classList.add('dark-mode');

        // Show loading spinner
        this.showLoading();

        // Check call status first
        const callStatus = await this.checkCallStatus();
        
        if (callStatus === 'in_progress') {
            // Show call progress overlay and start polling
            this.showCallProgress();
            await this.pollCallStatus();
        } else {
            // Fetch check-in data directly
            await this.fetchCheckIn();
        }

        // Hide loading spinner and call progress overlay
        this.hideLoading();
        this.hideCallProgress();

        // Render the page
        if (this.checkIn) {
            this.render();
        } else {
            this.renderNoData();
        }
    }

    showLoading() {
        const loadingContainer = document.getElementById('loading-container');
        const mainContent = document.querySelector('.transcript-page');
        if (loadingContainer) {
            loadingContainer.style.display = 'flex';
            loadingContainer.classList.add(this.isDarkMode ? 'dark-mode' : '');
        }
        if (mainContent) {
            mainContent.style.display = 'none';
        }
    }

    hideLoading() {
        const loadingContainer = document.getElementById('loading-container');
        const mainContent = document.querySelector('.transcript-page');
        if (loadingContainer) {
            loadingContainer.style.display = 'none';
        }
        if (mainContent) {
            mainContent.style.display = 'block';
        }
    }

    showCallProgress() {
        const callProgressOverlay = document.getElementById('call-progress-overlay');
        if (callProgressOverlay) {
            callProgressOverlay.style.display = 'flex';
        }
    }

    hideCallProgress() {
        const callProgressOverlay = document.getElementById('call-progress-overlay');
        if (callProgressOverlay) {
            callProgressOverlay.style.display = 'none';
        }
    }

    async checkCallStatus() {
        if (!this.checkInId) {
            return 'no_call';
        }

        try {
            const response = await fetch(`/retell/check-in/${this.checkInId}/status`, {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to check call status');
            }

            const statusData = await response.json();
            return statusData.status;
        } catch (error) {
            console.error('Error checking call status:', error);
            return 'error';
        }
    }

    async pollCallStatus() {
        const maxAttempts = 60; // Poll for up to 5 minutes (60 attempts * 5 seconds)
        let attempts = 0;

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
            attempts++;

            const status = await this.checkCallStatus();
            
            if (status === 'completed') {
                // Call completed, fetch the check-in data
                await this.fetchCheckIn();
                break;
            } else if (status === 'error' || status === 'no_call') {
                // Error or no call found, stop polling
                break;
            }
            
            // Continue polling if status is still 'in_progress'
        }

        // If we've exhausted all attempts, still try to fetch data
        if (attempts >= maxAttempts) {
            await this.fetchCheckIn();
        }
    }

    async fetchCheckIn() {
        if (!this.checkInId) {
            console.error('No check-in ID provided');
            return;
        }

        try {
            const response = await fetch('/check-ins', {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch check-ins');
            }

            const checkIns = await response.json();
            this.checkIn = checkIns.find(ci => ci.id.toString() === this.checkInId);

            if (!this.checkIn) {
                console.error('Check-in not found');
            }
        } catch (error) {
            console.error('Error fetching check-in:', error);
        }
    }

    render() {
        // Update page title
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = `Call Transcript - Check-in #${this.checkIn.id.toString().padStart(2, '0')}`;
        }

        // Render check-in details
        this.renderCheckInDetails();

        // Render status information
        this.renderStatusInfo();

        // Render transcript
        this.renderTranscript();

        // Render AI summary if available
        if (this.checkIn.AI_Response_Summary) {
            this.renderAISummary();
        }

        // Render output data if available
        if (this.checkIn.check_in_metadata) {
            this.renderOutputData();
        }
    }

    renderCheckInDetails() {
        const detailsContainer = document.getElementById('checkin-details');
        if (!detailsContainer) return;

        let detailsHTML = '';

        // Check-in ID
        detailsHTML += `
            <div class="info-item">
                <span class="info-label">Check-in ID:</span>
                <span class="info-value">#${this.checkIn.id.toString().padStart(2, '0')}</span>
            </div>
        `;

        // Call ID
        if (this.checkIn.call_id) {
            detailsHTML += `
                <div class="info-item">
                    <span class="info-label">Call ID:</span>
                    <span class="info-value">${this.checkIn.call_id}</span>
                </div>
            `;
        }

        // Load ID
        if (this.checkIn.load_id) {
            detailsHTML += `
                <div class="info-item">
                    <span class="info-label">Load ID:</span>
                    <span class="info-value">${this.checkIn.load_id}</span>
                </div>
            `;
        }

        // Date & Time
        if (this.checkIn.AI_Timestamp) {
            const date = new Date(this.checkIn.AI_Timestamp);
            const dateStr = date.toLocaleDateString('en-US', { 
                month: '2-digit', 
                day: '2-digit', 
                year: 'numeric' 
            });
            const timeStr = date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit', 
                second: '2-digit', 
                hour12: true 
            });
            detailsHTML += `
                <div class="info-item">
                    <span class="info-label">Date & Time:</span>
                    <span class="info-value">${dateStr} at ${timeStr}</span>
                </div>
            `;
        }

        // Miles
        if (this.checkIn.miles) {
            detailsHTML += `
                <div class="info-item">
                    <span class="info-label">Miles:</span>
                    <span class="info-value">${this.checkIn.miles}</span>
                </div>
            `;
        }

        // Recording URL
        if (this.checkIn.recording_url) {
            let recordingUrl = this.checkIn.recording_url;
            
            // Ensure the URL is absolute - if it doesn't start with http:// or https://, add https://
            if (!recordingUrl.startsWith('http://') && !recordingUrl.startsWith('https://')) {
                recordingUrl = 'https://' + recordingUrl;
            }
            
            // Generate a filename for download
            const timestamp = this.checkIn.AI_Timestamp ? new Date(this.checkIn.AI_Timestamp).toISOString().split('T')[0] : 'recording';
            const downloadFilename = `checkin_${this.checkIn.id}_${timestamp}.wav`;
            
            detailsHTML += `
                <div class="info-item">
                    <span class="info-label">Recording:</span>
                    <div class="info-value recording-actions">
                        <a href="${recordingUrl}" download="${downloadFilename}" class="recording-link download-link">
                            <i class="fas fa-download"></i> Download Recording
                        </a>
                    </div>
                </div>
            `;
        }

        detailsContainer.innerHTML = detailsHTML;
    }

    renderStatusInfo() {
        const statusContainer = document.getElementById('status-info');
        if (!statusContainer) return;

        const issueFlagged = this.checkIn.Issue_Flagged || false;
        const requiresReview = this.checkIn.Requires_Human_Review || false;

        statusContainer.innerHTML = `
            <div class="status-item ${issueFlagged ? 'flagged' : 'normal'}">
                <span class="status-label">Issue Flagged:</span>
                <span class="status-value">${issueFlagged ? 'Yes' : 'No'}</span>
            </div>
            <div class="status-item ${requiresReview ? 'review' : 'normal'}">
                <span class="status-label">Human Review:</span>
                <span class="status-value">${requiresReview ? 'Yes' : 'No'}</span>
            </div>
        `;
    }

    renderTranscript() {
        const transcriptContainer = document.getElementById('transcript-content');
        if (!transcriptContainer) return;

        if (!this.checkIn.call_transcript) {
            transcriptContainer.innerHTML = `
                <div class="no-transcript">
                    <i class="fas fa-comment-dots empty-icon"></i>
                    <p>No transcript available for this check-in.</p>
                </div>
            `;
            return;
        }

        const lines = this.checkIn.call_transcript.split('\n');
        let transcriptHTML = '';

        lines.forEach((line, index) => {
            const trimmedLine = line.trim();
            if (!trimmedLine) return;

            // Determine if this is an agent or user message
            const isAgent = /^(Agent:|AI:|AGENT:|Assistant:|Bot:)/i.test(trimmedLine);
            const isUser = /^(User:|USER:|Driver:|DRIVER:|Human:)/i.test(trimmedLine);

            let cleanLine = trimmedLine;
            
            // Remove prefixes
            if (isAgent) {
                cleanLine = trimmedLine.replace(/^(Agent:|AI:|AGENT:|Assistant:|Bot:)\s*/i, '').trim();
            } else if (isUser) {
                cleanLine = trimmedLine.replace(/^(User:|USER:|Driver:|DRIVER:|Human:)\s*/i, '').trim();
            }

            // If no clear prefix, assume it's an agent message
            const messageType = isUser ? 'user' : 'agent';
            const wrapperType = isUser ? 'user-wrapper' : 'agent-wrapper';

            if (cleanLine) {
                transcriptHTML += `
                    <div class="transcript-line-wrapper ${wrapperType}">
                        <div class="transcript-line ${messageType}">
                            ${this.escapeHtml(cleanLine)}
                        </div>
                    </div>
                `;
            }
        });

        transcriptContainer.innerHTML = transcriptHTML;
    }

    renderAISummary() {
        const summaryCard = document.getElementById('ai-summary-card');
        const summaryContent = document.getElementById('ai-summary-content');
        
        if (summaryCard && summaryContent) {
            summaryCard.style.display = 'block';
            summaryContent.innerHTML = `<p>${this.escapeHtml(this.checkIn.AI_Response_Summary)}</p>`;
        }
    }

    renderFormData() {
        const formCard = document.getElementById('form-card');
        const formContent = document.getElementById('form-content');
        
        if (formCard && formContent) {
            try {
                const metadata = JSON.parse(this.checkIn.check_in_metadata);
                
                if (metadata.form) {
                    formCard.style.display = 'block';
                    
                    // Parse the form data (it's a JSON string within the metadata)
                    const formData = JSON.parse(metadata.form);
                    let formHTML = '<div class="form-grid">';
                    
                    // Define a mapping for better display names
                    const fieldMapping = {
                        'load_id': 'Load ID',
                        'trucker_name': 'Driver Name',
                        'contact_phone': 'Contact Phone',
                        'pickup_address': 'Pickup Address',
                        'driver_type': 'Driver Type',
                        'tractor_number': 'Tractor Number',
                        'trailer_number': 'Trailer Number',
                        'required_equipment': 'Required Equipment',
                        'preferred_comms': 'Preferred Communication',
                        'tracking_on': 'Tracking Enabled'
                    };
                    
                    Object.entries(formData).forEach(([key, value]) => {
                        // Use mapping if available, otherwise format the key
                        const displayKey = fieldMapping[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        
                        // Format specific values
                        let displayValue = String(value);
                        if (key === 'tracking_on') {
                            displayValue = value === 'Y' ? 'Yes' : 'No';
                        }
                        
                        formHTML += `
                            <div class="form-item">
                                <span class="form-label">${displayKey}</span>
                                <span class="form-value">${this.escapeHtml(displayValue)}</span>
                            </div>
                        `;
                    });
                    
                    formHTML += '</div>';
                    formContent.innerHTML = formHTML;
                }
            } catch (error) {
                console.error('Error parsing form data:', error);
            }
        }
    }

    renderOutputData() {
        const outputCard = document.getElementById('output-card');
        const outputContent = document.getElementById('output-content');
        
        if (outputCard && outputContent) {
            try {
                const metadata = JSON.parse(this.checkIn.check_in_metadata);
                
                if (metadata.output) {
                    outputCard.style.display = 'block';
                    
                    // Parse the output data (it's a JSON string within the metadata)
                    const outputData = JSON.parse(metadata.output);
                    let outputHTML = '<div class="output-grid">';
                    
                    // Define better display names and order
                    const fieldMapping = {
                        'Is_assigned_driver': 'Correct Driver',
                        'Driver_empty': 'Driver Empty',
                        'Current_location': 'Current Location',
                        'ETA_to_shipper': 'ETA to Shipper',
                        'Confirmed_equipment': 'Equipment Confirmed',
                        'Tracking_started': 'Tracking Started',
                        'door number': 'Door Number'
                    };
                    
                    // Define field order for better presentation
                    const fieldOrder = [
                        'Is_assigned_driver',
                        'Current_location', 
                        'Driver_empty',
                        'ETA_to_shipper',
                        'Confirmed_equipment',
                        'Tracking_started',
                        'door number'
                    ];
                    
                    // Render fields in order
                    fieldOrder.forEach(key => {
                        if (outputData.hasOwnProperty(key)) {
                            const value = outputData[key];
                            const displayKey = fieldMapping[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            
                            // Format values
                            let displayValue = value;
                            let statusClass = '';
                            
                            if (typeof value === 'boolean') {
                                displayValue = value ? 'Yes' : 'No';
                                statusClass = value ? 'status-success' : 'status-warning';
                            } else if (key === 'door number' && (value === 'None' || value === null || value === '')) {
                                displayValue = 'Not provided';
                                statusClass = 'status-warning';
                            }
                            
                            outputHTML += `
                                <div class="output-item ${statusClass}">
                                    <span class="output-label">${displayKey}</span>
                                    <span class="output-value">${this.escapeHtml(String(displayValue))}</span>
                                </div>
                            `;
                        }
                    });
                    
                    // Add any remaining fields not in the order list
                    Object.entries(outputData).forEach(([key, value]) => {
                        if (!fieldOrder.includes(key)) {
                            const displayKey = fieldMapping[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            let displayValue = value;
                            let statusClass = '';
                            
                            if (typeof value === 'boolean') {
                                displayValue = value ? 'Yes' : 'No';
                                statusClass = value ? 'status-success' : 'status-warning';
                            }
                            
                            outputHTML += `
                                <div class="output-item ${statusClass}">
                                    <span class="output-label">${displayKey}</span>
                                    <span class="output-value">${this.escapeHtml(String(displayValue))}</span>
                                </div>
                            `;
                        }
                    });
                    
                    outputHTML += '</div>';
                    outputContent.innerHTML = outputHTML;
                }
            } catch (error) {
                console.error('Error parsing output data:', error);
            }
        }
    }

    renderMetadata() {
        const metadataCard = document.getElementById('metadata-card');
        const metadataContent = document.getElementById('metadata-content');
        
        if (metadataCard && metadataContent) {
            try {
                const metadata = JSON.parse(this.checkIn.check_in_metadata);
                
                // Only show technical metadata that's not form or output data
                const filteredMetadata = {};
                Object.entries(metadata).forEach(([key, value]) => {
                    if (key !== 'form' && key !== 'output') {
                        // Only include relevant technical fields
                        if (key === 'purpose' || key === 'output_schema') {
                            filteredMetadata[key] = value;
                        }
                    }
                });
                
                if (Object.keys(filteredMetadata).length > 0) {
                    metadataCard.style.display = 'block';
                    
                    let metadataHTML = '<div class="metadata-grid">';
                    
                    Object.entries(filteredMetadata).forEach(([key, value]) => {
                        let displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        let displayValue = value;
                        
                        // Format specific fields for better readability
                        if (key === 'purpose') {
                            displayKey = 'Call Purpose';
                            try {
                                // Parse and format the purpose array
                                const purposes = JSON.parse(value);
                                if (Array.isArray(purposes)) {
                                    displayValue = purposes.map((p, i) => `${i + 1}. ${p}`).join('\n');
                                }
                            } catch (e) {
                                // If not JSON, display as is
                            }
                        } else if (key === 'output_schema') {
                            displayKey = 'Expected Data Fields';
                            try {
                                const schema = JSON.parse(value);
                                if (schema.properties) {
                                    const fields = Object.keys(schema.properties);
                                    displayValue = fields.join(', ');
                                }
                            } catch (e) {
                                displayValue = 'Schema definition';
                            }
                        }
                        
                        metadataHTML += `
                            <div class="metadata-item">
                                <span class="metadata-label">${displayKey}</span>
                                <span class="metadata-value">${this.escapeHtml(String(displayValue))}</span>
                            </div>
                        `;
                    });
                    
                    metadataHTML += '</div>';
                    metadataContent.innerHTML = metadataHTML;
                }
            } catch (error) {
                console.error('Error parsing metadata:', error);
                // Don't show raw JSON on error, just hide the card
                metadataCard.style.display = 'none';
            }
        }
    }

    renderNoData() {
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = 'No Check-in Selected';
        }

        const transcriptContainer = document.querySelector('.transcript-container');
        if (transcriptContainer) {
            transcriptContainer.innerHTML = `
                <div class="transcript-content">
                    <p>No check-in data available.</p>
                </div>
            `;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CheckInPage();
}); 