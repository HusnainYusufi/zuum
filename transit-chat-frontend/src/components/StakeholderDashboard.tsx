import React, { useState, useEffect } from 'react';
import '../styles/StakeholderDashboard.css';
import { FaBell, FaMapMarkerAlt, FaClock, FaRoute, FaExclamationTriangle, FaCheck, FaRoad, FaSync, FaLocationArrow, FaCompass } from 'react-icons/fa';
import { MdWarning, MdLocationOn, MdTimeline } from 'react-icons/md';

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
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Format ETA to human readable form with 12-hour clock
  const formatETA = (etaString: string): string => {
    try {
      const date = new Date(etaString);
      // Check if date is valid
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
      // If any error occurs, return the original string
      return etaString;
    }
  };

  // Fetch stops function - not wrapped in useCallback to avoid dependency cycles
  const fetchStops = async () => {
    try {
      if (!loading) setIsRefreshing(true);
      const response = await fetch('http://localhost:8000/stops/details');
      if (!response.ok) {
        throw new Error('Failed to fetch stops');
      }
      const data = await response.json();
      setStops(data);
      
      // Update selected stop if needed
      if (data.length > 0) {
        if (!selectedStop) {
          setSelectedStop(data[0]);
        } else {
          // If we already have a selected stop, find and update it with fresh data
          const updatedStop = data.find((stop: Stop) => stop.id === selectedStop.id);
          if (updatedStop) {
            setSelectedStop(updatedStop);
          } else {
            // If the previously selected stop no longer exists, select the first one
            setSelectedStop(data[0]);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching stops:', error);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  // Fetch all stops data only on initial load
  useEffect(() => {
    fetchStops();
    // Empty dependency array means this effect runs only once on mount
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
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`dashboard-container ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="dashboard-header">
        <h1><FaRoute className="header-icon" /> Transit Stakeholder Dashboard</h1>
        <div className="header-actions">
          <button 
            className={`refresh-button ${isRefreshing ? 'refreshing' : ''}`} 
            onClick={fetchStops} 
            disabled={isRefreshing}
          >
            <FaSync className="refresh-icon" /> Refresh
          </button>
          <div className="notification-icon" onClick={() => setShowNotifications(!showNotifications)}>
            <FaBell />
            {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
          </div>
        </div>
      </div>

      {showNotifications && (
        <div className="notifications-panel">
          <div className="notifications-header">
            <h2><FaBell className="panel-icon" /> Notifications</h2>
            <button onClick={markAllAsRead}>Mark all as read</button>
          </div>
          <div className="notifications-list">
            {notifications.length === 0 ? (
              <p className="no-notifications">No notifications</p>
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
            {stop.is_delayed && <MdWarning className="delay-indicator" />}
          </button>
        ))}
      </div>

      {selectedStop && (
        <div className="stop-details">
          <h2><FaMapMarkerAlt className="detail-title-icon" /> {selectedStop.name}</h2>
          
          <div className="detail-cards">
            <div className="detail-card">
              <h3><MdLocationOn className="card-icon" /> Location Status</h3>
              <div className="detail-item">
                <span className="detail-label">Expected Location</span>
                <span className="detail-value">{selectedStop.expected_location}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Driver Location</span>
                <span className="detail-value">{selectedStop.reported_location}</span>
              </div>
              <div className="detail-status">
                {selectedStop.expected_location === selectedStop.reported_location ? (
                  <span className="status-ok"><FaCheck /> On Track</span>
                ) : (
                  <span className="status-warning"><FaExclamationTriangle /> Off Route</span>
                )}
              </div>
            </div>

            <div className="detail-card">
              <h3><FaClock className="card-icon" /> Schedule Info</h3>
              <div className="detail-item">
                <span className="detail-label">Estimated Arrival</span>
                <span className="detail-value">{formatETA(selectedStop.eta)}</span>
              </div>
              {selectedStop.is_delayed && (
                <div className="detail-item">
                  <span className="detail-label">Delay Reason</span>
                  <span className="detail-value">{selectedStop.delay_reason || 'Not specified'}</span>
                </div>
              )}
              <div className="detail-status">
                {selectedStop.is_delayed ? (
                  <span className="status-warning"><FaExclamationTriangle /> Delayed</span>
                ) : (
                  <span className="status-ok"><FaCheck /> On Time</span>
                )}
              </div>
            </div>

            <div className="detail-card">
              <h3><FaRoad className="card-icon" /> Navigation Details</h3>
              <div className="detail-item">
                <span className="detail-label">Nearest Highway</span>
                <span className="detail-value">{selectedStop.nearest_highway || 'Not Available'}</span>
              </div>
              <div className="detail-status">
                <span className="status-info"><FaCompass /> Transit Route</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StakeholderDashboard; 