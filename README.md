# BT Role-Gated Streamlit App

A minimal Streamlit app that allows access only to Discord users who:
1. are members of a configured guild, and
2. have the configured BT role.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create `.streamlit/secrets.toml` with your Discord configuration:
   ```toml
   CLIENT_ID = "..."
   CLIENT_SECRET = "..."
   REDIRECT_URI = "http://localhost:8501"
   GUILD_ID = "..."
   BT_ROLE_ID = "1011304196999487532" # optional override
   PSDS_ELITE_LOGGING_WEBHOOK = "..."   # optional
   ```
3. Run:
   ```bash
   streamlit run streamlit_app.py
   ```

## Notes
- OAuth scope used: `identify guilds guilds.members.read`
- The sidebar and protected page require `st.session_state['logged_in'] = True`.
- Built-in Streamlit page navigation is hidden via `.streamlit/config.toml`; use the custom sidebar links rendered by `navigation.py`.
