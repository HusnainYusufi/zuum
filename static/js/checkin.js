class CheckInPage {
    constructor() {
        this.checkIn = null;
        this.checkInId = this.getCheckInIdFromUrl();
        this.isDarkMode = true;
        // Don't call init() here - it will be called after DOM is ready
    }

    getCheckInIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    async init() {
        // Apply dark mode to the new structure
        const checkinPage = document.querySelector('.checkin-page');
        if (checkinPage) {
            checkinPage.classList.add('dark-mode');
        }

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
        const mainContent = document.querySelector('.checkin-page');
        
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
        const mainContent = document.querySelector('.checkin-page');
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
            // Use the correct API endpoint
            const response = await fetch(`/api/checkin/${this.checkInId}`, {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch check-in: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (result.status === 'success' && result.data) {
                this.checkIn = result.data;
            } else {
                console.error('Check-in not found or invalid response:', result);
            }
        } catch (error) {
            console.error('Error fetching check-in:', error);
        }
    }

    render() {

        // Update page title
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = `Check-in #${this.checkIn.id.toString().padStart(2, '0')}`;
        }

        // Render check-in details
        this.renderCheckInDetails();

        // Render status information
        this.renderStatusInfo();

        // Render transcript
        this.renderTranscript();

        // Render load information if available
        if (this.checkIn.forms || this.checkIn.check_in_metadata) {
            this.renderLoadInfo();
        }

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
        const isCallTransferred = this.checkIn.call_trasfered || false;
        const isCallActive = this.checkIn.is_active || false;

        let statusHTML = '';

        // Issue Flagged Status
        statusHTML += `
            <div class="info-item">
                <span class="info-label">Issue Flagged:</span>
                <span class="info-value ${issueFlagged ? 'status-flagged' : 'status-completed'}">${issueFlagged ? 'Yes' : 'No'}</span>
            </div>
        `;

        // Call Transfer Status
        statusHTML += `
            <div class="info-item">
                <span class="info-label">Call Transferred:</span>
                <span class="info-value ${isCallTransferred ? 'status-transferred' : 'status-completed'}">${isCallTransferred ? 'Yes' : 'No'}</span>
            </div>
        `;

        // Call Status (Active/Completed)
        statusHTML += `
            <div class="info-item">
                <span class="info-label">Call Status:</span>
                <span class="info-value ${isCallActive ? 'status-active' : 'status-completed'}">${isCallActive ? 'Active' : 'Completed'}</span>
            </div>
        `;

        statusContainer.innerHTML = statusHTML;
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

    renderLoadInfo() {
        const loadInfoCard = document.getElementById('load-info-card');
        const loadInfoContent = document.getElementById('load-info-content');
        
        if (loadInfoCard && loadInfoContent) {
            let formData = null;
            
            try {
                // First, try to get form data from the new 'forms' column
                if (this.checkIn.forms) {
                    formData = JSON.parse(this.checkIn.forms);
                    console.log('Using form data from new forms column');
                    formData._dataSource = 'new_forms_column';
                } 
                // Fall back to the old check_in_metadata.form for backward compatibility
                else if (this.checkIn.check_in_metadata) {
                    const metadata = JSON.parse(this.checkIn.check_in_metadata);
                    if (metadata.form) {
                        // Clean up the form JSON string before parsing
                        let formString = metadata.form.trim();
                        
                        // Remove trailing comma if it exists
                        if (formString.endsWith(',')) {
                            formString = formString.slice(0, -1);
                        }
                        
                        // Remove any trailing whitespace and commas from the end of the object
                        formString = formString.replace(/,\s*}$/, '}');
                        
                        // Parse the cleaned form data
                        formData = JSON.parse(formString);
                        console.log('Using form data from legacy check_in_metadata');
                        formData._dataSource = 'legacy_metadata';
                    }
                }
                
                if (formData) {
                    loadInfoCard.style.display = 'block';
                    
                    // Add visual indicator for form data presence
                    const cardHeader = loadInfoCard.querySelector('.card-header h3');
                    if (cardHeader && !cardHeader.querySelector('.form-data-indicator')) {
                        const isNewFormat = formData._dataSource === 'new_forms_column';
                        const indicatorText = isNewFormat ? 'FORM DATA' : 'FORM DATA (LEGACY)';
                        const indicatorColor = isNewFormat ? '#68d391' : '#f6ad55';
                        const indicatorBg = isNewFormat ? 'rgba(104, 211, 145, 0.1)' : 'rgba(246, 173, 85, 0.1)';
                        cardHeader.innerHTML += ` <span class="form-data-indicator" style="color: ${indicatorColor}; font-size: 12px; font-weight: 500; background: ${indicatorBg}; padding: 2px 8px; border-radius: 12px; margin-left: 8px;">${indicatorText}</span>`;
                    }
                    
                    let loadInfoHTML = '';
                    
                    // Define better field labels and organize them by category
                    const fieldLabels = {
                        // Basic Load Information
                        'load_id': 'Load ID',
                        'pickup_load_id': 'Load ID',
                        'pc_load_id': 'Load ID', 
                        'it_load_id': 'Load ID',
                        'ad_load_id': 'Load ID',
                        'del_load_id': 'Load ID',
                        'pod_load_id': 'Load ID',
                        
                        // Contact Information
                        'carrier_name': 'Carrier Name',
                        'contact_name': 'Contact Name',
                        'contact_phone': 'Contact Phone',
                        'pickup_contact_phone': 'Contact Phone',
                        'pc_contact_phone': 'Contact Phone',
                        'it_contact_phone': 'Contact Phone',
                        'ad_contact_phone': 'Contact Phone',
                        'del_contact_phone': 'Contact Phone',
                        'pod_contact_phone': 'Contact Phone',
                        'country_code': 'Country Code',
                        'pickup_country_code': 'Country Code',
                        'pc_country_code': 'Country Code',
                        'it_country_code': 'Country Code',
                        'ad_country_code': 'Country Code',
                        'del_country_code': 'Country Code',
                        'pod_country_code': 'Country Code',
                        
                        // Driver Information
                        'trucker_name': 'Trucker Name',
                        'pickup_trucker_name': 'Trucker Name',
                        'pc_trucker_name': 'Trucker Name',
                        'it_trucker_name': 'Trucker Name',
                        'ad_trucker_name': 'Trucker Name',
                        'del_trucker_name': 'Trucker Name',
                        'pod_trucker_name': 'Trucker Name',
                        'driver_type': 'Driver Type',
                        
                        // Equipment Information
                        'tractor_number': 'Tractor Number',
                        'trailer_number': 'Trailer Number',
                        'required_equipment': 'Required Equipment',
                        
                        // Location Information
                        'pickup_address': 'Pickup Address',
                        'origin_address': 'Origin Address',
                        'destination_address': 'Destination Address',
                        'receiver_address': 'Receiver Address',
                        'current_location': 'Current Location',
                        'next_stop_location': 'Next Stop Location',
                        
                        // Timing Information
                        'scheduled_pickup_time': 'Scheduled Pickup Time',
                        'scheduled_delivery_time': 'Scheduled Delivery Time',
                        'actual_pickup_time': 'Actual Pickup Time',
                        'scheduled_eta': 'Scheduled ETA',
                        'arrival_time': 'Arrival Time',
                        'empty_time': 'Empty Time',
                        'delivery_date': 'Delivery Date',
                        'last_check_call_time': 'Last Check Call Time',
                        
                        // Status Information
                        'last_known_status': 'Last Known Status',
                        'purpose': 'Call Purpose',
                        'remaining_miles': 'Remaining Miles',
                        'driver_tracking': 'Driver on Tracking',
                        'tracking_on': 'Tracking On',
                        'delay_reason': 'Delay Reason',
                        
                        // Delivery Information
                        'receiver_name': 'Receiver Name',
                        'dock_number': 'Dock Number',
                        'bol_verified': 'BOL/PO Verified',
                        'commodity_description': 'Commodity Description',
                        'lumper_needed': 'Lumper Needed',
                        'lumper_amount': 'Lumper Amount',
                        'payment_method': 'Payment Method',
                        'pod_uploaded': 'POD Uploaded',
                        'lumper_receipt': 'Lumper Receipt Collected',
                        'final_osd': 'Final OS&D',
                        'osd_notes': 'OS&D Notes',
                        'upload_method': 'Upload Method',
                        'reminder_attempt': 'Reminder Attempt',
                        
                        // Additional Information
                        'preferred_comms': 'Preferred Communication',
                        'accessorials_needed': 'Accessorials Needed',
                        'transfer_call_to': 'Transfer Call To',
                        'transfer_country_code': 'Transfer Country Code',
                        'notes': 'Notes'
                    };
                    
                    // Define field ordering for better presentation
                    const fieldOrder = [
                        // Load and Contact Info
                        'load_id', 'pickup_load_id', 'pc_load_id', 'it_load_id', 'ad_load_id', 'del_load_id', 'pod_load_id',
                        'carrier_name', 'contact_name', 
                        'contact_phone', 'pickup_contact_phone', 'pc_contact_phone', 'it_contact_phone', 'ad_contact_phone', 'del_contact_phone', 'pod_contact_phone',
                        'country_code', 'pickup_country_code', 'pc_country_code', 'it_country_code', 'ad_country_code', 'del_country_code', 'pod_country_code',
                        
                        // Driver Info
                        'trucker_name', 'pickup_trucker_name', 'pc_trucker_name', 'it_trucker_name', 'ad_trucker_name', 'del_trucker_name', 'pod_trucker_name',
                        'driver_type',
                        
                        // Equipment
                        'tractor_number', 'trailer_number', 'required_equipment',
                        
                        // Locations
                        'pickup_address', 'origin_address', 'destination_address', 'receiver_address', 'current_location', 'next_stop_location',
                        
                        // Timing
                        'scheduled_pickup_time', 'scheduled_delivery_time', 'actual_pickup_time', 'scheduled_eta', 'arrival_time', 'empty_time', 'delivery_date',
                        
                        // Status and Tracking
                        'purpose', 'last_known_status', 'remaining_miles', 'driver_tracking', 'tracking_on', 'delay_reason',
                        
                        // Delivery Details
                        'receiver_name', 'dock_number', 'bol_verified', 'commodity_description', 'lumper_needed', 'lumper_amount', 'payment_method',
                        'pod_uploaded', 'lumper_receipt', 'final_osd', 'osd_notes', 'upload_method', 'reminder_attempt',
                        
                        // Additional
                        'preferred_comms', 'accessorials_needed', 'transfer_call_to', 'notes'
                    ];
                    
                    // First render fields in order
                    fieldOrder.forEach(key => {
                        if (formData.hasOwnProperty(key) && formData[key] !== null && formData[key] !== '' && formData[key] !== undefined && !key.startsWith('_')) {
                            const displayLabel = fieldLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            let displayValue = this.escapeHtml(String(formData[key]));
                            
                            // Special formatting for common patterns
                            if (key.toLowerCase().includes('tracking') && (formData[key] === 'Y' || formData[key] === 'Yes' || formData[key] === true)) {
                                displayValue = '<span style="color: #68d391; font-weight: 600;">Yes</span>';
                            } else if (key.toLowerCase().includes('tracking') && (formData[key] === 'N' || formData[key] === 'No' || formData[key] === false)) {
                                displayValue = '<span style="color: #fc8181; font-weight: 600;">No</span>';
                            } else if (key.toLowerCase().includes('verified') && (formData[key] === 'Y' || formData[key] === 'Yes')) {
                                displayValue = '<span style="color: #68d391; font-weight: 600;">Yes - Matches</span>';
                            } else if (key.toLowerCase().includes('verified') && (formData[key] === 'N' || formData[key] === 'No')) {
                                displayValue = '<span style="color: #fc8181; font-weight: 600;">No - Does Not Match</span>';
                            } else if (key.toLowerCase().includes('needed') && (formData[key] === 'Y' || formData[key] === 'Yes')) {
                                displayValue = '<span style="color: #f6ad55; font-weight: 600;">Yes</span>';
                            } else if (key.toLowerCase().includes('needed') && (formData[key] === 'N' || formData[key] === 'No')) {
                                displayValue = '<span style="color: #68d391; font-weight: 600;">No</span>';
                            } else if (key.toLowerCase().includes('uploaded') && (formData[key] === 'Y' || formData[key] === 'Yes')) {
                                displayValue = '<span style="color: #68d391; font-weight: 600;">Yes</span>';
                            } else if (key.toLowerCase().includes('uploaded') && (formData[key] === 'N' || formData[key] === 'No')) {
                                displayValue = '<span style="color: #fc8181; font-weight: 600;">No</span>';
                            } else if (key.toLowerCase().includes('time') || key.toLowerCase().includes('date')) {
                                // Format datetime fields
                                try {
                                    const date = new Date(formData[key]);
                                    if (!isNaN(date.getTime())) {
                                        displayValue = date.toLocaleString('en-US', {
                                            month: '2-digit',
                                            day: '2-digit',
                                            year: 'numeric',
                                            hour: 'numeric',
                                            minute: '2-digit',
                                            hour12: true
                                        });
                                    }
                                } catch (e) {
                                    // Keep original value if date parsing fails
                                }
                            }
                            
                            loadInfoHTML += `
                                <div class="info-item">
                                    <span class="info-label">
                                        <i class="fas fa-info-circle" style="margin-right: 6px; color: #63b3ed;"></i>
                                        ${displayLabel}:
                                    </span>
                                    <span class="info-value">${displayValue}</span>
                                </div>
                            `;
                        }
                    });
                    
                    // Then render any remaining fields not in the order list
                    Object.entries(formData).forEach(([key, value]) => {
                        if (!fieldOrder.includes(key) && value !== null && value !== '' && value !== undefined && !key.startsWith('_')) {
                            const displayLabel = fieldLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            const displayValue = this.escapeHtml(String(value));
                            
                            loadInfoHTML += `
                                <div class="info-item">
                                    <span class="info-label">
                                        <i class="fas fa-info-circle" style="margin-right: 6px; color: #63b3ed;"></i>
                                        ${displayLabel}:
                                    </span>
                                    <span class="info-value">${displayValue}</span>
                                </div>
                            `;
                        }
                    });
                    
                    loadInfoContent.innerHTML = loadInfoHTML;
                } else {
                    console.log('No form data found in either forms column or metadata');
                }
            } catch (error) {
                console.error('Error parsing form data:', error);
                console.log('Check-in forms:', this.checkIn.forms);
                console.log('Check-in metadata:', this.checkIn.check_in_metadata);
            }
        }
    }

    renderAISummary() {
        const summaryCard = document.getElementById('ai-summary-card');
        const summaryContent = document.getElementById('ai-summary-content');
        
        if (summaryCard && summaryContent) {
            summaryCard.style.display = 'block';
            summaryContent.innerHTML = `<p>${this.escapeHtml(this.checkIn.AI_Response_Summary)}</p>`;
        }
    }

    renderOutputData() {
        const outputCard = document.getElementById('output-card');
        const outputContent = document.getElementById('output-content');
        
        if (outputCard && outputContent) {
            try {
                const metadata = JSON.parse(this.checkIn.check_in_metadata);
                console.log('Checking output data:', {
                    hasOutput: !!metadata.output,
                    hasOutputSchemaReceived: !!metadata.output_schema_received,
                    hasCustomAnalysisOutput: !!(metadata.custom_analysis_data && metadata.custom_analysis_data.output)
                });
                
                // Check if we have actual output data
                if (metadata.output) {
                    // Parse the output data (it's a JSON string within the metadata)
                    const outputData = JSON.parse(metadata.output);
                    
                    // Check if this is a JSON schema (has 'type', 'properties', etc.) or actual data
                    const isSchema = outputData.hasOwnProperty('type') && outputData.hasOwnProperty('properties');
                    
                    if (isSchema) {
                        // This is a schema definition, not actual output data - show schema received message
                        console.log('Output contains schema definition, not actual extracted data');
                        outputCard.style.display = 'block';
                        outputContent.innerHTML = `
                            <div class="no-output-data">
                                <i class="fas fa-exclamation-triangle" style="color: #f6ad55; font-size: 24px; margin-bottom: 12px;"></i>
                                <p style="color: #a0aec0; font-size: 14px; margin: 0;">Schema received but no data was extracted from the call.</p>
                                <p style="color: #718096; font-size: 12px; margin: 8px 0 0 0;">The AI was expecting to extract specific information but the call ended before data could be collected.</p>
                            </div>
                        `;
                        return;
                    }
                    
                    // This is actual output data, proceed with display
                    outputCard.style.display = 'block';
                    let outputHTML = '<div class="output-grid">';
                    
                    // Define better display names and order
                    const fieldMapping = {
                        'Is_assigned_driver': 'Correct Driver',
                        'Driver_empty': 'Driver Empty',
                        'Current_location': 'Current Location',
                        'ETA_to_shipper': 'ETA to Shipper',
                        'Confirmed_equipment': 'Equipment Confirmed',
                        'Tracking_started': 'Tracking Started',
                        'door number': 'Door Number',
                        'call_transferred': 'Call Transferred',
                        'transfer_reason': 'Transfer Reason',
                        'POD_followup_received': 'POD Follow-up Received',
                        'POD_uploaded': 'POD Uploaded',
                        'delivery_confirmation': 'Delivery Confirmed',
                        'driver_response': 'Driver Response',
                        'pickup_confirmed': 'Pickup Confirmed',
                        'arrival_confirmed': 'Arrival Confirmed'
                    };
                    
                    // Define field order for better presentation
                    const fieldOrder = [
                        'Is_assigned_driver',
                        'Current_location', 
                        'Driver_empty',
                        'ETA_to_shipper',
                        'Confirmed_equipment',
                        'Tracking_started',
                        'POD_followup_received',
                        'POD_uploaded',
                        'delivery_confirmation',
                        'pickup_confirmed',
                        'arrival_confirmed',
                        'driver_response',
                        'call_transferred',
                        'transfer_reason',
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
                            
                            if (typeof value === 'boolean' || key === 'call_transferred' || key.toLowerCase().includes('received') || key.toLowerCase().includes('uploaded') || key.toLowerCase().includes('confirmed')) {
                                const boolValue = value === true || value === 'true' || value === 'Y' || value === 'yes';
                                displayValue = boolValue ? 'Yes' : 'No';
                                statusClass = boolValue ? 'status-success' : (key === 'call_transferred' ? 'status-info' : 'status-warning');
                            } else if (key === 'door number' && (value === 'None' || value === null || value === '')) {
                                displayValue = 'Not provided';
                                statusClass = 'status-warning';
                            } else if (value === 'None' || value === null || value === '') {
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
                            } else if (value === 'None' || value === null || value === '') {
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
                    
                    outputHTML += '</div>';
                    outputContent.innerHTML = outputHTML;
                } else if (metadata.output_schema_received || (metadata.custom_analysis_data && metadata.custom_analysis_data.output)) {
                    // We have schema received but no actual extracted data, or output in custom_analysis_data
                    let outputFromCustom = null;
                    
                    // Check if there's output in custom_analysis_data
                    if (metadata.custom_analysis_data && metadata.custom_analysis_data.output) {
                        try {
                            const customOutputData = JSON.parse(metadata.custom_analysis_data.output);
                            const isCustomSchema = customOutputData.hasOwnProperty('type') && customOutputData.hasOwnProperty('properties');
                            
                            if (!isCustomSchema) {
                                // This is actual data from custom_analysis_data
                                outputFromCustom = customOutputData;
                            }
                        } catch (e) {
                            console.log('Could not parse custom_analysis_data.output');
                        }
                    }
                    
                    if (outputFromCustom) {
                        // Display the data from custom_analysis_data
                        outputCard.style.display = 'block';
                        let outputHTML = '<div class="output-grid">';
                        
                        Object.entries(outputFromCustom).forEach(([key, value]) => {
                            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            let displayValue = value;
                            let statusClass = '';
                            
                            if (typeof value === 'boolean') {
                                displayValue = value ? 'Yes' : 'No';
                                statusClass = value ? 'status-success' : 'status-warning';
                            } else if (value === 'None' || value === null || value === '') {
                                displayValue = 'Not provided';
                                statusClass = 'status-warning';
                            }
                            
                            outputHTML += `
                                <div class="output-item ${statusClass}">
                                    <span class="output-label">${displayKey}</span>
                                    <span class="output-value">${this.escapeHtml(String(displayValue))}</span>
                                </div>
                            `;
                        });
                        
                        outputHTML += '</div>';
                        outputContent.innerHTML = outputHTML;
                    } else {
                        // Show schema received message
                        outputCard.style.display = 'block';
                        outputContent.innerHTML = `
                            <div class="no-output-data">
                                <i class="fas fa-exclamation-triangle" style="color: #f6ad55; font-size: 24px; margin-bottom: 12px;"></i>
                                <p style="color: #a0aec0; font-size: 14px; margin: 0;">Expected data fields defined but no values were extracted.</p>
                                <p style="color: #718096; font-size: 12px; margin: 8px 0 0 0;">The AI was configured to extract specific information but the call ended before data could be collected.</p>
                            </div>
                        `;
                    }
                } else {
                    // No output data available at all
                    outputCard.style.display = 'none';
                }
            } catch (error) {
                console.error('Error parsing output data:', error);
                outputCard.style.display = 'none';
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
    // Add a small delay to ensure all elements are rendered
    setTimeout(() => {
        const checkInPage = new CheckInPage();
        checkInPage.init();
    }, 100);
}); 