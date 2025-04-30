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

  // Fetch all stops
  useEffect(() => {
    const fetchStops = async () => {
      try {
        const response = await fetch('http://localhost:8000/stops');
        if (!response.ok) {
          throw new Error('Failed to fetch stops');
        }
        const data = await response.json();
        setStops(data);
      } catch (error) {
        console.error('Error fetching stops:', error);
      }
    };

    fetchStops();
  }, []);

  // Handle stop selection
  const handleSelectStop = async (stopId: number) => {
    setSelectedStopId(stopId);
    
    try {
      // Fetch chat history for the selected stop
      const historyResponse = await fetch(`http://localhost:8000/chat-history/${stopId}`);
      if (historyResponse.ok) {
        const history = await historyResponse.json();
        
        // Convert history to message format
        const historyMessages: Message[] = [];
        for (const entry of history) {
          historyMessages.push({
            text: entry.user_message,
            isUser: true,
            timestamp: entry.timestamp
          });
          historyMessages.push({
            text: entry.bot_message,
            isUser: false,
            timestamp: entry.timestamp
          });
        }
        
        setMessages(historyMessages);
      } else {
        // If no history, initialize a new chat with the selected stop
        const response = await fetch(`http://localhost:8000/transit-chat?stop_id=${stopId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch initial message');
        }
        
        const data = await response.json();
        
        // Add initial bot message
        const botMessage: Message = {
          text: data.message,
          isUser: false,
          timestamp: formatTime()
        };
        setMessages([botMessage]);
      }
    } catch (error) {
      console.error('Error handling stop selection:', error);
      // Show error message
      const errorMessage: Message = {
        text: 'Sorry, there was an error connecting to the chat service.',
        isUser: false,
        timestamp: formatTime()
      };
      setMessages([errorMessage]);
    }
  };

  const handleSendMessage = async (message: string) => {
    // Add user message
    const userMessage: Message = {
      text: message,
      isUser: true,
      timestamp: formatTime()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      // Send message to backend with selected stop ID
      const response = await fetch('http://localhost:8000/transit-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message,
          stop_id: selectedStopId 
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      
      // Add bot response
      const botMessage: Message = {
        text: data.message,
        isUser: false,
        timestamp: formatTime()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      // Add error message
      const errorMessage: Message = {
        text: 'Sorry, there was an error processing your message.',
        isUser: false,
        timestamp: formatTime()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  // Initialize chat when no stop is selected
  useEffect(() => {
    if (stops.length === 0 || selectedStopId !== null) {
      return;
    }
    
    const initializeChat = async () => {
      try {
        const response = await fetch('http://localhost:8000/transit-chat', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const data = await response.json();
        
        // Add initial bot message
        const botMessage: Message = {
          text: data.message,
          isUser: false,
          timestamp: formatTime()
        };
        setMessages([botMessage]);
      } catch (error) {
        console.error('Error initializing chat:', error);
        const errorMessage: Message = {
          text: 'Sorry, there was an error connecting to the chat service.',
          isUser: false,
          timestamp: formatTime()
        };
        setMessages([errorMessage]);
      }
    };

    initializeChat();
  }, [stops]);

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
