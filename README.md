
# Civic Issues Tracker Backend

## Overview
The Civic Issues Tracker is a robust backend system built with Django and Django REST Framework for reporting, managing, and analyzing civic issues in a city or municipality. It supports user authentication, issue categorization, organization management, notifications, analytics, and more.

## Key Features
- Secure JWT-based authentication (email, phone, Telegram)
- Issue reporting with image uploads and geolocation
- AI-powered issue categorization
- Organization and department management
- Real-time notifications (email, Telegram)
- Analytics dashboard for insights
- Activity logging and audit trails

## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL (or SQLite for development)
- [pip](https://pip.pypa.io/en/stable/)

### Installation
1. **Clone the repository:**
	```bash
	git clone <repo-url>
	cd civic-issues-tracker
	```
2. **Create and activate a virtual environment:**
	```bash
	python -m venv .venv
	# On Windows:
	.venv\Scripts\activate
	# On Unix/Mac:
	source .venv/bin/activate
	```
3. **Install dependencies:**
	```bash
	pip install -r requirements.txt
	```
4. **Configure environment variables:**
	- Copy `.env.example` to `.env` and fill in all required values (see comments in the file).
5. **Apply database migrations:**
	```bash
	python manage.py migrate
	```
6. **Create a superuser (admin):**
	```bash
	python manage.py createsuperuser
	```
7. **Run the development server:**
	```bash
	python manage.py runserver
	```

## API Documentation & Testing

- The API follows RESTful conventions and is documented via the included Postman collection: `postman_test.JSON`.
- See `postman_guide.md` for a step-by-step guide to testing all endpoints using Postman.
- Most endpoints require authentication via JWT tokens.

## Project Structure

- `apps/` — Django apps (accounts, issues, organizations, analytics, etc.)
- `config/` — Django project settings and URLs
- `media/` — Uploaded files (e.g., issue images)
- `static/` — Static files
- `templates/` — Email and notification templates
- `scripts/` — Utility scripts

## Environment Variables

All sensitive settings are managed via the `.env` file. See `.env.example` for required variables (database, email, Telegram, superuser, etc.).

## Running Tests

To run the test suite:
```bash
python manage.py test
```

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository and create a new branch.
2. Make your changes with clear commit messages.
3. Ensure all tests pass and code is linted.
4. Submit a pull request with a detailed description.



