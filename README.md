# ff-opt
Computing the Optimal Fantasy Lineup in Auction Drafts using 0-1 Integer Linear Programming

### Pre-reqs
```
pip install -r requirements.txt
```
(`numpy`, `pandas`, `swiglpk` (https://pypi.python.org/pypi/swiglpk), `streamlit`)

### Running the GUI

```
streamlit run app.py
```

Run this from the repo root, since it reads/writes `csv_files/` using relative paths.
Set your starter counts, bench counts, and budget in the sidebar and click
**Start Draft**. Unlike `ff.py`'s notebook workflow — which optimizes starters first
and only figures out the bench afterward via a separate `bench_opt()` call — the GUI
solves for your whole roster (starters + bench) in one continuous optimization from
the start, so the optimizer reserves realistic budget for bench depth throughout the
draft instead of bolting it on at the end. The Draft Board splits the recommended
roster into Starter/Bench by ranking each position's players by points — that
split is a display label only, since the optimizer itself doesn't tag slot roles.
Log picks as they happen — the recommended roster, max bid per player, and
score-dropoff-if-outbid all recompute live. The **League** tab tracks every team's
roster, spend, and projected points the same way, assuming everyone drafts with the
budget you configured.

The sidebar also shows a live **market inflation** multiplier: real dollars left in
the league (assuming everyone has the same budget) divided by the projected cost of
what's left in the pool. It's damped by how much of the league's total budget has
actually been spent, so it stays near 1.0x early in the draft and only fully kicks in
once there's enough real pricing data to trust. This multiplier is what the optimizer
actually uses for its budget constraint and max/min-price guidance — the `proj_price`
column (from `price_proj.csv`) is shown alongside `adj_price` wherever both are
relevant, so you can see the pre-draft estimate and the live-adjusted number
together.

### Modes

The sidebar's **Mode** switch picks between:

* **Live Draft** — the auction-day tool described above. `price_proj.csv` can be
  either the plain headerless format or the headered/`$`-prefixed format (pandas'
  header inference and `$`-stripping handle both transparently) — just make sure
  every row has a `points` value, since a blank one used to crash the solver
  outright (fixed by zero-filling on load, but still worth keeping data clean).
  `process_keepers` now reads `keepers.csv` as the same full per-team roster dump
  the Keeper Simulator uses (see below) and applies the same top-3-by-keeper-value
  rule to decide who's actually kept, for every team including yours — override
  any pick you disagree with afterward via `i_got`/`they_got` in the GUI.
* **Keeper Simulator** — a standalone, pre-draft what-if tool (see below). Doesn't
  touch live draft state.

### Keeper Simulator

A pre-draft tool to answer two questions: what will opponents likely keep, and are
your own keeper prices actually worth it? It doesn't touch any live draft state
(`my_team.csv`, `their_team.csv`, etc.) — it's a sandboxed simulation.

1. **Predicts opponent keepers**: for every team but you, it keeps up to 3 players
   (your league's keeper cap) — whichever have the best keeper value (`ESPN Price -
   2027 Keeper Cost`), among those where that value is non-negative — and removes
   them from the simulated pool.
2. **Tests your own keepers**: shows all of your rostered players in an editable
   table (defaulting to each one's `2027 Keeper Cost`, which you can override) and
   runs the same combined starters+bench optimizer used in Live Draft, from an empty
   roster, over the full 2027 pool minus the predicted opponent keepers. Whichever of
   your candidates the optimizer actually selects — at the price you tested — are
   worth keeping at that price; if more than 3 clear the bar, pick your best 3.

It reads `csv_files/keepers.csv` as a full per-team roster dump (not just decided
keepers) with columns `Fantasy Team, Player, Position, ESPN Price, Actual Paid,
2027 Keeper Cost, Keeper Value, Savings` (a header row, `$`-prefixed dollar amounts,
blank separator rows between teams — all handled automatically), and
`csv_files/price_proj.csv` as `Player Name, Position, Average Value, Projection`
(also headered/`$`-prefixed). Note: this price_proj.csv format currently has no DST
rows, so the simulator can't recommend a defense.

### CSV files used by Live Draft (in `csv_files/`)

* **`price_proj.csv`** (required) — the full player pool: `player,pos,price,points`,
  headerless or headered/`$`-prefixed (both work). `price` is the projected auction
  price, `points` the projected season points — this is what the optimizer solves
  over.
* **`keepers.csv`** (optional) — a full per-team roster dump with keeper economics
  already computed: `Fantasy Team, Player, Position, ESPN Price, Actual Paid,
  2027 Keeper Cost, Keeper Value, Savings` (header row, `$`-prefixed, blank
  separator rows between teams all handled automatically). `process_keepers` decides
  who's kept — each team's top 3 by `Keeper Value` among those non-negative — and
  applies it before the live draft starts, using `2027 Keeper Cost` as the price
  paid. `Fantasy Team` must read exactly `Evan` for a row to count as *your* roster;
  that name is hardcoded in `ff.py` — edit it there if you're running this under a
  different name. `csv_files/keeper_sim.csv`, if `ff.py`'s `_set_up` is pointed at
  it instead of `price_proj.csv`, is a plain headerless `player,pos,price,points`
  snapshot of one specific keeper scenario (opponent keepers already removed,
  candidate players priced at keeper cost) — handy for sanity-checking one scenario
  through the normal Live Draft flow instead of the Keeper Simulator's editable UI.
* **`my_team.csv`** / **`their_team.csv`** (auto-generated) — the app appends to
  these as you record picks (`player,price` and `player` respectively), so you can
  close and reopen the app mid-draft. Check "Resume from saved picks" in the sidebar
  to reload them on startup. Delete both (or move them aside) to start a season fresh.
* **`owners.csv`** (optional) — the other teams in your league, one name per line.
  Populates the "Team" dropdown that's required whenever you record a "they got
  them" pick in the GUI.
* **`their_team_owners.csv`** (auto-generated) — `player,team,price` rows the app
  writes each time you record who got a player and what they paid, so the Picks Log
  tab can show which team has whom and for how much.

None of these are committed to git — see `.gitignore`.
