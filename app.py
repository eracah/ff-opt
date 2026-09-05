"""
Streamlit GUI for ff_opt — run with:
    streamlit run app.py
"""
import pandas as pd
import streamlit as st

from ff import ff_opt

st.set_page_config(page_title="FF Auction Draft Optimizer", layout="wide")

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]


# ---------- helpers that turn ff_opt's print-only methods into DataFrames ----------

def lineup_df(ff):
    aths, proj_points, my_total_points = ff._run_opt()
    orig = original_prices()
    rows = []
    for pl, price, pos in aths:
        diff = ff.pplim(pl, price, quiet=True)
        max_price = ff.m(pl)
        rows.append({
            "pos": pos, "player": pl,
            "proj_price": f"${int(orig.get(pl, price))}",
            "adj_price": f"${int(price)}", "max_price": f"${int(max_price)}",
            "score_dropoff": round(diff, 2),
        })
    return pd.DataFrame(rows), proj_points, my_total_points


def owner_names():
    try:
        with open("csv_files/owners.csv") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def record_team_owner(player, team, price):
    with open("csv_files/their_team_owners.csv", "a+") as f:
        f.write(f"{player},{team},{price}\n")


def team_owners_df():
    try:
        return pd.read_csv("csv_files/their_team_owners.csv",
                            names=["player", "team", "price"])
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=["player", "team", "price"])


def _read_csv_safe(path, names):
    try:
        return pd.read_csv(path, names=names)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=names)


def league_df():
    """Every drafted player (keepers + live picks, mine and everyone else's)
    joined back against price_proj.csv for position/points, since a player is
    removed from ff.df once anyone drafts them."""
    keepers = _read_csv_safe("csv_files/keepers.csv", ["player", "price", "team"])
    mine = _read_csv_safe("csv_files/my_team.csv", ["player", "price"])
    mine["team"] = "Evan"
    theirs = team_owners_df()

    picks = pd.concat(
        [keepers[["player", "price", "team"]], mine, theirs[["player", "price", "team"]]],
        ignore_index=True)

    proj = pd.read_csv("csv_files/price_proj.csv",
                        names=["player", "pos", "price", "points"],
                        usecols=["player", "pos", "points"])
    return picks.merge(proj, on="player", how="left")


def team_summary_df(league, starting_budget):
    summary = league.groupby("team").agg(
        players=("player", "count"),
        spent=("price", "sum"),
        points=("points", "sum"),
    ).reset_index()
    summary["budget_left"] = starting_budget - summary["spent"]
    return summary.sort_values("points", ascending=False).reset_index(drop=True)


def display_team_name(team):
    return "Me (Evan)" if team == "Evan" else team


def original_prices():
    """Static pre-draft price_proj.csv prices, indexed by player — the baseline
    that market-inflation adjustments are always computed from, so repeated
    adjustments never compound."""
    proj = pd.read_csv("csv_files/price_proj.csv",
                        names=["player", "pos", "price", "points"],
                        usecols=["player", "price"])
    return proj.set_index("player")["price"]


def compute_inflation(ff, starting_budget):
    """Ratio of real dollars left in the league to the projected cost of what's
    left in the pool. Damped by how much of the league's total budget has
    actually been spent so far, so one early over/under-pay doesn't swing it."""
    num_teams = len(owner_names()) + 1  # + Evan
    total_league_budget = starting_budget * num_teams
    total_spent = league_df()["price"].sum()
    if total_league_budget <= 0:
        return 1.0
    orig = original_prices()
    total_undrafted_price = orig.reindex(ff.df.player).sum()
    if total_undrafted_price <= 0:
        return 1.0
    raw_multiplier = (total_league_budget - total_spent) / total_undrafted_price
    confidence = min(1.0, max(0.0, total_spent / total_league_budget))
    return 1 + (raw_multiplier - 1) * confidence


def refresh_prices(ff, starting_budget):
    """Rewrite ff.df's price column (used by the optimizer's budget constraint
    and by every price shown for undrafted players) to the current
    inflation-adjusted estimate. Call after anything that changes who's
    drafted or how much money has moved."""
    multiplier = compute_inflation(ff, starting_budget)
    orig = original_prices()
    ff.df = ff.df.copy()
    ff.df["price"] = (ff.df["player"].map(orig) * multiplier).round().clip(lower=0)
    st.session_state.inflation = multiplier
    return multiplier


def max_prices_df(ff, pos=None):
    aths, _, _ = ff._run_opt()
    opt_players = {a[0] for a in aths}
    df = ff.df if pos is None else ff.df[ff.df.pos == pos]
    df_view = df[df.price > 0].drop(labels=["points", "pos"], axis=1).copy()
    orig = original_prices()
    df_view.insert(1, "proj_price", df_view["player"].map(orig))
    df_view = df_view.rename(columns={"price": "adj_price"})
    df_view["max_price"] = [
        (ff.m(p) if p in opt_players else ff.mn(p)) for p in df_view.player
    ]
    df_view = df_view[df_view.max_price > 0]
    return df_view.sort_values("max_price", ascending=False).reset_index(drop=True)


# ---------- session lifecycle ----------

def start_draft(setup):
    ff = ff_opt(**setup)
    refresh_prices(ff, setup["Budget"])
    st.session_state.ff = ff
    st.session_state.setup = setup
    st.session_state.log = []


def record_action(kind, player, price=None, team=None):
    st.session_state.log.append(
        {"type": kind, "player": player, "price": price, "team": team})


def undo_last():
    setup = st.session_state.setup
    log = st.session_state.log[:-1]
    ff = ff_opt(**setup)
    for action in log:
        if action["type"] == "i_got":
            ff.i_got(action["player"], action["price"], quiet=True, write=False)
        else:
            ff.they_got(action["player"], quiet=True, write=False)
    refresh_prices(ff, setup["Budget"])
    st.session_state.ff = ff
    st.session_state.log = log


if "ff" not in st.session_state:
    st.session_state.ff = None
    st.session_state.log = []


# ---------- sidebar: setup / status ----------

with st.sidebar:
    st.title("Draft Setup")

    if st.session_state.ff is None:
        with st.form("setup_form"):
            qb = st.number_input("QB", 0, 5, 1)
            rb = st.number_input("RB", 0, 8, 3)
            wr = st.number_input("WR", 0, 8, 3)
            te = st.number_input("TE", 0, 5, 1)
            dst = st.number_input("DST", 0, 3, 1)
            budget = st.number_input("Budget", 1, 1000, 189)
            process_keepers = st.checkbox(
                "Process keepers (csv_files/keepers.csv)", value=True)
            restore = st.checkbox(
                "Resume from saved picks (csv_files/my_team.csv / their_team.csv)",
                value=True)
            submitted = st.form_submit_button("Start Draft", type="primary")
        if submitted:
            setup = dict(QB=qb, RB=rb, WR=wr, TE=te, DST=dst, Budget=budget,
                         process_keepers=process_keepers, restore=restore)
            try:
                start_draft(setup)
            except Exception as e:
                st.error(f"Couldn't start draft: {e}")
            else:
                st.rerun()
    else:
        ff = st.session_state.ff
        rd = ff.row_dict
        st.metric("Budget left", f"${rd['Budget']}")
        st.metric("Slots left", rd["Tot"])
        cols = st.columns(5)
        for c, pos in zip(cols, POSITIONS):
            c.metric(pos, rd[pos])
        st.metric("Locked-in points", f"{ff.my_points:.1f}")
        infl = st.session_state.get("inflation", 1.0)
        st.metric("Market inflation", f"{infl:.2f}x", f"{(infl - 1) * 100:+.0f}%")
        st.caption(
            "Damped by how much of the league's budget has actually been "
            "spent — stays near 1.0x early in the draft.")

        st.divider()
        st.caption(
            "Undo reverts this session's view only — picks already written "
            "to the CSV log files are not erased.")
        if st.button("Undo last pick", disabled=not st.session_state.log,
                      use_container_width=True):
            undo_last()
            st.rerun()
        if st.button("Reset draft", use_container_width=True):
            st.session_state.ff = None
            st.session_state.log = []
            st.rerun()


# ---------- main area ----------

if st.session_state.ff is None:
    st.title("FF Auction Draft Optimizer")
    st.write("Configure your roster and budget in the sidebar, then click **Start Draft**.")
else:
    ff = st.session_state.ff
    st.title("FF Auction Draft Optimizer")

    tab_nominate, tab_board, tab_max, tab_whatif, tab_league, tab_log = st.tabs(
        ["Nominate", "Draft Board", "Max Prices", "What If", "League", "Picks Log"])

    # --- Nominate ---
    with tab_nominate:
        st.subheader("Player currently up for bid")
        nominee_players = sorted(ff.df.player.tolist())
        nominee = st.selectbox("Nominated player", nominee_players, key="nominee")

        if nominee:
            orig = original_prices()
            raw_price = orig.get(nominee)
            adj_price = ff.df.loc[ff.df.player == nominee, "price"].iloc[0]
            c0a, c0b = st.columns(2)
            c0a.metric("Projected price",
                       f"${int(raw_price)}" if raw_price is not None else "—")
            c0b.metric("Market-adjusted price", f"${int(adj_price)}")

            with st.spinner("Solving..."):
                aths, _, _ = ff._run_opt()
                in_lineup = nominee in {a[0] for a in aths}
                if in_lineup:
                    guidance_price = ff.m(nominee)
                    st.metric("Max you could pay and stay optimal", f"${guidance_price}")
                else:
                    guidance_price = ff.mn(nominee)
                    st.metric("Not worth it above this price", f"${guidance_price}")

            st.divider()
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**I got them**")
                with st.form("nominate_i_got_form"):
                    price1 = st.number_input("Price paid", 0, 1000, 1,
                                              key="nominate_i_got_price")
                    if st.form_submit_button("I got them"):
                        if price1 > ff.row_dict["Budget"]:
                            st.error(
                                f"Not enough budget: ${price1} paid but only "
                                f"${ff.row_dict['Budget']} left.")
                        else:
                            ff.i_got(nominee, price1, quiet=True, write=True)
                            record_action("i_got", nominee, price1)
                            refresh_prices(ff, st.session_state.setup["Budget"])
                            del st.session_state["nominee"]
                            st.rerun()

            with col2:
                st.markdown("**They got them**")
                with st.form("nominate_they_got_form"):
                    owners = owner_names()
                    if owners:
                        team2 = st.selectbox("Team", owners, key="nominate_they_got_team")
                    else:
                        team2 = st.text_input(
                            "Team (csv_files/owners.csv not found or empty)",
                            key="nominate_they_got_team_text")
                    price2 = st.number_input("Price paid", 0, 1000, 1,
                                              key="nominate_they_got_price")
                    if st.form_submit_button("They got them"):
                        if not team2:
                            st.error("Pick which team got this player.")
                        else:
                            ff.they_got(nominee, quiet=True, write=True)
                            record_team_owner(nominee, team2, price2)
                            record_action("they_got", nominee, price=price2, team=team2)
                            refresh_prices(ff, st.session_state.setup["Budget"])
                            del st.session_state["nominee"]
                            st.rerun()

    # --- Draft Board ---
    with tab_board:
        left, right = st.columns([2, 1])

        with left:
            st.subheader("Current optimal lineup")
            df, proj_points, my_total_points = lineup_df(ff)
            if df.empty:
                st.info("No players left to draft — roster is full or pool is empty.")
            else:
                st.dataframe(df, hide_index=True, use_container_width=True)
            m1, m2 = st.columns(2)
            m1.metric("Points if this lineup drafts as shown", f"{proj_points:.1f}")
            m2.metric("My total projected points", f"{my_total_points:.1f}")

        with right:
            st.subheader("Record a pick")
            available_players = sorted(ff.df.player.tolist())

            with st.form("i_got_form", clear_on_submit=True):
                st.markdown("**I got them**")
                p1 = st.selectbox("Player", available_players, key="i_got_player")
                price1 = st.number_input("Price paid", 0, 1000, 1, key="i_got_price")
                if st.form_submit_button("I got them"):
                    if price1 > ff.row_dict["Budget"]:
                        st.error(
                            f"Not enough budget: ${price1} paid but only "
                            f"${ff.row_dict['Budget']} left.")
                    else:
                        ff.i_got(p1, price1, quiet=True, write=True)
                        record_action("i_got", p1, price1)
                        refresh_prices(ff, st.session_state.setup["Budget"])
                        st.rerun()

            with st.form("they_got_form", clear_on_submit=True):
                st.markdown("**They got them**")
                p2 = st.selectbox("Player", available_players, key="they_got_player")
                owners = owner_names()
                if owners:
                    team2 = st.selectbox("Team", owners, key="they_got_team")
                else:
                    team2 = st.text_input(
                        "Team (csv_files/owners.csv not found or empty)",
                        key="they_got_team_text")
                price2 = st.number_input("Price paid", 0, 1000, 1, key="they_got_price")
                if st.form_submit_button("They got them"):
                    if not team2:
                        st.error("Pick which team got this player.")
                    else:
                        ff.they_got(p2, quiet=True, write=True)
                        record_team_owner(p2, team2, price2)
                        record_action("they_got", p2, price=price2, team=team2)
                        refresh_prices(ff, st.session_state.setup["Budget"])
                        st.rerun()

    # --- Max Prices ---
    with tab_max:
        st.subheader("Max price you could pay and still hit the optimal lineup")
        st.caption(
            "Recomputes across the full remaining player pool — can take a few "
            "seconds early in the draft. Click to refresh.")
        pos_choice = st.selectbox("Position", ["All"] + POSITIONS, key="max_pos")
        if st.button("Compute max prices"):
            pos = None if pos_choice == "All" else pos_choice
            with st.spinner("Solving..."):
                st.session_state.max_prices_result = max_prices_df(ff, pos)
        if "max_prices_result" in st.session_state:
            st.dataframe(st.session_state.max_prices_result, hide_index=True,
                         use_container_width=True)

    # --- What If ---
    with tab_whatif:
        st.subheader("What if...")
        available_players = sorted(ff.df.player.tolist())
        wp = st.selectbox("Player", available_players, key="whatif_player")
        wprice = st.number_input("Hypothetical price", 0, 1000, 1, key="whatif_price")
        if st.button("Evaluate"):
            with st.spinner("Solving..."):
                got_pts = ff.what_if_i_got(wp, wprice, quiet=True)
                miss_pts = ff.what_if_they_got(wp, quiet=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("If I got them", f"{got_pts:.1f} pts")
            c2.metric("If they got them", f"{miss_pts:.1f} pts")
            c3.metric("Points at risk", f"{got_pts - miss_pts:.1f} pts")

    # --- League ---
    with tab_league:
        st.subheader("Every team's roster, spend, and projected points")
        starting_budget = st.session_state.setup["Budget"]
        st.caption(
            f"Assumes every team drafts with the same ${starting_budget} budget "
            "you configured at setup.")
        league = league_df()
        if league.empty:
            st.info("No picks recorded yet.")
        else:
            summary = team_summary_df(league, starting_budget)
            overview = summary.copy()
            overview["team"] = overview["team"].apply(display_team_name)
            st.dataframe(
                overview[["team", "players", "points", "spent", "budget_left"]],
                hide_index=True, use_container_width=True)

            st.divider()
            ordered_teams = summary["team"].tolist()  # already sorted by points desc
            cols_per_row = 3
            for i in range(0, len(ordered_teams), cols_per_row):
                row_teams = ordered_teams[i:i + cols_per_row]
                cols = st.columns(len(row_teams))
                for col, team in zip(cols, row_teams):
                    with col:
                        row = summary[summary.team == team].iloc[0]
                        st.markdown(f"**{display_team_name(team)}**")
                        st.caption(
                            f"{row.points:.1f} pts · ${int(row.spent)} spent · "
                            f"${int(row.budget_left)} left")
                        roster = league[league.team == team][
                            ["player", "pos", "price", "points"]].sort_values("pos")
                        st.dataframe(roster, hide_index=True,
                                     use_container_width=True, height=250)

    # --- Picks Log ---
    with tab_log:
        st.subheader("Persisted picks (csv_files/*.csv)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**My team**")
            try:
                st.dataframe(pd.read_csv("csv_files/my_team.csv",
                                          names=["player", "price"]),
                             hide_index=True, use_container_width=True)
            except (FileNotFoundError, pd.errors.EmptyDataError):
                st.write("No picks yet.")
        with c2:
            st.markdown("**Their team**")
            try:
                their = pd.read_csv("csv_files/their_team.csv", names=["player"])
            except (FileNotFoundError, pd.errors.EmptyDataError):
                their = pd.DataFrame(columns=["player"])
            if their.empty:
                st.write("No picks yet.")
            else:
                st.dataframe(their.merge(team_owners_df(), on="player", how="left"),
                             hide_index=True, use_container_width=True)
