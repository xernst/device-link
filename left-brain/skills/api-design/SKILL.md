---
name: api-design
description: REST API design patterns — resource naming, status codes, pagination, filtering, error responses.
---

# API Design Patterns

## URL Structure
```
GET    /api/v1/users          # List
GET    /api/v1/users/:id      # Get one
POST   /api/v1/users          # Create
PUT    /api/v1/users/:id      # Full update
PATCH  /api/v1/users/:id      # Partial update
DELETE /api/v1/users/:id      # Delete
```

Resources are nouns, plural, lowercase, kebab-case.

## Status Codes

```
200 OK, 201 Created, 204 No Content
400 Bad Request, 401 Unauthorized, 403 Forbidden
404 Not Found, 409 Conflict, 422 Unprocessable, 429 Rate Limited
500 Internal Error
```

## Error Response Format
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [{"field": "email", "message": "Must be valid email"}]
  }
}
```

## Pagination

- **Offset** for small datasets: `?page=2&per_page=20`
- **Cursor** for large datasets: `?cursor=eyJpZCI6MTIzfQ&limit=20`

## Checklist

- [ ] URL follows naming conventions
- [ ] Correct HTTP method
- [ ] Appropriate status codes
- [ ] Input validated with schema
- [ ] Error responses follow format
- [ ] Pagination on list endpoints
- [ ] Auth required or marked public
- [ ] Rate limiting configured
