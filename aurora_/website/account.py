import streamlit as st
from langchain_community.utilities.sql_database import SQLDatabase
import datetime
import re
import sqlite3

# functions to validate the inserted values in registering


def is_valid_email(email):
    '''
    Checks if email syntax provided is valid.

    Parameters:
    - email (str): The email address inserted by the user.

    Returns:
    - bool: True, if email is valid (matches the regex pattern); Otherwise, False.
    '''
    pattern = "[\w\.-]+@[\w\.-]+\.\w+"
    return re.match(pattern, email) is not None


def check_if_email_exists(email, db):
    '''
    Checks if email provided exists in the Database.

    Parameters:
    - email (str): The email address inserted by the user.
    - db (database): Database containing information on users and courses from Aurora.

    Returns:
    - bool: True, if the email exists in the clients table from the Database; otherwise, False.
    '''
    return email in [a[0] for a in eval(db.run("SELECT email FROM clients"))]


def check_if_username_exists(username, db):
    '''
    Checks if username provided exists in the Database.

    Parameters:
    - username (str): The unique username inserted by the user.
    - db (database): Database containing information on users and courses from Aurora.

    Returns:
    - bool: True, if the username exists in the clients table from the Database; otherwise, False.
    '''
    return username in [a[0] for a in eval(db.run("SELECT username FROM clients"))]


def check_if_phone_exists(phone, db):
    '''
    Checks if phone number provided exists in the Database.

    Parameters:
    - phone (str): The unique phone number inserted by the user.
    - db (database): Database containing information on users and courses from Aurora.

    Returns:
    - bool: True, if phone simultaneously exists in the Database (withour country code),
            does not contain any other value besides numbers, and contains the country code; otherwise, False.
    '''
    t1 = phone.replace("+", "") in [a[0].replace("+", "") for a in eval(db.run("SELECT phonenumber FROM clients"))]
    t2 = len(re.findall(re.compile("[+\d]\d+"), phone)) == 0
    t3 = re.findall(re.compile("[+\d]\d+"), phone)[0] != phone
    return t1 and t2 and t3


def verify_user(email, password, db):
    '''
    Checks if user credentials are valid (the password matches the user email from the Database).

    Parameters:
    - email (str): The email address inserted by the user.
    - password (str): The password inserted by the user.
    - db (database): Database containing information on users and courses from Aurora.

    Returns:
    - bool: True, if the password inputted matches the password corresponding to the email in clients table from Database.
    '''
    return password == eval(db.run(f"SELECT password FROM clients WHERE email = '{email}'"))[0][0]


def get_user_details(email, db):
    '''
    Retrieves the user details (user id and username) from the Database, with the provided email correspondent.

    Parameters:
    - email (str): The email address inserted by the user.
    - db (database): Database containing information on users and courses from Aurora.

    Returns:
    - dictionary: dictionary with the user_id and username correspondent to the inputted email.
    '''
    user_id = eval(db.run(f"SELECT UserID FROM clients WHERE email = '{email}'"))[0][0]
    username = eval(db.run(f"SELECT username FROM clients WHERE email = '{email}'"))[0][0]
    return {"user_id": user_id, "username": username}


# Function to handle login
def try_login(email, password, db):
    """
    Authenticates the user with the provided email and password.

    Parameters:
    - email (str): The email address inserted by the user.
    - password (str): The password inserted by the user.

    Returns:
    - bool: True, if login is successful; otherwise, False.
    """
    if not email or not password:
        st.error('Please, fill all fields.')
        return False
    elif not check_if_email_exists(email, db):
        st.error('Email is not registered.')
        return False
    elif not verify_user(email, password, db):
        st.error('Incorrect password. Please, try again.')
        return False
    else:
        st.success('Login successful!')
        user_details = get_user_details(email, db)
        st.session_state.user_id = user_details["user_id"]
        st.session_state.logged_in = True
        st.session_state.username = user_details["username"]
        st.session_state.useremail = email
        st.balloons()
        return True


def log_out():
    '''
    Closes the session, logging out the user from their account.

    Parameters:
    None

    Returns:
    None
    '''
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.useremail = None
    st.info("Succesfully logged out. Until next time :)")


def add_user(name_, email, password, username, date_birth, gender, phone, minuter_per_day, pref_time,
             language, learning_styles, city, prev_course, curr_course, db_path):
    '''
    Adds a user to the Database. 

    Parameters:
    - name_ (str): The name of the user.
    - email (str): The email address of the user.
    - password (str): The password for the user's account.
    - username (str): The username for the user's account.
    - date_birth (str): The date of birth of the user.
    - gender (str): The gender of the user.
    - phone (str): The phone number of the user.
    - minuter_per_day (int): The number of minutes per day the user plans to spend.
    - pref_time (str): The preferred time of day for the user.
    - language (str): The primary language of the user.
    - learning_styles (list): A list of learning styles for the user.
    - city (str): The city where the user resides.
    - prev_course (list): A list of previous courses taken by the user.
    - curr_course (str): The current course the user is enrolled in.
    - db_path (str): The path to the database.

    Returns:
    - bool: True if the user is successfully added to the database, False otherwise.
    '''
    # Connect to the Database
    db = SQLDatabase.from_uri(f'sqlite:///{db_path}')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    city = city.split(",")[0]

    # Try to add new user to the database
    try:
        # Insert user details into client table
        cursor.execute(
            f"INSERT INTO clients (Name, Email, Password, Username, DateOfBirth, Gender, PhoneNumber, MinPerDay, PreferredTime, CityID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name_, email, password, username, date_birth, gender.split("[")[-1].replace("]", ""),
             phone, minuter_per_day,
             pref_time, eval(db.run(f"SELECT CityID From city WHERE CityName = '{city}'"))[0][0]
            ))
        connection.commit()

        id_ = eval(db.run(f"SELECT UserID FROM clients WHERE Email = '{email}'"))[0][0]

        # Set user's primary language to language table
        cursor.execute(
            f"INSERT INTO user_language (UserID, LanguageID, PrimaryLanguage) VALUES (?, ?, 1)",
            (id_, eval(db.run(f"SELECT LanguageID From languages WHERE Language = '{language}'"))[0][0])
        )
        connection.commit()

        # Set preferred learning styles in learning_style table
        for ls in learning_styles:
            cursor.execute(
            f"INSERT INTO user_learning_style (UserID, LearningID) VALUES (?, ?)",
             (id_, eval(db.run(f"SELECT LearningID From learning_style WHERE Name = '{ls}'"))[0][0])
            )
            connection.commit()

        # Add previous courses and respective GPA to previous_courses table
        for pc in prev_course:
            cursor.execute(
            f"INSERT INTO previous_courses (UserID, CourseID, GPA) VALUES (?, ?, 0.0)",
            (id_, eval(db.run(f"SELECT CourseID FROM course WHERE Name = '{pc}'"))[0][0]) 
            )
            connection.commit()

        for cc in curr_course:
            cursor.execute(
            f"INSERT INTO user_courses (UserID, CourseID) VALUES (?, ?)",
            (id_, eval(db.run(f"SELECT CourseID FROM course WHERE Name = '{cc}'"))[0][0])
            )
            connection.commit()
        return True
    except sqlite3.OperationalError as e:
        st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


def app():
    """
    Manages the main application interface for Aurora's learning platform.

    This function handles user authentication, registration and course management through a Streamlit web interface.
    It connects to a SQLite database to store and retrieve user data, course information and learning preferences.

    Parameters:
    None

    Returns:
    None - Updates the Streamlit interface based on user interactions.
    """
    # Connect to Database
    db_path = 'files/aurora.db'
    # Create a SQLDatabase object
    db = SQLDatabase.from_uri(f'sqlite:///{db_path}')
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    available_languages = sorted([a[0] for a in eval(db.run("SELECT language FROM languages"))])
    available_learning_styles = sorted([a[0] for a in eval(db.run("SELECT name FROM learning_style"))])
    available_city = sorted([", ".join(el) for el in eval(db.run("SELECT CityName, Country FROM city"))])
    available_courses = sorted(list(set([el[0] for el in eval(db.run("""SELECT Name FROM course"""))])))

    # Show welcome page if already logged in
    if st.session_state.get('logged_in', False):
        # Sidebar logout button
        with st.sidebar:
            if st.button("Log Out"):
                log_out()

        # "Welcome [name]!" page
        st.image('website/images/logo_full.png')
        st.title(f"Welcome back, {st.session_state.username}! 🫶")
        st.subheader("We're glad to see you again. You were missed dearly.")
        st.subheader("Let's continue our studies, shall we? 🥰")

        st.image('website/images/coquette.png')

        st.write('If you would like to edit the GPA in your previous courses, click "Edit Courses".')

        user_prev_courses = sorted(list(set(el[0] for el in eval(db.run(f'''SELECT cs.Name
                                                FROM (SELECT * FROM clients c WHERE c.UserID = {st.session_state.user_id}) c
                                                JOIN previous_courses u ON c.UserID = u.UserID
                                                JOIN course cs ON u.CourseID = cs.CourseID''')))))

        # User wants to edit their courses
        if st.button('Edit Courses'):
            with st.form('Previous Courses GPA'):
                for pc in user_prev_courses:
                    # Fetch CourseID from the Courses table based on the course name
                    cursor.execute(f"SELECT CourseID FROM course WHERE Name = ?", (pc,))
                    course_id = cursor.fetchone()

                    # For each course in user_prev_courses
                    if course_id:
                        course_id = course_id[0]
                        # Insert the value for course GPA
                        gpa_value = st.number_input(f"Your GPA in {pc}", min_value=0.0, max_value=4.0, format="%0.2f")

                        # Update the GPA value into the previous_courses table
                        cursor.execute(
                            "UPDATE previous_courses SET GPA = ? WHERE UserID = ? AND CourseID = ?",
                            (st.session_state.user_id, course_id, gpa_value))
                        connection.commit()

                st.form_submit_button('Update')

    # Show 'Login/SignUp' option and create the forms
    else:
        st.image('website/images/logo_full.png')
        st.title('Welcome to Aurora :deer:')
        st.header('Login or Sign Up your Account to Get Started!')

        choice = st.selectbox('Login/Signup', ['Login', 'Sign Up'])

        # Initialize session state variables
        if 'username' not in st.session_state:
            st.session_state.username = ''
        if 'useremail' not in st.session_state:
            st.session_state.useremail = ''
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

        if choice == 'Sign Up':
            # Create registration form
            with st.form('registration_form'):
                name_ = st.text_input('Name (First and Last)', key="")
                email = st.text_input('Email Address', key="")
                password = st.text_input('Password', type='password', key="")
                username = st.text_input('Unique Username', key="")
                date_birth = str(st.date_input('Date of Birth', min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today()))
                gender = st.radio('Gender', [':violet[Female]', ':blue[Male]', ':rainbow[Non-Binary]', 'Prefer Not To Say'])
                phone = st.text_input('Phone Number (with Country Code)', key="")
                minuter_per_day = st.number_input('Goal of Minutes to Learn per Day', min_value=5, max_value=1440)
                pref_time = st.time_input('Prefered Time to Study (Start)', value=datetime.time(9, 0))
                pref_time = "-".join(str(pref_time).split(":")[:2])
                st.caption("You can always change your answer when chatting with Aurora, later on.")
                language = st.selectbox('Prefered Learning Language', available_languages)
                learning_styles = st.multiselect('Select your learning styles', available_learning_styles)
                city = st.selectbox('Select your city of residence', available_city)
                prev_course = st.multiselect('Select previous courses you have been enrolled in', available_courses)

                curr_course = st.multiselect('Select courses you currently enrolled in', available_courses)
                st.caption("Don't worry if you course is not yet in our database. We just wait for your educational provider to give us some information on it :3")

                submit = st.form_submit_button('Create Account')

            # Make sure everything is valid
            if submit:
                if (not all([name_, email, password, username,
                             date_birth, gender, phone,
                             minuter_per_day, pref_time, language,
                             learning_styles, city])):
                    st.error('Please, fill all fields.')
                    st.session_state.register_in = False
                elif not is_valid_email(email):
                    st.error('Please, enter a valid email')
                    st.session_state.register_in = False
                elif (len(password) < 8) or ("'" in password):
                    st.error('Password must be at least 8 characters')
                    st.session_state.register_in = False
                elif check_if_email_exists(email, db):
                    st.error('Email already registered.')
                    st.session_state.register_in = False
                elif check_if_username_exists(username, db):
                    st.error('Username already registered.')
                    st.session_state.register_in = False
                elif check_if_phone_exists(phone, db):
                    st.error('Phone number already registered.')
                    st.session_state.register_in = False
                else:
                    if add_user(name_, email, password, username, date_birth, gender, phone, minuter_per_day,
                                pref_time, language, learning_styles, city, prev_course, curr_course, db_path):
                        st.success('Registration Successful!')
                        st.session_state.register_in = True
                        st.balloons()
                        st.info('Please, login to continue.')
                    else:
                        st.error('Registration failed. Please, try again.')
                        st.session_state.register_in = False

        else:
            # Create login form
            with st.form('login_form'):
                email = st.text_input('Email Address', key="")
                password = st.text_input('Password', type='password', key="")

                submit = st.form_submit_button('Login')

                # Make sure values inserted are valid
                if submit:
                    try_login(email, password, db)

        # Show welcome message when logged in
        if st.session_state.logged_in:
            st.toast(f'Welcome, {st.session_state.username}', icon='🥰')
        else:
            st.toast('Please log in to continue.', icon='😌')
