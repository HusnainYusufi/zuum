import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaClipboardCheck, FaArrowLeft, FaExclamationTriangle, FaTimes, FaClock, FaMapMarkerAlt, FaUser, FaPhone, FaTag, FaChartLine, FaMicrophone, FaDatabase } from 'react-icons/fa';
import { MdChatBubble, MdPerson, MdLocationOn, MdSpeed } from 'react-icons/md';
import { backend_url } from '../config';
import '../styles/CheckInPage.css';

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
  check_in_metadata?: string;
  miles?: string;
}

interface CheckInPageProps {
  isDarkMode: boolean;
  onBackToDashboard?: () => void; // Make optional since we'll use React Router
}

const CheckInPage: React.FC<CheckInPageProps> = ({ isDarkMode, onBackToDashboard }) => {
  const navigate = useNavigate();
  const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Format ETA to human readable form with 12-hour clock
  const formatETA = (etaString: string): string => {
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
  };

  // Fetch all check-ins
  const fetchCheckIns = async () => {
    try {
      setLoading(true);
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCheckIns();
  }, []);

  if (loading) {
    return (
      <div className={`check-in-page ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading check-ins...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`check-in-page ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="check-in-header">
        <div className="header-left">
          <button className="back-button" onClick={() => navigate('/dashboard')}>
            <FaArrowLeft /> Back to Dashboard
          </button>
          <h1><FaClipboardCheck className="page-icon" /> All Check-Ins</h1>
        </div>
        <div className="check-in-stats">
          <div className="stat-item">
            <span className="stat-number">{checkIns.length}</span>
            <span className="stat-label">Total Check-ins</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{checkIns.filter(c => c.Issue_Flagged).length}</span>
            <span className="stat-label">Issues Flagged</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{checkIns.filter(c => c.Requires_Human_Review).length}</span>
            <span className="stat-label">Need Review</span>
          </div>
        </div>
      </div>

      <div className="check-in-grid">
        {checkIns.length === 0 ? (
          <div className="no-check-ins">
            <FaClipboardCheck className="empty-icon" />
            <h3>No Check-ins Available</h3>
            <p>Check-ins will appear here when drivers make calls or submit reports.</p>
          </div>
        ) : (
          checkIns.map(checkIn => (
            <div key={checkIn.id} className="check-in-card-detailed">
              <div className="card-header">
                <div className="check-in-title">
                  <FaClipboardCheck className="title-icon" />
                  <span className="check-in-number">Check-in #{checkIn.id.toString().padStart(2, '0')}</span>
                  {checkIn.AI_Timestamp && (
                    <span className="check-in-date">
                      {new Date(checkIn.AI_Timestamp).toLocaleDateString('en-US', { 
                        month: '2-digit', 
                        day: '2-digit', 
                        year: 'numeric' 
                      })} at {new Date(checkIn.AI_Timestamp).toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit', 
                        second: '2-digit', 
                        hour12: true 
                      })}
                    </span>
                  )}
                </div>
                <div className="card-actions">
                  {checkIn.call_transcript && (
                    <button 
                      className="transcript-btn"
                      onClick={() => navigate(`/transcript/${checkIn.id}`)}
                    >
                      <MdChatBubble /> View Transcript
                    </button>
                  )}
                </div>
              </div>

              <div className="card-content">
                <div className="status-section">
                  <div className="status-badges">
                    <div className={`status-badge ${checkIn.Issue_Flagged ? 'flagged' : 'normal'}`}>
                      <FaExclamationTriangle className="badge-icon" />
                      <span>Issue Flagged: {checkIn.Issue_Flagged ? 'Yes' : 'No'}</span>
                    </div>
                    <div className={`status-badge ${checkIn.Requires_Human_Review ? 'review' : 'normal'}`}>
                      <MdPerson className="badge-icon" />
                      <span>Human Review: {checkIn.Requires_Human_Review ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>

                <div className="details-section">
                  {checkIn.load_id && (
                    <div className="detail-item">
                      <FaTag className="detail-icon" />
                      <span className="detail-label">Load ID:</span>
                      <span className="detail-value">{checkIn.load_id}</span>
                    </div>
                  )}
                  
                  {checkIn.stop_name && (
                    <div className="detail-item">
                      <FaMapMarkerAlt className="detail-icon" />
                      <span className="detail-label">Stop:</span>
                      <span className="detail-value">{checkIn.stop_name}</span>
                    </div>
                  )}

                  {checkIn.stop_location && (
                    <div className="detail-item">
                      <MdLocationOn className="detail-icon" />
                      <span className="detail-label">Location:</span>
                      <span className="detail-value">{checkIn.stop_location}</span>
                    </div>
                  )}

                  {checkIn.miles && (
                    <div className="detail-item">
                      <MdSpeed className="detail-icon" />
                      <span className="detail-label">Miles:</span>
                      <span className="detail-value">{checkIn.miles}</span>
                    </div>
                  )}

                  {checkIn.stop_eta && (
                    <div className="detail-item">
                      <FaClock className="detail-icon" />
                      <span className="detail-label">ETA:</span>
                      <span className="detail-value">{formatETA(checkIn.stop_eta)}</span>
                    </div>
                  )}

                  {checkIn.Exception_Type && (
                    <div className="detail-item">
                      <FaExclamationTriangle className="detail-icon" />
                      <span className="detail-label">Exception Type:</span>
                      <span className="detail-value">{checkIn.Exception_Type}</span>
                    </div>
                  )}

                  {checkIn.Call_confidence_score && (
                    <div className="detail-item">
                      <FaChartLine className="detail-icon" />
                      <span className="detail-label">Confidence Score:</span>
                      <span className="detail-value">{checkIn.Call_confidence_score}%</span>
                    </div>
                  )}

                  {checkIn.call_id && (
                    <div className="detail-item">
                      <FaPhone className="detail-icon" />
                      <span className="detail-label">Call ID:</span>
                      <span className="detail-value">{checkIn.call_id}</span>
                    </div>
                  )}

                  {checkIn.Tags && (
                    <div className="detail-item">
                      <FaTag className="detail-icon" />
                      <span className="detail-label">Tags:</span>
                      <span className="detail-value">{checkIn.Tags}</span>
                    </div>
                  )}

                  {checkIn.recording_url && (
                    <div className="detail-item">
                      <FaMicrophone className="detail-icon" />
                      <span className="detail-label">Recording:</span>
                      <a 
                        href={checkIn.recording_url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="detail-value recording-link"
                      >
                        Listen to Recording
                      </a>
                    </div>
                  )}

                  {checkIn.check_in_metadata && (
                    <div className="detail-item metadata-item">
                      <FaDatabase className="detail-icon" />
                      <span className="detail-label">Metadata:</span>
                      <span className="detail-value metadata-value">
                        {(() => {
                          try {
                            const metadata = JSON.parse(checkIn.check_in_metadata);
                            return Object.entries(metadata).map(([key, value]) => (
                              <div key={key} className="metadata-entry">
                                <strong>{key}:</strong> {String(value)}
                              </div>
                            ));
                          } catch {
                            return checkIn.check_in_metadata;
                          }
                        })()}
                      </span>
                    </div>
                  )}
                </div>

                {checkIn.query && (
                  <div className="query-section">
                    <h4><MdChatBubble className="section-icon" /> Driver Query</h4>
                    <p className="query-text">{checkIn.query}</p>
                  </div>
                )}

                {checkIn.AI_Response_Summary && (
                  <div className="summary-section">
                    <h4><FaUser className="section-icon" /> AI Summary</h4>
                    <p className="summary-text">{checkIn.AI_Response_Summary}</p>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>


    </div>
  );
};

export default CheckInPage; 