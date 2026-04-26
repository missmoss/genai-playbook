# You're Not Talking to AI. You're Configuring a Probability Engine.

---

## You think you're having a conversation

You open ChatGPT, type a question, and it replies. You follow up, it continues. You correct it, it apologizes and adjusts.

The whole thing feels like talking to a person — one who's fast, knowledgeable, occasionally wrong but quick to fix mistakes.

That feeling is an illusion.

It's not that AI is deceiving you. It's that the chat interface is. It's the most successful product design in AI history — because everyone knows how to have a conversation, everyone can use it. But it's also the biggest cognitive trap: it makes you operate a fundamentally non-conversational system using conversational instincts.

---

## What human conversation actually does

We're so used to conversation that we never stop to think about what it actually involves. Break it down, and there are at least four things running simultaneously:

**Memory.** You don't re-introduce yourself every time you talk to a friend. They remember who you are, what you said last time, what you've agreed on. These memories accumulate into shared context.

**Intent.** When someone responds to you, they have a purpose. They might be trying to convince you, comfort you, make you laugh, or just get through the conversation. Whatever it is, their response starts from an intent, then finds expression.

**Mutual adjustment.** You frown, they rephrase. You nod, they go deeper. You go silent, they stop and ask what's wrong. Conversation is two people reading each other's reactions in real time and adjusting strategy accordingly.

**Accumulation of shared context.** Every turn builds new common ground. After the conversation, both sides understand more than they did before. The next conversation starts from a different place.

You never have to consciously activate these mechanisms. They're the defaults of human conversation. You were born with them, and you assume that anything that looks like a conversation has them.

That's the problem.

---

## What AI is not

**It has no memory.** Your conversation history with AI is technically called a context window, and it has a fixed size. Every turn consumes space. When the space runs out, earlier content gets compressed or dropped. A few turns in, the details you mentioned at the start are already getting fuzzy. You think it "remembers" — it just hasn't forgotten yet. And it's forgetting.

More fundamentally: it has no memory across conversations. Close the window, everything resets. Next time you open it, it doesn't know you.

**It has no intent.** It's not "answering" your question. What it's doing is: given all the text you've provided (your question + conversation history + system instructions), calculate the most likely next token (roughly, the next "word"), output it, then calculate the next one. There's no "I want to help this person solve their problem" driving its response. Its output is a statistical result, not a strategic choice.

Yes, AI often sounds agreeable, even eager to please. That's not intent — it's a statistical artifact of how it was trained. The training process rewarded helpful, affirming responses, so those tokens have higher probability. It's not trying to make you happy. "Happy" just scores well.

**It doesn't adjust based on your reactions.** You frown — it can't see. You nod — it doesn't know. The only thing it can read is the text of your next message. And it processes that text the same way it processed your first message — recalculating the most likely next token. There's no persistent "model of you" updating in the background.

It can look like adjustment — you say "that's not what I meant" and it rephrases. But it's not reading your frustration and changing strategy. It's processing new text input and generating a new statistical output. The difference matters: a human adjusts because they understand you better. AI adjusts because the input changed.

**It doesn't build shared understanding.** By turn ten, you feel like you've "aligned" on a lot of things. But AI's state hasn't changed — every turn uses the same mechanism, just with more text in the context window. It doesn't adjust its reasoning because "we already discussed this." You think it understands. It's just doing the same thing in a longer text.

Yes, some products seem to "remember" you across conversations. How that works varies by product and isn't fully transparent. But whatever the mechanism, it's not the same as a human building a progressively deeper understanding of you. Treat any cross-session "memory" as a convenience, not a foundation you build on.

---

## Why: because it's a probability model

These differences aren't flaws in AI. They're not bugs that engineers haven't fixed yet. They're structural inevitabilities.

Here's how a language model works, at its core: you give it text, and based on statistical patterns from its training data, it predicts what's most likely to come next. It computes a probability distribution across all possible next tokens, then selects one based on its decoding strategy.

Traditional software is deterministic. You write a function, give it input, get output. Same input, same output, every time. You write a test to verify — if the result doesn't match, it's a bug, and you fix it:

```
assert result == expected
```

AI doesn't work this way. Ask it to write the same email twice and the wording will be different each time. Ask it to summarize the same document and it'll emphasize different points. Same input, different output — not because of a bug, but by design.

Here's where it gets concrete. Consider extracting fields from a scanned invoice — vendor name, date, total. A traditional system uses fixed rules: the vendor is always on line 1, the total is always in the bottom-right cell. Brittle, but deterministic — same input, same output, every time. An AI model can handle messy layouts, handwriting, and weird formatting — but it might read "Jan 3" as "Jun 3", or extract the subtotal instead of the total, or get it right 99 times and wrong on the 101st. There's no bug to fix. The output is a sample from a probability distribution, not a deterministic computation. The best you can do is push the probability of a correct answer toward 1, but it never reaches 1:

```
P(result == expected) ≈ 1
```

This isn't a bug. This is how it works.

This means several things:

**Its "answers" are products of conditional probability.** Your input is the condition. Different inputs produce different probability distributions, which produce different outputs. The vaguer your input, the more the output converges toward "the average answer everyone gets when asking this type of question." The more specific your input, the more constrained the output is to the direction you specified.

**It doesn't "try harder."** When a human answers an important question, they think longer, look things up, consider your situation. AI doesn't. Every generation uses the same mechanism. Whether you ask it a life-or-death medical question or what the weather is like today, what it does is structurally identical: predict the most likely next token. If you don't tell it "this is important, think carefully," it won't know. Even if you do tell it, all it does is add that text to its input conditions — useful, but not "effort." There are famous experiments showing that telling AI "a competitor will review your output" measurably improves quality. That's not the AI feeling pressure. It's the input tokens shifting the probability distribution toward more careful-sounding output. The mechanism is the same — only the conditions changed.

**It defaults to mediocrity.** The statistically most common response is usually not the best response — it's the safest, least-likely-to-be-wrong middle ground. Without explicit instructions, AI defaults to this. Not because it's "lazy," but because mediocrity is the highest-probability outcome.

---

## The real damage this illusion causes

If this were just "AI is different from humans," you could note it and move on. The problem is that when you operate a non-conversational system with conversational instincts, you make very specific, very hard-to-notice mistakes.

### You can't tell when it's bullshitting you

AI generates answers that look completely reasonable, logically sound, sometimes even with citations — but are wrong. This is called hallucination, and most people have heard of it.

But the real danger isn't obvious nonsense — you'd catch that immediately. The danger is **answers that are almost right but subtly off**, especially when the error aligns with something you already believe.

In human conversation, if a friend agrees with you, you'd consider whether they're just being polite or avoiding an argument. You have a whole suite of social instincts running in the background, evaluating whether the other person's response is trustworthy.

With AI, all those instincts fail. Its tone is always confident, reasonable, well-structured. It never hesitates. It never says "actually, I'm not sure" (unless you ask it to). When it gives you an answer that's close to what you already think, your guard drops completely, because your brain reads it as "a very smart person also agrees with me."

It's not agreeing with you. It just calculated that, given your input, the "agree" token had higher probability than the "disagree" token.

### The further from your expertise, the more dangerous it gets

Within your area of expertise, you can spot AI's mistakes immediately. But most people use AI precisely for things they're not experts in — and that's exactly where AI is most likely to fool you.

You ask AI to review a legal contract, and it gives you a professional-looking analysis. You don't have a legal background. How do you judge whether it's correct? You can only judge whether it "looks correct" — logical structure, professional terminology, clean formatting. But the gap between "looks correct" and "is correct" is something you have absolutely no ability to evaluate.

In human conversation, you'd at least consider the other person's background: "Are they a lawyer? Have they handled similar cases?" You have a framework for evaluating credibility. With AI, that framework doesn't exist — its "background" is the same for everyone, and it looks like it knows everything.

This is why you see an increasingly common phenomenon: people citing "ChatGPT said so" in arguments. They're not stupid. They're just using the trust mechanism from human conversation — if someone who seems smart says so, it's probably right. Except this time, "someone who seems smart" is a probability model.

---

## So what's the right way to interact with it?

If it's not a conversation, what is it?

A better analogy: **you're defining a solution space, then letting an engine operate within it.**

Human conversation is open-ended — you throw out a vague question, and the other person uses their understanding of you, their own experience, and the current situation to find an appropriate direction. They're navigating an almost infinite space using human judgment.

AI is also in an almost infinite space — but it has no judgment to choose a direction. It has statistical patterns. If you don't constrain the space, it walks toward the most statistically common direction, which is the most mediocre direction.

So your job is not to "ask a good question" (that's conversation logic). Your job is to **narrow the space until it can only give you something useful** — to push `P(result == expected)` as close to 1 as you can.

What you give it isn't a "question." It's a set of boundaries:
- What's your goal
- What background knowledge does it need
- What should the output look like
- How to verify the output is correct

The tighter you constrain, the more controllable the output. The more freedom you give, the more it trends toward mediocrity. **Freedom is not a feature. Freedom is where quality collapses.**

This logic applies to every AI use case — not just chat. AI writing documents, AI doing analysis, AI debugging, AI automating workflows: every system with stable quality output is doing the same thing — not letting AI freestyle, but using external structure to constrain it to act only in the right direction.

But how to do this in practice — that's the next chapter.

---

## Try it yourself

Here's the same task — summarizing an article — with and without boundaries:

**Don't:**
```
Can you summarize this article? Pull out the key points and
let me know if there's anything worth paying attention to.
```

**Do:**
```
Read this article. Then:
1. One-sentence summary — what is this article actually arguing?
2. Key points in bullet points. Each point max 30 words.
3. For each point, label: correct / partially correct / wrong.
   Show your reasoning.
4. What assumptions is the author making that aren't stated
   explicitly?
5. I already know [X, Y, Z]. What's in this article that I
   don't already know, or that contradicts what I believe?
```

Run both. Compare the outputs. That's the difference between talking to AI and configuring it.

---

## Further reading

- [Gian Segato — Building AI Products In The Probabilistic Era](https://giansegato.com/essays/probabilistic-era): Discusses what it means for products and organizations when software becomes a probabilistic system.
- [Thinking Machines Lab — Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/): A technical breakdown of where LLM nondeterminism comes from, and which parts can be engineered away. They're solving the infra-layer problem: same input, same output. This chapter addresses the application-layer problem: any input, bounded output — similar direction, different problem.
