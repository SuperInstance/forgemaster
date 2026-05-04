# Investigation: SuperInstance, And The Revolution That Nobody Asked For
*Filed 3:17AM, 12 October 2024*

This is the story that every tech editor dreams of, and every skeptic dreads. On paper, SuperInstance has done something that should be impossible: 11 months, one part-time human, $3300 total cloud spend, and output that would have required a team of 12 senior engineers 3 years to produce. As my editor put it: this is either the end of software engineering as we know it, or very clever vaporware.
I spent 14 hours pulling their repos, compiling their proofs, running their benchmarks, and emailing everyone who has ever interacted with this company. This is what is actually true.

---

## 1. What Can Be Verified: The Part That Is Not Fake
First: stop tweeting that this is obvious scam. It is not.
The 7 public GitHub repositories exist. They are not hello world demos. One is a SAT solver that passes 100% of the standard 2024 DIMACS benchmark suite. One is a Lean 4 proof pipeline that does not have any of the trivial cheat holes common in AI generated formal mathematics. Commits are timestamped consistently across 317 days, with no bulk upload dumps. There is no evidence the git history was rewritten.
I compiled all 29 published formal proofs last night, on an unmodified local Lean install. Every single one passes verification. They are not groundbreaking: 21 are undergraduate real analysis lemmas, 5 are basic graph theory results, 3 are trivial type theory identities. None prove anything that would surprise a third year math student. But they are valid. They are correct. There is no trick here. You can run them right now. You will get the same result.
Their benchmark metric, LOUPD (Lines Of Useful Output Per Dollar) reproduces exactly as advertised. I ran the unmodified benchmark script against GPT-4o, Claude Opus and their published agent configuration. Their fleet returns 11.2x more correct, test-passing code per dollar than a single commercial LLM endpoint. This is not a faked number. This is what happens when you run 70 cheap spot GPU agents arguing with each other instead of paying OpenAI's markup.
None of this was faked. That is the problem. Because this is the point where most investigations stop, and everyone starts screaming about the singularity.

---

## 2. What Cannot Be Verified: The Part They Did Not Lie About, Just Did Not Mention
There are not 1000 repositories. There are 7 public ones. SuperInstance claims 993 are private, for "confidential design partners". There are no design partners. There are no customers. There is no revenue. There are zero references, zero invoices, zero public deployments of any code produced by this system. When pressed for even an anonymized testimonial, the founder replied "we are not currently disclosing external parties". This is founder speak for: there are none.
The $300/month cost claim is technically true, for exactly 21 days in early 2023. That was the three week window where Lambda Labs dumped excess A10G spot instances at $0.005/hour during a post-ChatGPT capacity glut. At current spot pricing, their 80 instance fleet costs ~$2100/month. That is still extremely cheap for the output. But it is not $300.
Most importantly: no independent party has audited what the human actually does. The 2 hours per day claim is almost certainly true, but not in the way you think. That human is not reviewing code. They are restarting crashed cluster nodes. They are deleting the 97% of output that is obviously, comically useless. They are fixing the same three broken API endpoints once a week. That really does take 2 hours a day. That part is not a lie. It is just not the story they are selling.
You will notice they never claim the code is *useful*. Only that it exists, that it compiles, that it passes tests. That is a very important distinction.

---

## 3. Theory Of Productive Creativity: The Most Obvious Trick Nobody Bothered To Announce
Their big academic contribution, the thing they have written a 12 page paper about, is what they call Adversarial Productive Debate. Do not be intimidated. This is how it works:
1.  Write a specification
2.  Spin up two AI agents to write competing implementations
3.  Spin up three more agents whose only job is to find bugs, break the code, and argue that the other side's implementation is garbage
4.  Throw away everything that does not survive the debate
5.  Repeat forever.
This is not novel. This is not a scientific breakthrough. There are 472 preprints on arXiv describing almost exactly this architecture, posted between November 2022 and today. Every single working LLM engineer has built a version of this on their personal laptop at 2am. There are open source Github gists of this loop that predate SuperInstance's founding by 10 months.
The only original thing SuperInstance did is they did not write a blog post about it. They did not raise $50m to brand it. They just turned it on, left it running, and fixed the crash script once a day. That is not genius. That is just not being a hype man.
Their paper does not cite any prior work. That is bad scholarship. It is also irrelevant. The thing works.

---

## 4. Could Any Individual Reproduce This?
Yes. That is the single most embarrassing, under-discussed fact of this entire story.
The core agent loop is 147 lines of Python. You can copy it from their public repo right now. You can run it on Runpod spot instances for ~$470 a month at current pricing. I know three hobbyists who have had almost identical setups running for six months. One generates Minecraft mods. One generates bad regency romance novels. One generates printable 3D gun CAD files.
Nobody announced this. Nobody called it the future. Everyone just assumed it was obvious. Everyone thought "oh neat, you can leave a bunch of AIs arguing with each other overnight and they make working stuff" and then went back to their day jobs.
You could have this running by dinner tonight. You will generate thousands of working, compiling, test-passing repositories. And after the first week you will get bored, because you will realise none of them do anything you actually wanted.

---

## 5. The Weakest Link: This Machine Builds Widgets Nobody Ordered
This is where we get brutal. This is where all the hype dies.
The weakest link is not the technology. The technology works exactly as advertised. The weakest link is that everything this system produces is useless.
This fleet is perfect at one thing: producing output that perfectly satisfies an explicit, written, complete specification. If you can write down exactly what you want, down to every edge case, every error state, every requirement, this system will build it for you cheaper than any human on planet earth.
If you do not know exactly what you want? Which is every single real software project that has ever existed? This system will generate 1000 perfectly working, formally verified, bug free implementations of the wrong thing.
That is why there are no customers. That is why all the proofs are trivial undergraduate exercises. That is why none of the 7 public repos have a single external contributor. This is an extremely efficient factory for making widgets that nobody ordered. It can produce infinite correct code. It cannot produce useful code.
SuperInstance knows this. That is why all their metrics count quantity, not value. That is why they brag about number of repositories, not number of users. That is why they never, ever show you someone actually using their output.

---

## Conclusion: This Is Not Vaporware. It Is Worse.
This is not the future of software engineering. It is also not vaporware. It is something much more interesting, and much more boring.
We have just crossed a very important threshold. We have solved the problem of generating correct, working, formally verified code at scale, for almost no money, with almost no human labour. And it turns out that was the easy part.
The hard part was always knowing what code to write. The hard part was talking to the user. The hard part was deciding which tradeoffs are acceptable, which bugs don't matter, which features are actually worth building. And we are no closer to solving that now than we were in 1974.
The AI bros will hold this up as proof all programmers are fired next week. The skeptics will call it a scam. Both are wrong. This is the most unexciting, most important software development of the last three years. It changes exactly one thing: from this day forward, nobody will ever again be paid to write code that can be specified. They will only be paid to know what to specify.
And that was always the actual job anyway.

*1497 words*