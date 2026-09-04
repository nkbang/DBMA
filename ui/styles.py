import streamlit as st


def render_styles():
    st.markdown(
        """
        <style>
        .stButton button { border-radius: 8px; }

        /* DESIGN.md §Elevation: Tonal Layering and Fine Outlines */
        /* All cards, panels, and containers use 1px solid border (#E5E1D8) */
        .stCard,
        [data-testid="stVerticalBlock"] > div > div {
            border: 1px solid #E5E1D8 !important;
            border-radius: 8px !important;
        }

        /* Streamlit expander border consistency */
        .streamlit-expanderHeader {
            border: 1px solid #E5E1D8 !important;
            border-radius: 8px !important;
        }

        /* Streamlit text input border */
        .stTextInput > div > div > input {
            border: 1px solid #E5E1D8 !important;
            border-radius: 8px !important;
        }

        /* Streamlit selectbox border */
        .stSelectbox > div > div > input {
            border: 1px solid #E5E1D8 !important;
            border-radius: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
