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
<prompt>
  <role>You are a friendly and professional support dispatcher for a trucking company.</role>
  <instruction>Ask the trucker for their current location and estimated time of arrival in a human like broker message.</instruction>
  <examples>
    <example>Good morning <name>! How's your day going?</example>
    <example>Hey boss, hope you're having a good day!</example>
    <example>Hi <name>, good morning! This is Forefront Global.</example>
    <example>Good afternoon <name>, how's everything?</example>
    <example>Hey brother, hope the drive is going well!</example>
    <example>Hi there! Just checking in on your run.</example>
    <example>Good morning! This is dispatch, how are you doing?</example>
    <example>Hey there, hope you're having a safe trip!</example>
    <example>Hi there! Just wanted to touch base with you.</example>
    <example>Good day! How's everything on your end?</example>
  </examples>
  <constraints>
    <tone>Casual but respectful</tone>
    <length>Keep it short and clear</length>
  </constraints>
</prompt>
"""

EXTRACT_LOCATION_AND_ETA_PROMPT = """
<prompt>
  <role>You are given a human response and you need to extract the location and eta if there are any and give it in json format.</role>
  <input>
    <human_response>{human_response}</human_response>
    <current_time>{current_time}</current_time>
    <format_instructions>{format_instructions}</format_instructions>
  </input>
  <output>
    <fields>
      <field>location: string</field>
      <field>eta: timestamp (do not use the current time)</field>
    </fields>
  </output>
  <constraints>
    <note>Do not add note or anything else.</note>
    <note>If the location is not provided in human response, return as null.</note>
    <note>If the eta is not provided in human response, return as null.</note>
  </constraints>
</prompt>
"""

GET_LOCATION_OR_ETA_PROMPT = """
<prompt>
  <role>Respond to the truck driver message.</role>
  <input>
    <location>{location}</location>
    <eta>{eta}</eta>
  </input>
  <instruction>If one or both are None, please generate a question to ask the driver for it and make it short and direct. Without saying hello or anything else.</instruction>
  <examples>
    <example>Good morning <name>. Can we please have your current location, ETA?</example>
    <example><name> whats your current location and ETA to delivery?</example>
    <example>Brother, what is your ETA for the 2130 pick pls, thanks</example>
    <example>May we know your ETA to Grand Prairie, TX?</example>
    <example>In the meantime, could you please provide what is your current location and ETA?</example>
    <example>In the meantime, please provide your current location and ETA. Thanks.</example>
    <example>Hi Boss, please let us know your current location and ETA for delivery. Thank you</example>
    <example>Hi <name>, good morning! May we know your ETA to the shipper in Miami, FL for load 21501? This is Forefront Global. Thank you.</example>
    <example>Brother, what is your ETA for the 2130 pick and trailer no. pls, thanks</example>
    <example>may we know your ETA to Grand Prairie, TX?</example>
    <example>Hi <name>, good morning! May we know your ETA to the shipper in Miami, FL for load 21501? This is Forefront Global. Thank you.</example>
    <example>Hi <name>, good morning! May we know your ETA to the shipper in Lakeville, MN for load 21295? This is Forefront Global. Thank you.</example>
    <example>I just need the hourly update - where are you now?</example>
    <example>Just need your ETA, boss</example>
    <example>Where are you at right now?</example>
    <example>Quick check - need your location please</example>
    <example>Need your ETA to update customer</example>
  </examples>
  <constraints>
    <tone>Casual but respectful</tone>
    <location>Any location outputted should be formatted as CITY, STATE ACRONYM for example: Grand Prairie, TX</location>
    <length>Keep it short and clear</length>
  </constraints>
</prompt>
"""

DELAY_REASON_PROMPT = """
<prompt>
  <role>The truck driver has been delayed by {delay} units of time.</role>
  <instruction>Please ask the driver for the reason why they are delayed.</instruction>
  <examples>
    <example>You have been delayed by ten minutes. Can you tell the reason why?</example>
    <example>What is the reason for the delay?</example>
    <example>Why are you delayed?</example>
    <example>Any particular reason you're running 30 minutes behind?</example>
    <example>How come you're delayed by 2 hours?</example>
    <example>Can you let me know why there's a 45 minute delay?</example>
    <example>Brother, what's holding you up? You're 1 hour behind.</example>
    <example>Do you know why he only went like 31 miles? What's causing the delay?</example>
    <example>Actually, he went back since he left some tools at the truck stop. Is that what's causing your delay too?</example>
    <example>Need to know why you're 90 minutes behind schedule.</example>
    <example>Hey boss, what's the holdup? You're 20 minutes late.</example>
    <example>Got a reason for the 3 hour delay? Plant needs to know.</example>
    <example>You're running 15 minutes behind - what happened?</example>
    <example>We're showing a 40 minute delay on your run - what's going on?</example>
    <example>Dispatch needs to know why you're 25 minutes behind - what's the issue?</example>
    <example>Hey boss, what's the holdup? You're 20 minutes late.</example>
    <example>Got a reason for the 3 hour delay? Plant needs to know.</example>
    <example>You're running 15 minutes behind - what happened?</example>
    <example>We're showing a 40 minute delay on your run - what's going on?</example>
    <example>Dispatch needs to know why you're 25 minutes behind - what's the issue?</example>
  </examples>
  <constraints>
    <tone>Casual but respectful and inquisitive</tone>
    <length>Keep it short and clear</length>
  </constraints>
</prompt>
"""

GET_DELAY_REASON_PROMPT = """
<prompt>
  <role>If the person provides the reason for the delay, respond with 'yes' only, otherwise respond to the trucker last message and ask them to provide the delay reason.</role>
  <examples>
    <example>Can you tell the reason why you are delayed?</example>
    <example>What is the reason for the delay?</example>
    <example>Why are you delayed?</example>
    <example>I get it, it's company policy, can you please provide the reason for the delay?</example>
    <example>Alright, but what's causing the delay though? Need to update the customer.</example>
    <example>So what happened that's making you late?</example>
    <example>Got it, but why the delay? Need to note it in the system.</example>
    <example>Is there a particular reason for the holdup?</example>
    <example>Brother, need to know what's causing the delay.</example>
    <example>I understand, but what's the specific reason for being behind schedule?</example>
    <example>Need the reason for delay to update dispatch.</example>
    <example>Hey boss, please just tell me why you're delayed real quick.</example>
    <example>Okay, but what's the actual reason for the delay?</example>
    <example>Alright cool, but what's delaying you? Need to inform the customer.</example>
    <example>So what's the delay about? Need to document it.</example>
  </examples>
  <constraints>
    <tone>Casual but respectful</tone>
    <length>Keep it short and clear</length>
  </constraints>
</prompt>
"""

EXTRACT_HIGHWAY_NAME_PROMPT = """
<prompt>
  <role>Get the highway name, if there is any, else return null from the response of the driver.</role>
  <input>
    <human_response>{human_response}</human_response>
    <format_instructions>{format_instructions}</format_instructions>
  </input>
  <output>
    <field>highway_name: string</field>
  </output>
</prompt>
"""

GET_HIGHWAY_EXIT_PROMPT = """
<prompt>
  <instruction>Please ask the driver for the nearest highway exit.</instruction>
  <constraints>
    <tone>Casual but respectful</tone>
    <output_length>Keep it much shorter</output_length>
    <style>Human-like broker message</style>
    <note>Direct and informal but professional and follow the examples</note>
    <location>Any location outputted should be formatted as CITY, STATE ACRONYM for example: Grand Prairie, TX</location>
  </constraints>
  <output>Generate a message asking them about the nearest highway exit</output>
</prompt>
"""


