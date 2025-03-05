import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import google.generativeai as genai
import time
from streamlit_option_menu import option_menu
import PyPDF2

# ✅ **Set page configuration**
st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")

# ✅ **Apply Custom CSS for Chat Styling**
st.markdown(
    """
    <style>
        .chat-container {
            max-width: 700px;
            margin: auto;
        }
        .chat-message {
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
            max-width: 80%;
        }
        .user-message {
            background-color: #0078D4;
            color: white;
            align-self: flex-end;
            text-align: right;
            margin-left: auto;
        }
        .bot-message {
            background-color: #E5E5E5;
            color: black;
            align-self: flex-start;
            text-align: left;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    # ✅ **PDF Upload (Appears Only After Login)**
    st.markdown("## 📂 Upload PDF for Context")
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])

    pdf_text = ""
    if uploaded_pdf:
        def extract_text_from_pdf(pdf_file):
            """Extract text from an uploaded PDF file"""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()]).strip()

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

    # ✅ **Move "Logged in as" & Logout to the Bottom**
    st.markdown("---")  # Separator for clarity
    st.write(f"✅ Logged in as: **{st.session_state['user']['email']}**")

    if st.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()

# ✅ **Chatbot Interface**
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

if "conversations" not in st.session_state:
    st.session_state.conversations = [[]]  

if "current_chat" not in st.session_state:
    st.session_state.current_chat = 0

# **Display Chat History with Styling**
for message in st.session_state.conversations[st.session_state.current_chat]:
    role_class = "user-message" if message["role"] == "user" else "bot-message"
    
    st.markdown(
        f"<div class='chat-message {role_class}'>{message['content']}</div>",
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# **User Input**
user_input = st.chat_input("Type your message...")

if user_input:
    # Append User Message
    st.session_state.conversations[st.session_state.current_chat].append({"role": "user", "content": user_input})
    st.markdown(f"<div class='chat-message user-message'>{user_input}</div>", unsafe_allow_html=True)

    # **Loading Indicator**
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()

    # **Generate AI Response**
    with st.spinner("Processing..."):
        try:
            prompt = user_input
            if pdf_text:
                prompt = f"Based on this document:\n\n{pdf_text}\n\nAnswer this question: {user_input}"

            response = model.generate_content(prompt)
            bot_response = response.text if response and response.text else "I'm not sure how to respond."
        except Exception as e:
            bot_response = f"⚠️ Error: {str(e)}"

    # Append Bot Response
    st.session_state.conversations[st.session_state.current_chat].append({"role": "assistant", "content": bot_response})
    msg_placeholder.markdown(f"<div class='chat-message bot-message'>{bot_response}</div>", unsafe_allow_html=True)

    st.rerun()
