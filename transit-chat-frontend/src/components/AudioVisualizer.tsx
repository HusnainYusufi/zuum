import React, { useRef, useEffect, useState } from 'react';
import '../styles/AudioVisualizer.css';
import { BiMicrophone, BiPhoneOff, BiStop } from 'react-icons/bi';

// Define the ConversationState type
type ConversationState = 'listening' | 'processing' | 'agentSpeaking' | 'idle';

// Define agent types
type AgentType = 'custom' | 'retell';

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
  agentType?: AgentType;
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
  conversationState = 'idle',
  agentType = 'custom'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const [agentAudioContext, setAgentAudioContext] = useState<AudioContext | null>(null);

  // Add a method to connect to audio element
  // This would be called from App.tsx when AI audio is playing
  useEffect(() => {
    // Listen for when AI audio starts playing
    const handleAIAudioStart = (event: CustomEvent) => {
      const audio = event.detail.audioElement as HTMLAudioElement;
      if (audio && conversationState === 'agentSpeaking') {
        try {
          // Create new audio context
          const audioContext = new AudioContext();
          setAgentAudioContext(audioContext);
          
          // Create an analyzer
          const analyser = audioContext.createAnalyser();
          analyserRef.current = analyser;
          
          // Connect the audio element to the analyzer
          const source = audioContext.createMediaElementSource(audio);
          source.connect(analyser);
          
          // Also connect to destination so we can hear it
          analyser.connect(audioContext.destination);
          
          // Configure analyzer
          analyser.fftSize = 512;
        } catch (error) {
          console.error('Error connecting to AI audio:', error);
        }
      }
    };

    // Add event listener
    document.addEventListener('ai-audio-playing', handleAIAudioStart as EventListener);
    
    return () => {
      // Remove event listener on cleanup
      document.removeEventListener('ai-audio-playing', handleAIAudioStart as EventListener);
    };
  }, [conversationState]);

  // Effect for agent audio visualization
  useEffect(() => {
    // Only set up visualization when agent is speaking and we have an analyzer
    if (!canvasRef.current || conversationState !== 'agentSpeaking' || !analyserRef.current) {
      // Clean up any existing animation when not in agent speaking mode
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    const analyser = analyserRef.current;
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
      
      // Create a non-sequential mapping for frequency bands to circle positions
      const pointCount = 180; // Number of points to draw around the circle
      
      // Create chaotic frequency mapping but keep it within bounds
      const frequencyMapping = Array(pointCount).fill(0).map((_, i) => {
        // Use a chaotic but controlled pattern that stays within bounds
        return Math.floor(Math.abs((i * 17 + Math.sin(i) * 30) % bufferLength));
      });
      
      // Draw sequentially around the circle to maintain shape
      // but use non-sequential frequency data for audio response
      ctx.beginPath();
      
      // Start at point 0 and draw clockwise around the circle
      for (let i = 0; i < pointCount; i++) {
        // Get frequency data using our chaotic mapping
        const freqIndex = frequencyMapping[i];
        const value = dataArray[freqIndex];
        const percent = value / 255;
        
        // Calculate point position on circle (sequential around the circle)
        const angle = (i / pointCount) * Math.PI * 2;
        const length = radius * (0.9 + percent * 0.1);
        
        const x = centerX + Math.cos(angle) * length;
        const y = centerY + Math.sin(angle) * length;
        
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      
      // Close the path
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
    };
  }, [conversationState, isDarkMode, analyserRef.current]);

  // Cleanup all audio contexts on unmount
  useEffect(() => {
    return () => {
      if (agentAudioContext) {
        agentAudioContext.close();
      }
    };
  }, [agentAudioContext]);

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
    if (agentType === 'retell') {
      if (isRecording) {
        return 'Retell Call Active';
      } else {
        return isActive ? 'Call Connected (Mic Muted)' : 'Call Ready';
      }
    }
    
    switch (conversationState) {
      case 'listening':
        return isRecording ? 'Listening...' : 'Paused';
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
    if (agentType === 'retell' && isRecording) {
      return '#E91E63'; // Pink for Retell
    }
    
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

  // Check if visualizer should be active (only during agent speaking)
  const isVisualizerActive = isActive && conversationState === 'agentSpeaking';

  // Get microphone button tooltip based on agent type
  const getMicButtonTooltip = () => {
    if (agentType === 'retell') {
      return isRecording ? "Mute Microphone" : "Unmute Microphone";
    } else {
      return isRecording ? "Stop Recording & Send" : "Resume Recording";
    }
  };

  return (
    <div className={`audio-visualizer ${isActive ? 'active' : ''} ${isDarkMode ? 'dark-mode' : ''}`}>
      <canvas 
        ref={canvasRef} 
        className={isVisualizerActive ? 'visible' : 'hidden'}
      />
      
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
              animation: conversationState === 'agentSpeaking' ? 'pulse 1.5s infinite' : 'none'
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
          className={`mic-button ${agentType === 'retell' ? `retell-mic-button ${isRecording ? 'active' : 'muted'}` : ''}`}
          style={{
            ...buttonBaseStyle,
            backgroundColor: agentType === 'retell' 
              ? (isRecording ? '#4CAF50' : '#ff6b6b') 
              : isRecording 
                ? 'var(--button-bg, #ffffff)' 
                : 'var(--error-color, #ff4444)',
            color: '#ffffff',
            transform: `scale(${isRecording ? 1.1 : 1})`,
            position: 'relative'
          }}
          title={getMicButtonTooltip()}
          disabled={(agentType !== 'retell') && (conversationState === 'processing' || conversationState === 'agentSpeaking')}
        >
          {isRecording ? <BiStop size={24} /> : <BiMicrophone size={24} />}
          {agentType === 'retell' && (
            <span 
              style={{
                position: 'absolute',
                top: '-6px',
                right: '-6px',
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                backgroundColor: isRecording ? '#4CAF50' : '#f44336',
                border: '2px solid white',
                display: 'block',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
              }}
            />
          )}
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