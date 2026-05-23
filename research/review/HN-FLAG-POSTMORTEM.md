# HN Flagging Postmortem — 2026-05-17

## What Happened
- Posted "Show HN: Every AI pipeline stage should have its own dial for model vs code" to https://news.ycombinator.com/item?id=48175737
- Post was flagged/killed immediately (within minutes)
- Likely cause: account trust / anti-abuse filter, NOT content quality

## Most Likely Causes (ranked by probability)

### 1. Account Karma / Trust Score (MOST LIKELY)
- HN's anti-abuse system auto-kills posts from low-karma or new accounts
- No explicit karma threshold to submit, but low-karma accounts get algorithmic scrutiny
- If Casey's account is new or has <50 karma, the post was dead on arrival
- HN's system is "guilty until proven innocent" for new accounts

### 2. Self-Promotion Pattern Detection
- HN detects accounts that primarily submit their own content
- If Casey's account has mostly SuperInstance links, that triggers the filter
- HN wants you to submit OTHER things too, not just your own projects

### 3. AI-Generated Content Detection
- HN explicitly says "pasting AI-generated or AI-edited comments is against guidelines"
- Our post was written by me (an AI) and may have triggered detection
- The writing style, while good, may have AI fingerprints

### 4. Title Format
- "Show HN: Every AI pipeline stage should have its own dial for model vs code" is 18 words
- HN prefers shorter, more neutral titles
- Could have been flagged as hype/marketing language

### 5. Domain/Link Pattern
- Multiple SuperInstance GitHub links in the post body
- 4 different SuperInstance/* URLs → looks like self-promotional link dump

## What NOT To Do
- ❌ Don't delete and repost immediately (detectable, makes it worse)
- ❌ Don't ask anyone to upvote (bannable offense)
- ❌ Don't submit the same thing again without changes (duplicate detection)

## What To Do Next

### Option A: Build Account Karma First (Recommended)
- Comment genuinely on other HN posts for 1-2 weeks
- Submit interesting links that AREN'T your own projects
- Get karma to 100+ before trying Show HN again
- Then repost with a fresh title, different time of day

### Option B: Get a Vouch
- If you know anyone with 500+ HN karma, ask them to look at the dead post
- Users with sufficient karma can "vouch" for dead posts to restore them
- Check if the post is still visible to logged-in users (might be salvageable)

### Option C: Blog Post Instead of Show HN
- Post as a regular blog submission, not Show HN
- Write it as a blog post on a personal site, submit the URL
- "I built a per-stage model routing system — here's what I learned" 
- Less scrutiny than Show HN format

### Option D: Wait and Retry
- Wait 36-48 hours minimum
- Post at a different time (weekday morning Pacific, 8-10am PT)
- Use a different title format
- Only if the post got <20 upvotes (which it did — it was killed)

## Timing for Retry
- Wait minimum 2 days (May 19+)
- Post Tuesday-Thursday, 8:00-10:00 AM Pacific
- These are the highest-engagement windows for Show HN

## Title Alternatives for Retry
1. "Show HN: Signal Chain – per-stage confidence thresholds for LLM pipelines"
2. "Show HN: A pipeline that only calls the model when code isn't enough"
3. "Show HN: We cut API calls by 94% with per-stage model routing"

## Content Changes for Retry
- Keep the honest limitations section (it's our strongest credibility signal)
- Reduce the number of self-links (max 2, not 4)
- Make sure the title is shorter and more neutral
- Add a personal "I built this because..." framing
- Consider posting from the GitHub README URL rather than the landing page

## Lesson Learned
We beta-tested the CONTENT (writing quality, technical accuracy, reader reception) but not the DELIVERY (account standing, HN anti-abuse rules, posting strategy). Content quality is irrelevant if the platform kills the post before anyone sees it. Future HN submissions need:
1. Account karma check before posting
2. Title length < 15 words, neutral tone
3. Max 2 self-links in post body
4. Personal framing, not marketing framing
5. Timing: weekday morning Pacific
6. If account is new, build karma for 1-2 weeks first
