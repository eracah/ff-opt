__author__ = 'racah'
from swiglpk import *
import numpy as np
import pandas as pd
import copy
from util import run_opt
import csv
import warnings
warnings.filterwarnings("ignore")
# todo change max I could get to some sort of
# check to see how much my proj points change as it increases in price
# todo fix bug where you call min_I_could_pay for someone whose min is current value

#write code to simulate best bench
#write code to add certain draft picks to your bench

class ff_opt(object):
    def __init__(self, QB=1, RB=3, WR=3, TE=1, DST=1, Budget=189, process_keepers=True):
        self._set_up(QB, RB, WR, TE, DST, Budget, process_keepers)

    def _set_up(self,QB=1, RB=3, WR=3, TE=1, DST=1, Budget=189, process_keepers=True):
        Tot = QB + RB + WR + TE + DST
        self.row_dict = dict(QB=QB, RB=RB, WR=WR, TE=TE,DST=DST, Budget=Budget, Tot=Tot)
        projs = pd.read_csv("csv_files/proj.csv",
                            names=["player", "points"],
                            usecols=["points", "player"])
        prices = pd.read_csv("csv_files/prices.csv",
                            names=["player", "pos", "price"])
        self.df = pd.merge(projs, prices, on="player")
        
        self.df.drop(self.df[self.df['pos'] == 'K'].index, inplace=True)
        self.my_points = 0
        self.run_opt(quiet=True)
        if process_keepers:
            self.process_keepers("csv_files/keepers.csv")


    def restore(self, my_file="csv_files/my_team.csv",
                their_file="csv_files/their_team.csv"):
        print("resoring from file...")
        try:
            with open(my_file, 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                for idx, row in enumerate(reader):
                    player, price = row
                    #player = player.lower()
                    price = int(price)
                    self.i_got(player, price, quiet=True, write=False)
        except:
            pass

        try:
            with open(their_file, 'r') as csvfile:
                reader = csv.reader(csvfile, delimiter=',')
                for idx, row in enumerate(reader):
                    player, = row
                    #player = player.lower()
                    #price = int(price)
                    self.they_got(player,write=False)
        except:
            pass

        print("After restoring the optimal lineup to draft is:")
        self.run_opt()

    def bench_opt(self, QB=3, RB=4, WR=7, TE=2, DST=0, total_budget=200, process_keepers=True):
        self._set_up(QB, RB, WR, TE, DST, Budget=total_budget, process_keepers=process_keepers)
        self.restore()

    def _run_opt(self, df=None, row_dict=None):
        df = self.df if df is None else df
        row_dict = self.row_dict if row_dict is None else row_dict
        pos_list = ['QB', 'RB', 'TE', 'WR', "DST"]
        prices = np.asarray(df.price, dtype=np.float64)
        players = np.asarray(df.player)
        positions = np.asarray(df.pos)

        proj_points, player_mask = run_opt(row_dict, df)
        aths = []
        for pos in pos_list:
            temp_mask = positions[player_mask] == pos
            athletes = zip(players[player_mask][temp_mask], prices[player_mask][temp_mask])
            for ath in athletes:
                pl, price = ath
                aths.append((pl,price, pos))    
        return aths, proj_points, self.my_points + proj_points
    
    def run_opt(self, df=None, row_dict=None, quiet=False):
        aths, proj_points, my_total_points = self._run_opt(df, row_dict)
        updated_aths = []
        if not quiet:
            for (pl,price, pos) in aths:
                diff = self.pplim(pl, price, quiet=True)
                max_price = self.m(pl)
                updated_aths.append((pos, pl, '$' + str(int(price)), '$' + str(int(max_price)), diff))
                #print(f'{pos}: {pl} ${int(price)} (${int(max_price)}) ({diff:2.2f})')
            opt_df = pd.DataFrame(dict(zip([ 'pos','player', 'price', 'max_price', 'score_dropoff'],zip(*updated_aths))))
            print(opt_df)
            print(f'\nTotal Points of this Lineup: {proj_points:.3f}')
            print(f'My Points Would Be: {my_total_points:.3f}')
            print(f'Budget: {self.row_dict["Budget"]}')
        return aths, proj_points, my_total_points
        

    def process_keepers(self, keeper_file):
        print("processing keepers...")
        with open(keeper_file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for idx, row in enumerate(reader):
                player, price, team = row
                price = int(price)
                if team == 'Evan':
                    print('\t *', player)
                    self.i_got(player, price, quiet=True, write=False)
                else:
                    self.they_got(player, quiet=True, write=False)
        print("After keepers optimal lineup to draft is:\n")
        self.run_opt()

    def get_player(self, df, player_name):
        df_mask = df.player == player_name
        if not any(df_mask):
            print("That player ain't even an option")
            return None
        else:
            player = df[df_mask]

        return player

    def i_got(self, player_name, what_i_paid, quiet=False, write=True):
        if not quiet:
            print("i got ", player_name)
        player = self.get_player(self.df, player_name)
        if player is None:
            return
        # write to csv
        if write:
            with open("csv_files/my_team.csv", "a+") as f:
                f.write(f"{player_name},{what_i_paid}\n")
        # subtract from your budget
        budget = self.row_dict['Budget']
        if budget >= what_i_paid:
            self.row_dict['Budget'] -= what_i_paid
        else:
            print("you would be out of budget dood!")
            print("current budget: ", budget)
            return

        tot = self.row_dict['Tot']
        if tot > 0:
            self.row_dict['Tot'] -= 1

        # subtract from number of positions
        pos = player.pos.values[0]
        num_pos = self.row_dict[pos]
        if num_pos > 0:
            self.row_dict[pos] -= 1

        self.my_points += player.points.values[0]

        # remove player
        self.df = self.df[self.df.player != player_name]

        self.run_opt(quiet=quiet)
        # self.backup_options(aths)
        
    def ig(self, player_name, what_i_paid, quiet=False, write=True):
        return self.i_got(player_name, what_i_paid, quiet, write)


    def they_got(self, player_name, quiet=False, write=True):
        if not quiet:
            print("they got: ", player_name)
        self.df = self.df[self.df.player != player_name]

        if write:
            with open("csv_files/their_team.csv", "a+") as f:
                f.write(f"{player_name}\n")

        self.run_opt(quiet=quiet)
        # self.backup_options(aths)
        
    def tg(self, player_name, quiet=False, write=True):
        return self.they_got(player_name, quiet, write)

    def what_if_they_got(self, player_name, quiet=False):

        temp_df = self.df[self.df.player != player_name]

        if quiet:
            _, proj_points, my_proj_points = self._run_opt(df=temp_df, row_dict=self.row_dict)
        else:
            _, proj_points, my_proj_points = self.run_opt(df=temp_df, row_dict=self.row_dict, quiet=quiet)
            print("what if they got: ", player_name)
            print(f"My proj points would be: {my_proj_points}")
        return my_proj_points
    
    def witg(self, player_name, quiet=False):
        return self.what_if_they_got(player_name, quiet)

    def what_if_i_got(self, player_name, what_i_paid, quiet=False):
        temp_row_dict = copy.deepcopy(self.row_dict)
        temp_df = copy.deepcopy(self.df)
        temp_my_points = copy.deepcopy(self.my_points)

        df_mask = self.df.player == player_name
        if not any(df_mask):
            print("That player ain't even an option")
            return
        else:
            player = self.df[df_mask]

        # subtract from your budget
        budget = temp_row_dict['Budget']
        if budget >= what_i_paid:
            temp_row_dict['Budget'] -= what_i_paid
        else:
            print("you would be out of budget dood!")
            print("current budget: ", budget)
            assert False

        tot = temp_row_dict['Tot']
        if tot > 0:
            temp_row_dict['Tot'] -= 1

        # subtract from number of positions
        pos = player.pos.values[0]
        num_pos = temp_row_dict[pos]
        if num_pos > 0:
            temp_row_dict[pos] -= 1

        temp_my_points += player.points.values[0]

        # remove player
        temp_df = temp_df[temp_df.player != player_name]
        if quiet:
            _, proj_points, my_proj_points =self._run_opt(df=temp_df, row_dict=temp_row_dict)
        else:
            _, proj_points, my_proj_points =self.run_opt(df=temp_df, row_dict=temp_row_dict, quiet=quiet)
            print("what if I got: ", player_name)
            print(f"My proj points would be: {proj_points  + temp_my_points}")
        return proj_points  + temp_my_points

    def max_i_could_pay_for(self, player_name):
        temp_df = copy.deepcopy(self.df)
        player = self.get_player(temp_df, player_name)
        lst, proj_points, _ = self._run_opt(df=temp_df)
        price = int(player.price)
        player_index = temp_df[temp_df.player == player_name].index.values[0]
        while self.player_in_list(player_name, lst):
            price += 1
            temp_df.at[player_index,'price'] = price
            lst, proj_points, _ = self._run_opt(df=temp_df)

        price = int(temp_df[temp_df.player == player_name].price) - 1
        # print lst
        #print(f"The highest price {player_name} could be for me to get them would be ${price}")
        return price
    
    def m(self, player_name):
        return self.max_i_could_pay_for(player_name)


    def min_i_could_pay_for(self, player_name):
        temp_df = copy.deepcopy(self.df)
        player = self.get_player(temp_df, player_name)
        lst, proj_points, _ = self._run_opt(df=temp_df)
        price = int(player.price)
        player_index = temp_df[temp_df.player == player_name].index.values[0]
        while not self.player_in_list(player_name, lst):
            if price == 0:
                break
            price -= 1
            temp_df.at[player_index,'price'] = price
            lst, proj_points, _ = self._run_opt(df=temp_df)


        #price = int(temp_df[temp_df.player == player_name].price) - 1
        # print lst
        #print(f"The highest price {player_name} could be for me to get them would be ${price}")
        return price

    def mn(self, player_name):
        return self.min_i_could_pay_for(player_name)
    
    def proj_point_loss_if_miss(self, player_name, price, quiet=False):
        nomiss_pts = self.what_if_i_got(player_name, price, quiet=True)
        miss_pts = self.what_if_they_got(player_name, quiet=True)
        diff = nomiss_pts - miss_pts
        if not quiet:
            print(f"I would miss out on {diff} points")
            print(f"I would miss out on {diff / 14} points per game")
        return diff
        
    def pplim(self, player_name, price, quiet=False):
        return self.proj_point_loss_if_miss(player_name, price, quiet)


    def player_in_list(self, plyr, lst):
        for (player, price, pos) in lst:
            if plyr == player:
                return True
        return False
    
    def get_max_prices(self, df=None):
        aths, _, _ = self._run_opt()
        opt_players, _, _ = zip(*aths)
        if df is None:
            df = self.df       
        df_view = df[df.price > 0]
        df_view = df_view.drop(labels=['points', 'pos'], axis=1)
        max_prices = [(self.m(player) if player in opt_players else self.mn(player)) for player in df_view.player ]
        df_view.insert(2, 'max_price_id_pay_rn', max_prices)
        df_view = df_view[df_view.max_price_id_pay_rn > 0]
        print(df_view)
              
    def get_pos_max_prices(self, pos_str):
        pos_view = self.df[self.df.pos == pos_str]
        self.get_max_prices(pos_view)
        
    def allmax(self):
        self.get_max_prices()
    
    def wr(self):
        self.get_pos_max_prices('WR')
        
    def rb(self):
        self.get_pos_max_prices('RB')
        
    def te(self):
        self.get_pos_max_prices('TE')
        
    def qb(self):
        self.get_pos_max_prices('QB')
        
    def dst(self):
        self.get_pos_max_prices('DST')


if __name__ == "__main__":
    ff = ff_opt()
    # ff.restore()
    # ff.run_opt()
    # ff.i_got("DakPrescott",5)
    # ff.they_got("DeshaunWatson")
    # ff.they_got("KylerMurray")
    # ff.they_got("JoshAllen")
    # ff.i_got("JamesConner",20)









