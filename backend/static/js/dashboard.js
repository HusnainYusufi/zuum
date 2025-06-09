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
        this.isDarkMode = false;
        this.isMobile = window.innerWidth <= 768;
        this.isRefreshing = false;
        this.showNotifications = false;
        this.lastNotificationTime = Date.now();
        
        // Polling intervals
        this.notificationPoller = null;
        this.journeyStatePoller = null;
        
        // Initialize dashboard
        this.init();
    }

    async init() {
        // Load dark mode preference first
        this.loadDarkModePreference();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadInitialData();
        
        // Set up polling
        this.setupPolling();
        
        // Hide loading spinner
        this.hideLoadingSpinner();
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

        // Dark mode toggle
        const darkModeToggle = document.getElementById('dark-mode-toggle');
        if (darkModeToggle) {
            console.log('Setting up dark mode toggle, method exists:', typeof this.toggleDarkMode);
            darkModeToggle.addEventListener('click', () => {
                console.log('Dark mode button clicked, calling toggleDarkMode');
                if (typeof this.toggleDarkMode === 'function') {
                    this.toggleDarkMode();
                } else {
                    console.error('toggleDarkMode is not a function:', typeof this.toggleDarkMode);
                }
            });
        } else {
            console.warn('Dark mode toggle button not found in DOM');
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
            const response = await fetch(`${this.backendUrl}/ui/journey_state`, {
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

    setupPolling() {
        // Poll for notifications every 10 seconds
        this.notificationPoller = setInterval(() => {
            this.fetchNotifications();
        }, 10000);
        
        // Poll for journey state every 5 seconds
        this.journeyStatePoller = setInterval(() => {
            this.fetchJourneyState();
        }, 5000);
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
                        <span class="check-in-id clickable-link" onclick="window.location.href='/transcript/${checkIn.id}'">
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

    toggleDarkMode() {
        console.log('toggleDarkMode called, current isDarkMode:', this.isDarkMode);
        this.isDarkMode = !this.isDarkMode;
        const appContainer = document.getElementById('app');
        const darkToggleButton = document.getElementById('dark-mode-toggle');
        
        if (!appContainer) {
            console.error('App container not found');
            return;
        }
        
        if (!darkToggleButton) {
            console.error('Dark toggle button not found');
            return;
        }
        
        if (this.isDarkMode) {
            appContainer.classList.add('dark-mode');
            darkToggleButton.innerHTML = '☀️ Light Mode';
            localStorage.setItem('darkMode', 'true');
            console.log('Switched to dark mode');
        } else {
            appContainer.classList.remove('dark-mode');
            darkToggleButton.innerHTML = '🌙 Dark Mode';
            localStorage.setItem('darkMode', 'false');
            console.log('Switched to light mode');
        }
    }

    loadDarkModePreference() {
        const savedMode = localStorage.getItem('darkMode');
        if (savedMode === 'true') {
            this.isDarkMode = true;
            document.getElementById('app').classList.add('dark-mode');
            document.getElementById('dark-mode-toggle').innerHTML = '☀️ Light Mode';
        }
    }

    // Cleanup method
    destroy() {
        if (this.notificationPoller) {
            clearInterval(this.notificationPoller);
        }
        if (this.journeyStatePoller) {
            clearInterval(this.journeyStatePoller);
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