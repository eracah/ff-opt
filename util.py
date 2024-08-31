from swiglpk import *
import numpy as np
def run_opt(row_dict, df):
    prices = np.asarray(df.price, dtype=np.float64)
    players = np.asarray(df.player)
    points = np.asarray(df.points)
    positions = np.asarray(df.pos)
    num_players = players.shape[0]
    num_rows = len(row_dict.keys())
    mip = glp_create_prob()  # create problem instance
    glp_set_prob_name(mip, "ffopt")  # set nmame
    glp_set_obj_dir(mip, GLP_MAX)  # set to maximize

    glp_add_rows(mip, num_rows)  # add three rows

    # add three rows named p, q, and r and make them the dot product of the column soln times the row p to be between 0 and 100, etc.''

    for idx, name in enumerate(row_dict.keys()):
        glp_set_row_name(mip, idx + 1, name)
        glp_set_row_bnds(mip, idx + 1, GLP_UP, 0, row_dict[name])
    # glp_set_row_name(mip, 2, "q")
    # glp_set_row_bnds(mip, 2, GLP_UP, 0.0, 600.0)
    # glp_set_row_name(mip, 3, "r")
    # glp_set_row_bnds(mip, 3, GLP_UP, 0.0, 300.0)

    # add num_players columns (the variables we solve for)
    glp_add_cols(mip, num_players)

    # for each plater set the variable to binary and set the obj fxn coefficient to the points
    for idx in range(num_players):
        glp_set_col_name(mip, idx + 1, players[idx])
        glp_set_col_kind(mip, idx + 1, GLP_BV)
        glp_set_obj_coef(mip, idx + 1, points[idx])

    ia = intArray(num_players * num_rows + 1)
    ja = intArray(num_players * num_rows + 1)
    ar = doubleArray(num_players * num_rows + 1)

    counter = 1
    for row_idx, row in enumerate(row_dict.keys()):

        if row == 'Budget':
            for col in range(num_players):
                ia[counter] = row_idx + 1
                ja[counter] = col + 1
                ar[counter] = prices[col]
                counter += 1

        elif row == 'Tot':
            for col in range(num_players):
                ia[counter] = row_idx + 1
                ja[counter] = col + 1
                ar[counter] = 1.0
                counter += 1

        else:
            for col in range(num_players):
                ia[counter] = row_idx + 1
                ja[counter] = col + 1
                ar[counter] = 0.0 if positions[col] != row else 1.0
                counter += 1

    # setup matrix
    glp_load_matrix(mip, num_rows * num_players, ia, ja, ar)
    parm = glp_iocp()
    parm.presolve = GLP_ON
    parm.msg_lev = GLP_MSG_OFF
    parm.br_tech = GLP_BR_DTH
    parm.bt_tech = GLP_BT_BLB
    parm.pp_tech = GLP_PP_ALL
    parm.fp_heur = GLP_OFF
    parm.gmi_cuts = GLP_OFF
    parm.mir_cuts = GLP_OFF
    parm.cov_cuts = GLP_OFF
    parm.clq_cuts = GLP_OFF
    parm.tol_parm = 1e-5
    parm.tol_obj = 1e-7
    parm.mip_gap = 0.0
    parm.tol_int = 1e-5
    parm.tm_lim = 65000
    parm.out_frq = 5000
    parm.out_dly = 10000
    parm.cb_size = 0
    parm.binarize = GLP_OFF

    glp_intopt(mip, parm)


    # get objective value
    proj_points = glp_mip_obj_val(mip)

    player_mask = np.ones((num_players,)) < 1
    # get column solutions
    for i in range(num_players):
        x = glp_mip_col_val(mip, i + 1)
        if x >= 1:
            player_mask[i] = True
    return proj_points, player_mask