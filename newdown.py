import streamlit as st
import yt_dlp
import os
import time
import shutil
import json
from pathlib import Path

# =========================================================
# APP CONFIG & SESSION STATE
# =========================================================
st.set_page_config(
    page_title="PyMedia Downloader Pro",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for persistence
if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "last_url" not in st.session_state:
    st.session_state.last_url = ""

# =========================================================
# PATHS & SETTINGS
# =========================================================
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
SETTINGS_FILE = BASE_DIR / "settings.json"
DOWNLOAD_DIR.mkdir(exist_ok=True)

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "default_quality": "1080p HD",
    "auto_cleanup": False,
    "download_format": "mp4",
    "concurrent_fragment_downloads": 4,
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=4)

settings = load_settings()

# =========================================================
# DYNAMIC THEMING (CSS) - Python Brand Colors
# =========================================================
bg, card, text, accent = ("#0f172a", "#1e293b", "white", "#3776ab") # Python Blue

st.markdown(f"""
<style>
    .main {{ background: {bg}; color: {text}; }}
    .stButton > button {{ width:100%; border-radius:8px; background:{accent}; color:white; border:none; transition: 0.3s; }}
    .stButton > button:hover {{ background:#ffd43b; color:#0f172a; }} /* Python Yellow */
    .stDownloadButton > button {{ width:100%; border-radius:8px; background:#22c55e; color:white; border:none; }}
    .card {{ background:{card}; padding:25px; border-radius:15px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# UTILITIES & YT-DLP CORE
# =========================================================
def check_ffmpeg():
    return shutil.which("ffmpeg") is not None

@st.cache_data(show_spinner=False)
def get_video_info(url):
    opts = {"quiet": True, "noplaylist": True, "nocheckcertificate": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        return {"error": str(e)}

def download_video(url, quality, progress_bar):
    quality_map = {
        "Best": "bestvideo+bestaudio/best",
        "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best",
        "1080p HD": "bestvideo[height<=1080]+bestaudio/best",
        "720p": "bestvideo[height<=720]+bestaudio/best",
        "Audio MP3": "bestaudio/best",
    }

    timestamp = int(time.time())
    output_template = str(DOWNLOAD_DIR / f"%(title).50s_{timestamp}.%(ext)s")

    ydl_opts = {
        "format": quality_map.get(quality, "best"),
        "outtmpl": output_template,
        "merge_output_format": settings["download_format"],
        "noplaylist": True,
    }

    if quality == "Audio MP3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    def hook(d):
        if d["status"] == "downloading":
            p = d.get("_percent_str", "0%").replace("%", "").strip()
            try:
                progress_bar.progress(int(float(p)) / 100)
            except: pass

    ydl_opts["progress_hooks"] = [hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# =========================================================
# MAIN INTERFACE
# =========================================================
st.title("🐍 PyMedia Downloader")
st.subheader("High-speed video downloads for Python developers")

with st.sidebar:
    st.header("⚙ Setup")
    settings["theme"] = st.selectbox("UI Mode", ["Dark", "Light"])
    settings["default_quality"] = st.selectbox("Preferred Quality", ["1080p HD", "720p", "4K", "Audio MP3"])
    if st.button("💾 Save Settings"):
        save_settings(settings)
        st.success("Config Updated!")

url_input = st.text_input("🔗 Enter Video/Tutorial URL", placeholder="https://...")

if url_input:
    if url_input != st.session_state.last_url:
        st.session_state.video_info = None
        st.session_state.last_url = url_input

    if st.session_state.video_info is None:
        with st.spinner("🔍 Scanning source..."):
            st.session_state.video_info = get_video_info(url_input)

    info = st.session_state.video_info

    if "error" in info:
        st.error(f"Failed to fetch video. Check URL or connection.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(info.get("thumbnail"), use_container_width=True)
        
        with col2:
            st.write(f"### {info.get('title')}")
            st.caption(f"Channel: {info.get('uploader')} | Length: {info.get('duration_string')}")
            
            selected_q = st.selectbox("Quality Choice", ["Best", "1080p HD", "720p", "Audio MP3"])
            
            if st.button("⚡ Start Download"):
                bar = st.progress(0)
                try:
                    file_path = download_video(url_input, selected_q, bar)
                    
                    # File may have changed extension due to merging
                    if not os.path.exists(file_path):
                        # Simple check for converted mp4
                        file_path = file_path.rsplit('.', 1)[0] + ".mp4"

                    with open(file_path, "rb") as f:
                        st.download_button("📂 Save to Computer", f, file_name=os.path.basename(file_path))
                    
                    if settings["auto_cleanup"]:
                        os.remove(file_path)
                except Exception as e:
                    st.error(f"Download Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

# History Section
st.markdown("### 📂 Recent Downloads")
files = sorted(list(DOWNLOAD_DIR.glob("*")), key=os.path.getmtime, reverse=True)
for f in files[:5]:
    st.text(f"✔️ {f.name}")