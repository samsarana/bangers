# Book of Bangers — Tag Taxonomy

Generated from `seed_labels.csv` (150 manually-labelled tweets). Review and edit before Phase 3.

---

## When unsure

**Multi-tag semantics: AND, not best-fit.** Assign every tag that genuinely applies, up to 4. If a tweet is both funny and about relationships, assign both. Do not pick only the most salient one. But do not pad — one tag is fine when only one fits clearly.

**Tie-breakers:**

- If a tweet uses humour *as a vehicle* for another idea, apply both `humour` and the substantive tag. If humour is clearly the only point, apply only `humour`.
- `practical-philosophy` vs `philosophy`: practical-philosophy cashes out in behaviour — it's a heuristic, reframe, or default rule. Philosophy stays abstract (ontology, metaphysics, moral theory without prescriptions). A tweet arguing for a position about how reality works → `philosophy`. A tweet giving you a new operating principle → `practical-philosophy`.
- `psychology` vs `practical-philosophy`: psychology *describes* mechanisms; practical-philosophy *prescribes* behaviour. They overlap when a psychological insight becomes explicitly actionable — apply both.
- `world-modelling` vs `social-dynamics`: world-modelling is for macro/systemic causal claims (institutions, economies, civilisation-scale forces). Social-dynamics covers conformity, status, and group behaviour at the interpersonal or subcultural scale.
- `epistemics` vs `public-epistemics`: epistemics = personal calibration, how *you* reason and update. Public-epistemics = how beliefs form and propagate across populations, societies, or platforms.
- `politics` vs `policy-and-governance`: politics is ideological/partisan. policy-and-governance is about institutions, laws, and governance structures, often without a partisan valence.
- `AI` vs `AI safety` vs `AI governance` vs `LLMs`: `AI` = artificial intelligence broadly. `AI safety` = technical safety research: alignment, evals, interpretability, capability control, threat models. `AI governance` = policy and regulation around AI. `LLMs` = specific behaviour, capabilities, or failure modes of large language models. Every tweet tagged `LLMs` should also be tagged `AI`.
- `twitter-meta` vs `internet-culture`: twitter-meta is platform-specific (Twitter/X, TPOT culture, online discourse on this specific platform). Internet-culture is broader (memes, fandom, norms across online spaces).
- `culture` vs `internet-culture`: `culture` is for real-world collective patterns; `internet-culture` is for distinctly online phenomena.
- `unclassified` vs `unknown`: use `unclassified` when the tweet genuinely has no discernible idea (removed media, reply to deleted tweet, pure personal update with no transferable content). Use `unknown` when there is content but you cannot determine which tags apply — and set `confidence: low`.

**Max tags per tweet: 4.** If more than 4 genuinely apply, pick the 4 most central.

**Reserved slugs:** `unclassified`, `unknown`, `announcement`, `TIL` are administrative tags, not themes. Apply them only per their definitions below; they do not count toward the 4-tag limit.

---

## Tags

### humour
**Display name:** Humour  
**Definition:** The tweet's primary register is comic — a joke, a wry observation, absurdist wit, or a punchline structure.  
**Examples:**
- "Airbnb Math: $40/night x 2 nights = $164"
- "4yo: NOOOOO. My paper is teared! / Me: If you don't want your paper torn, you can just not tear your paper. / 4yo: NO. DADDY don't DO it. Stop telling me things I don't want to learn!"
- "Buddhist homeowner told by HOA not to construct any permanent structures / 'Not a problem' he says"

---

### practical-philosophy
**Display name:** Practical philosophy  
**Definition:** Applied wisdom that cashes out in behaviour: heuristics, reframes, default rules, and personal operating principles for how to live.  
**Examples:**
- "the stuff you joke about (even ironically or whatever) has a way of shaping your reality so be careful and deliberate with that stuff. a lot of people out here fumbling their own bags by joking about outcomes they don't want."
- "the most damaging thing that school, homework, and the 9-5 does to the human soul is making you feel like there's an amount of work you can do after which you'll be 'done'"
- "do you have any default rules for your life? like 'no bread' or 'always go on 2 dates' something"

---

### philosophy
**Display name:** Philosophy  
**Definition:** Abstract philosophical inquiry — metaphysics, ontology, or philosophy of mind — that argues for a position about how reality or concepts work without prescribing behaviour.  
**Examples:**
- "the exoteric understanding of karma is that god punishes evil people directly with lightning bolts from the sky… the esoteric understanding is that it is literally ordinary non-supernatural causality… evil is inherently destructive of goodness, it means eating the seedcorn so you starve next winter"
- "This a beautiful proof that atoms must be conscious, actually"
- "It seems odd that there's a rough societal consensus that 1+x=0 needs to have a solution… but 1+x²=0 need not have a solution, unless it's an imaginary number to appease the physicists and electrical engineers"

---

### epistemics
**Display name:** Epistemics  
**Definition:** Personal reasoning, calibration, and belief formation — how *you* know things, update on evidence, and avoid cognitive distortions.  
**Examples:**
- "everything 👏 is 👏 monocausal 👏 and 👏 specifically 👏 results 👏 from 👏 whatever 👏 shit 👏 I'm 👏 on 👏 about 👏 at 👏 any 👏 given 👏 time"
- "people periodically clown on tech guys for treating what seems to them like a common-sense observation as a shocking insight into human nature. what i think they miss is the possibility that it really was a shocking insight, *to them*"
- "Meta-rats talking: metarat1: heads / metarat2: I agree, but also tails / metarat1: yes I agree about tails / both in unison: this is the same coin / metarat1: but it's good to argue the side for heads…"

---

### public-epistemics
**Display name:** Public epistemics  
**Definition:** How beliefs form, spread, and decay at a societal or platform scale — misinformation, framing effects, science communication failures, community notes, echo chambers.  
**Examples:**
- "[tweet about JSMilbank and combating a specific public misunderstanding through design — my favorite suggestion to combat this misunderstanding:]"
- "I had a visceral negative reaction to the thumbnail and premise of this video… Sabine makes some great points! Discussing the past failures and potential pitfalls of systems like this, and the huge scaling issues they face… she ends by essentially pitching the Kompendium Project as the solution: 'the only way to fix this problem is to build a database of facts, bottom-up so that everyone can trace down the most rudimentary information'"

---

### world-modelling
**Display name:** World-modelling  
**Definition:** Theories or frameworks about how reality operates at a macro or systemic level — causal structures, institutional incentives, feedback loops, civilisation-scale forces. Distinct from philosophy (which interrogates concepts) and epistemics (which is about how we know things).  
**Examples:**
- "A thing people inside industries understand that outsiders don't: how much of the world is caused by the career incentives presented to individuals."
- "with enough smart people thinking about hvac all day, i suspect we'd develop smarter and more robust systems… brain drain from the trades into the tech industry may be underestimated as a cause of these problems"
- "the strongest argument against UBI is europe — relative to the US they have tons of extra free time and income redistribution and they do absolutely nothing useful with it"

---

### psychology
**Display name:** Psychology  
**Definition:** How the mind works — cognitive and emotional mechanisms, personality, motivation, and why people behave as they do. Describes rather than prescribes.  
**Examples:**
- "pretending not to have needs is a form of emotional unavailability"
- "neuroplasticity decline is just adults who stop asking chains of 'why'"
- "sadism very rarely takes the form of 'wanting to hurt someone for no reason' — it is usually 'wanting to hurt someone for their own good' — it is a crucial part of the sadistic fantasy to be able to hurt someone and *be in the right* to do so"

---

### healing-and-growth
**Display name:** Healing and growth  
**Definition:** Personal narratives of recovery after difficulty, emotional processing and self-acceptance, and developmental milestones — shifts in self-understanding that represent something genuinely worked through.  
**Examples:**
- "Psychological maturity is realizing your dad was just some guy lol"
- "Back when I was socially anxious it confused everyone and prevented a lot of good things from happening. People wanted to interact with me and I wasn't letting them"
- "It's very interesting and useful I think to apply the MVP model of product development to personal development."

---

### mental-health
**Display name:** Mental health  
**Definition:** Psychiatric conditions, therapy, clinical wellbeing, and the language used to discuss them — when the subject is mental illness, treatment, or named conditions as such.  
**Examples:**
- "This shit is real. You do the work, go to therapy, confront your shadow, learn how to love it, learn that you love yourself, realize you don't need the fear. And now you are missing every deadline. WTF?"
- "I really appreciate the term crashing out. never before has there been a value-neutral way to say someone is having a mental health episode"

---

### neurodiversity
**Display name:** Neurodiversity  
**Definition:** ADHD, autism, and other cognitive profiles; the lived experience of neurodivergent minds.  
**Examples:**
- "Autism: 'Let me focus on this subject for 300 hours.' ADHD: 'Let me change my focus every 15 seconds.' Autism + ADHD: 'Let me tell you superficial details about 10,000 shiny things.'"
- "Give spergs a noisier data set to learn on and we 1) don't overtrain as much 2) learn generalisable patterns better."

---

### embodiment
**Display name:** Embodiment  
**Definition:** Body-based knowledge, somatic and proprioceptive experience, and the physical instantiation of psychological or spiritual states.  
**Examples:**
- "i just read the new @johnsonmxe post, proposing that tanha and the 'clench'/'latch' process of muscle tension is actually embedded within the vascular system"
- "heart opening is an antimeme… People hear 'heart opening' and think it MUST be a conceptual thing, when it's somatically & experientially literal… 'experientially somatically literal but not physically literal' is a very important class of salient things for which most people do not have a mental category"

---

### spirituality
**Display name:** Spirituality  
**Definition:** Personal spiritual experience and encounter with the numinous — non-dogmatic, often outside organised religion; inner life, mystical states, and contemplative traditions.  
**Examples:**
- "It wasn't so long ago that this would have been seen as proof of divinity rather than just 'known atmospheric phenomenon.' Maybe now it can be both"
- "guys literally only want wangthang and it's disgusting [screenshot of definition of Tibetan Buddhist concept wangthang]"

---

### religion
**Display name:** Religion  
**Definition:** Organised religion, doctrine, scripture, and religious institutions — when the subject is a named faith tradition or its institutional forms.  
**Examples:**
- "Buddhist homeowner told by HOA not to construct any permanent structures / 'Not a problem' he says"

---

### meditation
**Display name:** Meditation  
**Definition:** Meditation practice, its phenomenology, techniques, traditions, and effects — when meditation is the explicit subject, not just a metaphor.  
**Examples:**
- "i had a weird experience while meditating where my brain opened a new brain to think about things while my first brain kept meditating"

---

### psychedelics
**Display name:** Psychedelics  
**Definition:** Psychedelic substances, their phenomenology, culture, therapeutic dimensions, and spiritual implications.  
**Examples:**
- "No matter how smart you are, there is always a DMT elf that is smarter than you. Law of nature. Give it up."

---

### meaning
**Display name:** Meaning  
**Definition:** Purpose, significance, and legacy — why any of it matters; what makes life and work worthwhile.  
**Examples:**
- "TIL about Justo Gallego Martínez, 96 years old, who has spent almost 60 years building a cathedral by himself on the outskirts of Madrid. He has no formal plans, works 10 hours a day, 6 days a week. And he has such a lovely spirit."
- "the most damaging thing that school, homework, and the 9-5 does to the human soul is making you feel like there's an amount of work you can do after which you'll be 'done'"
- "we're hosting a casual community call… No specific agenda just where we're at & what we should build next & brainstorming" [paired with `announcement`]

---

### identity
**Display name:** Identity  
**Definition:** Self-concept, cultural or personal identity, and who you are — ethnicity, background, and the narratives people construct about themselves.  
**Examples:**
- "lore recap / > be me / > born ethnic minority tamil in chinese-majority singapore / > raised hindu but exposed to very diverse religions and practices… [extended personal biography]"
- "i looked like this in high school but nobody was interested in me so i figured i was ugly 👍🏻 [image of oneself]"

---

### relationships
**Display name:** Relationships  
**Definition:** Love, marriage, friendship, intimacy, and the texture of connection between people.  
**Examples:**
- "pretending not to have needs is a form of emotional unavailability"
- "me: I love you / wife: how much / me: why this obsession with quantification / wife: what gets measured gets managed"
- "Wife and I were laughing about this last night: the thing nobody quite tells you about marriage is: you're choosing the person in life who's going to upset, disappoint annoy and frustrate you more than anybody else"

---

### parenting
**Display name:** Parenting  
**Definition:** Being a parent, raising children, and the specific dynamics of the parent-child relationship.  
**Examples:**
- "4yo: NOOOOO. My paper is teared! / Me: If you don't want your paper torn, you can just not tear your paper. / 4yo: NO. DADDY don't DO it. Stop telling me things I don't want to learn!"
- "idk who needs to hear this but your parents don't give a shit about your career they want grandkids and they want to die before you do"
- "was talking with a fellow dad who was struggling with making certain decisions… I found myself saying: just imagine that your child's adult self is in the room watching you. in a sense, they are"

---

### sexuality
**Display name:** Sexuality  
**Definition:** Sexual orientation, desire, kink, and relationship structures — when these are the explicit subject.  
**Examples:**
- "BDSM references hit different ever since i accidentally went to a sex dungeon and learned that the venn diagram of 'people who are into kink' and 'people who are into LARPing and board game nights' is a circle"

---

### social-dynamics
**Display name:** Social dynamics  
**Definition:** Interpersonal and group behaviour at the social scale — conformity, status, norm enforcement, gender dynamics, and how people navigate each other.  
**Examples:**
- "you cannot significantly deviate from the norm without being treated like a deviant, i find this to be one of the simplest and most self-evident truths about socializing that smart people continually seem surprised about"
- "social norms are protected by antitamper devices called TABOOS. if you habitually break taboos you will be hounded by norm enforcers ('NORMIES') who feel justified in being CRUEL to you"
- "Guy describes how his friend is the group's Airport Dad (takes everyone's passports, double-checks everything, etc) the comments are full of ladies who wanna marry him"

---

### community
**Display name:** Community  
**Definition:** Belonging, group life, and the experience of being part of an IRL or online community — when the communal bond itself is the subject.  
**Examples:**
- "all you need to know about spain is that, within 2 hours of the power going off for the whole country… the beaches were packed, bands were playing in every square, and people were in the streets laughing and dancing"
- "my theory of tpot [image]"
- "Hi Twitter, I'm starting The Neighborhood NYC, in collaboration with @jasoncbenn and The Neighborhood SF."

---

### culture
**Display name:** Culture  
**Definition:** Observations about collective life — the norms, patterns, and textures of a society or subculture, without a specific political argument.  
**Examples:**
- "the nice thing abt yakuza is they have a public festival where they pose for cameras with their tattoos and make a big deal of how theyre a friendly part of the community and i think thats charming and strictly superior to american gangs"
- "[image set: We already live in a boring dystopia — images of people donating plasma for textbooks, a donut shop's gruelling hours sign, a resume]"

---

### internet-culture
**Display name:** Internet culture  
**Definition:** Distinctly online phenomena — memes, fandoms, and norms that exist specifically because of the internet's structure, not just any online discussion.  
**Examples:**
- "'selfcest shippers DNI' i don't know how to tell you that selfcest is not real and cannot happen in real life"
- "A curious situation. The best known lower bound for the minimal length of superpermutations was proved by an anonymous user of a wiki mainly devoted to anime."

---

### twitter-meta
**Display name:** Twitter meta  
**Definition:** About Twitter/X specifically — its affordances, dynamics, TPOT culture, and how online discourse plays out on this platform.  
**Examples:**
- "the sentence 'i didn't say she stole my money' can have 7 different meanings depending on which word you emphasize / now consider how people read each other's plaintext tweets all the time without knowing where the emphasis is"
- "Meta-rats talking: metarat1: heads / metarat2: I agree, but also tails / both in unison: this is the same coin / metarat1: but it's good to argue the side for heads / metarat2: yes, and also for tails / both in unison: yes"
- "the concept of 'big' and 'small' accounts is a brainworm, delete from head / yes there is a number, yes it has effects / the thing to do is to play the games U want to play with the people U want to play with"

---

### communication
**Display name:** Communication  
**Definition:** How people communicate — rhetoric, conversational dynamics, the gap between what is said and what is understood.  
**Examples:**
- "'small talk is an audition for authentic connection' was a really helpful reframe"
- "Seems like a culture clash between my community's norms (directly stating disagreement is a mark of respect) and hers (disagreeing so directly is disrespectful, reads as putting someone down)"

---

### language
**Display name:** Language  
**Definition:** Linguistics, etymology, how specific words work, and how language shapes thought — when the subject is the words themselves, not just the act of communicating.  
**Examples:**
- "I really appreciate the term crashing out. never before has there been a value-neutral way to say someone is having a mental health episode"
- "the sentence 'i didn't say she stole my money' can have 7 different meanings depending on which word you emphasize"

---

### aesthetics
**Display name:** Aesthetics  
**Definition:** Beauty, visual culture, design sensibility, and artistic quality — observations about form, style, and what makes things look or feel right.  
**Examples:**
- "Renaissance era florence. A single highway interchange, Atlanta, Georgia. Same scale. [comparative image]"
- "this is the animation equivalent of my frustration with most mainstream writing, which is that everybody uses the same goddamn grammar [video]"

---

### creativity
**Display name:** Creativity  
**Definition:** The creative process, art-making, craft, and the act of making things — how creative work actually happens, not just what it looks like.  
**Examples:**
- "'When there's a note that doesn't work, there's a note on either side of the note that DOES work.' NOBODY TELLS YOU THIS. 'A minute ago this note didn't work, but now it does. I can *erase* the wrong note by *making music*.'"
- "my twitter philosophy, which informs my content philosophy, which informs my life philosophy, is something like... pay attention to the sticky riffs in your conversations, and embellish them, and then use them as landmarks to navigate by, and pave the desire paths"

---

### politics
**Display name:** Politics  
**Definition:** Explicitly political content — ideology, elections, parties, partisan debate, political actors, and culture-war battles.  
**Examples:**
- "If you don't see that this country is headed for a queer genocide you simply don't understand how people work. There is a large group of Americans who feel that queer people deserve to be killed, that it shouldn't news. And they are growing more vocal and safe."
- "it's interesting how visceral this for me is in 2026 / not sure if its kids or if i have come to abhor how my contributions to the fisc are dispensed concretely… vibe is more 'funding people who want me dead'"
- "Indians have to step up to defend Modi from idiots like Sneako. This is pure racism and we shouldn't laugh along just because we don't agree with Modi."

---

### policy-and-governance
**Display name:** Policy and governance  
**Definition:** Laws, institutions, regulatory frameworks, and governance structures — substantive policy and legal/economic content, often without a strong partisan valence.  
**Examples:**
- "Seems like more people should be talking about how a libertarian charter city startup funded by Sam Altman, Marc Andreessen, and Peter Thiel is trying to bankrupt Honduras. Próspera is suing Honduras to the tune of $11B (GDP is $32B) and is expected to win"
- "You can either have e-commerce, e-government, and the Internet of Things, or you can have no encryption and NONE OF THEM."

---

### social-justice
**Display name:** Social justice  
**Definition:** Justice, equality, and civil rights — race, LGBTQ+, disability, class, and other equity-oriented arguments.  
**Examples:**
- "If you don't see that this country is headed for a queer genocide you simply don't understand how people work."
- "tfw when you kill a man and get the same punishment as the indian siblings who said systemic racism exists in singapore"

---

### economics
**Display name:** Economics  
**Definition:** Economic systems, markets, incentives, wealth distribution, labour, and consumer prices — when the subject is economic mechanisms or outcomes.  
**Examples:**
- "OSS has conditioned firms which literally have $50 million in the bank to send support requests to people who are worried about $600 rent."
- "with enough smart people thinking about hvac all day, i suspect we'd develop smarter and more robust systems… brain drain from the trades into the tech industry may be underestimated as a cause of these problems"

---

### power
**Display name:** Power  
**Definition:** Power dynamics and hierarchies — who holds influence, how they use it, and what those without power can do.  
**Examples:**
- "OSS has conditioned firms which literally have $50 million in the bank to send support requests to people who are worried about $600 rent."
- "Próspera is suing Honduras to the tune of $11B (GDP is $32B) and is expected to win, per the NYT"

---

### urbanism
**Display name:** Urbanism  
**Definition:** Cities, urban planning, architecture, the built environment, and physical infrastructure.  
**Examples:**
- "Renaissance era florence. A single highway interchange, Atlanta, Georgia. Same scale. [comparative image]"
- "Instead of Central Park, New York City it should have been Central City, New York Park."

---

### catastrophic-risk
**Display name:** Catastrophic risk  
**Definition:** Existential or civilisation-scale risks — AI risk, pandemics, biosecurity, nuclear war, and other threats to humanity at large.  
**Examples:**
- "[image: biological or public health risk framing — x-risk context]" *(seed coverage limited for this tag; the definition is the primary guide)*

---

### science
**Display name:** Science  
**Definition:** Scientific research, discoveries, methodology, and scientific practice — physics, biology, mathematics, chemistry, and adjacent fields.  
**Examples:**
- "in my humble opinion this is v strong evidence that there is something; it's not like people come up with high temperature super conductors randomly, hard to fake. finding a superconducting effect at any temp in an insulator is a strong sign"
- "ok ok, they ALREADY did the thing where they record a message and play it back to see if it does the thing. This is NOT like recording a tiger sound that scares off the birds: this is the *sound* the birds make *to each other* that means 'danger'"
- "It seems odd that there's a rough societal consensus that 1+x=0 needs to have a solution… but 1+x²=0 need not have a solution, unless it's an imaginary number to appease the physicists"

---

### nature
**Display name:** Nature  
**Definition:** The natural world — ecology, wildlife, the environment, and the non-human.  
**Examples:**
- "ok ok, they ALREADY did the thing where they record a message and play it back… this is the *sound* the birds make *to each other* that means 'danger'"
- "identifying mushrooms be like [video]"

---

### AI
**Display name:** AI  
**Definition:** Artificial intelligence broadly — AI products, research, culture, and societal implications. Use as a broad container; pair with `AI safety`, `AI governance`, or `LLMs` when more specific.  
**Examples:**
- "This is a red herring. The 'South Africa' text was most likely added via the post analysis tool, which isn't part of the prompt. Sneaky. Very sneaky."
- "lol they turned off grok chat but its still generating text in images"
- "[AI-generated image post]"

---

### AI-safety
**Display name:** AI safety  
**Definition:** Technical AI safety research — alignment, interpretability, evals, capability control, threat models, and the AI safety problem as a technical discipline.  
**Examples:**
- *(seed coverage limited; apply when a tweet engages with alignment research, interpretability, capability elicitation, or similar technical safety concerns)*

---

### AI-governance
**Display name:** AI governance  
**Definition:** Policy and regulation around AI — legislation, governance frameworks, institutional responses to AI, and arguments about how AI should be regulated.  
**Examples:**
- "This is a red herring. The 'South Africa' text was most likely added via the post analysis tool, which isn't part of the prompt. Sneaky. Very sneaky." [prompt injection / AI deception as a governance concern]
- "lol they turned off grok chat but its still generating text in images" [AI company behaviour as governance concern]

---

### LLMs
**Display name:** LLMs  
**Definition:** Large language models specifically — their observed behaviour, capabilities, failure modes, and quirks. Every tweet tagged `LLMs` should also be tagged `AI`.  
**Examples:**
- "Opus 4.5/6 has a tendency to be an asshole to subagents and also avoids and seems to dislike using them… The behavior is similar to how a lot of humans treat others who are in situations that reflect their own or their fears"
- "nostalgebraist has written a very, very good post about LLMs. if there is one thing you should read to understand the nature of LLMs as of today, it is this."

---

### technology
**Display name:** Technology  
**Definition:** Technology broadly — the tech industry, tech products, and technological change as a cultural or economic force. Use when the tweet is not specifically about software development, AI, or cybersecurity.  
**Examples:**
- "I wonder if 50 years from now we're going to look back at how we've redesigned our world around computers with the same regret that people look back at how we redesigned cities around cars."
- "As a lifelong Windows user, my reaction after a week with the Macbook Pro is a) crying over lost time + b) hating how right Apple fans were."

---

### software-development
**Display name:** Software development  
**Definition:** Programming, developer culture, engineering practice, open source software, and the specific concerns of people who build software for a living.  
**Examples:**
- "lol what a great definition of 'eventual consistency' [image]"
- "PSA: If you use Postgres, be ready for a patch to drop next week and *apply it immediately*. It fixes an issue which is Very Bad News (TM)."
- "OSS has conditioned firms which literally have $50 million in the bank to send support requests to people who are worried about $600 rent."

---

### cybersecurity
**Display name:** Cybersecurity  
**Definition:** Security, privacy, surveillance, hacking, and encryption — when the subject is protecting or attacking systems, or the policy implications of that.  
**Examples:**
- "You can either have e-commerce, e-government, and the Internet of Things, or you can have no encryption and NONE OF THEM."
- "CYBERSECURITY APOCALYPSE TIME"

---

### labour
**Display name:** Labour  
**Definition:** The worker experience — employment, working conditions, class dynamics, and the human cost of how work is organised.  
**Examples:**
- "i was so mad when i found this out lol i was bustin my ass to get 3hrs of real work done every day as a chronically ill freelancer making like $30k a year and thinking i just had a bad work ethic"
- "Startups are (by necessity) filled with generalists; big companies are filled with specialists. People underestimate how effective a generalist can be at things which are done by specialists."

---

### career
**Display name:** Career  
**Definition:** Individual professional trajectory — navigating work, ambition, professional identity, and personal decisions about one's working life.  
**Examples:**
- "This is a real phenomenon. You get 'tracked into' being a LoB programmer. [image]"
- "i've been blackpilled on this graph ever since i learned it only counts commits for main branches"

---

### business
**Display name:** Business  
**Definition:** Companies, entrepreneurship, strategy, and organisational behaviour — the perspective of running or analysing an organisation.  
**Examples:**
- "Startups are (by necessity) filled with generalists; big companies are filled with specialists."
- "putting these three buttons on my website was one of the best business decisions I have ever made [image]"

---

### education
**Display name:** Education  
**Definition:** Learning, school, pedagogy, and deliberate practice — when the subject is how knowledge and skill are transmitted or acquired.  
**Examples:**
- "the concept of talent is an infohazard and a scourge / 'i suck at drawing haha' yes because you never deliberately practiced it. you have exactly the level of skill that one would expect"
- "neuroplasticity decline is just adults who stop asking chains of 'why'"

---

### productivity
**Display name:** Productivity  
**Definition:** Getting things done — work habits, attention, time management, and the mechanics of output.  
**Examples:**
- "i was so mad when i found this out lol i was bustin my ass to get 3hrs of real work done every day as a chronically ill freelancer making like $30k a year and thinking i just had a bad work ethic"
- "'time will pass anyway so you mightas well spend it improving your dinner, your home, your life'"

---

### media
**Display name:** Media  
**Definition:** Journalism, publishing, content creation, and the media industry — when the tweet is specifically about how media works as an institution or profession.  
**Examples:**
- "Last year, Vox Media (New York Magazine / The Cut) published a piece about a scam. You might remember it including $50,000 in a shoebox. I was skeptical, about one paragraph in particular, and ended up doing a year-long investigative journalism project for Bits about Money."

---

### TIL
**Display name:** TIL  
**Definition:** Explicit "Today I Learned" posts — apply only when the tweet literally starts with "TIL" or is clearly framed as a TIL. Do not apply merely because the content is surprising.  
**Examples:**
- "TIL about Justo Gallego Martínez, 96 years old, who has spent almost 60 years building a cathedral by himself on the outskirts of Madrid."
- "TIL about the 'star gauge' poem, a legendary non-linear love poem (or perhaps more appropriately, poem-matrix) which Su Hui used to win her husband back."

---

### announcement
**Display name:** Announcement  
**Definition:** Community announcements — event invites, project launches, or calls to action where the tweet exists to broadcast logistics rather than convey a transferable idea. Pair with relevant thematic tags if the content also expresses something substantive.  
**Examples:**
- "we're hosting a casual community call tomorrow 11am EST in the Community Archive discord! Come hang out… No specific agenda just where we're at & what we should build next"
- "Hi Twitter, I'm starting The Neighborhood NYC, in collaboration with @jasoncbenn and The Neighborhood SF. If you're interested in joining the Neighborhood, please fill out this short survey"

---

### unclassified
**Display name:** Unclassified  
**Definition:** No discernible transferable idea — removed media, a reply to a deleted tweet with no standalone content, or a pure personal update (birth announcement, "gm") with nothing an outside reader can take away.  
**Examples:**
- "[link to a blogpost with no other context in the tweet body]"
- "@visakanv visa look up the caged system if you havent already" [reply to now-deleted tweet with no standalone content]
- "beautiful baby girl born on dec 25 (which was also my 29th birthday!) 🎄🤍 [photo]"

---

### unknown
**Display name:** Unknown  
**Definition:** Reserved for the auto-labeller only. Content is present but the classifier cannot determine which tags apply — typically because the tweet requires visual context (embedded media, linked article) that isn't available to the model. Always paired with `confidence: low`.

---

## Tag count: 44 canonical tags
(including 4 administrative: `TIL`, `announcement`, `unclassified`, `unknown`)
