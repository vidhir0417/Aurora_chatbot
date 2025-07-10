import sys
sys.dont_write_bytecode = True

import streamlit as st


def app():
    """
    Provide the introduction page of the Aurora chatbot application.

    This function displays an introductory screen for the Aurora chatbot, highlighting its purpose and features aimed at enhancing personalized
    study experiences for students. The page includes visual elements such as the logo, title and detailed descriptions of Aurora's capabilities,
    as well as acknowledgments and links to the authors and the project's GitHub repository.

    Functionality:
    - Displays the application logo.
    - Introduces Aurora and its mission to improve study experiences.
    - Lists key features of Aurora, including unique study methods, file summarization and motivational support.
    - Provides information about the creators and acknowledges contributions from others.
    - Offers links for users to connect via social media and email.

    Returns:
    None
    """
    st.image('website/images/logo_full.png')

    st.title('Introducing Aurora 🦌: ')
    st.subheader('The revolution of personalized study experiences')

    st.markdown("Aurora was founded with the intention of making study experiences better for students. Aurora aids with personalized learning by providing unique ways for students to engage with their study materials. \
                Not everyone learns the same pace; With Aurora, how you study depends on you, and you only.")

    st.divider()

    st.markdown("""
    ### ⚔️ Features

    ➜ **Creating Unique Study Methods** 💫 : With Aurora, your will find the right educational content, create quizzes and flashcards, and help you remember key ideas effortlessly.

    ➜ **Files Summarizations** 📖 : Academic papers can be long and overwhelming, but Aurora simplifies things by summarizing them for you. It picks out the important facts, saving you time and effort.

    ➜ **Motivational Support** 💌 : Aurora analyzes your input and progress to understand when you're struggling and responds with thoughtful support to help you through challenging topics.
                
    _**:blue[NEW ➜]** Now you can also ask Aurora to send emails to the representatives of your Educational Provider! (Currently only available for NOVA IMS and Aurora's Organization)_


    ### 🌌 Let's Get Started, Shall We?
    Please, just log in and explore the sections in the sidebar menu — it's all waiting for you.


    ### 🤝 Creators
    Aurora's streamlit app was designed by [João Capitão](https://www.linkedin.com/in/joao-capitao/), [Maria Rodrigues](https://www.linkedin.com/in/maria-rodrigues2223/), \
    [Nuno Leandro](https://www.linkedin.com/in/nuno-tavares-leandro/), [Vidhi Rajanikante](https://www.linkedin.com/in/vidhi-rajanikante/), [Yehor Malakhov](https://www.linkedin.com/in/yehor-malakhov/).

    ### 📜 Acknowledgemnts:
    A big thank you to [Ashwani132003](https://github.com/Ashwani132003/pondering/tree/main), whose previous work inspired the Aurora Streamlit App, allowing it to reach its full potential.

    ### 👀 Curious?
    To see the full development of this app, check our [GitHub repository](https://github.com/epedri/aurora).

    Reach out to us by [instagram](https://www.instagram.com/aurora_chatbot?igsh=eHVrMjUycXl5NHgz) or via [email](aurora4you.cp@gmail.com).
    """)
    