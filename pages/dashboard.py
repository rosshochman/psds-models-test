import streamlit as st

from navigation import make_sidebar

make_sidebar()

if not st.session_state.get("logged_in", False):
    st.error("Unauthorized. Please log in from the main page.")
    st.stop()

st.title("Protected Dashboard")
st.write("Only users in the configured guild with BT role can view this page.")
