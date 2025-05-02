import React, { useState, useEffect } from 'react';
import Phone from './components/Phone';
import Sidebar from './components/Sidebar';
import StakeholderDashboard from './components/StakeholderDashboard';
import './App.css';

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
}

// Define conversation states for the audio call mode
type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedMode = localStorage.getItem('darkMode');
    return savedMode ? JSON.parse(savedMode) : false;
  });
  const [showDashboard, setShowDashboard] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isBlurred, setIsBlurred] = useState(false);
  const [isCallMode, setIsCallMode] = useState(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [silenceDetector, setSilenceDetector] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [silenceDetected, setSilenceDetected] = useState(false);
  const [conversationState, setConversationState] = useState<ConversationState>('idle');

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
  };

  // Fetch all stops and set default selection
  useEffect(() => {
    const fetchStops = async () => {
      try {
        const response = await fetch('http://localhost:8000/stops');
        if (!response.ok) {
          throw new Error('Failed to fetch stops');
        }
        const data = await response.json();
        setStops(data);
        
        // Select the first stop by default if no stop is selected
        if (data.length > 0) {
          setSelectedStopId(prevId => prevId === null ? data[0].id : prevId);
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

  // Add silence detection setup
  const setupSilenceDetection = (stream: MediaStream) => {
    // TODO: Replace ScriptProcessorNode with AudioWorkletNode in a future update
    // This implementation uses the deprecated ScriptProcessorNode for compatibility
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    
    // Configure analyser for voice detection
    analyser.smoothingTimeConstant = 0.8;
    analyser.fftSize = 256;
    
    source.connect(analyser);
    
    let silenceStart: number | null = null;
    const SILENCE_THRESHOLD = -50; // dB
    const SILENCE_DURATION = 2000; // ms

    // Create a monitoring function that doesn't require ScriptProcessor
    const silenceDetectionInterval = setInterval(() => {
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(dataArray);
      
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
      const dB = 20 * Math.log10(average / 255);

      if (dB < SILENCE_THRESHOLD) {
        if (!silenceStart) {
          silenceStart = Date.now();
        } else if (Date.now() - silenceStart > SILENCE_DURATION) {
          silenceStart = null;
          setSilenceDetected(true);
        }
      } else {
        silenceStart = null;
      }
    }, 100);

    return {
      cleanup: () => {
        clearInterval(silenceDetectionInterval);
        audioContext.close();
        source.disconnect();
        analyser.disconnect();
      }
    };
  };

  // Start listening after initialization or agent response
  const startListening = () => {
    if (isCallMode && audioStream) {
      console.log('Transitioning to listening state');
      setConversationState('listening');
      setSilenceDetected(false);
      // Ensure microphone is enabled
      audioStream.getAudioTracks().forEach(track => {
        track.enabled = true;
      });
      setIsRecording(true);
    }
  };

  // Handle recording toggle
  const handleRecordingToggle = () => {
    setIsRecording(!isRecording);
    // Mute/unmute the microphone if audio stream exists
    if (audioStream) {
      audioStream.getAudioTracks().forEach(track => {
        track.enabled = !isRecording;
      });
    }
  };

  // Effect to manage conversation state changes
  useEffect(() => {
    if (isCallMode && isInitialized && conversationState === 'idle') {
      startListening();
    }
  }, [isCallMode, isInitialized, conversationState]);

  // Function to process recorded audio and send it to the server
  const processRecordedAudio = async (audioBlob: Blob) => {
    try {
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('audio', audioBlob, 'audio.wav');
      
      // Also add the thread_id as regular parameter
      const threadIdParam = threadId?.toString() || '';
      
      // Use the conversation/chat endpoint but with the thread_id as a query parameter
      const response = await fetch(`http://localhost:8000/conversation/chat?thread_id=${threadIdParam}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
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

      // Set to agent speaking while playing response
      setConversationState('agentSpeaking');

      // Play audio for the response using the new audio endpoint
      if (data.AI || data.response) {
        const responseText = data.AI || data.response;
        const audioResponse = await fetch(`http://localhost:8000/conversation/audio?text=${encodeURIComponent(responseText)}`);
        if (audioResponse.ok) {
          const audioBlob = await audioResponse.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          // Listen for when audio finishes playing to start listening again
          audio.onended = () => {
            setConversationState('listening');
          };
          
          await audio.play();
        } else {
          // If audio fails, still start listening again
          setConversationState('listening');
        }
      } else {
        // No response to play, start listening again
        setConversationState('listening');
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      // On error, go back to listening state
      setConversationState('listening');
    }
  };

  // Effect to handle silence detection and audio recording lifecycle
  useEffect(() => {
    // Only record when we're in listening state
    if (!isCallMode || !audioStream || conversationState !== 'listening') {
      return;
    }
    
    console.log('Starting recording in listening state');
    
    let audioChunks: Blob[] = [];
    const mediaRecorder = new MediaRecorder(audioStream);
    let shouldProcessAudio = false; // Flag to track if we should process audio
    
    // Set up event handlers
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };
    
    const handleStopRecording = () => {
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        console.log('Recording stopped, shouldProcessAudio:', shouldProcessAudio);
        
        // Use our flag instead of checking the React state
        if (shouldProcessAudio) {
          console.log('Processing audio...');
          processRecordedAudio(audioBlob);
        }
      }
    };
    
    mediaRecorder.onstop = handleStopRecording;
    
    // Start recording
    mediaRecorder.start();
    
    // Request data regularly to collect audio chunks
    const requestInterval = setInterval(() => {
      if (mediaRecorder.state === 'recording') {
        mediaRecorder.requestData();
      }
    }, 500);
    
    // When silence is detected, transition to processing and stop recording
    const handleSilenceDetection = () => {
      if (silenceDetected && conversationState === 'listening') {
        console.log('Stopping recording due to silence detection');
        
        // Set our flag BEFORE stopping the recorder
        shouldProcessAudio = true;
        
        // Update the React state
        setConversationState('processing');
        
        // Stop the recorder - this will trigger the onstop event immediately
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
        
        setSilenceDetected(false);
      }
    };
    
    // Watch for silence detection
    const silenceCheckInterval = setInterval(handleSilenceDetection, 100);
    
    // Clean up
    return () => {
      clearInterval(requestInterval);
      clearInterval(silenceCheckInterval);
      if (mediaRecorder.state === 'recording') {
        // Don't process audio on unmount
        shouldProcessAudio = false;
        mediaRecorder.stop();
      }
    };
  }, [
    isCallMode,
    audioStream,
    conversationState,
    silenceDetected
  ]);

  const handleToggleCallMode = async () => {
    if (!isCallMode) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setAudioStream(stream);
        const detector = setupSilenceDetection(stream);
        setSilenceDetector(detector);
        setIsCallMode(true);
        // Start in idle state until initialized
        setConversationState('idle');
      } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Unable to access microphone. Please check permissions.');
      }
    } else {
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        if (silenceDetector) {
          silenceDetector.cleanup();
          setSilenceDetector(null);
        }
        setAudioStream(null);
      }
      setIsCallMode(false);
      setConversationState('idle');
    }
  };

  const handleInitializeChat = async () => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    setIsBlurred(true);
    // Ensure recording is off during initialization
    if (isCallMode) {
      setIsRecording(false);
    }
    
    try {
      const response = await fetch(`http://localhost:8000/conversation/initialize?stop_id=${selectedStopId}&is_audio=${isCallMode}`);
      
      if (!response.ok) {
        throw new Error('Failed to initialize chat');
      }

      const data = await response.json();
      
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

      if (isCallMode && data.response) {
        // Set to agent speaking while playing response
        setConversationState('agentSpeaking');
        setIsRecording(false);
        
        // Play audio for the response using the new audio endpoint
        const audioResponse = await fetch(`http://localhost:8000/conversation/audio?text=${encodeURIComponent(data.response)}`);
        if (audioResponse.ok) {
          const audioBlob = await audioResponse.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          // When audio finishes, start listening
          audio.onended = () => {
            startListening();
          };
          
          await audio.play();
        } else {
          // If audio fails, still start listening
          startListening();
        }
      } else {
        // Start listening immediately if not in call mode or no response
        if (isCallMode) {
          startListening();
        }
      }
    } catch (error) {
      console.error('Error initializing chat:', error);
      const errorMessage: Message = {
        text: 'Sorry, there was an error initializing the chat.',
        isUser: false,
        timestamp: formatTime()
      };
      setMessages([errorMessage]);
      
      if (isCallMode) {
        startListening();
      }
    } finally {
      setIsBlurred(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!threadId) {
      console.error('Chat not initialized');
      return;
    }

    // If in call mode, pause listening while processing
    if (isCallMode) {
      setConversationState('processing');
      setIsRecording(false);
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
      // Create URLSearchParams to append message to query string
      const queryParams = new URLSearchParams({
        thread_id: threadId.toString(),
        message: message
      });
      
      // Use query parameters for both thread_id and message
      const response = await fetch(`http://localhost:8000/conversation/chat?${queryParams.toString()}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Use response or AI field for the bot's message text
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

      if (isCallMode && responseText) {
        // Set to agent speaking while playing response
        setConversationState('agentSpeaking');
        setIsRecording(false);
        
        // Play audio for the response using the new audio endpoint
        const audioResponse = await fetch(`http://localhost:8000/conversation/audio?text=${encodeURIComponent(responseText)}`);
        if (audioResponse.ok) {
          const audioBlob = await audioResponse.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          // When audio finishes, start listening again
          audio.onended = () => {
            startListening();
          };
          
          await audio.play();
        } else {
          // If audio fails, still start listening again
          startListening();
        }
      } else if (isCallMode) {
        // No audio to play but still in call mode, start listening
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
      
      // On error, go back to listening if in call mode
      if (isCallMode) {
        startListening();
      }
    }
  };

  const handleReset = () => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    // Clear messages from state
    setMessages([]);
    
    // Clear localStorage for this stop
    localStorage.removeItem(`chat-data-${selectedStopId}`);
    
    // Reset thread ID to stop ID
    setThreadId(selectedStopId.toString());
    
    // Set initialized to false
    setIsInitialized(false);
    
    // Reset conversation state if in call mode
    if (isCallMode) {
      setConversationState('idle');
    }
  };

  return (
    <div className={`App ${isDarkMode ? 'dark-mode' : ''}`}>
      {showDashboard ? (
        <StakeholderDashboard isDarkMode={isDarkMode} />
      ) : (
        <div className="app-container">
          <Sidebar 
            stops={stops} 
            selectedStopId={selectedStopId}
            onSelectStop={handleSelectStop}
            isDarkMode={isDarkMode}
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
              isRecording={isRecording}
              onToggleRecording={handleRecordingToggle}
              conversationState={conversationState}
            />
         
         
          </div>
        </div>
      )}
      <div className="view-toggle">
        <button 
          onClick={toggleDashboard}
          className="toggle-button"
        >
          {showDashboard ? 'Switch to Chat View' : 'Switch to Stakeholder Dashboard'}
        </button>
        <button 
          onClick={toggleDarkMode}
          className="toggle-button dark-toggle"
        >
          {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </button>
      </div>
    </div>
  );
}

export default App;
