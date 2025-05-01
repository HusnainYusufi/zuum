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

  const handleInitializeChat = async () => {
    if (!selectedStopId) {
      console.error('No stop selected');
      return;
    }

    setIsBlurred(true);
    try {
      const response = await fetch(`http://localhost:8000/transit-chat/initialize?stop_id=${selectedStopId}`);
      
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
      
      // Store chat data
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages: [initialMessage],
        threadId: data.thread_id.toString()
      }));
      
      setIsInitialized(true);
    } catch (error) {
      console.error('Error initializing chat:', error);
      const errorMessage: Message = {
        text: 'Sorry, there was an error initializing the chat.',
        isUser: false,
        timestamp: formatTime()
      };
      setMessages([errorMessage]);
      localStorage.setItem(`chat-data-${selectedStopId}`, JSON.stringify({
        messages: [errorMessage],
        threadId: selectedStopId.toString()
      }));
    } finally {
      setIsBlurred(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!threadId) {
      console.error('Chat not initialized');
      return;
    }

    const userMessage: Message = {
      text: message,
      isUser: true,
      timestamp: formatTime()
    };
    
    // Add user message and save to localStorage
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
      console.log('Sending request with:', { message, thread_id: threadId });
      const response = await fetch(`http://localhost:8000/transit-chat/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          thread_id: threadId.toString()
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error('Response error:', response.status, errorData);
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      console.log(data);
      const botMessage: Message = {
        text: data,
        isUser: false,
        timestamp: formatTime()
      };
      
      // Add bot message and save to localStorage
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
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        text: 'Sorry, there was an error processing your message.',
        isUser: false,
        timestamp: formatTime()
      };
      
      // Add error message and save to localStorage
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
    
    // Set initialized to true so user can start chatting immediately
    setIsInitialized(false);
  };

  // Initialize chat when no stop is selected
  // useEffect(() => {
  //   if (stops.length === 0 || selectedStopId !== null) {
  //     return;
  //   }
    
  //   const initializeChat = async () => {
  //     try {
  //       const response = await fetch('http://localhost:8000/transit-chat', {
  //         method: 'GET',
  //         headers: {
  //           'Content-Type': 'application/json',
  //         }
  //       });

  //       if (!response.ok) {
  //         throw new Error('Network response was not ok');
  //       }

  //       const data = await response.json();
        
  //       // Add initial bot message
  //       const botMessage: Message = {
  //         text: data.message,
  //         isUser: false,
  //         timestamp: formatTime()
  //       };
  //       setMessages([botMessage]);
  //     } catch (error) {
  //       console.error('Error initializing chat:', error);
  //       const errorMessage: Message = {
  //         text: 'Sorry, there was an error connecting to the chat service.',
  //         isUser: false,
  //         timestamp: formatTime()
  //       };
  //       setMessages([errorMessage]);
  //     }
  //   };

  //   initializeChat();
  // }, [stops]);

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
