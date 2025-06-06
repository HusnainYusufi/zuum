import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/StakeholderDashboard.css';
import { FaBell, FaMapMarkerAlt, FaClock, FaRoute, FaExclamationTriangle, FaCheck, FaRoad, FaSync, FaLocationArrow, FaCompass, FaTruck, FaClipboardCheck, FaTags, FaTimes } from 'react-icons/fa';
import { MdWarning, MdLocationOn, MdTimeline, MdChatBubble, MdPerson, MdSpeed } from 'react-icons/md';
import { backend_url } from '../config';

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
  stop_id?: number;
  severity?: string;
}

interface CheckIn {
  id: number;
  stop_id: number;
  load_id?: string;
  query?: string;
  AI_Response_Summary?: string;
  AI_Timestamp?: string;
  Issue_Flagged: boolean;
  Exception_Type?: string;
  Call_confidence_score?: string;
  Requires_Human_Review: boolean;
  Tags?: string;
  stop_name?: string;
  stop_location?: string;
  stop_eta?: string;
  call_id?: string;
  call_transcript?: string;
  recording_url?: string;
}

interface StakeholderDashboardProps {
  isDarkMode: boolean;
  onViewCheckIns?: () => void;
}

const StakeholderDashboard: React.FC<StakeholderDashboardProps> = ({ isDarkMode, onViewCheckIns }) => {
  const navigate = useNavigate();
  const [stops, setStops] = useState<Stop[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [selectedStop, setSelectedStop] = useState<Stop | null>(null);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastNotificationTime, setLastNotificationTime] = useState<number>(Date.now());
  const [journeyState, setJourneyState] = useState<number>(0);
  const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number; checkInId: number | null }>({ x: 0, y: 0, checkInId: null });
  const [isMobile, setIsMobile] = useState<boolean>(window.innerWidth <= 768);

  // Detect mobile device
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Close notifications when clicking outside on mobile
  useEffect(() => {
    if (isMobile && showNotifications) {
      const handleClickOutside = (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        if (!target.closest('.notifications-panel') && !target.closest('.notification-icon')) {
          setShowNotifications(false);
        }
      };

      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isMobile, showNotifications]);

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

  // Fetch journey state from backend
  const fetchJourneyState = async () => {
    try {
      const response = await fetch(`${backend_url}/ui/journey_state`, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch journey state');
      }
      const data = await response.json();
      setJourneyState(data);
    } catch (error) {
      console.error('Error fetching journey state:', error);
    }
  };

  // Fetch check-ins for selected stop
  const fetchCheckIns = async (stopId: number) => {
    try {
      // Always fetch all check-ins, ignoring the stopId parameter
      const response = await fetch(`${backend_url}/check-ins`, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch check-ins');
      }
      const data = await response.json();
      setCheckIns(data);
    } catch (error) {
      console.error('Error fetching check-ins:', error);
      setCheckIns([]);
    }
  };

  // Fetch stops function - not wrapped in useCallback to avoid dependency cycles
  const fetchStops = async () => {
    try {
      if (!loading) setIsRefreshing(true);
      const response = await fetch(`${backend_url}/stops/details`, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
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

  // Fetch notifications from backend
  const fetchNotifications = async () => {
    try {
      // Check server logs for notifications
      // Since we don't have a direct API endpoint to fetch notifications yet,
      // we'll simulate by capturing driver inactivity notifications from the logs
      const currentTime = Date.now();
      console.log("Checking for new notifications since", new Date(lastNotificationTime).toLocaleTimeString());
      
      // Add notifications based on stop conditions
      stops.forEach(stop => {
        if (stop.is_delayed && !notifications.some(n => n.message.includes(`${stop.name} is delayed`))) {
          addNotification(`${stop.name} is delayed. Reason: ${stop.delay_reason || 'Not provided'}`, stop.id, "warning");
        }
        
        if (stop.expected_location !== stop.reported_location && 
            !notifications.some(n => n.message.includes(`${stop.name} is off route`))) {
          addNotification(`${stop.name} is off route. Expected: ${stop.expected_location}, Reported: ${stop.reported_location}`, stop.id, "warning");
        }
      });
      
      // Simulate checking for driver inactivity notifications
      // In a real app, we'd make an API call here to get notifications from the backend
      try {
        // This is a polling mechanism to detect chat notifications
        const response = await fetch(`${backend_url}/conversation/active_notifications`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (response.ok) {
          const data = await response.json();
          
          if (data && data.notifications && Array.isArray(data.notifications)) {
            data.notifications.forEach((notif: any) => {
              // Only add if we don't already have this notification
              if (!notifications.some(n => n.message === notif.message)) {
                addNotification(notif.message, notif.stop_id, notif.severity || "warning");
              }
            });
          }
        }
      } catch (err) {
        // If the endpoint doesn't exist yet, we'll check for "not responding" in the server logs
        // This is a fallback until the API is implemented
        const chatResponse = await fetch(`${backend_url}/conversation/initialize?stop_id=1&is_audio=false&dummy=${Math.random()}`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (chatResponse.ok) {
          // Check if the response contains any info about notifications
          const chatData = await chatResponse.json();
          if (chatData && chatData.notification) {
            addNotification(chatData.notification.message, chatData.notification.stop_id, chatData.notification.severity || "warning");
          }
        }
      }
      
      // Update the last notification check time
      setLastNotificationTime(currentTime);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  // Fetch all stops data only on initial load
  useEffect(() => {
    fetchStops();
    fetchJourneyState();
    // Empty dependency array means this effect runs only once on mount
  }, []);

  // Check for changes and create notifications
  useEffect(() => {
    fetchNotifications();
  }, [stops]);

  // Set up notification polling (every 10 seconds to catch driver inactivity notifications)
  useEffect(() => {
    const notificationPoller = setInterval(() => {
      fetchNotifications();
    }, 10000);
    
    return () => clearInterval(notificationPoller);
  }, []);

  // Set up journey state polling
  useEffect(() => {
    const journeyStatePoller = setInterval(() => {
      fetchJourneyState();
    }, 5000);
    
    return () => clearInterval(journeyStatePoller);
  }, []);

  // Fetch check-ins when selected stop changes
  useEffect(() => {
    // Always fetch all check-ins when component mounts or refreshes
    fetchCheckIns(0); // Pass 0 as we're fetching all check-ins
  }, []); // Remove selectedStop dependency

  // Manually check for notification the first time
  useEffect(() => {
    // Manually add the driver not responding notification for testing
    const checkForDriverNotifications = async () => {
      try {
        // We'll make one special call to check for driver inactivity
        const response = await fetch(`${backend_url}/conversation/check_driver_activity`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (response.ok) {
          const data = await response.json();
          if (data && data.inactive_drivers && Array.isArray(data.inactive_drivers)) {
            data.inactive_drivers.forEach((driver: any) => {
              if (driver.stop_id && driver.stop_name) {
                addNotification(
                  `Driver at ${driver.stop_name} is not responding to text chat after multiple attempts`,
                  driver.stop_id,
                  "warning"
                );
              }
            });
          }
        }
      } catch (error) {
        // If this endpoint doesn't exist yet, just log it
        console.log("No driver activity endpoint yet");
      }
    };
    
    checkForDriverNotifications();
  }, []);

  // Count unread notifications
  useEffect(() => {
    setUnreadCount(notifications.filter(n => !n.read).length);
  }, [notifications]);

  const addNotification = (message: string, stop_id?: number, severity: string = "info") => {
    const newNotification: Notification = {
      id: Date.now(),
      message,
      timestamp: new Date().toLocaleString(),
      read: false,
      stop_id,
      severity
    };
    
    // Avoid duplicate notifications
    setNotifications(prev => {
      if (prev.some(n => n.message === message)) {
        return prev;
      }
      return [newNotification, ...prev];
    });
  };

  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  };

  const markAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, read: true } : n
    ));
  };

  // Delivery status steps
  const deliverySteps = [
    { title: "Confirmed", isActive: journeyState >= 0 },
    { title: "In transit", isActive: journeyState >= 1 },
    { title: "Delivered", isActive: journeyState >= 2 }
  ];

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
        <h1><FaRoute className="header-icon" /> {isMobile ? 'Transit Dashboard' : 'Transit Stakeholder Dashboard'}</h1>
        <div className="header-actions">
          <button 
            className={`refresh-button ${isRefreshing ? 'refreshing' : ''}`} 
            onClick={() => {
              fetchStops();
              fetchNotifications();
              fetchJourneyState();
              fetchCheckIns(0); // Also refresh check-ins
            }} 
            disabled={isRefreshing}
          >
            <FaSync className="refresh-icon" /> {!isMobile && 'Refresh'}
          </button>
          <div className="notification-icon" onClick={() => setShowNotifications(!showNotifications)}>
            <FaBell />
            {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
          </div>
        </div>
      </div>

      <div className="dashboard-main-grid">
        <div className="dashboard-left-content">
          {/* Delivery Timeline */}
          <div className="delivery-timeline">
            <h2><FaTruck className="detail-title-icon" /> Delivery Status</h2>
            <div className="timeline-container">
              {deliverySteps.map((step, index) => (
                <React.Fragment key={index}>
                  <div className={`timeline-step ${step.isActive ? 'active' : ''}`}>
                    <div className="timeline-node"></div>
                    <div className="timeline-title">{step.title}</div>
                  </div>
                  {index < deliverySteps.length - 1 && (
                    <div className={`timeline-connector ${deliverySteps[index + 1].isActive ? 'active' : ''}`}></div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

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
                {/* Combined Location & Status Card */}
                <div className="detail-card location-card">
                  <div className="card-header">
                    <h3><MdLocationOn className="card-icon" /> Live Tracking</h3>
                    <div className="location-status-badge">
                      {selectedStop.expected_location.toLowerCase().split(',')[0].includes(selectedStop.reported_location.toLowerCase().split(',')[0]) ? (
                        <span className="status-ok"><FaCheck /> On Track</span>
                      ) : (
                        <span className="status-warning"><FaExclamationTriangle /> Off Route</span>
                      )}
                    </div>
                  </div>
                  <div className="location-grid">
                    <div className="location-info">
                      <div className="location-item expected">
                        <FaLocationArrow className="location-icon" />
                        <div>
                          <span className="location-label">Expected</span>
                          <span className="location-value">{selectedStop.expected_location}</span>
                        </div>
                      </div>
                      <div className="location-item current">
                        <FaTruck className="location-icon" />
                        <div>
                          <span className="location-label">Current</span>
                          <span className="location-value">{selectedStop.reported_location}</span>
                        </div>
                      </div>
                    </div>
                    <div className="route-info">
                      <FaRoad className="route-icon" />
                      <div>
                        <span className="route-label">Highway</span>
                        <span className="route-value">{selectedStop.nearest_highway || 'Not Available'}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Schedule & Timing Card */}
                <div className="detail-card schedule-card">
                  <div className="card-header">
                    <h3><FaClock className="card-icon" /> Schedule Status</h3>
                    <div className="schedule-status-badge">
                      {selectedStop.is_delayed ? (
                        <span className="status-warning"><FaExclamationTriangle /> Delayed</span>
                      ) : (
                        <span className="status-ok"><FaCheck /> On Time</span>
                      )}
                    </div>
                  </div>
                  <div className="schedule-grid">
                    <div className="eta-info">
                      <div className="eta-main">
                        <MdSpeed className="eta-icon" />
                        <div>
                          <span className="eta-label">Estimated Arrival</span>
                          <span className="eta-value">{formatETA(selectedStop.eta)}</span>
                        </div>
                      </div>
                      {selectedStop.is_delayed && (
                        <div className="delay-info">
                          <MdWarning className="delay-icon" />
                          <div>
                            <span className="delay-label">Delay Reason</span>
                            <span className="delay-value">{selectedStop.delay_reason || 'Not specified'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="timing-summary">
                      <div className="timing-indicator">
                        {selectedStop.is_delayed ? (
                          <div className="delay-indicator-visual">
                            <span className="delay-time">+{selectedStop.delay_reason ? '15' : '?'} min</span>
                          </div>
                        ) : (
                          <div className="ontime-indicator-visual">
                            <span className="ontime-text">On Schedule</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="check-ins-section">
          <h3><FaClipboardCheck className="section-icon" /> ALL CHECK-INS</h3>
          <div className="check-ins-container">
            {checkIns.length === 0 ? (
              <p className="no-check-ins">No check-ins available.</p>
            ) : (
              checkIns.map(checkIn => (
                <div 
                  key={checkIn.id} 
                  className="check-in-card"
                >
                  <div className="check-in-header">
                    <div className="check-in-id-wrapper">
                      <FaClipboardCheck className="check-in-icon" />
                      <span 
                        className="check-in-id clickable-link"
                        onClick={() => navigate(`/transcript/${checkIn.id}`)}
                      >
                        CHECK-IN #{checkIn.id.toString().padStart(2, '0')}
                        {checkIn.AI_Timestamp && ` | ${new Date(checkIn.AI_Timestamp).toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' }).replace(/\//g, '/')}, ${new Date(checkIn.AI_Timestamp).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true })}`}
                      </span>
                    </div>
                    <div className="check-in-status">
                      {checkIn.Issue_Flagged && (
                        <span className="status-badge issue-flagged" title="Issue Flagged">
                          ⚠️
                        </span>
                      )}
                      
                    </div>
                  </div>


                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {showNotifications && (
        <div className="notifications-panel">
          <div className="notifications-header">
            <h2><FaBell className="panel-icon" /> Notifications</h2>
            <div className="notifications-header-actions">
              <button onClick={markAllAsRead}>Mark all as read</button>
              {isMobile && (
                <button 
                  className="notifications-close"
                  onClick={() => setShowNotifications(false)}
                  aria-label="Close notifications"
                >
                  <FaTimes />
                </button>
              )}
            </div>
          </div>
          <div className="notifications-list">
            {notifications.length === 0 ? (
              <p className="no-notifications">No notifications</p>
            ) : (
              notifications.map(notification => (
                <div 
                  key={notification.id} 
                  className={`notification-item ${!notification.read ? 'unread' : ''} ${notification.severity === 'warning' ? 'warning' : notification.severity === 'error' ? 'error' : ''}`}
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


    </div>
  );
};

export default StakeholderDashboard; 