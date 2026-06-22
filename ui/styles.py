import streamlit as st


def render_styles():
    st.markdown(
        """
        <style>
        .stButton button { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
