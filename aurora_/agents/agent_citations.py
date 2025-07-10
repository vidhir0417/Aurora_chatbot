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

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
pc = Pinecone()
index: Index = pc.Index("total")
vector_store = PineconeVectorStore(
    index=index, embedding=embeddings_model
)

def format_docs(documents):
    return "\n\n".join(str(doc.metadata) + doc.page_content for doc in documents)

retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 10, "score_threshold": 0.65},
)

#----------------------------------------------PINE---------------------------

llm = ChatOpenAI(model="gpt-4o-mini")


template = """Use the following pieces of context to give user scientific citations 
              for the paper user created. Be very specific on everything in your citations.
              You don't provide a citation of their paper, you provide citation they can use in their paper
              All citation follow next structure you can't add anything but you can
              say that extra information is missing: Thomas, H. K. (2004). Training strategies for improving listeners' comprehension of foreign-accented speech (Doctoral dissertation). University of Colorado, Boulder.
              Don't provide any links.
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


class PineconeCitationTool(BaseTool):
    name: str="PineconeCitationTool"
    description: str= "Get citation from scientific papers"
    args_schema: Type[BaseModel] = CustomerInput
    return_direct: bool=False
    
    def _run(
            self,
            customer_id: int,
            customer_input: str,
    ) -> str:
        return rag_chain.invoke(customer_input)
    

#------------------------------------------------AGENT-----------------------------------------------------------------------------------


system_message = """
You are now connected to the Educational database. You can use the following tools to interact with the databases:

1. Citation. You can retrieve information on various topics from scientific papers and provide them as citation to user.

The user_id is 
{customer_id}

You can only provide information from these tools
Don't say repetitions.
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
tools = [PineconeCitationTool()]

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
