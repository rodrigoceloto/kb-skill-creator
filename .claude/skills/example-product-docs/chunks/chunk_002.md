# API Reference

**Path:** API Reference
**Source:** sample-doc-2.md
**Tokens:** ~585
**Section Level:** 1

---


Complete API documentation for developers.



All API requests require authentication using an API key.



To get your API key:
1. Log in to your account
2. Navigate to Settings > API Keys
3. Click "Generate New Key"
4. Save the key securely



Include the API key in the request header:

```
Authorization: Bearer YOUR_API_KEY
```





Manage user accounts and profiles.



Retrieve a list of users.

**Parameters:**
- `limit` (optional): Maximum number of results (default: 10, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "users": [
    {"id": 1, "name": "John Doe", "email": "john@example.com"},
    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
  ],
  "total": 2
}
```



Create a new user.

**Request Body:**
```json
{
  "name": "New User",
  "email": "newuser@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "id": 3,
  "name": "New User",
  "email": "newuser@example.com",
  "created_at": "2024-01-15T10:30:00Z"
}
```



Manage projects and their settings.



Retrieve all projects for the authenticated user.

**Response:**
```json
{
  "projects": [
    {"id": 1, "name": "Project A", "status": "active"},
    {"id": 2, "name": "Project B", "status": "archived"}
  ]
}
```



Create a new project.

**Request Body:**
```json
{
  "name": "My New Project",
  "description": "Project description",
  "settings": {
    "public": false,
    "notifications": true
  }
}
```



API requests are rate-limited to prevent abuse.



- **Free tier**: 100 requests per hour
- **Pro tier**: 1,000 requests per hour
- **Enterprise**: Custom limits



Each response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642251600
```



The API uses standard HTTP status codes.



- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Missing or invalid API key
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error



```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "email",
      "issue": "Email format is invalid"
    }
  }
}
```

