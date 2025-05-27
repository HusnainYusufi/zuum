import React, { useEffect, useState } from 'react';
import '../styles/Sidebar.css';

// Define agent types
type AgentType = 'custom' | 'retell';

interface Stop {
  id: number;
  name: string;
  location: string;
  eta: string;
  is_delayed: boolean;
  is_origin?: boolean;
  is_destination?: boolean;
}

interface SidebarProps {
  stops: Stop[];
  selectedStopId: number | null;
  onSelectStop: (stopId: number) => void;
  isDarkMode: boolean;
  agentType: AgentType;
  onToggleAgentType: (type: AgentType) => void;
  isCallMode: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  stops, 
  selectedStopId, 
  onSelectStop, 
  isDarkMode,
  agentType,
  onToggleAgentType,
  isCallMode
}) => {
  return (
    <div className={`sidebar ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="sidebar-header">
        <h2>Transit Stops</h2>
      </div>
      
      <div className="stops-list">
        {stops.length === 0 ? (
          <div className="loading">Loading stops...</div>
        ) : (
          stops.map((stop) => (
            <div
              key={stop.id}
              className={`stop-item ${selectedStopId === stop.id ? 'selected' : ''} ${stop.is_origin ? 'origin' : ''} ${stop.is_destination ? 'destination' : ''}`}
              onClick={() => onSelectStop(stop.id)}
            >
              <div className="stop-info">
                <h3>{stop.name}</h3>
                <p className="location">{stop.location}</p>
                <p className="eta">ETA: {stop.eta}</p>
                {stop.is_delayed && (
                  <span className="delayed-badge">Delayed</span>
                )}
                {stop.is_origin && (
                  <span className="origin-badge">Origin</span>
                )}
                {stop.is_destination && (
                  <span className="destination-badge">Destination</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Agent Toggle at the bottom */}
      <div className="agent-toggle-container">
        <div className="agent-toggle-header">
          <span>Agent Selection</span>
        </div>
        <div className="agent-toggle">
        <button 
            className={`agent-toggle-button ${agentType === 'retell' ? 'active' : ''}`}
            onClick={() => onToggleAgentType('retell')}
            disabled={isCallMode} // Disable switching while in a call
          >
            <span role="img" aria-label="Retell">🤖</span> API call
          </button>
          <button 
            className={`agent-toggle-button ${agentType === 'custom' ? 'active' : ''}`}
            onClick={() => onToggleAgentType('custom')}
            disabled={isCallMode} // Disable switching while in a call
          >
            <span role="img" aria-label="Custom">🎙️</span> Custom Agent
          </button>
          
        </div>
      </div>
    </div>
  );
};

export default Sidebar; 