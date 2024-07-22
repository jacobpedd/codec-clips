from braintrust import traced
from web.lib.llm_client import llm_client
from .transcript_utils import find_phrase, format_transcript_view


@traced
def critique_clip(transcript: dict, moment: dict, clip: dict | None) -> str | None:
    tools = [
        {
            "type": "function",
            "function": {
                "description": "Approve the clip that the user submitted and allow it to be submitted to social media. This tool has no parameters or arguments.",
                "name": "approve_clip",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    transcript_view = format_transcript_view(
        transcript, moment["quote"], clip, 100, 100
    )
    clip_start = find_phrase(transcript, clip["start_quote"])
    clip_end = find_phrase(transcript, clip["end_quote"])
    clip_duration = (clip_end["end"] - clip_start["start"]) / 1000.0
    clip_minutes = int(clip_duration // 60)
    clip_seconds = int(clip_duration % 60)
    print(f"Clip duration: {clip_minutes}min {clip_seconds}s")

    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "# Role and Context",
                    "You are an AI assistant helping podcast hosts edit viral clips form their podcast transcript. The clips are based on their podcast transcript and posted to their YouTube channel.",
                    "",
                    "# Task",
                    "Evaluate the clip draft based on the clip criteria. Provide feedback to the user if needed.",
                    "",
                    "# Input",
                    "The user will provide the clip's name, duration, and current transcript.",
                    "The transcript will have the following sections denoted by <tags>:",
                    "- <TRANSCRIPT START>: Denotes the start and end of the transcript. Your transcript will only contain this tag if it starts at the beginning of the podcast transcript.",
                    "- <TRANSCRIPT STOP>: Denotes the end of the transcript. Your transcript will only contain this tag if it ends at the end of the podcast transcript.",
                    "- <CONTEXT START>: Denotes the start of the context surrounding the clip. Your transcript will only contain this tag if it does not start at the beginning of the podcast transcript.",
                    "- <CONTEXT END>: Denotes the end of the context surrounding the clip. Your transcript will only contain this tag if it does not end at the end of the podcast transcript.",
                    "- <CLIP>: Opening and closing the tag denotes the start and end of the currently selected clip. If there is no clip selected, you need to use the submit_clip tool to submit the first clip.",
                    "- <QUOTE>: Opening and closing the tag denotes the start and end of a quote in the transcript. The quote is the key moment in the clip that the user wants to center the clip around.",
                    "",
                    "# Clip Criteria",
                    "- Be around 2-10 minutes in length",
                    "- Have enough context to stand alone when played without any additional content",
                    "- Exclude show intros, outros, and advertisements",
                    "- Only include the nessasary context to capture the moment",
                    "- Start clips with enough context to understand the discussion",
                    "- End clips with a natural conclusion to the discussion",
                    "- Do not start or end in the middle of a sentence",
                    "Note: The clip is only what is between the CLIP tags. Users will not see the surrounding context. Remember to only give feedback related to the start or end of the clip.",
                    "",
                    "# Response",
                    "If the clip meets the above criteria, use submit_clip to finalize it.",
                    "If there are changes the editors can make to comply with the criteria, respond to the user with your feedback.",
                    "Keep your feedback concise and to the point.",
                    "Your feedback can be at most 3 sentences long.",
                    "Editors can only change where the clip start and ends so only give feedback related to the start or end.",
                ]
            ),
        }
    ]
    for example in EXAMPLES:
        messages += [
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"Name: {example['name']}",
                        f"Duration: {example['clip_minutes']} minutes {example['clip_seconds']} seconds (criteria requires 2-10 minutes)",
                        f"Transcript:",
                        example["transcript"],
                        "Remember to give concise feedback that is only related to the start or end of the clip.",
                        "If the clip meets the your criteria, use the submit_clip tool to finalize it.",
                    ]
                ),
            },
            {"role": "assistant", "content": example["feedback"]},
        ]
    messages += [
        {
            "role": "user",
            "content": "\n".join(
                [
                    f"Name: {moment['name']}",
                    f"Duration: {clip_minutes} minutes {clip_seconds} seconds (criteria requires 2-10 minutes)",
                    f"Transcript:",
                    transcript_view,
                    "Remember to give concise feedback that is only related to the start or end of the clip.",
                    "If the clip meets the your criteria, use the submit_clip tool to finalize it.",
                ]
            ),
        },
    ]

    response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        tools=tools,
        tool_choice="auto",
        messages=messages,
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls is None:
        text = response_message.content
        return text
    if len(tool_calls) > 1:
        raise ValueError("More than one tool call found in response")

    tool_call = tool_calls[0]
    if tool_call.function.name == "approve_clip":
        return None


EXAMPLES = [
    {
        "name": "Gen Z voters' desire for generational shift in politics",
        "clip_minutes": 3,
        "clip_seconds": 2,
        "feedback": "While the start of the clip is strong, it appears to end in the middle of a sentence. The clip is only 3 minutes long so it can be extended to let the current topic come to a more natural conclusion. Extend the clip to a more natural ending.",
        "transcript": """<CONTEXT START>
# Speaker C
the group of people that are going to be fighting and begging and demanding change, like we're never going to be okay with what the status quo is. So even if Biden has been the most progressive president, and we do talk about that, I think young people are always going to be the group that pushes us to be better, to have a more equitable and fair society because we've always been that way on every civil justice fight that's existed, in my opinion. So I think we just need to do a better job at talking to them.


<CLIP>

<QUOTE>
# Speaker A
Anderson Clayton is a 26 year old voter in a swing state who wants to see a generational shift in our politics that makes her just like most Gen Z voters.


</QUOTE>
# Speaker A
What makes her different is that she decided to run for state party chair in North Carolina and is now the youngest person in America to ever hold that title. We called her up to talk about what she's hearing from young voters in North Carolina as she tries to flip the state this November. A tough challenge in a place that's only competitive because of an electorate that keeps getting younger and more diverse. For a few decades now, young voters have been a big reason that democrats win elections in 2020. Over half of 18 to 29 year olds voted low compared to other age groups, but still the highest youth turnout since the voting age was lowered to 18. For the first time ever, there were more Gen Z and millennial voters combined than there were baby boomers and the silent generation. And these voters supported Biden by around 20 points more than Trump, a huge gap that we also saw in the 2018 and 2022 midterms. But there are warning signs everywhere that 2024 may not look the same. You see it in polls, you hear it in focus groups, and youve probably heard it anecdotally. A lot of younger voters seem more disillusioned and angry than usual about politics, the two parties and their presidential candidates, Democrats, have always had challenges getting younger people to actually vote. But this time theres a concern that even if they do vote, they might not support Biden or other Democrats by the same margins they have in the past. The big question, of course, is why and what would actually motivate young voters to get out and help defeat Trump and MAGA politicians with the same turnout and margins that we saw in 2018, 2020 and 2022? We asked Anderson what she thinks.

# Speaker C
I think that parties in previous years have been the ways that people are motivated to turn out and vote. But I think in terms of young people, issues are gonna motivate them a lot more this year and in future generations and in future cycles of political organizing that we're gonna see. And young people really care about specific policy issues. Finding a job, finding a house, being able to live, like, deciding where they want to do they wanna start a family, do they not? Like, that should be their decision to make at the end of the day, like Gaza. And I. Cause I think about it, I'm like, that is the one issue I hear so much talked about when we put young people in that category. We have heard the president call for a ceasefire. We've heard the vice president call for a ceasefire. Like, I am not negating that. That is a huge issue for a lot of young people, especially a lot of politically active young people that are aware of that issue, have been aware of it, and know what's going on and have also come into a political awakening on it. But I also think that, like, young voters, especially in the south right now, have seen our rights be fundamentally stripped from us. And I think that people here in this region of the country care a lot about what is happening at the state


</CLIP>
# Speaker C
level and at the local level, because it is causing us to not be able to see a future staying in the state that we grew up in, that we care about, that we want to live in for the next 50 years. And so a lot of those issues look like housing affordability. It looks like wages in North Carolina. Abortion rights is something that I hear from college campuses every day when I am on them. And also the fact, I mean, UNC Chapel Hill had two school shooter drills last year alone, and they had a faculty

<CONTEXT END>""",
    },
    {
        "name": "Brian Windhorst's insights on Team USA's potential starting lineup and rotations",
        "clip_minutes": 5,
        "clip_seconds": 49,
        "feedback": "To give the audience more context, the clip should start with the question from Speaker B that triggers Speaker C's response: 'What's the most interesting strategic rotation, whatever question you, you are looking at for Team USA in this training camp?' The clips duration well within the acceptable range and it ends with a natural conclusion to the discussion.",
        "transcript": """<CONTEXT START>
# Speaker C
though it's the United States's game, the game is played in the international style. It just feel, it, just everything about it feels a little bit uncomfortable and it, it blunts the american advantage. So, and it, you know, last year they finished fourth. They finished fourth. And I loved being around that team. They had great chemistry and they finished fourth.

# Speaker B
You've, you're a busy man. I want to ask you just one last question. This is your domain. What's the most interesting strategic rotation, whatever question you, you are looking at for Team USA in this training camp?


<CLIP>

<QUOTE>
# Speaker C
So first off, who's going to, who's going to be the fifth starter because LeBron is starting, Steph Curry is starting, Joel Embiid is starting and Kevin Durant is starting. Who's going to be the fifth starter? I'm leaning toward probably Anthony Davis, but we'll see. Secondly, how much is Kawhi Leonard going to play?


</QUOTE>
# Speaker C
He, that's a huge advantage position for the US to have Kawhi Leonard potentially as a bench player and where you can say to him, Kawhi, you're only going to play 15 minutes, but play like your hair's on fire in those 15 minutes. That's the strategy that Mike Krzyzewski really got going. He's like, look, I'm going to play twelve guys and they're all going to play in five minute stretches and they're all going to play like crazy men, full press and everything like that. I don't know if we have the team to do that because we have an older team, but Kawhi Leonard's role is a question. And also Ann Edwards and Jason Tatum. Jason Tatum has played with Team USA. This is his third time playing for Team USA. He has been excellent in international basketball. He was terrific in, in the Olympics coming off the bench as sort of the bench score. So that's, that's the role I expect him in again, is coming off the bench is sort of the guy off the bench, but he's got to have a significant role. He is an excellent FIBA player. He's coming in off his best run as a pro. He is a champion. He is probably in his, in better rhythm than any of these guys. How on point is Tatum going to be and how much I think, I think you've got. Curry's going to have to kind of dedicate themselves himself to use them. And then thirdly, what role is Ann Edwards play? Because at the end of the game, I think Drew Holiday is going to be in there. Drew Holiday is going to be in there because he's so important defensively. He finished all of the games in Tokyo when he basically got on his feet after flying in from the US because he was in the finals. He had just won the title with Milwaukee and he was a little bit off of his game for a game and a half. He was a difference making player. Drew Holiday, I think, is going to finish games, so holiday is going to be one of the guards out there. I cannot see steph not being out there. He's just an absolute weapon and a half. But I think Ian Edwards is such a special talent and he was the USA's best player in FIBA last year. And the thing that he can do that is so valuable is he can score in all three levels and he applies so much pressure to the defense because of his penetration ability. The warm up games are going to be really interesting because last year what basically happened was Kerr went in thinking that Ant was going to be their 6th man and even told them, you're going to be the 6th man. And like ten days in he was like, actually, he's not our 6th man, he's our best player. And there are five exhibition games and they're going to, you know, you know, and bead's not going to be playing all of them. You know, LeBron's not going to be playing all of them. All these guys are going to take games off, but Ann is going to play. And it would not surprise me if Ant plays like awesome in these exhibition games. Ant loves playing in Dubai. This is ants third trip to Dubai in a year, and he's played some great games there because he went there with all this other stuff. So any with the Timberwolves as well as Team USA. So anyway, those three positions, how much for Kawhi, how much for Ant and how are they going to use holiday and who are they going to play at their guards at the end of the game. But these are all good problems. You know, there isn't a hole on the roster. I think there's only one guy that goes in who shouldn't expect much playing time, and that's Halliburton. But Halliburton was very good in the, in the World cup last year. He was a very. He wasn't good defensively, but he was a really good player. So if you needed to go to him, I wouldn't have any qualms about it. But really, the other eleven guys, I think you could honestly make a case. They're all going to be in the rotation and it wouldn't surprise me if Kerr used all eleven. And the other thing I'll say is, when it comes to Embiid and Kawhi, you don't need them for all six games. You need them against Serbia in the, in the pool play, and you need them in the three knockout games, potentially quarterfinals, semifinals, finals. If they want to sit and beat and kawhi down for South Sudan and Puerto Rico, then, I mean, I don't know. You're worried about rhythm? I am. I think they should use the depth.

# Speaker B
Even Giannis is on a minutes restriction right now in must win games for Greece.

# Speaker C
Yes. So, you know, they, you know, he's got a great roster, and his, his curse issue is, you know, figuring out a way to use everybody, so don't be afraid to rest, people. And last thing I'll say, I know I'm filibustering on your pod. I'm sorry, but this coaching staff is brilliant. You have Eric Spoelstra, who is tactically one of the best coaches in the history of the sport. You have Ty Liu, whose in game maneuvers are elite, if not the best in game adjustment guy up there in the top percentage and also a very good game planner. You have Steve Kerr, who is a very good vibes guy, keeping the guys together, you know, setting the tone, you know, everything like that mark Fu from Gonzaga, who is really, really good at bonding with some of the players. If the US loses the Olympics, we will have lost it with our best coaches. And this is what I, this is what I said. You know, there were some journalists last year at the World cup who were just defiant about the way the US is playing because they were playing super small and everything like that, and it ended up costing them. And I was like, look, these are our best coaches.


</CLIP>
# Speaker C
And by the way, there's other, like, supporting coaches out there, like behind the scenes that are, you know, that are, will not be on the bench, who are also supporting, like Jeff van Gundy.

# Speaker B
Is going to say, our old buddy.

# Speaker C
And, and Will Hardy, and we, this is the best we can send with our players. That's the best we can send with our coaches. And so if, if the US gets out coached, we must take the l because this is the best we got. So it's the best players we got. It's the best coaches we

<CONTEXT END>
""",
    },
    {
        "name": "Biden defiant about staying in 2024 race",
        "clip_minutes": 1,
        "clip_seconds": 27,
        "feedback": "The clip starts at the start of the transcript with what is likely an intro, which should not be included. It also ends abruptly in the middle of a thought while being less than 2 minutes long. The start of the script should skip the intro and the end of the clip should be extended to include the full thought.",
        "transcript": """<TRANSCRIPT START>

<CLIP>
# Speaker A
If it's Monday. An increasingly frustrated and defiant President Biden insists he is staying in the 2024 race, dismissing the growing number of Democrats calling for him to step aside and blasting what he calls the elites within his own party. Plus, ahead of next week's convention, the Trump campaign unveils the new Republican Party platform, softening its stance on the issue of abortion while doubling down on the former president's most aggressive policy proposals like mass deportations. And voters in France block the far right from power in a surprise upset victory for centrists and the left as the country enters a new phase of political uncertainty with no clear majority to form a government. And welcome to Meet the Press now. I'm Aaron Gilchrist in Washington, where a defiant President Biden is pledging to stay in the race no matter what, even as more Democrats call on him to reconsider running or step aside. Today, in an animated and occasionally testy phone interview on MSNBC, the president was adamant that he will not withdraw as he lashed out at political elites within his own party. The


<QUOTE>
# Speaker A
The bottom line here is that we're not going anywhere. I am not going anywhere. I wouldn't be running if I didn't absolutely believe that I am the best candidate to beat Donald Trump in 2024.


</QUOTE>

</CLIP>
# Speaker A
I'm not going to explain any more about what I should or shouldn't do. I am running. I'm getting so frustrated by the elites. Now, I'm not talking about you guys, but by the elites in the party who they know so much more. If any of these guys don't think I should run against me, announce the president challenge me at the convention. Now, this comes after the president sent a letter to congressional Democrats with a similarly defiant tone, suggesting that those calling for him to step aside are defying the will of democratic primary voters. So far,

<CONTEXT END>""",
    },
]
