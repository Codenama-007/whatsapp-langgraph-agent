from fastapi import FastAPI , Form
from fastapi.responses import Response
import os 
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage , HumanMessage , AIMessage
from twilio.rest import Client # Whatsapp Client 
from twilio.twiml.messaging_response import MessagingResponse # Replying to the Twilio Servers 

load_dotenv()

# loading the Required Variables for connecting to the twilio servers 
twilio_account_sid = os.environ["TWILIO_ACCOUNT_SID"]
twilio_auth_token = os.environ["TWILIO_AUTH_TOKEN"]

# Passing the System Propmpt for the OLLAMA Model
SYSTEM_PROMPT =  ''' YOU ARE HELPFUL ASSISTANT '''


# Initializing the LLM Model
LLM_MODEL = ChatOllama(model = 'llama3.2:3b')

# Specifications for storing the Chat
conversation_context = {}
conversation_context_limit = 6


def store_chat(number , message , role):
    if number in conversation_context:
        current_chat = conversation_context[number]
        
        if len(current_chat) > 6:
            current_chat.pop(0)
            
        current_chat.append(
            {
                "role" : role ,
                "message" : message
            }
        )
    else:
        conversation_context[number] = [
            {
                "role" : role ,
                "message" : message
            }
        ]    
def get_chat(number):
    return conversation_context[number]

app = FastAPI()

@app.get("/")
def home_route():
    return {
        "Message" : "First End Point"
    }
    
# Post Route for sending the messages to the WhatsAPP AI Agent 
@app.post("/whatsapp")
def whatsapp_response_bot(
    From : str = Form(...) ,
    Body : str = Form(...)
):
    # Extracting the Number and the message from the agent 
    reply_number = From
    message = Body
    
    # Storing the Chat
    store_chat(reply_number , message , "user")
    
    # Converting the stored Messages into the Langchain Messages 
    messages = [
        SystemMessage(
            content = SYSTEM_PROMPT
        )
        
    ]
    for chat in get_chat(reply_number): 
        if chat['role'] == 'user':
            messages.append(HumanMessage(content = chat['content']))
            
        elif chat['role'] == "assistant":
            messages.append(AIMessage(content = chat['content']))
            
            
    response = LLM_MODEL.invoke(
        messages
    )
    ai_message = response.content
    
    # Storing the AI Responses
    store_chat(reply_number , ai_message , "assistant")
    
    # Creating the Whatsapp Reply Bot 
    resp = MessagingResponse()
    resp.message(ai_message)
    
    return Response(
        content = str(resp) ,
        media_type = "application/xml"
    )