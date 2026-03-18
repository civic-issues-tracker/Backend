# Civic Issues Tracker Backend API

A Django REST Framework backend for reporting and tracking civic issues.

## Features
- User authentication with JWT
- Issue reporting with images and location
- AI-powered categorization
- Department assignment
- Real-time notifications
- Analytics dashboard
- Activity logging

## Setup
1. Create virtual environment: `python -m venv venv`
2. Activate: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure
5. Run migrations: `python manage.py migrate`
6. Create superuser: `python manage.py createsuperuser`
7. Run server: `python manage.py runserver`

## API Documentation
- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/