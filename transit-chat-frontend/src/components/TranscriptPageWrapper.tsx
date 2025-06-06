import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import TranscriptPage from './TranscriptPage';
import { backend_url } from '../config';

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

interface TranscriptPageWrapperProps {
  isDarkMode: boolean;
}

const TranscriptPageWrapper: React.FC<TranscriptPageWrapperProps> = ({ isDarkMode }) => {
  const { checkInId } = useParams<{ checkInId: string }>();
  const navigate = useNavigate();
  const [checkIn, setCheckIn] = useState<CheckIn | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCheckIn = async () => {
      if (!checkInId) {
        setLoading(false);
        return;
      }

      try {
        // Fetch all check-ins and find the specific one
        const response = await fetch(`${backend_url}/check-ins`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch check-ins');
        }
        
        const checkIns = await response.json();
        const foundCheckIn = checkIns.find((ci: CheckIn) => ci.id.toString() === checkInId);
        
        if (foundCheckIn) {
          setCheckIn(foundCheckIn);
        } else {
          console.error('Check-in not found');
        }
      } catch (error) {
        console.error('Error fetching check-in:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCheckIn();
  }, [checkInId]);

  const handleBack = () => {
    navigate('/dashboard');
  };

  if (loading) {
    return (
      <div className={`dashboard-container ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading transcript...</p>
        </div>
      </div>
    );
  }

  return (
    <TranscriptPage 
      isDarkMode={isDarkMode}
      checkIn={checkIn}
      onBack={handleBack}
    />
  );
};

export default TranscriptPageWrapper; 