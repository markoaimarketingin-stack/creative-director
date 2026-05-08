# Supabase Data Persistence Guide

## Overview
All user data is now automatically stored in Supabase:
- ✅ Chat history
- ✅ Knowledge base (uploaded files/documents)
- ✅ Execution history (campaign generation logs)

Users can access all their previous data from any session!

---

## Database Schema

### `chat_sessions`
Stores conversation sessions.
```sql
id VARCHAR(255) PRIMARY KEY
title TEXT
created_at TIMESTAMP
```

### `chat_messages`
Stores all chat messages within sessions.
```sql
id UUID PRIMARY KEY
session_id VARCHAR(255) - references chat_sessions
role VARCHAR(50) - "user" or "assistant"
content TEXT
created_at TIMESTAMP
```

### `knowledge_base`
Stores uploaded files, documents, and knowledge base items.
```sql
id UUID PRIMARY KEY
session_id VARCHAR(255) - references chat_sessions
file_name TEXT
file_type VARCHAR(50) - "pdf", "txt", "json", etc.
file_path TEXT
file_content TEXT - optional: full content
metadata JSONB - custom metadata
created_at TIMESTAMP
```

### `execution_history`
Stores all campaign generation and AI execution logs.
```sql
id UUID PRIMARY KEY
session_id VARCHAR(255) - references chat_sessions
campaign_name TEXT
execution_type VARCHAR(100) - "hook_generation", "angle_generation", "image_generation", etc.
input_data JSONB
output_data JSONB
status VARCHAR(50) - "success", "failed", "pending"
error_message TEXT - if failed
execution_time_ms INTEGER
created_at TIMESTAMP
```

---

## API Endpoints

### Get All Session Data
```http
GET /session-data/{session_id}
```
Returns:
```json
{
  "session_id": "abc123",
  "chat_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "knowledge_base": [
    {
      "id": "kb-uuid",
      "file_name": "document.pdf",
      "file_type": "pdf",
      "file_path": "/path/to/file",
      "metadata": {},
      "created_at": "2026-05-08T..."
    }
  ],
  "execution_history": [
    {
      "id": "exec-uuid",
      "campaign_name": "Q2 Campaign",
      "execution_type": "hook_generation",
      "input_data": {...},
      "output_data": {...},
      "status": "success",
      "execution_time_ms": 2500,
      "created_at": "2026-05-08T..."
    }
  ]
}
```

### Save Knowledge Base Item
```http
POST /knowledge-base/{session_id}
Content-Type: application/json

{
  "file_name": "brand_guidelines.pdf",
  "file_type": "pdf",
  "file_path": "/output/knowledge_base/brand_guidelines.pdf",
  "file_content": "optional full text content",
  "metadata": {
    "pages": 15,
    "uploaded_by": "user@example.com"
  }
}
```

### Get Knowledge Base
```http
GET /knowledge-base/{session_id}
```

### Save Execution History
```http
POST /execution-history/{session_id}
Content-Type: application/json

{
  "campaign_name": "Q2 2026 Campaign",
  "execution_type": "hook_generation",
  "input_data": {
    "brand": "MyBrand",
    "objective": "awareness"
  },
  "output_data": {
    "hooks": [...]
  },
  "status": "success",
  "error_message": null
}
```

### Get Execution History
```http
GET /execution-history/{session_id}
```

---

## User Session Flow

### First Visit
```
1. Generate UUID for session_id
2. Create chat_sessions record
3. User uploads knowledge base → saves to knowledge_base table
4. User requests campaign → executes → saves to execution_history table
5. Chat messages → save to chat_messages table
```

### Return Visit (Same Session)
```
1. Use same session_id
2. Load chat history from chat_messages
3. Load knowledge base from knowledge_base
4. Load previous campaigns from execution_history
5. Continue from where they left off
```

### Different Device/Browser
```
1. If session_id is provided → load all previous data
2. If no session_id → create new session (new history)
```

---

## Frontend Implementation

### Load All User Data on Session Load
```javascript
async function loadSessionData(sessionId) {
  const response = await fetch(`/session-data/${sessionId}`);
  const data = await response.json();
  
  // Display chat history
  displayChatHistory(data.chat_history);
  
  // Display knowledge base
  displayKnowledgeBase(data.knowledge_base);
  
  // Display previous executions
  displayExecutionHistory(data.execution_history);
}
```

### Save Knowledge Base
```javascript
async function uploadKnowledgeBase(sessionId, file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`/knowledge-base/${sessionId}`, {
    method: 'POST',
    body: {
      file_name: file.name,
      file_type: file.type,
      file_path: `/output/knowledge_base/${file.name}`,
      metadata: { size: file.size }
    }
  });
}
```

### Log Campaign Generation
```javascript
async function logExecution(sessionId, campaignData) {
  const response = await fetch(`/execution-history/${sessionId}`, {
    method: 'POST',
    body: JSON.stringify({
      campaign_name: campaignData.name,
      execution_type: 'campaign_generation',
      input_data: campaignData.input,
      output_data: campaignData.output,
      status: 'success'
    })
  });
}
```

---

## Benefits

✅ **Persistent Data**: All data survives browser refresh, device change, or logout
✅ **Multi-Device**: Access campaigns from phone, tablet, desktop
✅ **Audit Trail**: Complete history of what was generated and when
✅ **Collaboration**: Managers can review execution history
✅ **Analytics**: Track campaign generation metrics
✅ **Recovery**: Undo/redo using execution history
✅ **Knowledge Building**: Reuse previous knowledge base items

---

## Querying Examples

### Get all campaigns by a user
```sql
SELECT DISTINCT campaign_name, COUNT(*) as attempts, 
       MAX(created_at) as last_attempt
FROM execution_history
WHERE session_id = 'user-session-123'
GROUP BY campaign_name
ORDER BY last_attempt DESC;
```

### Get execution performance
```sql
SELECT execution_type, AVG(execution_time_ms) as avg_time, 
       COUNT(*) as count, 
       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes
FROM execution_history
WHERE session_id = 'user-session-123'
GROUP BY execution_type;
```

### Get most used knowledge base items
```sql
SELECT file_name, COUNT(*) as used_in_executions
FROM knowledge_base kb
JOIN execution_history eh ON kb.session_id = eh.session_id
WHERE kb.session_id = 'user-session-123'
GROUP BY file_name
ORDER BY used_in_executions DESC;
```

---

## Testing

Test the persistence with:
```bash
# 1. Get initial session
curl -X GET "http://localhost:8000/session-data/test-session-123"

# 2. Save knowledge base
curl -X POST "http://localhost:8000/knowledge-base/test-session-123" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"test.txt","file_type":"txt","file_path":"/test"}'

# 3. Save execution
curl -X POST "http://localhost:8000/execution-history/test-session-123" \
  -H "Content-Type: application/json" \
  -d '{"campaign_name":"Test","execution_type":"test","input_data":{},"output_data":{},"status":"success"}'

# 4. Verify all data persisted
curl -X GET "http://localhost:8000/session-data/test-session-123"
```
