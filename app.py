import streamlit as st
from google import genai
from google.genai import types
import sqlite3
import bcrypt
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="J-CORE AI", page_icon="⚡", layout="wide")

# --- DATABASE SETUP ---
conn = sqlite3.connect('jj_ai_users.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query TEXT,
        answer TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

# --- HELPER FUNCTIONS ---
def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# --- UI STYLING & BALANCED THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Font & Balanced Slate Background */
    .stApp {
        background-color: #1E293B !important; 
        color: #E2E8F0 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stTextInput label, .stSelectbox label, .stRadio label {
        color: #F1F5F9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0F172A !important; 
        border-right: 1px solid #334155 !important;
    }
    
    /* Branding Header */
    .brand-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-bottom: 2rem;
    }
    .brand-badge {
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #38BDF8;
        padding: 6px 16px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .brand-title {
        font-weight: 800;
        font-size: 3.5rem;
        color: #F8FAFC;
        margin: 0px;
        letter-spacing: -1px;
        text-align: center;
    }
    
    /* Auth Card */
    .auth-card {
        background: #0F172A;
        padding: 40px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 15px 30px -5px rgba(0, 0, 0, 0.3);
    }
    
    /* Buttons */
    .stButton button {
        background: #2563EB !important;
        color: white !important; 
        font-weight: 600 !important; 
        border: none !important;
        border-radius: 8px !important; 
        padding: 0.6rem 1.5rem !important;
        width: 100%;
        transition: all 0.2s ease !important;
    }
    .stButton button:hover {
        background: #1D4ED8 !important;
        transform: translateY(-1px);
    }
    
    /* Input Fields */
    .stTextInput input, .stSelectbox select, .stChatInput input {
        background-color: #0F172A !important; 
        color: #F8FAFC !important; 
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    
    .login-status {padding: 10px; border-radius: 6px; text-align: center; font-weight: bold;}
    .success-box {background-color: rgba(16, 185, 129, 0.12); color: #34D399 !important; border: 1px solid #10B981;}
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Safe API Key Initialization (Pulling securely from Streamlit Secrets)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ GEMINI_API_KEY is missing from Streamlit Secrets. Please configure it in your deployment settings.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.4, 1])
    
    with col2:
        st.markdown("""
            <div class="brand-container">
                <div class="brand-badge">Secure AI Terminal</div>
                <h1 class="brand-title">J-CORE AI</h1>
                <p style="color: #94A3B8; margin-top: 8px; font-size: 0.95rem; text-align: center;">Advanced Multi-Tool Intelligence Workspace</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="auth-card">', unsafe_allow_html=True)
            
            auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Sign In", "⚡ Register", "🔑 Recovery"])
            
            with auth_tab1:
                st.write("")
                login_user_input = st.text_input("Username", key="login_user")
                login_pass_input = st.text_input("Password", type="password", key="login_pass")
                st.write("")
                if st.button("Sign In"):
                    c.execute("SELECT id, password FROM users WHERE username = ?", (login_user_input,))
                    row = c.fetchone()
                    if row and bcrypt.checkpw(login_pass_input.encode('utf-8'), row[1]):
                        st.session_state.logged_in = True
                        st.session_state.username = login_user_input
                        st.session_state.user_id = row[0]
                        
                        c.execute("SELECT query, answer FROM history WHERE user_id = ?", (row[0],))
                        past_chats = c.fetchall()
                        st.session_state.messages = []
                        for q, a in past_chats:
                            st.session_state.messages.append({"role": "user", "content": q})
                            st.session_state.messages.append({"role": "assistant", "content": a})
                            
                        st.success("Login successful. Loading workspace...")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
                        
            with auth_tab2:
                st.write("")
                new_user = st.text_input("Choose Username", key="signup_user")
                new_pass = st.text_input("Choose Password", type="password", key="signup_pass")
                st.write("")
                if st.button("Create Account"):
                    if new_user and new_pass:
                        if create_user(new_user, new_pass):
                            st.success("Account created successfully! Switch to Sign In.")
                        else:
                            st.error("This username is already taken.")
                    else:
                        st.warning("Please fill in all fields.")
                        
            with auth_tab3:
                st.write("")
                reset_user = st.text_input("Your Username", key="reset_user")
                new_reset_pass = st.text_input("New Password", type="password", key="reset_pass")
                st.write("")
                if st.button("Reset Password"):
                    if reset_user and new_reset_pass:
                        c.execute("SELECT id FROM users WHERE username = ?", (reset_user,))
                        if c.fetchone():
                            new_hashed = bcrypt.hashpw(new_reset_pass.encode('utf-8'), bcrypt.gensalt())
                            c.execute("UPDATE users SET password = ? WHERE username = ?", (new_hashed, reset_user))
                            conn.commit()
                            st.success("Password updated successfully! Switch to Sign In.")
                        else:
                            st.error("Username not found.")
                    else:
                        st.warning("Please fill in all fields.")
            
            st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN APP WORKSPACE ---
else:
    st.sidebar.markdown(f"""
        <div class="login-status success-box">
        🟢 Active Operator: {st.session_state.username}
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.write("")
    if st.sidebar.button("Sign Out"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.session_state.messages = []
        st.success("Signed out safely.")
        st.rerun()

    menu = st.sidebar.selectbox("Navigation Menu", [
        "Chat & Research", 
        "Document Analysis", 
        "Voice Assistant", 
        "Vision & Image Studio", 
        "Task Automation", 
        "Scheduling", 
        "History"
    ])

    if menu == "Chat & Research":
        st.markdown("## 💬 J-CORE AI Chat Assistant")
        st.markdown("Ask anything below. Your chat history streams directly into the conversation stream.")
        st.write("")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask a question or type a research topic..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                try:
                    response = client.models.generate_content_stream(model='gemini-3.5-flash', contents=prompt)
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response)
                    
                    c.execute("INSERT INTO history (user_id, query, answer) VALUES (?, ?, ?)", 
                              (st.session_state.user_id, prompt, full_response))
                    conn.commit()
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        full_response = "⚠️ Free tier limit reached (5 requests per minute). Please wait about 15 seconds before trying again."
                    else:
                        full_response = f"An error occurred: {e}"
                    message_placeholder.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

    elif menu == "Document Analysis":
        st.markdown("## 📁 Document Analysis Workspace")
        st.markdown("Upload files (PDFs, text documents, or images) for deep scanning and summarization.")
        st.write("")

        doc_col1, doc_col2 = st.columns([1, 1.4], gap="large")

        with doc_col1:
            st.subheader("📥 File Upload Panel")
            uploaded_file = st.file_uploader("Choose a file (Max 5MB)", type=["pdf", "txt", "png", "jpg", "jpeg"])
            doc_query = st.text_input("Instructions for File", placeholder="e.g. Summarize the key takeaways...")
            st.write("")
            analyze_btn = st.button("Analyze Document")

        with doc_col2:
            st.subheader("📤 Document Scan Results")
            if analyze_btn:
                if uploaded_file:
                    if uploaded_file.size > 5 * 1024 * 1024:
                         st.error("File size exceeds the 5MB limit.")
                    else:
                        with st.spinner("Processing your document..."):
                            try:
                                file_bytes = uploaded_file.read()
                                temp_filename = uploaded_file.name
                                with open(temp_filename, "wb") as f: f.write(file_bytes)
                                gemini_file = client.files.upload(file=temp_filename, config={'mime_type': uploaded_file.type})
                                
                                prompt_text = doc_query if doc_query else "Please analyze this document in detail:"
                                response = client.models.generate_content(model='gemini-3.5-flash', contents=[gemini_file, prompt_text])
                                answer_text = response.text
                                
                                c.execute("INSERT INTO history (user_id, query, answer) VALUES (?, ?, ?)", 
                                          (st.session_state.user_id, f"[File] {uploaded_file.name}", answer_text))
                                conn.commit()
                                
                                st.success("Document analyzed successfully.")
                                st.markdown("---")
                                st.write(answer_text)
                            except Exception as e:
                                error_msg = str(e)
                                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                                    st.error("⚠️ Free tier limit reached. Please wait ~15 seconds and try again.")
                                else:
                                    st.error(f"An error occurred: {e}")
                else: 
                    st.warning("Please upload a file before clicking analyze.")
            else:
                st.info("System ready. Upload a file on the left and click **Analyze Document**.")

    elif menu == "Voice Assistant":
        st.header("🎙️ Voice Assistant")
        voice_query = st.text_input("Ask your question:", key="voice_input")
        if st.button("Submit Question"):
             with st.spinner("Generating response..."):
                try:
                    response = client.models.generate_content(model='gemini-3.5-flash', contents=voice_query)
                    answer_text = response.text
                    
                    c.execute("INSERT INTO history (user_id, query, answer) VALUES (?, ?, ?)", 
                              (st.session_state.user_id, f"[Voice] {voice_query}", answer_text))
                    conn.commit()
                    
                    st.write(answer_text)
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        st.error("⚠️ Free tier limit reached. Please wait ~15 seconds and try again.")
                    else:
                        st.error(f"An error occurred: {e}")

    elif menu == "Vision & Image Studio":
        st.header("📸 Vision & Image Studio")
        action = st.radio("Select Action", ["Analyze Photo", "Generate Image"])
        if action == "Analyze Photo":
            st.camera_input("Capture frame")
        else:
            st.text_input("Enter Image Prompt")

    elif menu in ["Task Automation", "Scheduling"]:
        st.write(f"The **{menu}** module is currently under maintenance.")

    elif menu == "History":
        st.header(f"📜 Activity History for {st.session_state.username}")
        
        c.execute("SELECT query, answer FROM history WHERE user_id = ?", (st.session_state.user_id,))
        user_history = c.fetchall()
        
        if not user_history:
            st.info("No past activity found.")
        else:
            if st.button("Clear My History"):
                c.execute("DELETE FROM history WHERE user_id = ?", (st.session_state.user_id,))
                conn.commit()
                st.session_state.messages = []
                st.rerun()
                
            for q, a in reversed(user_history):
                with st.expander(f"Query: {q}"):
                    st.write(a)
