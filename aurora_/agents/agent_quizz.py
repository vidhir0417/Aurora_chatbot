import sys
sys.dont_write_bytecode = True

import warnings
warnings.filterwarnings("ignore")

from pydantic import BaseModel, Field
from typing import Optional
import json
from langchain.schema.runnable.base import Runnable
from langchain.output_parsers import PydanticOutputParser
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from typing import Type
from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

class PromptTemplate(BaseModel):
    """Defines templates for system and human messages used in a conversation."""

    system_template: str = Field(
        description="Template for the system message in the conversation"
    )
    human_template: str = Field(
        description="Template for the human message in the conversation"
    )

class CustomerInput(BaseModel):
    customer_id: int 
    customer_input: str 

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

###############################################chain_tool_etc##############################################
class Quizz(BaseModel):
    question1:str
    question2:str
    question3:str
    question4:str
    question5:str

    options1:str
    options2:str
    options3:str
    options4:str
    options5:str

    answer1:str
    answer2:str
    answer3:str
    answer4:str
    answer5:str

class QuizzChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to create questions for quizzes based on the text provided. 
            Extract main concepts and create 5 questions of a quiz.
            For each question create 4 options for answer each of them defind by big latin letter (A, B, C or D)
            try to shuffle the correct option so the probability of being either of those letters is the same.
            For each question also given a big latin letter that will be the correct answer.
            Try to keep questions quite short

            Here is the user input:
            {customer_input}

            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=Quizz)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
    
class QuizzCreateTool(BaseTool):
    name: str="QuizzCreateTool"
    description: str= "Creating Quizzes for User"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=True

    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        llm = ChatOpenAI(model="gpt-4o-mini")
        change_info = QuizzChain(llm).invoke({"customer_input": customer_input})

        return change_info
    
class Answer(BaseModel):
    answer:Optional[str]=None

class AnswerChain(Runnable):
    def __init__(self, llm):
        super().__init__()

        self.llm = llm

        prompt_template = PromptTemplate(
            system_template=""" 
            You are a part of the teaching assistant named Aurora. 
            Your task is to understand which answer user chose from the question
            and options provided. you have tu return just single capital letter (A, B, C or D)

            Here is the user input:
            {customer_input}

            {format_instructions}
            """,
            human_template="Customer Query: {customer_input}",
        )

        self.prompt = generate_prompt_templates(prompt_template)
        self.output_parser = PydanticOutputParser(pydantic_object=Answer)
        self.format_instructions = self.output_parser.get_format_instructions()

        self.chain = self.prompt | self.llm | self.output_parser

    def invoke(self, inputs):
        return self.chain.invoke(
            {
                "customer_input": inputs["customer_input"],
                "format_instructions": self.format_instructions
            }
        )
    
class AnswerEvalTool(BaseTool):
    name: str="AnswerEvalTool"
    description: str= "Evaluate Answer of the User in Quizz"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=True

    def _run(
            self,
            customer_id: int,
            customer_input: str, 
    ) -> str:
        try:
            customer_input = json.loads(customer_input)
            llm = ChatOpenAI(model="gpt-4o-mini")
            change_info = QuizzChain(llm).invoke({"customer_input": "QUESTION:" + customer_input["question"] +
                                                                    "OPTIONS:" + customer_input["options"] +
                                                                    "CUSTOMER" + customer_input["customer_input"]})

            if change_info.answer:
                return change_info.answer.upper() == customer_input["answer"].upper()
            return None
        except:
            return None
##################################################AGENT####################################################

system_message = """
You are now able to evaluate people with quizzes. If person wrote a lot of text just pass it to quizz creator right away.
Tools availiable to you are:

1. Create Quizz: To initiate and create quizz.
2. Evaluate answer: check if the answer of user is correct.

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
tools = [QuizzCreateTool(), AnswerEvalTool()]

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)