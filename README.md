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

### CSV files (in `csv_files/`)

All files are headerless CSVs.

* **`price_proj.csv`** (required) — the full player pool: `player,pos,price,points`
  (`price` is the projected auction price, `points` the projected season points).
  This is the data the optimizer solves over.
* **`keepers.csv`** (optional) — pre-drafted keepers to apply before the live draft
  starts: `player,price,team`. `team` must be exactly `Evan` for a row to count as
  *your* keeper (budget/roster slot deducted, points credited); any other value is
  treated as an opponent's keeper (player just removed from the pool). That name is
  hardcoded in `ff.py`'s `process_keepers` — edit it there if you're running this
  under a different name.
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
