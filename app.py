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
    rows = []
    for pl, price, pos in aths:
        diff = ff.pplim(pl, price, quiet=True)
        max_price = ff.m(pl)
        rows.append({
            "pos": pos, "player": pl,
            "price": f"${int(price)}", "max_price": f"${int(max_price)}",
            "score_dropoff": round(diff, 2),
        })
    return pd.DataFrame(rows), proj_points, my_total_points


def max_prices_df(ff, pos=None):
    aths, _, _ = ff._run_opt()
    opt_players = {a[0] for a in aths}
    df = ff.df if pos is None else ff.df[ff.df.pos == pos]
    df_view = df[df.price > 0].drop(labels=["points", "pos"], axis=1).copy()
    df_view["max_price"] = [
        (ff.m(p) if p in opt_players else ff.mn(p)) for p in df_view.player
    ]
    df_view = df_view[df_view.max_price > 0]
    return df_view.sort_values("max_price", ascending=False).reset_index(drop=True)


# ---------- session lifecycle ----------

def start_draft(setup):
    ff = ff_opt(**setup)
    st.session_state.ff = ff
    st.session_state.setup = setup
    st.session_state.log = []


def record_action(kind, player, price=None):
    st.session_state.log.append({"type": kind, "player": player, "price": price})


def undo_last():
    setup = st.session_state.setup
    log = st.session_state.log[:-1]
    ff = ff_opt(**setup)
    for action in log:
        if action["type"] == "i_got":
            ff.i_got(action["player"], action["price"], quiet=True, write=False)
        else:
            ff.they_got(action["player"], quiet=True, write=False)
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

    tab_board, tab_max, tab_whatif, tab_log = st.tabs(
        ["Draft Board", "Max Prices", "What If", "Picks Log"])

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
                        st.rerun()

            with st.form("they_got_form", clear_on_submit=True):
                st.markdown("**They got them**")
                p2 = st.selectbox("Player", available_players, key="they_got_player")
                if st.form_submit_button("They got them"):
                    ff.they_got(p2, quiet=True, write=True)
                    record_action("they_got", p2)
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
                st.dataframe(pd.read_csv("csv_files/their_team.csv",
                                          names=["player"]),
                             hide_index=True, use_container_width=True)
            except (FileNotFoundError, pd.errors.EmptyDataError):
                st.write("No picks yet.")
