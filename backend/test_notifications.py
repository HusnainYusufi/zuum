"""
Test script for WebSocket notifications
Run this after starting the server to test real-time notifications
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime

# Server URL - adjust if needed
SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/notifications"

async def test_websocket_notifications():
    """Test WebSocket connection and notifications"""
    print("Connecting to WebSocket...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send a ping to keep connection alive
            await websocket.send("ping")
            response = await websocket.recv()
            print(f"Received echo: {response}")
            
            # Test different notification types
            print("\n📢 Testing notifications...")
            
            # Test 1: General notification
            print("\n1. Testing general notification...")
            requests.post(f"{SERVER_URL}/api/notifications/test", 
                         params={
                             "message": "Test notification from script",
                             "severity": "info"
                         })
            
            # Wait for notification
            notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {notification}")
            
            # Test 2: Stop update notification
            print("\n2. Testing stop update notification...")
            stop_data = {
                "id": 1,
                "name": "Test Stop",
                "location": "Test Location",
                "eta": datetime.now().isoformat(),
                "is_delayed": True,
                "delay_reason": "Test delay",
                "expected_location": "Expected Location",
                "reported_location": "Reported Location",
                "nearest_highway": "I-95",
                "is_origin": False,
                "is_destination": False
            }
            
            response = requests.post(f"{SERVER_URL}/api/notifications/stop-update", 
                                   json=stop_data)
            print(f"API Response: {response.json()}")
            
            # Wait for notification
            notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {notification}")
            
            # Test 3: Check-in update notification
            print("\n3. Testing check-in update notification...")
            check_in_data = {
                "id": 1,
                "stop_id": 1,
                "load_id": "LOAD123",
                "query": "Test query",
                "AI_Response_Summary": "Test summary",
                "AI_Timestamp": datetime.now().isoformat(),
                "Issue_Flagged": True,
                "Exception_Type": "Delay",
                "Call_confidence_score": "0.95",
                "Requires_Human_Review": False,
                "Tags": "test,notification",
                "stop_name": "Test Stop",
                "stop_location": "Test Location",
                "stop_eta": datetime.now().isoformat()
            }
            
            response = requests.post(f"{SERVER_URL}/api/notifications/check-in-update", 
                                   json=check_in_data)
            print(f"API Response: {response.json()}")
            
            # Wait for notification
            notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {notification}")
            
            # Test 4: Journey state update
            print("\n4. Testing journey state update notification...")
            response = requests.post(f"{SERVER_URL}/api/notifications/journey-state-update", 
                                   params={"state": 2})
            print(f"API Response: {response.json()}")
            
            # Wait for notification
            notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {notification}")
            
            print("\n✅ All tests completed successfully!")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Could not connect to WebSocket. Make sure the server is running.")
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for notification. Check if notifications are being sent.")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_multiple_connections():
    """Test multiple WebSocket connections"""
    print("\n📢 Testing multiple connections...")
    
    connections = []
    try:
        # Create 3 connections
        for i in range(3):
            ws = await websockets.connect(WS_URL)
            connections.append(ws)
            print(f"✅ Connection {i+1} established")
        
        # Check active connections
        response = requests.get(f"{SERVER_URL}/api/notifications/connections")
        print(f"\nActive connections: {response.json()}")
        
        # Send a broadcast notification
        print("\nSending broadcast notification...")
        requests.post(f"{SERVER_URL}/api/notifications/test", 
                     params={
                         "message": "Broadcast to all connections",
                         "severity": "info"
                     })
        
        # All connections should receive the notification
        for i, ws in enumerate(connections):
            notification = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"Connection {i+1} received: {notification}")
        
        print("\n✅ Multiple connection test completed!")
        
    finally:
        # Close all connections
        for ws in connections:
            await ws.close()

if __name__ == "__main__":
    print("🚀 WebSocket Notification Test Script")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_websocket_notifications())
    asyncio.run(test_multiple_connections())
    
    print("\n✅ All tests completed!") 