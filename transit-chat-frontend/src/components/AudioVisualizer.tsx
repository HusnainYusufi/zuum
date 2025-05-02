import React, { useRef, useEffect } from 'react';
import '../styles/AudioVisualizer.css';
import { BiMicrophone, BiPhoneOff } from 'react-icons/bi';

// Define the ConversationState type
type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';

interface AudioVisualizerProps {
  isActive: boolean;
  isRecording: boolean;
  audioStream?: MediaStream | null;
  onToggle: () => void;
  onEndCall: () => void;
  isDarkMode: boolean;
  isCallMode: boolean;
  onToggleCallMode: () => void;
  conversationState?: ConversationState;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ 
  isActive, 
  audioStream, 
  onToggle,
  onEndCall,
  isRecording,
  isDarkMode,
  isCallMode,
  onToggleCallMode,
  conversationState = 'idle'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !isActive || !audioStream) return;

    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    analyserRef.current = analyser;
    
    const source = audioContext.createMediaStreamSource(audioStream);
    source.connect(analyser);
    
    analyser.fftSize = 512; // Increased for better resolution
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d')!;

    // Handle high DPI displays
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    // Set the canvas size accounting for device pixel ratio
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    // Scale the context to ensure correct drawing operations
    ctx.scale(dpr, dpr);

    // Set canvas CSS size
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    
    const draw = () => {
      const WIDTH = rect.width;
      const HEIGHT = rect.height;
      
      analyser.getByteFrequencyData(dataArray);
      
      ctx.clearRect(0, 0, WIDTH * dpr, HEIGHT * dpr);
      
      // Enable anti-aliasing
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      const centerX = WIDTH / 2;
      const centerY = HEIGHT / 2;
      const radius = Math.min(WIDTH, HEIGHT) / 2 - 20; // Slightly smaller radius for better visibility
      
      // Draw background circle with smooth edges
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = isDarkMode ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.3)';
      ctx.fill();
      
      // Draw visualization with smooth lines
      ctx.beginPath();
      for (let i = 0; i < bufferLength; i++) {
        const value = dataArray[i];
        const percent = value / 255;
        
        const angle = (i / bufferLength) * Math.PI * 2;
        const length = radius * (0.7 + percent * 0.3);
        
        const x = centerX + Math.cos(angle) * length;
        const y = centerY + Math.sin(angle) * length;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      ctx.closePath();
      ctx.strokeStyle = isDarkMode ? 'rgba(255, 255, 255, 0.8)' : 'rgba(75, 0, 130, 0.8)';
      ctx.lineWidth = 2;
      
      // Enable anti-aliasing for the stroke
      ctx.shadowBlur = 4;
      ctx.shadowColor = isDarkMode ? 'rgba(255, 255, 255, 0.5)' : 'rgba(75, 0, 130, 0.5)';
      ctx.stroke();
      ctx.shadowBlur = 0;
      
      animationFrameRef.current = requestAnimationFrame(draw);
    };
    
    draw();
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      audioContext.close();
    };
  }, [isActive, audioStream, isRecording, isDarkMode]);

  const buttonBaseStyle = {
    padding: '12px',
    border: 'none',
    borderRadius: '50%',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
  };

  // Get status text based on conversation state
  const getStatusText = () => {
    switch (conversationState) {
      case 'listening':
        return 'Listening...';
      case 'processing':
        return 'Processing...';
      case 'agentSpeaking':
        return 'Agent is speaking...';
      case 'idle':
      default:
        return isActive ? 'Ready' : '';
    }
  };

  // Get status color based on conversation state
  const getStatusColor = () => {
    switch (conversationState) {
      case 'listening':
        return '#4CAF50'; // Green
      case 'processing':
        return '#FFC107'; // Amber
      case 'agentSpeaking':
        return '#2196F3'; // Blue
      case 'idle':
      default:
        return '#9E9E9E'; // Gray
    }
  };

  return (
    <div className={`audio-visualizer ${isActive ? 'active' : ''} ${isDarkMode ? 'dark-mode' : ''}`}>
      <canvas ref={canvasRef} />
      
      {/* Status indicator */}
      {isActive && (
        <div 
          style={{
            position: 'absolute',
            top: '15px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: isDarkMode ? 'rgba(0, 0, 0, 0.6)' : 'rgba(255, 255, 255, 0.6)',
            color: getStatusColor(),
            padding: '4px 12px',
            borderRadius: '16px',
            fontSize: '12px',
            fontWeight: 'bold',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <span 
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getStatusColor(),
              display: 'inline-block',
              animation: conversationState === 'listening' ? 'pulse 1.5s infinite' : 'none'
            }}
          ></span>
          {getStatusText()}
        </div>
      )}
      
      <div 
        style={{
          position: 'absolute',
          bottom: '20px',
          left: isActive ? '50%' : '150%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '16px',
          pointerEvents: 'auto',
          transition: 'left 0.3s ease'
        }}
      >
        <button 
          onClick={onToggle}
          style={{
            ...buttonBaseStyle,
            backgroundColor: isRecording 
              ? 'var(--error-color, #ff4444)' 
              : 'var(--button-bg, #ffffff)',
            color: isRecording 
              ? '#ffffff' 
              : 'var(--button-color, #333333)',
            transform: `scale(${isRecording ? 1.1 : 1})`,
          }}
          title={isRecording ? "Stop Recording" : "Start Recording"}
        >
          <BiMicrophone size={24} />
        </button>
        <button 
          onClick={onToggleCallMode}
          style={{
            ...buttonBaseStyle,
            backgroundColor: 'var(--error-color, #ff4444)',
            color: '#ffffff',
          }}
          className="end-call-button"
          title="End Call"
        >
          <BiPhoneOff size={24} />
        </button>
      </div>
    </div>
  );
};

export default AudioVisualizer; 