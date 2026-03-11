# BT Role-Gated Streamlit App

A minimal Streamlit app that allows access only to Discord users who:
1. are members of a configured guild, and
2. have the configured BT role.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy env vars:
   ```bash
   cp .env.example .env
   ```
3. Export the variables from `.env` (or your secret manager).
4. Run:
   ```bash
   streamlit run streamlit_app.py
   ```

## Notes
- OAuth scope used: `identify guilds guilds.members.read`
- The sidebar and protected page require `st.session_state['logged_in'] = True`.
