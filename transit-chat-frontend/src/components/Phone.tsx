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

// Define agent types
type AgentType = 'custom' | 'apicall';

interface PhoneProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  isInitialized: boolean;
  onInitialize: (isVoiceCall?: boolean, send_thread_id?: boolean) => void;
  isBlurred: boolean;
  onReset: () => void;
  isCallMode?: boolean;
  onToggleCallMode?: () => void;
  audioStream?: MediaStream | null;
  isRecording?: boolean;
  onToggleRecording?: () => void;
  conversationState?: ConversationState;
  agentType: AgentType;
  conversationType?: string;
  setConversationType?: (type: string) => void;
  query?: string;
  setQuery?: (query: string) => void;
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
  conversationState = 'idle',
  agentType = 'custom',
  conversationType = 'workflow',
  setConversationType = () => {},
  query = '',
  setQuery = () => {}
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

  // Determine if the call buttons should be disabled
  const shouldDisableCallButton = () => {
    if (agentType === 'apicall') {
      // For API call, only disable during processing
      return conversationState === 'processing';
    } else {
      // For custom agent, standard rules
      return conversationState === 'processing';
    }
  };

  // Get button text/label based on agent type and state
  const getCallButtonLabel = () => {
    if (agentType === 'apicall') {
      return isRecording ? "End API Call" : "Start API Call";
    } else {
      return isCallMode ? "Switch to Text Mode" : "Switch to Call Mode";
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
          <h2>
            {agentType === 'apicall' 
              ? 'API call' 
              : 'Custom Agent Chat'
            }
          </h2>
          {isInitialized && (
          <button
            onClick={onToggleCallMode}
            className={`mode-toggle-button ${isCallMode ? 'active' : ''}`}
            aria-label={getCallButtonLabel()}
            disabled={shouldDisableCallButton()}
          >
            <BiPhone size={24} />
          </button>
          )}
        </div>
        
        <div className="conversation-type-switch">
          <label className="switch-label">
            <input
              type="radio"
              name="conversationType"
              value="workflow"
              checked={conversationType === 'workflow'}
              onChange={() => setConversationType('workflow')}
            />
            <span>Workflow</span>
          </label>
          <label className="switch-label">
            <input
              type="radio"
              name="conversationType"
              value="checkin"
              checked={conversationType === 'checkin'}
              onChange={() => setConversationType('checkin')}
            />
            <span>Check-in</span>
          </label>
        </div>
        
        {!isInitialized && (
          <div className="initialize-container">
            {/* Show query input for check-in mode */}
            {conversationType === 'checkin' && (
              <div className="query-input-section">
                <label className="query-input-label">What to ask?</label>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter your query..."
                  className="message-input query-input"
                />
              </div>
            )}
            
            {/* Only show text chat button for custom agent */}
            {agentType === 'custom' && (
              <button 
                onClick={() => onInitialize(false)}
                className="initialize-button"
                disabled={isBlurred}
              >
                <BiMessageRounded size={18} style={{ marginRight: '5px' }} />
                Start Text Chat
              </button>
            )}
            <button 
              onClick={() => onInitialize(true)}
              className={`initialize-button voice-call-button ${agentType === 'apicall' ? 'apicall-single-button' : ''}`}
              disabled={isBlurred}
            >
              <BiPhone size={18} style={{ marginRight: '5px' }} />
              {agentType === 'apicall' 
                ? 'Start API call' 
                : 'Start Voice Call'
              }
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
          {conversationType === 'checkin' && (
            <label className="query-input-label">Query:</label>
          )}
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
          agentType={agentType}
        />
      </div>
    </div>
  );
};

export default Phone; 