from pathlib import Path
from time import sleep

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


def get_current_page_name() -> str:
    ctx = get_script_run_ctx()
    if ctx is None:
        raise RuntimeError("Couldn't get script context")
    return Path(ctx.main_script_path).stem


def logout() -> None:
    st.session_state.logged_in = False
    st.info("Logged out successfully!")
    sleep(0.5)
    st.rerun()


def make_sidebar() -> None:
    with st.sidebar:
        st.title("BT Access Portal")
        if "username" in st.session_state:
            st.write(f"Logged in as **{st.session_state['username']}**")

        if st.session_state.get("logged_in", False):
            st.page_link("streamlit_app.py", label="Home")
            st.page_link("pages/dashboard.py", label="Protected Dashboard")

            if st.button("Log out"):
                logout()
        elif get_current_page_name() != "streamlit_app":
            st.warning("Please log in from the main page.")
            st.page_link("streamlit_app.py", label="Go to Login")
