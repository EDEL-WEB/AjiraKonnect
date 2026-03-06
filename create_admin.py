#!/usr/bin/env python
"""
Flask shell script to create admin user
Usage: pipenv run python create_admin.py
"""

from app import create_app, db
from app.services.auth_service import AuthService

app = create_app()

with app.app_context():
    try:
        admin = AuthService.create_admin(
            email='kaziconnect@26.com',
            password='Admin@2024!',
            full_name='KaziConnect Admin',
            phone=''
        )
        print(f" Admin created successfully!")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")
        print(f"ID: {admin.id}")
    except ValueError as e:
        print(f" Error: {e}")
    except Exception as e:
        print(f" Unexpected error: {e}")
