import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
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
    col1, col2, col3 = st.columns([1, 2, 1])  # Centering the forms

    with col2:  # Form appears in the middle column
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
    st.markdown("## 📂 Upload PDF for Context")
    uploaded_pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    pdf_text = ""
    if uploaded_pdfs:
        def extract_text_from_pdfs(pdf_files):
            """Extract and combine text from multiple uploaded PDFs"""
            combined_text = ""
            for pdf_file in pdf_files:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
                combined_text += f"\n\n--- Extracted from {pdf_file.name} ---\n{text}"
            return combined_text.strip()

        pdf_text = extract_text_from_pdfs(uploaded_pdfs)
        st.success(f"📄 {len(uploaded_pdfs)} PDF(s) uploaded and processed!")

    st.markdown("## 💬 Chat")
    if st.button("+ New Chat"):
        st.session_state.conversations.append([])
        st.session_state.current_chat = len(st.session_state.conversations) - 1
        st.rerun()

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
        st.session_state.conversations = [[]]
        st.session_state.current_chat = 0
        st.rerun()

    st.markdown("---")
    st.write(f"✅ Logged in as: **{st.session_state['user']['email']}**")
    if st.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()

# ✅ **Welcome Message with Image**
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("citlogo.png", use_container_width=True)

st.markdown("<h2 style='text-align: center;'>Welcome to CIT Chatbot 🤖</h2>", unsafe_allow_html=True)

# ✅ **Chat Interface with Limited Width**
chat_container = st.container()

with chat_container:
    st.markdown("""
        <style>
            .chat-container {
                max-width: 900px;
                margin: auto;
            }
        </style>
        <div class="chat-container">
    """, unsafe_allow_html=True)

    chat_history_placeholder = st.empty()

    def display_chat_history():
        chat_history_placeholder.empty()
        with chat_history_placeholder.container():
            for msg in st.session_state.conversations[st.session_state.current_chat]:
                role = msg["role"]
                message_content = msg["content"]

                if role == "user":
                    st.markdown(f"<div style='background-color:#0078FF; color:white; padding:10px; border-radius:10px; margin-bottom:5px;'>{message_content}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color:#F0F0F0; color:black; padding:10px; border-radius:10px; margin-bottom:5px;'>{message_content}</div>", unsafe_allow_html=True)

    display_chat_history()

    user_input = st.chat_input("Ask anything...")
    if user_input:
        st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
        with st.spinner("Processing..."):
            response = model.generate_content(user_input)
            bot_response = response.text if response and response.text else "I'm not sure how to respond."
        st.session_state.conversations[st.session_state.current_chat].append({"role": "assistant", "content": bot_response})
        display_chat_history()
        st.rerun()
