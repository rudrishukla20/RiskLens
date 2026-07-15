# RiskLens API Contract Specification

This document details the request payload schemas and standardized JSON response envelopes for the RiskLens API endpoints.

---

## 1. Response Envelopes

All routes return a uniform response envelope.

### Success Response Envelope
```json
{
  "success": true,
  "message": "User login completed successfully.",
  "data": {
    "access_token": "eyJhbG...",
    "refresh_token": "d98341..."
  },
  "error": null,
  "meta": {
    "timestamp": "2026-07-12T00:54:17Z",
    "request_id": "8c5b3c8f-287c-473c-9a4f-7f61c6b24bc1"
  }
}
```

### Error Response Envelope
```json
{
  "success": false,
  "message": "Invalid password or email.",
  "data": null,
  "error": {
    "code": "AUTH_UNAUTHORIZED",
    "details": "Invalid password or email."
  },
  "meta": {
    "timestamp": "2026-07-12T00:54:17Z",
    "request_id": "8c5b3c8f-287c-473c-9a4f-7f61c6b24bc1"
  }
}
```

---

## 2. Authentication Endpoints

### Login Account
- **Method**: `POST`
- **Path**: `/api/v1/auth/login`
- **Request Body**:
  ```json
  {
    "email": "admin@risklens.com",
    "password": "ChangeMeStrongPassword123!"
  }
  ```
- **Returns**: `ResponseEnvelope[TokenResponse]`

### Refresh Tokens
- **Method**: `POST`
- **Path**: `/api/v1/auth/refresh`
- **Request Body**:
  ```json
  {
    "refresh_token": "d98341..."
  }
  ```
- **Returns**: `ResponseEnvelope[TokenResponse]`

### Logout Account
- **Method**: `POST`
- **Path**: `/api/v1/auth/logout`
- **Request Body**:
  ```json
  {
    "refresh_token": "d98341..."
  }
  ```
- **Returns**: `ResponseEnvelope[None]`

### Retrieve Profile Details
- **Method**: `GET`
- **Path**: `/api/v1/auth/me`
- **Headers**: `Authorization: Bearer <access_token>`
- **Returns**: `ResponseEnvelope[UserProfileResponse]`

---

## 3. Dataset Endpoints

### Upload Dataset
- **Method**: `POST`
- **Path**: `/api/v1/datasets/upload`
- **Form Data**:
  - `name`: string
  - `description`: string (optional)
  - `file`: binary file (CSV, XLSX, or JSON)
- **Returns**: `ResponseEnvelope[DatasetUploadResponse]`

### Confirm Schema Mapping
- **Method**: `POST`
- **Path**: `/api/v1/datasets/{dataset_id}/mapping`
- **Request Body**:
  ```json
  {
    "mappings": [
      {
        "original_column_name": "customer_id",
        "canonical_field": "borrower_id"
      },
      {
        "original_column_name": "annual_income",
        "canonical_field": "income"
      }
    ]
  }
  ```
- **Returns**: `ResponseEnvelope[List[SchemaMappingResponse]]`

---

## 4. Analytics & Reports Endpoints

### Retrieve Dashboard Overview
- **Method**: `GET`
- **Path**: `/api/v1/analytics/dashboard`
- **Returns**: `ResponseEnvelope[RiskDashboardResponse]`

### Generate Exportable Report
- **Method**: `POST`
- **Path**: `/api/v1/reports/generate`
- **Request Body**:
  ```json
  {
    "dataset_id": "c8e76c1e-8ad2-4752-a5e2-2ab2d67ea26d",
    "report_type": "PORTFOLIO_PERFORMANCE",
    "export_format": "PDF"
  }
  ```
- **Returns**: `ResponseEnvelope[ReportResponse]`
