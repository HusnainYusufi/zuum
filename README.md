# Voice Freight Broker Project

A backend service for freight broker voice call processing with web interface, powered by LangChain/LangGraph for AI orchestration.

## Overview

This project provides an automated system for handling freight broker voice calls, including:
- Check-in workflows for drivers
- Journey tracking (Origin → Transit → Destination)
- Real-time call processing with Retell AI integration
- Web dashboard for monitoring and management
- SQLite database for persistent storage

## Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (for containerized deployment)
- API Keys:
  - OpenAI API key
  - Retell AI API key and agent IDs
  - Ngrok authentication token (for webhook tunneling)

## Project Structure

```
voice_freight_broker/
├── templates/              # HTML templates for web interface
│   ├── transit-dashboard.html     # Main monitoring dashboard
│   └── checkin.html       # Driver check-in interface
├── services/
│   └── langrapghs/        # LangGraph workflows
│       ├── prompts/       # AI prompt templates
│       └── tests/         # Test suites and conversations
├── static/                # Static assets (CSS, JS)
├── routes/                # API route handlers
├── db_models.py           # SQLAlchemy database models
├── main.py                # FastAPI application entry point
├── init_db.py             # Database initialization script
├── reinit_db.py           # Database reset utility
├── llm_config.py          # LLM configuration
├── requirements.txt       # Python dependencies
├── env.example            # Environment variables template
├── docker-compose.yml     # Docker services configuration
├── docker-scripts.bat     # Windows Docker management script
├── docker-scripts.sh      # Unix/Linux Docker management script
└── Dockerfile             # Container image definition
```

## Quick Start with Docker (Recommended)

### 1. Clone the repository
```bash
git clone <repository-url>
cd voice_freight_broker
```

### 2. Set up environment variables
Copy the example environment file and configure your API keys:

```bash
# Copy the template
cp env.example .env

# Edit .env with your actual API keys:
# - OPENAI_API_KEY
# - RETELL_API_KEY
# - WORKFLOW_RETELL_AGENT_ID
# - CHECKIN_RETELL_AGENT_ID
# - NGROK_AUTH_TOKEN
# - LANGSMITH_API_KEY (optional)
```

### 3. Start the application

**For Windows:**
```bash
docker-scripts.bat start
```

**For macOS/Linux:**
```bash
chmod +x docker-scripts.sh
./docker-scripts.sh start
```

The application will be available at:
- Web Dashboard: http://localhost:8000/transit-dashboard
- Check-in Interface: http://localhost:8000/checkin
- API Documentation: http://localhost:8000/docs
- Ngrok Dashboard: http://localhost:4040 (for webhook inspection)

## Environment Configuration

The `env.example` file contains all configurable environment variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Ngrok Configuration
NGROK_AUTH_TOKEN=your_ngrok_auth_token_here

# Retell AI Configuration
RETELL_API_KEY=your_retell_api_key_here
WORKFLOW_RETELL_AGENT_ID=your_workflow_agent_id_here
CHECKIN_RETELL_AGENT_ID=your_checkin_agent_id_here

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=sqlite:///./data/transit.db

# Optional: CORS Configuration
# CORS_ORIGINS=["http://localhost:3000"]

# Optional: API Rate Limiting
API_RATE_LIMIT=100
```

## Database Models

The application uses SQLAlchemy with SQLite for data persistence. Key models include:

### Stop
- Represents pickup/delivery locations
- Tracks location details, ETAs, delays, and status
- Fields: name, location, eta, cross_street, nearest_highway, delay info

### Journey
- Manages the complete trip lifecycle
- States: ORIGIN (0), TRANSIT (1), DESTINATION (2)
- Links multiple stops together

### CheckIn
- Records driver check-in events
- Stores AI analysis and issue flagging
- Links to stops and includes load information

### RetellCall
- Stores voice call data from Retell AI
- Includes transcripts, recordings, and metadata
- Associated with check-ins

### Notification
- System notifications and alerts
- Severity levels and read status
- Linked to specific stops when applicable

## Docker Management Scripts

The project includes platform-specific scripts for easy Docker management:

### Windows (docker-scripts.bat)
```bash
docker-scripts.bat start     # Start all services
docker-scripts.bat stop      # Stop all services
docker-scripts.bat restart   # Restart services
docker-scripts.bat logs      # View logs
docker-scripts.bat status    # Check service status
docker-scripts.bat backup    # Backup database
docker-scripts.bat cleanup   # Remove containers/volumes
docker-scripts.bat help      # Show all commands
```

### macOS/Linux (docker-scripts.sh)
```bash
./docker-scripts.sh start    # Start all services
./docker-scripts.sh stop     # Stop all services
./docker-scripts.sh restart  # Restart services
./docker-scripts.sh logs     # View logs
./docker-scripts.sh status   # Check service status
./docker-scripts.sh backup   # Backup database
./docker-scripts.sh cleanup  # Remove containers/volumes
./docker-scripts.sh help     # Show all commands
```

## Web Interface

The application provides two main web interfaces:

### Dashboard (`/transit-dashboard`)
- Real-time monitoring of journeys and stops
- View active trips and their current state
- Check recent notifications and alerts
- Monitor system health and statistics

### Check-in Interface (`/checkin`)
- Driver self-service check-in portal
- Voice call integration with Retell AI
- Automatic issue detection and flagging
- Load and location verification

## API Endpoints

Key API endpoints include:
- `POST /retell-webhook` - Webhook for Retell AI call events
- `GET /api/journeys` - List all journeys
- `GET /api/stops` - List all stops
- `GET /api/notifications` - Get system notifications
- `POST /api/checkin` - Create new check-in

Full API documentation available at http://localhost:8000/docs when running.

## Dependencies

Key Python packages (see `requirements.txt` for full list):
- **langgraph** - AI workflow orchestration
- **langchain_openai** - OpenAI integration
- **fastapi[all]** - Web framework and API
- **sqlalchemy** - Database ORM
- **jinja2** - Template engine
- **pyngrok** - Ngrok tunnel management
- **sentence-transformers** - Text embeddings
- **rouge-score** - Text similarity metrics

## Manual Setup (Without Docker)

If you prefer to run without Docker:

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your API keys
```

4. Initialize the database:
```bash
python init_db.py
```

5. Run the application:
```bash
python main.py
```

## Troubleshooting

### Docker Issues
- **Docker not running**: Ensure Docker Desktop is started
- **Port conflicts**: Check if ports 8000 or 4040 are in use
- **Permission issues (Linux)**: Add user to docker group: `sudo usermod -aG docker $USER`

### Application Issues
- **Database errors**: Run `python reinit_db.py` to reset the database
- **API key errors**: Verify all required keys in `.env` file
- **Webhook issues**: Check Ngrok dashboard at http://localhost:4040

### Common Solutions
1. Clean rebuild: `docker-scripts.sh cleanup` then `docker-scripts.sh start`
2. View logs: `docker-scripts.sh logs` to see detailed error messages
3. Database backup: `docker-scripts.sh backup` before making changes

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test suites
python services/langrapghs/tests/test_origin.py
python services/langrapghs/tests/test_transit_offtime.py
python services/langrapghs/tests/test_destination.py
```

### Adding New Features
1. Database changes: Update `db_models.py` and run migrations
2. New routes: Add to `routes/` directory
3. Template changes: Modify files in `templates/`
4. LangGraph workflows: Update `services/langrapghs/`

## Support

For issues or questions:
1. Check the logs: `docker-scripts.sh logs`
2. Review the API docs: http://localhost:8000/docs
3. Inspect webhooks: http://localhost:4040
4. Contact the development team 
