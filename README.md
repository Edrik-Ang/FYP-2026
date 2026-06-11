# CM3070-FYP-Identity API
Final year project assigned by SIM GE - UOL.
---
## Tech stack
| This project is built with:
PostgreSQL
Django
TailWind
---
# Getting started
---
## Installations
Ensure you have the prerequisites installed, then ru:
Steps to run this project:
1. Clone repository
git clone https://github.com/Edrik-Ang/FYP-2026.git

2. Create virtual environment
python -m venv virtEnv

3. Activate virtual environment
virtEnv\Scripts\activate
4. Install requirements
pip install -r requirements.txt
** Ensure PostgreSQL bin directory is added to PATH. E.g C:\Program Files\PostgreSQL\18\bin
5. Create postgreSQL database

6. Create .env file

7. Run migrations
python manage.py migrate
8. Start server
python manage.py runserver
