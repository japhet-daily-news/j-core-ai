import streamlit as st
from google import genai
from google.genai.errors import APIError
import sqlite3
import bcrypt
import time
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="J-CORE AI Workspace", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DATABASE SETUP ---
conn = sqlite3.connect('jj_workspace_users.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        avatar TEXT DEFAULT '⚡'
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query TEXT,
        answer TEXT,
        category TEXT DEFAULT 'General',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

# --- HELPER FUNCTIONS ---
def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Check if username exists, if so, append a random tag to make it unique and allow registration
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    if c.fetchone():
        username = f"{username}_{random.randint(1000, 9999)}"
        
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True, username
    except Exception:
        return False, username

# --- ULTRA-MODERN DRIBBBLE DARK THEME & MICRO-INTERACTIONS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Dark Mode Obsidian Background */
    .stApp {
        background: radial-gradient(circle at 80% 20%, #171033 0%, #0c0e15 50%, #07090d 100%) !important;
        color: #F8FAFC !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6, .stMarkdown, p, span, label {
        color: #F8FAFC !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    p, li {
        font-size: 1.02rem !important;
        line-height: 1.6 !important;
        color: #94A3B8 !important;
    }
    
    /* Collapsible Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #090b10 !important;
        border-right: 1px solid rgba(139, 92, 246, 0.15) !important;
    }
    
    /* Hero Suggestion Cards */
    .suggestion-card {
        background: rgba(20, 24, 38, 0.7);
        border: 1px solid rgba(139, 92, 246, 0.22);
        backdrop-filter: blur(12px);
        padding: 22px;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        height: 100%;
    }
    .suggestion-card:hover {
        transform: translateY(-4px);
        border-color: rgba(139, 92, 246, 0.6);
        box-shadow: 0 20px 40px rgba(139, 92, 246, 0.15);
        background: rgba(26, 31, 49, 0.85);
    }
    
    /* Glassmorphism Auth Card */
    .glass-auth-card {
        background: rgba(16, 19, 29, 0.85);
        padding: 42px;
        border-radius: 28px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 35px 70px rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(24px);
    }
    
    /* Active Model / Persona Badge */
    .model-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(139, 92, 246, 0.12);
        border: 1px solid rgba(139, 92, 246, 0.35);
        color: #C084FC !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #10B981;
    }

    /* Vibrant Gradient Buttons */
    .stButton button {
        background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.8rem 1.5rem !important;
        width: 100%;
        box-shadow: 0 10px 25px rgba(139, 92, 246, 0.35);
        transition: all 0.25s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 35px rgba(236, 72, 153, 0.5);
    }
    
    /* Inputs */
    .stTextInput input, textarea {
        background-color: #121520 !important;
        color: #F8FAFC !important;
        -webkit-text-fill-color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 16px !important;
        font-size: 1.02rem !important;
        padding: 14px !important;
    }
    .stTextInput input:focus, textarea:focus {
        border-color: #8B5CF6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.25);
    }
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
if "active_model" not in st.session_state:
    st.session_state.active_model = "models/gemini-3.8-flash"

# --- API CLIENT INITIALIZATION ---
GEMINI_API_KEY = "AQ.Ab8RN6LWK92ZT8QlFuEo65z0aDn3L8qASy3ZekC2vKRuOANQ5g"
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    client = None

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    col_preview, col_form = st.columns([1.1, 1], gap="large")
    
    with col_preview:
        st.markdown("""
            <div style="padding: 2.5rem 1rem; display: flex; flex-direction: column; justify-content: center; height: 100%;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <span style="font-size: 2.4rem;">⚡</span>
                    <h2 style="font-weight: 800; font-size: 2.2rem; color: #FFFFFF; margin: 0; letter-spacing: -0.5px;">J-CORE AI</h2>
                </div>
                <p style="font-size: 1.15rem; color: #94A3B8; margin-bottom: 2.5rem;">
                    Next-generation intelligent workspace. Built with lightning-fast neural orchestration, multi-turn context, and sleek glassmorphism.
                </p>
                <div style="background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.35); padding: 20px 24px; border-radius: 20px; margin-bottom: 20px;">
                    <div style="font-size: 0.75rem; color: #C084FC; font-weight: 700; margin-bottom: 6px;">LIVE SYNTHESIS ENGINE</div>
                    <div style="color: #F8FAFC; font-size: 0.98rem;">Seamless code generation, document analysis, and deep research workflows.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_form:
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-auth-card">', unsafe_allow_html=True)
        
        st.markdown("""
            <div style="text-align: center; margin-bottom: 28px;">
                <h2 style="font-size: 1.8rem; font-weight: 700; margin-bottom: 6px; color: #FFFFFF;">Workspace Access</h2>
                <p style="color: #94A3B8; font-size: 0.92rem;">Sign in or create your secure account</p>
            </div>
        """, unsafe_allow_html=True)
        
        auth_mode = st.radio("Mode", ["🔐 Sign In", "⚡ Register"], label_visibility="collapsed", horizontal=True)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        if auth_mode == "🔐 Sign In":
            login_user_input = st.text_input("Username", key="login_user")
            login_pass_input = st.text_input("Password", type="password", key="login_pass")
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            if st.button("Sign In"):
                c.execute("SELECT id, password FROM users WHERE username = ?", (login_user_input,))
                row = c.fetchone()
                if row and bcrypt.checkpw(login_pass_input.encode('utf-8'), row[1]):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user_input
                    st.session_state.user_id = row[0]
                    
                    c.execute("SELECT query, answer FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 20", (row[0],))
                    past_chats = c.fetchall()
                    st.session_state.messages = []
                    for q, a in reversed(past_chats):
                        st.session_state.messages.append({"role": "user", "content": q})
                        st.session_state.messages.append({"role": "assistant", "content": a})
                        
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        elif auth_mode == "⚡ Register":
            new_user = st.text_input("Choose Username", key="signup_user")
            new_pass = st.text_input("Choose Password", type="password", key="signup_pass")
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            if st.button("Create Account & Login"):
                if new_user and new_pass:
                    success, assigned_username = create_user(new_user, new_pass)
                    if success:
                        c.execute("SELECT id FROM users WHERE username = ?", (assigned_username,))
                        row = c.fetchone()
                        st.session_state.logged_in = True
                        st.session_state.username = assigned_username
                        st.session_state.user_id = row[0]
                        st.session_state.messages = []
                        st.success(f"Account created successfully as '{assigned_username}'!")
                        st.rerun()
                    else:
                        st.error("Registration failed. Please try again.")
                else:
                    st.warning("Please fill in all fields.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN APP WORKSPACE ---
else:
    # --- COLLAPSIBLE SIDEBAR (LEFT) ---
    with st.sidebar:
        if st.button("✨ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 🕒 Recent History")
        c.execute("SELECT query, timestamp FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10", (st.session_state.user_id,))
        recent_threads = c.fetchall()
        
        if not recent_threads:
            st.markdown("<p style='font-size: 0.85rem; color: #64748B;'>No recent threads yet.</p>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='font-size: 0.75rem; color: #8B5CF6; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>Today</span>", unsafe_allow_html=True)
            for q, ts in recent_threads[:5]:
                display_title = q[:30] + "..." if len(q) > 30 else q
                if st.button(f"💬 {display_title}", key=f"hist_{ts}"):
                    st.session_state.messages = [{"role": "user", "content": q}]
                    st.rerun()

        st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        col_prof1, col_prof2 = st.columns([1, 3])
        with col_prof1:
            st.markdown("<div style='font-size: 1.8rem; text-align: center;'>⚡</div>", unsafe_allow_html=True)
        with col_prof2:
            st.markdown(f"<div style='font-weight: 700; font-size: 0.95rem; color: #F8FAFC;'>{st.session_state.username}</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.75rem; color: #10B981; font-weight: 600;'>🟢 Pro Plan Active</div>", unsafe_allow_html=True)
            
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.messages = []
            st.rerun()

    # --- MAIN WORKSPACE / HERO AREA (CENTER) ---
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
                <div class="model-badge"><span class="pulse-dot"></span> {st.session_state.active_model}</div>
            </div>
        """, unsafe_allow_html=True)
    with col_top2:
        selected_model = st.selectbox(
            "Model", 
            ["models/gemini-3.8-flash", "models/gemini-3.8-pro"], 
            label_visibility="collapsed"
        )
        if selected_model != st.session_state.active_model:
            st.session_state.active_model = selected_model

    # Welcome Message (If no active messages)
    if not st.session_state.messages:
        st.markdown(f"""
            <div style="text-align: center; margin-top: 4rem; margin-bottom: 2.5rem;">
                <h1 style="font-size: 2.6rem; font-weight: 800; color: #FFFFFF; letter-spacing: -1px; margin-bottom: 10px;">
                    Good morning, {st.session_state.username}. What are we building or exploring today?
                </h1>
                <p style="font-size: 1.15rem; color: #94A3B8;">Select a starter prompt below or type your inquiry into the neural workspace.</p>
            </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        starter_prompt = None
        
        with c1:
            st.markdown("""
                <div class="suggestion-card">
                    <div style="font-size: 1.6rem; margin-bottom: 10px;">💡</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin-bottom: 6px;">Brainstorm ideas</div>
                    <div style="font-size: 0.88rem; color: #94A3B8;">Generate innovative product angles & growth strategies.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Start Brainstorming", key="btn_brainstorm", use_container_width=True):
                starter_prompt = "Brainstorm high-impact product ideas and growth strategies for a next-gen AI platform."

        with c2:
            st.markdown("""
                <div class="suggestion-card">
                    <div style="font-size: 1.6rem; margin-bottom: 10px;">⚡</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin-bottom: 6px;">Write code</div>
                    <div style="font-size: 0.88rem; color: #94A3B8;">Architect full-stack modules or debug complex scripts.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Write Code", key="btn_code", use_container_width=True):
                starter_prompt = "Write a robust, production-ready Python backend API architecture with async support."

        with c3:
            st.markdown("""
                <div class="suggestion-card">
                    <div style="font-size: 1.6rem; margin-bottom: 10px;">📊</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin-bottom: 6px;">Analyze a topic</div>
                    <div style="font-size: 0.88rem; color: #94A3B8;">Break down advanced scientific or market trends.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Analyze Topic", key="btn_analyze", use_container_width=True):
                starter_prompt = "Provide a deep analytical breakdown of current trends in neural orchestration and AI agents."

        with c4:
            st.markdown("""
                <div class="suggestion-card">
                    <div style="font-size: 1.6rem; margin-bottom: 10px;">🎨</div>
                    <div style="font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin-bottom: 6px;">Creative design</div>
                    <div style="font-size: 0.88rem; color: #94A3B8;">Draft UX wireframes and brand typography guidelines.</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Create Design", key="btn_design", use_container_width=True):
                starter_prompt = "Design a futuristic UI layout framework focusing on dark mode glassmorphism and micro-interactions."
                
        if starter_prompt:
            st.session_state.messages.append({"role": "user", "content": starter_prompt})
            st.rerun()
    
    else:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="⚡" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)

    # --- CENTERED INPUT BAR ---
    user_query = st.text_area(
        "Workspace Input", 
        placeholder="Ask anything or type instructions...", 
        key="main_workspace_input",
        height=100,
        label_visibility="collapsed"
    )

    col_util1, col_util2, col_util3 = st.columns([1, 1, 3])
    with col_util1:
        uploaded_file = st.file_uploader("Upload File", type=["pdf", "png", "jpg", "txt"], label_visibility="collapsed")
    with col_util2:
        if st.button("🎙️ Voice"):
            st.toast("Voice input listening simulated.", icon="🎙️")
    with col_util3:
        send_btn = st.button("🚀 Send Prompt", use_container_width=True)

    # Handle Submission
    if send_btn and user_query:
        if not client:
            st.error("API client not initialized.")
        else:
            prompt = user_query
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="⚡"):
                message_placeholder = st.empty()
                full_response = ""
                
                max_retries = 3
                retry_delay = 2
                success = False

                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=st.session_state.active_model,
                            contents=prompt
                        )
                        full_response = response.text
                        success = True
                        break
                    except APIError as e:
                        if e.code == 503 and attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            full_response = f"API Error: {str(e)}"
                            break
                    except Exception as e:
                        full_response = f"API Error: {str(e)}"
                        break

                message_placeholder.markdown(full_response)
                
                if success:
                    c.execute("INSERT INTO history (user_id, query, answer) VALUES (?, ?, ?)", 
                              (st.session_state.user_id, prompt, full_response))
                    conn.commit()

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun()
