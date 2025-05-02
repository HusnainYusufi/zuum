import React, { useRef, useEffect, useState } from 'react';
import { BiReset, BiMessageRounded, BiMicrophone, BiPhoneOff, BiPhone } from 'react-icons/bi';
import '../styles/Phone.css';
import AudioVisualizer from './AudioVisualizer';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: string;
}

// Define the ConversationState type
type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';

interface PhoneProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  isInitialized: boolean;
  onInitialize: (isVoiceCall?: boolean) => void;
  isBlurred: boolean;
  onReset: () => void;
  isCallMode?: boolean;
  onToggleCallMode?: () => void;
  audioStream?: MediaStream | null;
  isRecording?: boolean;
  onToggleRecording?: () => void;
  conversationState?: ConversationState;
}

const Phone: React.FC<PhoneProps> = ({ 
  messages, 
  onSendMessage, 
  isDarkMode, 
  onToggleDarkMode,
  isInitialized,
  onInitialize,
  isBlurred,
  onReset,
  isCallMode = false,
  onToggleCallMode = () => {},
  audioStream = null,
  isRecording = false,
  onToggleRecording = () => {},
  conversationState = 'idle'
}) => {
  const [inputMessage, setInputMessage] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Effect to update UI when conversation state changes
  useEffect(() => {
    if (conversationState === 'processing' || conversationState === 'agentSpeaking') {
      // Ensure the button is disabled by visually updating
      // This is now handled via the disabled property on the button
    }
  }, [conversationState]);

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
          {isInitialized && (
            <button 
            onClick={onReset}
            className="reset-button"
            aria-label="Reset Chat"
          >
            <BiReset />
          </button>
          )}
          <h2>Transit Chat</h2>
          {isInitialized && (
          <button
            onClick={onToggleCallMode}
            className={`mode-toggle-button ${isCallMode ? 'active' : ''}`}
            aria-label={isCallMode ? "Switch to Text Mode" : "Switch to Call Mode"}
            disabled={conversationState === 'processing'}
          >
            <BiPhone size={24} />
          </button>
          )}
        </div>
        
        {!isInitialized && (
          <div className="initialize-container">
            <button 
              onClick={() => onInitialize(false)}
              className="initialize-button"
              disabled={isBlurred}
            >
              <BiMessageRounded size={18} style={{ marginRight: '5px' }} />
              Start Chat
            </button>
            <button 
              onClick={() => onInitialize(true)}
              className="initialize-button voice-call-button"
              disabled={isBlurred}
            >
              <BiPhone size={18} style={{ marginRight: '5px' }} />
              Start Voice Call
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
        
        {isInitialized && (
        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={isInitialized ? "Type your message..." : "Initialize chat to begin..."}
            className="message-input"
            disabled={!isInitialized || (isCallMode && conversationState !== 'idle')}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={!isInitialized || (isCallMode && conversationState !== 'idle')}
          >
            Send
          </button>
        </form>
        )}
        <AudioVisualizer 
          onEndCall={onToggleCallMode}
          isActive={isCallMode} 
          audioStream={audioStream}
          onToggle={onToggleRecording}
          isRecording={isRecording}
          isDarkMode={isDarkMode}
          isCallMode={isCallMode}
          onToggleCallMode={onToggleCallMode}
          conversationState={conversationState}
        />
      </div>
    </div>
  );
};

export default Phone; 