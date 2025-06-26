# Supabase Migration Guide

This document outlines the migration from SQLite + SQLAlchemy to Supabase for the Voice Freight Broker application.

## Migration Overview

### What Changed

1. **Database**: SQLite → Supabase (PostgreSQL)
2. **ORM**: SQLAlchemy → Supabase Client
3. **Schema**: Simplified tables with JSON fields
4. **Images**: Local storage → AWS S3
5. **Real-time**: Added notification system with real-time subscriptions

### New Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Supabase      │
│   Templates     │────│   FastAPI       │────│   PostgreSQL    │
│   + JavaScript  │    │   Routes        │    │   + RPC Funcs   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   AWS S3        │
                       │   Feedback      │
                       │   Images        │
                       └─────────────────┘
```

## New Database Schema

### Core Tables

#### 1. check_ins
```sql
CREATE TABLE check_ins (
    id BIGSERIAL PRIMARY KEY,
    load_id TEXT,
    ai_response_summary TEXT,
    ai_timestamp TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB DEFAULT '[]'::jsonb,
    issue_flagged BOOLEAN DEFAULT false,
    exception_type TEXT,
    confidence_score DECIMAL(5,4),
    forms JSONB DEFAULT '{}'::jsonb,
    call_status TEXT DEFAULT 'in_progress',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2. retell_calls
```sql
CREATE TABLE retell_calls (
    call_id TEXT PRIMARY KEY,
    check_in_id BIGINT REFERENCES check_ins(id) ON DELETE CASCADE,
    call_transcript TEXT,
    recording_url TEXT,
    output_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3. notifications
```sql
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    read BOOLEAN DEFAULT false,
    check_in_id BIGINT REFERENCES check_ins(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4. feedback
```sql
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    feedback_type TEXT NOT NULL,
    user_name TEXT NOT NULL,
    user_email TEXT NOT NULL,
    description TEXT NOT NULL,
    s3_image_urls JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### RPC Functions

#### Dashboard Statistics
```sql
SELECT * FROM get_dashboard_stats();
```

#### Paginated Check-ins
```sql
SELECT * FROM get_check_ins_paginated(1, 10, true, 'urgent', 'completed');
```

#### Recent Check-ins with Calls
```sql
SELECT * FROM get_recent_checkins_with_calls(10);
```

## Environment Variables

Add these to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# AWS S3 Configuration (for feedback images)
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=voice-freight-broker-feedback
```

## Migration Steps

### Step 1: Install Dependencies

```bash
pip install supabase boto3
```

### Step 2: Set Up Supabase Project

1. Create a new Supabase project
2. Copy the project URL and anon key
3. Add them to your environment variables

### Step 3: Apply Database Migrations

The migrations have been applied to create:
- Tables with proper structure
- RPC functions for complex queries
- Indexes for performance
- Row Level Security policies

### Step 4: Update Code

#### Before (SQLAlchemy):
```python
from db_models import get_db, CheckIn
from sqlalchemy.orm import Session

def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
    checkin = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    return checkin
```

#### After (Supabase):
```python
from services.supabase import supabase_service

async def get_checkin(checkin_id: int):
    result = await supabase_service.get_check_in(checkin_id)
    return result["data"] if result["success"] else None
```

### Step 5: Update Frontend

#### Include Supabase Client:
```html
<script src="https://unpkg.com/@supabase/supabase-js@2"></script>
<script src="/static/js/supabase-client.js"></script>
```

#### Initialize Client:
```javascript
const supabaseClient = new SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY);
await supabaseClient.init();

// Get dashboard stats
const stats = await supabaseClient.getDashboardStats();
```

## Updated Routes

### Key Changes in Routes

1. **Removed SQLAlchemy Dependencies**: No more `Session = Depends(get_db)`
2. **Async Functions**: All database operations are now async
3. **Supabase Service**: All DB operations go through `supabase_service`
4. **Error Handling**: Consistent error response format

### Example Route Update:

```python
# OLD
@router.get("/statistics")
def get_checkin_statistics(db: Session = Depends(get_db)):
    total_checkins = db.query(CheckIn).count()
    return {"total_checkins": total_checkins}

# NEW
@router.get("/statistics")
async def get_checkin_statistics():
    stats = await supabase_service.get_dashboard_stats()
    if not stats["success"]:
        raise HTTPException(status_code=500, detail=stats["error"])
    return stats
```

## Data Mapping

### Field Name Changes

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `AI_Response_Summary` | `ai_response_summary` | Snake case |
| `AI_Timestamp` | `ai_timestamp` | Snake case |
| `Issue_Flagged` | `issue_flagged` | Snake case |
| `Exception_Type` | `exception_type` | Snake case |
| `Call_confidence_score` | `confidence_score` | Simplified name |
| `call_trasfered` | `call_status` | More descriptive |
| `Tags` (string) | `tags` (JSONB) | Proper JSON array |
| `forms` (string) | `forms` (JSONB) | Proper JSON object |

### Backward Compatibility

The `_format_check_in_for_compatibility()` function in the Supabase service converts new field names back to old format for existing code.

## Frontend Integration

### Dashboard Updates

Use RPC functions for efficient queries:

```javascript
// Load dashboard stats
async function loadDashboard() {
    const stats = await supabaseClient.getDashboardStats();
    document.getElementById('total-checkins').textContent = stats.data.total_checkins;
}

// Load recent check-ins
async function loadRecentCheckins() {
    const result = await supabaseClient.getRecentCheckinsWithCalls(5);
    updateCheckinsTable(result.data);
}
```

### Real-time Updates

```javascript
// Subscribe to check-in changes
const checkinsSubscription = supabaseClient.subscribeToCheckIns((payload) => {
    console.log('Check-in updated:', payload);
    refreshDashboard();
});

// Subscribe to new notifications
const notificationsSubscription = supabaseClient.subscribeToNotifications((payload) => {
    if (payload.eventType === 'INSERT') {
        showNotification(payload.new);
    }
});
```

## S3 Integration for Feedback Images

### Backend (Python):
```python
from services.supabase import supabase_service

# Create feedback with images
image_files = [
    {
        'filename': 'screenshot.png',
        'content': image_data,
        'content_type': 'image/png'
    }
]

result = await supabase_service.create_feedback(feedback_data, image_files)
```

### Frontend (JavaScript):
```javascript
// Upload feedback with images
const formData = new FormData();
formData.append('feedback_type', 'bug');
formData.append('description', 'Issue description');
formData.append('images', fileInput.files[0]);

fetch('/api/feedback', {
    method: 'POST',
    body: formData
});
```

## Performance Benefits

1. **RPC Functions**: Complex queries are pre-compiled in the database
2. **JSON Fields**: Flexible data storage without schema changes
3. **Indexing**: Proper indexes on frequently queried fields
4. **Connection Pooling**: Supabase handles connection management
5. **Real-time**: Built-in real-time subscriptions

## Migration Checklist

- [ ] Install new dependencies (`supabase`, `boto3`)
- [ ] Set up Supabase project and get credentials
- [ ] Configure AWS S3 bucket for images
- [ ] Update environment variables
- [ ] Apply database migrations (already done via MCP)
- [ ] Update route imports and function signatures
- [ ] Test all CRUD operations
- [ ] Update frontend templates with Supabase client
- [ ] Test real-time functionality
- [ ] Migrate existing data (if needed)
- [ ] Update deployment configuration

## Troubleshooting

### Common Issues

1. **Environment Variables**: Ensure all Supabase and AWS variables are set
2. **Async/Await**: All database operations are now async
3. **Field Names**: Use new snake_case field names or compatibility layer
4. **Error Handling**: Check for `result["success"]` before accessing `result["data"]`

### Debugging

```python
# Check Supabase connection
health = await supabase_service.health_check()
print(f"Supabase connection: {'OK' if health else 'Failed'}")

# Log all operations
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Row Level Security**: Implement user-based access controls
2. **Edge Functions**: Move some logic to Supabase Edge Functions
3. **Advanced Analytics**: Use PostGIS for location-based queries
4. **Caching**: Implement Redis caching for frequently accessed data
5. **Backup Strategy**: Set up automated backups and point-in-time recovery

## Support

For issues with this migration:
1. Check the logs for detailed error messages
2. Verify environment variables are correctly set
3. Test Supabase connection using the health check endpoint
4. Review the migration guide for common patterns 