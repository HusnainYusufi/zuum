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
}

const Phone: React.FC<PhoneProps> = ({ messages, onSendMessage, isDarkMode, onToggleDarkMode }) => {
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
    if (inputMessage.trim()) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  return (
    <div className={`phone-container ${isDarkMode ? 'dark-mode' : ''}`}>
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
        <div className="phone-content">
          <div className="chat-header">
            <h2>Transit Chat</h2>
            <button 
              onClick={onToggleDarkMode} 
              className="theme-toggle"
              aria-label={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
          </div>
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
              placeholder="Type your message..."
              className="message-input"
            />
            <button type="submit" className="send-button">
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Phone; 