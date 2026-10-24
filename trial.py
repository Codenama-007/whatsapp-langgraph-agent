# # Download the helper library from https://www.twilio.com/docs/python/install
# import os
# from twilio.rest import Client
# from dotenv import load_dotenv

# load_dotenv()

# # Find your Account SID and Auth Token at twilio.com/console
# # and set the environment variables. See http://twil.io/secure
# account_sid = os.environ["TWILIO_ACCOUNT_SID"]
# auth_token = os.environ["TWILIO_AUTH_TOKEN"]
# client = Client(account_sid, auth_token)

# message = client.messages.create(
#     from_="whatsapp:+14155238886",   # your sandbox number from the console
#     to="whatsapp:+917820986147",     # your phone, in international format
#     body="Hello from Twilio!"
#     # content_sid="HXfe5ab5f00277942d4d4200328b4d403c",
# )

# print(message.sid)

import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

message = client.messages.create(
    from_="whatsapp:+14155238886",   # your sandbox number, exactly as shown in the console
    to="whatsapp:+917820986147",     # your phone
    body="Hello from my bot!",
)
print("Sent:", message.sid, message.status)