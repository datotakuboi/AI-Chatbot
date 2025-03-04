import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import google.generativeai as genai
import time
from streamlit_option_menu import option_menu
import json

# Set page config
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")

# ✅ Read API Key from Streamlit secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Missing Gemini API Key in Streamlit secrets!")
    st.stop()

API_KEY = st.secrets["GEMINI_API_KEY"]

# ✅ Initialize Gemini AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-pro")

# ✅ Initialize Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            firebase_credentials = dict(st.secrets["service_account"])
            cred = credentials.Certificate(firebase_credentials)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"🔥 Failed to initialize Firebase: {e}")

initialize_firebase()

# Sidebar navigation menu (only if the user is NOT logged in)
if "user" not in st.session_state:
    with st.sidebar:
        selected = option_menu(
            menu_title="Navigation",
            options=["Login", "Create Account", "Forgot Password?"],
            icons=["box-arrow-in-right", "person-plus", "question-circle"],
            menu_icon="list",
            default_index=0,
        )

# Handle authentication
if "user" not in st.session_state:
    if selected == "Login":
        st.title("🔑 Login")
        with st.form("Login Form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", placeholder="Enter your password", type="password")
            login_submit = st.form_submit_button("Login")
            if login_submit:
                try:
                    user = auth.get_user_by_email(email)
                    st.session_state["user"] = {"email": email, "uid": user.uid}
                    st.success(f"✅ Logged in as {email}")
                    time.sleep(1)
                    st.rerun()
                except firebase_admin.auth.UserNotFoundError:
                    st.error("❌ No user found. Please register first!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    elif selected == "Create Account":
        st.title("🆕 Create Account")
        with st.form("Register Form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Create a strong password")
            register_submit = st.form_submit_button("Sign Up")
            if register_submit:
                try:
                    auth.create_user(email=email, password=password)
                    st.success("✅ Registration successful! Please log in.")
                except Exception as e:
                    st.error(f"❌ Registration failed: {str(e)}")

    elif selected == "Forgot Password?":
        st.title("🔄 Forgot Password?")
        with st.form("Forgot Password Form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="Enter your registered email")
            reset_submit = st.form_submit_button("Reset Password")
            if reset_submit:
                try:
                    auth.send_password_reset_email(email)
                    st.success(f"✅ Password reset email sent to **{email}**. Check your inbox!")
                except firebase_admin.auth.UserNotFoundError:
                    st.error("❌ No user found with this email.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    st.stop()

# If logged in, show chatbot and chat history in the sidebar
with st.sidebar:
    st.write(f"✅ Logged in as: **{st.session_state['user']['email']}**")

    if "conversations" not in st.session_state:
        st.session_state.conversations = [[]]

    # New Chat Button
    if st.button("➕ New Chat"):
        st.session_state.conversations.append([])
        st.session_state.current_chat = len(st.session_state.conversations) - 1
        st.rerun()

    # Display chat history
    st.markdown("### Chat History")
    for i, conv in enumerate(st.session_state.conversations):
        with st.expander(f"Conversation {i+1}"):
            for msg in conv:
                role = "🧑" if msg["role"] == "user" else "🤖"
                st.write(f"{role} {msg['content']}")
            if st.button("🗑 Delete", key=f"delete_{i}"):
                del st.session_state.conversations[i]
                st.rerun()

    if st.button("🗑 Clear All Chats"):
        st.session_state.conversations = []
        st.rerun()

    if st.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()

# **Chatbot Interface**
st.title("🤖 AI Chatbot")
st.write("💬 Ask me anything!")

# Ensure at least one conversation exists before accessing it
if "conversations" not in st.session_state:
    st.session_state.conversations = [[]]  # Initialize with an empty conversation list

if "current_chat" not in st.session_state:
    st.session_state.current_chat = 0

# Display chat history in the main area
for message in st.session_state.conversations[st.session_state.current_chat]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Loading indicator (real-time animation)
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🤖 **Thinking...**")

    # Generate response with reduced token size for faster replies
    with st.spinner("Processing..."):
        try:
            response = model.generate_content(
                user_input, generation_config={"max_output_tokens": 200}
            )
            bot_response = response.text if response and response.text else "I'm not sure how to respond."
        except Exception as e:
            bot_response = f"⚠️ Error: {str(e)}"

    # Update UI with final response
    st.session_state.conversations[st.session_state.current_chat].append({"role": "assistant", "content": bot_response})
    
    msg_placeholder.markdown(bot_response)  # Replace "Thinking..." with real response
    
    st.rerun()
