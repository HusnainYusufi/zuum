import React from 'react';
import { FaArrowLeft, FaTimes, FaMicrophone, FaDatabase, FaUser } from 'react-icons/fa';
import { MdChatBubble, MdPerson, MdSpeed } from 'react-icons/md';
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
  recording_url?: string;
  check_in_metadata?: string;
  miles?: string;
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
              {checkIn.miles && (
                <div className="info-item">
                  <span className="info-label">Miles:</span>
                  <span className="info-value">{checkIn.miles}</span>
                </div>
              )}
              {checkIn.recording_url && (
                <div className="info-item">
                  <span className="info-label">Recording:</span>
                  <a 
                    href={checkIn.recording_url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="info-value recording-link"
                  >
                    <FaMicrophone /> Listen to Recording
                  </a>
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
                checkIn.call_transcript
                  .split('\n')
                  .map((line, index) => {
                    // More flexible parsing to handle different transcript formats
                    const isAgent = line.startsWith('Agent:') || 
                                   line.startsWith('AI:') || 
                                   line.startsWith('AGENT:') || 
                                   line.startsWith('Assistant:') ||
                                   line.startsWith('Bot:');
                    const isUser = line.startsWith('User:') || 
                                  line.startsWith('USER:') || 
                                  line.startsWith('Driver:') || 
                                  line.startsWith('DRIVER:') ||
                                  line.startsWith('Human:');
                    
                    let cleanLine = line.trim();
                    
                    // Remove common prefixes
                    if (isAgent) {
                      cleanLine = line.replace(/^(Agent:|AI:|AGENT:|Assistant:|Bot:)\s*/i, '').trim();
                    } else if (isUser) {
                      cleanLine = line.replace(/^(User:|USER:|Driver:|DRIVER:|Human:)\s*/i, '').trim();
                    }
                    
                    // If line doesn't have a clear prefix but has content, 
                    // try to determine speaker based on context or assume it's an agent message
                    // This is a fallback for transcripts without clear prefixes
                    if (!isAgent && !isUser && cleanLine) {
                      // For now, assume unprefixed messages are from the agent
                      // You can adjust this logic based on your specific transcript format
                      return {
                        originalIndex: index,
                        isAgent: true,
                        isUser: false,
                        cleanLine,
                        hasContent: !!cleanLine
                      };
                    }
                    
                    return {
                      originalIndex: index,
                      isAgent,
                      isUser,
                      cleanLine,
                      hasContent: !!cleanLine
                    };
                  })
                  .filter(item => item.hasContent)
                  .map((item, filteredIndex) => (
                    <div 
                      key={`message-${item.originalIndex}-${filteredIndex}`} 
                      className={`transcript-line-wrapper ${item.isAgent ? 'agent-wrapper' : item.isUser ? 'user-wrapper' : ''}`}
                    >
                      <div className={`transcript-line ${item.isAgent ? 'agent' : item.isUser ? 'user' : ''}`}>
                        {item.cleanLine}
                      </div>
                    </div>
                  ))
              ) : (
                <div className="no-transcript">
                  <MdChatBubble className="empty-icon" />
                  <p>No transcript available for this check-in.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="transcript-sidebar">
          {checkIn.AI_Response_Summary && (
            <div className="summary-card">
              <h3>
                <FaUser className="section-icon" />
                AI Summary
              </h3>
              <div className="summary-content">
                <p>{checkIn.AI_Response_Summary}</p>
              </div>
            </div>
          )}

          {checkIn.check_in_metadata && (
            <div className="metadata-card">
              <h3>
                <FaDatabase className="section-icon" />
                Metadata
              </h3>
              <div className="metadata-content">
                {(() => {
                  try {
                    const metadata = JSON.parse(checkIn.check_in_metadata);
                    return (
                      <div className="metadata-grid">
                        {Object.entries(metadata).map(([key, value]) => (
                          <div key={key} className="metadata-item">
                            <span className="metadata-label">{key.replace(/_/g, ' ')}:</span>
                            <span className="metadata-value">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    );
                  } catch {
                    return <p>{checkIn.check_in_metadata}</p>;
                  }
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TranscriptPage; 