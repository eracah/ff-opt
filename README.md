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
Set your roster size and budget in the sidebar and click **Start Draft**, then log
picks as they happen — the optimal remaining lineup, max bid per player, and
score-dropoff-if-outbid all recompute live.

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

None of these are committed to git — see `.gitignore`.
