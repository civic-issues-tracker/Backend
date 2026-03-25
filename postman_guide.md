# Postman API Testing Guide for Civic Issues Tracker

This guide explains how to use the `postman_test.JSON` file to test API endpoints, what data to insert, and what responses to expect. It is designed to help contributors validate and understand the backend API quickly.

---

## 1. Authentication

### 1.1 Register Resident (Email)
- **Endpoint:** `POST /api/v1/auth/register/resident/`
- **Body Example:**
  ```json
  {
    "email": "test@example.com",
    "phone": "+251911234567",
    "full_name": "Test User",
    "password": "TestPass123",
    "confirm_password": "TestPass123",
    "verification_method": "email"
  }
  ```
- **Expected Response:**
  - `201 Created` with a message about verification email sent.

### 1.2 Register Resident (Telegram)
- **Body Example:**
  ```json
  {
    "phone": "+251911234567",
    "full_name": "Telegram User",
    "password": "TestPass123",
    "confirm_password": "TestPass123",
    "verification_method": "telegram"
  }
  ```
- **Expected Response:**
  - `201 Created` with a message about verification code sent to Telegram.

### 1.3 Verify Email/Telegram
- **Body Example:**
  ```json
  {
    "token": "YOUR_TOKEN_FROM_EMAIL_OR_TELEGRAM",
    "type": "email" // or "telegram"
  }
  ```
- **Expected Response:**
  - `200 OK` with a message confirming verification.

### 1.4 Login (Email/Phone)
- **Body Example (Email):**
  ```json
  { "email": "test@example.com", "password": "TestPass123" }
  ```
- **Body Example (Phone):**
  ```json
  { "phone": "+251911234567", "password": "TestPass123" }
  ```
- **Expected Response:**
  - `200 OK` with `access` and `refresh` tokens.

### 1.5 Get Profile
- **Endpoint:** `GET /api/v1/auth/profile/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Expected Response:**
  - `200 OK` with user profile data.

---

## 2. Organizations

### 2.1 Create Organization
- **Endpoint:** `POST /api/v1/organizations/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Body Example:**
  ```json
  {
    "name": "Addis Ababa Water Utility - Bole District",
    "description": "Handles water supply, leakage, and maintenance in Bole area",
    "contact_email": "bole.water@addis.gov.et",
    "contact_phone": "+251111234567"
  }
  ```
- **Expected Response:**
  - `201 Created` with organization details.

### 2.2 List Organizations
- **Endpoint:** `GET /api/v1/organizations/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Expected Response:**
  - `200 OK` with a list of organizations.

### 2.3 Get Organization Details
- **Endpoint:** `GET /api/v1/organizations/{{org_id}}/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Expected Response:**
  - `200 OK` with organization details.

---

## 3. Categories & Subcategories

### 3.1 Create Category
- **Endpoint:** `POST /api/v1/categories/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Body Example:**
  ```json
  {
    "name": "water",
    "description": "Water-related issues like leakage, shortage, pollution",
    "organization_ids": []
  }
  ```
- **Expected Response:**
  - `201 Created` with category details.

### 3.2 Create Subcategory
- **Endpoint:** `POST /api/v1/subcategories/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Body Example:**
  ```json
  {
    "category": "<category_id>",
    "name": "Leakage",
    "description": "Water pipe leakage or burst pipes"
  }
  ```
- **Expected Response:**
  - `201 Created` with subcategory details.

---

## 4. Organization Admin Management

### 4.1 Create Organization Admin
- **Endpoint:** `POST /api/v1/auth/admin/create-org-admin/`
- **Headers:** `Authorization: Bearer <access_token>`
- **Body Example:**
  ```json
  {
    "email": "alemu@water.gov.et",
    "organization_id": "{{org_id}}"
  }
  ```
- **Expected Response:**
  - `201 Created` with a message about registration email sent.

### 4.2 Complete Registration (Org Admin)
- **Endpoint:** `POST /api/v1/auth/complete-registration/`
- **Body Example:**
  ```json
  {
    "token": "YOUR_TOKEN_FROM_EMAIL",
    "full_name": "Alemu Tadesse",
    "password": "SecurePass123",
    "confirm_password": "SecurePass123"
  }
  ```
- **Expected Response:**
  - `200 OK` with a message confirming registration.

---

## 5. General Tips
- Always check the request body and headers for required fields.
- Use the tokens returned from login for authenticated requests.
- Refer to the `Tests` and `Pre-request Script` tabs in Postman for automation and validation logic.
- For each endpoint, check the response code and returned data to verify correct behavior.

For more details, see the request examples in the Postman collection and the backend API documentation.
