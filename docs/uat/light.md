# Journey: Carry a light into the dark

**Persona:** A player who has stepped into Emberfield's dark town and found a
torch and a chalked map, and who wants to widen the little circle they can see
without turning the dark off entirely.
**Job:** As a player standing in a dark region, I want the things I carry to
push back the dark - a torch for a while, a map for good - so that exploring is
a choice about light, not only about walking.

1. I arrive in a region that is dark except for the circle of light I carry.
2. I find a torch, and a map already chalked with every street, in a container.
3. I open my Bag and use the torch; the lit circle grows, and a small count of
   its remaining turns appears while it burns.
4. When I use the map instead, the whole place is laid out at once.
5. If I have already turned the dark off, using a light tells me there is
   nothing to light, and keeps the thing.

# Acceptance: light in the fog region of the sample world

Against the woven sample world loaded at the fog region - Emberfield's town,
whose `acts/act-1/town/contract.json` declares `"fog": {"radius": 4}`. The
torch and the chalked map lie in the satchel chest at `[4, 7]` (walk down the
path to `[3, 7]`, then right). Serve the woven file and point the driver at
`http://127.0.0.1:PORT/<woven-file>.html`; the UAT driver's raw findings are
the evidence, and the driver itself issues no verdict.

| triple |
| --- |
| the chest can be opened / walk to [4, 7] and use the satchel / contains text: You take a pitch torch, a chalked map from the chest. |
| a carried torch has a Use control / open the Bag after taking the torch / visible: #bag-list button[data-item="torch"] |
| the light is usable / open the Bag and click the torch's Use control / contains text: The torch catches: 2 wider for 6 turns. |
| the light announces itself once / open the Bag and click the torch's Use control / contains text: The torch catches: |
| the counter appears while burning / open the Bag and click the torch's Use control / visible: #light-live |
| the counter shows the turns remaining / open the Bag and click the torch's Use control / contains text: Turns of light: 6 |
| the whole place can be laid out at once / open the Bag and click the chalked map's Use control / contains text: The whole place is laid out. |
| a light with nowhere to shine is refused / turn the dark off, then use a torch / contains text: There is no dark here to light. |
| the light burns down and dies / use a torch, then take six steps / contains text: The light gutters out. |
| the page carries no critical accessibility faults / load the page / axe has 0 critical |
