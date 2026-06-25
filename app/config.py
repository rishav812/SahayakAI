import os
from dotenv import load_dotenv
from app.tools import get_fee
from langchain_openai import ChatOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
llm_with_tools = llm.bind_tools([get_fee])
