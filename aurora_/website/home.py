import sys
sys.dont_write_bytecode = True

import streamlit as st


def app():
    """
    Provide the home page of the Aurora chatbot application.

    This function displays the welcome screen for the user, introducing Aurora as a chatbot designed to assist with studies.
    It includes visual elements such as the logo, title and various sections that outline the capabilities of the chatbot.
    It also provides links for users to explore more about Aurora's features and access the full website.

    Functionality:
    - Displays the application logo.
    - Welcomes the user with a friendly message.
    - Lists the key features of the chatbot, including customized learning, progress tracking and motivational support.
    - Provides a link to Aurora's full website for more information.

    Returns:
    None
    """
    st.image('website/images/logo_full.png')

    st.title('Welcome Home, my dear 🫂')

    st.header('I am Aurora, your Chatbot 🦌')
    st.write('Make yourself comfortable, dear. Let’s dive into our studies, shall we? Tell me, how can I help you?')

    st.divider()

    st.subheader("How can Aurora help you reach your full potential?")
    st.write(" ➜ Customized Learning Experience 🎯📚", unsafe_allow_html=True)
    st.write(" ➜ Real-time Progress Tracking 📊🕒", unsafe_allow_html=True)
    st.write(" ➜ Motivational Support 🌟❤️", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("To learn more on Aurora's capabilities, explore Aurora's streamlit app and website!🥰")

    st.markdown("<br>", unsafe_allow_html=True)

    st.caption("\nAurora's full website can be found [here](https://aurora4youcp.wixsite.com/aurora).")
