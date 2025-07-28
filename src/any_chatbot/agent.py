import getpass
import os
from dotenv import load_dotenv
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model

from any_chatbot.indexing import index_text_docs
from any_chatbot.tools import initialize_retrieve_tool

load_dotenv()

BASE = Path(__file__).parent.parent.parent
DATA = BASE / "data"
OUTPUTS = BASE / "outputs"

# INDEXING
embeddings, vector_store = index_text_docs(DATA)

# BUILD LLM
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")
llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

# LOAD TOOLS
retrieve_tool = initialize_retrieve_tool(vector_store)

# BUILD AGENT
# build checkpointer
memory = MemorySaver()
# build agent
agent_executor = create_react_agent(llm, [retrieve_tool], checkpointer=memory)
# save architecture graph image
png_bytes = agent_executor.get_graph().draw_mermaid_png()
# save to file
with open(OUTPUTS / "graph.png", "wb") as f:
    f.write(png_bytes)
print("Wrote graph.png")

# PROMPT
# specify an ID for the thread
import random
# config = {"configurable": {"thread_id": "abc123"}}
config = {"configurable": {"thread_id": random.random()}}

input_message = (
    "First retrieve what the revenue for Nike in 2023 was using the functional call.\n\n"
    "Once you get the answer, do a second retrieve to tell me which distribution centers nike have.\n\n"
    "Once you get the second answer,, tell me how many employees nike has. You can retreive MULTIPLE TIMES\n\n"
    "Base your answers only on the retrieved information thorugh the functional call you have."
)

for event in agent_executor.stream(
    {"messages": [{"role": "user", "content": input_message}]},
    stream_mode="values",
    config=config,
):
    event["messages"][-1].pretty_print()

