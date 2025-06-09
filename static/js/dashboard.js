/**
 * Transit Stakeholder Dashboard JavaScript
 * Replicates the functionality of the React StakeholderDashboard component
 */

class StakeholderDashboard {
    constructor() {
        // Backend URL - adjust this based on your setup
        this.backendUrl = window.location.origin;
        
        // State management
        this.stops = [];
        this.selectedStop = null;
        this.notifications = [];
        this.checkIns = [];
        this.journeyState = 0;
        this.isDarkMode = true; // Set dark mode as default
        this.isMobile = window.innerWidth <= 768;
        this.isRefreshing = false;
        this.showNotifications = false;
        this.lastNotificationTime = Date.now();
        
        // WebSocket connection for real-time updates
        this.ws = null;
        
        // Initialize dashboard
        this.init();
    }

    async init() {
        // Apply dark mode by default
        document.getElementById('app').classList.add('dark-mode');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadInitialData();
        
        // Set up WebSocket connection for real-time updates
        this.setupWebSocket();
        
        // Hide loading spinner
        this.hideLoadingSpinner();
    }

    setupWebSocket() {
        // Determine WebSocket URL based on current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connection established');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket connection closed. Attempting to reconnect...');
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.setupWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Failed to establish WebSocket connection:', error);
        }
    }

    handleWebSocketMessage(data) {
        console.log('Received WebSocket message:', data);
        
        switch (data.type) {
            case 'stop_update':
                this.handleStopUpdate(data.data);
                break;
            case 'check_in_update':
                this.handleCheckInUpdate(data.data);
                break;
            case 'journey_state_update':
                this.handleJourneyStateUpdate(data.data);
                break;
            case 'notification':
                this.handleNotification(data.data);
                break;
            default:
                console.warn('Unknown WebSocket message type:', data.type);
        }
    }

    handleStopUpdate(stopData) {
        // Update the stop in our local state
        const stopIndex = this.stops.findIndex(s => s.id === stopData.id);
        if (stopIndex !== -1) {
            this.stops[stopIndex] = stopData;
            this.renderStopsSelector();
            
            // If this is the selected stop, update the details
            if (this.selectedStop && this.selectedStop.id === stopData.id) {
                this.selectedStop = stopData;
                this.renderStopDetails();
            }
        } else {
            // New stop, add it to the list
            this.stops.push(stopData);
            this.renderStopsSelector();
        }
        
        // Check if we need to add notifications based on stop conditions
        if (stopData.is_delayed) {
            this.addNotification(
                `${stopData.name} is delayed. Reason: ${stopData.delay_reason || 'Not provided'}`,
                stopData.id,
                'warning'
            );
        }
        
        if (stopData.expected_location !== stopData.reported_location) {
            this.addNotification(
                `${stopData.name} is off route. Expected: ${stopData.expected_location}, Reported: ${stopData.reported_location}`,
                stopData.id,
                'warning'
            );
        }
    }

    handleCheckInUpdate(checkInData) {
        // Add or update check-in
        const checkInIndex = this.checkIns.findIndex(c => c.id === checkInData.id);
        if (checkInIndex !== -1) {
            this.checkIns[checkInIndex] = checkInData;
        } else {
            // Add new check-in at the beginning
            this.checkIns.unshift(checkInData);
        }
        this.renderCheckIns();
        
        // Add notification for new check-in
        this.addNotification(
            `New check-in #${checkInData.id} received${checkInData.Issue_Flagged ? ' - Issue Flagged!' : ''}`,
            checkInData.stop_id,
            checkInData.Issue_Flagged ? 'warning' : 'info'
        );
    }

    handleJourneyStateUpdate(journeyStateData) {
        this.journeyState = journeyStateData.state;
        this.updateDeliveryTimeline();
        
        // Add notification for journey state change
        const states = ['Confirmed', 'In transit', 'Delivered'];
        if (journeyStateData.state < states.length) {
            this.addNotification(
                `Journey status updated: ${states[journeyStateData.state]}`,
                null,
                'info'
            );
        }
    }

    handleNotification(notificationData) {
        this.addNotification(
            notificationData.message,
            notificationData.stop_id,
            notificationData.severity || 'info'
        );
    }

    setupEventListeners() {
        // Refresh button
        const refreshButton = document.getElementById('refresh-button');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                this.refreshAllData();
            });
        }

        // Notification icon
        const notificationIcon = document.getElementById('notification-icon');
        if (notificationIcon) {
            notificationIcon.addEventListener('click', () => {
                this.toggleNotifications();
            });
        }

        // Notification panel controls
        const notificationsClose = document.getElementById('notifications-close');
        if (notificationsClose) {
            notificationsClose.addEventListener('click', () => {
                this.hideNotifications();
            });
        }

        const markAllRead = document.getElementById('mark-all-read');
        if (markAllRead) {
            markAllRead.addEventListener('click', () => {
                this.markAllNotificationsAsRead();
            });
        }

        // Window resize handler
        window.addEventListener('resize', () => {
            this.isMobile = window.innerWidth <= 768;
            this.updateMobileLayout();
        });

        // Click outside notifications handler
        document.addEventListener('click', (event) => {
            if (this.isMobile && this.showNotifications) {
                const target = event.target;
                if (!target.closest('.notifications-panel') && !target.closest('.notification-icon')) {
                    this.hideNotifications();
                }
            }
        });
    }

    async loadInitialData() {
        try {
            // Load all data in parallel
            await Promise.all([
                this.fetchStops(),
                this.fetchJourneyState(),
                this.fetchCheckIns(),
                this.fetchNotifications()
            ]);

            // Select first stop by default
            if (this.stops.length > 0 && !this.selectedStop) {
                this.selectStop(this.stops[0]);
            }
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    async fetchStops() {
        try {
            const response = await fetch(`${this.backendUrl}/stops/details`, {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch stops');
            }
            
            this.stops = await response.json();
            this.renderStopsSelector();
        } catch (error) {
            console.error('Error fetching stops:', error);
            throw error;
        }
    }

    async fetchJourneyState() {
        try {
            const response = await fetch(`${this.backendUrl}/journey_state`, {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch journey state');
            }
            
            this.journeyState = await response.json();
            this.updateDeliveryTimeline();
        } catch (error) {
            console.error('Error fetching journey state:', error);
        }
    }

    async fetchCheckIns() {
        try {
            const response = await fetch(`${this.backendUrl}/check-ins`, {
                headers: {
                    'ngrok-skip-browser-warning': 'true'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch check-ins');
            }
            
            this.checkIns = await response.json();
            this.renderCheckIns();
        } catch (error) {
            console.error('Error fetching check-ins:', error);
        }
    }

    async fetchNotifications() {
        try {
            // Check for notifications based on stop conditions
            this.stops.forEach(stop => {
                if (stop.is_delayed && !this.notifications.some(n => n.message.includes(`${stop.name} is delayed`))) {
                    this.addNotification(
                        `${stop.name} is delayed. Reason: ${stop.delay_reason || 'Not provided'}`,
                        stop.id,
                        'warning'
                    );
                }
                
                if (stop.expected_location !== stop.reported_location && 
                    !this.notifications.some(n => n.message.includes(`${stop.name} is off route`))) {
                    this.addNotification(
                        `${stop.name} is off route. Expected: ${stop.expected_location}, Reported: ${stop.reported_location}`,
                        stop.id,
                        'warning'
                    );
                }
            });
            
            // Try to fetch active notifications from backend
            try {
                const response = await fetch(`${this.backendUrl}/conversation/active_notifications`, {
                    headers: {
                        'ngrok-skip-browser-warning': 'true'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data && data.notifications && Array.isArray(data.notifications)) {
                        data.notifications.forEach(notif => {
                            if (!this.notifications.some(n => n.message === notif.message)) {
                                this.addNotification(notif.message, notif.stop_id, notif.severity || 'warning');
                            }
                        });
                    }
                }
            } catch (err) {
                // Fallback if endpoint doesn't exist
                console.log('Active notifications endpoint not available');
            }
            
            this.renderNotifications();
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }

    renderStopsSelector() {
        const container = document.getElementById('stops-selector');
        container.innerHTML = '';
        
        this.stops.forEach(stop => {
            const button = document.createElement('button');
            button.className = `stop-button ${this.selectedStop?.id === stop.id ? 'selected' : ''}`;
            button.innerHTML = `
                ${stop.name}
                ${stop.is_delayed ? '<i class="fas fa-exclamation-triangle delay-indicator"></i>' : ''}
            `;
            button.addEventListener('click', () => this.selectStop(stop));
            container.appendChild(button);
        });
    }

    selectStop(stop) {
        this.selectedStop = stop;
        this.renderStopsSelector(); // Re-render to update selection
        this.renderStopDetails();
        document.getElementById('stop-details').style.display = 'block';
    }

    renderStopDetails() {
        if (!this.selectedStop) return;
        
        const stop = this.selectedStop;
        
        // Update stop name
        document.getElementById('selected-stop-name').textContent = stop.name || 'Unknown Stop';
        
        // Update location status with null safety
        const expectedLoc = stop.expected_location || stop.location || '';
        const reportedLoc = stop.reported_location || stop.location || '';
        const isOnTrack = expectedLoc.toLowerCase().split(',')[0]
            .includes(reportedLoc.toLowerCase().split(',')[0]);
        
        const locationStatus = document.getElementById('location-status');
        if (isOnTrack) {
            locationStatus.innerHTML = '<i class="fas fa-check"></i> On Track';
            locationStatus.className = 'status-ok';
        } else {
            locationStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Off Route';
            locationStatus.className = 'status-warning';
        }
        
        // Update location details
        document.getElementById('expected-location').textContent = expectedLoc || 'Not Available';
        document.getElementById('current-location').textContent = reportedLoc || 'Not Available';
        document.getElementById('highway-info').textContent = stop.nearest_highway || 'Not Available';
        
        // Update schedule status
        const scheduleStatus = document.getElementById('schedule-status');
        const delayInfo = document.getElementById('delay-info');
        const timingIndicator = document.getElementById('timing-indicator');
        
        if (stop.is_delayed) {
            scheduleStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Delayed';
            scheduleStatus.className = 'status-warning';
            delayInfo.style.display = 'flex';
            document.getElementById('delay-reason').textContent = stop.delay_reason || 'Not specified';
            
            timingIndicator.className = 'delay-indicator-visual';
            timingIndicator.innerHTML = '<span class="delay-time">+15 min</span>';
        } else {
            scheduleStatus.innerHTML = '<i class="fas fa-check"></i> On Time';
            scheduleStatus.className = 'status-ok';
            delayInfo.style.display = 'none';
            
            timingIndicator.className = 'ontime-indicator-visual';
            timingIndicator.innerHTML = '<span class="ontime-text">On Schedule</span>';
        }
        
        // Update ETA
        document.getElementById('eta-value').textContent = this.formatETA(stop.eta);
    }

    renderCheckIns() {
        const container = document.getElementById('check-ins-container');
        
        if (this.checkIns.length === 0) {
            container.innerHTML = '<p class="no-check-ins">No check-ins available.</p>';
            return;
        }
        
        container.innerHTML = '';
        
        this.checkIns.forEach(checkIn => {
            const checkInCard = document.createElement('div');
            checkInCard.className = 'check-in-card';
            
            const timestamp = checkIn.AI_Timestamp ? 
                this.formatCheckInTimestamp(checkIn.AI_Timestamp) : '';
            
            checkInCard.innerHTML = `
                <div class="check-in-header">
                    <div class="check-in-id-wrapper">
                        <i class="fas fa-clipboard-check check-in-icon"></i>
                        <span class="check-in-id clickable-link" onclick="window.location.href='/checkin/${checkIn.id}'">
                            CHECK-IN #${checkIn.id.toString().padStart(2, '0')}${timestamp ? ` | ${timestamp}` : ''}
                        </span>
                    </div>
                    <div class="check-in-status">
                        ${checkIn.Issue_Flagged ? '<span class="status-badge issue-flagged" title="Issue Flagged">⚠️</span>' : ''}
                        ${checkIn.Requires_Human_Review ? '<span class="status-badge requires-review" title="Requires Review">👁️</span>' : ''}
                    </div>
                </div>
            `;
            
            container.appendChild(checkInCard);
        });
    }

    renderNotifications() {
        const badge = document.getElementById('notification-badge');
        const unreadCount = this.notifications.filter(n => !n.read).length;
        
        if (unreadCount > 0) {
            badge.style.display = 'block';
            badge.textContent = unreadCount;
        } else {
            badge.style.display = 'none';
        }
        
        const container = document.getElementById('notifications-list');
        
        if (this.notifications.length === 0) {
            container.innerHTML = '<p class="no-notifications">No notifications</p>';
            return;
        }
        
        container.innerHTML = '';
        
        this.notifications.forEach(notification => {
            const notificationItem = document.createElement('div');
            notificationItem.className = `notification-item ${!notification.read ? 'unread' : ''} ${notification.severity || ''}`;
            notificationItem.addEventListener('click', () => this.markNotificationAsRead(notification.id));
            
            notificationItem.innerHTML = `
                <div class="notification-content">
                    <p>${notification.message}</p>
                    <span class="notification-time">${notification.timestamp}</span>
                </div>
                ${!notification.read ? '<div class="unread-indicator"></div>' : ''}
            `;
            
            container.appendChild(notificationItem);
        });
    }

    updateDeliveryTimeline() {
        const steps = document.querySelectorAll('.timeline-step');
        const connectors = document.querySelectorAll('.timeline-connector');
        
        steps.forEach((step, index) => {
            if (this.journeyState >= index) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
        
        connectors.forEach((connector, index) => {
            if (this.journeyState > index) {
                connector.classList.add('active');
            } else {
                connector.classList.remove('active');
            }
        });
    }

    // Utility methods
    formatETA(etaString) {
        try {
            const date = new Date(etaString);
            if (isNaN(date.getTime())) {
                return etaString;
            }
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        } catch (error) {
            return etaString;
        }
    }

    formatCheckInTimestamp(timestamp) {
        try {
            const date = new Date(timestamp);
            const dateStr = date.toLocaleDateString('en-US', { 
                month: '2-digit', 
                day: '2-digit', 
                year: 'numeric' 
            }).replace(/\//g, '/');
            const timeStr = date.toLocaleTimeString('en-US', { 
                hour: 'numeric', 
                minute: '2-digit', 
                second: '2-digit', 
                hour12: true 
            });
            return `${dateStr}, ${timeStr}`;
        } catch (error) {
            return timestamp;
        }
    }

    addNotification(message, stopId, severity = 'info') {
        const notification = {
            id: Date.now(),
            message,
            timestamp: new Date().toLocaleString(),
            read: false,
            stop_id: stopId,
            severity
        };
        
        // Avoid duplicates
        if (this.notifications.some(n => n.message === message)) {
            return;
        }
        
        this.notifications.unshift(notification);
        this.renderNotifications();
    }

    markNotificationAsRead(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification) {
            notification.read = true;
            this.renderNotifications();
        }
    }

    markAllNotificationsAsRead() {
        this.notifications.forEach(n => n.read = true);
        this.renderNotifications();
    }

    toggleNotifications() {
        this.showNotifications = !this.showNotifications;
        const panel = document.getElementById('notifications-panel');
        panel.style.display = this.showNotifications ? 'block' : 'none';
    }

    hideNotifications() {
        this.showNotifications = false;
        document.getElementById('notifications-panel').style.display = 'none';
    }

    async refreshAllData() {
        if (this.isRefreshing) return;
        
        this.isRefreshing = true;
        const refreshButton = document.getElementById('refresh-button');
        refreshButton.classList.add('refreshing');
        refreshButton.disabled = true;
        
        try {
            await Promise.all([
                this.fetchStops(),
                this.fetchJourneyState(),
                this.fetchCheckIns(),
                this.fetchNotifications()
            ]);
            
            // Update selected stop if it still exists
            if (this.selectedStop) {
                const updatedStop = this.stops.find(s => s.id === this.selectedStop.id);
                if (updatedStop) {
                    this.selectedStop = updatedStop;
                    this.renderStopDetails();
                } else if (this.stops.length > 0) {
                    this.selectStop(this.stops[0]);
                }
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showError('Failed to refresh data');
        } finally {
            this.isRefreshing = false;
            refreshButton.classList.remove('refreshing');
            refreshButton.disabled = false;
        }
    }

    updateMobileLayout() {
        const headerTitle = document.querySelector('.header-title');
        const refreshText = document.querySelector('.refresh-text');
        
        if (this.isMobile) {
            headerTitle.textContent = 'Transit Dashboard';
            refreshText.style.display = 'none';
        } else {
            headerTitle.textContent = 'Transit Stakeholder Dashboard';
            refreshText.style.display = 'inline';
        }
    }

    hideLoadingSpinner() {
        document.getElementById('loading-spinner').style.display = 'none';
    }

    showError(message) {
        // Simple error display - could be enhanced with a proper notification system
        console.error(message);
        this.addNotification(message, null, 'error');
    }

    // Cleanup method
    destroy() {
        // Close WebSocket connection
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new StakeholderDashboard();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
}); 