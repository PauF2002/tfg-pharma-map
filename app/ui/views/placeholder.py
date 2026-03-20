import streamlit as st


class PlaceholderView:
    def __init__(self, title: str, text: str):
        self.title = title
        self.text = text

    def render(self) -> None:
        main_html = (
            '<div class="main-wrap">'
            '<div class="main-card">'
            '<div class="main-kicker">PharmaTFG Platform</div>'
            f'<div class="main-title">{self.title}</div>'
            f'<div class="main-text">{self.text}</div>'
            '<div class="placeholder-grid">'
            '<div class="placeholder-box">Module area 1</div>'
            '<div class="placeholder-box">Module area 2</div>'
            '<div class="placeholder-box">Module area 3</div>'
            '<div class="placeholder-box">Module area 4</div>'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(main_html, unsafe_allow_html=True)
