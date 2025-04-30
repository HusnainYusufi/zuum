import React from 'react';
import '../styles/Sidebar.css';

interface Stop {
  id: number;
  name: string;
  location: string;
  eta: string;
  is_delayed: boolean;
}

interface SidebarProps {
  stops: Stop[];
  selectedStopId: number | null;
  onSelectStop: (stopId: number) => void;
  isDarkMode: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ stops, selectedStopId, onSelectStop, isDarkMode }) => {
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
              className={`stop-item ${selectedStopId === stop.id ? 'selected' : ''}`}
              onClick={() => onSelectStop(stop.id)}
            >
              <div className="stop-info">
                <h3>{stop.name}</h3>
                <p className="location">{stop.location}</p>
                <p className="eta">ETA: {stop.eta}</p>
                {stop.is_delayed && (
                  <span className="delayed-badge">Delayed</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Sidebar; 