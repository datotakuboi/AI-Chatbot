import firebase_admin
from firebase_admin import credentials, auth
import json
import os

# Load Firebase credentials from a JSON file
FIREBASE_CREDENTIALS_PATH = "ai_chatbotfirebase_credentials.json"

# Check if Firebase is already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

# Function to create a new user
def register_user(email, password):
    try:
        user = auth.create_user(email=email, password=password)
        return f"User {email} created successfully!"
    except Exception as e:
        return str(e)

# Function to sign in a user
def login_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        return user
    except Exception as e:
        return None
