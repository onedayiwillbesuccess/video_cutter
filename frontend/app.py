import time
import requests
import streamlit as st

API_URL = "http://10.10.2.64:8000"

st.set_page_config(page_title="The Clip Snipper", page_icon="✂️", layout="wide")

st.markdown("""
<style>
    .stApp { max-width: 900px; margin: auto; }
    .clip-card {
        background: #1e1e2e; border-radius: 12px; padding: 20px;
        margin: 10px 0; border: 1px solid #333;
    }
    .clip-title { font-size: 1.2em; font-weight: bold; color: #fff; }
    .clip-meta { color: #888; font-size: 0.9em; margin-top: 5px; }
    h1 { text-align: center; }
    .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
</style>
""", unsafe_allow_html=True)

st.title("✂️ The Clip Snipper")
st.markdown('<p class="subtitle">Automatically turn YouTube videos into viral vertical clips</p>', unsafe_allow_html=True)

if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "clips" not in st.session_state:
    st.session_state.clips = None

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
    )
with col2:
    submit = st.button("✂️ Snip It!", type="primary", use_container_width=True)

if submit and url:
    try:
        resp = requests.post(f"{API_URL}/api/submit", json={"url": url}, timeout=10)
        resp.raise_for_status()
        st.session_state.job_id = resp.json()["job_id"]
        st.session_state.clips = None
        st.rerun()
    except requests.ConnectionError:
        st.error("Cannot connect to backend. Make sure the API server is running on port 8000.")
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.job_id:
    job_id = st.session_state.job_id

    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = {
        "starting": ("Starting...", 0.05),
        "downloading_audio": ("Downloading audio...", 0.10),
        "transcribing": ("Transcribing with Whisper...", 0.30),
        "selecting_clips": ("AI selecting viral clips...", 0.50),
        "downloading_video": ("Downloading full video...", 0.65),
        "editing": ("Cutting and processing clips...", 0.75),
        "done": ("Complete!", 1.0),
        "error": ("Error occurred", 0),
    }

    while True:
        try:
            resp = requests.get(f"{API_URL}/api/status/{job_id}", timeout=5)
            status = resp.json()
        except Exception:
            st.error("Lost connection to backend.")
            break

        step = status.get("step", "starting")
        message = status.get("message", "Working...")
        step_label, default_progress = steps.get(step, ("Working...", 0.5))

        progress_bar.progress(default_progress)
        status_text.info(f"**{step_label}** — {message}")

        if status["status"] == "completed":
            progress_bar.progress(1.0)
            status_text.success(f"✅ {status['message']}")
            st.session_state.clips = status.get("clips", [])
            break
        elif status["status"] == "failed":
            progress_bar.progress(0)
            status_text.error(f"❌ {status['message']}")
            break

        time.sleep(2)

if st.session_state.clips:
    clips = st.session_state.clips
    job_id = st.session_state.job_id

    st.divider()
    st.subheader(f"🎉 {len(clips)} Clips Ready!")

    for i, clip in enumerate(clips):
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{clip['title']}**")
                st.caption(f"{clip['start_time']:.1f}s — {clip['end_time']:.1f}s  |  {clip['end_time'] - clip['start_time']:.1f}s")
            with c2:
                download_url = f"{API_URL}/api/download/{job_id}/clip_{i + 1}.mp4"
                st.link_button("⬇️ Download", download_url, type="secondary")
            st.video(f"{API_URL}/api/download/{job_id}/clip_{i + 1}.mp4")
            st.divider()
