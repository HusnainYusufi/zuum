class CheckInPage {
    constructor() {
        this.checkIn = null;
        this.checkInId = this.getCheckInIdFromUrl();
        this.isDarkMode = true;
        this.websocket = null;
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

        // Connect to WebSocket for real-time updates
        this.connectWebSocket();

        // Fetch check-in data first to determine current state
        await this.fetchCheckIn();
        
        // Debug logging
        console.log('Check-in data loaded:', {
            id: this.checkIn?.id,
            call_status: this.checkIn?.call_status,
            has_AI_Response: !!this.checkIn?.AI_Response_Summary,
            AI_Response_length: this.checkIn?.AI_Response_Summary?.length || 0,
            call_transcript: !!this.checkIn?.call_transcript,
            user_picked_up: this.checkIn?.user_picked_up
        });

        // Hide loading spinner first
        this.hideLoading();

        // PRIORITY 1: If we have AI response or transcript, render content immediately
        if (this.checkIn && (this.checkIn.AI_Response_Summary || this.checkIn.call_transcript)) {
            console.log('Rendering content immediately - analysis data available');
            this.hideCallProgress();
            this.render();
            return;
        }

        // PRIORITY 2: If call status is analyzed, render content
        if (this.checkIn && this.checkIn.call_status === 'analyzed') {
            console.log('Rendering content - call status is analyzed');
            this.hideCallProgress();
            this.render();
            return;
        }

        // PRIORITY 3: If call is completed but no analysis data, check for additional status
        if (this.checkIn && this.checkIn.call_status === 'completed') {
            console.log('Call completed - checking if transcript/analysis is available');
            
            // Give it a moment to check for recent updates
            setTimeout(async () => {
                await this.fetchCheckIn();
                if (this.checkIn && (this.checkIn.AI_Response_Summary || this.checkIn.call_transcript)) {
                    console.log('Found analysis data after refresh - rendering content');
                    this.hideCallProgress();
                    this.render();
                } else {
                    console.log('No analysis data found - showing basic content');
                    this.hideCallProgress();
                    this.render(); // Render basic content even without full analysis
                }
            }, 1000);
            
            // For now, show call progress while we check
            this.showCallProgress();
            return;
        }

        // PRIORITY 4: If call is in progress, show progress overlay and poll
        if (this.checkIn && this.checkIn.call_status === 'in_progress') {
            console.log('Call in progress - showing progress overlay');
            this.showCallProgress();
            
            // Start polling for updates
            const callStatus = await this.checkCallStatus();
            if (callStatus === 'in_progress') {
                await this.pollCallStatus();
            }
            return;
        }

        // PRIORITY 5: Default case - render whatever we have
        if (this.checkIn) {
            console.log('Rendering available content - default case');
            this.hideCallProgress();
            this.render();
        } else {
            console.log('No check-in data available');
            this.hideCallProgress();
            this.renderNoData();
        }
    }

    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/notifications`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = (event) => {
                console.log('WebSocket connected for check-in page');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const notification = JSON.parse(event.data);
                    console.log('Received notification:', notification);
                    
                    // Handle different types of notifications
                    if (notification.type === 'check_in_update') {
                        this.handleCheckInUpdate(notification.data);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket connection closed. Attempting to reconnect...');
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            // Send periodic ping to keep connection alive
            setInterval(() => {
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.websocket.send('ping');
                }
            }, 30000); // Send ping every 30 seconds
            
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            // Retry connection after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        }
    }

    handleCheckInUpdate(checkInData) {
        // Only handle updates for this specific check-in
        if (checkInData.id != this.checkInId) {
            return;
        }

        console.log('Check-in update received for current check-in:', checkInData);
        
        // Store previous state
        const wasActive = this.checkIn ? (this.checkIn.call_status === 'in_progress' || this.checkIn.call_status === 'completed') && !this.checkIn.AI_Response_Summary : false;
        
        // Show appropriate notification based on the update type
        if (checkInData.call_trasfered || checkInData.call_status === 'transferred') {
            this.showNotification({
                icon: 'fas fa-phone-alt',
                title: 'Call transferred',
                subtitle: 'Call successfully transferred to broker',
                background: 'linear-gradient(135deg, #48bb78, #68d391)',
                shadowColor: 'rgba(72, 187, 120, 0.3)'
            });
        } else if (checkInData.call_status === 'analyzed' || checkInData.AI_Response_Summary || checkInData.call_transcript) {
            // Call has been analyzed or has content
            this.showNotification({
                icon: 'fas fa-brain',
                title: 'Call analysis complete',
                subtitle: 'AI analysis results are now available',
                background: 'linear-gradient(135deg, #4299e1, #63b3ed)',
                shadowColor: 'rgba(66, 153, 225, 0.3)'
            });
            
            // Hide progress and show main content immediately
            this.hideCallProgress();
            this.render(); // Render immediately, no delay
        } else if ((checkInData.call_status === 'in_progress' || checkInData.call_status === 'completed') && !checkInData.AI_Response_Summary) {
            // Call was just made or in progress
            this.showNotification({
                icon: 'fas fa-phone',
                title: 'Call in progress',
                subtitle: 'Please wait while the call is being processed',
                background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                shadowColor: 'rgba(59, 130, 246, 0.3)'
            });
            
            // Show call progress if not already showing
            if (!wasActive) {
                this.showCallProgress();
            }
        } else if (checkInData.call_status === 'completed') {
            // Call is completed - always render content
            this.showNotification({
                icon: 'fas fa-check-circle',
                title: 'Call completed',
                subtitle: 'Call processing finished',
                background: 'linear-gradient(135deg, #10b981, #34d399)',
                shadowColor: 'rgba(16, 185, 129, 0.3)'
            });
            
            // Always render content for completed calls
            this.hideCallProgress();
            this.render();
        }
        
        // Refresh the check-in data silently
        this.refreshCheckInSilently();
    }

    async refreshCheckInSilently() {
        try {
            console.log('Refreshing check-in data silently...');
            const oldCheckIn = this.checkIn;
            await this.fetchCheckIn();
            
            // Check for state transitions
            if (oldCheckIn && this.checkIn) {
                const wasActive = (oldCheckIn.call_status === 'in_progress' || oldCheckIn.call_status === 'completed') && !oldCheckIn.AI_Response_Summary;
                const isActive = (this.checkIn.call_status === 'in_progress' || this.checkIn.call_status === 'completed') && !this.checkIn.AI_Response_Summary;
                const isAnalyzed = this.checkIn.call_status === 'analyzed' || this.checkIn.AI_Response_Summary;
                
                // If call went from active to analyzed with AI response, transition to main view
                if (wasActive && isAnalyzed) {
                    console.log('Call analysis completed, transitioning to main view');
                    setTimeout(() => {
                        this.hideCallProgress();
                        this.render();
                    }, 1000);
                    return;
                }
                
                // If call became active, show progress view
                if (!wasActive && isActive) {
                    console.log('Call became active, showing progress view');
                    this.showCallProgress();
                    return;
                }
            }
            
            // Only re-render if the page is currently showing content (analyzed state)
            if (this.checkIn && (this.checkIn.call_status === 'analyzed' || this.checkIn.AI_Response_Summary)) {
                this.render();
                console.log('Check-in data refreshed successfully');
            }
        } catch (error) {
            console.error('Error refreshing check-in data:', error);
        }
    }

    showNotification({ icon, title, subtitle, background, shadowColor }) {
        // Create a notification
        const notification = document.createElement('div');
        notification.className = 'update-notification';
        notification.innerHTML = `
            <i class="${icon}"></i>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                ${subtitle ? `<div class="notification-subtitle">${subtitle}</div>` : ''}
            </div>
        `;
        
        // Add styling for the notification
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${background};
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px ${shadowColor}, 0 4px 12px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
            font-weight: 500;
            animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            min-width: 280px;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        `;
        
        // Add CSS animation if not already added
        if (!document.querySelector('#notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOutRight {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
                .notification-content {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                .notification-title {
                    font-weight: 600;
                    font-size: 14px;
                }
                .notification-subtitle {
                    font-weight: 400;
                    font-size: 12px;
                    opacity: 0.9;
                }
                .update-notification i {
                    font-size: 18px;
                    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
                    animation: pulse 2s ease-in-out infinite;
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(notification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 400);
        }, 5000);
        
        // Allow clicking to dismiss
        notification.addEventListener('click', () => {
            notification.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 400);
        });
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
        const maxAttempts = 30; // Poll for up to 2.5 minutes (30 attempts * 5 seconds)
        let attempts = 0;

        console.log('Starting polling for call status updates...');

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds (faster polling)
            attempts++;

            console.log(`Poll attempt ${attempts}/${maxAttempts}`);

            // Fetch fresh data each time
            await this.fetchCheckIn();
            
            // Stop immediately if we have any meaningful content
            if (this.checkIn && (this.checkIn.AI_Response_Summary || this.checkIn.call_transcript || this.checkIn.call_status === 'analyzed' || this.checkIn.call_status === 'completed')) {
                console.log('Content found during polling - stopping and rendering:', {
                    has_AI_Response: !!this.checkIn.AI_Response_Summary,
                    has_transcript: !!this.checkIn.call_transcript,
                    call_status: this.checkIn.call_status
                });
                this.hideCallProgress();
                this.render();
                return;
            }

            // Check external call status
            const status = await this.checkCallStatus();
            console.log(`External call status: ${status}`);
            
            if (status === 'completed' || status === 'error' || status === 'no_call') {
                console.log('Call status indicates completion or error - stopping polling');
                break;
            }
            
            // Continue polling if status is still 'in_progress'
        }

        console.log('Polling completed - rendering final content');
        
        // Always render content at the end, regardless of what we have
        this.hideCallProgress();
        if (this.checkIn) {
            this.render();
        } else {
            this.renderNoData();
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
                console.log("check-in data", this.checkIn);
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
        // Use call_status to determine if call is active
        const isCallActive = this.checkIn.call_status === 'in_progress';
        const callStatusText = this.getCallStatusText(this.checkIn.call_status);

        let statusHTML = '';

        // Extract call direction from tags
        let callDirectionSymbol = '';
        if (this.checkIn.Tags) {
            try {
                // Parse the JSON string into an actual array
                const tagsArray = JSON.parse(this.checkIn.Tags);
                console.log('Parsed tags:', tagsArray);  // Debug log
                
                const callDirection = tagsArray[1];  // Get second element
                console.log('Call direction:', callDirection);  // Debug log
                
                if (callDirection && callDirection.toLowerCase() === 'inbound') {
                    console.log('inbound');
                    callDirectionSymbol = '<span class="call-direction-symbol inbound"><i class="fas fa-phone"></i><i class="fas fa-long-arrow-alt-down"></i></span>';
                } else if (callDirection && callDirection.toLowerCase() === 'outbound') {
                    console.log('outbound');
                    callDirectionSymbol = '<span class="call-direction-symbol outbound"><i class="fas fa-phone"></i><i class="fas fa-long-arrow-alt-up"></i></span>';
                }
            } catch (error) {
                console.error('Error parsing Tags:', error);
            }
        }

        // Phone Pickup Status
        const userPickedUp = this.checkIn.user_picked_up;
        const didNotPickUp = (userPickedUp === false || userPickedUp === 'false' || userPickedUp === 'False');
        const didPickUp = (userPickedUp === true || userPickedUp === 'true' || userPickedUp === 'True');
        statusHTML += `
            <div class="info-item">
                <span class="info-label">
                    ${callDirectionSymbol}
                    <i class="fas ${didNotPickUp ? 'fa-phone-slash' : 'fa-phone'}" style="margin-right: 6px; color: ${didNotPickUp ? '#fc8181' : '#68d391'};"></i>
                    Phone Pickup:
                </span>
                <span class="info-value ${didNotPickUp ? 'status-flagged' : 'status-completed'}">${didNotPickUp ? 'No Answer' : didPickUp ? 'Answered' : 'Unknown'}</span>
            </div>
        `;

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

        // Call Status (using actual call_status from database)
        statusHTML += `
            <div class="info-item">
                <span class="info-label">Call Status:</span>
                <span class="info-value ${this.getCallStatusClass(this.checkIn.call_status)}">${callStatusText}</span>
            </div>
        `;

        statusContainer.innerHTML = statusHTML;
    }

    getCallStatusText(callStatus) {
        switch (callStatus) {
            case 'in_progress':
                return 'Active';
            case 'completed':
                return 'Completed';
            case 'analyzed':
                return 'Analyzed';
            case 'transferred':
                return 'Transferred';
            default:
                return callStatus ? callStatus.charAt(0).toUpperCase() + callStatus.slice(1) : 'Unknown';
        }
    }

    getCallStatusClass(callStatus) {
        switch (callStatus) {
            case 'in_progress':
                return 'status-active';
            case 'completed':
            case 'analyzed':
                return 'status-completed';
            case 'transferred':
                return 'status-transferred';
            default:
                return 'status-info';
        }
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
        
        // Clean up WebSocket connection when page unloads
        window.addEventListener('beforeunload', () => {
            if (checkInPage.websocket) {
                checkInPage.websocket.close();
            }
        });
    }, 100);
}); 