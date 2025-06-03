import React, { useState, useEffect } from 'react';
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
  const [lastNotificationTime, setLastNotificationTime] = useState<number>(Date.now());
  const [journeyState, setJourneyState] = useState<number>(0);
  const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
  const [selectedCheckIn, setSelectedCheckIn] = useState<CheckIn | null>(null);
  const [showTranscriptModal, setShowTranscriptModal] = useState<boolean>(false);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number; checkInId: number | null }>({ x: 0, y: 0, checkInId: null });

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
        <h1><FaRoute className="header-icon" /> Transit Stakeholder Dashboard</h1>
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
            <FaSync className="refresh-icon" /> Refresh
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
                    {selectedStop.expected_location.toLowerCase().split(',')[0].includes(selectedStop.reported_location.toLowerCase().split(',')[0]) ? (
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

        <div className="check-ins-section">
          <h3><FaClipboardCheck className="section-icon" /> ALL CHECK-INS</h3>
          <div className="check-ins-container">
            {checkIns.length === 0 ? (
              <p className="no-check-ins">No check-ins available.</p>
            ) : (
              checkIns.map(checkIn => (
                <div 
                  key={checkIn.id} 
                  className="check-in-card clickable"
                  onClick={() => {
                    if (checkIn.call_transcript) {
                      setSelectedCheckIn(checkIn);
                      setShowTranscriptModal(true);
                    }
                  }}
                  onMouseMove={(e) => {
                    if (checkIn.call_transcript) {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setMousePosition({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                        checkInId: checkIn.id
                      });
                    }
                  }}
                  onMouseLeave={() => {
                    setMousePosition({ x: 0, y: 0, checkInId: null });
                  }}
                >
                  {checkIn.call_transcript && mousePosition.checkInId === checkIn.id && (
                    <div 
                      className="hover-tooltip"
                      style={{
                        left: `${mousePosition.x + 10}px`,
                        top: `${mousePosition.y - 30}px`
                      }}
                    >
                      Click to view transcript
                    </div>
                  )}
                  <div className="check-in-header">
                    <div className="check-in-id-wrapper">
                      <FaClipboardCheck className="check-in-icon" />
                      <span className="check-in-id">
                        Check-in #{checkIn.id.toString().padStart(2, '0')}
                        {checkIn.load_id && ` | Load: ${checkIn.load_id}`}
                        {checkIn.stop_name && ` | ${checkIn.stop_name}`}
                        {checkIn.AI_Timestamp && ` | ${new Date(checkIn.AI_Timestamp).toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' }).replace(/\//g, '/')}, ${new Date(checkIn.AI_Timestamp).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true })}`}
                      </span>
                    </div>
                    <div className="check-in-status">
                      {checkIn.Issue_Flagged && (
                        <span className="status-badge issue-flagged">
                          <FaExclamationTriangle /> Issue Flagged
                        </span>
                      )}
                      {checkIn.Requires_Human_Review && (
                        <span className="status-badge requires-review">
                          <MdPerson /> Requires Review
                        </span>
                      )}
                      
                    </div>
                  </div>
                  <div className="check-in-content">
                    {checkIn.stop_location && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <MdLocationOn className="content-icon" />
                          <span>LOCATION:</span>
                        </div>
                        <div className="field-value">{checkIn.stop_location}</div>
                      </div>
                    )}
                    {checkIn.stop_eta && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <FaClock className="content-icon" />
                          <span>ETA:</span>
                        </div>
                        <div className="field-value">{formatETA(checkIn.stop_eta)}</div>
                      </div>
                    )}
                    {checkIn.query && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <MdChatBubble className="content-icon" />
                          <span>QUERY:</span>
                        </div>
                        <div className="field-value">{checkIn.query}</div>
                      </div>
                    )}
                    {checkIn.AI_Response_Summary && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <MdPerson className="content-icon" />
                          <span>AI SUMMARY:</span>
                        </div>
                        <div className="field-value">{checkIn.AI_Response_Summary}</div>
                      </div>
                    )}
                    <div className="check-in-field">
                      <div className="field-label">
                        <FaExclamationTriangle className="content-icon" />
                        <span>ISSUE FLAGGED:</span>
                      </div>
                      <div className="field-value">{checkIn.Issue_Flagged ? 'Yes' : 'No'}</div>
                    </div>
                    <div className="check-in-field">
                      <div className="field-label">
                        <MdPerson className="content-icon" />
                        <span>HUMAN REVIEW:</span>
                      </div>
                      <div className="field-value">{checkIn.Requires_Human_Review ? 'Yes' : 'No'}</div>
                    </div>
                    {checkIn.Exception_Type && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <FaExclamationTriangle className="content-icon" />
                          <span>EXCEPTION TYPE:</span>
                        </div>
                        <div className="field-value">{checkIn.Exception_Type}</div>
                      </div>
                    )}
                    {checkIn.Call_confidence_score && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <MdSpeed className="content-icon" />
                          <span>CONFIDENCE SCORE:</span>
                        </div>
                        <div className="field-value">{checkIn.Call_confidence_score}%</div>
                      </div>
                    )}
                    {checkIn.Tags && (
                      <div className="check-in-field">
                        <div className="field-label">
                          <FaTags className="content-icon" />
                          <span>TAGS:</span>
                        </div>
                        <div className="field-value">{checkIn.Tags}</div>
                      </div>
                    )}
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
            <button onClick={markAllAsRead}>Mark all as read</button>
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

      {/* Transcript Modal */}
      {showTranscriptModal && selectedCheckIn && (
        <div className="modal-overlay" onClick={() => setShowTranscriptModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <MdChatBubble className="modal-icon" />
                Call Transcript
              </h2>
              <button className="modal-close" onClick={() => setShowTranscriptModal(false)}>
                <FaTimes />
              </button>
            </div>
            <div className="modal-body">
              <div className="modal-info">
                <div className="modal-info-item">
                  <span className="modal-info-label">Check-in ID:</span>
                  <span className="modal-info-value">#{selectedCheckIn.id.toString().padStart(2, '0')}</span>
                </div>
                {selectedCheckIn.call_id && (
                  <div className="modal-info-item">
                    <span className="modal-info-label">Call ID:</span>
                    <span className="modal-info-value">{selectedCheckIn.call_id}</span>
                  </div>
                )}
                {selectedCheckIn.load_id && (
                  <div className="modal-info-item">
                    <span className="modal-info-label">Load ID:</span>
                    <span className="modal-info-value">{selectedCheckIn.load_id}</span>
                  </div>
                )}
                {selectedCheckIn.stop_name && (
                  <div className="modal-info-item">
                    <span className="modal-info-label">Stop:</span>
                    <span className="modal-info-value">{selectedCheckIn.stop_name}</span>
                  </div>
                )}
              </div>
              <div className="modal-transcript">
                {selectedCheckIn.call_transcript?.split('\n').map((line, index) => {
                  const isAgent = line.startsWith('Agent:');
                  const isUser = line.startsWith('User:');
                  // Remove the prefix from the line
                  const cleanLine = isAgent ? line.replace('Agent:', '').trim() : 
                                   isUser ? line.replace('User:', '').trim() : 
                                   line.trim();
                  return (
                    <div key={index} className={`transcript-line-wrapper ${isAgent ? 'agent-wrapper' : isUser ? 'user-wrapper' : ''}`}>
                      <div className={`transcript-line ${isAgent ? 'agent' : isUser ? 'user' : ''}`}>
                        {cleanLine}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StakeholderDashboard; 