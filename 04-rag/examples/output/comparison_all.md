# RAG Demo: Results Comparison

## Query: "Who was the client in The Red-Headed League, and what was the scheme about?"

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | In "The Red-Headed League," the client was **Mr. Jabez Wilson**, a very stout, florid-faced, elderly gentleman with fiery red hair, who owned a small pawnbroker's business at Coburg Square. The sch... | 139861 | 214 | 4891 |
| [03+04] Naive RAG | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-009, adventures-02-the-red-headed-league-chunk-013, adventures-02-the-red-headed-league-chunk-0... | 5914 | 411 | 2741 |
| [05+06] RAG + structural metadata | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-009]. The scheme was designed to get Mr. Wilson out of his house for several hours each day [ad... | 6076 | 359 | 2477 |
| [07+08] RAG + LLM-enriched tags | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-007, adventures-02-the-red-headed-league-chunk-006, adventures-02-the-red-headed-league-chunk-0... | 6714 | 514 | 2984 |
| [09] Structural metadata-aware retrieval (no story index) | The client in "The Red-Headed League" was Mr. Jabez Wilson, a pawnbroker with bright, fiery red hair [adventures-02-the-red-headed-league-chunk-007, adventures-02-the-red-headed-league-chunk-004]. ... | 5671 | 382 | 2313 |
| [10] Enriched metadata-aware retrieval (no story index) | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-001]. The scheme, as deduced by Sherlock Holmes, was designed to get Mr. Wilson out of his pawn... | 6763 | 185 | 1656 |
| [11] Combined metadata-aware retrieval (no story index) | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-001]. The scheme involved an advertisement for "The Red-Headed League," which offered a salary ... | 6763 | 302 | 2253 |
| [12+13] Structural metadata-aware retrieval + story index | The client in "The Red-Headed League" was Mr. Jabez Wilson, a pawnbroker with bright, fiery red hair [adventures-02-the-red-headed-league-chunk-007, adventures-02-the-red-headed-league-chunk-004]. ... | 5671 | 382 | 2509 |
| [12+14] Enriched metadata-aware retrieval + story index | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-001]. The scheme involved an advertisement for the "Red-Headed League," which offered a salary ... | 6297 | 411 | 2710 |
| [12+15] Combined metadata-aware retrieval + story index | The client in "The Red-Headed League" was Mr. Jabez Wilson [adventures-02-the-red-headed-league-chunk-001]. The scheme involved an advertisement for the "Red-Headed League," which offered a salary ... | 6297 | 401 | 2888 |

## Query: "In which stories does Holmes use a disguise, and what does he disguise himself as?"

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | Holmes uses disguises in the following stories: * **A Scandal in Bohemia**: He disguises himself as a drunken-looking groom and later as an amiable and simple-minded Nonconformist clergyman. * **Th... | 139859 | 122 | 2746 |
| [03+04] Naive RAG | Holmes uses a disguise in the following stories: * **A Scandal in Bohemia**: Holmes disguises himself as an "amiable and drunken-looking groom" and later as a "dissenting clergyman" [adventures-01-... | 6542 | 148 | 1699 |
| [05+06] RAG + structural metadata | Based on the provided passages, Holmes uses a disguise in the following stories: * **A Scandal in Bohemia**: The passage mentions Holmes's "mission which he had accomplished so delicately and succe... | 6865 | 700 | 4131 |
| [07+08] RAG + LLM-enriched tags | The provided passages do not contain enough information to answer in which stories Holmes uses a disguise, or what he disguises himself as. While there is a mention of a character, Mr. Neville St. ... | 7476 | 123 | 1313 |
| [09] Structural metadata-aware retrieval (no story index) | Based on the provided passages, Holmes uses a disguise in the following stories: * **A Scandal in Bohemia**: The passage mentions Holmes's "mission which he had accomplished so delicately and succe... | 6865 | 700 | 4231 |
| [10] Enriched metadata-aware retrieval (no story index) | The provided passages do not contain enough information to answer in which stories Holmes uses a disguise, or what he disguises himself as. However, one passage mentions Mr. Neville St. Clair using... | 7385 | 68 | 1115 |
| [11] Combined metadata-aware retrieval (no story index) | The provided passages do not contain enough information to answer in which stories Holmes uses a disguise, or what he disguises himself as. However, one passage mentions Mr. Neville St. Clair using... | 7385 | 68 | 1240 |
| [12+13] Structural metadata-aware retrieval + story index | Holmes uses a disguise in "A Scandal in Bohemia" where he disguises himself as a drunken-looking groom and later as an amiable and simple-minded Nonconformist clergyman. [adventures-01-a-scandal-in... | 5973 | 82 | 1339 |
| [12+14] Enriched metadata-aware retrieval + story index | Holmes uses a disguise in the following stories: * **A Scandal in Bohemia**: * He disguises himself as a "drunken-looking groom, ill-kempt and side-whiskered, with an inflamed face and disreputable... | 6753 | 125 | 1428 |
| [12+15] Combined metadata-aware retrieval + story index | Holmes uses a disguise in the following stories: * **A Scandal in Bohemia**: * He disguises himself as a "drunken-looking groom, ill-kempt and side-whiskered, with an inflamed face and disreputable... | 6553 | 125 | 1428 |

## Query: "What was the murder weapon in The Boscombe Valley Mystery?"

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | In "The Boscombe Valley Mystery," the murder weapon was a jagged stone. Holmes deduced this because the grass was growing under it, indicating it had only lain there a few days, and it corresponded... | 139854 | 58 | 2809 |
| [03+04] Naive RAG | The head of the deceased, Mr. McCarthy, "had been beaten in by repeated blows of some heavy and blunt weapon." The injuries "might very well have been inflicted by the butt-end of his son’s gun, wh... | 4819 | 83 | 1266 |
| [05+06] RAG + structural metadata | The head of the victim, Mr. McCarthy, "had been beaten in by repeated blows of some heavy and blunt weapon." The injuries "might very well have been inflicted by the butt-end of his son’s gun, whic... | 4978 | 83 | 1217 |
| [07+08] RAG + LLM-enriched tags | The murder weapon in The Boscombe Valley Mystery was a heavy and blunt weapon, the injuries from which "might very well have been inflicted by the butt-end of his son’s gun" [adventures-04-the-bosc... | 5564 | 108 | 1362 |
| [09] Structural metadata-aware retrieval (no story index) | The murder weapon was a jagged stone. [adventures-04-the-boscombe-valley-mystery-chunk-021] Holmes states that the murder was done with the stone he picked up in the wood. [adventures-04-the-boscom... | 5679 | 146 | 1588 |
| [10] Enriched metadata-aware retrieval (no story index) | The murder weapon in The Boscombe Valley Mystery was a jagged stone. [adventures-04-the-boscombe-valley-mystery-chunk-021] Holmes also states that the head had been beaten in by repeated blows of s... | 6253 | 129 | 1327 |
| [11] Combined metadata-aware retrieval (no story index) | The murder weapon was a jagged stone [adventures-04-the-boscombe-valley-mystery-chunk-021]. Holmes explicitly states to Lestrade, "The murder was done with it," referring to the stone he picked up ... | 6288 | 134 | 1301 |
| [12+13] Structural metadata-aware retrieval + story index | The murder weapon was a jagged stone. [adventures-04-the-boscombe-valley-mystery-chunk-021] Holmes states that the murder was done with the stone he picked up in the wood. [adventures-04-the-boscom... | 5679 | 146 | 1513 |
| [12+14] Enriched metadata-aware retrieval + story index | The head of the victim, Mr. McCarthy, "had been beaten in by repeated blows of some heavy and blunt weapon." The injuries "might very well have been inflicted by the butt-end of his son’s gun, whic... | 6086 | 83 | 1207 |
| [12+15] Combined metadata-aware retrieval + story index | The murder weapon was a jagged stone. [adventures-04-the-boscombe-valley-mystery-chunk-021, adventures-04-the-boscombe-valley-mystery-chunk-022] | 6251 | 50 | 1150 |

## Query: "How did Irene Adler outsmart Holmes in A Scandal in Bohemia?"

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | In "A Scandal in Bohemia," Irene Adler outsmarted Holmes by anticipating his methods and taking preemptive action. Here's how she did it: * **Foreknowledge of Holmes's involvement:** She had been w... | 139855 | 361 | 7746 |
| [03+04] Naive RAG | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his plan to discover the location of the photograph. She was warned against him months prior and knew that if the King employ... | 6002 | 245 | 2864 |
| [05+06] RAG + structural metadata | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his methods and using a disguise to follow him. After Holmes staged a false fire alarm to discover the location of the photog... | 6148 | 255 | 1904 |
| [07+08] RAG + LLM-enriched tags | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his methods and taking preemptive action. After Holmes staged a fire alarm to trick her into revealing the photograph's locat... | 6734 | 186 | 1660 |
| [09] Structural metadata-aware retrieval (no story index) | Irene Adler outsmarted Holmes by anticipating his actions and using her own wit and training as an actress. Here's how she did it: * **Foreknowledge of Holmes:** She had been warned about Holmes mo... | 5660 | 457 | 3062 |
| [10] Enriched metadata-aware retrieval (no story index) | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his actions and using her intelligence to evade him. Here's how she did it: * **Foreknowledge of Holmes:** She had been warne... | 6262 | 397 | 2722 |
| [11] Combined metadata-aware retrieval (no story index) | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his methods and fleeing with her husband. She was warned about Holmes months in advance and knew that if the King employed an... | 6418 | 366 | 2592 |
| [12+13] Structural metadata-aware retrieval + story index | Irene Adler outsmarted Holmes by anticipating his actions and using her own wit and training as an actress. Here's how she did it: * **Anticipation of Holmes's involvement:** She had been warned mo... | 5660 | 426 | 2983 |
| [12+14] Enriched metadata-aware retrieval + story index | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his actions and using her intelligence and resourcefulness. Here's how she did it: * **Foreknowledge of Holmes:** She had bee... | 6262 | 425 | 2826 |
| [12+15] Combined metadata-aware retrieval + story index | Irene Adler outsmarted Holmes in "A Scandal in Bohemia" by anticipating his methods and fleeing with her husband. She was warned about Holmes months in advance and knew that if the King employed an... | 6418 | 366 | 2648 |

## Query: "Describe the scene where Holmes fights Moriarty at Reichenbach Falls."

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | I am sorry, but the provided stories do not contain any information about Holmes fighting Moriarty at Reichenbach Falls. Therefore, I cannot describe that scene. | 139856 | 32 | 2491 |
| [03+04] Naive RAG | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 4345 | 23 | 984 |
| [05+06] RAG + structural metadata | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 4511 | 23 | 952 |
| [07+08] RAG + LLM-enriched tags | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 5007 | 23 | 878 |
| [09] Structural metadata-aware retrieval (no story index) | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 4422 | 23 | 812 |
| [10] Enriched metadata-aware retrieval (no story index) | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 6372 | 23 | 920 |
| [11] Combined metadata-aware retrieval (no story index) | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 6372 | 23 | 884 |
| [12+13] Structural metadata-aware retrieval + story index | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 4511 | 23 | 884 |
| [12+14] Enriched metadata-aware retrieval + story index | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 5007 | 23 | 909 |
| [12+15] Combined metadata-aware retrieval + story index | The provided passages do not contain enough information to describe the scene where Holmes fights Moriarty at Reichenbach Falls. | 5007 | 23 | 1123 |

## Query: "Compare how Holmes treats Watson in the first story versus the last story of the collection."

| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |
|----------|----------------------------------|--------------|---------------|--------------|
| [02] Long context baseline | In "A Scandal in Bohemia," Holmes treats Watson as a trusted confidant and partner. He explicitly states, "Not a bit, Doctor. Stay where you are. I am lost without my Boswell." He also involves Wat... | 139859 | 214 | 6347 |
| [03+04] Naive RAG | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer glimpses into various inte... | 5666 | 74 | 1139 |
| [05+06] RAG + structural metadata | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer glimpses into various stor... | 5826 | 71 | 1209 |
| [07+08] RAG + LLM-enriched tags | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer glimpses into various stor... | 6407 | 74 | 1210 |
| [09] Structural metadata-aware retrieval (no story index) | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer glimpses into various stor... | 5826 | 71 | 1369 |
| [10] Enriched metadata-aware retrieval (no story index) | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer snippets from various stor... | 5849 | 71 | 1065 |
| [11] Combined metadata-aware retrieval (no story index) | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages include excerpts from "A Scandal... | 7022 | 92 | 1329 |
| [12+13] Structural metadata-aware retrieval + story index | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages are excerpts from various storie... | 5919 | 67 | 3087 |
| [12+14] Enriched metadata-aware retrieval + story index | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages offer glimpses into various stor... | 7088 | 67 | 1160 |
| [12+15] Combined metadata-aware retrieval + story index | The provided passages do not contain enough information to compare how Holmes treats Watson in the first story versus the last story of the collection. The passages include excerpts from "A Scandal... | 7022 | 89 | 1369 |

## Cost Summary

| Approach | Avg input tokens | Avg output tokens | Indexing cost | Query cost (avg) | Total setup + 6 queries |
|----------|------------------|-------------------|---------------|------------------|-------------------------|
| [02] Long context baseline | 139857 | 167 | $0.000000 | $0.042374 | $0.254246 |
| [03+04] Naive RAG | 5548 | 164 | $0.002341 | $0.002075 | $0.014789 |
| [05+06] RAG + structural | 5734 | 248 | $0.002341 | $0.002342 | $0.016391 |
| [07+08] RAG + enriched | 6317 | 171 | $0.131217 | $0.002324 | $0.145159 |
| [09] Structural metadata-aware retrieval (no story index) | 5687 | 296 | $0.002341 | $0.002610 | $0.018002 |
| [10] Enriched metadata-aware retrieval (no story index) | 6481 | 146 | $0.131217 | $0.002470 | $0.146036 |
| [11] Combined metadata-aware retrieval (no story index) | 6708 | 164 | $0.131217 | $0.002585 | $0.146725 |
| [12+13] Structural metadata-aware retrieval + story index | 5569 | 188 | $0.138778 | $0.003173 | $0.157816 |
| [12+14] Enriched metadata-aware retrieval + story index | 6249 | 189 | $0.136437 | $0.003384 | $0.156739 |
| [12+15] Combined metadata-aware retrieval + story index | 6258 | 176 | $0.136437 | $0.003349 | $0.156530 |
