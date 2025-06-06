import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { RetellWebClient } from 'retell-client-js-sdk';
import Phone from './components/Phone';
import Sidebar from './components/Sidebar';
import StakeholderDashboard from './components/StakeholderDashboard';
import CheckInPage from './components/CheckInPage';
import TranscriptPageWrapper from './components/TranscriptPageWrapper';
import './App.css';
import { backend_url } from './config';
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

// Define conversation states for the audio call mode
type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';

// Define agent types
type AgentType = 'custom' | 'apicall';

// ViewToggleButton component that uses useLocation
const ViewToggleButton: React.FC<{ isDarkMode: boolean; toggleDarkMode: () => void }> = ({ isDarkMode, toggleDarkMode }) => {
  const location = useLocation();
  const isStakeholderPage = location.pathname === '/dashboard';
  
  return (
    <div className="view-toggle">
      <button 
        onClick={() => window.location.href = isStakeholderPage ? '/' : '/dashboard'}
        className="toggle-button"
      >
        {isStakeholderPage ? 'Switch to Testing' : 'Switch to Stakeholder Dashboard'}
      </button>
      <button 
        onClick={toggleDarkMode}
        className="toggle-button dark-toggle"
      >
        {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
      </button>
    </div>
  );
};

// Simple MainAppPage component
const MainAppPage: React.FC<any> = (props) => {
  return (
    <div className="app-container">
      <Sidebar 
        stops={props.stops} 
        selectedStopId={props.selectedStopId}
        onSelectStop={props.handleSelectStop}
        isDarkMode={props.isDarkMode}
        agentType={props.agentType}
        onToggleAgentType={props.toggleAgentType}
        isCallMode={props.isCallMode}
      />
      <div className="main-content">
        <Phone 
          messages={props.messages} 
          onSendMessage={props.handleSendMessage} 
          isDarkMode={props.isDarkMode}
          onToggleDarkMode={props.toggleDarkMode}
          isInitialized={props.isInitialized}
          onInitialize={props.handleInitializeChat}
          isBlurred={props.isBlurred}
          onReset={props.handleReset}
          isCallMode={props.isCallMode}
          audioStream={props.audioStream}
          onToggleCallMode={props.handleToggleCallMode}
          isRecording={props.agentType === 'apicall' ? props.isAPICallActive : props.isRecording}
          onToggleRecording={props.handleToggleMicrophone}
          conversationState={props.conversationState}
          agentType={props.agentType}
          conversationType={props.conversationType || 'workflow'}
          setConversationType={props.setConversationType}
          query={props.query}
          setQuery={props.setQuery}
        />
      </div>
  
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedMode = localStorage.getItem('darkMode');
    return savedMode ? JSON.parse(savedMode) : false;
  });
  
  const [conversationType, setConversationType] = useState<string | null>('workflow');
  const [query, setQuery] = useState<string>('');
  const [showDashboard, setShowDashboard] = useState(false);
  const [showCheckInPage, setShowCheckInPage] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isBlurred, setIsBlurred] = useState(false);
  const [isCallMode, setIsCallMode] = useState(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [conversationState, setConversationState] = useState<ConversationState>('idle');
  const [initAttempt, setInitAttempt] = useState(0);
  
  // New state for agent type
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

  const toggleDarkMode = () => {
    setIsDarkMode((prev: boolean) => {
      const newMode = !prev;
      localStorage.setItem('darkMode', JSON.stringify(newMode));
      return newMode;
    });
  };

  const toggleDashboard = () => {
    setShowDashboard(prev => !prev);
    setShowCheckInPage(false); // Close check-in page when opening dashboard
  };

  const toggleCheckInPage = () => {
    setShowCheckInPage(prev => !prev);
    setShowDashboard(false); // Close dashboard when opening check-in page
  };

  const goBackToDashboard = () => {
    setShowCheckInPage(false);
    setShowDashboard(true);
  };

  // Toggle between agent types with clearer feedback
  const toggleAgentType = (newType: AgentType) => {
    if (newType === agentType) {
      console.log(`📊 Already using ${newType} agent`);
      return; // No change needed
    }
    
    console.log(`🔄 Switching agent type from ${agentType} to ${newType}`);
    
    // If there's an active call, stop it first
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
    
    // Reset messages when switching agent types
    setMessages([]);
    if (selectedStopId) {
      localStorage.removeItem(`chat-data-${selectedStopId}`);
    }
    
    // Reset state
    setIsInitialized(false);
    setThreadId(selectedStopId?.toString() || null);
    
    // Change the agent type
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
        
        // Map the data to conform to our Stop interface
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
        console.log(mappedStops)
        
        setStops(mappedStops);
        
        // Select the first stop by default if no stop is selected
        if (mappedStops.length > 0) {
          setSelectedStopId(prevId => prevId === null ? mappedStops[0].id : prevId);
        }
      } catch (error) {
        console.error('Error fetching stops:', error);
      }
    };

    fetchStops();
  }, []); // Only run once on component mount

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
    // Save current messages and thread ID for previous stop if any exist
    if (selectedStopId && messages.length > 0) {
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages,
        threadId: threadId
      }));
    }

    setSelectedStopId(stopId);
    
    // Get stored chat data for this stop
    const storedData = localStorage.getItem(`chat-data-${stopId}`);
    
    if (storedData) {
      // If chat data exists, parse and set them
      const { messages: storedMessages, threadId: storedThreadId } = JSON.parse(storedData);
      setMessages(storedMessages);
      setThreadId(storedThreadId);
      setIsInitialized(true);
    } else {
      // If no chat data, reset messages and show initialize state
      setMessages([]);
      setThreadId(stopId.toString()); // Set default thread ID to stop ID
      setIsInitialized(false);
    }
  };

  // Function to start the listening state
  const startListening = () => {
    console.log('startListening called with isCallMode:', isCallMode, 'audioStream:', !!audioStream);
    
    setConversationState('listening');
    
    if (audioStream) {
      console.log('Enabling microphone tracks');
      audioStream.getAudioTracks().forEach(track => {
        track.enabled = true;
      });
    }
    
    if (isCallMode) {
      setIsRecording(true);
    }
  };

  // Handle recording toggle
  const handleRecordingToggle = () => {
    if (isCallMode && agentType === 'apicall' && apiCallClientRef.current) {
      if (isAPICallActive) {
        apiCallClientRef.current.stopCall();
      } else {
        initializeAPICall();
      }
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      setConversationState('processing');
      const manualSubmitEvent = new CustomEvent('manualAudioSubmit');
      document.dispatchEvent(manualSubmitEvent);
    } else {
      setIsRecording(true);
      if (audioStream) {
        audioStream.getAudioTracks().forEach(track => {
          track.enabled = true;
        });
      }
    }
  };

  // Effect to manage conversation state changes
  useEffect(() => {
    if (isCallMode && isInitialized && conversationState === 'idle' && agentType === 'custom') {
      startListening();
    }
  }, [isCallMode, isInitialized, conversationState, agentType]);

  // Effect to ensure audio tracks are properly managed
  useEffect(() => {
    if (!audioStream || agentType !== 'custom') return;
    
    const audioTracks = audioStream.getAudioTracks();
    
    if (conversationState === 'listening') {
      audioTracks.forEach(track => { track.enabled = true; });
    } else if (conversationState === 'processing' || conversationState === 'agentSpeaking') {
      audioTracks.forEach(track => { track.enabled = false; });
    }
  }, [audioStream, conversationState, agentType]);

  // Effect to handle audio recording lifecycle for custom agent
  useEffect(() => {
    if (!isCallMode || !audioStream || conversationState !== 'listening' || agentType !== 'custom') {
      return;
    }
    
    let audioChunks: Blob[] = [];
    const mediaRecorder = new MediaRecorder(audioStream, {
      mimeType: 'audio/webm;codecs=opus',
      audioBitsPerSecond: 128000
    });
    
    const shouldProcessRef = { value: false };
    let recordingStartTime = Date.now();
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };
    
    const handleStopRecording = () => {
      const recordingDuration = Date.now() - recordingStartTime;
      
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const shouldProcess = shouldProcessRef.value || (recordingDuration >= 3000 && audioBlob.size > 10000);
        
        if (shouldProcess) {
          processRecordedAudio(audioBlob);
          shouldProcessRef.value = false;
          audioChunks = [];
        }
      }
    };
    
    mediaRecorder.onstop = handleStopRecording;
    mediaRecorder.start(100);
    
    const handleManualSubmit = () => {
      if (mediaRecorder.state === 'recording') {
        shouldProcessRef.value = true;
        mediaRecorder.requestData();
        setTimeout(() => {
          if (mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
          }
        }, 200);
      }
    };
    
    document.addEventListener('manualAudioSubmit', handleManualSubmit);
    
    const MAX_RECORDING_TIME = 30000;
    const maxRecordingTimer = setTimeout(() => {
      if (mediaRecorder.state === 'recording' && conversationState === 'listening') {
        shouldProcessRef.value = true;
        setConversationState('processing');
        mediaRecorder.stop();
      }
    }, MAX_RECORDING_TIME);
    
    return () => {
      clearTimeout(maxRecordingTimer);
      document.removeEventListener('manualAudioSubmit', handleManualSubmit);
      if (mediaRecorder.state === 'recording') {
        shouldProcessRef.value = true;
        mediaRecorder.requestData();
        setTimeout(() => {
          if (mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
          }
        }, 300);
      }
    };
  }, [isCallMode, audioStream, conversationState, agentType]);

  const playAgentAudio = async (responseText: string) => {
    try {
      const audioResponse = await fetch(`${backend_url}/conversation/audio?text=${encodeURIComponent(responseText)}`, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (audioResponse.ok) {
        const audioBlob = await audioResponse.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        const customEvent = new CustomEvent('ai-audio-playing', {
          detail: { audioElement: audio }
        });
        document.dispatchEvent(customEvent);
        
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          setTimeout(() => {
            startListening();
          }, 300);
        };
        
        try {
          await audio.play();
        } catch (error) {
          console.error('Error playing audio:', error);
          startListening();
        }
      } else {
        startListening();
      }
    } catch (error) {
      console.error('Error fetching or playing audio:', error);
      startListening();
    }
  };

  const processRecordedAudio = async (audioBlob: Blob) => {
    try {
      // Remove the audio playback code
      console.log('Processing recorded audio:', audioBlob);
      
      const threadIdParam = threadId?.toString() || '';
      const formData = new FormData();
      
      // Make sure we're sending the audio file with the correct filename and type
      formData.append('audio', audioBlob, 'recording.webm');
      
      const response = await fetch(`${backend_url}/conversation/chat?thread_id=${threadIdParam}&stop_id=${selectedStopId}`, {
        method: 'POST',
        headers: {
          'ngrok-skip-browser-warning': 'true'
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.status}`);
      }

      const data = await response.json();
      
      const humanMessage: Message = {
        text: data.user || 'No response',
        isUser: true,
        timestamp: formatTime()
      };
      const botMessage: Message = {
        text: data.AI || data.response || 'No response',
        isUser: false,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, humanMessage, botMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });

      setConversationState('agentSpeaking');
      setIsRecording(false);

      if (data.AI || data.response) {
        const responseText = data.AI || data.response;
        await playAgentAudio(responseText);
      } else {
        startListening();
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      
      setMessages(prev => {
        const errorMessage: Message = {
          text: 'Sorry, there was an error processing your audio message. Please try again.',
          isUser: false,
          timestamp: formatTime()
        };
        const newMessages = [...prev, errorMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });
      
      startListening();
    }
  };

  // Initialize API call client
  useEffect(() => {
    console.log("Initializing API call client");
    
    if (!apiCallClientRef.current) {
      try {
        apiCallClientRef.current = new RetellWebClient();
        console.log("API call client created successfully");
        
        // Set up event listeners
        apiCallClientRef.current.on("call_started", () => {
          console.log("API call started event received");
          setIsAPICallActive(true);
          // Set recording to true by default when call starts (mic is active)
          setIsRecording(true);
          
          // Add UI message that the call started
          const systemMessage: Message = {
            text: "Call connected. You can speak with the API call agent now.",
            isUser: false,
            timestamp: formatTime()
          };
          
          setMessages(prev => {
            const newMessages = [...prev, systemMessage];
            if (selectedStopId) {
              localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
                messages: newMessages,
                threadId: threadId
              }));
            }
            return newMessages;
          });
        });

        apiCallClientRef.current.on("call_ended", () => {
          console.log("API call ended event received");
          setIsAPICallActive(false);
          setIsRecording(false); // Ensure microphone state is reset
          
          // Add UI message that the call ended
          const systemMessage: Message = {
            text: "Call ended.",
            isUser: false,
            timestamp: formatTime()
          };
          
          setMessages(prev => {
            const newMessages = [...prev, systemMessage];
            if (selectedStopId) {
              localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
                messages: newMessages,
                threadId: threadId
              }));
            }
            return newMessages;
          });
        });

        apiCallClientRef.current.on("agent_start_talking", () => {
          console.log("Agent started talking event received");
          setConversationState('agentSpeaking');
        });

        apiCallClientRef.current.on("agent_stop_talking", () => {
          console.log("Agent stopped talking event received");
          setConversationState('listening');
        });

        apiCallClientRef.current.on("update", (update) => {
          console.log("Update received:", update);
          if (update.transcript) {
            // Add the transcript to the messages
            const userMessage: Message = {
              text: update.transcript.user || "...",
              isUser: true,
              timestamp: formatTime()
            };
            
            const agentMessage: Message = {
              text: update.transcript.agent || "...",
              isUser: false,
              timestamp: formatTime()
            };
            
            setMessages(prev => {
              // Filter out any "..." messages that were placeholders
              const filteredMessages = prev.filter(msg => 
                !(msg.text === "..." || msg.text === "")
              );
              
              // Only add non-empty messages
              const newUserMessage = userMessage.text !== "..." ? [userMessage] : [];
              const newAgentMessage = agentMessage.text !== "..." ? [agentMessage] : [];
              
              const newMessages = [...filteredMessages, ...newUserMessage, ...newAgentMessage];
              
              if (selectedStopId) {
                localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
                  messages: newMessages,
                  threadId: threadId
                }));
              }
              
              return newMessages;
            });
          }
        });

        apiCallClientRef.current.on("error", (error) => {
          console.error("API call error:", error);
          setIsAPICallActive(false);
          
          // Add error message to the UI
          const errorMessage: Message = {
            text: `Call error: ${error.message || "Unknown error"}`,
            isUser: false,
            timestamp: formatTime()
          };
          
          setMessages(prev => {
            const newMessages = [...prev, errorMessage];
            if (selectedStopId) {
              localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
                messages: newMessages,
                threadId: threadId
              }));
            }
            return newMessages;
          });
        });
      } catch (error) {
        console.error("Error initializing API call client:", error);
      }
    }
    
    return () => {
      // Clean up on component unmount
      if (apiCallClientRef.current && isAPICallActive) {
        console.log("Cleaning up API call on unmount");
        apiCallClientRef.current.stopCall();
      }
    };
  }, []);

  // Function to get an access token from your backend
  const getAPICallAccessToken = async () => {
    try {
      console.log("🔑 Making fetch request to /conversation/retell-token");
      
      // Call the backend endpoint to get a Retell access token
      const response = await fetch(`${backend_url}/conversation/retell-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        // Add empty body to ensure POST works correctly
        body: JSON.stringify({
          stop_id: selectedStopId,
          journey_id: 1,
          query: conversationType === 'checkin' ? query : null
        })
      });
      
      console.log("📡 Response received:", response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("❌ Error response body:", errorText);
        throw new Error(`Failed to get API call access token: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      // Try to parse JSON response
      let data;
      try {
        data = await response.json();
        console.log("📦 Token response data:", data);
      } catch (jsonError: any) {
        console.error("❌ Failed to parse JSON response:", jsonError);
        throw new Error(`Invalid JSON response from server: ${jsonError.message}`);
      }
      
      // Check if we received a real token or a mock token
      if (data.message && data.message.includes("mock token")) {
        console.warn("⚠️ Using mock API call token. For production, configure API_CALL_API_KEY in backend.");
      }
      
      // Log call information for debugging
      if (data.call_id) {
        console.log(`📞 API call created with ID: ${data.call_id}, status: ${data.call_status || 'unknown'}`);
      }
      
      if (!data.access_token) {
        console.error("❌ No access_token in response:", data);
        throw new Error("No access_token provided in server response");
      }
      
      setAccessToken(data.access_token);
      return data.access_token;
    } catch (error) {
      console.error("❌ Error getting API call access token:", error);
      
      if (error instanceof TypeError && error.message.includes('fetch')) {
        console.error("🔌 Network error - Is your backend server running at https://trusting-dolphin-internally.ngrok-free.app?");
      }
      
      throw error;
    }
  };

  // Update the initializeAPICall function
  const initializeAPICall = async () => {
    console.log("📞 Starting API call initialization");
    
    if (!apiCallClientRef.current) {
      console.error("⚠️ API call client not initialized");
      
      // Try to initialize it again
      try {
        apiCallClientRef.current = new RetellWebClient();
        console.log("✅ API call client created on-demand");
      } catch (error) {
        console.error("❌ Failed to create API call client:", error);
        return;
      }
    }
    
    try {
      // Request microphone permissions before starting the call
      try {
        console.log("🎤 Requesting microphone permissions");
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // We don't need to store this stream as API call will handle it
        stream.getTracks().forEach(track => track.stop());
        console.log("✅ Microphone permissions granted");
      } catch (micError) {
        console.error("❌ Failed to get microphone permissions:", micError);
        throw new Error("Microphone access is required for the call. Please grant permission.");
      }
      
      // Show a connecting message in the UI
      const connectingMessage: Message = {
        text: "Connecting to agent call...",
        isUser: false,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, connectingMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });
      
      // Set initial mic state to active
      setIsRecording(true);
      
      // Get access token from your backend
      console.log("🔑 Requesting API call token from backend...");
      try {
        const token = await getAPICallAccessToken();
        console.log("✅ Successfully received token:", token ? "Token received" : "No token received");
        
        if (!token) {
          throw new Error("Failed to get valid access token");
        }
        
        console.log("🚀 Starting call with API call SDK");
        
        // Start the call
        await apiCallClientRef.current.startCall({
          accessToken: token,
          sampleRate: 24000, // 24kHz sample rate for better quality
          // Optional configuration below if needed
          // captureDeviceId: "default", // Use default microphone
          // playbackDeviceId: "default", // Use default speaker
          emitRawAudioSamples: false // Set to true if you need raw audio data
        });
        
        console.log("✅ Call started successfully");
        setIsAPICallActive(true);
        setConversationState('listening');
      } catch (tokenError) {
        console.error("❌ Error getting or using token:", tokenError);
        throw new Error(`Token error: ${tokenError instanceof Error ? tokenError.message : "Unknown token error"}`);
      }
    } catch (error) {
      console.error("❌ Failed to initialize API call:", error);
      
      // Reset the recording state
      setIsRecording(false);
      
      // Add error message to the UI
      const errorMessage: Message = {
        text: `Failed to start call: ${error instanceof Error ? error.message : "Unknown error"}`,
        isUser: false,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, errorMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });
    }
  };

  const handleToggleCallMode = async () => {
    if (!isCallMode) {
      try {
        if (agentType === 'custom') {
          // For custom agent, we need to access the microphone
          console.log('🎤 Starting custom agent call mode');
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          setAudioStream(stream);
          setIsCallMode(true);
          setConversationState('idle');
        } else if (agentType === 'apicall') {
          // For API call, we'll initialize a voice call
          console.log('🎤 Starting API call mode');
          setIsCallMode(true);
          setConversationState('idle');
          handleInitializeChat(true);
        }
      } catch (error) {
        console.error('❌ Error accessing microphone:', error);
        alert('Unable to access microphone. Please check permissions.');
      }
    } else {
      // Stop the call
      console.log('📴 Ending call');
      if (agentType === 'custom' && audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        setAudioStream(null);
      } else if (agentType === 'apicall' && apiCallClientRef.current) {
        console.log('📴 Ending API call');
        apiCallClientRef.current.stopCall();
        setIsAPICallActive(false);
        
        // Add a message that call was ended by user
        const endMessage: Message = {
          text: "Call ended by user.",
          isUser: false,
          timestamp: formatTime()
        };
        
        setMessages(prev => {
          const newMessages = [...prev, endMessage];
          if (selectedStopId) {
            localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
              messages: newMessages,
              threadId: threadId
            }));
          }
          return newMessages;
        });
      }
      
      setIsCallMode(false);
      setIsRecording(false);
      setConversationState('idle');
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!threadId) {
      console.error('Chat not initialized');
      return;
    }

    if (agentType === 'apicall' && isCallMode) {
      // For API call agent in call mode, messages are handled differently
      // Just add the user message to the UI
      const userMessage: Message = {
        text: message,
        isUser: true,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, userMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });
      
      // The response will come through the API call event listeners
      return;
    }

    if (isCallMode && agentType === 'custom') {
      setConversationState('processing');
      setIsRecording(false);
    } else {
      setInitAttempt(0);
    }

    const userMessage: Message = {
      text: message || '🎤 Audio message',
      isUser: true,
      timestamp: formatTime()
    };
    
    setMessages(prev => {
      const newMessages = [...prev, userMessage];
      if (selectedStopId) {
        localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
          messages: newMessages,
          threadId: threadId
        }));
      }
      return newMessages;
    });

    try {
      const queryParams = new URLSearchParams({
        thread_id: threadId.toString(),
        message: message
      });
      
      const response = await fetch(`${backend_url}/conversation/chat?${queryParams.toString()}&stop_id=${selectedStopId}`, {
        method: 'POST',
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      const responseText = data.response || data.AI || 'No response';
      
      const botMessage: Message = {
        text: responseText,
        isUser: false,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, botMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });

      if (isCallMode && responseText && agentType === 'custom') {
        setConversationState('agentSpeaking');
        setIsRecording(false);
        await playAgentAudio(responseText);
      } else if (isCallMode && agentType === 'custom') {
        startListening();
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        text: 'Sorry, there was an error processing your message.',
        isUser: false,
        timestamp: formatTime()
      };
      
      setMessages(prev => {
        const newMessages = [...prev, errorMessage];
        if (selectedStopId) {
          localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
            messages: newMessages,
            threadId: threadId
          }));
        }
        return newMessages;
      });
      
      if (isCallMode && agentType === 'custom') {
        startListening();
      }
    }
  };

  // Update handleInitializeChat
  const handleInitializeChat = async (isVoiceCall = false, send_thread_id = false) => {
    if (!selectedStopId) {
      console.error('❌ No stop selected');
      return;
    }

    console.log(`🚀 Initializing chat - Voice call: ${isVoiceCall}, Agent: ${agentType}, Selected stop: ${selectedStopId}`);

    if (isVoiceCall) {
      if (agentType === 'custom' && !isCallMode) {
        try {
          console.log('📱 Initializing custom agent voice call');
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          setAudioStream(stream);
          setIsCallMode(true);
        } catch (error) {
          console.error('❌ Error accessing microphone:', error);
          alert('Unable to access microphone. Please check permissions.');
          return;
        }
      } else if (agentType === 'apicall' && !isCallMode) {
        console.log('📱 Initializing API call agent call immediately');
        setIsCallMode(true);
        setIsInitialized(true); // Mark as initialized for API call
        
        // Add a "connecting" message
        const connectingMessage: Message = {
          text: "Connecting to API call voice call...",
          isUser: false,
          timestamp: formatTime()
        };
        
        setMessages([connectingMessage]);
        
        // Save the thread ID
        const threadIdToUse = selectedStopId.toString();
        setThreadId(threadIdToUse);
        
        // Immediately start the API call
        try {
          await initializeAPICall();
        } catch (error) {
          console.error("❌ Failed to start API call:", error);
          // Add error message already handled in initializeAPICall
        }
        
        return; // Return early as we've already initiated the call
      }
    } else if (!isVoiceCall && isCallMode) {
      if (agentType === 'custom' && audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        setAudioStream(null);
      } else if (agentType === 'apicall' && apiCallClientRef.current && isAPICallActive) {
        apiCallClientRef.current.stopCall();
        setIsAPICallActive(false);
      }
      setIsCallMode(false);
    }

    setIsBlurred(true);
    if (isCallMode) {
      setIsRecording(false);
    }

    // For API call agent in call mode, we've already handled initialization above
    if (agentType === 'apicall' && isVoiceCall) {
      setIsBlurred(false);
      return; // Already handled above
    }

    let url = `${backend_url}/conversation/initialize?stop_id=${selectedStopId}&is_audio=${isVoiceCall}`
    if (send_thread_id) {
      url += `&thread_id=${threadId}`
    }
    
    try {
      console.log(`📡 Fetching from ${url}`);
      const response = await fetch(url, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to initialize chat');
      }

      const data = await response.json();
      console.log('📦 Initialization response:', data);
      
      const initialMessage: Message = {
        text: data.response,
        isUser: false,
        timestamp: formatTime()
      };

      setMessages([initialMessage]);
      setThreadId(data.thread_id.toString());
      
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages: [initialMessage],
        threadId: data.thread_id.toString()
      }));
      
      setIsInitialized(true);

      if (!isVoiceCall && data.repeat === true) {
        setInitAttempt(prev => prev + 1);
      } else {
        setInitAttempt(0);
      }

      if (isVoiceCall && data.response && agentType === 'custom') {
        setConversationState('agentSpeaking');
        setIsRecording(false);
        await playAgentAudio(data.response);
      } else if (isVoiceCall && agentType === 'custom') {
        startListening();
      }
    } catch (error) {
      console.error('❌ Error initializing chat:', error);
      const errorMessage: Message = {
        text: 'Sorry, there was an error initializing the chat.',
        isUser: false,
        timestamp: formatTime()
      };
      setMessages([errorMessage]);
      
      if (isVoiceCall && agentType === 'custom') {
        startListening();
      }
    } finally {
      setIsBlurred(false);
    }
  };

  // Handle microphone toggle for API call separately to avoid ending call
  const handleToggleMicrophone = () => {
    if (agentType === 'apicall') {
      if (!isAPICallActive) {
        // If call is not active, do nothing - call is already started by handleInitializeChat
        console.log("ℹ️ API call not active");
        return;
      } else {
        // If call is active, just toggle mic state (not stopping the call)
        const newRecordingState = !isRecording;
        console.log(`🎤 ${newRecordingState ? 'Unmuting' : 'Muting'} microphone for API call`);
        
        // Toggle recording state for UI feedback
        setIsRecording(newRecordingState);
        
        // In a real implementation with API call SDK you would use:
        // apiCallClientRef.current.toggleMicrophone(); (if available)
        
        // Add a message to indicate microphone state
        const micMessage: Message = {
          text: newRecordingState 
            ? "✅ Microphone activated. The agent can hear you." 
            : "🔇 Microphone muted. The agent can't hear you.",
          isUser: false,
          timestamp: formatTime()
        };
        
        setMessages(prev => {
          const newMessages = [...prev, micMessage];
          if (selectedStopId) {
            localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
              messages: newMessages,
              threadId: threadId
            }));
          }
          return newMessages;
        });
      }
    } else {
      // For custom agent, use the original recording toggle
      handleRecordingToggle();
    }
  };

  // Update handleReset
  const handleReset = () => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    // Stop any active calls
    if (agentType === 'custom' && audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      setAudioStream(null);
    } else if (agentType === 'apicall' && apiCallClientRef.current && isAPICallActive) {
      apiCallClientRef.current.stopCall();
      setIsAPICallActive(false);
    }

    setMessages([]);
    localStorage.removeItem(`chat-data-${selectedStopId}`);
    setThreadId(selectedStopId.toString());
    setIsInitialized(false);
    setInitAttempt(0);
    setIsCallMode(false);
    setConversationState('idle');
  };

  // For debugging - expose the client to window
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // @ts-ignore - for debugging only
      window.apiCallClient = apiCallClientRef;
    }
  }, []);

  // Add a debug useEffect to monitor API call states
  useEffect(() => {
    console.log(`API call state update - Agent type: ${agentType}, Call active: ${isAPICallActive}, Call mode: ${isCallMode}`);
  }, [agentType, isAPICallActive, isCallMode]);

  // Add effect to log microphone state changes
  useEffect(() => {
    if (agentType === 'apicall') {
      console.log(`🎤 Microphone state changed: ${isRecording ? 'ACTIVE' : 'MUTED'}`);
    }
  }, [isRecording, agentType]);

  return (
    <Router>
      <div className={`App ${isDarkMode ? 'dark-mode' : ''}`}>
        <Routes>
          <Route 
            path="/dashboard" 
            element={<StakeholderDashboard isDarkMode={isDarkMode} onViewCheckIns={toggleCheckInPage} />} 
          />
          <Route 
            path="/check-ins" 
            element={<CheckInPage isDarkMode={isDarkMode} onBackToDashboard={goBackToDashboard} />} 
          />
          <Route 
            path="/transcript/:checkInId" 
            element={<TranscriptPageWrapper isDarkMode={isDarkMode} />} 
          />
                     <Route 
            path="/" 
            element={
              <MainAppPage 
                stops={stops}
                selectedStopId={selectedStopId}
                handleSelectStop={handleSelectStop}
                isDarkMode={isDarkMode}
                agentType={agentType}
                toggleAgentType={toggleAgentType}
                isCallMode={isCallMode}
                messages={messages}
                handleSendMessage={handleSendMessage}
                toggleDarkMode={toggleDarkMode}
                isInitialized={isInitialized}
                handleInitializeChat={handleInitializeChat}
                isBlurred={isBlurred}
                handleReset={handleReset}
                audioStream={audioStream}
                handleToggleCallMode={handleToggleCallMode}
                isAPICallActive={isAPICallActive}
                isRecording={isRecording}
                handleToggleMicrophone={handleToggleMicrophone}
                conversationState={conversationState}
                conversationType={conversationType}
                setConversationType={setConversationType}
                query={query}
                setQuery={setQuery}
              />
            } 
          />
        </Routes>
        <ViewToggleButton isDarkMode={isDarkMode} toggleDarkMode={toggleDarkMode} />
      </div>
    </Router>
  );
}

export default App;
