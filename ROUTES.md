# API Routes Documentation

This document outlines all available API endpoints for the Code-Till-Failure backend.

## Base URL
```
/api
```

---

## Authentication Routes
**Base Path:** `/api/auth`

### 1. Check User Exists
- **Endpoint:** `POST /api/auth/exists`
- **Description:** Check if a user exists. If not, create a new user.
- **Request Body:**
  ```json
  {
    "user_id": "string",
    "password": "string",
    "display_name": "string (optional, defaults to 'user')"
  }
  ```
- **Response:**
  ```json
  {
    "exists": boolean
  }
  ```

### 2. Check User Verification
- **Endpoint:** `POST /api/auth/verified`
- **Description:** Check if a user is verified by domain and email.
- **Request Body:**
  ```json
  {
    "domain": "string",
    "email": "string"
  }
  ```
- **Response:**
  ```json
  {
    "verified": boolean
  }
  ```

### 3. Get User Status
- **Endpoint:** `POST /api/auth/status`
- **Description:** Get the current status of a user (recommended endpoint).
- **Request Body:**
  ```json
  {
    "domain": "string",
    "email": "string"
  }
  ```
- **Response:** User status object

---

## Roads Routes
**Base Path:** `/api/roads`

### 1. Create Road Report
- **Endpoint:** `POST /api/roads/reports`
- **Description:** Create a new road report.
- **Request Body:** Report data (varies by report type)
- **Response:** Created report object with status code

### 2. Confirm Road Report
- **Endpoint:** `POST /api/roads/reports/{report_id}/confirm`
- **Description:** Confirm an existing road report.
- **Path Parameters:**
  - `report_id` (string): The ID of the report to confirm
- **Request Body:** Confirmation data
- **Response:** Updated report object with status code

### 3. List All Road Reports
- **Endpoint:** `GET /api/roads/reports`
- **Description:** Retrieve a list of road reports with optional filtering.
- **Query Parameters:**
  - `report_type` (string, optional): Filter by report type
  - `verified_only` (boolean, optional): Show only verified reports (default: false)
  - `lat` (float, optional): Latitude for location-based filtering
  - `lng` (float, optional): Longitude for location-based filtering
  - `radius_km` (float, optional): Search radius in kilometers (default: DEFAULT_RADIUS_KM)
- **Response:** List of road report objects

### 4. Get Road Report by ID
- **Endpoint:** `GET /api/roads/reports/{report_id}`
- **Description:** Retrieve a specific road report by its ID.
- **Path Parameters:**
  - `report_id` (string): The ID of the report
- **Response:** Report object

### 5. Update Road Report
- **Endpoint:** `PUT /api/roads/reports/{report_id}`
- **Description:** Update an existing road report.
- **Path Parameters:**
  - `report_id` (string): The ID of the report to update
- **Request Body:** Updated report data
- **Response:** Updated report object with status code

### 6. Delete Road Report
- **Endpoint:** `DELETE /api/roads/reports/{report_id}`
- **Description:** Delete a road report by ID.
- **Path Parameters:**
  - `report_id` (string): The ID of the report to delete
- **Response:** Status message with status code

### 7. List Checkpoints
- **Endpoint:** `GET /api/roads/checkpoints`
- **Description:** Retrieve a list of all checkpoints.
- **Response:** List of checkpoint objects

### 8. List Gas Stations
- **Endpoint:** `GET /api/roads/gas-stations`
- **Description:** Retrieve a list of all gas stations.
- **Response:** List of gas station objects

---

## Shops Routes
**Base Path:** `/api/shops`

### 1. Create Shop
- **Endpoint:** `POST /api/shops`
- **Description:** Create a new shop.
- **Request Body:** Shop details
- **Response:** Created shop object with status code

### 2. List All Shops
- **Endpoint:** `GET /api/shops`
- **Description:** Retrieve a list of shops with optional filtering.
- **Query Parameters:**
  - `category` (string, optional): Filter by shop category
  - `is_open` (boolean, optional): Filter by open/closed status
  - `search` (string, optional): Search by shop name or details
  - `lat` (float, optional): Latitude for location-based filtering
  - `lng` (float, optional): Longitude for location-based filtering
  - `radius_km` (float, optional): Search radius in kilometers (default: DEFAULT_RADIUS_KM)
- **Response:** List of shop objects

### 3. List Pharmacies
- **Endpoint:** `GET /api/shops/pharmacies`
- **Description:** Retrieve a list of all pharmacies.
- **Query Parameters:**
  - `is_open` (boolean, optional): Filter by open/closed status
  - `lat` (float, optional): Latitude for location-based filtering
  - `lng` (float, optional): Longitude for location-based filtering
  - `radius_km` (float, optional): Search radius in kilometers (default: DEFAULT_RADIUS_KM)
- **Response:** List of pharmacy objects

### 4. Get Shop by ID
- **Endpoint:** `GET /api/shops/{shop_id}`
- **Description:** Retrieve a specific shop by its ID.
- **Path Parameters:**
  - `shop_id` (string): The ID of the shop
- **Response:** Shop object

### 5. Update Shop
- **Endpoint:** `PUT /api/shops/{shop_id}`
- **Description:** Update an existing shop.
- **Path Parameters:**
  - `shop_id` (string): The ID of the shop to update
- **Request Body:** Updated shop data
- **Response:** Updated shop object with status code

### 6. Delete Shop
- **Endpoint:** `DELETE /api/shops/{shop_id}`
- **Description:** Delete a shop by ID.
- **Path Parameters:**
  - `shop_id` (string): The ID of the shop to delete
- **Response:** Status message with status code

### 7. Report Shop Status
- **Endpoint:** `POST /api/shops/{shop_id}/status-updates`
- **Description:** Report a status update for a shop.
- **Path Parameters:**
  - `shop_id` (string): The ID of the shop
- **Request Body:** Status update information
- **Response:** Status response with status code

### 8. Get Shop Status History
- **Endpoint:** `GET /api/shops/{shop_id}/status-history`
- **Description:** Retrieve the status history of a shop.
- **Path Parameters:**
  - `shop_id` (string): The ID of the shop
- **Query Parameters:**
  - `limit` (integer, optional): Maximum number of history records to return (default: 20)
- **Response:** List of status history objects

---

## Summary

| Route Group | Total Routes |
|------------|--------------|
| Authentication | 3 |
| Roads | 8 |
| Shops | 8 |
| **Total** | **19** |

---

## Notes

- All endpoints use JSON for request/response bodies
- Location-based filtering (lat, lng, radius_km) is available for roads and shops endpoints
- The `DEFAULT_RADIUS_KM` constant is used when no radius is specified in location-based queries
