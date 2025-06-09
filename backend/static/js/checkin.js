class CheckInPage {
    constructor() {
        this.checkIn = null;
        this.checkInId = this.getCheckInIdFromUrl();
        this.isDarkMode = localStorage.getItem('darkMode') === 'true';
        this.init();
    }

    getCheckInIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    async init() {
        // Apply dark mode if enabled
        if (this.isDarkMode) {
            document.querySelector('.App').classList.add('dark-mode');
            document.querySelector('.transcript-page').classList.add('dark-mode');
        }

        // Show loading spinner
        this.showLoading();

        // Fetch check-in data
        await this.fetchCheckIn();

        // Hide loading spinner
        this.hideLoading();

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

        // Render metadata if available
        if (this.checkIn.check_in_metadata) {
            this.renderMetadata();
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

    renderMetadata() {
        const metadataCard = document.getElementById('metadata-card');
        const metadataContent = document.getElementById('metadata-content');
        
        if (metadataCard && metadataContent) {
            metadataCard.style.display = 'block';
            
            try {
                const metadata = JSON.parse(this.checkIn.check_in_metadata);
                let metadataHTML = '<div class="metadata-grid">';
                
                Object.entries(metadata).forEach(([key, value]) => {
                    metadataHTML += `
                        <div class="metadata-item">
                            <span class="metadata-label">${key.replace(/_/g, ' ')}:</span>
                            <span class="metadata-value">${this.escapeHtml(String(value))}</span>
                        </div>
                    `;
                });
                
                metadataHTML += '</div>';
                metadataContent.innerHTML = metadataHTML;
            } catch {
                metadataContent.innerHTML = `<p>${this.escapeHtml(this.checkIn.check_in_metadata)}</p>`;
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