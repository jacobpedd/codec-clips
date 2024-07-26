from django.core.management.base import BaseCommand
from django.conf import settings
from langsmith import Client


NEW_EXAMPLES = [
    {
        "input": {
            "metadata": {
                "reasoning": "This clip captures an entertaining and heated debate about who is to blame for ruining a surprise baby shower. It showcases the personalities and dynamics between the hosts, which listeners would likely find amusing.",
                "start_index": 95,
                "end_index": 196,
                "start": 289548,
                "end": 492788,
                "name": "Baby Shower Surprise Debate",
                "summary": "A humorous discussion unfolds as the speakers debate the responsibility of revealing information about a surprise baby shower. They highlight the nuances of communication, confusion over invitations, and the inherent surprises that both organizers and guests experience. The conversation navigates through the topic of accountability among friends, with playful banter as each speaker deflects blame while offering amusing anecdotes about their lack of involvement and knowledge in baby shower traditions. The tone is light-hearted and sarcastic, filled with camaraderie and wit.",
            },
            "transcript": """
# A 0:01
# B 0:23
1 I want to talk about something, but I know that I need to discuss it very delicately because I know that it's a dangerous topic that has led to, let's just say, outbursts.
2 And I want to have this conversation and avoid the outburst, and I just want to have it in a civil manner.
# A 0:44
3 Why are you looking at me?
# B 0:45
4 I'm just looking around.
5 I'm just looking.
6 I can look to the audience at home.
7 I just.I want to have a conversation, discuss something.
# C 0:51
8 Does it have to do with spoiling parties?
# B 0:52
9 But I'm afraid the reaction that might come as a result of this conversation, and this is a controversy the likes of which this office has never seen before.
10 Moments ago we were preparing to do mystery crate, and we also have a co worker who's going to have a child.
11 And we had a planned surprise baby shower.
12 And before said planned baby shower, we were about 2 hours out from it at the time.
13 This has been in the works for weeks now.
14 Many texts, sentence texts have been sent.
15 A lot has been going on behind the scenes to plan this and to have this be a successful surprise baby shower.
16 And then a co worker of ours apparently received bad intel and went up to the person who's having the baby and the surprise baby shower and said, hey, gotta go.
17 I'm not gonna be here for the baby shower.
18 Just wanted to, you know, wish you the best or whatever.
19 And then everybody who was around kind of froze because everybody knew what was going on.
20 And then that person immediately realized what happened and said, dammit, was it a surprise?
21 Oh, Fuentes told me it was not a surprise.
22 And this person knew and immediately threw Fuentes under the bus and the surprise was ruined.
23 And Fuentes got very angry at the accusation that did not get very angry.
24 He got very defensive.
# D 2:19
25 No, I didn't get defensive.
# B 2:20
26 He got very defensive at the situation.
27 The implication that he ruined the surprise baby shower and screamed out one of my favorite lines that I've heard in a long time here.
28 I have like three lines that I've heard like this week that I loved.
29 And Fuentes screamed out one of them just moments ago while not being angry and not being upset.
# E 2:40
30 Not angry or defensive, it was, welcome to Mystery Creek.
# C 2:43
31 Yeah, welcome to Mystery Creek.
# B 2:44
32 No, what he screamed out was, we're 40 effing years old.
33 Why are we still doing surprises?
# E 2:52
34 You know what?
35 You are absolutely right.
36 Why are we still doing surprises?
37 Man, we're getting too old for this shit.
# D 2:57
38 This, this, this place is obsessed with surprises.
39 We have four birthday cakes a week, and every single one's, like, on the hush.
40 It's like.It's like they know it's their birthday.
41 You can just sing happy birthday for more context.
# C 3:07
42 It was Mike Ryan that ruined the surprise.
43 I wasn't gonna name names.
# B 3:11
44 Why?If you feel bad about not getting a birthday cake, I will tell you.
45 On your birthday, we sang happy birthday to Juju.
46 So there was a cake on your birthday.
47 You just weren't here.
48 We were celebrating another birthday.
49 And to Fuentes Point now in the fridge, slash freezer for cake, four cakes.
# C 3:29
50 Now I'm about to point something out, and I want to say that I could not care less that I didn't receive a baby shower here, but this is the first baby shower we've had in these parts.
# B 3:39
51 Yeah, we never had.
# C 3:41
52 We had many a baby around these parts.
# D 3:42
53 Apparently.It's surprise.
# C 3:44
54 I'm just saying, you know, we're scheduling, you know, baby Billy had a baby a couple years ago.
# B 3:48
55 A year ago.
56 Where.
# C 3:49
57 Where was that baby shower?
# B 3:50
58 Yeah, I didn't have one.
59 That's fine.
# C 3:51
60 Yeah, that's my point either.
# A 3:52
61 I don't want one.
# C 3:55
62 I am curious, our decision for this one to be, like, now we're doing a baby show.
# B 3:59
63 Well, this person's liked.
# D 4:00
64 Oh, yeah.
# C 4:01
65 I think you're like, you're not liked.
# D 4:02
66 Nobody's liked.
# C 4:03
67 You're not liked.
# B 4:03
68 I would say the issue that we're having now, though, is now the president has been set the precedent.
69 That's why.And I, to my knowledge, we have two other babies on the way.
70 So are we having two more baby.
# C 4:14
71 Showers or two more slippers, or are.
# B 4:17
72 We now gonna have a joint baby shower?
73 Moving forward, like, how does this end?
# C 4:21
74 I'm kind of good with all, like, we not.
75 Weren't us not doing it.
76 I'm good.I don't want to start the president.
77 We're now.We're now we're.
78 It's doing president.
# D 4:28
79 Yeah, president.What?
# A 4:29
80 I keep saying president.
# C 4:31
81 I know.
# A 4:32
82 President's on the mind.
# B 4:33
83 There's a precedent.
# D 4:34
84 There's a cine.
# C 4:35
85 I know.I don't talk good.
86 I know.
# E 4:37
87 Well, don't talk well.
# C 4:38
88 I did that on purpose.
# E 4:39
89 Okay, there you go.
90 I'm just making sure.
# C 4:41
91 I know precedent.
# E 4:42
92 So there's no baby coming.
# B 4:44
93 Fuentes.Yeah, Fuentes.
94 Any apologies you feel are in order or are you good?
<CLIP>
95 You feel like that was all cleaned up?
# D 4:51
96 I'm not responsible for what other grown men say.
97 So he.He went and, you know, he.
98 His.His exact quote to me was, I'm 99% sure that this isn't a surprise.
99 So he already had it, had it in his mind.
100 It was not a surprise.
101 So I, and then I responded to him.
102 I said, I am also 99.9% sure, yes.
103 That it is not a surprise because one, I've never been to a baby shower or been involved in a baby shower in my life.
104 To me, that's for other people.
# B 5:16
105 Oh, yeah.
# D 5:16
106 So this for other people.
107 I've never been involved in any baby shower festivities, planning or any, or things ever.
# B 5:24
108 To father.
# D 5:25
109 Yeah, it's not my kid.
# B 5:26
110 Well, I will say this.
111 On Friday we got a text.
112 It was an invitation that was sent out.
113 The invitation itself doesn't say anything but the message.
114 And he says, hi, everyone.
115 We're throwing a surprise in all capital letters, baby shower for, you know, said person at the studio, blah, blah, blah, date and time.
116 There's a register if you want.
117 If not, you can get diapers, blah, blah, blah.
118 And then some emojis.
119 Right.And then yesterday at 06:27 p.m.
120 we got a reminder.
121 Hello all.Reminder.
122 Tomorrow is blank's surprise baby shower at 230.
# C 5:54
123 That hurts.
# B 5:55
124 So we got aaa.
125 Double surprise there.
# C 5:58
126 Still 99% sure.
# B 5:59
127 Yeah.
# D 6:00
128 When someone asks me something, yes, he can continue to do research.
129 Well, I didn't know I was this bastion of information.
# C 6:08
130 First.
# D 6:09
131 Everyone surprised person do this a lot.
# C 6:13
132 You love to give helpful information.
133 You need to admit when you don't know somebody.
134 But that's my point.
135 You always think you know.
136 Kind of.
# D 6:19
137 Yeah, I thought I did know.
138 But it's not my responsibility if I'm gonna go blabbing trying to leave early.
139 Well, that, I didn't, I didn't say, hey, you haven't.
140 I'm sorry.
# B 6:28
141 I don't know if that matters.
# D 6:29
142 Yeah, but I didn't, I don't, I don't have to say like, I didn't ruin the baby shower.
143 I just gave information.
144 He could ask somebody else.
145 He could have checked the phone.
146 He could have checked through his 3000.
# C 6:38
147 Shouting from the other.
# B 6:40
148 I will say this.
149 He's, he was also then he was in.
# D 6:46
150 Are responsible for their own fights happening.
# A 6:48
151 Here's the response Billy was worried about.
# B 6:50
152 See, that's what I trying to avoid.
# E 6:52
153 One of the people that were playing this baby shower is into the room.
154 That's Cynthia.
# D 6:56
155 That's.
# F 6:56
156 First of all, first of all, I.
# D 6:57
157 Didn'T say, I didn't say anything about the baby shower.
158 Mike said it.
159 So whose fault is it?
# E 7:01
160 You, one of the mics?
# F 7:02
161 If someone is asking you for information about something.
162 Give them the complete information.
# D 7:07
163 Oh, so now I'm responsible?
164 You are information that I don't.
# F 7:10
165 You are responsible to answer properly.
# E 7:14
166 You missed a word in there.
167 And that was surprised.
# D 7:16
168 When Cynthia comes out to me and says, mike, is it okay for me to punch Ethan in the face?
169 I say, yeah, sure.
170 And then she goes, okay, first of.
# C 7:21
171 All, you're thinking something could do with me.
172 Fuentes said for some reason that she could, even though he's not.
# D 7:28
173 It doesn't.It has nothing to do with.
174 I did not ruin the surprise.
175 Mike Ryan did.
176 It's not my fault he didn't follow up with somebody else.
177 Basically, Mike Ryan's real Mike, right?
# F 7:36
178 Basically, yes.
# D 7:37
179 Mike Ryan.Mike Ryan's real fuck up was asking me in the first place.
180 You needed a second opinion.
# B 7:41
181 Well, you give off the bastion of information.
# D 7:44
182 We all know that Kristen and Cynthia are responsible for these things.
183 Go ask them.
# B 7:48
184 Well, I love a good pie chart.
# F 7:50
185 I just.I just love deflecting.
186 And it's never anyone's specific fault.
187 No, it's still gonna be abused.
# B 7:57
188 Baby show.
# F 7:58
189 Are we sure about that?
# D 7:59
190 I'm just the guess.
# B 8:00
191 He was.He was not.
# F 8:01
192 It's never your fault.
193 It's always everybody else.
# B 8:03
194 He was upset about the idea of group texting at one point as well, if I remember correctly.
# F 8:09
195 And we were all very well behaved on that group text.
196 No one responded.
</CLIP>
197 It didn't get crazy.
# B 8:13
198 Well, can I be honest with you?
199 I didn't respond because I was worried that someone included him in it, and I was like, there's a high probability there was an oversight, and he's on this group text, and it will be ruined in this group text.
200 Right.
# D 8:25
201 So you're saying that he's gonna be in a group text where they're talking about his surprise baby shot.
# B 8:29
202 I thought it was entirely possible.
203 I thought it was entirely possible.
204 That's why I was like, a group tech.
205 Seems very dangerous with this situation.
206 This is a word of mouth thing.
# C 8:37
207 At best, on the pie chart of blame.
208 All right, we got 10% for Cynthia and Kristen just for planning this thing.
# D 8:42
209 Thank you.
# C 8:43
210 Ten, then.40% Mike Ryan.
# D 8:47
211 Way closer to, like, that's at least 80%.
# C 8:49
212 50%, my friend.
213 That's 50%.
# E 8:52
214 Wow.
# F 8:53
215 Thank you.Thank you, Chris.
216 Chris gets it.
# D 8:55
217 No, it's 70% Mike Ryan, because he's the one that blew it.
# A 8:57
218 If you expect.
# D 8:58
219 I'll take 20%, Mike.
220 And I didn't even say that I was 100% sure.
221 I set up 99%.
222 That's what he has said.
# A 9:06
223 Earlier.
# F 9:06
224 99.
# B 9:07
225 But there's a margin.
# D 9:08
226 There's a margin for error.
# C 9:09
227 One sentence to Mike Ryan.
228 I don't know.
229 How about when you say 99% sure?
230 You're sure?
# D 9:14
231 Like, he doesn't.
232 I'm not.I'm not sure.
# F 9:17
233 Can you do me a favor?
234 Can you reread the very first sentence of that text message?
# B 9:21
235 It was all capitalized and bold.
# D 9:23
236 And when was that sent in gold?
# F 9:25
237 And when was it resent again?
# B 9:26
238 And then there was one yesterday also.
# F 9:28
239 Okay, thank you.
240 So fuck off.
# B 9:29
241 Whoa.Okay.
# E 9:30
242 There you go.
# B 9:31
243 That sounds very necessary.
# E 9:32
244 I think it is super necessary.
# B 9:34
245 Had he just seen the.
# F 9:35
246 He told me to fuck off earlier, so why can't I say yes?
# E 9:39
247 You did.
# D 9:39
248 That's.That's even more egregious than the fuck off.
# A 9:42
249 You don't.
# F 9:42
250 You don't always remember everything you said.
251 I just want you to.
# D 9:45
252 You know what, guys?
253 I'm done with surprises.
254 No surprises.
# E 9:47
255 No more surprises.
# D 9:48
256 There's five cakes in the.
# F 9:50
257 He's.He's mad.
# B 9:50
258 Why?
# F 9:51
259 He's upset.
# B 9:52
260 I don't think anyone's directly blaming you.
# D 9:54
261 I mean, I shouldn't have any blame.
262 I'll give myself 20.
263 I'll give myself 20% for having false information.
# B 10:00
264 Well, no.
# E 10:04
265 Misinformation.
# F 10:06
266 You did not complete the information.
# D 10:07
267 This is what happens, you know, on Twitter.
268 This doesn't happen anymore.
269 Community notes.Somebody should have community noted.
270 Me.
# B 10:11
271 Yeah.When it.
# A 10:13
272 Well, never your fault.
# B 10:14
273 Can I ask you something?
274 When did this conversation between the two of you happen?
275 Because no one saw that happen.
276 Because had someone seen that, then the correction could have been made immediately.
277 Like, when did he ask you?
278 Is this a surprise?
# D 10:25
279 I was like, right before he went over there.
280 Maybe five minutes before he went over.
# B 10:29
281 Okay, well, then this needs to be investigated, because you were at the community table, and there were a lot of people around.
282 See, I was over by the person who's having the party.
283 And I will admit I didn't do a great job because it was me, it was Taylor, and it was Thomas sitting around this person.
284 And then the surprise was ruined, and all of us immediately froze up and just looked at him like, terrible under pressure.
# F 10:51
285 I knew something was wrong.
# B 10:53
286 It was odd because he's just like, hey, I'm sorry.
287 I'm not gonna be here for.
288 I'm not gonna be able to make it.
289 And then we all, like, kind of looked up, and we're like, no, no, stop talking.
290 Like, stop talking.
291 But, like, can't say, like, stop talking.
292 And then he was like, what do you mean?
293 Like, when he's like, for the baby shower.
294 And then he's like, wait, what?
295 And then instead of anyone, like, kind of stepping in, and at that point, it's gone.
296 Right?Like, we've lost it.
297 But he just immediately goes to Mike Fuentes, give me the wrong information.
298 And immediately threw Mike Fuentes under the bus.
299 And he goes, was this a surprise?
300 Mike Fuentes give me the wrong information.
# E 11:25
301 That's a deflection.
# C 11:26
302 Is our co worker who's here and the surprise was ruined for is his.
303 The mom to be the wife.
304 Did she know about this?
# D 11:33
305 Yes, she's coming.
# C 11:36
306 I got news for all of you.
# D 11:37
307 He knew exactly.
# B 11:38
308 So, no, he did not tell you.
# C 11:40
309 He's gonna play like he did because.
# F 11:42
310 We know who this person is.
# C 11:44
311 Our marriages work.
312 That's on you.
# B 11:45
313 Hold on.
# D 11:46
314 That's what got me just.
# F 11:47
315 We asked him, because did you know?
# B 11:49
316 Of course.No.
317 This person would tell this person, back channels were worse.
# C 11:54
318 Marriages work.You don't undercut.
319 Your wife said to him, if you.
# B 11:58
320 Tell them that I believe this, no back channels were worked.
321 And I will also.
322 I will also say this.
# C 12:05
323 You know how many times you guys have been laying in bed like, all right, so you're not right.
324 Couples share everything with each other.
# D 12:10
325 And here's another thing.
# B 12:12
326 Affairs wouldn't exist.
# D 12:13
327 How often is the said individual hear it at the time that this is taking place?
328 Unless he's in meetings, he's not here at that time.
329 Okay, so all of a sudden, he's sitting around for an hour.
# B 12:22
330 Well, the original issue was it was supposed to be on a Friday, and then it had to be figured out.
331 If he's not here a lot of Fridays, how do we make this happen?
332 And I will also say this to the point.
333 Point that he did not know is many discussions in the idea or the ideation of this surprise.
334 It was discussed, he will not like this.
335 He will hate this happening because he hates.
336 And then we said, yeah, it's gonna be so much better.
337 That's why.It's gonna be even better.
# D 12:51
338 Yeah.
# B 12:52
339 Cause he's gonna hate this.
# F 12:53
340 And figured it out and had a whole thing, and we even had other.
# C 12:57
341 You guys are adorable.
342 That.You think she didn't tell him.
# F 12:59
343 No, she does not.
344 She didn't.
# C 13:01
345 I get it.
# B 13:02
346 I feel like she would.
# C 13:04
347 That could be covered up.
348 Like he could know.
349 He could come in here and say he didn't.
# B 13:07
350 I think she would want him to be embarrassed.
# C 13:09
351 Right?She did.
# F 13:09
352 And she was part.
353 She liked that.
# C 13:11
354 I could picture him hating it.
355 So that part I will maybe give.
# B 13:14
356 You guys it anyway, so.
# E 13:15
357 Anyways, anyone?
# F 13:16
358 So there you go.
# B 13:17
359 No more surprises.
# F 13:18
360 Baby shower.
# B 13:18
361 Moving forward.You're welcome.
362 Do we just, do we just.
# A 13:21
363 Dan, do we kidding, obviously.
364 But for just a half a second, for just a half a second, the entire audience freaked out.
# B 13:29
365 Yeah.
# D 13:30
366 When's one surprise baby shower?
# C 13:32
367 Why is that the third one?
# D 13:34
368 You.
# C 13:34
369 We mentioned a third.
# B 13:35
370 No.
# D 13:36
371 No.
# B 13:36
372 Yeah.
# F 13:36
373 Just tell them I plan on having.
# D 13:39
374 A kid in the next two years.
375 Can you guys plan the surprise?
# B 13:41
376 No, see, look, I don't.
377 I didn't know if it was public information that you was having a kid.
378 That's why they're all gonna get a name.
# D 13:48
379 They're all gonna get bleeped out.
# B 13:49
380 You're gonna.Well, I mean, now they know the relation to you, so he'll bleep out that he's.
# A 13:53
381 You don't bleep out.
# B 13:54
382 Dan, can I say something?
383 We should.And, and, and I don't think a lot of people agree with me on this.
384 I feel like you're gonna become an uncle, so you should get a surprise as well in that baby shower.
385 You know what I mean?
# D 14:05
386 Surprise uncle Shower.
# B 14:06
387 Yeah.
# D 14:06
388 That's gonna get Crimson on it.
# F 14:07
389 That's not how that works.
# D 14:08
390 I'm already an uncle.
391 He has one already.
# B 14:09
392 I know, but you're gonna be, it's a great, wonderful, you know, thing.
393 You don't, you don't seem to feel any remorse or bad at all.
# F 14:15
394 No, he is standing ten toes down.
# D 14:17
395 I did nothing wrong.
# C 14:18
396 So he thinks he's.
397 We're getting a glimpse of what it would be like to date Mike Fuentes right now.
# F 14:22
398 I'd rock your world, rock it with annoyance.
# B 14:26
399 And do you know, you know, you're just not wrong on things.
# D 14:30
400 I'm not saying I was wrong that I gave the wrong information, but I don't blame myself for someone else ruining.
# B 14:35
401 Here's the issue.
402 Here's.
# C 14:36
403 Dude, do you hear that?
404 What you just said?
# D 14:38
405 I don't blame myself ruining a surprise.
# B 14:40
406 No, here's the.
# D 14:41
407 I said the wrong thing.
408 I'm sorry.Got crossed up.
# C 14:43
409 I'm sorry information.
# D 14:44
410 My whole life is not consumed by when this said individual.
# A 14:47
411 I do.
# C 14:48

""",
        },
        "output": {
            "start_index": 1,
            "start_change": True,
            "end_index": 193,
            "end_change": True,
        },
    },
    {
        "input": {
            "metadata": {
                "reasoning": "This clip covers the hosts' analysis of recent political developments, including Joe Biden's potential stepping down and the rise of Trump-supporting tech investors. It provides insider perspectives on current events that could attract viewers interested in politics and tech.",
                "start_index": 588,
                "end_index": 629,
                "start": 1945640,
                "end": 2120686,
                "name": "Tech Titans and Trump's Influence",
                "summary": "The clip discusses the recent endorsements of Trump by notable tech figures, including Elon Musk, Mark Andreessen, and David Sachs, amidst their controversial financial contributions to a Trump super PAC. Scott highlights the skepticism surrounding their motivations, particularly focusing on the belief that a Trump presidency may benefit startups and Bitcoin investments. The tone is sharp and satirical, critiquing the 'losers' in tech backing Trump and their perceived small-mindedness. The hosts analyze Trump's intersection with tech politics, mentioning JD Vance's dubious career record and Peter Thiel's significant influence, all while contrasting the views of Silicon Valley voters who favor Biden.",
            },
            "transcript": """
# B 25:22
# A 25:24
495 I'd be the way he tried to get down the stairs.
496 I mean, I'm at a point where I think you're gonna have a lot of anger among Democrats, like, who the fuck made the decision to hide all of this shit from us?
497 I mean, who thought that was a good idea, to even believe that if they just managed it all, they could cosplay a competent president for the next four and a half years?
# B 25:46
498 Well, let me be fair.
499 He's been competent, Scott.
500 He's been doing whatever.
501 It's team Biden or whatever they've been doing, vigorous.
502 Despite all the stuff at the republican convention, like taking credit for the economy, taking credit for this.
# A 25:59
503 And that's fair.
# B 26:02
504 You can't have gramps wandering around the west Wing without some.
505 He's very, like, when he did the foreign policy stuff, sharp as a friggin tack, right?
506 It was very good.
507 And so I think it's just a question of focus and what's interesting to him.
508 Right.I do that, too.
509 I won't talk about things I'm not interested in anymore.
510 I'm like, no, I refuse to speak of that.
# A 26:26
511 But where I was headed with it is that as it became evident that he just should not, he should drop out, the risk of the chaos and the disorganization became a risk worth taking.
512 And that's where we are.
513 Is that the risk and the chaos and the insecurity of how this plays out with an untested candidate that might not have as much name recognition, all the candidates bring their strings, strength and their, and hair.
514 The risks are now definitely worth taking.
515 And so people are going to be.
# B 26:55
516 Mad at us for saying that.
# A 26:57
517 Yeah.So I, but look, this is, this has gone on too long.
518 It is time, and there's just no doubt about it.
519 Also, they, they must be freaked out on the DNC side about how moment, how much momentum Trump has.
520 If Trump came out of this the last couple of weeks, weekend, Orlando, and the polls haven't been that bad for Trump, and I'm sorry the polls haven't been for Biden, and Biden had kind of a little bit better performance, not even a great performance on Stephanopoulos and Lester Holt.
521 I think there still would be a lot of people saying it's not worth the risk.
522 And they have a point now.
523 The risk is a risk worth taking, and I think everyone's coming around to that.
# B 27:34
524 Yeah, I would agree.
525 In the midst of all the campaign chaos, Biden is reportedly making some big moves when it comes to the Supreme Court.
526 He's finalizing plans to endorse major changes to court in coming weeks, as we suggested, including proposals for terminal limits for justice is an enforceable ethics code.
527 According to the Washington Post, those changes would be subject to congressional approval, which is a long shot given the make up of the House and Senate right now.
528 If Biden doesn't drop out of the race, you know, it could be a Hail Mary to get people to stay with him.
529 You know, if they do win the House and the Senate, they can do these things, right.
530 The president, if Trump is vetoed, he's not, Trump is not a fan of these proposed changes, calling them an illegal and unconstitutional attack on the Supreme Court.
531 Court in a true social post.
532 But we're with you, Joe, on this one.
533 We think of term limits.
534 We love them.
# A 28:21
535 Yeah, I think it makes sense.
536 I don't know if we'll go through, we've said this before.
537 I think there are few institutions that have lost as much brand equity, but the Supreme Court used to be towards the top.
# B 28:31
538 This is ridiculous.
539 And it shouldn't just be for Clarence Thomas and whatever scam he's perpetrating.
# A 28:36
540 Well, but to be fair, it's presented a real challenge for Justice Thomas because he faced a situation where both sides of a case, both offered him really awesome scuba trips and he just didn't know what to do.
# B 28:52
541 I know.He should come back.
542 I thought that was good.
# A 28:55
543 I thought that would get a laugh out of you.
544 Get it?Both sides of the case.
# B 29:00
545 Scuba trip.
# A 29:02
546 Really awesome scuba trip to belize.
# B 29:04
547 Like Belize.A belizean scuba trip for insane spending with rich people.
548 Anyway, we're going to get to rich people in a second.
549 All right, Scott, let's go on a quick break.
550 When we come back, we'll talk about big tech investors turning to Trump.
# A 29:23
551 Support for pivot comes from Greenlight.
552 A lot of people don't love to talk about the best ways to responsibly manage money.
553 But you know who really doesn't like to talk about it?
554 Children.Well, with Greenlight, you can introduce your kids to money management in a fun and easy way and teach them how to spend and save for the future.
555 Greenlight is a debit card and money app made for families.
556 You can send money to your kids and keep an eye on their spending and savings.
557 The Greenlight app also includes a chores feature where you can set up one time or recurring chores customized to your family's needs and reward kids with allowance for a job well done.
558 The best endorsement I can give is that we were a Greenlight family before they ever contacted us.
559 At Pivot, the Greenlight app also comes with games that teach kids money skills in a fun, memorable way.
560 You can sign up for Greenlight today and get your first month free when you go to greenlight.com pivot.
561 That's greenlight.com pivot to try greenlight for free.
562 Greenlight.com pivot.
# C 30:22
563 Support for pivot comes from the world as you'll know it.
564 A podcast about the forces shaping our future.
565 Most people understand the reality of climate change.
566 You can see and experience the effects.
567 But what's harder to see is what's being done to combat it.
568 On this season of the world as you'll know it, they go deep inside the technological revolution to replace fossil fuels with clean energy.
569 It's a monumental task and is a story full of big successes, major failures, difficult grinding work, and enormous promise.
570 You can meet the scientists, engineers and entrepreneurs taking this challenge on, and they dig into questions about technologies can you make clean steel at scale?
571 Can you capture carbon from the atmosphere and lock it underground?
572 The show looks at how solar power became cheaper than gasoline, at batteries that can power longer and longer drives, and at air conditioners that might be able to keep us cool without heating up the planet.
573 It's a new season of the world as you'll know it, the great rebuild, available wherever you get your podcasts.
# D 31:22
574 When you bring your own phone and switch at a San Francisco Verizon, you get three lines for the price of two.
575 Which is perfect if like, you're a couple with a daughter who's ready for her own phone.
576 Or maybe you have a son who wants to be able to text you and definitely not his girlfriend.
577 Or a brother who wants in on the deal.
578 Or your uncle could really use a line.
579 Or your wife has a sweet but clingy twin sister, or your best friend from college relies on you.
580 Give him a free line.
581 Or you guys have a roommate who's kind of a mooch, or your dog walker needs a solid.
582 Or your wife's ex boss's dermatologist attorney's best friend could also use a line.
583 Anyway, you get the idea.
584 Bring your phone and get three lines for the price of two and pay less than $29 a line.
585 Visit a San Francisco Verizon store now and save $180 BYod promo credit per phone and $720 local promo credit applied for 36 months for new customers activating three new lines with your own 4g or 5g phones on unlimited welcome plan required.
586 Additional terms apply auto pay and paper free billing required in times of congestion.
587 Unlimited five G and four G LTE may be temporarily slower than other domestic data roaming at 2g speeds.
# B 32:25
<CLIP>
588 Scott we're back with our second big story.
589 More big names in tech are getting behind Trump, although not that many.
590 Like they put a list together and it was all the same losers and small dick energy that's always been.
591 In addition to his endorsement, Elon reported his plans to commit around 45 million.
592 But that's today.
593 It got a little sketchier to the new Trump super PaC.
594 According to Wall Street Journal, he's trying to get people to do it.
595 Elon, by the way, has pushed back against that report about his $45 million super back contributions.
596 The Wall Street Journal says it stands by its reporting, and I, for one believe the Wall Street Journal.
597 Mark Andreessen and Ben Horace did tell the firm they intend to make significant donations to Trump PAC, explaining on their podcast this week that they believe the former president is better for startups.
598 Mark Cuban.I would urge you to read his explanation.
599 They want an environment where bitcoin will do better with cyber stuff because Mark Andreessen and Ben Horse have a huge investment in, in that area.
600 And so tariffs and lower taxes would be better for bitcoin, etcetera.
601 And there'll be inflation, too.
602 Investor David slacks even had a slot at the RNC convention that he bought.
603 Oh, did I say that out loud?
604 Where he reportedly met with tepid response by convention attendees.
605 I got a lot of texts like, who is this clown?
606 And I was like, welcome to my world.
607 So here we have it.
608 Here they have, they're trying to buy a presidency, essentially.
609 I think Trump doesn't get what just happened with JD Vance.
610 Let me just take a moment.
611 We talked about him last week.
612 His job record is not good in tech.
613 Let me just say, including Steve Kate saying he didn't do much right when he worked for him.
614 He had a firm that didn't do well.
615 He had one company took public that's gone bankrupt.
616 He essentially was, it was really interesting because Rachel Maddow did a great thing on him this week where she basically called him an intern for Peter Thiel.
617 Peter Thiel got him all his jobs and then gave him money to run Senate and now has pushed him right into Trump's arms, including getting the Senate endorsement, which was critical to him, and then convincing Donald junior to press the president for this.
618 So, you know, this has been a beater teal operation the whole time.
619 I have to tip my hat to him because I do think he's quite brilliant.
620 Not so much David Sachs, but he certainly is.
621 But you know, it's a small group of people.
622 They put up a list of them.
623 David Sachs did.
624 And it's all like the Winklevosses and a bunch of other, this Sean McGuire person who never shuts up.
625 Is it, it's all these unpleasant VC's.
626 And when you, the information did a poll of voters in Silicon Valley and it was overwhelmingly Biden over Trump.
627 The average people and startup people and this and that, it's mostly these incredibly afflicted vc's who think they're victims.
628 So, you know, and there's others on the other side, obviously, Reid Hoffman, Mark Cuban, et cetera, et cetera, et cetera.
629 Quietly, General Sandberg.
</CLIP>
# A 35:20
630 It is a dramatic shift, red, because in past, I think the past couple of presidential elections, you've had like 80 plus percent of the dollar volume coming out of the value has gone democratic.
631 These are real players.
632 The thing that struck me was that I found it.
633 A couple of things.
634 One, for Sequoia and Andreessen to come out and be this political overly must mean that they have such extraordinary, they feel they have such extraordinary upside, probably around bitcoin, probably around some sort of dialogue they've had with President Trump, that if he's elected, he's going to do something that totally legitimizes or integrates bitcoin technology into whatever the Federal Reserve or fiscal planning or some sort of monetary policy that would take the price of bitcoin and crypto so far up that they've decided it's worth the risk.
635 Because what I got to think here is, if I'm sequoia has, like, Ottawa teachers or the state pension fund from Michigan as limited partners, I got to think right away, they got letters saying, okay, let's be clear.
636 We gave you money to get an above market return investing in startups.
637 We are not interested in taking the pensions of teachers, of public school teachers in Michigan and having it go to a Trump pack.
638 So the deal here must be, on the face of it, so incredibly lucrative in terms of upside for them to publicly come out of, in favor of Trump.
# B 36:48
639 Let me, let me just read.
640 Let me read Mark Cuban's thing.
641 Here's a contrary opinion on the emergence of Silicon Valley support for President Trump.
642 And I agree with him.
643 This is all about money.
644 Let me be clear.
645 These people, I've never heard a value out of these people, including any values.
646 They don't have any values.
647 Their values are themselves and their money, and they love themselves.
648 That's what they love.
649 That's it.Which, like all my opinions here, probably popular.
650 It's a bitcoin play.
651 Not because former president is a far stronger proponent of crypto.
652 That's nice, but because.
653 But it doesn't really impact the price of crispr.
654 It makes it easier to operate a crypto business because of the inevitable required change at the SEC, but will drive the price of bitcoin as lower taxes and tariffs, which, if history is any guide, it's not, always will be inflationary.
655 Combined with the global uncertainty as to the geopolitical role of the USA and the impact on the US dollar as a reserve currency, you can't align stars any better for the bitcoin price acceleration.
656 How high can the price go?
657 Way higher than you think.
658 Remember, the market for bitcoin is global and the supply has a final limit of 21 million bitcoins with unlimited fractional.
659 Keep in mind, you consider this happens because of geopolitical uncertainty and decline in the dollar and it keeps going crazy.
660 It already happens in countries facing hyperinflations and thing will go further than we can imagine today.
661 I'm not saying it will.
662 Then bitcoin becomes exactly what the maxis envision, a global currency.
663 I was like, Mark always thinks of things that I don't think of.
664 I have to say he had the same idea around AI that I thought was super on it anyway.
# A 38:17
665 But the thing that's disappointing here is it's one thing when people.
666 So first off, Citizens United, it's too much money in politics.
667 It is what it is.
668 The Supreme Court has decided that money is free speech, okay?
669 It is what it is.
670 People have the right to give money and it's going to result in influence.
671 This seems to have taken it, though, to kind of a next level of pay to play, that these are specific issues that aren't even connected to any sort of ideology or political way of thinking.
672 It's a general notion that if I give $45 million a month, I'm pretty sure he will place slap tariffs on BYD, the largest chinese EV company.
673 I'm pretty sure that if these, if we and Andreessen give a lot of money to Trump, that he will do what we want around crypto.
674 This is, this feels like a kleptocracy.
675 It's not supporting political ideology.
676 It's just if I give you enough money, you will use the strength and the reach of the government to ensure that I get.
677 I get sweetheart deals.
# B 39:22
678 And they're also trying to go against competitors.
679 Elon's way behind in AI.
680 So attack OpenAI, attack Google.
681 One thing that's interesting is what JD Vance, we'll talk about in a second.
682 But one of the things Elon's bought Twitter and made it assessful, but it's also part of a play, which Mark Cuban told me was he said, this isn't about Twitter or anything else that comes out of his stupid.
683 It's about his global impact in terms of dealing with autocrats and his other businesses.
684 Right.He always was like, focus on his businesses, Karen, not his stupid remarks about trans people, even though they're stupid, you know, but he's erased any era of neutrality for the platform.
685 The New York Times noted.
686 Another thing I would note is back in March, I said he was going to back Trump and back him heavy.
687 And his stance came down on me like a ton of bricks when I said that on Jennifer Jen Psaki show and.
688 Right.You know, because I know he wants money.
689 And that was sort of inspired by my discussion I had with Mark Cuban, I think it was 100% right.
690 He predicted that.
691 And this role of JD Vance in all this is interesting.
692 You know, he's kind of a tech bro butler.
693 He's a tech bro butler.
694 He's like a billionaire butler.
695 Peter Thiel's been holding his hand the whole time, you know.
696 You know, holding everything to help him along the way.
697 You know, it's literally like.
698 And they say everyone gets on their own merit.
699 This guy is like a poster child for special needs.
700 He keeps getting pushed upward, even though he's not that particularly successful.
701 But he has those stances.
702 He's bullish on crypto.
703 He owns bitcoin.
704 He's actually praised FTC Chairlina Khan.
705 He's a conservative for her efforts to crack down on big tech.
706 But the tech he's going after is Google, because in his words, it's explicitly progressive technology company.
707 They're also going to Facebook, which is interesting.
708 Mark Andreessen's on the board of that.
709 He's called for the reform section 230.
710 He's just in there.
711 He's in their pocket.
712 I just don't know what else to say.
713 What do you think?
# A 41:21
714 Yeah, like I said, it feels like a kleptocracy.
715 It's pay for play.
716 It's not on ideology.
717 I think we've covered this.
718 The place I disagree with you on JD Vance, does he have the credentials to be vice president?
719 Probably nothing.He.
720 Well, I don't know.
# B 41:39
721 He's been there a year and a half.
722 Scott.He's passed regulation.
# A 41:42
723 How long was Obama.
# B 41:43
724 I get that.
725 But nonetheless, he's passed no significant registration.
726 He had no business.
727 He had no business success.
# A 41:52
728 I'm not a fan of the man.
729 I think that when the scariest thing, in my view, around Trump is that he's, in my opinion, lacks focus and wants to take us to the handmaid's tale in 2025, if you're interested, is literally a manifesto for where they're planning to go.
730 And the thing that scares me about Vance is that he has said repeatedly, I don't care about Ukraine.
731 And generally speaking, throughout history, when world leaders have shown, western leaders have shown an indifference to an autocrat invading Europe, it doesn't end well.

""",
        },
        "output": {
            "start_index": 588,
            "start_change": False,
            "end_index": 638,
            "end_change": True,
        },
    },
    {
        "input": {
            "metadata": {
                "reasoning": "This clip contains a shocking and dramatic story about a woman protecting her husband's niece and nephew from a pit bull attack while her husband abandons them. It's an emotionally charged, self-contained narrative that's likely to generate strong reactions and discussions about courage, relationships, and moral obligations.",
                "start_index": 11,
                "end_index": 70,
                "start": 26190,
                "end": 268268,
                "name": "Husband Abandons Wife During Dog Attack",
                "summary": "A wife recounts a traumatic incident where she defended her husband's niece from a pit bull, while her husband fled the scene in panic. The discussion revolves around trust, betrayal, and the impact of fear during emergencies. The emotional tone is intense and raw, shedding light on feelings of abandonment, trauma, and a potential rift in their marriage. The speaker reflects on the gravity of the husband's actions and questions whether this might warrant forgiveness or lead toward divorce, revealing deep-seated frustrations about child care arrangements and marital expectations.",
            },
            "transcript": """
# A 0:03
1 Shots left and right.
# B 0:06
2 I know they know our next play.
# A 0:07
3 Before we even make it.
4 We gotta tighten up off the court too.
5 Businesses track and sell our personal information.
6 They dunk on us all the time with that data.
# B 0:16
7 Wait, what do you mean?
# A 0:17
8 You have to exercise your privacy rights?
9 If you don't opt out of the sale and sharing of your information, businesses will always have the upper hand.
# B 0:24
10 The ball is in your court.
<CLIP>
11 Get your digital privacy game plan at privacy dot ca dot gov dot welcome to r relationship advice where Ops husband abandons his wife to be eaten alive by a rabid pit bull our next Reddit post is from throwaway.
12 Some advice I'm a 31 year old woman and my husband is 31.
13 I had to protect my husband's niece from a pit bull and my husband ran off.
14 Ive been ignoring him since.
15 Is this something that I should forgive him for?
16 Im going to start by saying that im still a bit traumatized.
17 Ill be finding someone to talk to.
18 I dont know if the pit bull survived the attack.
19 I havent asked me.
20 My husband and my husbands niece and nephew were in our backyard.
21 Im going to assume our gate was open, but I cant remember.
22 Suddenly this pit bull came out of nowhere and latched onto his five year old niece.
23 His niece screamed.
24 I turned and kicked the pit bull with all the force that I could manage.
25 I was lucky enough to hit it in the jaw somewhere that made its jaw dislodge.
26 My husband, who was a few feet away, shouted something along the lines of whose dog is this?
27 I told him to get our bear spray from the house.
28 I was in a panic.
29 Im an animal lover but it was so insane.
30 The pit bull seemed almost rabid.
31 I dont think that it was rabid in hindsight.
32 It wasnt foaming at the mouth, it was just crazed.
33 My husband ran, but not towards the house.
34 He literally ran out of the fence gate and shut it behind him.
35 He didn't run towards his niece or his nephew.
36 His nephew, by the way, was also present in an outdoor bassinet.
37 What?So that means wow.
38 That means the nephew had to have been like a baby.
39 A straight up baby, maybe one year old, probably younger.
40 Wow.That is okay.
41 I wasn't expecting that.
42 I managed to all but toss the bassinet onto the picnic table to make sure that it was out of the dogs reach.
43 All this while holding his niece on my shoulder.
44 I put her on top of the barbecue to keep her out of reach, but the dog was literally jumping and snapping and I was worried that if I tried to carry his niece im sure it would manage to grab her out of my hands.
45 It chased me but I swung at it and I just kept swinging until it stopped.
46 I dont think ill ever forget the sound or feeling.
47 It was so high stress I didnt even realized that it had bit me twice.
48 I havent spoken to my husband for a full week even though we live in the same house.
49 I didnt even ask him where he ran off to.
50 He only came back a few minutes later to pack us into the car and drive us to the hospital.
51 Hes now angry at me for giving him the silent treatment, but I feel like its his fault that I was the one who had to fight the animal.
52 If he had just gotten the bear spray, which I literally keep in my purse then I dont think that I would have had to do what I had to do.
53 The bear spray was literally just inside the door of our house.
54 He knows where I keep it.
55 Instead he took off to God knows where me and those two children who by the way im not even related to, could have died.
56 This detail might not even be relevant, but I dont even like kids.
57 Im staunchly child free and my husband was the one who offered to babysit for the weekend.
58 I dont know.
59 Is this grounds for divorce?
60 Im not sure I can even look at him.
61 Any attraction I had to him is pretty much gone.
62 He tried to touch me yesterday just to move me so that he could pass by and I smacked his hand away without even thinking about it.
63 Like he was some stranger at a bar because it was literally jarring.
64 Hes been sulking around the house trying to talk to me and then getting frustrated, then sulking more.
65 I wasnt expecting him to be macho and fist fight the freaking dog, but at least follow instruction.
66 At least don't abandon me to a life or death situation with a toddler and an infant.
67 Should I chalk this up to a moment of panic?
68 I don't even know if I want to hear him out.
69 There's absolutely no coming back from this.
70 No way on earth.
</CLIP>
71 I do understand that people can't really expect to act a certain way in a life or death situation because adrenaline makes people do crazy stuff.
72 But yo, abandoning your wife and a toddler and a child to die while you go run away like a scared little baby?
73 Nah man, I couldn't come back from that.
74 There's no way.
75 Also down in the comments we have this story from I'm smarter there was an incident during a bonfire night when my daughter was six.
76 We were in the neighbor's garden setting off fireworks, and one of the fireworks went sideways and came straight for us.
77 My neighbor grabbed her granddaughter and my daughter and covered them up.
78 I had my grandson in my arms, so I turned away to shield him.
79 Also, both my ex and my neighbors husband moved towards the problem to help.
80 However, my neighbors daughter, the mother of those kids, ran past her mother to safety.
81 She abandoned both of her kids.
82 It was a small little moment, but it changed everything.
# B 5:26
83 My neighbor never really sided with her daughter again.
84 Her daughter developed substance abuse issues, and multiple times my neighbor took custody of her kids.
85 From that day on, my neighbor never trusted her daughter again.
86 She showed who she was that night.
87 And op, your husband showed you believe him.
88 Then one day later, op posted an update.
89 And I'll summarize because these updates tend to be kind of long and dry, so I'll just stick to the juicy parts.
90 First off, op sought the help of a mental health professional, which is good.
91 Op continues.Last night, I told my husband that I needed space.
92 I wasnt as nice as I wanted to be.
93 He argued and didnt want to leave.
94 Its my house, but I told him that I just didnt want to look at him, that I couldnt look at him.
95 He cried, and I hate that.
96 I felt apathetic towards it.
97 As for my husbands sister and her husband, as in the parents of the niece and the nephew, they arent speaking with my husband.
98 I dont know when this happened, but the truth definitely got out at the hospital while I was getting stitches.
99 After I was done blubbering and trying to explain how something so terrible happened to their little girl under my watch, they apparently asked him where he was.
100 Whatever answer he gave, it clearly didnt satisfy them.
101 His niece just got out of the hospital yesterday, so that really triggered everything and a lot happened.
102 I had sent her flowers, a bear, and this one toy that she had been asking about.
103 I didnt go to the hospital, though.
104 I was scared that seeing that little girl would make her nervous.
105 But his sister and her husband sent me flowers, too, which made me bawl.
106 Im just a freaking mess, honestly.
107 The father sent me a long message that I havent been able to get through, but its the sweetest thing that anyones ever sent me.
108 He also sent me $1,000.
109 Theyre good people, and I still feel terrible that I couldnt have done more for her.
110 Anyways, I havent looked into filing for divorce yet.
111 I know that fight or flight cant be helped, but now I think I realize that its okay to not want to be with someone who would leave you behind.
112 I think I can say that im a fighter, and I want a fighter with me.
113 Maybe hed be better off with a runner instead, too.
114 Then he at least wouldnt be leaving someone behind.
115 Wow.The way op talks makes it clear that she has zero love for him.
116 We may have even tipped into the negative love value spilled over into, like, hatred.
117 It sounds like she actually has contempt for her husband.
118 Anyways, Opie continues, I dont know.
119 It feels like im done, but im also just a mess.
120 So right now, I'm glad that I have space.
121 Man, op, I think you're a million percent justified.
122 I don't know how anyone on earth could be with someone or even want to be with someone who would abandon you to die.
123 Yo, I just put something together, a detail that I didn't even register when I was reading the story.
124 He closed the gate behind him when he left.
125 He closed the pit bull in the yard with his wife and the children.
126 How did I miss that?
127 That makes it so much worse.
128 Anyways, Op, I think what you should do here is try to put aside the hatred that you're feeling towards your husband and focus on the positive here.
129 Because you literally saved the lives of two kids.
130 That makes you a hero.
131 You're you're just.
132 I mean, there's no other way to put it.
133 You're a hero.
134 Op.Round of applause for Op.
135 Our next Reddit post is from throwaway lantern misses.
136 I'm a 26 year old woman, and my boyfriend is 28.
137 My boyfriend has become obsessed with the lantern that he found at a flea market, and it's getting weird.
138 How do I approach this?
139 So my boyfriend and I recently went to a flea market, and he found this old style lantern that he absolutely fell in love with.
140 He bought it on the spot, and I thought that it was a cute little vintage decoration for our apartment.
141 But now things have taken a strange turn.
142 Ever since he got the lantern, he's become super attached to it.
143 He keeps it by his bedside and even gets up in the middle of the night to walk around the apartment with it, pretending to, pretending to be an old timey watchman.
144 He'll say things like, all is well, or the night is dark and full of terrors, and he really gets into character.
145 At first, I thought that it was kind of funny and endearing, as he's always had this eccentric style of humor, but now it's starting to annoy me.
146 He does this almost every night, and it's disrupting our sleep.
147 I've tried to talk to him.
148 I've tried to talk to him about it, but he just tells me that he takes his watch, that he takes his watchman duties very seriously, and that it's important for our safety.
149 The issue is, I genuinely can't tell if he's joking.
150 Well, op, you're still alive, aren't you?
151 Has anyone else experienced something like this?""",
        },
        "output": {
            "start_index": 12,
            "start_change": True,
            "end_index": 76,
            "end_change": True,
        },
    },
    {
        "input": {
            "metadata": {
                "reasoning": "This clip discusses the controversial short-selling of Trump's stock and potential connections to powerful figures like George Soros and Blackrock. It's likely to generate interest and discussion about political influence and financial manipulation.",
                "start_index": 476,
                "end_index": 524,
                "start": 1303012,
                "end": 1469916,
                "name": "Investigating Soros, Vanguard, and BlackRock's Influence",
                "summary": "This clip dives into the murky connections between major financial players like George Soros, Vanguard, and BlackRock, dissecting ownership stakes and investment strategies. It humorously references conspiracy theories surrounding George Soros, including his son's cryptic tweets linked to a recent tragedy. The tone is conversational and speculative, mixing insightful observations with casual banter, as the speakers explore the potential implications of these financial relationships on politics, specifically regarding Trump's antagonists. The mention of JP Morgan's controversial ties to Epstein adds a spicy layer to the discussion, enhancing the intrigue and highlighting the complexities of financial ethics.",
            },
            "transcript": """
# A 14:22
# B 14:32
318 Yeah.
# A 14:32
319 Yeah.John Heath Hinckley.
320 He tweeted this out.
321 Violence is not the way to go.
322 Give peace a chance.
# B 14:40
323 Being sarcastic.
# A 14:41
324 I don't know, man.
325 Listen, I don't know.
# B 14:43
326 He's out now, though.
# A 14:44
327 I think he is out.
328 He's, like, playing, you know, ukulele's and shit now.
# B 14:47
329 I don't.
# A 14:47
330 But, like, I just thought that was interesting.
# B 14:49
331 Yeah.
# A 14:50
332 Like, of all people.
# B 14:52
333 Yeah.
# A 14:52
334 All right, cool, dude.
# B 14:53
335 You know that he did that because he was obsessed with Jamie Lee Curtis, the actress, and he was trying to impress her.
# A 15:00
336 Is that what it was?
# B 15:01
337 Yeah.He thought if he killed Reagan, she would like him.
# A 15:03
338 Jamie Lee Curtis, though, like.
# B 15:05
339 Well, back then, bro, she was like a thing.
# A 15:07
340 Was she?
# B 15:07
341 Oh, yeah, dude.
342 Back in the, like, seventies.
343 She was like it really?
344 Oh, yeah, dude.
# A 15:13
345 Huh?Yeah.Yeah.
346 That's weird.Yeah, yeah.
# B 15:17
347 Oh, bro.She was like the thing.
# A 15:19
348 Really?
# B 15:20
349 Oh, yeah.Her and John Travolta and all like that era.
# A 15:22
350 That was it.
# B 15:23
351 Oh, yeah.
# A 15:23
352 Bush and all, huh?
353 Huh?
# B 15:25
354 Yeah.Oh, yeah.
355 Full bush.Yeah, bush heavy.
356 Yeah.
# A 15:32
357 Right?Yeah, yeah.
358 I mean, it's interesting.
359 Now.Now, this is where this.
360 This is where I had to put my, my investigator goggles on the right, and I did some sort of.
# B 15:41
361 Your beer goggles.
# A 15:42
362 Huh?
# B 15:43
363 Huh?Like your beer goggles.
# A 15:44
364 Bush light goggles.
365 Yeah, yeah.
# B 15:46
366 You got that bush heavy goggles.
# A 15:48
367 No, but I had to do some digging and, you know, I should, you know, put an actress here.
368 That was definitely.
# B 15:54
369 Actress.
# A 15:55
370 What is it called?
# B 15:56
371 I put an actress there.
# A 15:57
372 What's it called?
# B 15:58
373 An asterisk.
# A 15:59
374 What did I say?
# B 16:00
375 You said you're gonna put an actress over there.
# A 16:02
376 Is that what I said?
# B 16:03
377 Well, let's play it back and see what he says.
# A 16:05
378 That really what I, you know, put an actress here.
# B 16:07
379 All right.
# A 16:08
380 I.
# B 16:08
381 We'll put one of those extras.
# A 16:10
382 I'm gonna put access here.
# B 16:11
383 Okay.
# A 16:13
384 Because, you know, this computer thing, I'm still having some challenges.
# B 16:16
385 I know.It's like reading.
386 It's hard.
# A 16:17
387 It's difficult.It's difficult.
388 And, you know, but we covered a little bit yesterday, on yesterday's episode about this shortage that this put on these stocks that happened on Donald John Trump's bro.
389 And we, like, we know because we didn't know who did it.
# B 16:34
390 No, we.By the time, I think yesterday when we were recording, it hadn't really come out yet.
# A 16:38
391 No, there's new information, but we got some stuff here.
# B 16:42
392 Yeah.
# A 16:42
393 And the company, the company that did it is a company that's based here in America, based in Austin, Texas, called Austin Private Wealth, LLC.
394 Now, I guess we should lead first.
395 The company has put out a statement.
396 This is their official statement.
397 They put this out today, or, I'm sorry.
398 Yesterday, July 17, the statement reads, quote, the SEC filing, which showed that Austin private wealth shorted a large number of shares of Trump media and technology group Corp.
399 Or DJT, was incorrect, and we immediately amended it as soon as we learned of the error.
400 No client of APW holds or has ever held a put on DJT, and the quantity initially reported, the correct holding amount was twelve contracts, or 1200 shares, not 12 million shares, as was filed in error.
401 In submitting the required report for the second quarter of 2024, a multiplier was added by a third party vendor that increased the number of the shares by a multiple of 10,000 for all option contracts, not just Djtanh.
402 We did not catch the error before proving the filing, we filed the report on July 12 to reflect our positions on June 28.
403 We amended it on July 16.
404 Then they continue to say, we deeply regret this error and the concern it has caused, especially at such a fraught moment for our nation.
405 We are committed to full transparency and maintaining the trust of our clients.
406 As such, we are reviewing our internal procedures and our processes with a third party vendor that assists with SEC filings to better understand how this happened and avoid similar issues moving forward.
407 Now, I'm not a calculator, but 1200 versus 12,000 in there.
408 Like an extra zero in a twelve month.
# B 18:45
409 Oh, yeah.1212 contracts, 1200 shares to 12 million, right?
# A 18:51
410 Not, I mean.
411 Yeah, well, in the, in the contract sense it's twelve.
412 1200 versus 10,000.
413 Like that was the added.
414 Isn't that a difference in numbers or something?
415 Like the place of the decimal point?
416 You know, you subtract the two and multiply.
# B 19:04
417 Yeah.What I'm trying to figure out is did they actually file this?
418 So, so this is actually filed.
419 So, and then they're saying, oh, we made a mistake and they amended it.
420 Okay, so we accidentally executed that guy.
# A 19:18
421 Right.
# B 19:18
422 Sorry.We weren't supposed to.
# A 19:19
423 We attempt, we tried to, we thought it was gonna, you know, be successful.
# B 19:23
424 Yeah.
# A 19:24
425 And it wasn't.
# B 19:25
426 Yeah.So, so do they gotta, do they lose all that money that they bet?
# A 19:29
427 Yeah, I don't know.
428 I mean, I think there's still, there's got to be some SEc repercussions here, right?
429 Because, I mean, the end of the day, that money's gone.
# B 19:35
430 Well, who, who's the third party?
431 Well, no, who, who owns this company?
# A 19:40
432 Well, that's interesting you say that, Andy.
433 So I did a little digging.
434 Austin private wealth.
435 And this, this is where this shit gets really, really deep.
436 And I know we try to be careful, you know, these are, all this I got.
437 This is not speculation.
438 These are real facts.
439 We'll link all of this stuff here for you.
440 These are.
# B 19:55
441 It's important to state that the show, the show is, the show is speculation.
# A 19:58
442 Show is speculation.
443 But these, like, these are the most verified sources you can get.
444 These are straight from government websites.
445 These are government filings.
446 Everything I'm about to show you, these are real things.
447 There is no bullshitting this, all right?
448 But I looked into this.
449 So APW, they manage about a billion dollars of market share, essentially, of stocks, portfolios for about 1200, almost 1300 clients.
450 Now, there's this form, it's called a 13 f.
451 That kind of puts together a lot of stuff that kind of shows, you know, who they're heavily, who heavily invests, who they're managing, what clients they're managing, who's the main shareholders and stakeholders in this company.
452 And, you know, you look, and there's some common ones, you know, the ones that I don't, you know, really attribute to much.
453 There's Google's on there.
454 They have quite a few.
455 And if you look here, you can kind of see the amount.
456 This is the number we want to focus on here.
457 This is.So this is apples.
458 You know, they got a couple of different ones.
459 20,000, 28,000.Right.
460 Like, not a big contributor.
461 But they're in there.
462 Apple's in there.
463 Of course.Of course.
464 Metas in there.
465 Right?Again, you look at Metas.
466 Meta's number, I mean, it's nothing too crazy.
467 4400.And, you know, twelve, like, these are equivalent to twelve shares.
468 Four shares, right?
469 Like small numbers.
470 Nothing too crazy there.
471 JPMorgan Chase is in there again, you know, eight shares, half of one.
472 Shit like these, nothing too crazy.
473 But then it gets interesting.
474 Blackrock, I've heard that name before.
475 Have you heard that name before, Andy?
# B 21:43
<CLIP>
476 Yep.
# A 21:43
477 Let's look at the difference on these numbers.
478 That would be the equivalent of about 800 shares of this.
479 That's a big number.
480 That's a big percentage.
481 It's a big percentage.
482 Who else is in there, man?
483 Vanguard.Vanguard.That's all that.
484 That's Vanguard.And it shows them divided up because Vanguard breaks themselves off into trust and all these different, you know, entities all under the same thing, but a shit ton of shares by band, by vanguard, too.
485 I'm like, man, that's interesting.
# B 22:15
486 Now, who's behind Vanguard?
# A 22:17
487 What's that, guys?
488 Rhymes with oros.
489 What's his name?
# B 22:21
490 I think it's the same guy I said yesterday was responsible for this.
# A 22:24
491 Most likely the Georgie.
492 Yeah, Georgie Soros, man.
# B 22:27
493 Yeah.And then.
494 And then do we remember what his.
# A 22:29
495 Son tweeted with the glass breaking.
# B 22:32
496 With the glass breaking and the dollar 47.
497 And then the hole through the glass.
# A 22:38
498 And the place that the shooter was on was a glass place like they made.
# B 22:42
499 That's right.That's right.
500 The building that the shooter, the who can't shoot was a glass manufacturer.
501 Manufacturer.
# A 22:52
502 And that.Interesting.
503 And then Black Rock had a commercial.
# B 22:56
504 So you have George Soros, who's heavily invested in Vanguard.
505 And then you have vanguard owning the most shares of this fund.
506 Then you have Alex Soros tweeting a picture with a bullet hole through the glass and $47 when the shooter was standing on a glass factory.
507 I'm sure it's nothing.
# A 23:25
508 Sure.Sure.It's not the Blackrock.
509 Blackrock's heavily invested in this.
# B 23:29
510 I mean, who are the people that have really turned against Trump over the last four years in 2020 and in through.
511 I mean, you got meta, you got Alphabet, you got Blackrock.
512 And you got Vanguard.
513 All of those guys owning the company that supposedly shorted Trump stock the day after or the day before he was assassinated.
514 It's almost like I said that yesterday.
# A 24:01
515 It's weird.Now it gets even.
516 It gets even deeper.
517 So there's a.
518 Like I said, JP Morgan Chase are also in there a little bit, right?
519 JP Morgan chase.
520 For those of you guys who forgot, they're affiliated with Epstein.
# B 24:16
521 Yeah.
# A 24:17
522 They are the.
523 The money bank that was facilitating all of these payments for Epstein.
# B 24:23
524 Yeah.And remember when the governor of the US Virgin Islands tried to, uh, subpoena them, George?
</CLIP>
525 Or, I'm sorry, Biden flew down there that day, fired her.
# A 24:34
526 Isn't that weird?
527 Yeah, that's interesting.
528 Now let's get a little deeper.
# B 24:37
529 Same day, the same day that she filed, that she was going to do.
# A 24:40
530 This unexpected trip for no reason.
531 Yeah, like, there was not.
532 It was not even, like, scheduled, like, a emergency trip down there.
533 Now it gets.
534 It gets a little deeper, man.
535 So on the SEC's website, you can again link all this stuff for you.
536 Austin private wealth.
537 This is their company snapshot.
538 This is a list of their six approved managing members for this company, right?
539 These are the brokers who are making these trades right?
540 Now, most of these people have been there.
541 You know, there's a few from 2019.
542 That's the majority of these guys.
543 Now, I want to say these.
544 All of these guys came from one other company called Ameriprise, which is another institution that does stock trading.
545 They actually manage, like, almost half a trillion dollars and assets is insane.
546 And you'll see the same similarities there.
547 But one guy in particular stood out to me, and it's this last guy here, this Joshua Charles Dobrak.
548 Okay?I'm like, man, you know, he's fairly new to that company.
549 He's fairly new into their.
550 Their ranks there.
551 And I'm like, okay, well, who is this guy?
552 So I went and I found this IAPD report, which is what the SEC puts together on every single broker.
553 Again, this is all public information.
554 You guys can.
555 Can find this here.
556 And it's a report, it's a couple of pages that shows, you know, his history as a broker, where he bent to any negative marks they get, like he was terminated from fudging some stuff when he was with fidelity.
557 It shows that he's a current registered member for Austin private wealth.
558 I'm like, man, where did this guy come from?
559 Who is this guy?
560 That's interesting.And guess what.
561 Guess what came up.
562 JP Morgan securities.
563 And guess when he was there.
564 Andy, during the same time Epstein was moving the money.
565 Now that may be nothing.
566 Might just be a big coincidence.
567 I don't know.
# B 26:28
568 Oh, yeah, sure it is.
# A 26:29
569 But that's fucking weird.
# B 26:31
570 Yeah.
# A 26:31
571 Well, that's fucking weird.
572 Now, another interesting thing that I should point out here.
573 When you go to Austin, privatewealth.com, you know, you find this, and they put that.
574 Notice that statement right up front and center on their homepage.
575 This is a screenshot of their homepage.
576 But I checked.
# B 26:45
577 Yeah, because they know they're caught.
# A 26:47
578 They're fucking caught.
579 But on the top, you know, they have all these.
580 These different tabs.
581 And there's this, like, in the community tab, right?
582 I'm like, man, like, you know, Austin's a pretty liberal place.
583 Most people know that about Texas.
584 Like, that's where a lot of the settlers went.
585 Let's.Let's see what they're doing in the community.
586 Right?I thought that was interesting.
587 So I went to the community page, and scrolling down, I was.
588 I was surprised, not surprised, to see, you know, they contribute to a number of organizations.
589 The American Cancer Society, the Austin Symphony, Boy Scouts of America, the Jewish Community Center, Shalom, Austin ACLU, the AdL, Congregation Beth Israel, the Austin Jewish Academy, or my personal favorite, the LDF, which is basically BLM on steroids for Austin.
590 They helped get off a lot of those protesters that were charged with destroying our country.
591 Now, they defended these people for free.
592 Andy, what do we make of all of this?
593 What do you, what do you, what do you got on all of this?
# B 27:55
594 I mean, look, anybody who can't connect the dots here or refuses to connect the dots is being willfully ignorant because they don't want to accept the reality.
595 You know, there's a lot of people out here right now who are saying that this was a false flag.
596 Dude.You can watch the video from the multiple angles.
597 And this wasn't like Trump throwing a ketchup packet on his fucking ear like some of these morons are trying to.
598 Trying to say.
599 Also, like I said yesterday, there's nobody in the world good enough to shoot someone's ear off a moving target from 150 yards away, all right?
600 Nobody, not a single person could do it.
601 And it shows the ignorance.
602 These people have a firearms and what can be done and what can't be done.
603 And then you see the other angle where the spectators were in the range of fire and taking fire, and you see the one guy, the one guy in the stands get shot.
604 This was this.
605 It is what it is, dude.
606 I mean, we've watched for the last eight years them villainize this man, demonize this man, attack this man, destroy his reputation, try to paint him as a criminal, criminal, try to cancel him, try to impeach him, tried to ruin his reputation.
607 They've literally brainwashed a percentage of the country.
608 And I think that percentage is small at this point.
609 I think most people see through the b's, but they brainwashed people based around things that were completely made up, like the Russia collusion.
610 And we go on and on and on, and they haven't been able to stop this guy.
611 And the more they push to stop him, the more he grows.
612 And that's because people can more clearly see what we're dealing with.
613 We're dealing with tyrants.
614 And it's good for us that we're dealing with incompetent, sloppy tyrants, okay?
615 Because we can see what they're doing.
616 And I think the game is up for these people.
617 I think everybody pretty much understands what happened.
618 They're just trying to figure out who.
619 But I think breaking down who is behind that SEC filing and that short on DJT stock is pretty fucking accurate to who's been attacking them the entire time.
620 Okay, so who would benefit?
# A 30:16
621 I mean, we're talking about half a billion.
# B 30:18
622 Look, dudes, there's no reason to skirt around it.
623 These motherfuckers did this.
624 They were planning on fucking getting this dude assassinated.
625 They wanted to try to make a bunch of money.
626 And because they were sloppy, it's now being exposed, and it's being exposed in real time.
627 You know, when they did this stuff with JFK 50 years ago, 60 years ago, whatever that was, there was no Internet.
628 There was only one narrative that could be presented.
629 Now we have, you know, thousands of cameras that were on that scene.
630 We have the ability to communicate information instantly.
631 It's just not the same environment.
632 And they're trying to run the same play and it's, it's exposing them at every chance.
633 And like I said, dude, I think, you know, yesterday I said, I think they might be trying to create a retaliatory, you know, action against Biden, but I don't think that's what they're going to do.
634 After kind of observing what's happening here, my opinion is obviously they're going to try again.
635 They cannot have this guy win.
636 You guys have to understand that, like, at any cost.
637 Yes.This isn't overdeveloped.
638 They're not going to stop.
639 This is, they're not going to allow this guy to win.
640 He's not going to win it.""",
        },
        "output": {
            "start_index": 387,
            "start_change": True,
            "end_index": 514,
            "end_change": True,
        },
    },
]


class Command(BaseCommand):
    help = "Create a LangChain dataset from critique inputs and outputs"

    def handle(self, *args, **options):
        dataset_name = "critique-eval"

        # Initialize LangSmith client
        client = Client(api_key=settings.LANGSMITH_API_KEY)

        # Check if the dataset already exists
        dataset = None
        datasets = client.list_datasets(dataset_name=dataset_name)
        for dataset in datasets:
            if dataset.name == dataset_name:
                print(f"Dataset {dataset_name} already exists")
                dataset = dataset
                break
        if dataset is None:
            # Create the dataset
            print(f"Creating dataset {dataset_name}")
            dataset = client.create_dataset(
                dataset_name=dataset_name, description=f"Critique examples"
            )

        for example in NEW_EXAMPLES:
            self.stdout.write(
                f"Processing example: {example['input']['metadata']['name']}"
            )

            # Create an example in the dataset
            client.create_example(
                inputs=example["input"],
                outputs=example["output"],
                dataset_id=dataset.id,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created dataset "{dataset_name}" with {len(NEW_EXAMPLES)} examples'
            )
        )
