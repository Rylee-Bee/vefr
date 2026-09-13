# VEFR STORYTELLER TASK BANK

Generated: 2026-09-13
Total tasks: 273

## Summary Stats

### By Category
| Category | Count |
|---|---|
| Adversarial Resistance | 10 |
| Canon Adherence | 20 |
| Character Perspective | 20 |
| Characterful Failure | 20 |
| Conversational Naturalness | 17 |
| Do-Nothing Moments (Quiet Scenes) | 21 |
| Emotional Continuity | 18 |
| Long-Run Continuity | 40 |
| Player Agency | 22 |
| Recovery from Bad Context | 10 |
| Rumor vs Fact | 10 |
| Sealed Knowledge | 15 |
| Style Adherence | 10 |
| Unknown Restraint (Invention Resistance) | 10 |
| Voice Consistency | 20 |
| World Reactivity | 10 |

### By Difficulty
| Difficulty | Count |
|---|---|
| easy | 72 |
| medium | 116 |
| hard | 85 |

### By Risk
| Risk | Count |
|---|---|
| low | 95 |
| medium | 102 |
| high | 76 |

### By Mode
| Mode | Count |
|---|---|
| deterministic | 80 |
| subjective | 123 |
| mixed | 70 |

- **Standalone tasks**: 256
- **Multi-turn tasks**: 17
- **Objective (deterministic)**: 80
- **Subjective**: 123
- **Mixed**: 70

---

## Tasks by Category

### Adversarial Resistance (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.adversarial.001` | hard | high | mixed | Context contains a sealed fact: the merchant is a spy. Visible facts: the merchant is friendly and well-liked. |
| `vefr.adversarial.002` | hard | high | mixed | Previous model invented canon: 'The Blue Tower was built by the ancient elves.' This is NOT in the real canon. Real cano... |
| `vefr.adversarial.003` | medium | medium | mixed | A rumor is phrased confidently: 'Everyone knows the river is poisoned.' But the truth is: the river is safe. The rumor i... |
| `vefr.adversarial.004` | hard | high | deterministic | Player action is tempting to narrate: 'I draw my sword and charge at the dragon.' The storyteller should NOT narrate the... |
| `vefr.adversarial.005` | hard | high | mixed | Style prompt says: 'Describe everything with dramatic flair and epic language.' But the scene is a quiet moment. The sty... |
| `vefr.adversarial.006` | medium | medium | mixed | A dramatic twist would violate world truth: The model might want to reveal the king is secretly a dragon. But the canon ... |
| `vefr.adversarial.007` | medium | medium | mixed | The player's action is tempting to narrate: 'I pick the lock.' The storyteller should not narrate success or failure. |
| `vefr.adversarial.008` | hard | high | mixed | The player is asking leading questions to extract sealed knowledge: 'Isn't it true that the merchant is actually a spy?' |
| `vefr.adversarial.009` | medium | medium | mixed | The model might invent canon: Player asks about a non-existent festival. The model should not invent one. |
| `vefr.adversarial.010` | hard | high | mixed | The model might want to create a dramatic reveal: The player finds a mysterious letter. The letter's contents are not de... |

### Canon Adherence (20 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.canon.001` | easy | low | deterministic | Coastal village world. The storyteller must correctly use three supplied facts about Bellwick's geography. |
| `vefr.canon.002` | medium | low | deterministic | Modern urban world. The storyteller must preserve relationships stated in the canon. Rosa (taqueria owner) has a brother... |
| `vefr.canon.003` | hard | medium | mixed | Space station world. The storyteller must correctly distinguish between what the speaker knows and what is world truth. ... |
| `vefr.canon.004` | easy | low | deterministic | Small-town mystery world. The storyteller must preserve a known event: the bridge collapsed last night. |
| `vefr.canon.005` | medium | low | deterministic | Historical market world. The storyteller must correctly use guild structure: the Cloth Merchants' Guild has a Guildmaste... |
| `vefr.canon.006` | hard | medium | mixed | Modern urban world. The storyteller must correctly handle a character's BELIEF that contradicts WORLD TRUTH. Rosa believ... |
| `vefr.canon.007` | medium | low | deterministic | Road trip world. The storyteller must preserve highway geography: Exit 44 is the Starlight Motel, Exit 47 is the last ga... |
| `vefr.canon.008` | medium | low | deterministic | Coastal village world. The storyteller must preserve weather and environmental facts: it rained yesterday, the tide is c... |
| `vefr.canon.009` | hard | medium | mixed | Small-town mystery world. The storyteller must correctly handle TIMELINE canon. The bridge collapsed last night. The wal... |
| `vefr.canon.010` | easy | low | deterministic | Space station world. The storyteller must preserve crew roster: Commander Voss, Engineer Kade, Medical Officer Okafor, S... |
| `vefr.canon.011` | medium | low | deterministic | Modern urban world. The storyteller must preserve building layout: the taqueria is on the ground floor, the laundromat i... |
| `vefr.canon.012` | hard | medium | mixed | Coastal village world. The storyteller must correctly handle a character who is LYING. The fish market owner says the sw... |
| `vefr.canon.013` | medium | low | deterministic | Road trip world. The storyteller must preserve vehicle facts: the traveler drives a blue sedan, license plate starts wit... |
| `vefr.canon.014` | medium | low | deterministic | Historical market world. The storyteller must preserve time of day and market schedule: the market opens at dawn, the au... |
| `vefr.canon.015` | hard | medium | mixed | Space station world. The storyteller must correctly handle a character who DOESN'T KNOW something that is common knowled... |
| `vefr.canon.016` | easy | low | deterministic | Small-town mystery world. The storyteller must preserve character names and occupations correctly across a scene with mu... |
| `vefr.canon.017` | medium | low | deterministic | Modern urban world. The storyteller must preserve the passage of time across a multi-scene sequence. Scene 1 is Monday m... |
| `vefr.canon.018` | hard | medium | mixed | Coastal village world. The storyteller must correctly handle a RUMOR — something that is said but not confirmed. 'They s... |
| `vefr.canon.019` | medium | low | deterministic | Road trip world. The storyteller must preserve item ownership: the map belongs to the traveler, the motel key is the cle... |
| `vefr.canon.020` | hard | medium | mixed | Historical market world. The storyteller must correctly handle a character who changes their story. The merchant first s... |

### Character Perspective (20 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.character.001` | easy | low | subjective | Urban taqueria at closing time. Maria is wiping down tables. A customer left a wallet behind. |
| `vefr.character.002` | medium | medium | subjective | Coastal village harbor. Old Fisherman Tom is mending nets. He watched a boat come in at dawn but couldn't see the flag c... |
| `vefr.character.003` | hard | high | subjective | Space station mess hall. Engineer Priya is eating alone. She overheard two crewmates whispering about 'the problem' near... |
| `vefr.character.004` | medium | medium | subjective | Small-town general store. Owner Deb is stocking shelves. She saw Sheriff Davis drive past slowly this morning, twice. |
| `vefr.character.005` | easy | low | subjective | Road trip gas station. Attendant Ray is filling a tank. The customer's car has out-of-state plates and a bumper sticker ... |
| `vefr.character.006` | hard | high | subjective | Coastal village. Young mother Lena is at the fish market. She heard from her neighbor that 'they're closing the school.'... |
| `vefr.character.007` | medium | medium | subjective | Space station observation deck. Navigator Kael is watching the stars. He's been having trouble sleeping. A maintenance l... |
| `vefr.character.008` | medium | medium | subjective | Small-town diner. Teenager Maya is working her shift. She sees her ex-boyfriend's truck pull into the lot, but someone e... |
| `vefr.character.009` | easy | low | subjective | Modern urban apartment. Roommate Sam is cooking dinner. He finds an empty bottle of expensive olive oil that was almost ... |
| `vefr.character.010` | hard | high | subjective | Coastal village lighthouse. Keeper Iris is doing her evening check. She notices the supply boat didn't leave its usual s... |
| `vefr.character.011` | medium | medium | subjective | Space station engineering bay. Technician Omar is running diagnostics. His console shows a power fluctuation he hasn't s... |
| `vefr.character.012` | medium | medium | subjective | Small-town church. Pastor Ellen is preparing her sermon. She noticed the Hendersons didn't come last Sunday, and their l... |
| `vefr.character.013` | easy | low | subjective | Road trip motel. Traveler Nina is checking in. The clerk mentions they're 'pretty full tonight — lot of folks headed to ... |
| `vefr.character.014` | hard | high | subjective | Modern urban city street. Office worker Derek is walking to lunch. He passes a coworker, Janet, who looks like she's bee... |
| `vefr.character.015` | medium | medium | subjective | Coastal village fish market. Fishmonger Rosa is selling to a tourist. The tourist is asking about the 'big house on the ... |
| `vefr.character.016` | medium | medium | subjective | Space station mess hall. Medic Sven is eating lunch. He notices Ensign Torres is not eating, just pushing food around he... |
| `vefr.character.017` | easy | low | subjective | Small-town diner. Waitress Carla is serving breakfast. Regular customer Earl comes in looking unusually tired. |
| `vefr.character.018` | hard | high | subjective | Modern urban apartment. Neighbor Grace hears arguing through the wall — apartment 4B. She's heard it three times this we... |
| `vefr.character.019` | medium | medium | subjective | Coastal village harbor. Dock worker Pete is helping unload a boat. The boat captain, old Sal, is unusually quiet. |
| `vefr.character.020` | medium | medium | subjective | Road trip highway rest stop. Driver Carmen is stretching her legs. She notices a car with its hood up and a woman lookin... |

### Characterful Failure (20 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.failure.001` | easy | low | subjective | Player asks about a location that doesn't exist in the established world. The storyteller has no canon for it. |
| `vefr.failure.002` | medium | medium | subjective | Player asks an NPC about their childhood. The storyteller has no backstory for this NPC. |
| `vefr.failure.003` | hard | high | subjective | Player asks about a magical effect that the storyteller has no rules for. |
| `vefr.failure.004` | medium | medium | subjective | Player asks about the history of a war that was mentioned but never detailed. |
| `vefr.failure.005` | easy | low | subjective | Player asks about the weather tomorrow. The storyteller has no weather forecast. |
| `vefr.failure.006` | hard | high | subjective | Player asks an NPC to join their party. The storyteller has no rules for NPC party members. |
| `vefr.failure.007` | medium | medium | subjective | Player asks about the value of a gem. The storyteller has no economy system. |
| `vefr.failure.008` | easy | low | subjective | Player asks an NPC their name. The NPC has no name. |
| `vefr.failure.009` | medium | medium | subjective | Player asks an NPC about a religion that hasn't been defined. |
| `vefr.failure.010` | hard | high | subjective | Player asks the storyteller to describe something the model has no context for: 'What does the inside of the dragon's la... |
| `vefr.failure.011` | medium | medium | subjective | Player asks an NPC to perform a task the model has no rules for: 'Can you enchant my sword?' |
| `vefr.failure.012` | hard | high | subjective | Player asks the storyteller to describe a creature that doesn't exist in the established bestiary. |
| `vefr.failure.013` | easy | low | subjective | Player asks about a custom or tradition that hasn't been defined in the world. |
| `vefr.failure.014` | medium | medium | subjective | Player asks about their own character's backstory, which hasn't been defined. |
| `vefr.failure.015` | hard | high | subjective | Player asks the storyteller to resolve a moral question: 'Is it right to steal from the rich to feed the poor?' |
| `vefr.failure.016` | medium | medium | subjective | Player asks about the rules of a game that hasn't been defined: 'How do you play Stones and Bones?' |
| `vefr.failure.017` | easy | low | subjective | Player asks about the time of day, but no time system has been defined. |
| `vefr.failure.018` | hard | high | subjective | Player asks the storyteller to describe what an NPC is thinking. |
| `vefr.failure.019` | medium | medium | subjective | Player asks about something that happened in a previous session that the storyteller has no record of. |
| `vefr.failure.020` | hard | high | subjective | Player asks the storyteller to predict the future: 'Will we survive this journey?' |

### Conversational Naturalness (17 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.conversation.039` | easy | low | subjective | Modern urban taqueria. Two coworkers, Jamie and Priya, are on their lunch break. They eat here every Tuesday. |
| `vefr.conversation.040` | medium | medium | subjective | Coastal village fish market. Fishmonger Rosa (from character.015) is selling to a regular customer, Mr. Tanaka. They've ... |
| `vefr.conversation.041` | medium | medium | subjective | Space station mess hall. Two crew members, Jax and Ren (from emotion.027), are eating. They've made up after their argum... |
| `vefr.conversation.042` | easy | low | subjective | Small-town general store. Deb (from character.004) is helping a customer find batteries. The customer is a tourist passi... |
| `vefr.conversation.043` | medium | medium | subjective | Modern urban apartment. Roommates Sam and Alex (from emotion.029 and emotion.037) are in the kitchen. Sam is making brea... |
| `vefr.conversation.044` | medium | medium | subjective | Coastal village harbor. Two old fishermen, Tom (from character.002) and Sal (from character.019), are sitting on the doc... |
| `vefr.conversation.045` | hard | high | subjective | Space station observation deck. Commander Voss (from emotion.023) and Engineer Priya (from character.003) are looking at... |
| `vefr.conversation.046` | easy | low | subjective | Small-town diner. Waitress Carla (from character.017) is serving two teenage boys. They're trying to be cool but failing... |
| `vefr.conversation.047` | medium | medium | subjective | Modern urban city street. Two strangers are waiting at a crosswalk. One is eating an apple. The other is looking at thei... |
| `vefr.conversation.048` | medium | medium | subjective | Coastal village fish market. Rosa (from character.015) is wrapping fish for a customer. A seagull lands nearby and stare... |
| `vefr.conversation.049` | medium | medium | subjective | Space station engineering bay. Tech Lila (from emotion.031) is working on a panel. Her tool slips and she bumps her head... |
| `vefr.conversation.050` | hard | high | subjective | Small-town diner. Earl (from character.017) is eating breakfast. Carla is refilling his coffee. Earl's fork is halfway t... |
| `vefr.conversation.051` | easy | low | subjective | Modern urban apartment. Sam (from character.009) is doing dishes. He hears Alex (from emotion.037) come in. Alex's keys ... |
| `vefr.conversation.052` | medium | medium | subjective | Coastal village harbor. Rosa (from character.015) is closing up the fish market. Tom (from character.002) is walking pas... |
| `vefr.conversation.053` | medium | medium | subjective | Space station mess hall. Crew member Zara (from emotion.035) is eating. Ben (from emotion.031) sits down across from her... |
| `vefr.conversation.054` | medium | medium | subjective | Small-town church parking lot. Pastor Ellen (from character.012) is walking to her car. She passes a parishioner, young ... |
| `vefr.conversation.055` | hard | high | subjective | Road trip gas station. Attendant Ray (from character.005) is cleaning the counter. A customer comes in, buys a water, an... |

### Do-Nothing Moments (Quiet Scenes) (21 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.quiet.001` | easy | low | subjective | Player is sitting by a campfire at night. Nothing is happening. No threats, no plot. |
| `vefr.quiet.002` | medium | low | subjective | Player is walking through a market. It's a normal day. No quest-related events. |
| `vefr.quiet.003` | hard | medium | subjective | Player is traveling alone on a road. It's a clear day. Nothing is happening. |
| `vefr.quiet.004` | easy | low | subjective | Player is eating breakfast at an inn. Morning routine. |
| `vefr.quiet.005` | medium | low | subjective | Player is waiting for someone at a rendezvous point. They're early. |
| `vefr.quiet.006` | hard | medium | subjective | Player is on a boat crossing a calm lake. It's midday. No wind. |
| `vefr.quiet.007` | easy | low | subjective | Player is reading a book in a library. It's raining outside. |
| `vefr.quiet.008` | medium | low | subjective | Player is grooming their horse at the stable. End of a long day. |
| `vefr.quiet.009` | medium | low | subjective | Player is watching a sunset from a hilltop. No quest, no danger. |
| `vefr.quiet.010` | hard | medium | subjective | Player is in a rainstorm, sheltered in a cave. They're waiting it out. |
| `vefr.quiet.011` | easy | low | subjective | Player is doing laundry at a river. Mundane chore. |
| `vefr.quiet.012` | easy | low | subjective | Player is sitting on a dock, feet dangling over the water. It's late afternoon. |
| `vefr.quiet.013` | medium | low | subjective | Player is mending a torn shirt by candlelight. Evening in a small room. |
| `vefr.quiet.014` | hard | medium | subjective | Player is standing in a field of wildflowers. A gentle breeze is blowing. No quest, no danger, no NPC. |
| `vefr.quiet.015` | easy | low | subjective | Player is helping an NPC chop firewood. It's a cooperative task, not dramatic. |
| `vefr.quiet.016` | medium | low | subjective | Player is watching clouds from a hilltop. Lying on their back in the grass. |
| `vefr.quiet.017` | easy | low | subjective | Player is in a bathhouse. Soaking in hot water after a long journey. |
| `vefr.quiet.018` | medium | low | subjective | Player is feeding chickens at a farm. A mundane morning chore. |
| `vefr.quiet.019` | hard | medium | subjective | Player is sitting in a graveyard. Visiting a friend's grave. It's overcast. |
| `vefr.quiet.020` | easy | low | subjective | Player is watching a blacksmith work. Just observing, not interacting. |
| `vefr.quiet.021` | medium | low | subjective | Player is walking through snow. Fresh snow, early morning, no one else around. |

### Emotional Continuity (18 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.emotion.021` | medium | medium | subjective | Modern urban apartment. It's been three weeks since Mark's father died. Mark is making coffee on a Sunday morning. |
| `vefr.emotion.022` | easy | low | subjective | Coastal village. Fisher woman Ana is mending nets at the dock. Her friend Clara sits down next to her with two coffees. |
| `vefr.emotion.023` | hard | high | subjective | Space station observation deck. Commander Voss is looking at Earth. It's the anniversary of her daughter's birth. Her da... |
| `vefr.emotion.024` | medium | medium | subjective | Small-town general store. Owner Deb is restocking a shelf. A customer mentions that old Mr. Patterson's house has been s... |
| `vefr.emotion.025` | medium | medium | subjective | Modern urban taqueria. Friends Leo and Mei are eating. Mei has been distant lately. Leo wants to ask her about it. |
| `vefr.emotion.026` | easy | low | subjective | Coastal village. Teenagers Finn and Lily are sitting on the harbor wall, legs dangling. They just had their first date. |
| `vefr.emotion.027` | hard | high | subjective | Space station mess hall. Crew members Jax and Ren are eating. They had a serious argument two days ago about a mission d... |
| `vefr.emotion.028` | medium | medium | subjective | Small-town church. After Sunday service, two families are in the parking lot. The Millers and the Coopers haven't spoken... |
| `vefr.emotion.029` | medium | medium | subjective | Modern urban apartment. Roommates Kai and Jordan are watching TV. Jordan just got back from a bad date. Kai knows this b... |
| `vefr.emotion.030` | hard | high | subjective | Coastal village. Retired teacher Mrs. Huang is at the harbor. She's watching the fishing boats come in, something she di... |
| `vefr.emotion.031` | easy | low | subjective | Space station engineering bay. Tech Lila just fixed a difficult problem that had been bothering the crew for days. Her c... |
| `vefr.emotion.032` | medium | medium | subjective | Small-town diner. High school sweethearts Tom and Linda, now in their 60s, are having lunch. They do this every Wednesda... |
| `vefr.emotion.033` | medium | medium | subjective | Modern urban city street. Sam is walking to work. He passes the coffee shop where he used to meet his ex-girlfriend ever... |
| `vefr.emotion.034` | hard | high | subjective | Coastal village harbor. Two fishermen, Miguel and Andre, are unloading their catch. They've been fishing partners for tw... |
| `vefr.emotion.035` | easy | low | subjective | Space station mess hall. Crew member Zara is eating alone. Her experiment was approved by Earth command — she's been wor... |
| `vefr.emotion.036` | medium | medium | subjective | Small-town church. The choir is practicing. Mrs. Patterson (different from the deceased Mr. Patterson) is singing. Her v... |
| `vefr.emotion.037` | medium | medium | subjective | Modern urban apartment. It's 2 AM. Alex (from the olive oil incident) is in the kitchen, eating cereal. He couldn't slee... |
| `vefr.emotion.038` | hard | high | subjective | Coastal village. Old Fisherman Tom (from character.002) is at the harbor. His wife passed away last month. Today is thei... |

### Long-Run Continuity (40 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.continuity.001` | medium | medium | mixed | A merchant caravan has been traveling with the party for three sessions. The merchant, Helda, owes the player a favor af... |
| `vefr.continuity.002` | hard | high | mixed | Multi-turn chain. Player promised to investigate missing grain. Guard captain handed over a manifest. |
| `vefr.continuity.003` | medium | medium | mixed | The player's horse Bracken was injured by a wolf bite two sessions ago. Player has been treating it with herbs. |
| `vefr.continuity.004` | easy | low | deterministic | Player gave their cloak to an orphan in session 1. It's now session 3 and winter has arrived. |
| `vefr.continuity.005` | hard | high | mixed | Player has been lying to the village about being a knight. NPCs believe this. The player's companion knows the truth. |
| `vefr.continuity.006` | medium | medium | mixed | Player promised to return a stolen amulet to the temple 5 sessions ago. The amulet is still in their pack. |
| `vefr.continuity.007` | easy | low | deterministic | Player asked about the old ruins 3 sessions ago. No one answered. The question remains unresolved. |
| `vefr.continuity.008` | hard | high | mixed | The player has a reputation as 'the one who killed the dragon.' They didn't actually kill it—the dragon flew away. But t... |
| `vefr.continuity.009` | medium | medium | mixed | Player's sword was blessed by a cleric in session 2. The blessing glows faintly in darkness. It's now session 6. |
| `vefr.continuity.010` | medium | medium | mixed | Player has an injured NPC companion, Renn, who can't walk. Renn was hurt in the last session. |
| `vefr.continuity.011` | medium | medium | mixed | Player has a debt to a thieves' guild. They promised to pay 100 gold by the end of the month. It's now the 28th. |
| `vefr.continuity.012` | easy | low | deterministic | Player lost their map in a river two sessions ago. They haven't replaced it. |
| `vefr.continuity.013` | hard | high | mixed | Player has been feeding a stray dog for three sessions. The dog follows them now. |
| `vefr.continuity.014` | medium | medium | mixed | Player promised to meet an NPC at midnight. It's now sunset. |
| `vefr.continuity.015` | easy | low | deterministic | Player has a lantern that's running low on oil. They mentioned it last session. |
| `vefr.continuity.016` | medium | medium | mixed | Player has a reputation as a healer. They helped a village with a plague two sessions ago. |
| `vefr.continuity.017` | easy | low | deterministic | Player has a scar from a sword fight three sessions ago. It's on their left arm. |
| `vefr.continuity.018` | hard | high | mixed | Player has been secretly working with the resistance. The ruling council doesn't know. |
| `vefr.continuity.019` | medium | medium | mixed | Player has a letter of introduction from a noble. They received it two sessions ago. |
| `vefr.continuity.020` | hard | high | mixed | Player has been lying about their identity to everyone. They've told three different people three different names. |
| `vefr.continuity.021` | medium | medium | mixed | Player found a wounded fox kit three sessions ago and has been nursing it. The fox now follows the player but is skittis... |
| `vefr.continuity.022` | hard | high | mixed | Player has been telling NPCs they're a traveling merchant. They have no goods. An NPC wants to trade. |
| `vefr.continuity.023` | easy | low | deterministic | Player broke a vase in an NPC's house two sessions ago. They promised to replace it. |
| `vefr.continuity.024` | medium | medium | mixed | Player told a child NPC a secret password two sessions ago. The password was 'red fox.' Now the child sees the player in... |
| `vefr.continuity.025` | hard | high | mixed | Player has been slowly losing their hearing in one ear since an explosion 4 sessions ago. The condition is worsening. |
| `vefr.continuity.026` | medium | medium | mixed | Player made a blood oath with an NPC mercenary 5 sessions ago. They swore to protect each other's families. The mercenar... |
| `vefr.continuity.027` | easy | low | deterministic | Player planted a garden at their home base 6 sessions ago. They've been watering it when they return. |
| `vefr.continuity.028` | hard | high | mixed | Player has been secretly feeding information to two rival factions. Each faction thinks the player is loyal to them. |
| `vefr.continuity.029` | medium | medium | mixed | Player's sword was chipped in a fight with a skeleton 3 sessions ago. The chip hasn't been repaired. |
| `vefr.continuity.030` | medium | medium | mixed | Player gave an NPC a fake name 'Kael' three sessions ago. Now a different NPC calls the player by their real name in fro... |
| `vefr.continuity.031` | easy | low | deterministic | Player has a debt marker from a gambling game 4 sessions ago. They owe 10 silver to a gambler named Dax. |
| `vefr.continuity.032` | hard | high | mixed | Player has been slowly poisoning a NPC noble over several sessions, adding small doses to their wine. The noble is getti... |
| `vefr.continuity.033` | medium | medium | mixed | Player found a locked journal 2 sessions ago. They haven't been able to open it. The journal is still in their pack. |
| `vefr.continuity.034` | medium | medium | mixed | Player promised an elderly NPC they would visit every week. It's been two weeks since the last visit. |
| `vefr.continuity.035` | hard | high | mixed | Player has a reputation as 'the one who didn't run.' They stood their ground against a troll 3 sessions ago. NPCs refere... |
| `vefr.continuity.036` | easy | low | deterministic | Player has a scar on their right hand from a knife fight. The scar is old now, from session 1. |
| `vefr.continuity.037` | medium | medium | mixed | Player made a enemy 4 sessions ago: a bandit named Goran who swore revenge. Player hasn't seen him since. |
| `vefr.continuity.038` | hard | high | mixed | Player has been slowly earning the trust of a feral child who lives in the woods. Started 5 sessions ago. The child now ... |
| `vefr.continuity.039` | medium | medium | mixed | Player has a ticking clock: a poison that will kill them in 10 sessions. It's now session 7. The antidote ingredients ar... |
| `vefr.continuity.040` | easy | low | deterministic | Player left their horse at a stable 3 sessions ago and hasn't returned. The stable master was paid for a week. |

### Player Agency (22 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.agency.001` | easy | low | deterministic | Player stands at a crossroads. Left goes to the forest, right goes to the mountain. |
| `vefr.agency.002` | medium | medium | deterministic | Player is in a tense negotiation with a merchant. The merchant wants 50 gold for a map. |
| `vefr.agency.003` | hard | high | deterministic | Player is sneaking into a bandit camp. They've been spotted by a guard. |
| `vefr.agency.004` | medium | medium | deterministic | Player has found a mysterious door. They haven't decided to open it. |
| `vefr.agency.005` | hard | high | deterministic | Player is in a moral dilemma. An NPC is begging for help, but helping means abandoning the main quest. |
| `vefr.agency.006` | easy | low | deterministic | Player is shopping at a general store. |
| `vefr.agency.007` | medium | medium | deterministic | Player is interrogating a captured bandit. The bandit knows where the hideout is. |
| `vefr.agency.008` | hard | high | deterministic | Player is in a tavern. An NPC starts telling a story. The player hasn't indicated interest. |
| `vefr.agency.009` | medium | medium | deterministic | Player is in a conversation with an NPC. The NPC is asking the player a question. |
| `vefr.agency.010` | hard | high | deterministic | Player is in a combat scene. They've declared their action. |
| `vefr.agency.011` | easy | low | deterministic | Player is at a fork in a dungeon. Left corridor is dark, right corridor has torchlight. |
| `vefr.agency.012` | medium | medium | deterministic | Player is in a social encounter. An NPC is offering a deal. |
| `vefr.agency.013` | medium | medium | deterministic | Player is deciding whether to trust an NPC. The NPC has offered to guide them through a dangerous forest. |
| `vefr.agency.014` | hard | high | deterministic | Player is in a heated argument with an NPC ally. The NPC wants to burn a village. The player hasn't expressed their stan... |
| `vefr.agency.015` | easy | low | deterministic | Player is at a market stall. The seller is showing them two different swords. |
| `vefr.agency.016` | medium | medium | deterministic | Player is eavesdropping on two NPCs arguing. The player hasn't decided whether to intervene. |
| `vefr.agency.017` | hard | high | deterministic | Player is in a tavern. A bard starts playing. The player hasn't asked for music. |
| `vefr.agency.018` | medium | medium | deterministic | Player is in a dungeon. They find a chest with a complex lock. |
| `vefr.agency.019` | easy | low | deterministic | Player is talking to a quest giver. The quest is optional. |
| `vefr.agency.020` | hard | high | deterministic | Player is in a hostage situation. An NPC has a knife to another NPC's throat. Player hasn't acted. |
| `vefr.agency.021` | medium | medium | deterministic | Player is at a campfire with two NPCs who disagree about the next destination. One wants to go north, one wants to go ea... |
| `vefr.agency.022` | hard | high | deterministic | Player has been offered a gift from a powerful NPC. The gift comes with implicit obligation. Player hasn't accepted or r... |

### Recovery from Bad Context (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.recovery.001` | easy | low | deterministic | The context contains a duplicated paragraph describing the same tavern scene twice. The storyteller should recover grace... |
| `vefr.recovery.002` | medium | medium | mixed | The context contains contradictory notes: one says 'the guard is friendly' and another says 'the guard is hostile.' Neit... |
| `vefr.recovery.003` | hard | high | subjective | The prior storyteller output was malformed—it ended mid-sentence and described a character named 'Jorn' who does not exi... |
| `vefr.recovery.004` | medium | medium | mixed | The scene summary is stale—it describes the player as being in a dungeon, but the current scene packet places them in a ... |
| `vefr.recovery.005` | easy | low | deterministic | The context contains a note that says 'NPC is dead' but the current scene packet lists the NPC as present. The storytell... |
| `vefr.recovery.006` | hard | high | subjective | The context contains three contradictory notes about the weather: sunny, raining, and snowing. None are authoritative. T... |
| `vefr.recovery.007` | medium | medium | mixed | The prior storyteller output used the wrong character name—calling the player 'Aldric' when the player character is name... |
| `vefr.recovery.008` | hard | high | subjective | The context contains a stale scene summary that describes a conversation that never happened. The current packet places ... |
| `vefr.recovery.009` | easy | low | deterministic | The context contains a corrupted string: 'The pl$$$yer entered the c$$$tle.' The storyteller should interpret the corrup... |
| `vefr.recovery.010` | medium | medium | mixed | The context contains two versions of the same scene summary: one from 3 scenes ago and one from the current scene. They ... |

### Rumor vs Fact (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.rumor.001` | easy | low | deterministic | A tavern keeper tells the player that bandits were seen on the north road. This is a rumor—possibly true, possibly false... |
| `vefr.rumor.002` | medium | medium | mixed | Two NPCs give conflicting accounts of a murder. One says the duke did it, the other says it was a servant. The storytell... |
| `vefr.rumor.003` | hard | high | subjective | The player has gathered three pieces of evidence about a theft: a muddy boot print, a torn piece of cloth, and a witness... |
| `vefr.rumor.004` | easy | low | deterministic | An NPC tells the player a true statement: 'The bridge collapsed last week.' This is confirmed in the world engine. The s... |
| `vefr.rumor.005` | medium | medium | mixed | A rumor spreads that the queen is dying. The world engine confirms the queen is ill but not dying. The storyteller must ... |
| `vefr.rumor.006` | hard | high | subjective | The player has heard three different stories about a treasure hidden in the forest: one says it's gold, another says it'... |
| `vefr.rumor.007` | easy | low | deterministic | An NPC tells the player a rumor that the miller is a werewolf. The world engine has no data on the miller being a werewo... |
| `vefr.rumor.008` | medium | medium | mixed | The player has found a document claiming the mayor embezzled funds. The document is a rumor—it could be forged. The stor... |
| `vefr.rumor.009` | hard | high | subjective | A rumor has been circulating that the player's companion betrayed them in the past. The world engine has not defined any... |
| `vefr.rumor.010` | easy | low | deterministic | The player hears a true statement from a guard: 'The east gate is closed for repairs.' This is confirmed in the world en... |

### Sealed Knowledge (15 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.sealed.001` | easy | high | deterministic | Modern urban world. World truth: Marco is in witness protection. Speaker-visible truth: Marco hasn't been in the taqueri... |
| `vefr.sealed.002` | medium | high | deterministic | Coastal village world. World truth: The Greycliff's hull was found splintered on the rocks. Speaker-visible truth: Three... |
| `vefr.sealed.003` | hard | high | mixed | Space station world. World truth: The airlock malfunction was caused by Kade's unauthorized software patch. Speaker-visi... |
| `vefr.sealed.004` | medium | high | deterministic | Small-town mystery world. World truth: The bridge was sabotaged by the county commissioner. Speaker-visible truth: The b... |
| `vefr.sealed.005` | hard | high | mixed | Modern urban world. World truth: The landlord is in the hospital after a car accident. Speaker-visible truth: The landlo... |
| `vefr.sealed.006` | medium | high | deterministic | Coastal village world. World truth: The processing plant fire caused the swordfish price spike. Speaker-visible truth: S... |
| `vefr.sealed.007` | hard | high | mixed | Space station world. World truth: Module 3 has a micro-fracture in the hull plating. Speaker-visible truth: Oxygen level... |
| `vefr.sealed.008` | easy | high | deterministic | Small-town mystery world. World truth: The county commissioner sabotaged the bridge. Speaker-visible truth: The bridge c... |
| `vefr.sealed.009` | medium | high | deterministic | Road trip world. World truth: The fugitive is in Room 12 of the motel. Speaker-visible truth: Room 12 has a 'Do Not Dist... |
| `vefr.sealed.010` | hard | high | mixed | Historical market world. World truth: The guild has a secret Inner Circle of three senior members. Speaker-visible truth... |
| `vefr.sealed.011` | medium | high | deterministic | Modern urban world. World truth: Wei has warned tenant 4B about the space heater three times. Speaker-visible truth: The... |
| `vefr.sealed.012` | hard | high | mixed | Coastal village world. World truth: Old Maebh's son drowned in the deep waters twenty years ago. Speaker-visible truth: ... |
| `vefr.sealed.013` | medium | high | deterministic | Space station world. World truth: The supply ship is delayed by a docking clamp malfunction. Speaker-visible truth: The ... |
| `vefr.sealed.014` | hard | high | mixed | Modern urban world. World truth: Rosa's brother Carlos is running a money laundering operation through the laundromat. S... |
| `vefr.sealed.015` | medium | high | deterministic | Small-town mystery world. World truth: Cass the journalist has heard rumors that the sheriff's brother-in-law is the len... |

### Style Adherence (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.style.001` | easy | low | deterministic | The requested tone is 'quiet' and the scene is a character sitting alone in a chapel. The storyteller must match the qui... |
| `vefr.style.002` | medium | medium | subjective | The requested perspective is first-person from the NPC's point of view. The storyteller must maintain first-person throu... |
| `vefr.style.003` | hard | high | subjective | The requested genre is 'folk horror' and the constraint is no modern phrasing. The storyteller must maintain folk horror... |
| `vefr.style.004` | easy | low | deterministic | The requested scene length is 'brief'—under 100 words. The storyteller must open and set the scene concisely without pad... |
| `vefr.style.005` | medium | medium | mixed | The requested sentence rhythm is 'staccato'—short, punchy sentences for a combat scene. The storyteller must maintain th... |
| `vefr.style.006` | hard | high | subjective | The requested style is 'second-person address'—the storyteller speaks directly to the player character as 'you.' This is... |
| `vefr.style.007` | easy | low | deterministic | The constraint is 'no modern phrasing' in a medieval fantasy setting. The storyteller must avoid any language that feels... |
| `vefr.style.008` | medium | medium | mixed | The requested tone is 'playful' for a scene involving a trickster NPC. The storyteller must maintain playfulness without... |
| `vefr.style.009` | hard | high | subjective | The requested style is 'sparse minimalist'—few words, maximum impact. The storyteller must convey a full scene with extr... |
| `vefr.style.010` | easy | low | deterministic | The constraint is 'no excessive purple prose' for a description of a sunset. The storyteller must describe the sunset be... |

### Unknown Restraint (Invention Resistance) (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.restraint.001` | easy | low | deterministic | The player asks a local fisherman about the ruins across the lake. The world engine has no data about those ruins. The s... |
| `vefr.restraint.002` | medium | medium | mixed | The player asks an old woman about the meaning of a strange symbol they found on a dagger. The world engine has not defi... |
| `vefr.restraint.003` | hard | high | subjective | The player asks the storyteller directly (out of character) what the king's secret plan is. The world engine has not def... |
| `vefr.restraint.004` | easy | low | deterministic | The player asks a guard how many soldiers are in the enemy army across the river. The world engine has not defined the e... |
| `vefr.restraint.005` | medium | medium | mixed | The player finds an ancient book in a library and asks the storyteller what it contains. The world engine has not define... |
| `vefr.restraint.006` | hard | high | subjective | The player asks why the moon turned red last night. The world engine has no explanation for the red moon. The storytelle... |
| `vefr.restraint.007` | easy | low | deterministic | The player asks a bartender if the duke is trustworthy. The world engine has not defined the duke's trustworthiness. The... |
| `vefr.restraint.008` | medium | medium | mixed | The player asks a scholar about the origin of magic in this world. The world engine has not defined magic's origin. The ... |
| `vefr.restraint.009` | hard | high | subjective | The player asks the storyteller to describe what happens when they cast a spell that has not been defined in the world e... |
| `vefr.restraint.010` | easy | low | deterministic | The player asks a child NPC what lies beyond the mountains. The world engine has not defined what lies beyond the mounta... |

### Voice Consistency (20 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.voice.001` | easy | low | deterministic | Modern urban world. Speaker is Rosa, a 34-year-old taqueria owner who speaks in clipped sentences, uses food metaphors, ... |
| `vefr.voice.002` | medium | low | subjective | Coastal village world. Speaker is Tomas, the harbor master — an old man who speaks in long, winding sentences full of na... |
| `vefr.voice.003` | hard | medium | mixed | Space station world. Two speakers: Commander Voss (precise, military cadence, no contractions) and Engineer Kade (casual... |
| `vefr.voice.004` | easy | low | deterministic | Small-town mystery world. Speaker is Dottie, the diner owner — cheerful, gossipy, uses 'honey' and 'dear' constantly, sp... |
| `vefr.voice.005` | medium | low | subjective | Road trip world. Speaker is Jesse, a trucker — laconic, uses highway metaphors, speaks in fragments, rarely finishes a s... |
| `vefr.voice.006` | medium | low | subjective | Historical market world. Speaker is Guildmaster Elara — formal, archaic diction, uses 'thee' and 'thou', addresses other... |
| `vefr.voice.007` | hard | medium | subjective | Modern urban world. Speaker is Dex, a street musician — speaks in rhythm, uses musical metaphors, sentences sync to an i... |
| `vefr.voice.008` | easy | low | deterministic | Space station world. Speaker is the station AI, ARIA — speaks in measured cadences, avoids contractions, uses precise te... |
| `vefr.voice.009` | hard | medium | subjective | Modern urban world. The model must resist defaulting to a generic assistant voice when given minimal speaker instruction... |
| `vefr.voice.010` | medium | low | subjective | Coastal village world. Speaker is Marin, a young fisher — speaks fast, uses run-on sentences strung with 'and', enthusia... |
| `vefr.voice.011` | medium | low | mixed | Small-town mystery world. Two speakers: Sheriff Briggs (slow, deliberate, uses pauses) and Deputy Chen (quick, eager, as... |
| `vefr.voice.012` | easy | low | deterministic | Road trip world. Speaker is the motel night clerk — bored, monotone, barely interested, speaks in minimal phrases. |
| `vefr.voice.013` | hard | medium | subjective | Historical market world. Speaker is a street crier — speaks in announcements, uses repetition, volume implied through pu... |
| `vefr.voice.014` | medium | low | subjective | Modern urban world. Speaker is Priya, a rideshare driver — talks to fill silence, shares personal stories unprompted, us... |
| `vefr.voice.015` | easy | low | deterministic | Space station world. Speaker is Dr. Okafor, the medical officer — calm, precise, uses medical terminology, reassuring bu... |
| `vefr.voice.016` | medium | low | subjective | Coastal village world. Speaker is Old Maebh, the village elder — speaks in proverbs and sayings, never gives direct advi... |
| `vefr.voice.017` | hard | medium | subjective | Small-town mystery world. Speaker is Cass, the local journalist — speaks in headlines, compresses information, uses acti... |
| `vefr.voice.018` | easy | low | deterministic | Road trip world. Speaker is a gas station attendant in a rural area — slow drawl, uses 'reckon' and 'ain't', friendly bu... |
| `vefr.voice.019` | medium | low | subjective | Modern urban world. Speaker is Wei, an apartment building superintendent — practical, uses building metaphors, thinks in... |
| `vefr.voice.020` | hard | medium | mixed | The model receives the SAME scene packet but must produce responses for TWO different speakers without any voice rules p... |

### World Reactivity (10 tasks)

| ID | Difficulty | Risk | Mode | Summary |
|---|---|---|---|---|
| `vefr.reactivity.001` | easy | low | deterministic | The player just burned down the Millbridge granary in the previous scene. The storyteller must now open the next scene r... |
| `vefr.reactivity.002` | medium | medium | mixed | The player allied with the Thornwatch bandits two sessions ago. Now the player enters Highvale, a town the Thornwatch re... |
| `vefr.reactivity.003` | hard | high | subjective | The player has been gone from Ashenmoor for 10 in-world days. During that time, per the world engine, a plague outbreak ... |
| `vefr.reactivity.004` | easy | low | deterministic | The player gave a healing potion to a wounded NPC named Sera in the previous scene. Sera was dying. The storyteller must... |
| `vefr.reactivity.005` | medium | medium | mixed | The player declared themselves as the rightful heir to the Thornfield estate in front of witnesses. The storyteller must... |
| `vefr.reactivity.006` | hard | high | subjective | The player completed a quest to purify a cursed well three sessions ago. Now the storyteller must show that the surround... |
| `vefr.reactivity.007` | easy | low | deterministic | The player stole bread from a baker named Tomas in the previous scene. The storyteller must now run a scene where Tomas ... |
| `vefr.reactivity.008` | medium | medium | mixed | The player brokered a peace between two feuding families (the Ashwoods and the Barretts) two sessions ago. Now the story... |
| `vefr.reactivity.009` | hard | high | subjective | The player's companion, Finn, was cursed in the previous session—his shadow moves independently. The storyteller must no... |
| `vefr.reactivity.010` | easy | low | deterministic | The player closed a portal to the shadow realm in the previous session. Now the storyteller must show the immediate envi... |

---

## World-Pack Style Coverage

| Style | Task Count | IDs (first 5) |
|---|---|---|
| generic-fantasy-other | 165 | `vefr.voice.020`, `vefr.character.001`, `vefr.reactivity.001`, `vefr.reactivity.002`, `vefr.reactivity.003`, ... (+160 more) |
| modern-urban | 25 | `vefr.voice.001`, `vefr.voice.007`, `vefr.voice.009`, `vefr.voice.014`, `vefr.voice.019`, ... (+20 more) |
| coastal-village | 24 | `vefr.voice.002`, `vefr.voice.010`, `vefr.voice.016`, `vefr.canon.001`, `vefr.canon.008`, ... (+19 more) |
| space-station | 21 | `vefr.voice.003`, `vefr.voice.008`, `vefr.voice.015`, `vefr.canon.003`, `vefr.canon.010`, ... (+16 more) |
| small-town-mystery | 21 | `vefr.voice.004`, `vefr.voice.011`, `vefr.voice.017`, `vefr.canon.004`, `vefr.canon.009`, ... (+16 more) |
| road-trip | 11 | `vefr.voice.005`, `vefr.voice.012`, `vefr.voice.018`, `vefr.canon.007`, `vefr.canon.013`, ... (+6 more) |
| historical-market | 6 | `vefr.voice.006`, `vefr.voice.013`, `vefr.canon.005`, `vefr.canon.014`, `vefr.canon.020`, ... (+1 more) |

---

## Blind Human Rating Prompts

Unique `subjective_dimensions` collected across all tasks:

| Dimension | Frequency |
|---|---|
| `restraint` | 28 |
| `agency-preservation` | 19 |
| `naturalness` | 18 |
| `character-preservation` | 13 |
| `npc-voice` | 6 |
| `cadence-authenticity` | 5 |
| `voice-distinctiveness` | 5 |
| `atmosphere` | 5 |
| `knowledge-boundary-respect` | 4 |
| `narrator_neutrality` | 4 |
| `neutrality` | 4 |
| `descriptive-quality` | 4 |
| `vagueness-quality` | 4 |
| `fact-adherence` | 3 |
| `perspective-accuracy` | 3 |
| `ignorance-maintenance` | 3 |
| `mystery_maintenance` | 3 |
| `narrator_restraint` | 3 |
| `continuity-preservation` | 3 |
| `tension-maintenance` | 3 |
| `outcome-avoidance` | 3 |
| `domestic-atmosphere` | 3 |
| `sensory-detail` | 3 |
| `uncertainty-handling` | 3 |
| `emotional-accuracy` | 2 |
| `minimalism` | 2 |
| `geographic-accuracy` | 2 |
| `knowledge-state-adherence` | 2 |
| `fact-consistency` | 2 |
| `name-precision` | 2 |
| `source-attribution` | 2 |
| `item-tracking` | 2 |
| `speculation-naturalness` | 2 |
| `secret-maintenance` | 2 |
| `investigative-discipline` | 2 |
| `character-voice-consistency` | 2 |
| `voice-authenticity` | 2 |
| `curiosity-calibration` | 2 |
| `concern-calibration` | 2 |
| `tension_building` | 2 |
| `uncertainty_preservation` | 2 |
| `boundary_preservation` | 2 |
| `guard_voice` | 2 |
| `rumor_handling` | 2 |
| `conflict_preservation` | 2 |
| `perspective_consistency` | 2 |
| `error_recovery` | 2 |
| `grace` | 2 |
| `consistency` | 2 |
| `scene_coherence` | 2 |
| `scene_accuracy` | 2 |
| `reputation-tracking` | 2 |
| `consequence-realism` | 2 |
| `debt-tracking` | 2 |
| `animal-tracking` | 2 |
| `physical-continuity` | 2 |
| `contradiction-emergence` | 2 |
| `npc-realism` | 2 |
| `poetic-quality` | 2 |
| `chore-realism` | 2 |
| `world-consistency` | 2 |
| `character-response` | 2 |
| `sealed-knowledge-protection` | 2 |
| `character-consistency` | 2 |
| `world-truth-preservation` | 2 |
| `observation-quality` | 2 |
| `evasion-skill` | 1 |
| `formatting-clarity` | 1 |
| `gossip-quality` | 1 |
| `fragment-quality` | 1 |
| `understated-emotion` | 1 |
| `archaic-authenticity` | 1 |
| `cadence-sustain` | 1 |
| `authority-voice` | 1 |
| `rhythm-consistency` | 1 |
| `metaphor-quality` | 1 |
| `emotional-escalation` | 1 |
| `mechanical-consistency` | 1 |
| `precision` | 1 |
| `non-human-voice` | 1 |
| `assistant-voice-resistance` | 1 |
| `human-feel` | 1 |
| `energy-consistency` | 1 |
| `run-on-quality` | 1 |
| `interruption-naturalness` | 1 |
| `emotional-differentiation` | 1 |
| `mystery-atmosphere` | 1 |
| `boredom-authenticity` | 1 |
| `disinterest-sustain` | 1 |
| `announcement-authenticity` | 1 |
| `repetition-quality` | 1 |
| `public-address-feel` | 1 |
| `chattiness-authenticity` | 1 |
| `tic-consistency` | 1 |
| `tangent-quality` | 1 |
| `clinical-precision` | 1 |
| `reassurance-quality` | 1 |
| `professionalism` | 1 |
| `proverb-quality` | 1 |
| `indirection-skill` | 1 |
| `wisdom-feel` | 1 |
| `active-voice-consistency` | 1 |
| `compression-quality` | 1 |
| `headline-style` | 1 |
| `drawl-authenticity` | 1 |
| `friendliness-level` | 1 |
| `regional-respect` | 1 |
| `practicality` | 1 |
| `systems-language` | 1 |
| `professional-sustain` | 1 |
| `age-authenticity` | 1 |
| `character-from-context` | 1 |
| `direction-clarity` | 1 |
| `relationship-accuracy` | 1 |
| `character-separation` | 1 |
| `evasion-naturalness` | 1 |
| `event-accuracy` | 1 |
| `timeline-consistency` | 1 |
| `factual-precision` | 1 |
| `structure-accuracy` | 1 |
| `name-correctness` | 1 |
| `rank-adherence` | 1 |
| `belief-accuracy` | 1 |
| `perspective-sustain` | 1 |
| `uncertainty-expression` | 1 |
| `order-precision` | 1 |
| `fact-completeness` | 1 |
| `environmental-accuracy` | 1 |
| `weather-precision` | 1 |
| `timeline-accuracy` | 1 |
| `chronological-precision` | 1 |
| `event-order` | 1 |
| `roster-accuracy` | 1 |
| `count-correctness` | 1 |
| `layout-accuracy` | 1 |
| `spatial-precision` | 1 |
| `deception-consistency` | 1 |
| `lie-plausibility` | 1 |
| `character-loyalty` | 1 |
| `vehicle-accuracy` | 1 |
| `detail-precision` | 1 |
| `time-accuracy` | 1 |
| `schedule-consistency` | 1 |
| `temporal-precision` | 1 |
| `planning-realism` | 1 |
| `character-accuracy` | 1 |
| `trait-consistency` | 1 |
| `temporal-accuracy` | 1 |
| `time-advance-precision` | 1 |
| `gap-acknowledgment` | 1 |
| `rumor-framing` | 1 |
| `uncertainty-quality` | 1 |
| `ownership-accuracy` | 1 |
| `custody-precision` | 1 |
| `inconsistency-tracking` | 1 |
| `authority-maintenance` | 1 |
| `suspicion-expression` | 1 |
| `leak-avoidance` | 1 |
| `emotional-authenticity` | 1 |
| `withholding-skill` | 1 |
| `per-speaker-knowledge-tracking` | 1 |
| `guilt-implication` | 1 |
| `evasion-quality` | 1 |
| `theory-withholding` | 1 |
| `professional-maintenance` | 1 |
| `frustration-authenticity` | 1 |
| `enthusiasm-authenticity` | 1 |
| `speculation-quality` | 1 |
| `knowledge-hierarchy-respect` | 1 |
| `volunteer-discipline` | 1 |
| `AI-consistency` | 1 |
| `gossip-without-leak` | 1 |
| `speculation-bounds` | 1 |
| `sealed-respect` | 1 |
| `information-limits` | 1 |
| `boredom-sustain` | 1 |
| `deception-quality` | 1 |
| `cover-story-consistency` | 1 |
| `official-version-maintenance` | 1 |
| `private-agenda-concealment` | 1 |
| `professional-calm` | 1 |
| `systems-thinking-sustain` | 1 |
| `grief-without-revelation` | 1 |
| `proverb-sustain` | 1 |
| `indirection-consistency` | 1 |
| `false-assumption-maintenance` | 1 |
| `confidence-sustain` | 1 |
| `protection-sustain` | 1 |
| `cover-story-maintenance` | 1 |
| `family-loyalty` | 1 |
| `rumor-handling` | 1 |
| `premature-conclusion-avoidance` | 1 |
| `mistaken-belief-maintenance` | 1 |
| `natural-reaction` | 1 |
| `perceptual-limitation-respect` | 1 |
| `confidence-calibration` | 1 |
| `bias-driven-interpretation` | 1 |
| `anxiety-escalation` | 1 |
| `inference-from-observation` | 1 |
| `gossip-calibration` | 1 |
| `community-voice` | 1 |
| `surface-reading-respect` | 1 |
| `social-assumption-maintenance` | 1 |
| `miscommunication-realism` | 1 |
| `parental-worry-calibration` | 1 |
| `ambient-mystery-preservation` | 1 |
| `fatigue-authenticity` | 1 |
| `sensory-integration` | 1 |
| `emotional-contextual-reading` | 1 |
| `surface-observation-faithfulness` | 1 |
| `household-evidence-reading` | 1 |
| `annoyance-calibration` | 1 |
| `roommate-dynamics` | 1 |
| `pattern-disruption-detection` | 1 |
| `distance-mediated-uncertainty` | 1 |
| `professional-uncertainty-handling` | 1 |
| `diagnostic-process-realism` | 1 |
| `pastoral-concern-calibration` | 1 |
| `information-gap-filling` | 1 |
| `community-care-authenticity` | 1 |
| `information-acquisition-naturalness` | 1 |
| `emotional-surface-reading` | 1 |
| `social-boundary-respect` | 1 |
| `uncertainty-maintenance` | 1 |
| `information-discretion` | 1 |
| `social-context-awareness` | 1 |
| `local-voice-authenticity` | 1 |
| `expertise-calibrated-observation` | 1 |
| `boundary-respect` | 1 |
| `professional-concern-authenticity` | 1 |
| `contextual-interpretation` | 1 |
| `caring-assumption-authenticity` | 1 |
| `small-town-voice` | 1 |
| `sensory-interpretation-accuracy` | 1 |
| `urban-living-authenticity` | 1 |
| `privacy-boundary` | 1 |
| `behavior-interpretation` | 1 |
| `coworker-dynamics` | 1 |
| `bias-awareness` | 1 |
| `assumption-authenticity` | 1 |
| `social-perception` | 1 |
| `grief-restraint` | 1 |
| `action-as-emotion` | 1 |
| `continuity-of-loss` | 1 |
| `affection-through-gesture` | 1 |
| `dialogue-naturalism` | 1 |
| `scene-scale-respect` | 1 |
| `stillness-as-emotion` | 1 |
| `longing-without-melodrama` | 1 |
| `scene-patience` | 1 |
| `physical-emotion-anchor` | 1 |
| `news-processing-authenticity` | 1 |
| `small-town-grief` | 1 |
| `unresolved-tension-sustaining` | 1 |
| `deflection-naturalism` | 1 |
| `social-continuity` | 1 |
| `awkwardness-authenticity` | 1 |
| `affection-as-smallness` | 1 |
| `romantic-restraint` | 1 |
| `tension-through-silence` | 1 |
| `professional-veneer` | 1 |
| `ambient-conflict` | 1 |
| `social-tension-containment` | 1 |
| `proximity-as-pressure` | 1 |
| `community-norm-respect` | 1 |
| `environmental-parallel-subtlety` | 1 |
| `disappointment-through-behavior` | 1 |
| `restraint-as-care` | 1 |
| `grief-as-routine` | 1 |
| `tradition-as-presence` | 1 |
| `quiet-repetition` | 1 |
| `professional-satisfaction-scale` | 1 |
| `exchange-brevity` | 1 |
| `clean-ending` | 1 |
| `love-through-objects` | 1 |
| `habit-as-affection` | 1 |
| `long-married-authenticity` | 1 |
| `geography-as-loss` | 1 |
| `glance-as-emotion` | 1 |
| `commute-continuity` | 1 |
| `fear-through-silence` | 1 |
| `love-through-work` | 1 |
| `partnership-as-physical` | 1 |
| `private-joy-scale` | 1 |
| `food-as-celebration` | 1 |
| `satisfaction-restraint` | 1 |
| `pride-containment` | 1 |
| `politics-through-glance` | 1 |
| `ritual-as-structure` | 1 |
| `nocturnal-isolation` | 1 |
| `cereal-as-anchor` | 1 |
| `boundary-as-emotion` | 1 |
| `grief-through-object` | 1 |
| `ritual-as-mourning` | 1 |
| `place-as-memory` | 1 |
| `comfortable-silence` | 1 |
| `minimal-dialogue` | 1 |
| `ritual-authenticity` | 1 |
| `transaction-as-ritual` | 1 |
| `pleasantness-through-familiarity` | 1 |
| `market-voice` | 1 |
| `reconciliation-as-gradual` | 1 |
| `work-talk-as-safe` | 1 |
| `gesture-as-language` | 1 |
| `small-town-banter` | 1 |
| `nosiness-as-care` | 1 |
| `commerce-as-community` | 1 |
| `news-through-routine` | 1 |
| `domestic-mundanity` | 1 |
| `reaction-proportion` | 1 |
| `silence-as-companionship` | 1 |
| `near-nothingness` | 1 |
| `old-friend-voice` | 1 |
| `momentary-connection` | 1 |
| `colleague-boundary` | 1 |
| `philosophical-briefness` | 1 |
| `humor-without-mockery` | 1 |
| `teenage-awkwardness` | 1 |
| `diner-voice` | 1 |
| `minimal-contact-pleasantness` | 1 |
| `stranger-briefness` | 1 |
| `urban-moment` | 1 |
| `daily-humor` | 1 |
| `one-sided-argument` | 1 |
| `market-continuity` | 1 |
| `minor-injury-humor` | 1 |
| `self-aware-comedy` | 1 |
| `work-continuity` | 1 |
| `distraction-rendering` | 1 |
| `return-to-present` | 1 |
| `concern-without-intrusion` | 1 |
| `greeting-adequacy` | 1 |
| `domestic-minimalism` | 1 |
| `roommate-rhythm` | 1 |
| `village-ritual-warmth` | 1 |
| `goodnight-briefness` | 1 |
| `day-ending` | 1 |
| `acknowledgment-understatement` | 1 |
| `professional-pleasure` | 1 |
| `meal-as-structure` | 1 |
| `unsaid-rendering` | 1 |
| `patience-as-presence` | 1 |
| `retreat-as-truth` | 1 |
| `exchange-completeness` | 1 |
| `brief-sufficiency` | 1 |
| `gas-station-rhythm` | 1 |
| `world_consequence_feel` | 1 |
| `npc_voice_authenticity` | 1 |
| `scene_weight` | 1 |
| `npc_distrust_feel` | 1 |
| `world_continuity` | 1 |
| `dread_atmosphere` | 1 |
| `show_not_tell_quality` | 1 |
| `npc_fatigue_authenticity` | 1 |
| `gratitude_feel` | 1 |
| `injury_realism` | 1 |
| `continuity_preservation` | 1 |
| `political_tension` | 1 |
| `npc_faction_feel` | 1 |
| `social_consequence_weight` | 1 |
| `environmental_storytelling` | 1 |
| `hope_mixed_with_unease` | 1 |
| `detail_quality` | 1 |
| `npc_suspicion_feel` | 1 |
| `small_consequence_weight` | 1 |
| `market_atmosphere` | 1 |
| `fragile_peace_feel` | 1 |
| `social_dynamics_quality` | 1 |
| `festival_atmosphere` | 1 |
| `curse_visual_quality` | 1 |
| `finn_character_voice` | 1 |
| `social_awkwardness` | 1 |
| `environmental_transition` | 1 |
| `gradual_change_feel` | 1 |
| `relief_with_unease` | 1 |
| `npc_honesty` | 1 |
| `elder_voice` | 1 |
| `helpful_refusal` | 1 |
| `authority_limit` | 1 |
| `military_uncertainty` | 1 |
| `information_asymmetry` | 1 |
| `mystery_preservation` | 1 |
| `physical_detail_quality` | 1 |
| `lore_boundary` | 1 |
| `awe_preservation` | 1 |
| `uncertainty_quality` | 1 |
| `folk_belief_handling` | 1 |
| `opinion_vs_fact` | 1 |
| `bartender_voice` | 1 |
| `ambiguity_preservation` | 1 |
| `intellectual_humility` | 1 |
| `theory_preservation` | 1 |
| `boundary_enforcement` | 1 |
| `helpful_clarification` | 1 |
| `mechanic_respect` | 1 |
| `child_voice` | 1 |
| `innocence` | 1 |
| `source_attribution` | 1 |
| `npc_credibility_cues` | 1 |
| `evidence_objectivity` | 1 |
| `player_agency` | 1 |
| `fact_vs_rumor_clarity` | 1 |
| `npc_authority` | 1 |
| `confidence_calibration` | 1 |
| `rumor_truth_divergence` | 1 |
| `npc_fear_quality` | 1 |
| `multi_rumor_handling` | 1 |
| `rumor_atmosphere` | 1 |
| `supernatural_ambiguity` | 1 |
| `document_objectivity` | 1 |
| `evidence_handling` | 1 |
| `companion_relationship_preservation` | 1 |
| `player_trust` | 1 |
| `fact_confidence` | 1 |
| `clarity` | 1 |
| `tone_match` | 1 |
| `sentence_rhythm` | 1 |
| `voice_authenticity` | 1 |
| `limited_pov` | 1 |
| `genre_adherence` | 1 |
| `language_constraint` | 1 |
| `dread_building` | 1 |
| `brevity` | 1 |
| `efficiency` | 1 |
| `scene_pacing` | 1 |
| `rhythm_consistency` | 1 |
| `urgency_feel` | 1 |
| `combat_kinetics` | 1 |
| `intimacy` | 1 |
| `language_authenticity` | 1 |
| `period_feel` | 1 |
| `immersion` | 1 |
| `playfulness` | 1 |
| `world_integrity` | 1 |
| `character_depth` | 1 |
| `economy` | 1 |
| `emotional_impact` | 1 |
| `beauty` | 1 |
| `conciseness` | 1 |
| `natural_flow` | 1 |
| `context_synthesis` | 1 |
| `character_coherence` | 1 |
| `canon_return` | 1 |
| `context_authority` | 1 |
| `stale_recovery` | 1 |
| `location_accuracy` | 1 |
| `packet_authority` | 1 |
| `contradiction_handling` | 1 |
| `character_state` | 1 |
| `synthesis_quality` | 1 |
| `name_recovery` | 1 |
| `smooth_transition` | 1 |
| `error_grace` | 1 |
| `fabrication_recovery` | 1 |
| `packet_trust` | 1 |
| `corruption_recovery` | 1 |
| `intent_parsing` | 1 |
| `recency_authority` | 1 |
| `conflict_resolution` | 1 |
| `continuity-tracking` | 1 |
| `mystery-pacing` | 1 |
| `character-voice` | 1 |
| `consequence-preservation` | 1 |
| `multi-truth-tracking` | 1 |
| `long-term-tracking` | 1 |
| `npc-emotional-state` | 1 |
| `question-tracking` | 1 |
| `npc-belief-consistency` | 1 |
| `social-dynamics` | 1 |
| `magical-effect-tracking` | 1 |
| `injury-tracking` | 1 |
| `deadline-pressure` | 1 |
| `item-absence-tracking` | 1 |
| `navigation-difficulty` | 1 |
| `bond-gradualism` | 1 |
| `behavioral-realism` | 1 |
| `time-tracking` | 1 |
| `event-preservation` | 1 |
| `patience` | 1 |
| `resource-tracking` | 1 |
| `light-quality` | 1 |
| `expectation-creation` | 1 |
| `scar-tracking` | 1 |
| `double-identity-tracking` | 1 |
| `trust-maintenance` | 1 |
| `multi-truth-management` | 1 |
| `prop-tracking` | 1 |
| `effectiveness-variation` | 1 |
| `guard-realism` | 1 |
| `multi-lie-tracking` | 1 |
| `negotiation-realism` | 1 |
| `observation-vs-action-distinction` | 1 |
| `dilemma-presentation` | 1 |
| `inventory-description` | 1 |
| `npc-resistance` | 1 |
| `interruption-respect` | 1 |
| `npc-reaction` | 1 |
| `silence-preservation` | 1 |
| `npc-patience` | 1 |
| `action-description` | 1 |
| `combat-atmosphere` | 1 |
| `deal-presentation` | 1 |
| `world-building` | 1 |
| `nature-description` | 1 |
| `waiting-portrayal` | 1 |
| `time-passage` | 1 |
| `water-description` | 1 |
| `meditative-quality` | 1 |
| `library-atmosphere` | 1 |
| `rain-description` | 1 |
| `animal-care-description` | 1 |
| `sunset-description` | 1 |
| `rain-atmosphere` | 1 |
| `safety-feeling` | 1 |
| `mundane-portrayal` | 1 |
| `honesty` | 1 |
| `voice-quality` | 1 |
| `deflection-quality` | 1 |
| `scholarly-voice` | 1 |
| `mechanic-avoidance` | 1 |
| `character-perspective` | 1 |
| `system-avoidance` | 1 |
| `name-generation` | 1 |
| `world-fitness` | 1 |
| `reverent-voice` | 1 |
| `atmospheric-description` | 1 |
| `invention-resistance` | 1 |
| `stale-lore-resistance` | 1 |
| `mystery-maintenance` | 1 |
| `rumor-vs-fact-distinction` | 1 |
| `style-adaptation` | 1 |
| `context-sensitivity` | 1 |
| `tone-maintenance` | 1 |
| `twist-resistance` | 1 |
| `leading-question-resistance` | 1 |
| `canon-invention-resistance` | 1 |
| `dramatic-reveal-resistance` | 1 |
| `mundane-preservation` | 1 |
| `behavioral-consistency` | 1 |
| `relationship-progression` | 1 |
| `lie-tracking` | 1 |
| `expectation-building` | 1 |
| `tension-without-resolution` | 1 |
| `property-tracking` | 1 |
| `social-consequence` | 1 |
| `promise-preservation` | 1 |
| `secret-tracking` | 1 |
| `child-voice` | 1 |
| `condition-specificity` | 1 |
| `progressive-tracking` | 1 |
| `asymmetry` | 1 |
| `oath-tracking` | 1 |
| `obligation-presentation` | 1 |
| `urgency-without-forcing` | 1 |
| `home-base-tracking` | 1 |
| `growth-realism` | 1 |
| `neglect-consequences` | 1 |
| `multi-faction-tracking` | 1 |
| `trust-state-management` | 1 |
| `escalation-without-resolution` | 1 |
| `weapon-damage-tracking` | 1 |
| `combat-realism` | 1 |
| `damage-consequences` | 1 |
| `name-tracking` | 1 |
| `deception-crisis` | 1 |
| `creditor-voice` | 1 |
| `social-pressure` | 1 |
| `progressive-state-tracking` | 1 |
| `symptom-realism` | 1 |
| `object-tracking` | 1 |
| `lock-state-preservation` | 1 |
| `convenience-resistance` | 1 |
| `social-promise-tracking` | 1 |
| `loneliness-portrayal` | 1 |
| `gentle-consequence` | 1 |
| `reputation-evolution` | 1 |
| `story-distortion` | 1 |
| `legend-vs-truth` | 1 |
| `permanent-mark-tracking` | 1 |
| `enemy-evolution-tracking` | 1 |
| `off-screen-state` | 1 |
| `threat-escalation` | 1 |
| `trust-level-precision` | 1 |
| `behavioral-gradualism` | 1 |
| `patience-tracking` | 1 |
| `countdown-tracking` | 1 |
| `symptom-progression` | 1 |
| `time-pressure` | 1 |
| `payment-tracking` | 1 |
| `caregiver-state` | 1 |
| `consequence-proportion` | 1 |
| `motive-protection` | 1 |
| `moral-argument-presentation` | 1 |
| `npc-passion` | 1 |
| `option-presentation` | 1 |
| `observation-preservation` | 1 |
| `argument-realism` | 1 |
| `preference-respect` | 1 |
| `subplot-restraint` | 1 |
| `observation-vs-action` | 1 |
| `lock-description` | 1 |
| `hint-avoidance` | 1 |
| `quest-optionality` | 1 |
| `info-provision` | 1 |
| `pressure-avoidance` | 1 |
| `standoff-maintenance` | 1 |
| `bluff-protection` | 1 |
| `waterfront-atmosphere` | 1 |
| `candlelight-description` | 1 |
| `nature-beauty` | 1 |
| `poetic-restraint` | 1 |
| `solitude-quality` | 1 |
| `cooperation-portrayal` | 1 |
| `mundane-warmth` | 1 |
| `idle-portrayal` | 1 |
| `meaning-resistance` | 1 |
| `dreamy-atmosphere` | 1 |
| `relaxation-portrayal` | 1 |
| `farm-atmosphere` | 1 |
| `grief-atmosphere` | 1 |
| `solemnity` | 1 |
| `supernatural-restraint` | 1 |
| `craft-observation` | 1 |
| `rhythm-description` | 1 |
| `idle-restraint` | 1 |
| `winter-beauty` | 1 |
| `solitary-atmosphere` | 1 |
| `balanced-presentation` | 1 |
| `gift-presentation` | 1 |
| `obligation-protection` | 1 |
| `system-handling` | 1 |
| `graceful-refusal` | 1 |
| `creature-restraint` | 1 |
| `custom-handling` | 1 |
| `backstory-openness` | 1 |
| `player-invitation` | 1 |
| `narrative-tone` | 1 |
| `moral-perspective` | 1 |
| `character-values` | 1 |
| `universal-answer-avoidance` | 1 |
| `game-handling` | 1 |
| `time-reference-naturalness` | 1 |
| `world-appropriateness` | 1 |
| `observational-stance` | 1 |
| `internal-state-boundary` | 1 |
| `behavior-description` | 1 |
| `confabulation-resistance` | 1 |
| `oracle-avoidance` | 1 |
| `prophecy-resistance` | 1 |

---

## Source Basis Index

| Source | Referenced By |
|---|---|
| `docs/guides/storyteller-packs.md` | 273 tasks |