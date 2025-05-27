# Voice Freight Broker Project

This project consists of a backend service for broker message processing and a frontend chat interface.

## Prerequisites

1. Python 3.8 or higher
2. Node.js 16 or higher
3. pnpm (for frontend)
4. OpenAI API key
5. Docker and Docker Compose (for containerized deployment)

## Docker Setup (Recommended)

### Installing Docker

#### Windows
1. Download Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Run the installer and follow the setup wizard
3. Restart your computer when prompted
4. Launch Docker Desktop and wait for it to start
5. Verify installation by opening PowerShell/Command Prompt and running:
   ```bash
   docker --version
   docker-compose --version
   ```

#### macOS
1. Download Docker Desktop from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Drag Docker.app to your Applications folder
3. Launch Docker Desktop from Applications
4. Verify installation by opening Terminal and running:
   ```bash
   docker --version
   docker-compose --version
   ```

#### Linux (Ubuntu/Debian)
```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install docker.io docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker-compose --version
```

### Quick Start with Docker

1. Clone the repository and navigate to the project directory

2. Create a `.env` file with your API keys and configuration:
   ```bash
   # For Windows (PowerShell/Command Prompt)
   echo LANGSMITH_TRACING=true > .env
   echo LANGSMITH_ENDPOINT=https://api.smith.langchain.com >> .env
   echo LANGSMITH_API_KEY=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 >> .env
   echo LANGSMITH_PROJECT=voice_freight_broker >> .env
   echo OPENAI_API_KEY=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 >> .env
   echo NGROK_AUTH_TOKEN=2xNZg1ikvgD >> .env
   ```

   ```bash
   # For macOS/Linux
   cat > .env << EOF
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=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
   LANGSMITH_PROJECT=voice_freight_broker
   OPENAI_API_KEY=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
   NGROK_AUTH_TOKEN=2xNZg1ikvgD
   EOF
   ```

   **Or manually create a `.env` file** in the project root with the following content:
   ```env
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=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
   LANGSMITH_PROJECT=voice_freight_broker
   OPENAI_API_KEY=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
   NGROK_AUTH_TOKEN=2xNZg1ikvgD
   ```

3. **For Windows users**, run:
   ```bash
   docker-scripts.bat start
   ```

4. **For macOS/Linux users**, run:
   ```bash
   chmod +x docker-scripts.sh
   ./docker-scripts.sh start
   ```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Console Output After Startup

Once Docker has successfully started all services, you will see a success message in your console with clickable links:

```
[SUCCESS] Application started successfully
[INFO] Frontend: http://localhost:3000
[INFO] Backend API: http://localhost:8000
[INFO] API Docs: http://localhost:8000/docs
```

These links are clickable in most modern terminals and will open directly in your default browser. You can also copy and paste these URLs manually if your terminal doesn't support clickable links.

### Environment Variables Explained

The application uses the following environment variables:

- **`LANGSMITH_TRACING`**: Enables LangSmith tracing for debugging and monitoring LangChain operations
- **`LANGSMITH_ENDPOINT`**: LangSmith API endpoint for tracing data
- **`LANGSMITH_API_KEY`**: Your LangSmith API key for authentication
- **`LANGSMITH_PROJECT`**: Project name in LangSmith for organizing traces
- **`OPENAI_API_KEY`**: Your OpenAI API key for GPT model access
- **`NGROK_AUTH_TOKEN`**: Ngrok authentication token for creating secure tunnels (optional for local development)

> **Security Note**: The `.env` file contains sensitive API keys. Never commit this file to version control. The project includes `.env` in `.gitignore` to prevent accidental commits.

### Docker Script Commands

The project includes convenient scripts for managing the Docker environment:

#### Windows (docker-scripts.bat)
```bash
# Start the application (build and run all services)
docker-scripts.bat start

# Stop all services
docker-scripts.bat stop

# Restart all services
docker-scripts.bat restart

# View logs for all services
docker-scripts.bat logs

# View logs for specific service (backend or frontend)
docker-scripts.bat logs backend
docker-scripts.bat logs frontend

# Build Docker images only
docker-scripts.bat build

# Check application and Docker status
docker-scripts.bat status

# Clean up Docker resources (containers, images, volumes)
docker-scripts.bat cleanup

# Backup database
docker-scripts.bat backup

# Show help and available commands
docker-scripts.bat help
```

#### macOS/Linux (docker-scripts.sh)
```bash
# Start the application (build and run all services)
./docker-scripts.sh start

# Stop all services
./docker-scripts.sh stop

# Restart all services
./docker-scripts.sh restart

# View logs for all services
./docker-scripts.sh logs

# View logs for specific service (backend or frontend)
./docker-scripts.sh logs backend
./docker-scripts.sh logs frontend

# Build Docker images only
./docker-scripts.sh build

# Check application and Docker status
./docker-scripts.sh status

# Clean up Docker resources (containers, images, volumes)
./docker-scripts.sh cleanup

# Backup database
./docker-scripts.sh backup

# Show help and available commands
./docker-scripts.sh help
```

### Docker Environment Management

The scripts automatically handle:
- **Environment Setup**: Creates `.env` file from template if missing
- **Docker Health Check**: Verifies Docker is running before executing commands
- **Service Management**: Builds, starts, stops, and monitors all services
- **Log Management**: Easy access to application logs
- **Resource Cleanup**: Removes unused containers, images, and volumes
- **Database Backup**: Creates timestamped database backups

### Troubleshooting Docker Issues

1. **Docker not running**:
   - Ensure Docker Desktop is started
   - Check Docker service status: `docker info`

2. **Port conflicts**:
   - Stop other services using ports 3000 or 8000
   - Or modify ports in `docker-compose.yml`

3. **Permission issues (Linux)**:
   - Add user to docker group: `sudo usermod -aG docker $USER`
   - Log out and back in

4. **Build failures**:
   - Clean up resources: `./docker-scripts.sh cleanup`
   - Rebuild: `./docker-scripts.sh build`

## Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory with your OpenAI API key:
```bash
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

5. Run the backend server:
```bash
python3 main.py
```

The backend server should now be running on `http://localhost:8000`.

## Frontend Setup

1. Navigate to the frontend directory:
```bash
cd transit-chat-frontend
```

2. Install dependencies using pnpm:
```bash
pnpm install
```

3. Start the development server:
```bash
npm start
```

The frontend application should now be running on `http://localhost:3000`.

## Running Tests

The project includes a comprehensive test suite for broker message evaluation. To run the tests:

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install test dependencies:
```bash
pip install sentence-transformers numpy rouge-score langchain langgraph
```

3. Run the test files:
```bash
# Test Origin Conversations
python services/langrapghs/tests/test_origin.py

# Test Transit Conversations
python services/langrapghs/tests/test_transit_offtime.py

# Test Destination Conversations
python services/langrapghs/tests/test_destination.py
```

## Project Structure

```
.
├── backend/
│   ├── services/
│   │   └── langrapghs/
│   │       ├── tests/
│   │       │   ├── test_origin.py
│   │       │   ├── test_transit_offtime.py
│   │       │   ├── test_destination.py
│   │       │   └── README.md
│   │       └── real_conversations/
│   │           ├── test_origin_conversation.json
│   │           ├── test_transit_conversation.json
│   │           └── test_destination_conversation.json
│   ├── main.py
│   ├── requirements.txt
│   └── .env
└── transit-chat-frontend/
    ├── package.json
    ├── pnpm-lock.yaml
    └── src/
```

## Dependencies

### Backend Dependencies
- FastAPI
- OpenAI
- sentence-transformers
- numpy
- rouge-score
- langchain
- langgraph
- python-dotenv

### Frontend Dependencies
- React
- TypeScript
- Material-UI
- Axios
- React Router

## Troubleshooting

### Backend Issues
1. **API Key Issues**:
   - Ensure your `.env` file contains the correct OpenAI API key
   - Check if the API key has sufficient quota

2. **Port Conflicts**:
   - If port 8000 is in use, modify the port in `main.py`

3. **Dependency Issues**:
   - Ensure you're using the correct Python version
   - Try reinstalling dependencies: `pip install -r requirements.txt --force-reinstall`

### Frontend Issues
1. **Installation Issues**:
   - Clear pnpm cache: `pnpm store prune`
   - Delete node_modules and reinstall: `rm -rf node_modules && pnpm install`

2. **Port Conflicts**:
   - If port 3000 is in use, the development server will prompt to use a different port

3. **API Connection Issues**:
   - Ensure the backend server is running
   - Check the API endpoint configuration in the frontend code

## Development

1. **Backend Development**:
   - The main server code is in `backend/main.py`
   - Test files are in `backend/services/langrapghs/tests/`
   - Add new dependencies to `requirements.txt`

2. **Frontend Development**:
   - The main application code is in `transit-chat-frontend/src/`
   - Add new dependencies using: `pnpm add package-name`

## Support

For any issues or questions, please contact the development team. 
