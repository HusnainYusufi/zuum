import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { RetellWebClient } from 'retell-client-js-sdk';
import Phone from './Phone';
import Sidebar from './Sidebar';
import { backend_url } from '../config';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: string;
}

interface Stop {
  id: number;
  name: string;
  location: string;
  eta: string;
  is_delayed: boolean;
  thread_id: string;
  is_origin?: boolean;
  is_destination?: boolean;
}

type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';
type AgentType = 'custom' | 'apicall';

interface AppWrapperProps {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
}

const AppWrapper: React.FC<AppWrapperProps> = ({ isDarkMode, toggleDarkMode }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null);
  
  const [conversationType, setConversationType] = useState<string | null>('workflow');
  const [query, setQuery] = useState<string>('');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isBlurred, setIsBlurred] = useState(false);
  const [isCallMode, setIsCallMode] = useState(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [conversationState, setConversationState] = useState<ConversationState>('idle');
  const [initAttempt, setInitAttempt] = useState(0);
  
  const [agentType, setAgentType] = useState<AgentType>('apicall');
  const [isAPICallActive, setIsAPICallActive] = useState(false);
  const apiCallClientRef = useRef<RetellWebClient | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const formatTime = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  // Add navigation functions
  const goToDashboard = () => {
    navigate('/dashboard');
  };

  const goToCheckIns = () => {
    navigate('/check-ins');
  };

  const goBackToDashboard = () => {
    navigate('/dashboard');
  };

  // Toggle between agent types with clearer feedback
  const toggleAgentType = (newType: AgentType) => {
    if (newType === agentType) {
      console.log(`📊 Already using ${newType} agent`);
      return;
    }
    
    console.log(`🔄 Switching agent type from ${agentType} to ${newType}`);
    
    if (isCallMode) {
      if (agentType === 'apicall' && apiCallClientRef.current && isAPICallActive) {
        console.log("⏹️ Stopping active API call before switching agent type");
        apiCallClientRef.current.stopCall();
        setIsAPICallActive(false);
      } else if (agentType === 'custom' && audioStream) {
        console.log("⏹️ Stopping custom agent audio before switching agent type");
        audioStream.getTracks().forEach(track => track.stop());
        setAudioStream(null);
      }
      setIsCallMode(false);
      setConversationState('idle');
    }
    
    setMessages([]);
    if (selectedStopId) {
      localStorage.removeItem(`chat-data-${selectedStopId}`);
    }
    
    setIsInitialized(false);
    setThreadId(selectedStopId?.toString() || null);
    setAgentType(newType);
  };

  // Fetch all stops and set default selection
  useEffect(() => {
    const fetchStops = async () => {
      try {
        const response = await fetch(`${backend_url}/stops/details`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (!response.ok) {
          throw new Error('Failed to fetch stops');
        }
        const data = await response.json();
        
        const mappedStops = data.map((stop: any) => ({
          id: stop.id,
          name: stop.name,
          location: stop.location,
          eta: stop.eta,
          is_delayed: stop.is_delayed,
          thread_id: stop.thread_id || stop.id.toString(),
          is_origin: stop.is_origin || false,
          is_destination: stop.is_destination || false
        }));
        
        setStops(mappedStops);
        
        if (mappedStops.length > 0) {
          setSelectedStopId(prevId => prevId === null ? mappedStops[0].id : prevId);
        }
      } catch (error) {
        console.error('Error fetching stops:', error);
      }
    };

    fetchStops();
  }, []);

  // Load messages from localStorage when selectedStopId changes
  useEffect(() => {
    if (selectedStopId) {
      const storedData = localStorage.getItem(`chat-data-${selectedStopId}`);
      
      if (storedData) {
        const { messages: storedMessages, threadId: storedThreadId } = JSON.parse(storedData);
        setMessages(storedMessages);
        setThreadId(storedThreadId);
        setIsInitialized(true);
      } else {
        setMessages([]);
        setThreadId(selectedStopId.toString());
        setIsInitialized(false);
      }
    }
  }, [selectedStopId]);

  // Handle stop selection
  const handleSelectStop = async (stopId: number) => {
    if (selectedStopId && messages.length > 0) {
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages,
        threadId: threadId
      }));
    }

    setSelectedStopId(stopId);
  };

  // Placeholder functions - implement as needed
  const startListening = () => {};
  const handleRecordingToggle = () => {};
  const playAgentAudio = async (responseText: string) => {};
  const processRecordedAudio = async (audioBlob: Blob) => {};
  const getAPICallAccessToken = async () => {};
  const initializeAPICall = async () => {};
  const handleToggleCallMode = async () => {};
  const handleSendMessage = async (message: string) => {};
  const handleInitializeChat = async (isVoiceCall = false, send_thread_id = false) => {};
  const handleToggleMicrophone = () => {};
  const handleReset = () => {};

  return (
    <div className="app-container">
      <Sidebar 
        stops={stops} 
        selectedStopId={selectedStopId}
        onSelectStop={handleSelectStop}
        isDarkMode={isDarkMode}
        agentType={agentType}
        onToggleAgentType={toggleAgentType}
        isCallMode={isCallMode}
      />
      <div className="main-content">
        <Phone 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          isDarkMode={isDarkMode}
          onToggleDarkMode={toggleDarkMode}
          isInitialized={isInitialized}
          onInitialize={handleInitializeChat}
          isBlurred={isBlurred}
          onReset={handleReset}
          isCallMode={isCallMode}
          audioStream={audioStream}
          onToggleCallMode={handleToggleCallMode}
          isRecording={agentType === 'apicall' ? isAPICallActive : isRecording}
          onToggleRecording={handleToggleMicrophone}
          conversationState={conversationState}
          agentType={agentType}
          conversationType={conversationType || 'workflow'}
          setConversationType={setConversationType}
          query={query}
          setQuery={setQuery}
        />
      </div>
      <div className="view-toggle">
        <button 
          onClick={goToDashboard}
          className="toggle-button"
        >
          Switch to Stakeholder Dashboard
        </button>
      </div>
    </div>
  );
};

export default AppWrapper; 