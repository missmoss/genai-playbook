# RAG: Retrieval-Augmented Generation

---

> **How you read this chapter depends on what you need.**
>
> If you want to understand RAG concepts first, start here and read through. If you want to jump straight to a hands-on experiment, skip to [The Experiment](#the-experiment-progressive-rag-improvement) or go directly to the `[examples/](examples/)` folder and run the code. If you already know RAG and want to see what's different here, skip to [Metadata-Aware Retrieval](#phase-3-metadata-aware-retrieval) — that's where the non-obvious lessons are.

---

## Most RAG tutorials teach you the wrong thing

Open any RAG tutorial and you'll see the same structure: what is an embedding, how does a transformer encode semantic meaning, how does cosine similarity work in high-dimensional space, here's how to set up a vector database.

That's ML engineering. It's useful knowledge, but it's not your job.

Your job as an application engineer is to build a system that reliably answers questions from a knowledge source. You don't train the embedding model — you call an API. You don't implement the vector search algorithm — you use a library or a database. What you *do* decide is: how to break your documents into pieces, what metadata to attach, how to assemble retrieved context into a prompt, and when the system should say "I don't know."

Those decisions determine whether your RAG system works. This chapter is about those decisions.

---

## What RAG is

Chapters 1 and 2 established that AI operates within the context you give it, and that controlling what goes in determines what comes out. Chapter 3 extended this to context management — your responsibility to decide what the model sees.

RAG is what happens when your context source is too large to fit in the context window. Or when it changes over time and you can't re-embed everything on every query. Or when you simply can't afford to send 140,000 tokens per question.

The idea is straightforward:

1. **Indexing (once):** Break your documents into chunks. Convert each chunk into a vector embedding. Store them.
2. **Retrieval (per query):** Convert the user's question into a vector. Find the chunks whose vectors are closest. These are your candidate context.
3. **Generation (per query):** Send the retrieved chunks to an LLM along with the question. The LLM generates an answer from those chunks — not from its training data.

That's the whole pipeline. Here's how the pieces fit together:

```
                         INDEXING (once)
                         ─────────────────────────────────────────
  Documents ──→ [ Chunk ] ──→ [ Embed ] ──→ [ Store vectors + metadata ]
                    │                              │
                    │        (optional)             │
                    └──→ [ Enrich with LLM ] ──────┘
                         (tags, summaries)


                         QUERY TIME (per question)
                         ─────────────────────────────────────────
  Question ──→ [ Embed query ] ──→ [ Vector search ]
                                        │
                       (optional)        │
                  [ Query analysis ] ────┤  (metadata filter / rerank)
                                        │
                                        ▼
                                  [ Top-k chunks ]
                                        │
                       (optional)        │
                    [ Re-rank ] ─────────┤
                                        │
                                        ▼
                              [ Pack context + prompt ]
                                        │
                                        ▼
                                  [ Generate answer ]
```

Everything labeled "optional" is a design decision. A minimal RAG system includes only the core steps — chunk, embed, search, and generate. Whether to add the optional steps depends on whether they measurably improve your results.

---

## The building blocks

Before we run the experiment, here's what each piece of the pipeline does. This is application-level understanding — enough to make design decisions, not enough to publish a paper.


| Concept                                                      | What it does                                                    | Core or optional?                                           |
| ------------------------------------------------------------ | --------------------------------------------------------------- | ----------------------------------------------------------- |
| [Chunking](#chunking)                                        | Breaks documents into retrievable pieces                        | Core                                                        |
| [Embedding](#embedding)                                      | Converts text to vectors that encode meaning                    | Core                                                        |
| [Vector search](#vector-search)                              | Finds chunks closest to the query                               | Core                                                        |
| [Keyword / hybrid search](#keyword-search-and-hybrid-search) | Adds exact-term matching alongside semantic search              | Optional — use when queries include specific terms          |
| [Re-ranking](#re-ranking)                                    | Scores query-chunk pairs more precisely after initial retrieval | Optional — add when retrieval quality is measurably lacking |
| [Metadata filtering](#metadata-filtering)                    | Narrows search using structured fields (date, category, source) | Optional — high impact when documents have clear attributes |
| [Context packing](#context-packing)                          | Assembles retrieved chunks into the generation prompt           | Core                                                        |


### Chunking

Documents are too long to embed or retrieve as a whole. Chunking breaks them into pieces — typically 200–1,000 tokens each.

The core tradeoff: **smaller chunks give more precise retrieval** (the vector represents a focused idea) **but less context per chunk** (the LLM may not have enough surrounding information to answer). Larger chunks carry more context but the embedding becomes a blurry average of multiple ideas.

Common strategies:

- **Fixed-size splitting.** Cut every N tokens regardless of content. Simple, predictable, frequently splits mid-sentence or mid-paragraph. Fine for prototyping.
- **Recursive character splitting.** Try to split on paragraph boundaries (`\n\n`) first, then sentences, then words. Respects document structure where it exists, degrades gracefully. This is the practical default.
- **Sentence-based splitting.** Split at sentence boundaries, group N sentences per chunk. Clean splits, variable chunk sizes.

**Overlap** means repeating 50–100 tokens between consecutive chunks. It prevents losing information at boundaries — if a key fact spans two chunks, overlap ensures it appears fully in at least one.

Structural elements matter more than most tutorials mention. Tables split mid-row lose column headers. Code split mid-function loses syntax. A section header separated from its body produces a chunk with no topic context. These aren't edge cases — they're the norm in real documents.

### Embedding

An embedding model takes text and returns a vector — a list of numbers (typically 768–3,072 floats) that encodes semantic meaning. Similar texts produce vectors that point in similar directions. Dissimilar texts point in different directions.

You don't train this model. You call an API — OpenAI's `text-embedding-3-small`, Cohere's `embed-english-v3`, or you run an open-source model like `BAAI/bge-large-en-v1.5` locally.

Two things to know:

**Token limits are silent killers.** Every embedding model has a maximum input length, and limits vary significantly by model. Some models accept thousands of tokens; others cap at a few hundred. Text exceeding the limit may be truncated without an obvious warning. This means your chunk size must respect your embedding model's token limit, and you should verify how your specific API behaves. If your chunks are 1,000 tokens and your model accepts 512, you may be throwing away half of every chunk.

**Semantic similarity has blind spots.** Embeddings capture meaning, not exact strings. "Automobile" and "car" embed closely — that's the point. But "invoice #INV-2024-0091" won't reliably match a specific invoice number. "Has side effects" and "has no side effects" embed almost identically — negation is poorly captured. Numbers, proper nouns, and exact-match queries are where embedding-based retrieval breaks down.

### Vector search

At query time, you embed the user's question with the same model, then find the chunks whose vectors are closest.

"Closest" is typically measured by **cosine similarity** — the angle between two vectors, ignoring magnitude. Scores range from -1 to 1. The score distribution varies significantly between embedding models — what counts as "high similarity" for one model may be mediocre for another. Don't assume a universal threshold; look at your own score distribution with known-relevant and known-irrelevant pairs before setting cutoffs.

You retrieve the **top-k** results — commonly k=5–20. Too small and you miss relevant chunks. Too large and you flood the LLM with noise, increasing cost and degrading quality (relevant information buried in the middle of a long context gets overlooked — a well-documented phenomenon called "lost in the middle").

A common pattern: retrieve k=20–50 broadly, then narrow down with re-ranking or filtering before passing the top 3–10 to the LLM.

At small scale (under ~100K chunks), brute-force search works fine — compute cosine similarity against every chunk, sort, take the top-k. Our experiment does exactly this with numpy. At large scale, approximate nearest neighbor algorithms (HNSW, IVF) trade a tiny amount of accuracy for massive speed gains. These are handled by your vector database — Qdrant, Pinecone, pgvector, Weaviate — not by you.

### Keyword search and hybrid search

Vector search finds semantic matches but misses exact terms. BM25 (the standard keyword search algorithm) does the opposite — it scores documents by how often query terms appear, weighted by how rare those terms are across all documents. Rare, specific terms get high scores. Common words get low scores.

"Find invoice INV-2024-0091" is a keyword search problem, not a vector search problem. "What causes fever?" is a vector search problem — BM25 won't match a document about "elevated body temperature."

**Hybrid search** runs both and merges results, typically using Reciprocal Rank Fusion (RRF): a document that ranks high in both lists gets a combined boost. Hybrid is the safer default when you don't know your query distribution yet.

Some databases support hybrid natively (Weaviate, Elasticsearch). Others require you to run BM25 and vector search separately and combine results yourself.

### Re-ranking

"Re-ranking" means re-sorting initial retrieval results using a more informed scoring method. There are two common approaches:

**Model-based re-ranking** uses a cross-encoder model (Cohere Rerank, ColBERT, or a custom model) that takes each (query, document) pair jointly and scores how well the document actually answers the query. It sees both texts together, so it catches nuances that independent embeddings miss. Example: you search for "side effects of ibuprofen." Vector retrieval returns chunks about ibuprofen's mechanism of action (semantically close — it's about ibuprofen) alongside chunks about side effects. A cross-encoder re-ranker can distinguish which chunks are about side effects specifically. This adds 100–500ms of latency per query.

**Heuristic re-ranking** applies rule-based score adjustments — boosting chunks that match metadata criteria (correct story, matching characters, target scene type) without calling an additional model. This is fast (sub-millisecond) but only helps when the metadata signals are relevant to the query.

The workflow for both: retrieve top-20–50 with vector search, re-rank all of them, pass the top 3–10 to the LLM. Our experiment uses heuristic re-ranking — metadata-based score boosts — not a cross-encoder model. Whether model-based re-ranking is worth the added cost and latency depends on whether heuristic signals are sufficient for your use case.

### Metadata filtering

Every chunk can carry structured metadata alongside its vector: source document, date, category, author, section name — any field you want to filter on.

At query time, you apply filters (like a SQL `WHERE` clause) to restrict which chunks are searched. "What's the current refund policy?" filtered to `document_type = "policy" AND version = "current"` avoids returning outdated drafts.

The catch: **metadata must be attached at indexing time.** You can't filter on fields that don't exist. Retrofitting metadata to an existing index means re-indexing.

This is important enough that we dedicate a major section of the experiment to it. Metadata can be extracted from document structure (file name, section headers, dates) or generated by an LLM at indexing time (topic tags, entity lists, event summaries). The latter costs money upfront but can dramatically improve retrieval quality.

### Context packing

Retrieval gives you chunks. Context packing is how you assemble them into the generation prompt. This is not just concatenation.

**Ordering matters.** Most relevant first? Chronological? By source document? The answer depends on the question. A factual lookup wants the most relevant chunk front and center. A timeline question wants chronological order.

**Deduplication matters.** If you used overlapping chunks, consecutive chunks may repeat the same sentences. The LLM doesn't know they're duplicates — it may treat repeated information as more important.

**Metadata in the prompt matters.** Include the source, section name, and date with each chunk. Without this, the LLM can't cite sources, can't prefer newer versions, and can't flag when two chunks contradict each other.

### What you decide vs. what you don't


| Your decisions                                 | Someone else handles it             |
| ---------------------------------------------- | ----------------------------------- |
| Chunk size and overlap                         | Embedding model internals           |
| What metadata to attach                        | Vector index algorithms (HNSW, IVF) |
| Retrieval strategy (vector / keyword / hybrid) | Embedding model training            |
| Whether to re-rank                             | Database scaling and replication    |
| Context packing and ordering                   | GPU allocation for embeddings       |
| Citation rules and abstention policy           |                                     |
| Evaluation criteria                            |                                     |


This is the line between AI application engineering and ML engineering. Everything on the left is what this chapter teaches. Everything on the right is what your API provider or database handles.

---

## The experiment: progressive RAG improvement

We ran an experiment with 12 Sherlock Holmes short stories — about 108,000 words. We chose fiction because you can read the source and verify answers yourself, and it still surfaces the retrieval problems that matter — wrong chunks selected, cross-document queries, metadata as a lever, when to refuse. The problems that literary text *doesn't* cover (exact identifiers, versioning, tables, hybrid search) are called out in [Where this breaks with real documents](#where-this-breaks-with-real-documents).

We asked the same 6 questions using 10 different approaches, from "stuff everything in the context window" to "metadata-aware retrieval with story-index-guided query analysis." All code is in the `[examples/](examples/)` folder; you can run every step yourself.

The questions:

1. **Single-story factual:** "Who was the client in The Red-Headed League, and what was the scheme about?"
2. **Cross-story:** "In which stories does Holmes use a disguise, and what does he disguise himself as?"
3. **Precise detail:** "What was the murder weapon in The Boscombe Valley Mystery?"
4. **Reasoning chain:** "How did Irene Adler outsmart Holmes in A Scandal in Bohemia?"
5. **Abstention test:** "Describe the scene where Holmes fights Moriarty at Reichenbach Falls." *(This scene is not in The Adventures — it tests whether the system refuses to answer.)*
6. **Cross-story comparison:** "Compare how Holmes treats Watson in the first story versus the last story of the collection."

These aren't random. Each one exercises a different failure mode. A system that answers all six correctly is doing something right. A system that fails on #3 but passes #1 tells you something specific about where retrieval breaks down.

Here's the full progression — what each approach adds, what script to run, and where the biggest improvements happen:

`A+B` in the tables means: run prerequisite `A`, then run `B`. A shared prerequisite may appear in multiple rows.

*"Total setup + 6 queries" includes one-time indexing costs (embedding, LLM enrichment, story summary generation) amortized over this single run. In production, indexing cost is amortized over all queries; per-query cost would be lower.*


| Phase | Approach                                                    | What changed                                                        | Script(s)                                                                                      | Avg input tokens | Avg output tokens | Total setup + 6 queries | Key result                                |
| ----- | ----------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------- | ----------------- | ----------------------- | ----------------------------------------- |
| 1     | [02] Long context baseline                                  | Everything in context window                                        | `02_baseline_long_context.py`                                                                  | 139,857          | 167               | $0.254246           | High quality, ~$0.04/query                |
| 1     | [03+04] Naive RAG                                           | Chunk → embed → cosine search → generate                            | `03_index_naive.py`, `04_rag_naive.py`                                                         | 5,548            | 164               | $0.014789           | 20x cheaper, but Boscombe Valley wrong    |
| 2     | [05+06] + structural metadata in generation                 | Story title, position in generation prompt                          | `05_index_structural.py`, `06_rag_structural.py`                                               | 5,734            | 248               | $0.016391           | No improvement — same retrieval           |
| 2     | [07+08] + LLM-enriched tags in generation                   | Characters, scene type in generation prompt                         | `07_index_enriched.py`, `08_rag_enriched.py`                                                   | 6,317            | 171               | $0.145159           | No improvement — same retrieval           |
| 3a    | [09] + structural-aware retrieval                           | Score boosts from metadata in retrieval, but no story-level index   | `09_rag_structural_retrieval_no_story_index.py`                                                | 5,687            | 296               | $0.018002           | ⬆ Boscombe Valley now correct             |
| 3a    | [10] + enriched-aware retrieval                             | Character/scene tags in retrieval, but no story-level index         | `10_rag_enriched_retrieval_no_story_index.py`                                                  | 6,481            | 146               | $0.146036           | Mixed results — disguise query still weak |
| 3a    | [11] + combined retrieval                                   | Hard-filter by story + rerank by all tags, but no story-level index | `11_rag_combined_retrieval_no_story_index.py`                                                  | 6,708            | 164               | $0.146725           | ⬆ Best pre-story-index RAG quality        |
| 3b    | [12+13] + structural-aware retrieval + story index          | Structural retrieval guided by story summaries                      | `12_build_story_index.py`, `13_rag_structural_retrieval_story_index.py`                        | 5,569            | 188               | $0.157816           | ⬆ Disguise query improves materially      |
| 3b    | [12+14] + enriched-aware retrieval + story index            | Enriched retrieval guided by story summaries                        | `12_build_story_index.py`, `14_rag_enriched_retrieval_story_index.py`                          | 6,249            | 189               | $0.156739           | ⬆ Disguise query improves materially      |
| 3b    | [12+15] + combined retrieval + story index                  | Hard story filter + rerank + story-index-guided query analysis      | `12_build_story_index.py`, `15_rag_combined_retrieval_story_index.py`                          | 6,258            | 176               | $0.156530           | ⬆ Best overall RAG quality                |



| Approach                                                    | Q1: Red-Headed League client + scheme | Q2: Holmes disguises                                                                                         | Q3: Boscombe weapon                                                                              | Q4: Irene Adler | Q5: Moriarty / Reichenbach | Q6: Holmes vs. Watson                                      |
| ----------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | --------------- | -------------------------- | ---------------------------------------------------------- |
| [02] Long context baseline                                  | ✓                                     | △ Mostly right, but adds `Copper Beeches` and the list is not cleanly scoped to Holmes-only disguise stories | ✓                                                                                                | ✓               | ✓                          | ✓                                                          |
| [03+04] Naive RAG                                           | ✓                                     | △ Gets `A Scandal in Bohemia`, but then switches to Neville St. Clair's disguise instead of Holmes's         | ✗ Says the weapon was the butt-end of the son's gun, not Holmes's final answer: the jagged stone | ✓               | ✓                          | ✗ Abstains instead of comparing the first and last stories |
| [05+06] + structural metadata in generation                 | ✓                                     | ✗ Speculates from weak passages instead of naming Holmes's actual disguises                                  | ✗ Same gun-butt error as naive RAG                                                               | ✓               | ✓                          | ✗ Abstains instead of comparing the first and last stories |
| [07+08] + LLM-enriched tags in generation                   | ✓                                     | △ Fails to answer fully; only mentions Neville St. Clair's disguise                                          | ✗ Still centers the heavy blunt weapon / gun-butt line instead of the jagged stone               | ✓               | ✓                          | ✗ Abstains instead of comparing the first and last stories |
| [09] + structural-aware retrieval                           | ✓                                     | ✗ Still does not recover Holmes's actual disguise passages                                                   | ✓                                                                                                | ✓               | ✓                          | ✗ Abstains instead of comparing the first and last stories |
| [10] + enriched-aware retrieval                             | ✓                                     | ✗ Still fails to recover Holmes's disguise passages                                                          | ✓                                                                                                | ✓               | ✓                          | ✗ Abstains instead of comparing the first and last stories |
| [11] + combined retrieval                                   | ✓                                     | ✗ Still fails to recover Holmes's disguise passages                                                          | ✓                                                                                                | ✓               | ✓                          | ✗ Still cannot make the comparison                         |
| [12+13] + structural-aware retrieval + story index          | ✓                                     | △ Now recovers `A Scandal in Bohemia`, but still misses Holmes's other disguise stories                      | ✓                                                                                                | ✓               | ✓                          | ✗ Still cannot make the comparison                         |
| [12+14] + enriched-aware retrieval + story index            | ✓                                     | △ Now recovers `A Scandal in Bohemia`, but still misses Holmes's other disguise stories                      | ✗ Regresses to the gun-butt line instead of the jagged stone                                     | ✓               | ✓                          | ✗ Still cannot make the comparison                         |
| [12+15] + combined retrieval + story index                  | ✓                                     | △ Now recovers `A Scandal in Bohemia`, but still misses Holmes's other disguise stories                      | ✓                                                                                                | ✓               | ✓                          | ✗ Still cannot make the comparison                         |


### Phase 1: Baseline and naive RAG

**[02] Long context baseline.** All 12 stories, concatenated, stuffed into the context window. ~140K input tokens per query. This is the "no RAG" approach — just give the model everything and ask.

Results: surprisingly good. It correctly identified Jabez Wilson as the Red-Headed League client, accurately described how Irene Adler outsmarted Holmes, correctly refused the Moriarty question, and even found specific quotes comparing Holmes's treatment of Watson across stories. Quality was high across 5 of 6 queries.

Cost: ~$0.04 per query. Six queries cost $0.25. For 12 stories, this is manageable. For 1,000 documents, it's not — and it would exceed the context window anyway.

**[03] [04] Naive RAG.** Chunk the stories (500 tokens, 100 overlap), embed with OpenAI's `text-embedding-3-small`, retrieve top-10 by cosine similarity, generate with the same LLM.

Results: Red-Headed League — correct. Irene Adler — correct. Moriarty — correctly refused. So far, so good.

But: the Boscombe Valley murder weapon question went wrong. The model said "butt-end of his son's gun" — which is a red herring from the trial testimony. The actual answer (a jagged stone, identified by Holmes's deduction) was in a chunk that didn't make the top-10 because its embedding wasn't close enough to "murder weapon." The Watson comparison question failed entirely — the retrieval couldn't find the right chunks from the first and last stories to compare tone.

Cost: ~$0.002 per query. **20x cheaper than baseline.** But some answers got worse.

### Phase 2: Adding metadata to generation only

Two types of metadata appear throughout the experiment:

| Term         | What it contains                               | How it's produced              |
| ------------ | ---------------------------------------------- | ------------------------------ |
| Structural   | Story title, position in story (opening/middle/resolution) | Extracted from document structure — no LLM cost |
| Enriched     | Characters, scene type, key events             | Generated by an LLM at indexing time — costs ~$0.13 for our corpus |

**[05] [06] and [07] [08].** We tried two things: adding structural metadata to each chunk's generation prompt, and adding enriched (LLM-generated) tags to the generation prompt.

Both times, retrieval stayed the same — pure cosine similarity, top-10.

**Results barely changed.** The same chunks came back from retrieval, so the same answers came out of generation. The metadata in the prompt was decoration — the model already had the wrong chunks; telling it which story they came from didn't fix that.

This is an important lesson from our experiment: **metadata that only appears in the generation prompt didn't help when retrieval had already brought the wrong chunks.** The bottleneck was retrieval, not generation. (In other contexts — e.g., helping the LLM distinguish document versions or assess recency — generation-time metadata can still matter. The point is to identify your actual bottleneck before adding complexity.)

### Phase 3: Metadata-aware retrieval

This is where things got interesting.

#### Phase 3a: [09] [10] [11] Retrieval uses metadata, but query analysis has no story index

[09] [10] [11] first added metadata-aware retrieval without a story-level index.

First, we used a **query analysis step** to extract likely target stories, characters, and scene types from the question itself. Then we used those hints to **rerank** the cosine similarity results. In [09] and [10], chunks from the target story got a score boost; chunks containing the target characters or matching the target scene type got additional boosts. No chunks were excluded — the full candidate pool was re-sorted. Only in [11], the "combined" variant, did we add a **hard prefilter**: restrict to chunks from the target story first (falling back to the full pool when the filtered set was too small), then rerank by all metadata signals.

**The Boscombe Valley murder weapon went from wrong to right.** With score boosting from story metadata, the deduction chunk — where Holmes identifies the jagged stone — rose from below 15th into the top-10. Without those boosts, it was crowded out by chunks from other stories that happened to mention weapons or violence.

Same model. Same prompt. Same question. Different chunks in, different answer out. This is Chapter 1's principle made visible: the model didn't get smarter — the input changed.

But the disguise cross-story query was still inconsistent. Without a story index, the query analysis step had no document-level context to work with — the model could only guess story titles from its own training data, not from our indexed content. This means Phase 3a's query analysis is implicitly relying on the corpus being well-known (Sherlock Holmes). For a proprietary or obscure corpus, this approach would produce meaningless or hallucinated story references.

#### Phase 3b: [12] [13] [14] [15] Retrieval uses metadata plus a story-level index

[12] built a **story-level index** from the enriched chunks we already had. For each story: a title, a 2–3 sentence summary (generated from the chunk-level key events), and a list of all characters that appear. This cost almost nothing — the key events were already extracted, we just asked a cheap model to summarize them per story.

Then, before retrieval, we added a **query analysis step**: show the model the story index (titles, summaries, characters) and ask it to identify which stories, characters, and scene types the question is about. This gives us structured hints — not from the model's training data, but from our actual indexed content.

Finally, we used those hints to **filter and rerank** the cosine similarity results. Chunks from the target story get a score boost. Chunks containing the target characters get a boost. Chunks matching the target scene type get a boost. In the "combined" variant, we prefilter to the target stories first only when doing so still leaves enough candidate chunks; otherwise we fall back to the broader candidate pool.

The disguise cross-story query improved — it now reliably found A Scandal in Bohemia's disguise passages — but it still missed some stories. Cross-story queries remain hard because even with a story index, the analysis step may not infer every relevant story when the question doesn't name them explicitly.

One caveat: progress was not monotonic. [12+14] (enriched retrieval + story index) regressed on the Boscombe Valley murder weapon question — a query that [09] and [11] answered correctly. The story index changed which chunks the enriched-tag reranking surfaced, and in this case the change was harmful. Adding complexity doesn't guarantee improvement on every query; it shifts the distribution of successes and failures.

**Cost:** Each query analysis call added ~$0.001. The story index was a one-time cost. Total query cost went from ~$0.002 to ~$0.003 — a 50% increase for measurably better answers on the queries that matter.

### Phase 4: What still fails and why

Two types of cross-story queries failed, for different reasons:

**Q6 (Watson comparison)** failed across all ten RAG approaches — only the long context baseline answered it. This question requires reading the *tone and attitude* across broad narrative passages, not finding a specific fact in a specific chunk. RAG retrieves fragments; this question needs full stories. No amount of metadata or re-ranking fixes that — it's a fundamentally different context granularity.

**Q2 (Holmes disguises)** improved with the story index but never fully succeeded. This is a different failure mode: the relevant evidence exists in retrievable chunks, but it's scattered across multiple stories and the query analysis step can't reliably identify all of them. Better story selection or multi-hop retrieval could plausibly solve this without abandoning chunk-level retrieval entirely.

These two failures point to different solutions. Q6 likely needs **query routing**: before retrieval, classify the question — if it needs chunk-level facts, run RAG; if it needs broad narrative context, send the full document (or a story-level summary) instead; if it can be answered without retrieval at all, skip it. Q2 might be solvable with better metadata coverage, iterative retrieval, or a wider top-k. Grouping them as "cross-story queries are hard" obscures the fact that the fixes are different.

Query routing is an application design decision — you decide the routing logic based on your use case and your budget. We didn't implement it in this experiment, so we can't confirm it solves Q6, but the failure pattern strongly suggests it's the right direction.

**This is the real lesson of the experiment.** RAG is not a pipeline you configure once. It's a set of design decisions you make based on your data, your queries, and your quality requirements. The experiment showed us exactly where each decision matters:


| What we tested              | What we learned                                                                |
| --------------------------- | ------------------------------------------------------------------------------ |
| Metadata in generation only | Didn't help in our experiment — retrieval was the bottleneck                   |
| Metadata in retrieval       | Measurably improves answers that depend on finding the right document          |
| Cross-story queries (Q2)    | Story selection problem — improved with story index but not fully solved        |
| Broad-context queries (Q6)  | Fundamentally needs full-document context, not better retrieval tuning          |
| Abstention (Moriarty)       | All approaches correctly refused in our 1-query test                           |
| Cost                        | RAG was 10–20x cheaper per query than long context for this corpus size        |
| Indexing investment         | Enrichment is a one-time cost; whether it's worth it depends on query patterns |


Full results are in `[examples/output/comparison_all.md](examples/output/comparison_all.md)`.

---

## Design decisions, not pipeline parameters

The experiment demonstrated something that most RAG tutorials miss: the quality of a RAG system is not determined by which vector database you use or what embedding dimensions you choose. It's determined by a small number of design decisions that are specific to your application.

**Chunk size** is one of the few parameters you actually choose. We used 500 tokens — a common default. Larger chunks (1,000–2,000 tokens) carry more context per chunk but produce blurrier embeddings. Smaller chunks (200–300 tokens) retrieve more precisely but may lack the surrounding context the LLM needs. The right size depends on your documents and your questions. Start with 500, measure retrieval quality, adjust.

**Metadata enrichment** is a one-time indexing cost. In our experiment, we spent ~$0.13 tagging chunks with characters, scene types, and key events. That investment paid off when we used the tags in retrieval — the Boscombe Valley answer went from wrong to right. But if your queries are simple keyword lookups against well-structured documents, you may not need enrichment at all. The decision is: do your queries require filtering or routing by attributes that aren't in the text itself?

**Query routing** is the most underrated design decision. Not every query should go through the same pipeline. Some need chunk-level retrieval. Some need full-document context. Some need a story-level summary. Some can be answered by the model's own knowledge without retrieval. In production, you put a cheap, fast classifier in front of the pipeline that decides which path to take. This is not a RAG optimization — it's application architecture.

**Evaluation** is what makes all the other decisions possible. You can't improve what you don't measure. Build a small ground truth set — 50–100 questions with known answers and known relevant chunks. Measure recall@k (are the right chunks in the top-k?) and faithfulness (does the generated answer stick to the retrieved context?). Compare approaches against this set before shipping.

These decisions apply regardless of domain. Customer support knowledge bases, legal document search, internal wikis, medical reference systems — the domain changes, the documents change, the questions change. The design framework doesn't.

---

## When not to use RAG

RAG is a specific solution to a specific problem. It is not the default architecture for every AI application.

**If your corpus fits in the context window, just use long context.** Our 12-story baseline proved this — quality was higher than any RAG approach, at the cost of more tokens per query. If you can afford it and your data doesn't change, long context is simpler and often better.

**If your data changes faster than you can re-index, RAG may hurt more than it helps.** A RAG system answering from a stale index is worse than a system that admits it doesn't know. Consider live context injection — fetching current data at query time instead of relying on a pre-built index.

**If retrieval precision isn't the bottleneck, don't add retrieval complexity.** Some applications fail because the prompt is bad, not because the context is wrong. Fix the prompt first.

**If the question needs broad context, not specific chunks, RAG is the wrong tool.** Our Watson comparison question showed this clearly. The solution is query routing or full-document context — not more retrieval tuning.

Start with the simplest approach that could work. Add complexity only when you can measure that it helps.

---

## Where this breaks with real documents

Our experiment used literary fiction — continuous prose, no structured data, no versioning. Real-world corpora will hit problems that Sherlock Holmes simply doesn't exercise:

- **Exact identifiers.** Queries like "find invoice INV-2024-0091" or "what's the status of ticket PROJ-847" need keyword matching, not semantic search. Embeddings won't reliably retrieve a specific ID. You need hybrid search (BM25 + vector) or metadata filtering on extracted identifiers.
- **Version and date filtering.** When multiple versions of a policy, contract, or API doc exist, pure vector similarity can't distinguish "current" from "superseded." You need date/version metadata attached at indexing time and hard filters at query time.
- **Tables and code.** A table split mid-row loses its column headers. A function split mid-body loses its signature. Standard text chunking destroys these structures. You need format-aware chunking or pre-processing that preserves structural context (e.g., prepending headers to each row, keeping functions as atomic chunks).
- **Keyword and hybrid retrieval.** Our experiment used only vector search because Holmes queries are semantic ("how did Adler outsmart Holmes?"). Production workloads typically mix semantic and exact-match queries. If you skip hybrid search, you'll miss an entire class of queries on day one.

These aren't advanced optimizations — they're problems you'll hit in your first real deployment. The design framework from this chapter (identify the bottleneck, measure, add complexity where it helps) still applies; the specific techniques needed will be different.

---

## Try it yourself

The `[examples/](examples/)` folder contains every script from this experiment. Text generation, enrichment, and query-analysis can run through Gemini, Anthropic, or OpenAI; embeddings use OpenAI, and the scripts call the APIs over plain HTTP plus numpy. `[R00] R00_shared.py` is the shared helper module, and `texts/the-adventures-of-sherlock-holmes.txt` is the source file.

```bash
cd 04-rag/examples

export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export GEMINI_API_KEY="your-key"

# Prepare texts and baseline artifacts
python 01_prepare_texts.py

# Phase 1: Baseline and naive RAG
python 02_baseline_long_context.py
python 03_index_naive.py
python 04_rag_naive.py

# Phase 2: Metadata in generation only
python 05_index_structural.py
python 06_rag_structural.py
python 07_index_enriched.py
python 08_rag_enriched.py

# Phase 3a: Metadata-aware retrieval without story index
python 09_rag_structural_retrieval_no_story_index.py
python 10_rag_enriched_retrieval_no_story_index.py
python 11_rag_combined_retrieval_no_story_index.py

# Phase 3b: Metadata-aware retrieval with story index
python 12_build_story_index.py
python 13_rag_structural_retrieval_story_index.py
python 14_rag_enriched_retrieval_story_index.py
python 15_rag_combined_retrieval_story_index.py

# Compare everything
python 16_compare_all.py
```

Try changing the queries. Try different chunk sizes. Try asking questions that need information from multiple stories. The point isn't to reproduce our exact results — it's to see how each design decision changes the outcome.
