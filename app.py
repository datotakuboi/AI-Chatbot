import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import google.generativeai as genai
import time
from streamlit_option_menu import option_menu
import PyPDF2
import io

# Set page config
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
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            firebase_credentials = dict(st.secrets["service_account"])
            cred = credentials.Certificate(firebase_credentials)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"🔥 Failed to initialize Firebase: {e}")

initialize_firebase()

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
                    reset_link = auth.generate_password_reset_link(email)
                    st.success(f"✅ Password reset email sent to **{email}**. Check your inbox!")
                except firebase_admin.auth.UserNotFoundError:
                    st.error("❌ No user found with this email.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    st.stop()

# ✅ **If Logged In, Show Chatbot**
with st.sidebar:
    # ✅ **PDF Upload (Appears Only After Login)**
    st.markdown("## 📂 Upload PDF for Context")
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

    pdf_text = ""
    if uploaded_pdf:
        def extract_text_from_pdf(pdf_file):
            """Extract text from an uploaded PDF file"""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages]).strip()

        pdf_text = extract_text_from_pdf(uploaded_pdf)
        st.success("📄 PDF uploaded and processed!")

    # ✅ **New Chat & Chat History**
    st.markdown("## 💬 Chat")
    if "conversations" not in st.session_state:
        st.session_state.conversations = [[]]

    if st.button("➕ New Chat"):
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
        st.session_state.conversations = []
        st.rerun()

    # ✅ **Move "Logged in as" & Logout to the Bottom**
    st.markdown("---")  # Separator for clarity
    st.write(f"✅ Logged in as: **{st.session_state['user']['email']}**")

    if st.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()

# ✅ **Chatbot Interface (Centered Title and Text)**
st.markdown(
    """
    <h1 style="text-align: center;">🤖 AI Chatbot</h1>
    <p style="text-align: center; font-size: 18px;">💬 Ask me anything!</p>
    """,
    unsafe_allow_html=True
)

# Ensure at least one conversation exists before accessing it
if "conversations" not in st.session_state:
    st.session_state.conversations = [[]]  # Initialize with an empty conversation list

if "current_chat" not in st.session_state:
    st.session_state.current_chat = 0

# **Display Chat History**
for message in st.session_state.conversations[st.session_state.current_chat]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# **User Input**
user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # **Loading Indicator**
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()

    # **Generate AI Response with PDF Context**
    with st.spinner("Processing..."):
        try:
            prompt = f"{user_input}"
            if pdf_text:
                prompt = f"Based on this document:\n\n{pdf_text}\n\nAnswer this question: {user_input}"

            response = model.generate_content(
                prompt, generation_config={"max_output_tokens": 200}
            )
            bot_response = response.text if response and response.text else "I'm not sure how to respond."
        except Exception as e:
            bot_response = f"⚠️ Error: {str(e)}"

    # **Update UI with Final Response**
    st.session_state.conversations[st.session_state.current_chat].append({"role": "assistant", "content": bot_response})
    msg_placeholder.markdown(bot_response)  # Replace "Thinking..." with real response
    
    st.rerun()
