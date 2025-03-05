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

# ✅ **Authentication Handling**
if "user" not in st.session_state:
    with st.sidebar:
        selected = option_menu(
            menu_title="Navigation",
            options=["Login", "Create Account", "Forgot Password?"],
            icons=["box-arrow-in-right", "person-plus", "question-circle"],
            menu_icon="list",
            default_index=0,
        )

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

# ✅ **PDF Upload for Context**
pdf_text = ""
with st.sidebar:
    st.markdown("## 📂 Upload PDF for Context")
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

    if uploaded_pdf:
        def extract_text_from_pdf(pdf_file):
            """Extract text from an uploaded PDF file"""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()]).strip()

        pdf_text = extract_text_from_pdf(uploaded_pdf)
        st.success("📄 PDF uploaded and processed!")

# ✅ **Chat History Handling**
if "conversations" not in st.session_state:
    st.session_state.conversations = [[]]  
if "current_chat" not in st.session_state:
    st.session_state.current_chat = 0

# ✅ **Custom CSS for Chat Alignment**
st.markdown("""
    <style>
        .chat-container {
            display: flex;
            flex-direction: column;
        }
        .user-message {
            background-color: #DCF8C6; /* Light green for user */
            padding: 10px;
            border-radius: 15px;
            max-width: 70%;
            align-self: flex-end;
            text-align: right;
        }
        .assistant-message {
            background-color: #EAEAEA; /* Light gray for assistant */
            padding: 10px;
            border-radius: 15px;
            max-width: 70%;
            align-self: flex-start;
            text-align: left;
        }
    </style>
""", unsafe_allow_html=True)

# ✅ **Display Chat History**
st.markdown("<h2 style='text-align: center;'>Welcome to AI Chatbot</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>💬 Ask me anything!</p>", unsafe_allow_html=True)

chat_container = st.container()
with chat_container:
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for message in st.session_state.conversations[st.session_state.current_chat]:
        if message["role"] == "user":
            st.markdown(f"<div class='user-message'>{message['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='assistant-message'>{message['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ✅ **User Input & AI Response**
user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
    st.rerun()

    # **Generate AI Response**
    try:
        prompt = user_input
        if pdf_text:
            prompt = f"Based on this document:\n\n{pdf_text}\n\nAnswer this question: {user_input}"

        generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048  # Allows longer responses
        }

        response = model.generate_content(prompt, generation_config=generation_config)
        bot_response = response.text if response and response.text else "I'm not sure how to respond."
    except Exception as e:
        bot_response = f"⚠️ Error: {str(e)}"

    # **Store AI Response**
    st.session_state.conversations[st.session_state.current_chat].append({"role": "assistant", "content": bot_response})
    st.rerun()
