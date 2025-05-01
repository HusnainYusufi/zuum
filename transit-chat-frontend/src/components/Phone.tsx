import React, { useRef, useEffect } from 'react';
import '../styles/Phone.css';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: string;
}

interface PhoneProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  isInitialized: boolean;
  onInitialize: () => void;
  isBlurred: boolean;
  onReset: () => void;
}

const Phone: React.FC<PhoneProps> = ({ 
  messages, 
  onSendMessage, 
  isDarkMode, 
  onToggleDarkMode,
  isInitialized,
  onInitialize,
  isBlurred,
  onReset
}) => {
  const [inputMessage, setInputMessage] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && isInitialized) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  return (
    <div className={`phone-container ${isDarkMode ? 'dark-mode' : ''} ${isBlurred ? 'blurred' : ''}`}>
      <div className="phone">
        <div className="phone-header">
          <div className="phone-notch"></div>
          <div className="status-bar">
            <span>9:41</span>
            <div className="status-icons">
              <span>📶</span>
              <span>🔋</span>
            </div>
          </div>
        </div>
        
        <div className="chat-header">
          <h2>Transit Chat</h2>
          <div className="header-buttons">
            <button 
              onClick={onReset}
              className="reset-button"
              aria-label="Reset Chat"
            >
              🔄
            </button>
      
          </div>
        </div>
        
        {!isInitialized && (
          <div className="initialize-container">
            <button 
              onClick={onInitialize}
              className="initialize-button"
              disabled={isBlurred}
            >
              Start Chat
            </button>
          </div>
        )}
        
        <div className="messages-container">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.isUser ? 'user-message' : 'bot-message'}`}
            >
              <div className="message-content">
                <p>{message.text}</p>
                <span className="message-time">{message.timestamp}</span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={isInitialized ? "Type your message..." : "Initialize chat to begin..."}
            className="message-input"
            disabled={!isInitialized}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={!isInitialized}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default Phone; 