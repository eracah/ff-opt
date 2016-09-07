__author__ = 'racah'
from swiglpk import *
import numpy as np
import pandas as pd
import copy
# todo: make way to reconstruct data if fails (save intermediate results)
#write code to simulate best bench
#write code to add certain draft picks to your bench

class ff_opt(object):
    def __init__(self, row_dict={'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'K': 1, 'Budget': 165, 'Tot': 8},
                 filename='data.csv', df=None):
        if not df:
            self.df = pd.read_csv('data.csv')
        else:
            self.df = df
        self.df = self.df[self.df.risk != 'High']
        self.row_dict = row_dict
        self.original_df = self.df
        self.my_points = 0


    def i_got(self, player_name, what_i_paid):
        df_mask = self.df.player == player_name
        if not any(df_mask):
            print "That player ain't even an option"
            return
        else:
            player = self.df[df_mask]

        #subtract from your budget
        budget = self.row_dict['Budget']
        if budget >= what_i_paid:
            self.row_dict['Budget'] -= what_i_paid
        else:
            print "you would be out of budget dood!"
            print "current budget: ", budget
            return

        tot = self.row_dict['Tot']
        if tot > 0:
            self.row_dict['Tot'] -= 1

        #subtract from number of positions
        pos = player.pos.values[0]
        num_pos = self.row_dict[pos]
        if num_pos > 0:
            self.row_dict[pos] -= 1

        self.my_points += player.points.values[0]

        #remove player
        self.df = self.df[self.df.player != player_name]

        self.run_opt()

    def they_got(self, player_name):
        self.df = self.df[self.df.player != player_name]

        self.run_opt()

    def what_if_they_got(self, player_name):
        temp_df = self.df[self.df.player != player_name]

        self.run_opt(df=temp_df)

    def what_if_i_got(self, player_name, what_i_paid):
        temp_row_dict = copy.deepcopy(self.row_dict)
        temp_df = copy.deepcopy(self.df)
        temp_my_points = copy.deepcopy(self.my_points)

        df_mask = self.df.player == player_name
        if not any(df_mask):
            print "That player ain't even an option"
            return
        else:
            player = self.df[df_mask]


        #subtract from your budget
        budget = temp_row_dict['Budget']
        if budget >= what_i_paid:
            temp_row_dict['Budget'] -= what_i_paid
        else:
            print "you would be out of budget dood!"
            print "current budget: ", budget
            return

        tot = temp_row_dict['Tot']
        if tot > 0:
            temp_row_dict['Tot'] -= 1

        #subtract from number of positions
        pos = player.pos.values[0]
        num_pos = temp_row_dict[pos]
        if num_pos > 0:
            temp_row_dict[pos] -= 1

        temp_my_points += player.points.values[0]

        #remove player
        temp_df = temp_df[temp_df.player != player_name]

        self.run_opt(df=temp_df, row_dict=temp_row_dict, my_points=temp_my_points)


    def run_opt(self, df=None, row_dict=None, my_points=None):
        pos_list = ['QB', 'RB', 'TE', 'WR', 'K']
        if not isinstance(df, pd.core.frame.DataFrame):
            df = self.df
        if not row_dict:
            row_dict = self.row_dict
        if not my_points:
            my_points = self.my_points

        prices = np.asarray(df.price, dtype=np.float64)
        players = np.asarray(df.player)
        points = np.asarray(df.points)
        firefactors = np.asarray(df.firefactor)
        positions = np.asarray(df.pos)
        num_players = players.shape[0]
        num_rows = len(row_dict.keys())
        mip = glp_create_prob();  #create problem instance
        glp_set_prob_name(mip, "ffopt");  # set nmame
        glp_set_obj_dir(mip, GLP_MAX);  #set to maximize

        glp_add_rows(mip, num_rows);  #add three rows



        #add three rows named p, q, and r and make them the dot product of the column soln times the row p to be between 0 and 100, etc.''

        for idx, name in enumerate(row_dict.keys()):
            glp_set_row_name(mip, idx + 1, name);
            glp_set_row_bnds(mip, idx + 1, GLP_UP, 0, row_dict[name]);
        # glp_set_row_name(mip, 2, "q");
        # glp_set_row_bnds(mip, 2, GLP_UP, 0.0, 600.0);
        # glp_set_row_name(mip, 3, "r");
        # glp_set_row_bnds(mip, 3, GLP_UP, 0.0, 300.0);

        #add num_players columns (the variables we solve for)
        glp_add_cols(mip, num_players);

        #for each plater set the variable to binary and set the obj fxn coefficient to the points
        for idx in range(num_players):
            glp_set_col_name(mip, idx + 1, players[idx]);
            glp_set_col_kind(mip, idx + 1, GLP_BV)
            glp_set_obj_coef(mip, idx + 1, points[idx]);

        ia = intArray(num_players * num_rows + 1);
        ja = intArray(num_players * num_rows + 1);
        ar = doubleArray(num_players * num_rows + 1);

        counter = 1
        for row_idx, row in enumerate(row_dict.keys()):


            if row == 'Budget':
                for col in range(num_players):
                    ia[counter] = row_idx + 1;
                    ja[counter] = col + 1;
                    ar[counter] = prices[col];
                    counter += 1

            elif row == 'Tot':
                for col in range(num_players):
                    ia[counter] = row_idx + 1;
                    ja[counter] = col + 1;
                    ar[counter] = 1.0;
                    counter += 1

            else:
                for col in range(num_players):
                    ia[counter] = row_idx + 1;
                    ja[counter] = col + 1;
                    ar[counter] = 0.0 if positions[col] != row else 1.0
                    counter += 1




        #setup matrix
        glp_load_matrix(mip, num_rows * num_players, ia, ja, ar);
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
        #run simplex
        # glp_simplex(mip, None);

        #get objective value
        Z = glp_mip_obj_val(mip);

        player_mask = np.ones((num_players,)) < 1
        #get column solutions
        for i in range(num_players):
            x = glp_mip_col_val(mip, i + 1);
            if not x < 1:
                player_mask[i] = True

        print my_points
        print Z
        for pos in pos_list:
            temp_mask = positions[player_mask] == pos
            athletes = zip(players[player_mask][temp_mask], prices[player_mask][temp_mask])
            for ath in athletes:
                pl, price = ath
                print pos + ': ', pl, '$' + str(int(price))

        print my_points + Z
        glp_delete_prob(mip);


def get_best_bench():
    row_dict = {'QB': 2, 'RB': 3, 'WR': 3, 'TE': 1, 'K': 1, 'Budget': 40.0, 'Tot': 6}
    f = ff_opt(row_dict=row_dict)

#loop thru and say they_got the 10 best qb's, the 20 best rb's



if __name__ == "__main__":
    pass
# ff = ff_opt()
# ff.they_got('jamaal charles')
# ff.i_got("le'veon bell", 50)

