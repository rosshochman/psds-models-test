import os
from time import sleep
from urllib.parse import urlencode

import requests
import streamlit as st

from navigation import make_sidebar

st.set_page_config(layout="wide", page_title="BT Access Portal")

# Discord OAuth2 credentials
CLIENT_ID = os.getenv("client_id")
CLIENT_SECRET = os.getenv("client_secret")
REDIRECT_URI = os.getenv("redirect_uri")

# Optional logging webhook
LOGGING_WEBHOOK = os.getenv("psds_elite_logging_webhook")

# Discord guild and role requirements
GUILD_ID = os.getenv("guild_id")
BT_ROLE_ID = os.getenv("bt_role_id", "1011304196999487532")


def generate_discord_login_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds guilds.members.read",
    }
    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    response = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    return response.json()


def fetch_user_guilds(token: str) -> list:
    response = requests.get(
        "https://discord.com/api/users/@me/guilds",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    return response.json()


def fetch_user_info(token: str) -> dict:
    response = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    return response.json()


def fetch_user_roles_in_guild(token: str) -> list[str]:
    response = requests.get(
        f"https://discord.com/api/users/@me/guilds/{GUILD_ID}/member",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if response.status_code == 200:
        return response.json().get("roles", [])
    return []


def is_user_in_guild(guilds: list) -> bool:
    return any(guild.get("id") == GUILD_ID for guild in guilds)


def validate_required_config() -> bool:
    missing = [
        key
        for key, value in {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "guild_id": GUILD_ID,
        }.items()
        if not value
    ]

    if missing:
        st.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    return True


# OAuth callback code capture
query_params = st.query_params
if "code" in query_params and "access_token" not in st.session_state:
    token_data = exchange_code_for_token(query_params["code"])
    if "access_token" in token_data:
        st.session_state["access_token"] = token_data["access_token"]
        st.query_params.clear()


if "access_token" in st.session_state and "logged_in" not in st.session_state:
    st.write("Checking your Discord guild membership and BT role...")
    token = st.session_state["access_token"]

    guilds = fetch_user_guilds(token)
    user_info = fetch_user_info(token)
    roles = fetch_user_roles_in_guild(token)

    st.session_state["username"] = user_info.get("username", "Unknown")

    if not is_user_in_guild(guilds):
        st.error("Access denied: you are not in the required Discord guild.")
        st.session_state["logged_in"] = False
        st.stop()

    if BT_ROLE_ID not in roles:
        st.error("Access denied: BT role is required.")
        st.session_state["logged_in"] = False
        st.stop()

    st.session_state["logged_in"] = True
    st.success(f"Welcome, {st.session_state['username']}! BT role verified.")

    if LOGGING_WEBHOOK:
        try:
            requests.post(
                LOGGING_WEBHOOK,
                json={"content": f"**{st.session_state['username']}** has logged in."},
                timeout=10,
            )
        except Exception:
            pass
    sleep(1)


make_sidebar()


st.title("BT Member Access")
st.write("This app is restricted to users in the configured Discord guild with the BT role.")

if not validate_required_config():
    st.stop()

if not st.session_state.get("logged_in", False):
    st.write("Click below to authenticate with Discord.")
    if st.button("Login with Discord"):
        st.markdown(f"[Click here to authenticate with Discord]({generate_discord_login_url()})")
else:
    st.info("You are logged in and can access protected pages from the sidebar.")
