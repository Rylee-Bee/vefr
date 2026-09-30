# Journey: Explore the dark without walking every tile

**Persona:** A player who has just stepped into Emberfield's dark town, and who does not want to tap an arrow for every unseen square.
**Job:** As a player standing in a dark region, I want the game to walk me to the ground I have not seen yet so that I can uncover the map without pressing a key for every step.

1. I arrive in a region that is dark except for the circle of light I carry.
2. I find a control that explores for me, and its name tells me what it does.
3. I turn it on, watch the light move through the black, and turn it off when I want the wheel back.
4. When a monster steps into the light, or there is nothing left to see, the game stops and tells me why.

# Acceptance: autoexplore in the fog region of the sample world

Against the woven sample world loaded at the fog region - Emberfield's town, whose
`acts/act-1/town/contract.json` declares `"fog": {"radius": 4}`. Serve the woven file and
point the driver at `http://127.0.0.1:PORT/<woven-file>.html`; the UAT driver's raw findings
are the evidence, and the driver itself issues no verdict.

| triple |
| --- |
| the Explore control is on screen / load the page / visible: #explore |
| the Explore control is named / load the page / contains text: Explore |
| the Explore control is reachable from the keyboard / press Tab to focus the Explore control / focus is on: #explore |
| the status line appears while walking / press "O" / visible: #explore-status |
| the walk announces itself once / press "O" / contains text: Exploring... |
| the control shows it is on while walking / press "O" / value equals: aria-pressed="true" |
| the walk hands control back when the dark is gone / press "O" then wait for the walk to end / contains text: Nothing left to explore here. |
| a second press stops the walk / click "Explore" then click "Explore" again / contains text: Stopped. |
| the page carries no critical accessibility faults / load the page / axe has 0 critical |
| the Display switch is reachable / click "Display" / visible: #fog-toggle |
| the dark can be turned off for the player / click "Darkness: on" / value equals: aria-pressed="false" |
| turning the dark off is announced / click "Darkness: on" / contains text: Darkness off. |
