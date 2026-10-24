from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import SystemMessage, trim_messages
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

SYSTEM_PROMPT = (
    "You are a helpful assistant replying over WhatsApp. "
    "Keep answers short and clear, in plain text (no markdown tables)."
)

# Keep the last N messages as context (matches your old limit of 6)
HISTORY_LIMIT = 6

llm = ChatOllama(model="llama3.2:3b")


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot_node(state: State):
    history = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len,      # count messages, not tokens
        max_tokens=HISTORY_LIMIT,
        start_on="human",
    )
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT)] + history)
    return {"messages": [response]}


workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot_node)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)

# In-memory: conversations reset when the server restarts
memory = MemorySaver()
compiled_graph = workflow.compile(checkpointer=memory)


def get_agent_response(user_message: str, thread_id: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = compiled_graph.invoke({"messages": [("user", user_message)]}, config)
    return result["messages"][-1].content