import sys
sys.dont_write_bytecode = True

import streamlit as st
from streamlit_option_menu import option_menu
import about, account, home
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import session

# Now you can import res_fun
#import session

# Set page title
st.set_page_config(page_title='Aurora 🦌: Your Personalized Learning Experience')

# Hide the 'RUNNING' indicator
st.markdown("""
    <style>
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    </style>
            """, unsafe_allow_html=True)


class MultiApp:
    """
    Manage and run multiple applications within the Streamlit sidebar.

    This class allows you to add different applications (functions) to a sidebar menu
    and run the selected application based on user input.

    Attributes
    ----------
    apps : list
        A list of dictionaries, each containing the title and function of an app.

    Methods
    -------
    add_app(title, func):
        Adds a new application to the list of apps.
    run():
        Displays the sidebar menu and runs the selected application.
    """
    def __init__(self):
        """
        Initialize the MultiApp with an empty list of apps.
        """
        self.apps = [] # list to store applications added to the MultiApp

    def add_app(self, title, func):
        """
        Add a new application to the MultiApp.

        Parameters
        ----------
        title : str
            The title of the application to be displayed in the sidebar.
        func : callable
            The function that implements the application logic.

        Returns
        -------
        None
        """
        # Append a dictionary containing the title and function to the apps list
        self.apps.append({'title': title,
                          'function': func})

    def run(self):
        """
        Display the sidebar menu and run the selected application.

        This method creates a sidebar menu using Streamlit's option_menu and
        executes the function associated with the selected application.

        Returns
        -------
        None
        """
        with st.sidebar:
            # Create a sidebar menu with options for different applications
            app = option_menu(menu_title='Aurora',
                              options=['Home', 'Account', 'Chat', 'About'],
                              icons=['house-door', 'person', 'chat-heart', 'info'],
                              menu_icon='stars',
                              default_index=1,
                              styles={"icon": {"font-size": "23px"},
                                      "nav-link": {"font-size": "20px", "text-align": "left", "margin": "0px", "--hover-color": "#D3C2E4"},
                                      "nav-link-selected": {"background-color": "#2CA89D"}, }
                              )

        # Run selected application based on user choice
        if app == 'Home':
            home.app()  # call 'Home' application function
        if app == 'Account':
            account.app()  # call 'Account' application function
        if app == 'Chat':
            session.session()  # call 'Session' application function
        if app == 'About':
            about.app()  # call 'About' application function


# Create an instance of MultiApp
app = MultiApp()
app.run()
