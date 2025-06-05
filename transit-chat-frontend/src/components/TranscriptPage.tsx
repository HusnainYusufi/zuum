import React from 'react';
import { FaArrowLeft, FaTimes } from 'react-icons/fa';
import { MdChatBubble, MdPerson } from 'react-icons/md';
import '../styles/TranscriptPage.css';

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

interface TranscriptPageProps {
  isDarkMode: boolean;
  checkIn: CheckIn | null;
  onBack: () => void;
}

const TranscriptPage: React.FC<TranscriptPageProps> = ({ isDarkMode, checkIn, onBack }) => {
  if (!checkIn) {
    return (
      <div className={`transcript-page ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className="transcript-header">
          <button className="back-button" onClick={onBack}>
            <FaArrowLeft /> Back
          </button>
          <h1>No Check-in Selected</h1>
        </div>
        <div className="transcript-content">
          <p>No check-in data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`transcript-page ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="transcript-header">
        <div className="header-left">
          <button className="back-button" onClick={onBack}>
            <FaArrowLeft /> Back to Dashboard
          </button>
          <h1>
            <MdChatBubble className="page-icon" />
            Call Transcript - Check-in #{checkIn.id.toString().padStart(2, '0')}
          </h1>
        </div>
      </div>

      <div className="transcript-container">
        <div className="transcript-info">
          <div className="info-card">
            <h3>Check-in Details</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Check-in ID:</span>
                <span className="info-value">#{checkIn.id.toString().padStart(2, '0')}</span>
              </div>
              {checkIn.call_id && (
                <div className="info-item">
                  <span className="info-label">Call ID:</span>
                  <span className="info-value">{checkIn.call_id}</span>
                </div>
              )}
              {checkIn.load_id && (
                <div className="info-item">
                  <span className="info-label">Load ID:</span>
                  <span className="info-value">{checkIn.load_id}</span>
                </div>
              )}
              {checkIn.AI_Timestamp && (
                <div className="info-item">
                  <span className="info-label">Date & Time:</span>
                  <span className="info-value">
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
                </div>
              )}
            </div>
          </div>

          <div className="status-card">
            <h3>Status Information</h3>
            <div className="status-grid">
              <div className={`status-item ${checkIn.Issue_Flagged ? 'flagged' : 'normal'}`}>
                <span className="status-label">Issue Flagged:</span>
                <span className="status-value">{checkIn.Issue_Flagged ? 'Yes' : 'No'}</span>
              </div>
              <div className={`status-item ${checkIn.Requires_Human_Review ? 'review' : 'normal'}`}>
                <span className="status-label">Human Review:</span>
                <span className="status-value">{checkIn.Requires_Human_Review ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="transcript-main">
          <div className="transcript-card">
            <h3>
              <MdChatBubble className="section-icon" />
              Call Transcript
            </h3>
            <div className="transcript-content">
              {checkIn.call_transcript ? (
                checkIn.call_transcript.split('\n').map((line, index) => {
                  const isAgent = line.startsWith('Agent:');
                  const isUser = line.startsWith('User:');
                  const cleanLine = isAgent ? line.replace('Agent:', '').trim() : 
                                   isUser ? line.replace('User:', '').trim() : 
                                   line.trim();
                  
                  if (!cleanLine) return null;
                  
                  return (
                    <div key={index} className={`transcript-line-wrapper ${isAgent ? 'agent-wrapper' : isUser ? 'user-wrapper' : ''}`}>
                      <div className={`transcript-line ${isAgent ? 'agent' : isUser ? 'user' : ''}`}>
                        {cleanLine}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="no-transcript">
                  <MdChatBubble className="empty-icon" />
                  <p>No transcript available for this check-in.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscriptPage; 