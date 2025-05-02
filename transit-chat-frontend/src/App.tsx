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
  const [isRecording, setIsRecording] = useState(false);
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

  // Function to start the listening state
  const startListening = () => {
    console.log('startListening called with isCallMode:', isCallMode, 'audioStream:', !!audioStream);
    
    // Always set the conversation state to listening regardless of conditions
    setConversationState('listening');
    
    // Only attempt to enable microphone if we have an audio stream
    if (audioStream) {
      console.log('Enabling microphone tracks');
      audioStream.getAudioTracks().forEach(track => {
        track.enabled = true;
      });
    } else {
      console.warn('No audioStream available for microphone');
    }
    
    // Only set recording to true if we're in call mode
    if (isCallMode) {
      setIsRecording(true);
    } else {
      console.warn('Not in call mode, recording not started');
    }
  };

  // Handle recording toggle
  const handleRecordingToggle = () => {
    if (isRecording) {
      // If we're currently recording, stop and process the audio
      setIsRecording(false);
      setConversationState('processing');
      
      // Trigger manual audio submission via a custom event
      const manualSubmitEvent = new CustomEvent('manualAudioSubmit');
      document.dispatchEvent(manualSubmitEvent);
    } else {
      // Start recording
      setIsRecording(true);
      // If audio stream exists, ensure microphone is enabled
      if (audioStream) {
        audioStream.getAudioTracks().forEach(track => {
          track.enabled = true;
        });
      }
    }
  };

  // Effect to manage conversation state changes
  useEffect(() => {
    if (isCallMode && isInitialized && conversationState === 'idle') {
      startListening();
    }
  }, [isCallMode, isInitialized, conversationState]);

  // Effect to handle audio recording lifecycle
  useEffect(() => {
    // Only record when we're in listening state
    if (!isCallMode || !audioStream || conversationState !== 'listening') {
      return;
    }
    
    console.log('Starting recording in listening state');
    
    let audioChunks: Blob[] = [];
    // Set proper MIME type and higher bitrate for better audio quality
    const mediaRecorder = new MediaRecorder(audioStream, {
      mimeType: 'audio/webm;codecs=opus',
      audioBitsPerSecond: 128000
    });
    
    // Create a ref for shouldProcessAudio to ensure it survives across render cycles
    const shouldProcessRef = { value: false };
    let recordingStartTime = Date.now();
    
    // Set up event handlers
    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        console.log(`Received audio chunk: ${event.data.size} bytes`);
        audioChunks.push(event.data);
      }
    };
    
    const handleStopRecording = () => {
      const recordingDuration = Date.now() - recordingStartTime;
      console.log(`Recording stopped after ${recordingDuration}ms, chunks: ${audioChunks.length}, shouldProcess: ${shouldProcessRef.value}`);
      
      if (audioChunks.length > 0) {
        // Use webm for better compatibility
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log(`Created audio blob: ${audioBlob.size} bytes, shouldProcess: ${shouldProcessRef.value}`);
        
        // Use our ref instead of a regular variable
        if (shouldProcessRef.value) {
          console.log('Processing audio...');
          processRecordedAudio(audioBlob);
          // Reset after processing
          shouldProcessRef.value = false;
          // Clear audio chunks after processing
          audioChunks = [];
        }
      } else {
        console.warn('No audio chunks collected during recording!');
      }
    };
    
    mediaRecorder.onstop = handleStopRecording;
    
    // Start recording
    mediaRecorder.start(100); // Collect chunks every 100ms for smoother recording
    recordingStartTime = Date.now();
    console.log('Media recorder started');
    
    // Handle manual audio submission via custom event
    const handleManualSubmit = () => {
      console.log('Manual audio submission triggered');
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
    
    // Add event listener for manual submission
    document.addEventListener('manualAudioSubmit', handleManualSubmit);
    
    // Backup timer to ensure we always get some recording in case user doesn't manually stop
    const MAX_RECORDING_TIME = 30000; // 30 seconds max
    const maxRecordingTimer = setTimeout(() => {
      if (mediaRecorder.state === 'recording' && conversationState === 'listening') {
        console.log(`Max recording time (${MAX_RECORDING_TIME}ms) reached, stopping.`);
        shouldProcessRef.value = true;
        setConversationState('processing');
        mediaRecorder.stop();
      }
    }, MAX_RECORDING_TIME);
    
    // Clean up
    return () => {
      clearTimeout(maxRecordingTimer);
      document.removeEventListener('manualAudioSubmit', handleManualSubmit);
      console.log('Cleaning up recording effect, shouldProcess:', shouldProcessRef.value);
      if (mediaRecorder.state === 'recording') {
        const wasProcessingTriggered = shouldProcessRef.value;
        
        // Only reset the flag if we're not supposed to be processing
        if (!wasProcessingTriggered) {
          shouldProcessRef.value = false;
        }
        
        console.log('Stopping recorder from cleanup, preserving shouldProcess:', shouldProcessRef.value);
        mediaRecorder.stop();
      }
    };
  }, [
    isCallMode,
    audioStream,
    conversationState
  ]);

  // Modify this function in both processRecordedAudio and handleSendMessage functions
  const playAgentAudio = async (responseText: string) => {
    try {
      // Play audio for the response using the audio endpoint
      const audioResponse = await fetch(`http://localhost:8000/conversation/audio?text=${encodeURIComponent(responseText)}`);
      if (audioResponse.ok) {
        const audioBlob = await audioResponse.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        
        // Dispatch custom event with audio element for visualizer
        const customEvent = new CustomEvent('ai-audio-playing', {
          detail: { audioElement: audio }
        });
        document.dispatchEvent(customEvent);
        
        // When audio finishes, start listening again
        audio.onended = () => {
          console.log('Audio finished playing, now starting listening');
          URL.revokeObjectURL(audioUrl); // Clean up the URL object
          // Slight delay to ensure state updates have propagated
          setTimeout(() => {
            // Always call startListening without checking isCallMode
            startListening();
          }, 300);
        };
        
        try {
          await audio.play();
          console.log('Audio playback started successfully');
        } catch (error) {
          console.error('Error playing audio:', error);
          // If audio play fails, still start listening
          startListening();
        }
      } else {
        console.error('Failed to fetch audio from endpoint:', audioResponse.status);
        // If audio fails, still start listening again
        startListening();
      }
    } catch (error) {
      console.error('Error fetching or playing audio:', error);
      startListening();
    }
  };

  // Now update the processRecordedAudio function to use this helper
  const processRecordedAudio = async (audioBlob: Blob) => {
    try {
      console.log(`Processing audio blob: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
      
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('audio', audioBlob, 'audio.webm');
      
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
      setIsRecording(false);

      // Play audio for the response using the new audio endpoint
      if (data.AI || data.response) {
        const responseText = data.AI || data.response;
        await playAgentAudio(responseText);
      } else {
        // No response to play, start listening again
        startListening();
      }
    } catch (error) {
      console.error('Error processing audio:', error);
      // On error, go back to listening state
      startListening();
    }
  };

  const handleToggleCallMode = async () => {
    if (!isCallMode) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setAudioStream(stream);
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
        setAudioStream(null);
      }
      setIsCallMode(false);
      setConversationState('idle');
    }
  };

  // Update handleSendMessage to use the helper function
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
        
        // Use the helper function to play audio
        await playAgentAudio(responseText);
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

  // Update handleInitializeChat to use the helper function
  const handleInitializeChat = async (isVoiceCall = false) => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    // Set call mode based on parameter
    if (isVoiceCall && !isCallMode) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setAudioStream(stream);
        setIsCallMode(true);
      } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Unable to access microphone. Please check permissions.');
        return;
      }
    } else if (!isVoiceCall && isCallMode) {
      // Switch to text mode if needed
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        setAudioStream(null);
      }
      setIsCallMode(false);
    }

    setIsBlurred(true);
    // Ensure recording is off during initialization
    if (isCallMode || isVoiceCall) {
      setIsRecording(false);
    }
    
    try {
      const response = await fetch(`http://localhost:8000/conversation/initialize?stop_id=${selectedStopId}&is_audio=${isVoiceCall}`);
      
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

      // Use isVoiceCall parameter instead of isCallMode state
      if (isVoiceCall && data.response) {
        // Set to agent speaking while playing response
        setConversationState('agentSpeaking');
        setIsRecording(false);
        
        console.log('Playing initial audio response in voice call mode');
        
        // Use the helper function to play audio
        await playAgentAudio(data.response);
      } else {
        // Start listening immediately if in voice call mode but no response to play
        if (isVoiceCall) {
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
      
      if (isVoiceCall) {
        startListening();
      }
    } finally {
      setIsBlurred(false);
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
