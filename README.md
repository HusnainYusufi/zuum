# Voice Freight Broker Project

This project consists of a backend service for broker message processing and a frontend chat interface.

## Prerequisites

1. Python 3.8 or higher
2. Node.js 16 or higher
3. pnpm (for frontend)
4. OpenAI API key

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
