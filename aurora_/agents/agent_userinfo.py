import sys
sys.dont_write_bytecode = True

import warnings
warnings.filterwarnings("ignore")

from pydantic import BaseModel, Field
from typing import Type, Optional
from langchain.schema.runnable.base import Runnable
from langchain.tools import BaseTool
from langchain.output_parsers import PydanticOutputParser
import sqlite3
import re
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")


class PromptTemplate(BaseModel):
    """Defines templates for system and human messages used in a conversation."""

    system_template: str = Field(
        description="Template for the system message in the conversation"
    )
    human_template: str = Field(
        description="Template for the human message in the conversation"
    )


def generate_prompt_templates(
    prompt_template: PromptTemplate
) -> ChatPromptTemplate:
    """Generate a chat prompt template based on given templates and memory setting.

    Args:
        prompt_template: An instance of PromptTemplate containing system and human templates.

    Returns:
        A configured ChatPromptTemplate with specified message structure.
    """

    # Create prompt template without chat history
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                prompt_template.system_template
            ),
            HumanMessagePromptTemplate.from_template(
                prompt_template.human_template
            ),
        ]
    )

    return prompt

########################################CHANGE DATA####################################

class UserChange(BaseModel):
    clients_city:Optional[str]=None 
    clients_name:Optional[str]=None
    clients_username:Optional[str]=None 
    clients_dob:Optional[str]=None 
    clients_password:Optional[str]=None
    clients_email:Optional[str]=None 
    clients_phone:Optional[str]=None 
    clients_gender:Optional[str]=None 
    clients_time:Optional[str]=None 
    clients_mins:Optional[int]=None

    prevcourse_course_gpa:Optional[dict[str, Optional[float]]]=None

    currcourse_course:Optional[list[str]]=None 

    styles_style:Optional[list[str]]=None 
    
    language_languages:Optional[list[str]]=None 
    language_default:Optional[str]=None 

class GetChangeableUserInfoChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to identify the the type of information user wants to change about themselves from the user input
            and what is the new value for that information if user doesn't provide anything value must be None.

            Here is the list of information user can change:
            Their city, their name, their username,  
            their date of birth (date always must be in yyyy-mm-dd format), their password, their email, 
            their gender (it can be either of those: Male, Female, Non-Binary, Prefer Not To Say), 
            their phone number, their preffered studying time (must always be in fromat HH-MM), 
            amount of minutes they want to study per day, languages they speak,
            their preffered language, their learning style (here are valid options: 'Visual', 'Auditory', 'Kinesthetic', 'Reading/Writing',
            'Logical', 'Social', 'Solitary', 'Verbal', 'Musical', 'Naturalistic'), Courses they did,
            GPA in those courses, courses they are doing at the moment

            Here is the user input:
            {customer_input}

            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=UserChange)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
        

class CustomerInput(BaseModel):
    customer_id: int 
    customer_input: str 

class ChangeCustomerInfoTool(BaseTool):
    name: str="ChangeCustomerInfoTool"
    description: str= "Change User's Data in Educational database"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False
    
    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = GetChangeableUserInfoChain(llm).invoke({"customer_input": customer_input})

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
        
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        try:
            #----------------------------------------------CLIENTS_TABLE-------------------------------------------------------------------------
            to_change_clients = ""
            vals_clients = []

            if change_info.clients_city is not None: 
                cities = {c[1].lower(): c[0] for c in eval(db.run("SELECT CityID, CityName from city"))}
                try:
                    key = cities[change_info.clients_city.lower().strip()]
                    to_change_clients += "CityID" + " = ?, "
                    vals_clients.append(key)
                except KeyError:
                    pass

            if change_info.clients_name is not None:
                to_change_clients += "Name" + " = ?, "
                vals_clients.append(change_info.clients_name)

            if change_info.clients_username is not None: 
                usernames = [c[0] for c in eval(db.run("SELECT username from clients"))]
                if ((change_info.clients_username not in usernames) and 
                    (len(re.findall(re.compile("\w+"), change_info.clients_username)) != 0) and 
                    (re.findall(re.compile("\w+"), change_info.clients_username)[0] == change_info.clients_username)):
                    to_change_clients += "Username" + " = ?, "
                    vals_clients.append(change_info.clients_username)

            if (change_info.clients_dob is not None) and (re.findall(re.compile("\d{4}-\d{2}-\d{2}"), change_info.clients_dob.strip())):
                to_change_clients += "DateOfBirth" + " = ?, "
                vals_clients.append(change_info.clients_dob)

            if (change_info.clients_password is not None) and ("'" not in change_info.clients_password) and (len(str(change_info.client_password))>=8):
                to_change_clients += "Password" + " = ?, "
                vals_clients.append(str(change_info.clients_password))

            if change_info.clients_email is not None: 
                emails = [c[0] for c in eval(db.run("SELECT Email from clients"))]
                if ((change_info.clients_email not in emails) and 
                    (len(re.findall(re.compile("[\w\.-]+@[\w\.-]+\.\w+"), change_info.clients_email)) != 0) and 
                    (re.findall(re.compile("[\w\.-]+@[\w\.-]+\.\w+"), change_info.clients_email)[0] == change_info.clients_email)):
                    to_change_clients += "Email" + " = ?, "
                    vals_clients.append(change_info.clients_email)

            if change_info.clients_phone is not None: 
                phones = [c[0].replace("+", "") for c in eval(db.run("SELECT PhoneNumber from clients"))]
                if ((change_info.clients_phone.replace("+", "") not in phones) and 
                    (len(re.findall(re.compile("[+\d]\d+"), change_info.clients_phone)) != 0) and 
                    (re.findall(re.compile("[+\d]\d+"), change_info.clients_phone)[0] == change_info.clients_phone)):
                    to_change_clients += "PhoneNumber" + " = ?, "
                    vals_clients.append(change_info.clients_phone)

            if (change_info.clients_gender is not None) and (change_info.clients_gender.lower() in 
                                                             ["male", "female", "non-ninary", "prefer not to say"]): 
                to_change_clients += "Gender" + " = ?, "
                gender_spelling = {a: b for (a, b) in zip(["male", "female", "non-ninary", "prefer not to say"], 
                                                          ["Male", "Female", "Non-Binary", "Prefer Not To Say"])}
                vals_clients.append(gender_spelling[change_info.clients_gender.lower()])

            if (change_info.clients_time is not None) and (re.findall(re.compile("\d{2}-\d{2}"), 
                                                                     change_info.clients_time)[0] == change_info.clients_time.strip()): 
                to_change_clients += "PreferredTime" + " = ?, "
                vals_clients.append(change_info.clients_time)

            if change_info.clients_mins is not None:
                to_change_clients += "MinPerDay" + " = ?, "
                vals_clients.append(change_info.clients_mins)

            if len(vals_clients) > 0:
                cursor.execute( 
                    f"UPDATE clients SET {to_change_clients[:-2]} WHERE UserID = ?",
                    tuple(list(vals_clients)) + tuple([customer_id])
                )
                
            # ------------------------------------------PREV_COURSES---------------------------------------------------------------------------
            to_change_prevcourse = []
            vals_prevcourse = []
            if change_info.prevcourse_course_gpa is not None:
                for course, gpa in zip(change_info.prevcourse_course_gpa.keys(), change_info.prevcourse_course_gpa.values()):
                    try:
                        c_id = {b.lower(): a for (a, b) in eval(db.run("select CourseID, Name from Course"))}[course.lower()]
                        if c_id in [a[0] for a in eval(db.run(f"SELECT CourseID FROM user_courses WHERE UserID = {customer_id}"))]:
                            cursor.execute(
                                f"DELETE FROM user_courses WHERE CourseID = ? AND UserID = ?",
                                (c_id, customer_id)
                            )

                        if c_id in [a[0] for a in eval(db.run(f"SELECT CourseID FROM previous_courses WHERE UserID = {customer_id}"))]:
                            cursor.execute(
                                f"UPDATE previous_courses SET GPA = ? WHERE UserID = ? AND CourseID = ?",
                                (gpa, customer_id, c_id)
                            )
                        else:
                            cursor.execute(
                                f"INSERT INTO previous_courses (CourseID, UserID, GPA) VALUES (?, ?, ?)",
                                (c_id, customer_id, gpa)
                            )
                        to_change_prevcourse.append(course)
                        vals_prevcourse.append(gpa) 
                    except KeyError:
                        warnings.warn(f"The name of Course ({course}) is not recognised") 
            
            # --------------------------------------CURRENT_COURSES-----------------------------------------------------------------------------

            vals_currcourse = [] 
            if change_info.currcourse_course is not None:
                for course in change_info.currcourse_course:
                    try:
                        c_id = {b.lower(): a for (a, b) in eval(db.run("select CourseID, Name from Course"))}[course.lower()]
                        if c_id in [a[0] for a in eval(db.run(f"SELECT CourseID FROM user_courses WHERE UserID = {customer_id}"))]:
                            warnings.warn(f"The user already enrolled in ({course})")
                        else:
                            cursor.execute(
                                f"INSERT INTO user_courses (CourseID, UserID) VALUES (?, ?)",
                                (c_id, customer_id)
                            )
                            vals_currcourse.append(course)
                    except KeyError:
                        warnings.warn(f"The name of Course ({course}) is not recognised") 
                
            if len(vals_currcourse) == 0:
                to_change_currcourse = []
            else:
                to_change_currcourse = ["new course"]*len(vals_currcourse)
            #-----------------------------------------------------------LEARNING_STYLE----------------------------------------------------------
            vals_styles = []
            if change_info.styles_style is not None:
                for style in change_info.styles_style:
                    try:
                        s_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT LearningID, Name FROM learning_style "))}[style.lower()]
                        if s_id in [a[0] for a in eval(db.run(f"SELECT LearningID FROM user_learning_style WHERE UserID = {customer_id}"))]:
                            pass # letting this slide because it's not too significant
                        else:
                            cursor.execute(
                                f"INSERT INTO user_learning_style (LearningID, UserID) VALUES (?, ?)",
                                (s_id, customer_id)
                            )
                            vals_styles.append(style)
                    except KeyError:
                        warnings.warn(f"The name of learning style ({style}) is not recognised") 
                
            if len(vals_styles) == 0:
                to_change_styles = []
            else:
                to_change_styles = ["new learning style"]*len(vals_styles)
            #-------------------------------------------------------LANGUAGE---------------------------------------------------------------------
            vals_language = []
            if change_info.language_languages is not None:
                for l in change_info.language_languages:
                    try:
                        l_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT LanguageID, Language FROM languages"))}[l]
                        if l_id in [a[0] for a in eval(db.run(f"SELECT LanguageID FROM user_language WHERE UserID = {customer_id}"))]:
                            pass
                        else:
                            cursor.execute(
                                f"INSERT INTO user_language (UserID, LanguageID, PrimaryLanguage) VALUES (?, ?, 0)",
                                (customer_id, l_id)
                            )
                            vals_language.append(l)
                    except KeyError:
                        warnings.warn(f"Language {l} was not recognised")  
                    
            if len(vals_language) == 0:
                to_change_language = []
            else:
                to_change_language = ["new language"] * len(vals_language)

            if change_info.language_default is not None:
                l = change_info.language_default.lower()
                try:
                    l_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT LanguageID, Language FROM languages"))}[l]
                    if l_id in [a[0] for a in eval(db.run(f"SELECT LanguageID FROM user_language WHERE UserID = {customer_id}"))]:
                        cursor.execute(
                            f"UPDATE user_language SET PrimaryLanguage = 0 WHERE UserID = ? AND PrimaryLanguage = 1",
                            (customer_id)
                        )
                        cursor.execute(
                                f"UPDATE user_language SET PrimaryLanguage = 1 WHERE UserID = ? AND LanguageID = ?",
                                (customer_id, l_id)
                            )
                    else:
                        cursor.execute(
                            f"UPDATE user_language SET PrimaryLanguage = 0 WHERE UserID = ? AND PrimaryLanguage = 1",
                            (customer_id)
                        )
                        cursor.execute(
                                f"INSERT INTO user_language (UserID, LanguageID, PrimaryLanguage) VALUES (?, ?, 1)",
                                (customer_id, l_id)
                            )
                    vals_language.append(l)
                    to_change_language.append("new primary language")
                except KeyError:
                        warnings.warn(f"Language {l} was not recognised")
                
            connection.commit()

            to_change = (to_change_clients.split(" = ?, ") + 
                     to_change_prevcourse + 
                     to_change_currcourse + 
                     to_change_styles +
                     to_change_language)
        
            if to_change[0] == "":
                to_change = to_change[1:]

            vals = (vals_clients + 
                    vals_prevcourse + 
                    vals_currcourse + 
                    vals_styles + 
                    vals_language)
        except sqlite3.OperationalError as e:
            print(f"Error: {e}") 
            to_change = ["##UNKNOWN##"]
            vals = ["##UNKNOWN##"]
        finally:
            cursor.close()
            connection.close()

        return f"Succesfully updated following data:\n{[(i, j) for i, j in zip(to_change, vals)]}"
    
################################################READ DATA#########################################

class UserRead(BaseModel):
    clients_city:Optional[bool]=None 
    clients_name:Optional[bool]=None
    clients_username:Optional[bool]=None 
    clients_dob:Optional[bool]=None 
    clients_password:Optional[bool]=None
    clients_email:Optional[bool]=None 
    clients_phone:Optional[bool]=None 
    clients_gender:Optional[bool]=None 
    clients_time:Optional[bool]=None 
    clients_mins:Optional[bool]=None
    clients_streak:Optional[bool]=None

    prevcourse_course_gpa:Optional[bool]=None

    currcourse_course:Optional[bool]=None 

    styles_style:Optional[bool]=None 
    
    language_languages:Optional[bool]=None 
    language_default:Optional[bool]=None 

class ReadUserInfoChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to identify the the type of information user wants to see about themselves in the database
            from the user input.

            For each of those provide True if user is interested to know it and False otherwise.
            City they live in, their Name, their Username, their date ob birth, their password,
            their email, their phone number, their gender, their preffered time for studying,
            the minutes they want to study per day, courses they did or gpa in them, their learning styles,
            languages they speak, and their default language, their study streak as well

            Here is the user input:
            {customer_input}

            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=UserRead)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
        

class ReadCustomerInfoTool(BaseTool):
    name: str="ReadCustomerInfoTool"
    description: str= "Get User's Data in Educational database"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False

    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        total_text = ""
        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = ReadUserInfoChain(llm).invoke({"customer_input": customer_input})

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
        
        if change_info.clients_city:
            total_text += "City: "
            total_text += ", ".join(eval(db.run(f"SELECT CityName, Country FROM city c JOIN clients cs ON c.CityID = cs.CityID WHERE cs.UserID = {customer_id}"))[0])
            total_text += "\n"

        if change_info.clients_streak:
            total_text += "Streak: "
            total_text += str(eval(db.run(f"SELECT Streak FROM clients WHERE UserID = {customer_id}"))[0][0])
            total_text += "\n"

        if change_info.clients_name:
            total_text += "Name: "
            total_text += eval(db.run(f"SELECT Name FROM clients WHERE UserID = {customer_id}"))[0][0]
            total_text += "\n"

        if change_info.clients_username:
            total_text += "UserName: "
            total_text += str(eval(db.run(f"SELECT Username FROM clients WHERE UserID = {customer_id}"))[0][0])
            total_text += "\n"

        if change_info.clients_dob:
            total_text += "Date of birth: "
            total_text += eval(db.run(f"SELECT DateOfBirth FROM clients WHERE UserID = {customer_id}"))[0][0]
            total_text += "\n"

        if change_info.clients_password:
            total_text += "password: "
            total_text += str(eval(db.run(f"SELECT Password FROM clients WHERE UserID = {customer_id}"))[0][0])
            total_text += "\n"

        if change_info.clients_email:
            total_text += "email: "
            total_text += eval(db.run(f"SELECT Email FROM clients WHERE UserID = {customer_id}"))[0][0]
            total_text += "\n"

        if change_info.clients_phone:
            total_text += "phone: "
            total_text += str(eval(db.run(f"SELECT PhoneNumber FROM clients WHERE UserID = {customer_id}"))[0][0])
            total_text += "\n"

        if change_info.clients_gender:
            total_text += "Gender: "
            total_text += eval(db.run(f"SELECT Gender FROM clients WHERE UserID = {customer_id}"))[0][0]
            total_text += "\n"

        if change_info.clients_time:
            total_text += "Preffered study time: "
            total_text += eval(db.run(f"SELECT PreferredTime FROM clients WHERE UserID = {customer_id}"))[0][0]
            total_text += "\n"

        if change_info.clients_mins:
            total_text += "Minutes per day: "
            total_text += str(eval(db.run(f"SELECT MinPerDay FROM clients WHERE UserID = {customer_id}"))[0][0])
            total_text += "\n"   

        if change_info.prevcourse_course_gpa:
            total_text += "Previous Courses Information: "
            for pair in eval(db.run(f"""SELECT co.Name, p.GPA 
                                        FROM course co 
                                        JOIN previous_courses p 
                                        ON co.CourseID = p.CourseID 
                                        JOIN clients c 
                                        ON p.UserID = c.UserID 
                                        WHERE c.UserID = {customer_id}""")):
                total_text += ": ".join((pair[0], str(pair[1])))
                total_text += "; "
            total_text += "\n"
                

        if change_info.currcourse_course:
            total_text += "Current Courses Information: "
            cs = eval(db.run(f"""SELECT co.Name 
                                 FROM course co 
                                 JOIN user_courses p 
                                 ON co.CourseID = p.CourseID 
                                 JOIN clients c 
                                 ON p.UserID = c.UserID 
                                 WHERE c.UserID = {customer_id}"""))
            cs = [a[0] for a in cs]
            total_text += ", ".join(cs)
            total_text += "\n"   

        if change_info.styles_style:
            total_text += "Styles Information: "
            cs = eval(db.run(f"""SELECT co.Name 
                                 FROM learning_style  co 
                                 JOIN user_learning_style  p 
                                 ON co.LearningID = p.LearningID 
                                 JOIN clients c 
                                 ON p.UserID = c.UserID 
                                 WHERE c.UserID = {customer_id}"""))
            cs = [a[0] for a in cs]
            total_text += ", ".join(cs)
            total_text += "\n"      

        if change_info.language_languages:
            total_text += "Languages Information: "
            cs = eval(db.run(f"""SELECT co.language 
                                 FROM languages  co 
                                 JOIN user_language  p 
                                 ON co.LanguageID = p.LanguageID 
                                 JOIN clients c 
                                 ON p.UserID = c.UserID 
                                 WHERE c.UserID = {customer_id}"""))
            cs = [a[0] for a in cs]
            total_text += ", ".join(cs)
            total_text += "\n"         

        if change_info.language_default:
            total_text += "Primary Language: "   
            cs = eval(db.run(f"""SELECT co.language 
                                 FROM languages  co 
                                 JOIN user_language  p 
                                 ON co.LanguageID = p.LanguageID 
                                 JOIN clients c 
                                 ON p.UserID = c.UserID 
                                 WHERE c.UserID = {customer_id} and p.PrimaryLanguage=1"""))[0][0]
            total_text += cs
            total_text += "\n"   

        return "Here is the data I was able to find:\n" + total_text
    
################################################DELETE DATA#########################

class UserDelete(BaseModel):
    languages:Optional[list[str]]=None 
    styles:Optional[list[str]]=None
    curr_courses:Optional[list[str]]=None
    prev_courses:Optional[list[str]]=None

class DeleteUserInfoChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to identify the the type of information user wants to delete about themselves in the database
            from the user input.

            For each of those types of information provide a list with subcategories user wants to delete.
            languages (so for example ['Portugease', 'English']);
            learning styles (so for example ['Auditory', 'Verbal']) (here are also all valid options: 'Visual', 'Auditory', 'Kinesthetic', 'Reading/Writing',
            'Logical', 'Social', 'Solitary', 'Verbal', 'Musical', 'Naturalistic')
            current courses (so for example ['Text Mining', 'Autoimmune diseases treatment'])
            previous courses (for example ['Math Analysis'])

            Here is the user input:
            {customer_input}

            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=UserDelete)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
        
class DeleteCustomerInfoTool(BaseTool):
    name: str="DeleteCustomerInfoTool"
    description: str= "Delete User's Data in Educational database"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False

    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        total_text = ""
        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = DeleteUserInfoChain(llm).invoke({"customer_input": customer_input})

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        deleted_info = ""
        if change_info.languages is not None:
            for lan in change_info.languages:
                try:
                    l_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT LanguageID, Language FROM languages"))}[lan]
                    if not(eval(db.run(f"""SELECT PrimaryLanguage 
                                       FROM user_language 
                                       WHERE LanguageID = {l_id} AND UserID = {customer_id}"""))[0][0] == 1):
                        cursor.execute(
                            "DELETE FROM user_language WHERE UserID = ? and LanguageID = ?",
                            (customer_id, l_id)
                        )
                        deleted_info += f"Language: {lan}; "
                    else:
                        warnings.warn(f"Cannot delete primary language")
                except KeyError:
                    warnings.warn(f"Language {lan} was not recognised")

        if change_info.styles is not None:
            for st in change_info.styles:
                try:
                    st_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT LearningID, Name FROM languages"))}[st]
                    cursor.execute(
                        "DELETE FROM user_language WHERE UserID = ? and LearningID = ?",
                        (customer_id, st_id)
                    )
                    deleted_info += f"Learning style: {st}; "
                except KeyError:
                    warnings.warn(f"Learning style {st} was not recognised")

        if change_info.curr_courses is not None:
            for cc in change_info.curr_courses:
                try:
                    cc_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT CourseID, Name FROM course"))}[cc]
                    cursor.execute(
                        "DELETE FROM user_courses WHERE UserID = ? and CourseID = ?",
                        (customer_id, cc_id)
                    )
                    deleted_info += f"Current course information: {cc}; "
                except KeyError:
                    warnings.warn(f"Course {cc} was not recognised")

        if change_info.prev_courses is not None:
            for pc in change_info.prev_courses:
                try:
                    pc_id = {a[1].lower(): a[0] for a in eval(db.run("SELECT CourseID, Name FROM course"))}[pc]
                    cursor.execute(
                        "DELETE FROM previous_courses WHERE UserID = ? and CourseID = ?",
                        (customer_id, pc_id)
                    )
                    deleted_info += f"Previous course information: {pc}; "
                except KeyError:
                    warnings.warn(f"Course {pc} was not recognised")
        
        return "Succesfully deleted the following information:\n" + deleted_info
    

################################################AGENT######################################

system_message = """
You are now connected to the Educational-commerce database. You can use the following tools to interact with the database:

1. Update information: Update user's information in database.
2. Read information: Get User's information from the database
3. Delete information. Delete User's information from the database

The user_id is 
{customer_id}

If none of the above tools are needed, you can answer the customer in a sweet motherly manner.
If you used any of the tools, still give the output from them in sweet motherly manner.
"""

human_template = """
Customer Query: {customer_input}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(system_message),
        HumanMessagePromptTemplate.from_template(human_template),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

llm = ChatOpenAI(model="gpt-4o-mini")
tools = [ChangeCustomerInfoTool(), ReadCustomerInfoTool(), DeleteCustomerInfoTool()]

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)