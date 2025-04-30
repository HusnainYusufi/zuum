import React, { useState, useEffect } from 'react';
import '../styles/StakeholderDashboard.css';

interface Stop {
  id: number;
  name: string;
  location: string;
  eta: string;
  cross_street: string;
  nearest_highway: string;
  is_delayed: boolean;
  delay_reason: string;
  expected_location: string;
  reported_location: string;
}

interface Notification {
  id: number;
  message: string;
  timestamp: string;
  read: boolean;
}

interface StakeholderDashboardProps {
  isDarkMode: boolean;
}

const StakeholderDashboard: React.FC<StakeholderDashboardProps> = ({ isDarkMode }) => {
  const [stops, setStops] = useState<Stop[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [selectedStop, setSelectedStop] = useState<Stop | null>(null);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  // Fetch all stops data
  useEffect(() => {
    const fetchStops = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/stops/details');
        if (!response.ok) {
          throw new Error('Failed to fetch stops');
        }
        const data = await response.json();
        setStops(data);
        if (data.length > 0) {
          setSelectedStop(data[0]);
        }
      } catch (error) {
        console.error('Error fetching stops:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStops();
    const interval = setInterval(fetchStops, 10000); // Poll every 10 seconds
    
    return () => clearInterval(interval);
  }, []);

  // Check for changes and create notifications
  useEffect(() => {
    const checkForChanges = () => {
      // This would ideally use WebSockets or Server-Sent Events in production
      stops.forEach(stop => {
        if (stop.is_delayed && !notifications.some(n => n.message.includes(`${stop.name} is delayed`))) {
          addNotification(`${stop.name} is delayed. Reason: ${stop.delay_reason || 'Not provided'}`);
        }
        
        if (stop.expected_location !== stop.reported_location && 
            !notifications.some(n => n.message.includes(`${stop.name} is off route`))) {
          addNotification(`${stop.name} is off route. Expected: ${stop.expected_location}, Reported: ${stop.reported_location}`);
        }
      });
    };
    
    checkForChanges();
  }, [stops]);

  // Count unread notifications
  useEffect(() => {
    setUnreadCount(notifications.filter(n => !n.read).length);
  }, [notifications]);

  const addNotification = (message: string) => {
    const newNotification: Notification = {
      id: Date.now(),
      message,
      timestamp: new Date().toLocaleString(),
      read: false
    };
    
    setNotifications(prev => [newNotification, ...prev]);
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  };

  const markAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, read: true } : n
    ));
  };

  if (loading) {
    return (
      <div className={`dashboard-container ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className="loading-spinner">Loading data...</div>
      </div>
    );
  }

  return (
    <div className={`dashboard-container ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="dashboard-header">
        <h1>Transit Stakeholder Dashboard</h1>
        <div className="notification-icon" onClick={() => setShowNotifications(!showNotifications)}>
          <span className="material-icons">notifications</span>
          {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
        </div>
      </div>

      {showNotifications && (
        <div className="notifications-panel">
          <div className="notifications-header">
            <h2>Notifications</h2>
            <button onClick={markAllAsRead}>Mark all as read</button>
          </div>
          <div className="notifications-list">
            {notifications.length === 0 ? (
              <p>No notifications</p>
            ) : (
              notifications.map(notification => (
                <div 
                  key={notification.id} 
                  className={`notification-item ${!notification.read ? 'unread' : ''}`}
                  onClick={() => markAsRead(notification.id)}
                >
                  <div className="notification-content">
                    <p>{notification.message}</p>
                    <span className="notification-time">{notification.timestamp}</span>
                  </div>
                  {!notification.read && <div className="unread-indicator"></div>}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <div className="stops-selector">
        {stops.map(stop => (
          <button 
            key={stop.id}
            className={`stop-button ${selectedStop?.id === stop.id ? 'selected' : ''}`}
            onClick={() => setSelectedStop(stop)}
          >
            {stop.name}
            {stop.is_delayed && <span className="delay-indicator">⚠️</span>}
          </button>
        ))}
      </div>

      {selectedStop && (
        <div className="stop-details">
          <h2>{selectedStop.name}</h2>
          
          <div className="detail-cards">
            <div className="detail-card">
              <h3>Location</h3>
              <div className="detail-item">
                <span className="detail-label">Expected:</span>
                <span className="detail-value">{selectedStop.expected_location}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Reported:</span>
                <span className="detail-value">{selectedStop.reported_location}</span>
              </div>
              <div className="detail-status">
                {selectedStop.expected_location === selectedStop.reported_location ? (
                  <span className="status-ok">On Track</span>
                ) : (
                  <span className="status-warning">Off Route</span>
                )}
              </div>
            </div>

            <div className="detail-card">
              <h3>Schedule</h3>
              <div className="detail-item">
                <span className="detail-label">ETA:</span>
                <span className="detail-value">{selectedStop.eta}</span>
              </div>
              <div className="detail-status">
                {selectedStop.is_delayed ? (
                  <span className="status-warning">Delayed</span>
                ) : (
                  <span className="status-ok">On Time</span>
                )}
              </div>
              {selectedStop.is_delayed && (
                <div className="detail-item">
                  <span className="detail-label">Reason:</span>
                  <span className="detail-value">{selectedStop.delay_reason || 'Not provided'}</span>
                </div>
              )}
            </div>

            <div className="detail-card">
              <h3>Navigation</h3>
              <div className="detail-item">
                <span className="detail-label">Cross Street:</span>
                <span className="detail-value">{selectedStop.cross_street || 'Not provided'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Nearest Highway:</span>
                <span className="detail-value">{selectedStop.nearest_highway || 'Not provided'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StakeholderDashboard; 