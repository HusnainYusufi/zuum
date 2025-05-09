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
  is_origin?: boolean;
  is_destination?: boolean;
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
  const [initAttempt, setInitAttempt] = useState(0);

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
        const response = await fetch('http://localhost:8000/stops/details');
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
    if (isCallMode && isInitialized && conversationState === 'idle') {
      startListening();
    }
  }, [isCallMode, isInitialized, conversationState]);

  // Effect to ensure audio tracks are properly managed
  useEffect(() => {
    if (!audioStream) return;
    
    const audioTracks = audioStream.getAudioTracks();
    
    if (conversationState === 'listening') {
      audioTracks.forEach(track => { track.enabled = true; });
    } else if (conversationState === 'processing' || conversationState === 'agentSpeaking') {
      audioTracks.forEach(track => { track.enabled = false; });
    }
  }, [audioStream, conversationState]);

  // Effect to handle audio recording lifecycle
  useEffect(() => {
    if (!isCallMode || !audioStream || conversationState !== 'listening') {
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
  }, [isCallMode, audioStream, conversationState]);

  const playAgentAudio = async (responseText: string) => {
    try {
      const audioResponse = await fetch(`http://localhost:8000/conversation/audio?text=${encodeURIComponent(responseText)}`);
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
      const threadIdParam = threadId?.toString() || '';
      
      const audioArrayBuffer = await audioBlob.arrayBuffer();
      const audioBase64 = btoa(
        new Uint8Array(audioArrayBuffer)
          .reduce((data, byte) => data + String.fromCharCode(byte), '')
      );
      
      const response = await fetch(`http://localhost:8000/conversation/chat?thread_id=${threadIdParam}&stop_id=${selectedStopId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          audio_file: audioBase64,
          thread_id: threadIdParam
        })
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

  const handleToggleCallMode = async () => {
    if (!isCallMode) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setAudioStream(stream);
        setIsCallMode(true);
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

  const handleSendMessage = async (message: string) => {
    if (!threadId) {
      console.error('Chat not initialized');
      return;
    }

    if (isCallMode) {
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
      
      const response = await fetch(`http://localhost:8000/conversation/chat?${queryParams.toString()}&stop_id=${selectedStopId}`, {
        method: 'POST'
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

      if (isCallMode && responseText) {
        setConversationState('agentSpeaking');
        setIsRecording(false);
        await playAgentAudio(responseText);
      } else if (isCallMode) {
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
      
      if (isCallMode) {
        startListening();
      }
    }
  };

  // Update handleInitializeChat
  const handleInitializeChat = async (isVoiceCall = false, send_thread_id = false) => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

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
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        setAudioStream(null);
      }
      setIsCallMode(false);
    }

    setIsBlurred(true);
    if (isCallMode || isVoiceCall) {
      setIsRecording(false);
    }

    let url = `http://localhost:8000/conversation/initialize?stop_id=${selectedStopId}&is_audio=${isVoiceCall}`
    if (send_thread_id) {
      url += `&thread_id=${threadId}`
    }
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to initialize chat');
      }

      const data = await response.json();
      
      const initialMessage: Message = {
        text: data.response,
        isUser: false,
        timestamp: formatTime()
      };

      setMessages([...messages, initialMessage]);
      setThreadId(data.thread_id.toString());
      
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages: [...messages, initialMessage],
        threadId: data.thread_id.toString()
      }));
      
      setIsInitialized(true);

      if (!isVoiceCall && data.repeat === true) {
        setInitAttempt(prev => prev + 1);
      } else {
        setInitAttempt(0);
      }

      if (isVoiceCall && data.response) {
        setConversationState('agentSpeaking');
        setIsRecording(false);
        await playAgentAudio(data.response);
      } else if (isVoiceCall) {
        startListening();
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

  // Update handleReset
  const handleReset = () => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    setMessages([]);
    localStorage.removeItem(`chat-data-${selectedStopId}`);
    setThreadId(selectedStopId.toString());
    setIsInitialized(false);
    setInitAttempt(0);
    
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
