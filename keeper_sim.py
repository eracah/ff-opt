"""
2027 keeper decision simulator — standalone from the live draft app in app.py.

Reads csv_files/keepers.csv and csv_files/price_proj.csv directly in their
current raw format (header row, $-prefixed prices, spaced player names).
Doesn't touch ff.py/util.py's live-draft CSV assumptions or any live draft
state (my_team.csv, their_team.csv, etc.) — this is a pre-draft what-if tool.
"""
import re

import numpy as np
import pandas as pd
import streamlit as st

from util import run_opt

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]
MAX_KEEPERS = 3


def parse_money(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    if cleaned in ("", "-"):
        return None
    return float(cleaned)


def load_price_proj():
    df = pd.read_csv("csv_files/price_proj.csv", header=0,
                      names=["player", "pos", "price", "points"])
    df["price"] = df["price"].apply(parse_money).fillna(0)
    df["points"] = df["points"].apply(parse_money).fillna(0)
    return df


def load_keeper_sheet():
    df = pd.read_csv("csv_files/keepers.csv", header=0, usecols=[0, 1, 2, 3, 4, 5, 6, 7],
                      names=["team", "player", "pos", "espn_price", "actual_paid",
                             "keeper_cost", "keeper_value", "savings"])
    df = df.dropna(subset=["team", "player"]).reset_index(drop=True)
    for col in ["espn_price", "actual_paid", "keeper_cost", "keeper_value", "savings"]:
        df[col] = df[col].apply(parse_money)
    return df


def predict_opponent_keepers(keeper_sheet, max_keepers=MAX_KEEPERS):
    """Every opponent keeps up to max_keepers players, choosing whichever have
    the best keeper value (ESPN price - 2027 keeper cost), among those where
    that value is non-negative."""
    opponents = keeper_sheet[keeper_sheet.team != "Evan"]
    qualifying = opponents[opponents.keeper_value >= 0]
    kept = (qualifying.sort_values("keeper_value", ascending=False)
            .groupby("team", group_keys=False).head(max_keepers))
    return kept.sort_values(["team", "keeper_value"],
                             ascending=[True, False]).reset_index(drop=True)


def solve_pool(pool, row_dict):
    """Run the same 0-1 ILP the live draft app uses, directly on an in-memory
    pool — no ff_opt/file coupling, since this pool is hypothetical (opponent
    keepers removed, Evan's candidates priced at test cost)."""
    pool = pool.reset_index(drop=True)
    proj_points, mask = run_opt(row_dict, pool)
    players = np.asarray(pool.player)[mask]
    positions = np.asarray(pool.pos)[mask]
    prices = np.asarray(pool.price)[mask]
    points = np.asarray(pool.points)[mask]
    result = pd.DataFrame({"player": players, "pos": positions,
                            "price": prices, "points": points})
    return result, proj_points


def render():
    st.title("2027 Keeper Simulator")
    st.caption(
        "Standalone what-if tool — doesn't touch live draft state. Reads "
        "csv_files/keepers.csv and csv_files/price_proj.csv directly.")

    try:
        keeper_sheet = load_keeper_sheet()
    except FileNotFoundError:
        st.error("csv_files/keepers.csv not found.")
        return
    try:
        proj = load_price_proj()
    except FileNotFoundError:
        st.error("csv_files/price_proj.csv not found.")
        return

    if not (proj.pos == "DST").any():
        st.info(
            "price_proj.csv has no DST rows this year, so this sim can't "
            "recommend a defense — DST slots default to 0 below.")

    opp_keepers = predict_opponent_keepers(keeper_sheet)
    st.subheader(f"Predicted opponent keepers (top {MAX_KEEPERS} by value per team)")
    st.dataframe(
        opp_keepers[["team", "player", "pos", "keeper_cost", "keeper_value"]],
        hide_index=True, use_container_width=True)

    st.subheader("Your keeper candidates — edit test prices, then run")
    mine = keeper_sheet[keeper_sheet.team == "Evan"][
        ["player", "pos", "keeper_cost", "keeper_value"]].reset_index(drop=True)
    mine = mine.rename(columns={"keeper_cost": "test_price"})
    edited = st.data_editor(
        mine, hide_index=True, use_container_width=True,
        disabled=["player", "pos", "keeper_value"], key="keeper_editor")
    edited = edited.copy()
    edited["test_price"] = edited["test_price"].fillna(0)

    st.divider()
    st.subheader("Roster & budget for the simulated draft")
    st.caption("Starts from an empty roster — this simulates drafting from scratch.")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    qb = c1.number_input("QB", 0, 5, 1, key="ks_qb")
    rb = c2.number_input("RB", 0, 8, 3, key="ks_rb")
    wr = c3.number_input("WR", 0, 8, 3, key="ks_wr")
    te = c4.number_input("TE", 0, 5, 1, key="ks_te")
    dst = c5.number_input("DST", 0, 3, 0, key="ks_dst")
    budget = c6.number_input("Budget", 1, 1000, 189, key="ks_budget")
    c1b, c2b, c3b, c4b, c5b = st.columns(5)
    qb_b = c1b.number_input("QB bench", 0, 10, 1, key="ks_qb_b")
    rb_b = c2b.number_input("RB bench", 0, 10, 2, key="ks_rb_b")
    wr_b = c3b.number_input("WR bench", 0, 10, 2, key="ks_wr_b")
    te_b = c4b.number_input("TE bench", 0, 10, 1, key="ks_te_b")
    dst_b = c5b.number_input("DST bench", 0, 5, 0, key="ks_dst_b")

    if st.button("Run simulation", type="primary"):
        pool = proj[~proj.player.isin(opp_keepers.player)].copy()
        missing = sorted(set(edited.player) - set(pool.player))
        if missing:
            st.warning(f"Not found in price_proj.csv, skipped: {', '.join(missing)}")

        price_overrides = edited.set_index("player")["test_price"]
        pool["price"] = [
            price_overrides[p] if p in price_overrides.index else price
            for p, price in zip(pool.player, pool.price)
        ]

        row_dict = dict(QB=qb + qb_b, RB=rb + rb_b, WR=wr + wr_b,
                         TE=te + te_b, DST=dst + dst_b, Budget=budget)
        row_dict["Tot"] = sum(row_dict[p] for p in POSITIONS)
        result, proj_points = solve_pool(pool, row_dict)
        result["kept_candidate"] = result.player.isin(edited.player)
        st.session_state.ks_result = (result, proj_points)

    if "ks_result" in st.session_state:
        result, proj_points = st.session_state.ks_result
        st.metric("Optimal roster projected points", f"{proj_points:.1f}")

        kept = result[result.kept_candidate]
        st.write(f"**{len(kept)} of your candidates made the optimal roster:**")
        if kept.empty:
            st.write("None of your tested prices were worth it at this budget/roster.")
        else:
            st.dataframe(kept[["player", "pos", "price", "points"]],
                         hide_index=True, use_container_width=True)
            if len(kept) > MAX_KEEPERS:
                st.warning(
                    f"{len(kept)} clear the bar, but your league caps keepers at "
                    f"{MAX_KEEPERS} — pick your best {MAX_KEEPERS} among these "
                    "(e.g. by keeper_value in the table above).")

        st.write("**Full simulated optimal roster:**")
        st.dataframe(
            result.sort_values("pos")[["pos", "player", "price", "points", "kept_candidate"]],
            hide_index=True, use_container_width=True)
