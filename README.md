# Wheatley Census

A Django-based web application for cataloging, managing, and analyzing rare book and provenance data. Built to support libraries, researchers, and digital humanities scholars in tracking the lifecycle and movement of historical works.

## Features

- **Rich Data Models:** Track locations, titles, editions, issues, copies, and provenance with normalized relational models.
- **Admin Interface:** Secure, user-friendly data entry and management via Django Admin.
- **Search & Visualization:** User-facing templates for searching, filtering, and visualizing bibliographic and provenance data.
- **Authentication:** Secure login/logout and admin features.
- **Custom Static & Media Handling:** Supports images, facsimiles, and custom static assets.
- **Extensible:** Modular codebase for easy integration with APIs, analytics, or new features.

## Data Engineering & Information Science Relevance

- **Data Modeling:** Normalized schema for bibliographic and provenance data, supporting efficient querying and analytics.
- **Data Quality:** Built-in validation, verification, and admin workflows for high data integrity.
- **Lifecycle Management:** Covers acquisition, storage, processing, and presentation of data.
- **Automation:** Utility scripts and constants for repeatable, automated data processing.

## Tech Stack

- **Backend:** Django (Python)
- **Database:** Supabase (PostgreSQL, cloud) by default; SQLite supported for local development
- **Frontend:** Django Templates, HTML, CSS, JavaScript
- **Admin:** Django Admin

## Database & Backend

By default, this project is configured to use **Supabase** (PostgreSQL) as the backend database, rather than SQLite.

- **No data is included by default.**
- To use the app, create your own Supabase project and database, and update the Django `settings.py` with your Supabase/PostgreSQL credentials.
- Run Django migrations to create the necessary tables.

If you wish to use SQLite for local development, you can update `settings.py` accordingly.

## Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd wheatleycensus
   ```
2. **Create and activate a virtual environment (recommended, not included in repo):**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Configure your database:**
   - Update `wheatleycensus/settings.py` with your Supabase/PostgreSQL credentials.
   - Or, use SQLite for local testing.
5. **Apply migrations:**
   ```sh
   python manage.py migrate
   ```
6. **Create a superuser (for admin access):**
   ```sh
   python manage.py createsuperuser
   ```
7. **Run the development server:**
   ```sh
   python manage.py runserver
   ```
8. **Access the app:**
   - Main site: [http://localhost:8000/](http://localhost:8000/)
   - Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)

> **Note:** The `venv-sqlite/` folder is for local development only and should not be included in the repository. Each user should create their own virtual environment.

## Project Structure

- `wheatleycensus/` - Main Django app (models, views, templates, static)
- `static/` - Project-level static files (CSS, JS, images)
- `media/` - Uploaded media (title icons, facsimiles)
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script

## Data Model Overview

- **Location:** Libraries/collections with geospatial data
- **Title/Edition/Issue:** Hierarchical bibliographic structure
- **Copy:** Tracks each physical/digital copy, verification, shelfmark, digital facsimile, etc.
- **Provenance:** Ownership history, biographical and temporal metadata
- **StaticPageText:** Editable site content (About, Advisory Board, etc.)

## Advisory Board & Contributors

**Editors**  
Jonathan Senchyne, University of Wisconsin-Madison  
Brigitte Fielder, University of Wisconsin-Madison

**Advisory Board**  
Dorothy Berry, National Museum of African American History & Culture  
Lauren Gottlieb-Miller, University of Houston  
Cassander Smith, University of Alabama  
Jesse Erickson, Morgan Library and Museum  
Tara Bynum, University of Iowa  
Laura Helton, University of Delaware

**Student Project Assistants**  
Akshith Goud Mothkuri (2025)

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a Pull Request

## License

This project is for academic and research use. Please contact the maintainer for other uses.

## Deployment Guide

### Prerequisites

- PythonAnywhere account
- Supabase project
- GitHub repository access

### Setup Steps

1. **Environment Variables**

   - Copy `.env.example` to `.env`
   - Fill in the required values:
     - `SECRET_KEY`: Generate a new Django secret key
     - `DATABASE_URL`: Your Supabase PostgreSQL connection string
     - `SUPABASE_URL` and `SUPABASE_KEY`: From your Supabase project settings
     - `ALLOWED_HOSTS`: Your PythonAnywhere domain
     - Email settings if needed

2. **PythonAnywhere Setup**

   - Clone the repository
   - Create a virtual environment
   - Install requirements: `pip install -r requirements.txt`
   - Configure the web app to use your virtual environment
   - Set up environment variables in PythonAnywhere's web app configuration

3. **Database Migration**

   - Run migrations: `python manage.py migrate`
   - Create superuser: `python manage.py createsuperuser`

4. **Static Files**
   - Collect static files: `python manage.py collectstatic`
   - Configure static files in PythonAnywhere

### Important Notes

- Never commit `.env` or `security.py` to version control
- Keep your Supabase credentials secure
- Update `ALLOWED_HOSTS` when deploying to a new domain
- Make sure DEBUG is set to False in production

### Troubleshooting

- Check PythonAnywhere error logs
- Verify database connection
- Ensure all environment variables are set correctly
- Check static files configuration

---
