import getpass
import os
import random
from dotenv import load_dotenv
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model

from any_chatbot.indexing import embed_and_index_all_docs
from any_chatbot.tools import initialize_retrieve_tool, initialize_sql_toolkit
from any_chatbot.prompts import system_message

load_dotenv()

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"
OUTPUTS = BASE / "outputs"
DATABASE = DATA / "csv_excel_to_db" / "my_data.duckdb"

# INDEXING
embeddings, vector_store = embed_and_index_all_docs(DATA, DATABASE)

# BUILD LLM
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")
llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

# LOAD TOOLS
retrieve_tool = initialize_retrieve_tool(vector_store)
sql_tools = initialize_sql_toolkit(llm, DATABASE)

# BUILD AGENT
# build checkpointer
memory = MemorySaver()
# build agent
agent_executor = create_react_agent(
    llm, [retrieve_tool, *sql_tools], prompt=system_message, checkpointer=memory
)
# save architecture graph image
png_bytes = agent_executor.get_graph().draw_mermaid_png()
# save to file
with open(OUTPUTS / "graph.png", "wb") as f:
    f.write(png_bytes)
print("Created graph.png")

# PROMPT
# specify an ID for the thread
# config = {"configurable": {"thread_id": "abc123"}}
config = {"configurable": {"thread_id": random.random()}}

# input_message = (
#     "What is the content of the image?\n\n"
#     "When you don't know while files the user is talking about, use the functional call to retrieve what data is available with a general prompt.\n\n"
#     "Base your answers only on the retrieved information thorugh the functional call you have. You can retreive MULTIPLE TIMES"
# )

input_message = (
    "What kinds (images, text docs, or excel sheets) are available in the documents I have provided to you? Use the functional call to retrieve information for each type first.\n\n"
    # "What colums does the excel have? once you found the answer, tell me there types too.\n\n"
    # "Once you have that answer, I want you to calculate the median for each column.\n\n"
    "When you don't know while files the user is talking about, use the functional call to retrieve what data is available with a general prompt.\n\n"
    "You can refine your semantic search queries and try multiple times with different queries until you resonably determine the data is not available on the given documents.\n\n"
    "Base your answers only on the retrieved information thorugh the functional call you have. You can retreive MULTIPLE TIMES"
)

for event in agent_executor.stream(
    {"messages": [{"role": "user", "content": input_message}]},
    stream_mode="values",
    config=config,
):
    event["messages"][-1].pretty_print()
