import sys
sys.dont_write_bytecode = True

from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.schema.runnable.base import Runnable
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from res_fun import get_completion_from_messages, send_it
#from operator import itemgetter
from langchain_openai import OpenAIEmbeddings
from pinecone import Index, Pinecone
from typing import Type, Optional
from langchain.tools import BaseTool
from dotenv import load_dotenv
import random
from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# -------------------------------------PREPARE------------------------------------------------------------------------------------
load_dotenv()


class PromptTemplate_(BaseModel):
    """Defines templates for system and human messages used in a conversation."""

    system_template: str = Field(
        description="Template for the system message in the conversation"
    )
    human_template: str = Field(
        description="Template for the human message in the conversation"
    )


def generate_prompt_templates(
    prompt_template: PromptTemplate_
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

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
pc = Pinecone()
index: Index = pc.Index("total")
vector_store = PineconeVectorStore(
    index=index, embedding=embeddings_model
)

def format_docs(documents):
    return f"{documents[0].metadata}" + "\n\n".join(doc.page_content for doc in documents if doc.metadata["file_path"] == documents[0].metadata["file_path"])

retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 10, "score_threshold": 0.5},
)

#-------------------------------------------------------PINE---------------------------------------------------------------------
llm = ChatOpenAI(model="gpt-4o-mini")


template = """Use the following pieces of context to provide full and complete
              overview to question user. don't add anything from yourself only use 
              the provided context. at the end you must provide user with information of where the information
              comes from either based on the metadata at the start or important information with
              context itself or a combination of both.
              you must speak is tender soft motherly tone.

{context}

Question: {question}
"""

custom_rag_prompt = PromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | custom_rag_prompt
    | llm
    | StrOutputParser()
)
#----------------------------------------------TOOL-PINE-----------------------------
class CustomerInput(BaseModel):
    customer_id: int 
    customer_input: str 


class PineconeResourceTool(BaseTool):
    name: str="PineconeResourceTool"
    description: str= "Get information from scientific papers"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False
    
    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        return rag_chain.invoke(customer_input)

#-------------------------------------------------------SQL---------------------------------------------------------------------------
class UserReadCourse(BaseModel):
    course_syllabus:Optional[bool]=None 
    course_lo:Optional[bool]=None 
    course_lu:Optional[bool]=None 
    course_eval:Optional[bool]=None 
    course_credits:Optional[bool]=None 
    city:Optional[str]=None
    tipo:Optional[str]=None
    topic:Optional[list[Optional[str]]]=None

class UserReadCourseInfoChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

        prompt_template = PromptTemplate_(
            system_template=f""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to identify the the type of information user wants to see about a given course
            from the user input.

            For each of those provide True if user is interested to know it and False otherwise.
            The syllabus of the course, the learning objectives, learning units, the evaluation
            methods, the amount of credits.

            Also you have to identify city in which they want to study and weather the curse has to be online or InPerson (spell exactly like this)

            And list of topics that related to their search that can be either of those {[a[0] for a in eval(db.run("SELECT Name FROM topic"))]}

            Here is the user input:
            {{customer_input}}

            {{format_instructions}}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=UserReadCourse)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
    

#--------------------------------TOOL----------------------

class ReadCourseInfoTool(BaseTool):
    name: str="ReadCourseInfoTool"
    description: str= "Get information on courses, educational providers, universities"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False

    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = UserReadCourseInfoChain(llm).invoke({"customer_input": customer_input})

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

        if change_info.city:
            user_city = change_info.city
        else:
            user_city = eval(db.run(f"SELECT CityID FROM clients WHERE UserID = {customer_id}"))[0][0]

        select_base = "c.Name, CityName, Country, e.Name, e.Type"
        if change_info.course_syllabus:
            select_base += ", c.Syllabus" 
        if change_info.course_lo:
            select_base += ", c.LearningObjectives"
        if change_info.course_lu:
            select_base += ", c.LearningUnits"
        if change_info.course_eval:
            select_base += ", c.evaluation"
        if change_info.course_credits:
            select_base += ", c.credits"
        
        try:
            search = eval(db.run(f""" SELECT {select_base}
                                    FROM course c
                                    JOIN course_location cl 
                                    ON c.CourseID = cl.CourseID
                                    JOIN educational_provider e 
                                    ON e.ProviderID = cl.ProviderID
                                    JOIN city 
                                    ON e.CityID = city.CityID
                                    JOIN course_topic ct
                                    ON c.CourseID = ct.CourseID
                                    JOIN topic
                                    ON topic.TopicID = ct.TopicID
                                    WHERE city.CityID = '{user_city}' AND e.Type = '{change_info.tipo}'
                                    AND topic.Name in {str(change_info.topic).replace("[", "(").replace("]", ")")};
                                    """)) 

        except SyntaxError:
            search = None

        return "Here is the courses in users area I was able to find:\n" + str(search)

#------------------------------------------------------EMAIL---------------------------------------
class Recievers(BaseModel):
    joao:bool
    maria:bool
    nuno:bool
    tiago:bool
    vidhi:bool
    yehor:bool

class EmailChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate_(
            system_template=f""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to identify people that user want to send email to.

            For each of those provide True if user is interested to to talk to them and False otherwise.
            Here is the list of possible people user can interact with:

            João Capitão: CEO of Aurora assistant mother company. Any business questions have to be discussed with him.
            Maria Rodrigues: Marketing Manager of Aurora assistant mother company. Any questions related to social media or motenization of Aurora have to be discussed with her.
            Nuno Leandro: Human Resourses Manager of Aurora assistant mother company. Any questions related to working in Aurora or Aurora's staff must be discussed with him.
            Tiago Moço dos Santos: Nova University Information Managment School Representative. Any questions regarding this university must be dicussed him.
            Vidhi Rajanikante: Product Manager of Aurora assistant mother company. Any questions regarding Aurora's strategy must be discussed with her.
            Yehor Malakhov: Head of coding department of Aurora assistant mother company. Any questions related Aurora base implementation must be discussed with him.

            Here is the user input:
            {{customer_input}}

            {{format_instructions}}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=Recievers)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
    
# --------------------------TOOl-----------------------------
class EmailTool(BaseTool):
    name: str="EmailTool"
    description: str= "Send emails to Educational Providers or Aurora stuff"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False

    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        
        people_info = {"João Capitão": "CEO of Aurora assistant mother company. Any business questions have to be discussed with him.",
                       "Maria Rodrigues": "Marketing Manager of Aurora assistant mother company. Any questions related to social media or motenization of Aurora have to be discussed with her.",
                       "Nuno Leandro": "Human Resourses Manager of Aurora assistant mother company. Any questions related to working in Aurora or Aurora's staff must be discussed with him.",
                       "Tiago Moço dos Santos": "Nova University Information Managment School Representative. Any questions regarding this university must be dicussed him.",
                       "Vidhi Rajanikante": "Product Manager of Aurora assistant mother company. Any questions regarding Aurora's strategy must be discussed with her.",
                       "Yehor Malakhov": "Head of coding department of Aurora assistant mother company. Any questions related Aurora base implementation must be discussed with him."}
        
        emails = {person: em for (person, em) in zip(people_info.keys(), ["20221863@novaims.unl.pt",
                                                                          "20221938@novaims.unl.pt",
                                                                          "20221861@novaims.unl.pt",
                                                                          "tmsantos@novaims.unl.pt",
                                                                          "20221982@novaims.unl.pt",
                                                                          "20221691@novaims.unl.pt",
                                                                          ])}

        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = EmailChain(llm).invoke({"customer_input": customer_input})

        options = {person: em for (person, em) in zip(people_info.keys(), [change_info.joao,
                                                                          change_info.maria,
                                                                          change_info.nuno,
                                                                          change_info.tiago,
                                                                          change_info.vidhi,
                                                                          change_info.yehor])}

        db_path = "files/aurora.db"
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

        personal_info = db.run(f"""SELECT Name, Gender, Email
                                   FROM clients 
                                   WHERE UserID = {customer_id}""")
        
        languages = [a[0] for a in eval(db.run(f"""SELECT l.Language 
                                   FROM clients c
                                   JOIN user_language ul 
                                   ON c.UserID = ul.UserID 
                                   JOIN languages l 
                                   ON ul.LanguageID = l.LanguageID
                                   WHERE c.UserID={customer_id}"""))]
        
        courses = eval(db.run(f"""SELECT cc.Name, cc.Syllabus, pc.GPA
                                   FROM clients c
                                   JOIN previous_courses pc
                                   ON pc.USERID = c.UserID
                                   JOIN Course cc 
                                   ON cc.CourseID = pc.CourseID
                                   WHERE c.UserID={customer_id}"""))
        
        sent=[]
        for name in people_info.keys():
            if options[name]:
                system_message = f"""Your task is to write a text of respectful email based on last promt of user. 
                                    Email must be alike cover letter for a user
                                    to a given person. Be very respectful and promote user in best way possible. Your name
                                    is Aurora and you're a Teahing Assistant ChatBot. 
                                    
                                    Here's Name, Gender, Email of user: {personal_info}. You must mention email at least once so the reciever will
                                    be able to contact the user.
                                    Here's their personal expirience meaning a list of courses, their syllabus' and GPA's they got in it: {courses}
                                    And here are the languages user proficient in: {languages}

                                    You writing to a person named {name} their position is {people_info[name]}
                                    """ 
                
                messages = [{"role": "system", "content": system_message},
                            {"role": "user", "content": customer_input}]
                response = get_completion_from_messages(messages, temperature=0.4)   
                yas = send_it(reciever=emails[name], caption="NEW AURORA BOT SUGGESTION", text=response)
                if yas:
                    sent.append(name)

        return f"Sent emails to {sent}"


#------------------------------------------------AGENT-----------------------------------------------------------------------------------


system_message = """
You are now connected to the Educational database. You can use the following tools to interact with the databases and email:

1. Import Resourse. You can reatrieve information on various topics from scientific papers in our Database
2. Course search. You can find information on educational providers like universitites for the User.
3. Send Emails. You can send cover letters to educational providers or related to Aurora staff mentioned by this User.

The user_id is 
{customer_id}

You can only provide information from these tools
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
tools = [PineconeResourceTool(), 
         ReadCourseInfoTool(), 
         EmailTool()
         ]

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)