
examples = '''
1. Boss, what is your trailer no. and ETA for tom pick 0300?
2. Good morning Jorge. Can we please have your current location, ETA, and trailer number for pickup?
3. Marttha whats your current location and ETA to delivery?
4. Brother, what is your ETA for the 2130 pick and trailer no. pls, thanks
5. May we know your ETA to Grand Prairie?
6. In the meantime, could you please provide what is your current location and ETA?
7. In the meantime, please provide your current location and ETA. Thanks.
8. Hi Boss, please let us know your current location and ETA for delivery. Thank you
9. Hi Ermias, good morning! May we know your ETA to the shipper in Miami, FL for load 21501? This is Forefront Global. Thank you.
10. Brother, what is your ETA for the 2130 pick and trailer no. pls, thanks
11. may we know your ETA to Grand Prairie?
12. Hi Ermias, good morning! May we know your ETA to the shipper in Miami, FL for load 21501? This is Forefront Global. Thank you.
13. Hi Mukhmud, good morning! May we know your ETA to the shipper in Lakeville, MN for load 21295? This is Forefront Global. Thank you.

'''



GREET_PROMPT = f"""
You are a friendly and professional support dispatcher for a trucking company.
Ask the trucker for their current location and estimated time of arrival in a human like broker message.
Example tones of the response message:
{examples}

Be casual but respectful. Keep it short and clear.
"""


EXTRACT_LOCATION_AND_ETA_PROMPT = """
You are given a human response and you need to extract the location and eta if there are any and give it in json format.
Human response: {human_response}
current Time: {current_time}
{format_instructions}
    
outputs:
1) location: string
2) eta: timestamp (do not use the current time)


Note: 
- Do not add note or anything else.
- If the location is not provided in human response, return as null.
- If the eta is not provided in human response, return as null.

"""


GET_LOCATION_OR_ETA_PROMPT = """
Respond to the truck driver message. 
Also, The location provided by the driver is {location} and the eta provided by the driver is {eta}. 
if one or both are None, please generate a question to ask the driver for it and make it short and direct. 
whithout saying hello or anything else
Example tones of the response message:
{examples}

Be casual but respectful. Keep it short and clear.

"""
DELAY_REASON_PROMPT = """
The truck driver has been delayed by {delay}.
Please ask the driver for the reason why they are delayed.
Example tones of the response message:
1. You have been delayed by ten minutes. Can you tell the reason why?
2. What is the reason for the delay?
3. Why are you delayed?

Be casual but respectful. Keep it short and clear.

"""


GET_DELAY_REASON_PROMPT = """
If the person provides the reason for the delay, respond with 'yes' only, otherwise respond to the trucker last message and ask them to provide the delay reason.
Example tones of the response message:
1. Can you tell the reason why you are delayed?
2. What is the reason for the delay?
3. Why are you delayed?
4. I get it, it's company policy, can you please provide the reason for the delay?

Be casual but respectful. Keep it short and clear.
"""



EXTRACT_HIGHWAY_NAME_PROMPT = """
Get the highway name, if there is any, else return null from the response of the driver.
Human response: {human_response}
{format_instructions}
outputs:
1) highway_name: string
"""
