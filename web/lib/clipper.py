import os
import json
import re
import ffmpeg
import anthropic
from thefuzz import fuzz
from django.conf import settings

from web.lib.r2 import download_audio_file, get_audio_transcript, upload_file_to_r2

client = anthropic.Anthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    base_url="https://anthropic.hconeai.com/",
    default_headers={
        "Helicone-Auth": f"Bearer {settings.HELICONE_API_KEY}",
        "Helicone-Cache-Enabled": "true",
        "Helicone-User-Id": "clipper",
        "Helicone-Retry-Enabled": "true",
    },
)


class Clip:
    def __init__(self, name: str, start: int, end: int, start_phrase: str, end_phrase: str):
        self.name = name
        self.start = start
        self.start_phrase = start_phrase
        self.end = end
        self.end_phrase = end_phrase
    
    def overlaps_with(self, start: int, end: int) -> bool:
        # Check if there's any overlap between the clip and the given range
        return max(self.start, start) < min(self.end, end)


def generate_clips(transcript_bucket_key: str) -> list[Clip]:
    transcript = get_audio_transcript(transcript_bucket_key)
    if not transcript:
        raise ValueError("Transcript not found")

    clips = suggest_clips(transcript)
    clips = refine_clips(transcript, clips)

    return clips


def generate_clips_audio(audio_bucket_key: str, clips: list[Clip]):
    # Download the audio file from R2 to the disk
    audio_file_path = download_audio_file(audio_bucket_key)
    print(f"Downloaded audio file to {audio_file_path}")

    clip_bucket_keys = []
    try:
        for clip in clips:
            try:
                # Use ffmpeg to create the clip
                clip_file_path = save_clip_audio("/tmp/", audio_file_path, clip)

                # Upload the clip to R2
                clip_key = (
                    f"clip-{os.path.basename(audio_bucket_key)}-{clip_file_path}"
                )
                upload_file_to_r2(clip_file_path, clip_key)
                print(f"Uploaded clip to R2: {clip_key}")

                clip_bucket_keys.append(clip_key)
            finally:
                # Clean up the temporary clip file
                if os.path.exists(clip_file_path):
                    os.remove(clip_file_path)
                    print(f"Cleaned up temporary clip file: {clip_file_path}")

    finally:
        # Clean up the temporary input audio file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            print(f"Cleaned up temporary audio file: {audio_file_path}")

    return clip_bucket_keys

def save_clip_audio(output_dir, audio_file_path: str, clip: Clip):
    output_filename = f"clip_{clip.name.replace(' ', '_')}.mp3"
    output_path = os.path.join(output_dir, output_filename)

    # Convert milliseconds to seconds
    start_seconds = clip.start / 1000.0
    duration_seconds = (clip.end - clip.start) / 1000.0

    # Use ffmpeg to create the clip
    (
        ffmpeg.input(audio_file_path, ss=start_seconds, t=duration_seconds)
        .output(output_path, acodec="libmp3lame", ab="128k")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )

    return output_path

def suggest_clips(transcript: str):
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    completion = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        stop_sequences=["</CLIPS>"],
        system="\n".join(
            [
                "You are a helpful assistant who identifies social media clips in podcast transcripts.",
                "# TASK",
                "You are helping the user, the podcast host, by finding clips within their show's transcripts.",
                "The user will provide the transcript in their message.",
                "You will provide 5 total clips.",
                "# CLIPS",
                "Clip are between 2 and 10 minutes long (at least 500 words).",
                "Clips capture interesting takes and the conversation around them.",
                "Clips do not start or stop in the middle of a thought or statement.",
                "Clips feel like they have a logical introduction and conclusion.",
                "Listeners enjoy listening to the clip without any additional context.",
                "Clips will be posted on YouTube and are crafted to go viral.",
                "Content from clips does not overlap.",
                "Clips never include the show's intros, outros, or ads.",
                "# RESPONSE FORMAT",
                "Your response should contain <CLIPS></CLIPS> inside of which you should put your JSON array of clips.",
                "Each clip should be a JSON object with the following keys: name, start, and end.",
                "- name: The name of the clip",
                "- start: A unique short string that marks the start of the clip",
                "- end: A unique short string that marks the end of the clip",
                'Start and end phrases should be as short as possible while remaining unique.',
                'Cut off phrases before they encounter an advertisement or outro.',
                "A python script will look for start and end phrases in the transcript.",
            ]
        ),
        messages=[
            {"role": "user", "content": f"Here is my show's transcript, can you suggest 5 clips for YouTube?\n<TRANSCRIPT>\n{lex_example['content']}\n</TRANSCRIPT>"},
            {"role": "assistant", "content": "I understand. I'll be happy to assist you while being careful not to reproduce any copyrighted material. I'll focus on summarizing and discussing the content rather than directly quoting large sections. Please let me know if you have any specific questions about the podcast transcript that I can help with."},
            {"role": "user", "content": "Thank you for not reproducing any copyright material. Please proceed by suggesting 5 clips for YouTube."},
            {
                "role": "assistant",
                "content": "\n".join([
                    "Sure, here are 5 clips from the show that will work well on YouTube:\n<CLIPS>",
                    "[",
                    f"   {json.dumps(lex_example["clips"][0])}",
                    f"   {json.dumps(lex_example["clips"][1])}",
                    f"   {json.dumps(lex_example["clips"][2])}",
                    f"   {json.dumps(lex_example["clips"][3])}",
                    f"   {json.dumps(lex_example["clips"][4])}",
                    "]",
                    "</CLIPS>",
                ]),
            },
            {"role": "user", "content": f"Here is the transcript for another one of my shows. Can you suggest 5 clips for YouTube from this transcript?\n<TRANSCRIPT>\n{format_transcript(transcript)}\n</TRANSCRIPT>"},
        ],
    )

    if not completion:
        raise ValueError("Empty response from model")

    text = completion.content[0].text

    if completion.stop_reason == "stop_sequence":
        text += "</CLIPS>"

    suggested_clips = parse_json_from_tag(text, "<CLIPS>", "</CLIPS>")

    clips = []
    for clip in suggested_clips:
        try:
            start, end = find_clip_timing(transcript, clip["start"], clip["end"])
            clips.append(Clip(
                clip["name"], 
                start, 
                end, 
                clip["start"], 
                clip["end"]
            ))
        except ValueError as e:
            print("Error finding timing for clip:", json.dumps(clip, indent=2))
            print(e)
            continue

    return clips

def refine_clips(transcript: str, clips: [Clip]) -> list[Clip]:
    refined_clips = []

    # Add global word index to each word in the transcript
    word_index = 0
    for utterance in transcript:
        for word in utterance["words"]:
            word["word_index"] = word_index
            word_index += 1

    total_words = word_index  # Total number of words in the transcript

    for clip in clips:
        start_word_index = -1
        end_word_index = -1

        # Find the start and end word indices of the clip
        clip_transcript = ""
        for utterance in transcript:
            if clip.overlaps_with(utterance["start"], utterance["end"]):
                clip_transcript += f"# Speaker {utterance['speaker']}\n"
                
                words = [
                    word for word in utterance["words"] 
                    if clip.overlaps_with(word["start"], word["end"])
                ]

                if start_word_index == -1:
                    start_word_index = words[0]["word_index"]
                end_word_index = words[-1]["word_index"]
                
                text = " ".join([word["text"] for word in words])
                clip_transcript += f"{text}\n\n"

        # Add N words of context to the start and end of the clip
        context_length = 1000
        start_context_start_index = max(0, start_word_index - context_length)
        start_context_end_index = start_word_index - 1

        end_context_start_index = end_word_index + 1
        end_context_end_index = min(total_words - 1, end_word_index + context_length)

        def get_transcript_between_indices(start_index, end_index):
            transcript_between_indices = ""
            for utterance in transcript:
                utterance_start_index = utterance["words"][0]["word_index"]
                utterance_end_index = utterance["words"][-1]["word_index"]
                
                # Check if there's any overlap between the utterance and the desired range
                if start_index <= utterance_end_index and end_index >= utterance_start_index:
                    transcript_between_indices += f"# Speaker {utterance['speaker']}\n"
                    words_in_range = [word for word in utterance["words"] 
                                      if start_index <= word["word_index"] <= end_index]
                    transcript_between_indices += " ".join([word["text"] for word in words_in_range])
                    transcript_between_indices += "\n\n"
            return transcript_between_indices

        start_context = get_transcript_between_indices(start_context_start_index, start_context_end_index)
        end_context = get_transcript_between_indices(end_context_start_index, end_context_end_index)

        # Construct the final transcript with context
        final_transcript = '[START OF TRANSCRIPT] ' if start_context_start_index == 0 else '[START OF CONTEXT]'
        final_transcript += '\n' + start_context
        final_transcript += "\n\n<CLIP START>\n\n"
        final_transcript += clip_transcript
        final_transcript += "\n\n<CLIP END>\n\n" 
        final_transcript += end_context
        final_transcript += '[END OF TRANSCRIPT]' if end_context_end_index == total_words - 1 else '[END OF CONTEXT]'

        # Ask the LLM to critique the clip
        critique = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            system="\n".join(
                [
                    "You are a helpful assistant who critiques podcast clips that are generate for social media.",
                    "# TASK",
                    "The user will send you the transcript of the clip as well as some of the transcript before and after the clip.",
                    "The user will also send the name and duration of the clip in their message.",
                    "The clip identified in the transcript using <CLIP START> and <CLIP END>.",
                    "The ways to edit the content of the clip are changing the start and end phrases that bound the clip.",
                    "You should first critique the clip, the suggest changes to start and end phrases if needed.",
                    "# CLIPS",
                    "Clip are between 2 and 10 minutes long (at least 500 words).",
                    "Clips capture interesting takes and the conversation around them.",
                    "Clips do not start or stop in the middle of a thought or statement.",
                    "Clips feel like they have a logical introduction and conclusion.",
                    "Listeners enjoy listening to the clip without any additional context.",
                    "Clips will be posted on YouTube and are crafted to go viral.",
                    "Content from clips does not overlap.",
                    "Clips never include the show's intros, outros, or ads.",
                    "# RESPONSE FORMAT",
                    "Respond to the following questions:",
                    '1. As a listener, what do you like about the clip?',
                    '2. What do you dislike about the clip?',
                    '3. How is the length of the clip compared to the guidelines for clip length? How much content can be added or removed?',
                    '4. Can you improve where the clip starts? If so, to what?',
                    '5. Can you improve where the clip ends? If so, to what?',
                    "Don't give specific edits, just give general feedback.",
                    "Don't give exact start and end phrases, the user will make that decision.",
                    "It's ok if no changes are needed, sometimes the first clip is the best possible clip.",
                    "Only change the start start or end phrase if you're changing the start or end of the clip.",
                    "Examples of common edits:"
                    "- A minor change to the end phrase to give it a more clean stopping point.",
                    "- A major extension to the clip to add the continuation of a relevant conversation.",
                    "- Change the start phrase to remove the podcast introduction."
                    "- A clip is on the longer end and includes two topics, edit it to just include the best topic.",
                    "- Changing nothing because the clip is already good.",
                ]
            ),
            messages=[

                {"role": "user", "content": "\n".join(
                    [
                        f"Name: {clip.name}",
                        f"Duration: {int((clip.end - clip.start) / 60000)} minutes & {((clip.end - clip.start) / 1000.0) % 60:.2f} seconds",
                        "Transcript:",
                        final_transcript,
                    ]
                )},
            ],
        )

        if not critique:
            raise ValueError("Empty response from model")

        critique_text = critique.content[0].text

        # Apply the critique to the clip
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            stop_sequences=["</CLIP>"],
            system="\n".join(
                [
                    "You are a helpful assistant who improves podcast clips based on the user's feedback.",
                    "# TASK",
                    "You generated a clip based on the transcript of a podcast episode.",
                    "The user has feedback on the contents of the clip",
                    "You should improve the clip based on the users feedback.",
                    "To improve the clip, you can change the name, start phrase, and end phrase.", 
                    "You should think about what content you could add or remove from the ends of the clip.",
                    "# RESPONSE FORMAT",
                    "Your response should contain <CLIP></CLIPS> inside of which you should put the JSON object of the clip.",
                    "The clip should be a JSON object with the following keys: name, start, and end.",
                    "- name: The name of the clip",
                    "- start: A unique, verbatim word phrase that starts the clip",
                    "- end: A unique, verbatim phrase that ends the clip",
                    "Don't change the name of the clip.",
                    "Start and end phrases must be exact matches from transcript otherwise it will cause an error.",
                    "Start and end phrases should be as short as possible while remaining unique.",
                ]
            ),
            messages=[
                {"role": "user", "content": format_transcript(transcript)},
                {"role": "assistant", "content": "\n".join([
                    "<CLIP>",
                    json.dumps({
                        "name": clip.name,
                        "start": clip.start_phrase,
                        "end": clip.end_phrase,
                    }),
                    "</CLIP>"
                ])},
                {"role": "user", "content": critique_text},
            ],
        )

        if not response:
            raise ValueError("Empty response from model")
        
        text = response.content[0].text

        if response.stop_reason == "stop_sequence":
            text += "</CLIP>"

        suggested_clip = parse_json_from_tag(text, "<CLIP>", "</CLIP>")
        try:
            start, end = find_clip_timing(transcript, suggested_clip["start"], suggested_clip["end"])
            refined_clips.append(Clip(
                suggested_clip["name"], 
                start, 
                end, 
                suggested_clip["start"], 
                suggested_clip["end"]
            ))
        except ValueError as e:
            print(f"Error finding clip timing: {json.dumps(suggested_clip, indent=2)}")
            continue
    
    return refined_clips

def format_transcript(transcript):
    formatted_transcript = ""
    for utterance in transcript:
        formatted_transcript += f"# Speaker {utterance['speaker']}\n"
        formatted_transcript += f"{utterance['text']}\n\n"
    return formatted_transcript

def find_clip_timing(transcript: list, start_phrase: str, end_phrase: str) -> tuple[int, int]:
    start_time = -1
    end_time = -1
    start_phrase = start_phrase.lower()
    end_phrase = end_phrase.lower()

    # We only care about timing, so we can just loop through all the words
    words = []
    for utterance in transcript:
        words += utterance["words"]

    def find_phrase(phrase, start_from=0, end_at=None):
        if end_at is None:
            end_at = len(words)
        
        phrase_words = phrase.split()
        best_match = (-1, 0)  # (index, score)
        
        for i in range(start_from, end_at - len(phrase_words) + 1):
            candidate = ' '.join(word['text'].lower() for word in words[i:i+len(phrase_words)])
            candidate = re.sub(r'[^\w\s]', '', candidate)
            score = fuzz.ratio(phrase, candidate)
            
            if score > best_match[1]:
                best_match = (i, score)
        
        if best_match[1] > 85:  # NOTE: Threshold for matching, set based on vibes
            return best_match[0]
        else:
            print(f"Error finding phrase, best score was {best_match[1]} out of {90}")
            print(f"Original phrase: {phrase}")
            print(f"Best match:      {' '.join(word['text'] for word in words[best_match[0]:best_match[0]+len(phrase_words)]).lower()}")
            raise ValueError("Error finding phrase")
        return -1

    # Find start phrase
    start_index = find_phrase(start_phrase)
    if start_index != -1:
        start_time = words[start_index]["start"]

        # Find end phrase, starting from after the start phrase
        end_index = find_phrase(end_phrase, start_index + len(start_phrase.split()))
        if end_index != -1:
            end_time = words[end_index + len(end_phrase.split()) - 1]["end"]

    if start_time == -1 or end_time == -1:
        raise ValueError("Could not find clip timing")

    return start_time, end_time

def parse_json_from_tag(text: str, start_tag: str, end_tag: str) -> dict:
    start_index = text.index(start_tag)
    end_index = text.index(end_tag)

    if start_index == -1:
        raise ValueError(f"Start tag {start_tag} not found in text")
    if end_index == -1:
        raise ValueError(f"End tag {end_tag} not found in text")
    
    json_text = text[start_index + len(start_tag):end_index]
    return json.loads(json_text)

lex_example = {
    "clips": [
        {
            "name": "Jeff Bezos on banning Powerpoint in meetings at Amazon",
            "start": "How do you achieve time where you can focus and truly think through problems?",
            "end": "They can start on time and end on time.",
        },
        {
            "name": "Jeff Bezos: Truth is uncomfortable",
            "start": "What does it take to be the guy or gal who brings up the point",
            "end": "You may want to sort of compensate for that human bias of looking for, you know",
        },
        {
            "name": "Jeff Bezos on Elon Musk",
            "start": "But I spoke to Elon a few times recently about you, about Blue Origin, and he was very positive",
            "end": "And so I, you know, I love that idea.",
        },
        {
            "name": "Jeff Bezos on how to make decisions",
            "start": "If you make the wrong decision, if it's a two way door decision, you walk out the door",
            "end": "And that's because the culture supports that.",
        },
        {
            "name": "Jeff Bezos was going to be a physicist",
            "start": "You were at Princeton with aspirations to be a theoretical physicist.",
            "end": "I feel like that's a Mark Twain quote.",
        },
    ],
    "content": """
# Speaker A
The following is a conversation with Jeff Bezos, founder of Amazon and Blue Origin. This is his first time doing a conversation of this kind and of this length, and as he told me, it felt like we could have easily talked for many more hours. And I'm sure we will. And now a quick few second mention of each sponsor. Check them out in the description. It's the best way to support this podcast. We got notion for team collaboration, policy genius for insurance, masterclass for learning, asleep for naps, and insight tracker for biological data. Choose wisely, my friends. Also, if you want to work with our amazing team, we're always hiring. Go to lexfreedman.com hiring and if you want to get in touch with me for other reasons, I guess suggestions, you can go to lexfreedman.com contact like with aliens, but in this case it's with me. And now onto the full ad reads. There's always no ads in the middle. I try to make this interesting, but if you must, skip them friends, please still check out our sponsors. I enjoy their stuff. Maybe you will too. This show is brought to you by notion, a note taking app that I've been using forever. But it's not just for note taking, it's also for team collaboration. It's been doing that forever, but recently it also has the extra added AI capabilities. With the notion AI tool, obviously everybody's trying to figure out how to integrate the progress with LLMs, the continued progress, the accelerating progress, the boundless progress with LLMs into our productive lives. To me, obviously, the note taking, the putting words onto paper as part of the process of figuring out intellectual puzzles, of thinking through things, designing things, summarizing things, interpreting things, all of that, that's the writing process. And integrating AI into that to help you, almost like a buddy, is obviously empowering. But there's an interface question, how to do that? Well, and to me, notion does that better than any tool I've used so far. Notion AI can now give you instant answers to your questions using information from across your wiki projects, docs and meeting notes. Try notion AI for free when you go to notion.com lex. That's all lowercase notion.com lex to try the power of notionai today. This show is also brought to you by policy genius, a marketplace for finding and buying life insurance. Almost every single conversation I have, in different ways, I ponder, I explore, I deliberate, the simple fact of our mortality, the finiteness of every experience, the human experience, but every experience that makes up the human experience, the good and the bad. I think bringing that up as a topic is important because it is one of the big questions for the introspecting animal that is a human being. For somebody who's trying to figure out the puzzle of the human condition, why does it have to end? Is it good that it has to end? How does the fact of it ending play with the richness of the experience of every moment that we feel when we open our eyes to the beauty of that experience? Those are good questions, but they also put you in the right mindset to explore the other questions. The details of engineering, the details of business and science, all of that are somehow made more visceral, more intensely salient when grounded in the context of pondering one's own mortality. That's why I tried to do it. And I guess PolicyGenius wants you to ponder your mortality and do something about it. A programmatic angle with PolicyGenius you can find life insurance policies that start at just $292 a year for $1 million of coverage. Head to PolicyGenius.com lex or click the link in the description to get your free life insurance quotes and see how much you could save. That's policygenius.com lex. This show is also brought to you by Masterclass. $10 a month gets you an all access pass to watch courses from the best people in the world and their particular thing. That's how you should learn. You should try to find a way to listen to to get close to the people that are the best at a thing that you're interested in. That's not the only way to learn. Textbooks, tutorials, lectures, books about a thing are good, but the doers of the thing reveals something, not just in their explanations, but in how they construct the explanations, how they think about the words that lead to the formation of the explanations. And all of that becomes salient when you just listen to these masterclasses. It's the doers that now have become teachers, but they were doers first anyway. Chris Hatfield. Will Wright. Carlos Santana. Daniel Negrano. Neil Gaiman. Martin Scorsese I would love to talk to Mark Scorsese in this podcast. There's just a lot of classes to choose from. The ones I mentioned are the ones I've personally enjoyed, but maybe there's many others. Maybe you can write to me and recommend ones that were really impactful to you. Get unlimited access to every masterclass, and get an additional 15% off an annual membership@masterclass.com. lexpod that's Masterclass.com lexpod. This episode is also brought to you by eight sleep. I don't know why I'm speaking like this quietly, because when I mention eight sleep, I think about myself napping and the calm peace that overtakes my surrounding environment. When I'm napping on a cold bed with a warm blanket, it's a little sampling of heaven. No matter how I'm feeling, I could be feeling totally shitty about whatever thing. I could be angry. I could be sad. I could be lonely. All of these things, all of the different emotional trajectories that the human mind can take you on, somehow get all resolved. The knots get untied, and everything becomes simple again after a good nap. So take the naps seriously, friends. They are the cure for many of life's ills. And if you want to do your naps the way I do my naps, the right way, you should use eight sleep. Check it out and get special savings when you go to eight sleep.com. this show is also brought to you by Insidetracker, a service I use to track biological data that comes from my body. This complex hierarchical biological machine that provides an infinity of signals, most of which are ignored when we make health, lifestyle, diet, whatever decisions, life decisions. The future is designing systems, machine learning systems, that don't ignore those signals, that leverage those signals, combine them, integrate them with the best scientific work of the day to give you advice on what to do with your life. An insight tracker is taking steps towards that bright to me, bright future. So they're using data from your blood, DNA data, fitness tracker data, all of that to give you lifestyle recommendations. I'm really glad they are pushing this kind of work forward. Get special savings for a limited time when you go to insidetracker.com. lex. This is the Lex agreement podcast. And now, dear friends, here's Jeff Bezos. You spent a lot of your childhood with your grandfather on a ranch here in Texas, and I heard you had a lot of work to do around the ranch. So what's the coolest job you remember doing there? 

# Speaker B
Wow. 

# Speaker A
Coolest, most interesting, most memorable, most interesting. 

# Speaker B
It's a real working ranch, and I spent all my summers on that ranch from age four to 16. And my grandfather was really taking me those in the summers, in the early summers. He was letting me pretend to help on the ranch because of course, a four year old is a burden, not a help. In real life. He was just watching me and taking care of me. He was doing that because my mom was so young. She had me when she was 17, and so he was sort of giving her a break and my grandmother and my grandfather would take me for these summers. But as I got a little older, I actually was helpful on the ranch, and I loved it. I was out there, like, my grandfather had a huge influence on me, huge factor in my life. I did all the jobs you would do on a ranch. I've fixed windmills and laid fences and pipelines and, you know, done all the things that any rancher would do. Vaccinated the animals, everything. But we had a, you know, my grandfather, after my grandmother died, I was about twelve, and I kept coming to the ranch. So then it was just him and me, just the two of us. And he was completely addicted to the soap opera the days of our lives. And we would go back to the ranch house every day around 01:00 p.m. or so to watch days of our lives. Like sands through an hourglass. So are the days of our lives. 

# Speaker A
Just the image of that, the two. 

# Speaker B
Watching slow poppers, big crazy dogs. It was really a very formative experience. But the key thing about it, for me, the great gift I got from it was that my grandfather was so resourceful. You know, he did everything himself. He made his own veterinary tools. He would make needles to suture the cattle up with. He would find a little piece of wire and heat it up and pound it thin and drill a hole in it and sharpen it. So you learn different things on a ranch than you would learn growing up in a city. 

# Speaker A
So self reliance. 

# Speaker B
Yeah, like figuring out that you can solve problems with enough persistence and ingenuity. And my grandfather bought a d six bulldozer, which is a big bulldozer. And he got it for like $5,000 because it was completely broken down. It was like a 1955 caterpillar d six bulldozer. Knew it would have cost, I don't know, more than $100,000. And we spent an entire summer fixing, like, repairing that bulldozer. We'd use mail order to buy big gears for the transmission, and they'd show up, they'd be too heavy to move, so we'd have to build a crane. Just that kind of. That problem solving mentality. He had it so powerfully. He did all of his own. He didn't pick up the phone and call somebody. He would figure it out on his own. He doing his own veterinary work, you know. 

# Speaker A
But just the image of the two you fixing a d six bulldozer and then going in for a little break at 01:00 p.m. to watch soap opera. 

# Speaker B
Laying on the floor, that's how he watched tv. He was a really, really remarkable guy. 

# Speaker A
That's how I imagine Clint Eastwood also in all those westerns, when he's. When he's not doing what he's doing, he's just watching soap operas. All right. I read that you fell in love with the idea of space and space exploration when you were five watching Neil Armstrong walking on the moon. So let me ask you to look back at the historical context and impact of that. So the space race from 1957 to 1969 between the Soviet Union and the US was in many ways epic. It was a rapid sequence of dramatic events. First satellite to space, first human to space for a spacewalk. First uncrewed landing on the moon, then some failures, explosions, deaths on both sides, actually. And then the first human walking on the moon. What are some of the more inspiring moments or insights you take away from that time, those few years that just twelve years? 

# Speaker B
Well, I mean, there's so much inspiring there. One of the great things to take away from that, one of the great von Braun quotes is I have come to use the word impossible with great caution. That's kind of the big story of Apollo, is that things going to the moon was literally an analogy that people used for something that's impossible. Oh, yeah, you'll do that when men walk on the moon. And of course, it finally happened. So I think it was pulled forward in time because of the space race. I think with the geopolitical implications and how much resource was put into it. At the peak, that program was spending two or 3% of gdp on the Apollo program. So much resource. I think it was pulled forward in time. We did it ahead of when we should have done it in that way. It's also a technical marvel. I mean, it's truly incredible. It's the 20th century version of building the pyramids or something. It's an achievement that because it was pulled forward in time and because it did something that had previously been thought impossible, it rightly deserves its place in the pantheon of great human achievements. 

# Speaker A
And, of course, you named the projects, the rockets that blue Origin is working on after some of the folks involved. I don't understand why I didn't say new Gagarin is that there's an american. 

# Speaker B
Bias in the naming. I apologize. 

# Speaker A
Very strange. Lex asking for a friend. Clarify. 

# Speaker B
I'm a big fan of Gagarin snow. In fact, I think his first words in space, I think, are incredible. He purportedly said, my God, it's blue. And that really drives home. No one had seen the earth from space. No one knew that we were on this blue planet. No one knew what it looked like from out there, and Gagarin was the first person to see it. 

# Speaker A
One of the things I think about is how dangerous those early days were for Gagarin, for Glenn, for everybody involved, like how big of a risk they. 

# Speaker B
Were all, they were taking huge risks. I'm not sure what the Soviets thought about Gagarin's flight, but I think that the Americans thought that the Alan Shepard flight, the flight that New Shepard is named after, the first American in space. He went on his suborbital flight. They thought he had about a 75% chance of success. So that's a pretty big risk, a 25% risk. 

# Speaker A
It's kind of interesting that Alan Shepard is not quite as famous as John Glenn. So for people who don't know, Alan Shepard is the first astronaut, the first American in space. American in suborbital flight. 

# Speaker B
Correct. 

# Speaker A
And then the first orbital flight, that. 

# Speaker B
John Glenn is the first American to orbit the earth. By the way, I have the most charming, sweet, incredible letter from John Glenn, which I have framed and hang on my office wall. 

# Speaker A
What did he say? 

# Speaker B
Where he tells me how grateful he is that we have named New Glenn after him, and they sent me that letter about a week before he died. And it's really an incredible. It's also a very funny letter he's writing, and he says, this is a letter about new Glenn from the original Glenn. And he's got a great sense of humor, and he's very happy about it and grateful. It's very sweet. 

# Speaker A
Does he say, ps, don't mess this up, or is it. No, he doesn't make me look good. 

# Speaker B
He doesn't do that. But, John, wherever you are, we got you covered. 

# Speaker A
Good. So back to maybe the big picture of space. When you look up at the stars and think big, what do you hope is the future of humanity hundreds, thousands of years from now, out in space? 

# Speaker B
I would love to see a trillion humans living in the solar system. If we had a trillion humans, we would have, at any given time, 1000 Mozarts and 1000 Einsteins. Our solar system would be full of life and intelligence and energy, and we can easily support a civilization that large with all of the resources in the solar system. 

# Speaker A
So what do you think? That looks like giant space stations. 

# Speaker B
Yeah. The only way to get to that vision is with giant space stations. The planetary surfaces are just way too small. So you can. I mean, unless you turn them into giant space stations or something. But, yeah, we will take materials from the moon and from near Earth objects and from the asteroid belt and so on, and will build giant O'Neill style colonies, and people will live in those. And they have a lot of advantages over planetary surfaces. You can spin them to get normal Earth gravity. You can put them where you want them. I think most people are going to want to live near Earth, not necessarily in Earth orbit, but in, you know, Earth, but near Earth vicinity orbits. And so they can move relatively quickly back and forth between their station and Earth. So I think a lot of people, especially in the early stages, are not going to want to give up Earth altogether. 

# Speaker A
They go to Earth for vacation. 

# Speaker B
Yeah, same way that you might go to Yellowstone National park for vacation. And people get to choose whether they live on Earth or whether they live in space, but they'll be able to use much more energy and much more material resource in space than they would be able to use on Earth. 

# Speaker A
One of the interesting ideas you had is to move the heavy industry away from Earth. So people sometimes have this idea that somehow space exploration is in conflict with the celebration of the planet Earth, that we should focus on preserving Earth. And basically your idea is that space travel and space exploration is a way to preserve Earth. 

# Speaker B
Exactly. This planet. We've sent robotic probes to all the planets. We know that this is the good one. 

# Speaker A
Not to play favorites or anything. 

# Speaker B
Earth really is the good planet. It's amazing, the ecosystem we have here, all of the life and the lush plant life and the water resources, everything. This planet is really extraordinary. And, of course, we evolved on this planet, so, of course, it's perfect for us, but it's also perfect for all the advanced life forms on this planet, all the animals and so on. And so this is a gem. We do need to take care of it. And as we enter the Anthropocene, as we get, as we humans have gotten so sophisticated and large and impactful, as we stride across this planet, that is going to. As we continue, we want to use a lot of energy. We want to use a lot of energy per capita. We've gotten amazing things. We don't want to go backwards. If you think about the good old days, they're mostly an illusion in almost every way. Life is better for almost everyone today than it was, say, 50 years ago or 100 years. We live better lives, by and large, than our grandparents did and their grandparents did, and so on. And you can see that in global illiteracy rates, global poverty rates, global infant mortality rates, like almost any metric you choose, we're better off than we used to be, and we get antibiotics and all kinds of life saving, medical care and so on and so on. And there's one thing that is moving backwards and it's the natural world. So it is a fact that 500 years ago, pre industrial age, the natural world was pristine. It was incredible. And we have traded some of that pristine beauty for all of these other gifts that we have as an advanced society. And we can have both. But to do that, we have to go to space. And all of this, really the most fundamental measure is energy usage per capita. And when you look at, you do want to continue to use more and more energy. It is going to make your life better in so many ways, but that's not compatible ultimately with living on a finite planet. And so we have to go out into the solar system. And really you could argue about when you have to do that, but you can't credibly argue about whether you have to do that. 

# Speaker A
Eventually we have to do that. 

# Speaker B
Exactly. 

# Speaker A
So you don't often talk about it. But let me ask you on that topic about the blue ring and the orbital reef space infrastructure projects. What's your vision for these? 

# Speaker B
So blue ring is a very interesting spacecraft that is designed to take up to 3000 payload up to geosynchronous orbit or in lunar vicinity. It has two different kinds of propulsion. It has chemical propulsion and it has electric propulsion. And so you can use blue ring in a couple different ways. You can slowly move, let's say up to geosynchronous orbit using electric propulsion. That might take 100 days or 150 days, depending on how much mass you're carrying, and reserve your chemical propulsion so that you can change orbits quickly in geosynchronous orbit. Or you can use the chemical propulsion first to quickly get up to geosynchronous and then use your electrical propulsion to slowly change your geosynchronous orbit. Blue ring has a couple of interesting features. It provides a lot of services to these payloads. So it could be one large payload or it can be a number of small payloads. And it provides thermal management, it provides electric power, it provides compute, provides communications. And so when you design a payload for blue ring, you don't have to figure out all of those things on your own. So kind of radiation tolerant. Compute is a complicated thing to do. And so we have an unusually large amount of radiation tolerant compute on board blue ring. And your payload can just use that when it needs to. So it's sort of all these services, it's like a set of APIs. It's a little bit like Amazon Web services. But for space payloads that need to move about an earth vicinity or lunar vicinity. 

# Speaker A
Awss. Okay, so compute in space. So you get a giant chemical rocket to get a payload all torba, and then you have these admins that show up this boo ring thing that manages various things like compute. 

# Speaker B
Exactly. And it can also provide transportation and move you around to different orbits, including humans. You think so? But blue ring is not designed to move humans around. It's designed to move payloads around. So we're also building a lunar lander, which is of course designed to land humans on the surface of the moon. 

# Speaker A
I'm going to ask you about that, but let me actually just a step back to the old days. You were at Princeton with aspirations to be a theoretical physicist. 

# Speaker B
Yeah. 

# Speaker A
What attracted you to physics? And why did you change your mind and not become why you're not Jeff Bezos, the famous theoretical physicist? 

# Speaker B
So I loved physics and I studied physics and computer science, and I was proceeding along the physics path. I was planning to major in physics and I wanted to be a theoretical physicist. And the computer science was sort of something I was doing for fun. I really loved it and I was very good at the programming and doing those things, and I enjoyed all my computer science classes immensely, but I really was determined to be a theoretical physicist. That's why I went to Princeton in the first place. It was definitely, and then I realized I was going to be a mediocre theoretical physicist. And there were a few people in my classes, like in quantum mechanics and so on, who they could effortlessly do things that were so difficult for me. And I realized, like, you know, there are a thousand ways to be smart and to be a really, you know, theoretical physics is not one of those fields where the, you know, only the top few percent actually move the state of the art forward. It's one of those things where you have to be really just, your brain has to be wired in a certain way. And there was a guy named one of these people who convinced me. He didn't mean to convince me, but just by observing him, he convinced me that I should not try to be a theoretical physicist. His name was Yosanta, and Yosanta was from Sri Lanka, and he was one of the most brilliant people I'd ever met. My friend Joe and I were working on a very difficult partial differential equations problem set one night, and there was one problem that we worked on for 3 hours and we made no headway whatsoever. And we looked up at each other at the same time and we said, yosanta, so we went to Yosanta's dorm room, and he was there. He was almost always there. And we said, yosanta, we're having trouble solving this partial differential equation. Would you mind taking a look? And he said, of course, by the way, he was the most humble, most kind person. And so he took our, he looked at our problem and he stared at it for just a few seconds, maybe 10 seconds, and he said, cosine. And I said, what do you mean, Yosanto, what do you mean, cosine? He said, that's the answer. And I said, no, no, no. Come on. And he said, let me show you. And he took out some paper, and he wrote down three pages of equations. Everything canceled out. And the answer was cosine. And I said, yosanta, did you do that in your head? And he said, no, that would be impossible. A few years ago, I solved a similar problem, and I could map this problem onto that problem. And then it was immediately obvious that the answer was cosine. I had a few. You know, you have an experience like that, you realize maybe being a theoretical physicist isn't sure, isn't what the universe wants you to be. And so I switched to computer science, and that worked out really well for me. I enjoy it. I still enjoy it today. 

# Speaker A
Yeah. There's a particular kind of intuition. You need to be a great physicist applied to physics. 

# Speaker B
I think the mathematical skill required today is so high, you have to be a world class mathematician to be a successful theoretical physicist today. And it's not, you know, you probably need other skills, too. Intuition, lateral thinking, and so on. But without the, without just top notch math skills, you're unlikely to be successful. 

# Speaker A
And visualization skill, you have to be able to really kind of do these kinds of thought experiments. And if you want to, truly great creativity. Actually, Walter Isaacson writes about you. It puts you on the same level as Einstein. 

# Speaker B
That's very kind. I'm an inventor. If you want to boil down what I am, I'm really an inventor. And I look at things and I can come up with atypical solutions, and, you know, and then I can create a hundred such atypical solutions for something. 99 of them may not survive, you know, scrutiny, but one of those 100 is like, hmm, maybe there is. Maybe that might work, and then you can keep going from there. So that kind of lateral thinking, that kind of inventiveness in a high dimensionality space where the search space is very large, that's where my inventive skills come. That's the thing I self identify as an inventor more than anything else. 

# Speaker A
Yeah. And he describes in all kinds of different ways Walter Isaacson does that creativity combined with childlike wander that you've maintained still to this day, all of that combined together, is there like if you were to study your own brain introspect, how do you think, what's your thinking process like? We'll talk about the writing process of putting it down on paper, which is quite rigorous and famous at Amazon. But how do you, when you sit down, maybe alone, maybe with others, and thinking through this high dimensional space and looking for creative solutions, creative paths forward, is there something you could say about that process? 

# Speaker B
It's such a good question, and I honestly don't know how it works. If I did, I would try to explain it. I know it involves lots of wandering. So when I sit down to work on a problem, I know I don't know where I'm going. So to go in a straight line, to be efficient, efficiency and invention are sort of at odds, because invention, real invention, not incremental improvement. Incremental improvement is so important in every endeavor. And everything you do, you have to work hard on also just making things a little bit better. But I'm talking about real invention, real lateral thinking that requires wandering, and you have to give yourself permission to wander. I think a lot of people, they feel like wandering is inefficient. And when I sit down at a meeting, I don't know how long the meeting is going to take if we're trying to solve a problem, because if I did, then I'd already. I know there's some kind of straight line that we're drawing to the solution. The reality is we may have to wander for a long time. And I do like group invention. I think there's really nothing more fun than sitting at a whiteboard with a group of smart people and spitballing and coming up with new ideas and objections to those ideas, and then solutions to the objections and going back and forth. So, like, sometimes you wake up with an idea and the middle of the night, and sometimes you sit down with a group of people and go back and forth, and both things are really pleasurable. 

# Speaker A
And when you wander, I think one key thing is to notice a good idea and to maybe to notice the kernel of a good idea, maybe pull at that string, because I don't think good ideas come fully formed 100% right. 

# Speaker B
In fact, when I come up with what I think is a good idea and it survives kind of the first level of scrutiny, you know, that I do in my own head, and I'm ready to tell somebody else about the idea. I will often say, look, it is going to be really easy for you to find objections to this idea, but work with me. 

# Speaker A
There's something there. 

# Speaker B
There's something there, and that is intuition, because it's really easy to kill new ideas in the beginning because they do have so many, so many easy objections to them. So you need to kind of forewarn people and say, look, I know it's going to take a lot of work to get this to a fully formed idea. Let's get started on that. It'll be fun. 

# Speaker A
So you got that ability to say cosine in you somewhere after all. Maybe not on math in a different domain. 

# Speaker B
There are a thousand ways to be smart, by the way. And that is a really, like, when I go around, you know, and I meet people, I'm always looking for the way that they're smart, and you find it is. That's one of the things that makes the world so interesting and fun is that it is not. It's not like IQ is a single dimension. There are people who are smart in such unique ways. 

# Speaker A
Yeah, you just gave me a good response when somebody calls me an idiot on the Internet. You know, there's a thousand ways to be smart, sir. 

# Speaker B
Well, they might tell you. Yeah, but there are millions of ways to be done. Yeah. 

# Speaker A
I feel like that's a Mark Twain quote. Okay. All right. You gave me an amazing tour of blue origin rocket factory and launch complex in the historic Cape Canaveral. That's where new Glenn, the. The big rocket we talked about, is being built and will launch. Can you explain what the new Glenn rocket is and tell me some interesting technical aspects of how it works? 

# Speaker B
Sure. New Glenn is a very large, heavy lift launch vehicle. It'll take about 45 metric tons to Leo, a very large class. It's about half the thrust, a little more than half the thrust of the Saturn V rocket. So it's about 3.9 million pounds of thrust on liftoff. The booster has seven be four engines. Each engine generates a little more than 550,000 pounds of thrust. The engines are fueled by liquid natural gas, liquefied natural gas, lng as the fuel and lox as the oxidizer. The cycle is an ox rich stage combustion cycle. It's a cycle that was really pioneered by the Russians. It's a very good cycle. And that engine is also going to power the first stage of the Vulcan rocket, which is the United launch alliance rocket. Then the second stage of new Glenn is powered by two be three U engines, which is an upper stage variant of our new Shepard liquid hydrogen engine. So the be three U has 160,000 pounds of thrust, so two of those 320,000 pounds of thrust. And hydrogen is a very good propellant for upper stages because it has very high isp. It's not a great propellant, in my view, for booster stages, because the stages then get physically so large. Hydrogen has very high Isp, but liquid hydrogen is not dense at all. So to store liquid hydrogen, you need to store many thousands of pounds of liquid hydrogen. Your tanks, your liquid hydrogen tank gets very large. So you really get more benefit from the higher ISP, the specific impulse. You get more benefit from the higher specific impulse on the second stage. And that stage carries less propellant, so you don't get such geometrically gigantic tanks. The Delta IV is an example of a vehicle that is all hydrogen. The booster stage is also hydrogen. And I think that it's a very effective vehicle, but it never was very cost effective. So it's operationally very capable, but not very cost effective. 

# Speaker A
So size is also costly. 

# Speaker B
Size is costly. So it's interesting. Rockets love to be big. Everything works better. 

# Speaker A
What do you mean by that? You've told me that before. It sounds epic, but what's it, I. 

# Speaker B
Mean, when you look at the kind of the physics of rocket engines, and also when you look at parasitic mass, it doesn't. If you have, let's say you have an avionics system, so you have a guidance and control system that is going to be about the same mass and size for a giant rocket as it is going to be for a tiny rocket. And so that's just parasitic mass. That is very consequential if you're building a very small rocket, but is trivial if you're building a very large rocket. So you have the parasitic mass thing, and then if you look at, for example, rocket engines have turbo pumps. They have to pressurize the fuel and the oxidizer up to a very high pressure level in order to inject it into the thrust chamber where it burns. And those pumps, all rotating machines, in fact, get more efficient as they get larger. So really tiny turbo pumps are very challenging to manufacture. And any kind of gaps, you know, are like between the housing, for example, and the rotating impeller that pressurizes the fuel, there has to be some gap there. You can't have those parts scraping against one another, and those gaps drive inefficiencies. And so, you know, if you have a very large turbo pump, those gaps and percentage terms end up being very small. And so there's a bunch of things that you end up loving about having a large rocket and that you end up hating for a small rocket. But there's a giant exception to this rule, and it is manufacturing. So manufacturing large structures is very, very challenging. It's a pain in the butt. And so it's just, if you're making a small rocket engine, you can move all the pieces by hand, you can assemble it on a table, one person can do it. You don't need cranes and heavy lift operations and tooling and so on and so on. When you start building big objects, infrastructure, civil infrastructure, just like the launch pad and all this. We went and visited, I took you to the launch pad and you can see it's so monumental and so just these things become major undertakings, both from an engineering point of view, but also from a construction and cost point of. 

# Speaker A
View, and even the foundation of the launch pad. I mean, this is Florida, isn't it? Like swampland, like how deep you have. 

# Speaker B
To go at Cape Canaveral. In fact, most ocean, you know, most launch pads are on beaches somewhere in the ocean side, because you want to launch over water for safety reasons. Yes. You have to drive pilings, dozens and dozens and dozens of pilings, 5100, 150ft deep, to get enough structural integrity for these very large. Yes. These turned into major civil engineering projects. 

# Speaker A
I just have to say, everything about that factory is pretty badass. You said tooling. The bigger it gets, the more epic it is. 

# Speaker B
It does make it epic. It's fun to look at. It's extraordinary. 

# Speaker A
It's humbling also, because humans are so small compared to it. 

# Speaker B
We are building these enormous machines that are harnessing enormous amounts of chemical power in very, very compact packages. It's truly extraordinary. 

# Speaker A
But then there's all the different components, the materials involved. Is there something interesting that you can describe about the materials that comprise the rocket? So it has to be as light as possible, I guess, whilst withstanding the heat and the harsh conditions. 

# Speaker B
Yeah, I play a little kind of game sometimes with other rocket people that I run into. Where what are the things that would amaze the 1960s engineers? What's changed? Because, surprisingly, some of rocketry's greatest hits have not changed. They are still. They would recognize immediately a lot of what we do today. And it's exactly what they pioneered back in the sixties. But a few things have changed. The use of carbon composites is very different today. We can build very sophisticated. You saw our carbon tape laying machine that builds the giant fairings, and we can build these incredibly light, very stiff fairing structures out of carbon composite material that they could not have dreamed of. I mean, the efficiency, the structural efficiency of that material is so high compared to any metallic material you might use or anything else. So that's one. Aluminum, lithium. And the ability to friction stir weld. Aluminum, lithium. Do you remember the friction stir welding that I showed you? This is a remarkable technology. This invented decades ago, but has become very practical over just the last couple of decades. Instead of using heat to weld two pieces of metal together, it literally stirs the two pieces. There's a pin that rotates at a certain rate, and you put that pin between the two plates of metal that you want to weld together, and then you move it at a very precise speed, and instead of heating the material, it heats it a little bit because of friction, but not very much. You can literally, immediately after welding, with stir friction welding, you can touch the material and it's just barely warm. It literally stirs the molecules together. It's quite extraordinary. 

# Speaker A
Relatively low temperature, and I guess high temperature is what makes them the. That's the, that makes it a weak point. 

# Speaker B
Exactly. So with traditional welding techniques, you may have whatever the underlying strength characteristics of the material are, you end up with weak regions where you weld. And with friction stir welding, the welds are just as strong as the bulk material. So it really allows you. And so because when you're, you know, let's say you're building a tank that you're going to pressurize, you know, a large, you know, liquid natural gas tank for our, for our booster stage, for example. You know, if you are welding that with traditional methods, you have to size those weld lands, the thickness of those pieces with that knockdown for whatever damage you're doing with the weld. And that's going to add a lot of weight to that tank. 

# Speaker A
I mean, even just looking at the fairings, the result of that, the complex shape that it takes and, like, what it's supposed to do is kind of incredible because people don't know it's on top of the rocket. It's going to fall apart. That's its task. But it has to stay strong sometimes and then disappear when it needs to. 

# Speaker B
That's right. 

# Speaker A
Which is a very difficult task. 

# Speaker B
Yes. When you need something that needs to have 100% integrity until it needs to have 0% integrity, it needs to stay attached until it's ready to go away, and then when it goes away. It has to go away completely. You use explosive charges for that. And so it's a very robust way of separating structure when you need to exploding. Yeah. Little tiny bits of explosive material, and it'll sever the whole connection. 

# Speaker A
So if you want to go from 100% structural integrity to zero as fast. 

# Speaker B
As possible, explosives, use explosives. 

# Speaker A
The entirety of this thing is so badass. Okay, so we're back to the two stages. So the first stage is reusable. 

# Speaker B
Yeah. Second stage is expendable. Second stage is liquid hydrogen, liquid oxygen. So we get take advantage of the higher specific impulse. The first stage lands downrange on a landing platform in the ocean, comes back for maintenance and get ready to do the next mission. 

# Speaker A
I mean, there's a million questions, but also, is there a path towards reusability for the second stage? 

# Speaker B
There is, and we know how to do that. Right now we're going to work on manufacturing that second stage to make it as inexpensive as possible. Sort of two paths for a second stage. Make it reusable or work really hard to make it inexpensive so you can afford to expend it. And that trade is actually not obvious. Which one is better even in terms of cost? 

# Speaker A
Even like time, even in terms of. 

# Speaker B
I'm talking about costs, space. Getting into orbit is a solved problem. We solved it back in the fifties and sixties, making it sound easy. The only interesting problem is dramatically reducing the cost of access to orbit, which is if you can do that, you open up a bunch of new endeavors that lots of startup companies, everybody else can do. So that's one of our missions, is to be part of this industry and lower the cost to orbit so that there can be a kind of a renaissance, a golden age of people doing all kinds of interesting things in space. 

# Speaker A
I like how you said getting to orbit is a solved problem. It's just, the only interesting thing is reducing the cost. You know, you can describe every single problem facing human civilization that way. The physicists will say everything is a solved problem. We've solved everything. The rest is just. Rutherford said that it's just stamp collecting, it's just the details. Some of the greatest innovations, interventions, and, you know, brilliance is in that cost reduction stage, right? And you, you've had a long career of cost reduction, for sure. 

# Speaker B
You know, when you. What does cost reduction really mean? It means inventing a better way. 

# Speaker A
Yeah, exactly right. 

# Speaker B
And when you invent a better way, you make the whole world richer. So, you know, whatever it was, I don't know how many thousands of years ago somebody invented the plow. And when they invented the plow, they made the whole world richer because they made farming less expensive. And so it is a big deal to invent better ways. That's how the world gets richer. 

# Speaker A
So what are some of the biggest challenges on the manufacturing side and the engineering side that you're facing in working to get to the first launch of new Glenn? 

# Speaker B
The first launch is one thing, and we'll do that in 2024 coming up in this coming year. The real thing that's the bigger challenge is making sure that our factory is efficiently manufacturing at rate, so rate production. So consider, if you want to launch new Glenn, you know, 24 times a year, you need to manufacture a upper stage since they're expendable every, you know, twice a month. You need to do one every two weeks. So you need to be, you need to have all of your manufacturing facilities and processes and inspection techniques and acceptance tests and everything operating at rate and rate. Manufacturing is at least as difficult as designing the vehicle in the first place. And the same thing. So every, every upper stage has two be three U engines. So those engines you know, you need, if you're going to launch the vehicle twice a month, you need four engines a month. So you need an engine every week. So you need to be, that engine needs to be being produced at rate. And there's all of the things that you need to do that. All the right machine tools, all the right fixtures, the right people process, etcetera. So it's one thing to build a first article, to launch new Glenn for the first time, you need to produce a first article. But that's not the hard part. The hard part is everything that's going on behind the scenes to build a factory that can produce new glens at rate. 

# Speaker A
So the first one is produced in a way that enables the production of the second, third and the fourth and the fifth and 6th. 

# Speaker B
You could think of the first article as kind of pushing. It pushes all of the rate manufacturing technology along. In other words, it's kind of the, it's the test article in a way that's testing out your manufacturing technologies. 

# Speaker A
The manufacturing is the big challenge. 

# Speaker B
Yes. I don't want to make it sound like any of it is easy. The people who are designing the engines and all this, all of it is hard for sure. But the challenge right now is driving really hard to get to rate manufacturing, to do that in an efficient way. Again, back to our cost point. If you get to rate manufacturing in an inefficient way, you havent really solved the cost problem. And maybe you havent really moved the state of the art forward. All this has to be about moving the state of the art forward. There are easier businesses to do. I always tell people, look, if you are trying to make money, start a salty snack food company or something, you. 

# Speaker A
Write that idea down. 

# Speaker B
Make the Lex Friedman potato chips. You know this, don't say it. 

# Speaker A
People are going to steal it. But yeah, it's hard. 

# Speaker B
You see what I'm saying? It's like, there's nothing easy about this business and, but, but it's its own reward. It's, it's, it's, it's fascinating, it's worthwhile, it's meaningful. And so, you know, I, you know, not, I don't want to pick on salty snack food companies, but I think it's, it's less meaningful. You know, at the end of the day, you're not going to, you're not going to have accomplished something amazing. Yeah, there's, even if you do make a lot of money on it. 

# Speaker A
Yeah. There's something fundamentally different about the quote unquote, business of space exploration. Yeah, for sure. It's a grand project of humanity. 

# Speaker B
Yes, it's one of humanity's grand challenges. And especially as you look at going to the moon and going to Mars and building giant O'Neill colonies and unlocking all the things, you know, I won't live long enough to see the fruits of this, but the fruits of this come from building a road to space, getting the infrastructure. I'll give you an analogy. When I started Amazon, I didn't have to develop a payment system. It already existed. It was called the credit card. I didn't have to develop a transportation system to deliver the packages that already existed. It was called the postal service and Royal Mail and Deutsche Post and so on. So all this heavy lifting infrastructure was already in place. And I could stand on its shoulders. And that's why when you look at the Internet, by the way, another giant piece of infrastructure that was around in the early, I'm taking you back to like 1994, people were using dial up modems and it was piggybacking on top of the long distance phone network. That's how the Internet, that's how people were accessing servers and so on. And again, if that hadn't existed, it would have been hundreds of billions of capex to put that out there. No startup company could have done that. And so the problem, you see, if you look at the dynamism in the Internet space over the last 20 years, it's because you see, like, two kids in a dorm room could start an Internet company that could be successful and do amazing things because they didn't have to build heavy infrastructure. It was already there. And that's what I want to do. I take my Amazon winnings and use that to build heavy infrastructure so the next generation, the generation that's my children and their children, those generations can then use that heavy infrastructure. Then there'll be space entrepreneurs who start in their dorm room. That will be a marker of success. When you can have a really valuable space company started in a dorm room, then we know that we've built enough infrastructure so that ingenuity and imagination can really be unleashed. I find that very exciting. 

# Speaker A
They will, of course, as kids do, take all of this hard infrastructure building for granted. Of course, the entrepreneurial spirit, that's an. 

# Speaker B
Inventor'S greatest dream is that their inventions are so successful that they are one day taken for granted. Nobody thinks of Amazon is an invention anymore. Nobody thinks of customer reviews as an event. We pioneered customer reviews, but now they're so commonplace. Same thing with one click shopping and so on. But that's a compliment. That's how, you know, you invent something that's so used, so beneficially used by so many people that they take it for granted. 

# Speaker A
I don't know about nobody. Every time I use Amazon, I'm still amazed. How does this work? 

# Speaker B
That proves you're a very curious explorer. 

# Speaker A
All right. All right. Back to rockets timeline. You said 2024. As it stands now, are both the first test launch and the launch of escapade explorers to Mars still possible? 

# Speaker B
Yeah, I think so. For sure. The first launch and then we'll see if escapade goes on that or not. I think that the first launch for sure, and I hope escapade to hope. Well, I just don't know which mission it's actually going to be slated on. So we also have other things that might go on that first mission. 

# Speaker A
Oh, I got it. But you're optimistic that the launches will still. 

# Speaker B
Oh, the first launch. I'm very optimistic that the first launch of new Glenn will be in 2024. And I'm just not 100% certain what payload will be on that first launch. 

# Speaker A
Are you nervous about it? 

# Speaker B
Are you kidding? I'm extremely nervous about it. 

# Speaker A
Oh, man. 

# Speaker B
100%. Every launch I go to for New Shepard, for other vehicles, too, I'm always nervous for these launches. But, yes, for sure, a first launch to have no nervousness about that would be some sign of derangement, I think. 

# Speaker A
Well, I got to visit launch, but it's pretty, I mean, that big. 

# Speaker B
You know, we have done a tremendous amount of ground testing, a tremendous amount of simulation. So, you know, a lot of the problems that we might find in flight have been resolved, but there are some problems you can only find in flight. So, you know, cross your fingers. I guarantee you you'll have fun watching it no matter what happens. 

# Speaker A
100%. Thing is fully assembled and comes up. 

# Speaker B
Yeah. The transporter erector. Just transporter erector. For a rocket of this scale. 

# Speaker A
Yeah. 

# Speaker B
Is extraordinary. 

# Speaker A
That's an incredible machine. 

# Speaker B
Vehicle. Travels out horizontally and then kind of. Yeah, you know, comes up over a few hours. Yeah. It's a beautiful thing to watch. 

# Speaker A
Speaking of which, if that makes you nervous, I don't know if you remember, but you were aboard new Shepard on its first crude flight. How was that experience? Were you, were you terrified then? 

# Speaker B
You know, strangely, I wasn't. 

# Speaker A
You know, I ride the rocket. 

# Speaker B
I've watched other people ride in the rocket, and I'm more nervous than when I was inside the rocket myself. It was a difficult conversation to have with my mother when I told her I was going to go on the first one, and not only was I going to go, but I was going to bring my brother, too. This is a tough conversation to have with a mom. 

# Speaker A
There's a long pause. 

# Speaker B
She's like, both of you. It was an incredible experience. And we were laughing inside the capsule, and, you know, we're not nervous. The people on the ground were very nervous for us. It was actually one of the most emotionally powerful parts of the experience was not what happened even before the flight. At 430 in the morning. Brother and I are getting ready to go to the launch site, and Lauren is going to take us there in her helicopter, and we're getting ready to leave. And we go outside, outside the ranch house there in West Texas where the launch facility is, and all of our family, my kids and my brother's kids and our, you know, our parents and close friends are assembled there and they're saying goodbye to us, but they're kind of saying maybe they think they're saying goodbye to us forever. And, you know, we might not have felt that way, but it was obvious from their faces how nervous they were that they felt that way. And it was sort of powerful because it allowed us to see. It was almost like attending your own memorial service or something, like you could feel how loved you were in that moment. And it was really amazing. Yeah. 

# Speaker A
And, I mean, there's just an epic nature to it, too. 

# Speaker B
The ascent, the floating zero gravity. I'll tell you something very interesting. Zero gravity feels very natural. I don't know if it's because we, you know, it's like return to the womb. 

# Speaker A
He just confirmed you're an alien. But I think that's what, I think that's what you just said. 

# Speaker B
It feels so natural to be in zero g. It was really interesting. And then when people talk about the overview effect and seeing Earth from space, I had that feeling very powerfully. I think everyone did. You see how fragile the earth is. If you're not an environmentalist, it will make you one. The great Jim Lovell quote, you know, he looked back at the earth from space and he said he realized, you don't go to heaven when you die. You go to heaven when you're born. And it's just, you know, that's the feeling that people get when they're in space. You see all this blackness, all this nothingness. And there's one gem of life, and it's Earth. 

# Speaker A
It is a gem. What? You know, you've talked a lot about decision making throughout your time with Amazon. What was that decision like to ride, to be the first to ride new shepherd? Like, what, just before you talk to your mom? 

# Speaker B
Yeah. 

# Speaker A
Like, the pros and cons, actually, as one human being, as a leader of a company on all fronts, like, what was that decision making like? 

# Speaker B
I decided that, first of all, I knew the vehicle extremely well. I know the team who built it. I know the vehicle. I'm very comfortable with the escape system. We put as much effort into the escape system on that vehicle as we put into all the rest of the vehicle combined. It's one of the hardest pieces of engineering in the entire new Shepard architecture. 

# Speaker A
Can you actually describe what do you mean by escape system, what's involved? 

# Speaker B
We have a solid rocket motor in the base of the crew capsule, so that if anything goes wrong on ascent, you know, while the main rocket engine is firing, we can ignite this solid rocket motor in the base of the crew capsule and escape from the booster. It's a very challenging system to build, design, validate, test all of these things. It is the reason that I am comfortable letting anyone go on New Shepard. So the booster is as safe and reliable as we can make it. But we are harnessing, whenever you are talking about rocket engines, I dont care what rocket engine youre talking about. You are harnessing such vast power in such a small, compact, geometric space. The power density is so enormous that it is impossible to ever be sure that nothing will go wrong. And so the only way to improve safety is to have an escape system. And, you know, and historically, rockets, human rated rockets, have had escape systems only. The space shuttle did not, and but Apollo had one. All of the previous Gemini, et cetera, they all had escape systems. And we have, on New Shepard, unusual escapes. Most escape systems are towers. We have a pusher escape system. So the solid rocket motor is actually embedded in the base of the crew capsule, and it pushes, and it's reusable in the sense that if we don't use it, so if we have a nominal emission, we land with it. The tower systems have to be ejected at a certain point in the mission, and so they get wasted even in a nominal mission. And so, again, you know, cost really matters on these things. So we figured out how to have the escape system be a reusable in the event that it's not used, it can reuse it and have it be a pusher system. It's a very sophisticated thing. So I knew these things. You asked me about my decision to go, and so I know the vehicle very well. I know the people who designed it. I have great trust in them and in the engineering that we did. And I thought to myself, look, if I am not ready to go, then I wouldn't want anyone to go. A tourism vehicle has to be designed, in my view, to be as safe as one can make it. You can't make it perfectly safe. It's impossible. But you have to. People will do things. People take risk. They climb mountains, they skydive, they do deep underwater scuba diving and so on. People are okay taking risk. You can't eliminate the risk. But it is something because it's a tourism vehicle. You have to do your utmost to eliminate those risks. And I felt very good about the system. I think it's one of the reasons I was so calm inside. Maybe others weren't as calm. They didn't know as much about it as I did. 

# Speaker A
Who was in charge of engaging in this system? 

# Speaker B
It's automated. 

# Speaker A
Okay. 

# Speaker B
The escape system is visualizing is completely automated. Automated is better because it can react so much faster. 

# Speaker A
So, yeah, for tourism, rockets safety is a huge, huge, huge priority for space exploration also. But a little, you know, a delta less. 

# Speaker B
Yes. I mean, I think for, you know, if you're doing, you know, there are human activities where we tolerate more risk. If you're saving somebody's life, if you are engaging in real exploration, these are things where I personally think we would accept more risk, in part because you have to. 

# Speaker A
Is there a part of you that's frustrated by the rate of progress in blue Origin? 

# Speaker B
Blue origin needs to be much faster. And it's one of the reasons that I left my role as the CEO of Amazon a couple of years ago. I wanted to come in and Blue Origin needs me right now. When I was the CEO of Amazon, my point of view on this is if I'm the CEO of a publicly traded company, it's going to get my full attention. And I really, it's just how I think about things. It was very important to me. I felt I had an obligation to all the stakeholders at Amazon to do that. And so having turned the CEO, I was still the executive chair there, but I turned the CEO role over. And the reason, the primary reason I did that is so that I could spend time of origin adding some energy, some sense of urgency. We need to move much faster and we're going to. 

# Speaker A
What are the ways to speed it up? You've talked a lot of different ways to sort of an Amazon removing barriers for progress or distributing, making everybody autonomous and self reliant, all those kinds of things. Does that apply at blue Origin or. 

# Speaker B
Is it does apply and I'm leading this directly. We are going to become the world's most decisive company across any industry. And so, you know, at Amazon for, you know, ever since the beginning, I said we're going to become the world's most customer obsessed company. And no matter the industry like people, one day people are going to come to Amazon from the healthcare industry and want to know how did you guys, how do you, how are you so customer obsessed? How do you actually not just pay lip service but actually do that? And from all different industries should come on to study us to see how we accomplish that. And the analogous thing at Blue Origin and will help us move faster is we are going to become the world's most decisive company. We're going to get really good at taking appropriate technology risk, making those decisions quickly, being bold on those things and having the right culture that supports that. You need people to be ambitious, technically ambitious. You know, if there are five ways to do something, we'll study them, but let's study them very quickly and make a decision. We can always change our mind. It doesn't, you know, changing your mind. I talk about one way doors and two way doors. Most decisions are two way doors. 

# Speaker A
Can you explain that? Because I love that metaphor. 

# Speaker B
If you make the wrong decision, if it's a two way door decision, you walk out the door, you pick a door. You walk out, you spend a little time there, it turns out to be the wrong decision. You can come back in and pick another door. Some decisions are so consequential and so important and so hard to reverse that they really are one way door decisions. You go in that door, you're not coming back. And those decisions have to be made very deliberately, very carefully. If you can think of yet another way to analyze the decision, you should slow down and do that. So when I was CEO of Amazon, I often found myself in the position of being the chief slowdown officer because somebody would be bringing me a one way door decision. I can think of three more ways to analyze that. So let's go do that because we are not going to be able to reverse this one easily. Maybe you can reverse if it's going to be very costly and very time consuming. We really have to get this one right from the beginning. What happens, unfortunately, in companies, what can happen is that you have a one size fits all decision making process where you end up using the heavyweight process. 

# Speaker A
On all decisions for everything. Yeah. 

# Speaker B
Including the lightweight ones. The two way door decisions. Two way door decisions should mostly be made by single individuals or by very small teams deep in the organization. And one way door decisions are the ones that are the irreversible ones. Those are the ones that should be elevated up to, you know, the senior, most executives who should slow them down and make sure that the right thing is being done. 

# Speaker A
Yeah. Part of the skill here is to know the difference in one way and two way. I think you mentioned. Yes, I think you mentioned Amazon prime. The decision to sort of create Amazon prime as a one way door. I mean, it's unclear if it is or not, but it probably is. And it's a really big risk to go there. 

# Speaker B
There are a bunch of decisions like that that are changing. The decision is going to be very, very complicated. Some of them are technical decisions, too, because some technical decisions are like quick drying cement. You know, if you're going to, once you make them, it gets really hard. I mean, you know, choosing which propellants to use in a vehicle, you know, selecting lng for the booster stage and selecting hydrogen for the upper stage. That has turned out to be a very good decision. But if you changed your mind, that would be a big. That would be a very big setback. Do you see what I was saying? 

# Speaker A
Yeah. 

# Speaker B
That's the kind of decision you scrutinize very, very carefully. Other things just aren't like that. Most decisions are not that way. Most decisions should be made by single individuals, but they need and done quickly in the full understanding that you can always change your mind. 

# Speaker A
Yeah. One of the things I really liked, perhaps it's not two way decisions, is I disagree and commit phrase. So somebody brings up an idea to you. If it's a two way door, you state that you don't understand enough to agree, but you still back them. I'd love for you to explain. 

# Speaker B
Yes, disagree and commit is a really important principle that saves a lot of arguing. 

# Speaker A
Yeah. 

# Speaker B
So you want to use that. 

# Speaker A
In my personal life, I disagree, but. 

# Speaker B
Commit, it's very common in any endeavor in life, in business, and any, you know, anybody where you have teammates, you have a teammate, and the two of you disagree. 

# Speaker A
Yeah. 

# Speaker B
At some point, you have to make a decision. And, you know, in companies, we tend to organize hierarchically. So there's this, you know, whoever's the more senior person ultimately gets to make the decision. So ultimately, the CEO gets to make that decision. And the CEO may not always make the decision that they agree with. So, like, you know, I would say, I would often, I would be the one who would disagree and commit. Some. One of my direct reports would very much want to do it, do something in a particular way. I would think it was a bad idea. I would explain my point of view. They would say, jeff, I think you're wrong, and here's why. And we would go back and forth, and I would often say, you know what? Think you're right, but I'm going to gamble with you, and you're closer to the ground truth than I am. I've known you for 20 years. You have great judgment. I don't know that I'm right either. Not really. Not for sure. All these decisions are complicated. Let's do it your way. But at least then you've made a decision, and I'm agreeing to commit to that decision. So I'm not going to be second guessing it. I'm not going to be sniping at it. I'm not going to be saying, I told you so. I'm going to try actively to help make sure it works. That's a really important teammate behavior. There's so many ways that dispute resolution is a really interesting thing on teams, and there are so many ways when two people disagree about something, I'm assuming the case where everybody is well intentioned, they just have a very different opinion about what the right decision is. And we have, in our society and inside companies, we have a bunch of mechanisms that we use to resolve these kinds of disputes. A lot of them are, I think, really bad. So an example of a really bad way of coming to agreement is compromise. Compromise. You know, look, I, here's, we're in a room here, and I could say, lex, how tall do you think this ceiling is? And you'd be like, I don't know, Jeff, maybe 12ft tall. And I would say, I think it's 11ft tall. And then we'd say, you know what? Let's just call it eleven and a half feet. That's compromise. Instead of the right thing to do is, you know, to get a tape measure or figure out some way of actually measuring, but think getting that tape measure and figure out how to get it to the top of the ceiling and all these things. That requires energy compromise. The advantage of compromise as a resolution mechanism is that it's low energy, but it doesn't lead to truth. And so in things like the height of the ceiling, where truth is a noble thing, you shouldn't allow compromise to be used when you can know the truth. Another really bad resolution mechanism that happens all the time is just who's more stubborn? This is also, let's say, two executives who disagree and they just have a war of attrition. And whichever one gets exhausted first capitulates to the other one. Again, you haven't arrived at truth, and this is very demoralizing. So this is where escalation, I try to ask people who on my team to say, never get to a point where you are resolving something by who gets exhausted first. Escalate that. I'll help you make the decision because that's so de energizing and such a terrible, lousy way to make a decision. 

# Speaker A
Do you want to get to the resolution as quickly as possible? Because that ultimately leads to a high velocity. 

# Speaker B
Yes. And you want to try to get as close to truth is possible. So you want, like, you know, exhausting the other person is not truth seeking. 

# Speaker A
Yes. 

# Speaker B
And compromise is not truth seeking. So, you know, it doesn't mean, and there are a lot of cases where no one knows the real truth, and that's where disagree and commit can come in. But it's escalation is better than war of attrition. Escalate. Just, you know, to your boss and say, hey, we can't agree on this. We like each other, we're respectful of each other, but we strongly disagree with each other. We need you to make a decision here so we can move forward. But decisiveness moving forward quickly on decisions as quickly as you responsibly can is how you increase velocity. Most of what slows things down is taking too long to make decisions at all skill levels. So it has to be part of the culture to get high velocity. Amazon has a million and a half people. And the company is still fast. We're still decisive, we're still quick. And that's because the culture supports that. 

# Speaker A
At every scale in a distributed way. Maximize the velocity of decisions. 

# Speaker B
Exactly. 

# Speaker A
You've mentioned the lunar program. Let me ask you about that. 

# Speaker B
Yeah. 

# Speaker A
There's a lot going on there and you haven't really talked about it much. So in addition to the Artemis program with NASA, Blue is doing its own lander program. Can you describe it? There's a sexy picture on Instagram with one of them. Is it the mk one? 

# Speaker B
I guess, yeah, the mark one. The picture. Is it me with Bill Nelson, the NASA administrator. 

# Speaker A
Just to clarify, the lander is the sexy thing about the instagram. 

# Speaker B
I know it's not me. I know it was either the lander or bill. 

# Speaker A
I love Bill. 

# Speaker B
But yes, the mark one lander is designed to take 3000 surface of the moon expendable cargo. It's an expendable lander, lands on the moon, stays there, take 3000 surface, it can be launched on a single new glenn flight, which is very important. So it's a relatively simple architecture just like the human landing system. Lander, called the mark two. Mark one is also fueled with liquid hydrogen, which is for high energy missions like landing on the surface of the moon. The high specific impulse of hydrogen is a very big advantage. The disadvantage of hydrogen has always been that it's, since it's such a deep cryogenic, it's not storable. So it's constantly boiling off and you're losing propellant because it's boiling off. And so what we're doing as part of our lunar program is developing solar powered cryocoolers that can actually make hydrogen a storable propellant for deep space. And that's a real game changer. It's a game changer for any high energy mission. So to the moon, but to the outer planets, to Mars, everywhere. 

# Speaker A
So the idea with Mark one, both Mark one and Mark two is the new glenn can carry it from the surface of Earth to the surface of the moon. 

# Speaker B
Exactly. So the mark one is expendable. The lunar. The lunar lander we're developing for NASA, the mark two lander. That's part of the Artemis program. They call it the sustaining lander program. So that lander is designed to be reusable. It can land on the surface moon in a single stage configuration and then take off. So the whole, you know, the, if you look at the Apollo program, the lunar lander, and Apollo was really two stages. It would land on the surface, and then it would leave the descent stage on the surface of the moon and only the ascent stage. We go back up into lunar orbit, where it would rendezvous with the command module. Here, what we're doing is we have a single stage lunar lander that carries down enough propellant so that it can bring the whole thing back up so that it can be reused over and over. And the point of doing that, of course, is to reduce cost so that you can make lunar missions more affordable over time, which is, that's one of NASA's big objectives, because this time, the whole point of Artemis is go back to the moon, but this time to stay. So, you know, back in the Apollo program, we went to the moon six times and then ended the program, and it really was too expensive to continue. 

# Speaker A
And so there's a few questions there, but one is, how do you stay on the moon? What ideas do you have about, yeah, like a sustained, sustaining life where a few folks can stay there for prolonged periods of time? 

# Speaker B
Well, one of the things we're working on is using lunar resources like lunar regolith to manufacture commodities and even solar cells on the surface of the moon. We've already built a solar cell that is completely made from lunar regolith stimulant. And this solar cell is only about 7% power efficient. So it's very inefficient compared to, you know, the more advanced solar cells that we make here on Earth. But if you can figure out how to make a practical solar cell factory that you can land on the surface of the moon, and then the raw material for those solar cells is simply lunar regolith, then you can just, you know, continue to churn out. Solar cells on the surface of the moon, have lots of power on the surface of the moon that will make it easier for people to live on the moon. Similarly, we're working on extracting oxygen from lunar regolith. So lunar regolith by weight has a lot of oxygen in it. It's bound very tightly as oxides with other elements. And so you have to separate the oxygen, which is very energy intensive. So that also could work together with the solar cells. But if you can, and then ultimately, we may be able to find practical quantities of ice in the permanently shadowed craters on the poles of the moon. And we know there is ice, water, or water ice in those craters, and we know that we can break that down with electrolysis into hydrogen and oxygen. And then you not only have oxygen, but you'd also have a very good, high efficiency propellant fuel in hydrogen. So there's a lot we can do to make the moon more sustainable over time. But the very first step, the kind of gate that all of that has to go through, is we need to be able to land cargo and humans on the surface of the moon at an acceptable cost. 

# Speaker A
To fast forward a little bit, is there any chance Jeff Bezos steps foot on the moon and on Mars, one or the other or both? 

# Speaker B
It's very unlikely. I think it's probably something that gets done by future generations. By the time it gets to me. I think in my lifetime, that's probably going to be done by professional astronauts. Sadly, I would love to sign up for that mission. So don't count me out yet, Lex. You know, give me. Give me a fighting shot here, maybe. But I think if we're. If we are placing reasonable bets on such a thing in my lifetime, that will continue to be done by professional astronauts. 

# Speaker A
Yeah. So these are risky, difficult missions and. 

# Speaker B
Probably missions that require a lot of training. You know, you are going there for a very specific purpose, to do something. We're going to be able to do a lot on the moon, too, with automation. So, you know, in terms of setting up these factories and doing all that, we're sophisticated enough now with automation that we probably don't need humans to tend those factories and machines. So there's a lot that's going to be done in both modes. 

# Speaker A
So I have to ask the bigger picture question about the two companies pushing humanity forward, out towards the stars. Blue origin and SpaceX. Are you competitors, collaborators, which. And to what degree? 

# Speaker B
Well, I would say just like the Internet is big, and there are lots of winners at all skill levels. I mean, there are half a dozen giant companies the Internet has made, but they're a bunch of medium sized companies and a bunch of small companies, all successful, all with profit streams, all driving great customer experiences. That's what we want to see in space, that kind of dynamism. And space is big. There's room for a bunch of winners, and it's going to happen at all skill levels. And so SpaceX is going to be successful for sure. I want Blue Origin to be successful, and I hope there are another five companies right behind us. 

# Speaker A
But I spoke to Elon a few times recently about you, about Blue Origin, and he was very positive about you as a person and very supportive of all the efforts you've been leading. At blue, what's your thoughts? You worked with a lot of leaders at Amazon. At blue, what's your thoughts about Elon as a human being and a leader? 

# Speaker B
Well, I don't really know Elon very well. I know his public Persona, but I also know you can't know anyone by their public Persona. It's impossible. I mean, you may think you do, but I guarantee you don't. So I don't really know, you know, elon way better than I do, Lex, but in terms of his, judging by the results, he must be a very capable leader. There's no way you could have Tesla and SpaceX without being a capable leader. It's impossible. 

# Speaker A
Yeah. I hope you guys hang out sometimes, shake hands and sort of have a kind of friendship that would inspire just the entirety of humanity, because what you're doing is one of the big grand challenges ahead for humanity. 

# Speaker B
Well, I agree with you, and I think in a lot of these endeavors, we're very like minded. 

# Speaker A
Yeah. 

# Speaker B
So I think, I think, I'm not saying we're identical, but I think we're very like minded. And so I, you know, I love that idea. 

# Speaker A
I, going back to sexy pictures on your instagram, there's a video of you from the early days of Amazon giving a tour of your, quote, sort of offices. I think your dad is holding the camera. 

# Speaker B
He is. Yeah, I know, right? Yes. This is what, the giant orange extension cord? Yeah. 

# Speaker A
And you're like, explaining the genius of the extension cord. There's a desk and the CRT monitor and sort of that's where all the magic happened. I forget what your dad said, but this is like the center of it all. So what was it like? What was going through your mind at that time? You left a good job in New York and took this leap. Were you excited? Were you scared? 

# Speaker B
So excited and scared, anxious. Thought the odds of success were low. Told all of our early investors that I thought there was a 30% chance of success, by which I just been getting your money back, not turning out what actually happened, because that's the truth. Every startup company is unlikely to work. It's helpful to be in reality about that, but that doesn't mean you can't be optimistic. So you kind of have to have this duality in your head. On the one hand, you know what the baseline statistics say about startup companies, and the other hand, you have to ignore all of that and just be 100% sure it's going to work. And you're doing both things at the same time. You're holding that contradiction in your head. But it was so exciting. I love from 1994 when the company was founded, 1995, when we opened our doors all the way until today. I find Amazon so exciting. And that doesn't mean it's like full of pain, full of problems. It's like there's so many things that need to be resolved and worked and made better, etcetera. But on balance, it's so fun, it's such a privilege, it's been such a joy. I feel so grateful that I've been part of that journey. It's just been incredible. 

# Speaker A
So in some sense, you don't want a single day of comfort. You've written about this many times. We'll talk about your writing, which I would highly recommend people read in just the letters to shareholders. So you wrote up explaining the idea of day one thinking. I think you first wrote about in 97 letters to shareholders. Then you also, in a way, wrote about, sad to say, is your last letter to shareholders and CEO. And you said that day two is stasis, followed by irrelevance, followed by excruciating painful decline, followed by death. And that is why it's always day one. Can you explain this day one thing? This is a really powerful way to describe the beginning and the journey of Amazon. 

# Speaker B
It's really a very simple, and I think, age old idea about renewal and rebirth. And like every day is day one. Every day you're deciding what you're going to do and you are not trapped by what you were or who you were or any self consistency. Self consistency even can be a trap. And so day one thinking is kind of, we start fresh every day and we get to make new decisions every day about invention, about customers, about how we're going to operate, what are even, even as deeply as what our principles are. We can go back to that. Turns out we don't change those very often, but we change them occasionally. And when we work on programs at Amazon, we often make a list of tenants. And the tenants are kind of, they're not principles. They're a little more tactical than principles. But it's kind of the main ideas that we want this program to embody, whatever those are. And one of the things that we do is we put, these are the tenets for this program. And in parentheses, we always put, unless you know a better way. And that idea, unless you know a better way is so important because you never want to get trapped by dogma, you never want to get trapped by history. It doesn't mean you discard history or ignore it. There's so much value in what has worked in the past, and. But you can't be blindly following what you've done. And that's the heart of day one. You're always starting fresh. 

# Speaker A
And to the question of how to fend off day two, you said such a question can't have a simple answer. As you're saying, there will be many elements, multiple paths, and many traps. I don't know the whole answer, but I may know bits of it. Here's a starter pack of essentials. Maybe others come to mind for day one defense. Customer obsession, a skeptical view of proxies, the eager adoption of external trends and high velocity decision making. So we talked about high velocity decision making. That's more difficult than it sounds. So maybe you can pick one that stands out to you as you can comment on eager adoption of external trends, high velocity decision making, skeptical view of proxies. How do you fight off day two? 

# Speaker B
Well, you know, I'll talk about. Because I think it's the one that is maybe in some ways, the hardest to understand is the skeptical view of proxies. One of the things that happens in business, probably anything that you're, where you're, you know, you have an ongoing program and something is underway for a number of years, is you develop certain things that you're managing to like, let's say the typical case would be a metric, and that metric isn't the real underlying thing. And so, you know, maybe the metric is efficiency metric around customer contacts per unit sold or something like if you sell a million units, how many customer contacts do you get? Or how many returns do you get? And so on and so on. What happens is a little bit of a kind of inertia sets in where somebody a long time ago invented that metric, and they invented that metric. They decided we need to watch for customer returns per unit sold as an important metric, but they had a reason why they chose that metric. The person who invented that metric and decided it was worth watching. And then fast forward five years, that metric is the proxy for truth, I guess. Proxy for truth, the proxy for customers, let's say. In this case, it's a proxy for customer happiness. But that metric is not actually customer happiness, it's a proxy for customer happiness. The person who invented the metric understood that connection. Five years later, a kind of inertia can set in, and you forget the truth behind why you were watching that metric in the first place. And the world shifts a little. And now that proxy isn't as valuable as it used to be, or it's missing something, and you have to be on alert for that. You have to know, okay, this is, I don't really care about this metric. I care about customer happiness. And this metric is worth putting energy into and following and improving and scrutinizing only insomuch as it actually affects customer happiness. And so you got to constantly be on guard. And it's very, very common. This is a nuanced problem. It's very common, especially in large companies, that they are managing to metrics that they don't really understand. They don't really know why they exist. And the world may have shifted out from under them a little. And the metrics are no longer as relevant as they were when somebody ten years earlier invented the metric. 

# Speaker A
That is a nuance, but that's a big problem, right? Something so compelling to have a nice metric to try to optimize. 

# Speaker B
Yes. And by the way, you do need, you know, you can't ignore them. You want them, but you just have to be constantly on guard. This is, you know, a way to slip into day two thinking would be to manage your business. Two metrics that you don't really understand, and you're not really sure why they were invented in the first place, and you're not sure they're still as relevant as they used to be. 

# Speaker A
What does it take to be the guy or gal who brings up the point that this proxy might be outdated, I guess. What does it take to have a culture that enables that in the meeting? Because that's a very uncomfortable thing to bring up at a meeting. We all showed up here. It's a Friday. 

# Speaker B
This is such. You have just asked a million dollar question. So this is, this is what you're, if I generalize what you're asking, you're talking in general about truth telling. 

# Speaker A
Yeah. 

# Speaker B
And we humans are not really truth seeking animals. We are social animals. 

# Speaker A
Yeah, we are. 

# Speaker B
And, you know, take you back in time 10,000 years, and you're in a small village. If you go along to get along, you can survive, you can procreate. If you're the village truth teller, you might get clubbed to death in the middle of the night. Truths are often, they don't want to be heard because important truths can be uncomfortable. They can be awkward. They can be exhausting, impolite, yes. Challenging. They can make people defensive, even if that's not the intent. But any high performing organization, whether it's a sports team, a business, a political organization, an activist group, I don't care what it is. Any high performing organization has to have mechanisms and a culture that supports truth telling. One of the things you have to do is you have to talk about that, and you have to talk about the fact that it takes energy to do that. You have to talk to people. You have to remind people it's okay, that it's uncomfortable. You have to literally tell people it's not what we're designed to do as humans. It's not really. It's kind of a side effect. You know, we can do that, but it's not how we survive. We mostly survive by being social animals and being cordial and cooperative, and that's really important. And so there's a, you know, science is all about truth telling. It's actually a very formal mechanism for trying to tell the truth. And even in science, you find that it's hard to tell the truth, right? Even, you know, you're supposed to have hypothesis test it and find data and reject the hypothesis and so on. It's not easy. 

# Speaker A
But even in science, there's, like, the senior scientists and the junior scientists, and then there's a hierarchy of humans where the seniority, somehow seniority matters in the scientific process, which is, and that's true inside companies, too. 

# Speaker B
And so you want to set up your culture so that the most junior person can overrule the most senior person if they have data. And that really is about trying to, you know, there are little things you can do. So, for example, in every meeting that I attend, I always speak last. And I know from experience that, you know, if I speak first, even very strong willed, highly intelligent, high judgment participants in that meeting will wonder, well, if Jeff thinks that I came in this meeting thinking one thing, but maybe I'm not right. And so you can do little things like, if you're the most senior person in the room, go last, let everybody else go first. In fact, ideally, try to have the most senior person go first and the second, then try to go in order of seniority so that you can hear everyone's opinion in a kind of unfiltered way, because we really do. We actually literally change our opinions if somebody who you really respect says something makes you change your mind a little. 

# Speaker A
So you're saying implicitly or explicitly, give permission for people to have a strong opinion that as long as it's backed by data, yes. 

# Speaker B
And sometimes it can. Even, by the way, a lot of our most powerful truths turn out to be hunches. They turn out to be based on anecdotes. They're intuition based, and sometimes you don't even have strong data. But you may know the person well enough to trust their judgment. You may feel yourself leaning in. It may resonate with a set of anecdotes you have, and then you may be able to say, you know something about that feels right. Let's go collect some data on that. Let's try to see if we can actually know whether it's right. But for now, let's not disregard it because it feels right. You can also fight inherent bias. There's an optimism bias. If there are two interpretations of a new set of data and one of them is happy and one of them is unhappy, it's a little dangerous to jump to the conclusion that the happy interpretation is right. You may want to sort of compensate for that human bias of looking for, you know, trying to find the silver lining and say, look, this, that might be good, but I'm going to go with it's bad for now until we're sure. 

# Speaker A
So, speaking of happiness bias, data collection and anecdotes, you have to. How's that for transition? You have to tell me the story of the call you made, the customer service call you made to demonstrate a point about wait times. 

# Speaker B
Yeah, this is very early in the history of Amazon, and we were going over a weekly business review and a set of documents, and I have a saying, which is when the data and the anecdotes disagree, the anecdotes are usually right. And it doesn't mean you just slavishly go follow the anecdotes, then it means you go examine the data. It's usually not the data is being mis collected. It's usually that you're not measuring the right thing. And so if you have a bunch of customers complaining about something, and at the same time your metrics look like, why aren't they shouldn't be complaining, you should doubt the metrics. And an early example of this was we had metrics that showed that our customers were waiting, I think, less than, I don't know, 60 seconds when they called it 1800 number to get phone customer service. The wait time was supposed to be less than 60 seconds, but we had a lot of complaints that it was longer than that. And anecdotally, it seemed longer than that. Like I would call customer service myself. And so one day we're in a meeting or going through the WBR and the weekly business review, and we get to this metric in the DAC, and the guy who leads. Customer service is to fit in the metric. And I said, okay, let's call. Picked up the phone and I dialed the 1800 number and called customer service. And we just waited in silence for. 

# Speaker A
What did it turn out to be? 

# Speaker B
Oh, it was really long, more than ten minutes, I think. 

# Speaker A
Oh, wow. 

# Speaker B
I mean, it was many minutes. And so, you know, it dramatically made the point that something was wrong with the data collection. We weren't measuring the right thing. And that set off a whole chain of events where we started measuring it. Right. And that's an example, by the way, of truth telling is like, that's an uncomfortable thing to do, but you have to seek truth even when it's uncomfortable. And you have to get people's attention and they have to buy into it and they have to get energized around really fixing things. 

# Speaker A
So that speaks to the obsession with the customer experience. So one of the defining aspects of your approach to Amazon is just being obsessed with making customers happy. I think companies sometimes say that, but Amazon is really obsessed with that. I think there's something really profound to that, which is seeing the world through the eyes of the customer, like the customer experience, the human being that's using the product, that's enjoying the product, like what they're like the subtle little things that make up their experience. Like how do you optimize those? 

# Speaker B
This is another really good and kind of deep question because there are big things that are really important to manage and then there are small things internally into Amazon. We call them paper cuts. So we have, we're always working on the big things, like if you ask me, and most of the energy goes into the big things, as it should. So, and you can identify the big things. And I would encourage anybody, if anybody listening to this is an entrepreneur that's a small business, whatever, think about the things that are not going to change over ten years. And those are probably the big things. So, like, I know in our retail business at Amazon, ten years from now, customers are still going to want low prices. I know they're still going to want fast delivery, and I just know they're still going to want big selection. So it's impossible to imagine a scenario where ten years from now I say, where a customer says, I love Amazon, I just wish the prices were a little higher, or I love Amazon, I just wish you delivered a little more slowly. So when you identify the big things, you can tell they're worth putting energy into because they're stable in time. Okay. But you're asking about something a little different, which is in every customer experience, there are those big things. And by the way, it's astonishingly hard to focus even on just the big things. So even though they're obvious, they're really hard to focus on. But in addition to that, there are all these little tiny customer experience deficiencies, and we call those paper cuts. And we make long lists of them. And then we have dedicated teams that go fix paper cuts, because the teams working on the big issues never get to the paper cuts. They never work their way down the list to get to. They're working on big things, as they should and as you want them to. And so you need special teams who are charged with fixing paper cuts. 

# Speaker A
Where would you put on the paper cut spectrum? The buy now with one click button, which is, I think, pretty genius. So to me, like, okay, my interaction with things I love on the Internet, there's things I do a lot. I may be representing regular human. I would love for those things to be frictionless. For example, booking airline tickets, just saying. But, you know, it's buying a thing with one click, making that experience frictionless, intuitive, all aspects of it like that. That just fundamentally makes my life better. Not just in terms of efficiency, in terms of some kind of cognitive load. Yeah, cognitive load. And peace. Inner peace and happiness. First of all, buying stuff isn't a pleasant experience. Having enough money to buy a thing and then buying it is a pleasant experience. And, like, having pain around that is somehow just. You're ruining a beautiful experience. And I guess all I'm saying, as a person who loves good ideas, is that a paper cut, a solution to a paper cut? 

# Speaker B
Yes. So it's probably. That particular thing is probably a solution to a number of paper cuts. So if you go back and look at our order pipeline and how people shopped on Amazon before we invented one click shopping, there were a whole series. There was more friction. There was a whole series of paper cuts. And that invention eliminated a bunch of paper cuts. And I think you're absolutely right, by the way, that there, when you come up with something like one click shopping again, this is, like, so ingrained in people now. I'm impressed that you even notice it. I mean, most people, every time I. 

# Speaker A
Click the button, surge of happiness. 

# Speaker B
There is in the perfect invention, for the perfect moment, in the perfect context. There is real beauty. It is actual beauty. And it feels good. It's emotional. It's emotional for the inventor, it's emotional for the team that builds it. It's emotional for the customer. It's a big deal. And you can feel those things. 

# Speaker A
But to keep coming up with that idea, with those kinds of ideas, I guess the day one thinking effort. 

# Speaker B
Yeah. And you need a big group of people who feel that kind of satisfaction with creating that kind of beauty. 

# Speaker A
There's a lot of books written about you. There's a book invent and wander, where Walter Isaacson does an intro. And it's mostly collective writings of yours. I've read that. I also recommend people check out the founders podcast that covers you a lot, and it does different analysis of different business advice you've given over the years. I bring all that up because I saw that there. I mentioned that you said that books are an antidote for short attention spans, and I forget how it was phrased, but that when you were thinking about the Kindle, that you're thinking about how technology changes us. 

# Speaker B
Yeah, we co evolve. 

# Speaker A
Yeah. 

# Speaker B
With our tools. So, you know, we invent new tools and then our tools change us, which. 

# Speaker A
Is fascinating to think about. 

# Speaker B
Goes in a circle. 

# Speaker A
And there's some aspect, you know, even just inside business where you don't just make the customer happy, but you also have to think about, like, where is this going to take humanity if you. 

# Speaker B
Zoom out a bit and, you know, you can feel your brain, brains are plastic, and you can feel your brain getting reprogrammed. I remember the first time this happened to me was when Tetris, who first came on the scene, I'm sure you've had anybody who's been a game player has this experience where you close your eyes to lay down, to go to sleep, and you see all the little blocks moving and you can, you're kind of rotating them in your mind, and you can just tell as you walk around the world that you have rewired your brain to play Tetris. And, but that happens with everything. And so, you know, one of the, I think we still have yet to see the full repercussions of this, I fear. I think one of the things that we've done online, you know, largely because of social media, is we have trained our brains to be really good at processing super short form content. And, you know, your podcast flies in the face of this. You know, you do these long format things and reading books, reading books is a long format thing. And we all do more of, if you, if something is convenient, we do more of it. And so when you make tools, you know, we carry around a little. We carry around in our pocket a phone. And one of the things that phone does, for the most part, is it is an attention shortening device, because most of the things we do on our phone shorten our attention spans. And I'm not even going to say we know for sure that that's bad, but I do think it's happening. It's one of the ways we're co evolving with that tool. But I think. I think it's important to spend some of your time and some of your life doing long attention span things. 

# Speaker A
Yeah. I think you've spoken about the value in your own life of focus, of singular focus on the thing for prolonged periods of time. And that's certainly what books do, and that's certainly what that piece of technology does. But I bring all that up to ask you about another piece of technology, AI, that has the potential to have various trajectories, to have an impact on human civilization. How do you think AI will change this? 

# Speaker B
If you're talking about generative AI, large language models, things like Chad GPT and its soon successors, these are incredibly powerful technologies. To believe otherwise is to bury your head in the sand soon to be even more powerful. It's interesting to me that large language models in their current form are not inventions, they're discoveries. The telescope was an invention, but looking through it at Jupiter, knowing that it had moons was a discovery. Like, my God, it has moons, and that's what Galileo did. And so this is closer on that spectrum of invention. You know, we know exactly what happens with a 787. It's an engineered object. We designed it. We know how it behaves. We don't want any surprises. Large language models are much more like discoveries. We're constantly getting surprised by their capabilities. They're not really engineered objects. Then you have this debate about whether they're going to be good for humanity or bad for humanity. Even specialized AI could be very bad for humanity. I mean, just regular machine learning models can make certain weapons of war that could be incredibly destructive and very powerful, and they're not general AI's. They could just be very smart weapons. And so we have to think about all of those things. I'm very optimistic about this. So even in the face of all this uncertainty, my own view is that these powerful tools are much more likely to help us and save us, even than they are to unbalance, hurt us and destroy us. I think we humans have a lot of ways of we can make ourselves go extinct. These things may help us not do that, so they may actually save us. So the people who are overly concerned, in my view, overly. It's a valid debate. I think that they may be missing part of the equation, which is how helpful they could be in making sure we don't destroy ourselves. I don't know if you saw the movie OppenheiMer, but to me, first of all, I loved the movie. And I thought the best part of the movie is this bureaucrat played by Robert Downey Junior, who, you know, some people have talked to think that's the most boring part of the movie. I thought it was the most fascinating because what's going on here is you realize we have invented these awesome, destructive, powerful technologies called nuclear weapons, and they are managed, and, you know, we humans are, we're not really capable of wielding those weapons. That's what he represented in that movie is here's this guy who is just, he wrongly thinks he's, like, being so petty. He thinks that he said something, that Oppenheimer said something bad to Einstein about him. They didn't talk about him at all, as you find out in the final scene of the movie. And yet he spent his career trying to be vengeful and petty. And that's the problem. We as a species are not really sophisticated enough and mature enough to handle these technologies. And by the way, before you get to General AI and the possibility of AI having agency, and there's a lot of things would have to happen, but there's so much benefit that's going to come from these technologies in the meantime, even before they're general AI in terms of better medicines and better tools to develop more technologies and so on. So I think it's an incredible moment to be alive and to witness the transformations that are going to happen. How quickly will happen, no one knows. But over the next ten years and 20 years, I think we're going to see really remarkable advances. And I personally am very excited about it. 

# Speaker A
First of all, really interesting to say that it's discoveries, that it's true that we don't know the limits of what's possible with the current language models. 

# Speaker B
We don't. 

# Speaker A
And it could be a few tricks and hacks here and there that open doors to hold entire new possibilities. 

# Speaker B
We do know that humans are doing something different from these models, in part because we're so power efficient. The human brain does remarkable things, and it does it on about 20 watts of power. And the AI techniques we use today use many kilowatts of power to do equivalent tasks. There's something interesting about the way the human brain does this, and also, we don't need as much data. So, you know, like self driving cars, are they have to drive billions and billions of miles to try and to learn how to drive. And, you know, your average 16 year old figures it out with many fewer miles. So there are still some tricks, I think, that we have yet to learn. I don't think we've learned the last trick. I don't think it's just a question of scaling things up, but what's interesting is that just scaling things up, and I put just in quotes because it's actually hard to scale things up, but just scaling things up also appears to pay huge dividends. 

# Speaker A
Yeah. And there's some more nuanced aspects about human beings that's interesting. That's able to accomplish, like being truly original and novel to, you know, large language models, being able to come up with some truly new ideas. That's one. And the other one is truth. It seems that large language models are very good at sounding like they're saying a true thing, but they don't require or often have a grounding in sort of a mathematical truth. It can just basically is a very good bullshitter. So if. If there's not enough data, if there's not enough sort of data in the training, data about a particular topic is just going to concoct accurate sounding narratives, which is a very fascinating problem to try to solve. How do you get language models to infer what is true or not to sort of introspect? 

# Speaker B
Yeah. They need to be taught to say, I don't know, more often. 

# Speaker A
Yeah. 

# Speaker B
I know of several humans who could be taught that as well. 

# Speaker A
And then the other stuff, because you're still a bit involved in the Amazon side with the AI things. The other open question is what kind of products are created from this? 

# Speaker B
Oh, so many. 

# Speaker A
Yeah. 

# Speaker B
I mean, you know, just to, you know, we have Alexa and Echo, and Alexa has hundreds of millions of installed base, you know, inputs. And so there's this. There's, you know, there's Alexa everywhere. And guess what? Alexa is about to get a lot smarter. 

# Speaker A
Yeah. 

# Speaker B
And so that's really, you know, from a product point of view, that's super exciting. 

# Speaker A
There's so many opportunities there. 

# Speaker B
So many opportunities. Shopping assistant. You know, like, all that stuff is amazing. AWS, you know, we're building Titan, which is our foundational model. We're also building bedrock, which are corporate clients at AWS or enterprise clients. They want to be able to use these powerful models with their own corporate data without accidentally contributing their corporate data to that model. Those are the tools we're building for them with bedrock. So there's tremendous opportunity here, the security. 

# Speaker A
The privacy, all those things are fascinating of how to, because so much value can be gained by training on private data. But you want to keep this secure. It's a fascinating technical. 

# Speaker B
This is a very challenging technical problem, and it's one that we're making progress on and dedicated to solving for our customers. 

# Speaker A
Do you think there will be a day when humans and robots, maybe, Alexa, have a romantic relationship? I couldn't be her. 

# Speaker B
Well, I mean, if you look at products here, if you look at the spectrum of human variety and what people like, you know, sexual variety, yes. You know, there are people who like everything. So the answer, your question, has to be yes. 

# Speaker A
Okay. I guess I'm asking. 

# Speaker B
I don't know how widespread that will be. All right, but it will happen. 

# Speaker A
I was just asking when for a friend, but it's all right. I'm just moving on. Next question. What's a perfectly productive day in the life of Jeff Bezos? You're one of the most productive humans in the world. 

# Speaker B
Well, first of all, I get up in the morning, and I putter. I like, I like, have a coffee. You just find putter, just like I slowly move around. I'm not as productive as you might think I am. I mean, I. Because I do believe in wandering, and I sort of, you know, I read my phone for a while. I read newspapers for a while, I chat with Laura, and I drink my first coffee. So I kind of. I move pretty slowly in the first couple of hours. I get up early, just naturally. And. And then, you know, I exercise most days, and most days, it's not that hard for me. Some days it's really hard, and I do it anyway. I don't want to, you know, and it's painful. And I'm like, why am I here? And I don't want to do, why. 

# Speaker A
Am I here at the gym? 

# Speaker B
Why am I here at the gym? Why don't I do something else? You know, it's not always easy. 

# Speaker A
What's your source of motivation in those moments? 

# Speaker B
I know that I'll feel better later if I do it. And so the real source of motivation, I can tell the days when I skip it, I'm not quite as alert. I don't feel as good. And then there's harder motivations. It's longer term. You want to be healthy as you age. You want health Spanish. But ideally, you want to be healthy and moving around when you're 80 years old. So there's a lot of. But that kind of motivation so far in the future, it can be very hard to work in the second. So thinking about the fact I'll feel better in about 4 hours if I do it now, have more energy for the rest of my day, and so on and so on. 

# Speaker A
What's your exercise routine? Just to linger on that? What do you, how much you curl? I mean, what are we talking about here? That's all I do at the gym. 

# Speaker B
So I just, my routine on a good day, I do about half an hour of cardio, and I do about 45 minutes of weightlifting, resistance training of some kind, mostly weights. I have a trainer who I love who pushes me, which is really helpful. I'll be like, he'll say, jeff, you could. Can we go up on that way a little bit? And I'll think about it and I'll be like, no, I don't think so. And he'll be, he'll look at me and say, yeah, I think you can. And of course, he's right. 

# Speaker A
Yeah. 

# Speaker B
So it's cool to have somebody push. 

# Speaker A
You a little bit, but almost every day you do that. 

# Speaker B
I do almost every day. I do a little bit of cardio and a little bit of weightlifting and I'd rotate. I do a pulling day and a pushing day and a leg day. It's all pretty standard stuff. 

# Speaker A
So puttering. Coffee gym. 

# Speaker B
Coffee gym. And then work. 

# Speaker A
What's work look like? What are the productive hours look like for you? 

# Speaker B
I, you know, so I, a couple years ago, I left as the CEO of Amazon, and I have never worked harder in my life. I am working so hard, and I'm mostly enjoying it, but there are also some very painful days. Most of my time is spent on blue origin, and I've been so deeply involved here now for the last couple of years. In the big, I love it. And the small. There's all the frustrations that come along with everything. We're trying to get to rate manufacturing as we talked about. That's super important. We'll get there. We just hired a new CEO, a guy I've known for close to 15 years now, a guy named Dave Limp, who I love. He's amazing. So we're super lucky to have Dave. And you're going to see us move faster there by day of work, reading documents, having meetings, sometimes in person, sometimes over Zoom. Depends on where I am. It's all about the technology, it's about the organization. I'm very, I have architecture and technology meetings almost every day on various subsystems, inside the vehicle, inside the engines. It's super fun for me. My favorite part of it is the technology. My least favorite part of it is, you know, building organizations and so on. That's important. But it's also my least favorite part. So, you know, that's why they call it work. You don't always get to do what you want to do. 

# Speaker A
How do you achieve time where you can focus and truly think through problems? 

# Speaker B
I do little thinking retreats, so this is not the only. I can do that all day long. I'm very good at focusing. I'm very good at, you know, I don't keep to a strict schedule. Like, my meetings often go longer than I plan for them to because I believe in wandering. My perfect meeting starts with a crisp document. So the document should be written with such clarity that it's like angels singing from on high. I like a crisp document and a messy meeting. And so the meeting is about, like, asking questions that nobody knows the answer to and trying to, like, wander your way to a solution. And because, like, and that is if, when that happens just right, it makes all the other meanings worthwhile. It feels good. It has a kind of beautiful to it, it has an aesthetic beauty to it. And you get real breakthroughs in meetings like that. 

# Speaker A
Can you actually describe the crisp document? Like, this is one of the legendary aspects of Amazon, of the way you approach meetings. Just the six page memo, maybe first describe the process of running a meeting with memos. 

# Speaker B
Meetings at Amazon and Blue origin are unusual. When we get new, when new people come in, like a new executive joins, and they're a little taken aback sometimes because the typical meeting will start with a six page, narratively structured memo. And we do study hall for 30 minutes. We sit there silently together in the meeting and read, take notes in the margins, and then we discuss. And the reason, by the way, we do study, you could say, I would like everybody to read these memos in advance. But the problem is people don't have time to do that, and they end up coming to the meeting having only skimmed the memo or maybe not read it at all. And they're trying to catch up, and they're also bluffing like they were in college, having pretended to do the reading. 

# Speaker A
Exactly. 

# Speaker B
It's better just to carve out the time for people. So now we're all on the same page, we've all read the memo, and now we can have a really elevated discussion. And this is so much better from having a slideshow presentation, a PowerPoint presentation of some kind that has so many difficulties. But one of the problems is PowerPoint is really designed to persuade. It's kind of a sales tool, and internally, the last thing you want to do is sell. You want to, again, you're truth seeking. You're trying to find truth. And the other problem with PowerPoint is it's easy for the author and hard for the audience, and a memo is the opposite. It's hard to write a six page memo. A good six page memo might take two weeks to write. You have to write it. You have to rewrite it. You have to edit. You have to talk to people about it. They have to poke holes in it for you. You write it again, it might take two weeks. So the author, it's really a very difficult job, but for the audience, it's much better. So you can read a half hour. And, you know, there are little problems with PowerPoint presentations, too. You know, senior executives interrupt with questions halfway through the presentation. That question's going to be answered on the next slide, but you never got there. Whereas if you read the whole memo in advance, I often write lots of questions that I have in the margins of these memos, and then I go cross them all out, because by the time I get to the end of the memo, they've been answered. That's why I save all that time. You also get the person who's preparing the memo. We talked earlier about groupthink and the fact that I go last in meetings and that you don't want your ideas to pollute the meeting prematurely. You know, the author of the memos has kind of got to be very vulnerable. They got to put all their thoughts out there, and they've got to go first. But that's great because it makes them really good. And so, and you get to see their real ideas and you're not trampling on them accidentally in a big, you know, PowerPoint presentation, what's that feel like. 

# Speaker A
When you've authored a thing and then you're sitting there and everybody's reading your. 

# Speaker B
Thing, you're like, I think it's mostly terrifying. 

# Speaker A
Yeah. Like, maybe in a good way. I think it's, like a purifying. 

# Speaker B
I think it's terrifying. In a, in a productive way. 

# Speaker A
Yeah. 

# Speaker B
But I think it's emotionally a very nerve wracking experience. 

# Speaker A
Is there art, science to the writing of the six page memo or just writing in general to you? 

# Speaker B
The. I mean, and it's really got to be a real memo. So it means paragraphs have topic sentences. It's verbs and nouns. That's the other problem with PowerPoint versus. They're often just bullet points. And you can hide a lot of sloppy thinking behind bullet points. When you have to write in complete sentences with narrative structure, it's really hard to hide sloppy thinking. So it forces the author to be at their best. And so you're getting somebody's. They're getting somebody's really their best thinking. And then you don't have to spend a lot of time trying to tease that thinking out of the person. You've got it from the very beginning, so it really saves you time in the long run. 

# Speaker A
So that part is crisp and then the rest is messy. Crisp document. 

# Speaker B
Yes. You don't want to pretend that the discussion should be crisp. There's, you know, most meetings, you're trying to solve a really hard problem. There's a different kind of meeting which we call weekly business reviews or business reviews. They may be weekly or monthly or daily, whatever they are. But these business review meetings, that's usually for incremental improvement. And you're looking at a series of metrics. Every time it's the same metrics. Those meetings can be very efficient. They can start on time and end on time. 

# Speaker A
So we're about to run out of time, which is a good time to ask about the 10,000 year clock. That's what I'm known for, is the humor. Okay, can you explain what the 10,000 year clock is? 

# Speaker B
10,000 year clock is a physical clock of monumental scale. It's about 500ft tall. It's inside a mountain in west Texas, in a chamber that's about 12ft in diameter and 500ft tall. 10,000 year clock is an idea conceived by brilliant guy named Danny Hillis way back in the eighties. The idea is to build a clock as a symbol for long term thinking. And you can kind of just very conceptually think of the 10,000 year clock as it, you know, it ticks once a year, it chimes once, you know, every hundred years, and the cuckoo comes out once every thousand years. So it just sort of slows everything down. And it's a completely mechanical clock. It is designed to last 10,000 years with no human intervention. So the material choices and everything else, it's in a remote location both to protect it, but also so that visitors have to kind of make a pilgrimage. The idea is that over time, this will take hundreds of years, but over time it will take on the patina of age, and then it will become a symbol for long term thinking that will actually, hopefully get humans to extend their thinking horizons. And my view, that's really important as we have become, as a species, as a civilization, more powerful, we're really affecting the planet now. We're really affecting each other. We have weapons of mass destruction. We have all kinds of things where we can really hurt ourselves. And the problems we create can be so large, you know, the unintended consequences of some of our actions, like climate change, putting carbon in the atmosphere is a perfect example. That's an unintended consequence of the industrial revolution, that a lot of benefits from it. But we've also got this side effect that is very detrimental. We need to be. We need to start training ourselves to think longer term. Long term thinking is a giant leverage. You can literally solve problems if you think long term that are impossible to solve if you think short term. And we aren't really good at thinking long term, as you know, it's not really. We're kind of. Five years is a tough timeframe for most institutions to think past, and we probably need to stretch that to ten years and 15 years and 20 years and 25 years. And we do a better job for our children or our grandchildren if we could stretch those thinking horizons. And so the clock is, in a way, it's an art project. It's a symbol. And if it ever has any power to influence people to think longer term, that won't happen for hundreds of years. But we have to. We're going to build it now and let it accrue the patina of age. 

# Speaker A
Do you think humans will be here when the clock runs out here on earth? 

# Speaker B
I think so, but, you know, the United States won't exist. Like, whole civilizations rise and fall. 10,000 years is so long. Like, no nation state has ever survived for anywhere close to 10,000 years. 

# Speaker A
And the increasing rate of progress makes that even less likely. 

# Speaker B
So do I think humans will be here? Yes. What, you know, how will we have changed ourselves and what will we be? And so on, so on? I don't know, but I think we'll be here. 

# Speaker A
On that grand scale, a human life feels tiny. Do you ponder your own mortality? Are you afraid of death? 

# Speaker B
No, I'm, you know, I. I used to be afraid of death. I did. 

# Speaker A
I. 

# Speaker B
Like my, like, I remember as a young person being kind of, like, very scared of mortality, like, didn't want to think about it and so on, and always had a big. And as I've gotten older, I'm 59 now. As I've gotten older, somehow that fear has sort of gone away. I don't, you know, I would like to stay alive for, as long as possible, but I'd like to be, it's, I'm really more focused on health span. I want to be healthy. I want that square wave. I want to, you know, be healthy, healthy, healthy, and then gone. I don't want the long decay, but, and I'm curious, I want to see how things turn out. You know, I'd like to be here. I love my, my family and my close friends and I want to, I'm curious about them and I want to see, so I have a lot of reasons to stay around, but it's, mortality doesn't have that effect on me that it did, you know, maybe when I was in my twenties. 

# Speaker A
Well, Jeff, thank you for creating Amazon, one of the most incredible companies in history. And thank you for trying your best to make humans a multi planetary species, expanding out into our solar system, maybe beyond, to meet the aliens out there. And thank you for talking today. 

# Speaker B
Well, Lex, thank you for doing your part to lengthen our attention spans. Appreciate that very much. 

# Speaker A
Thanks for listening to this conversation with Jeff Bezos. To support this podcast, please check out our sponsors in the description. And now let me leave you with some words from Jeff Bezos himself. Be stubborn on vision, but flexible on the details. Thank you for listening and hope to see you next time.
""",
}
