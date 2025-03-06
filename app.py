import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import pyrebase
import google.generativeai as genai
import time
from streamlit_option_menu import option_menu
import PyPDF2

# ✅ **Set page configuration**
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")

# ✅ **Load API Key from Streamlit Secrets**
try:
    API_KEY = st.secrets["api_keys"]["GEMINI_API_KEY"]
except KeyError:
    st.error("❌ Missing Gemini API Key in Streamlit secrets!")
    st.stop()

# ✅ **Initialize Gemini AI**
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ✅ **Initialize Firebase**
if not firebase_admin._apps:
    try:
        firebase_credentials = dict(st.secrets["service_account"])
        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"🔥 Failed to initialize Firebase Admin SDK: {e}")

# ✅ Load Firebase Web App Config (for authentication via Pyrebase)
try:
    firebase_config = dict(st.secrets["firebase_config"])
    firebase = pyrebase.initialize_app(firebase_config)
    auth_pyrebase = firebase.auth()
except Exception as e:
    st.error(f"❌ Failed to initialize Firebase Web SDK: {e}")

# ✅ **Sidebar Navigation**
if "user" not in st.session_state:
    with st.sidebar:
        selected = option_menu(
            menu_title="Navigation",
            options=["Login", "Create Account", "Forgot Password?"],
            icons=["box-arrow-in-right", "person-plus", "question-circle"],
            menu_icon="list",
            default_index=0,
        )

# ✅ **Handle Authentication**
if "user" not in st.session_state:
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if selected == "Login":
            st.title("🔑 Login")
            with st.form("Login Form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", placeholder="Enter your password", type="password")
                login_submit = st.form_submit_button("Login")
                
                if login_submit:
                    try:
                        user = auth_pyrebase.sign_in_with_email_and_password(email, password)
                        if "idToken" in user:
                            st.session_state["user"] = {"email": email, "uid": user["localId"]}
                            st.success(f"✅ Logged in as {email}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Authentication failed. Please try again.")
                    except Exception as e:
                        error_message = str(e).lower()  # Convert to lowercase to catch variations
                        if "invalid_password" in error_message or "invalid_login_credentials" in error_message:
                            st.error("❌ Incorrect email or password. Please try again.")
                        elif "email_not_found" in error_message:
                            st.error("❌ Email not registered. Please sign up first.")
                        elif "too_many_attempts" in error_message:
                            st.error("❌ Too many failed attempts. Please reset your password or try again later.")
                        else:
                            st.error(f"❌ Login failed: {error_message}")

        elif selected == "Create Account":
            st.title("🆕 Create Account")
            with st.form("Register Form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Create a strong password")
                register_submit = st.form_submit_button("Sign Up")
                
                if register_submit:
                    try:
                        auth_pyrebase.create_user_with_email_and_password(email, password)
                        st.success("✅ Registration successful! Please log in.")
                    except:
                        st.error("❌ Registration failed. Try again with a stronger password.")

        elif selected == "Forgot Password?":
            st.title("🔄 Forgot Password?")
            with st.form("Forgot Password Form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="Enter your registered email")
                reset_submit = st.form_submit_button("Reset Password")
                
                if reset_submit:
                    try:
                        # Check if the email exists in Firebase Authentication
                        auth_pyrebase.get_account_info(email)
                        auth_pyrebase.send_password_reset_email(email)
                        st.success(f"✅ Password reset email sent to **{email}**. Check your inbox!")
                    except Exception as e:
                        error_message = str(e).lower()
                        if "email_not_found" in error_message:
                            st.error("❌ No user found with this email. Please register first.")
                        else:
                            st.error(f"❌ Failed to send reset email: {error_message}")
    st.stop()



# ✅ **If Logged In, Show Chatbot**
with st.sidebar:
    # ✅ **PDF Upload (Appears Only After Login)**
    st.markdown("## 📂 Upload PDF for Context")
    uploaded_pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    pdf_text = ""

    if uploaded_pdfs:
        def extract_text_from_pdfs(pdf_files):
            """Extract and combine text from multiple uploaded PDF file"""
            combined_text = ""
            for pdf_file in pdf_files:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
                combined_text += f"\n\n--- Extracted from {pdf_file.name} ---\n{text}"
            return combined_text.strip()

        pdf_text = extract_text_from_pdfs(uploaded_pdfs)
        st.success(f"📄 {len(uploaded_pdfs)} PDF(s) uploaded and processed!")

    # ✅ **New Chat & Chat History**
    st.markdown("## 💬 Chat")
    if "conversations" not in st.session_state:
        st.session_state.conversations = [[]]

    if st.button("+ New Chat"):
        st.session_state.conversations.append([])
        st.session_state.current_chat = len(st.session_state.conversations) - 1
        st.rerun()

    # **Display Chat History**
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
        st.session_state.conversations = [[]]  # Ensure at least one empty conversation exists
        st.session_state.current_chat = 0  # Reset index to avoid out-of-range errors
        st.rerun()


    # ✅ **Move "Logged in as" & Logout to the Bottom**
    st.markdown("---")  # Separator for clarity
    st.write(f"✅ Logged in as: **{st.session_state['user']['email']}**")
    if st.button("Logout"):
        st.session_state.pop("user", None)
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()

# ✅ Display logo and welcome message in the perfect center
st.markdown(
    """
    <div style="text-align: center;">
        <img src="https://raw.githubusercontent.com/datotakuboi/AI-Chatbot/main/citlogo.png" style="width: 500px;">
        <h2>Welcome to CIT Chatbot 🤖</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# ✅ **Chatbot Interface**
if "conversations" not in st.session_state:
    st.session_state.conversations = [[]]  

if "current_chat" not in st.session_state:
    st.session_state.current_chat = 0

# ✅ **Display Chat History with Styling**
chat_history_placeholder = st.empty()

def display_chat_history():
    chat_history_placeholder.empty()  # Clear before rendering

    with chat_history_placeholder.container():
        st.markdown("""
    <style>
    /* Chat Bubble Styles */
    .chat-bubble {
        padding: 12px;
        border-radius: 15px;
        margin-bottom: 5px;
        max-width: 65%; /* Ensures bubbles don't stretch too much */
        word-wrap: break-word;
        font-size: 16px;
    }

    .user-bubble {
        background-color: #0078FF;
        color: white;
        align-self: flex-end;
        text-align: right;
        margin-left: auto;
    }

    .bot-bubble {
        background-color: #F0F0F0;
        color: black;
        align-self: flex-start;
        text-align: left;
        margin-right: auto;
    }

    /* Chat Container - Centers the Chat */
    .chat-container {
        display: flex;
        flex-direction: column;
        margin-bottom: 10px;
        max-width: 750px; /* Set max width to match ChatGPT */
        margin: auto; /* Center chat container */
    }

    /* Fix Input Field Width */
    .stChatInput {
        display: flex;
        justify-content: center;
        margin: auto;
    }

    /* Target the actual input field */
    div[data-baseweb="base-input"] {
        max-width: 750px !important; /* Match chat width */
        width: 100% !important;
        margin: auto !important;
    }

    /* Adjust parent div of input field */
    div[data-testid="stChatInput"] {
        max-width: 750px !important;
        width: 100% !important;
        margin: auto !important;
        padding-bottom: 10px; /* Add space between input and chat */
    }
    </style>
""", unsafe_allow_html=True)


        for msg in st.session_state.conversations[st.session_state.current_chat]:
            role = msg["role"]
            message_content = msg["content"]

            if role == "user":
                st.markdown(f"""
                <div class="chat-container">
                    <div class="chat-bubble user-bubble">{message_content}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-container">
                    <div class="chat-bubble bot-bubble">{message_content}</div>
                </div>
                """, unsafe_allow_html=True)


# ✅ **Call function to display chat history**
display_chat_history()


# **User Input**
user_input = st.chat_input("Ask anything...")

if user_input:
    # Append user message to session state
    st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
    display_chat_history()
    
    # Append temporary bot response (spinner)
    temp_bot_msg = {"role": "assistant", "content": "🤖 Thinking..."}
    st.session_state.conversations[st.session_state.current_chat].append(temp_bot_msg)
    display_chat_history()

    # Construct conversation history for AI
    conversation_history = "\n".join(
        [f"User: {msg['content']}" if msg["role"] == "user" else msg['content']
         for msg in st.session_state.conversations[st.session_state.current_chat]]
    )

    # Prepare the prompt with context
    prompt = f"{conversation_history}\n\nUser: {user_input}"
    if pdf_text:
        prompt = f"Based on the following extracted information from uploaded PDFs:\n\n{pdf_text}\n\n{prompt}"

    # **Generate AI Response**
    try:
        response = model.generate_content(prompt, generation_config={
            "temperature": 0.7,  # Adjusts response creativity
            "top_p": 0.9,        # Ensures diverse responses
            "top_k": 40,         # Limits response randomness
            "max_output_tokens": 2048  # Allows **longer** responses
        })
        bot_response = response.text if response and response.text else "I'm not sure how to respond."
    except Exception as e:
        bot_response = f"⚠️ Error: {str(e)}"

    # Replace the temporary message with the actual bot response
    st.session_state.conversations[st.session_state.current_chat][-1]["content"] = bot_response

    # **Update UI**
    display_chat_history()
    st.rerun()
