__author__ = 'racah'
import csv
import json

d = {}
lines=[]
with open('espn_prices.csv', 'rU') as csvfile:
    reader = csv.reader(csvfile, delimiter=',',dialect=csv.excel_tab)
    for idx, row in enumerate(reader):
            pos,player,price = row
            for p in ["RB","WR","QB","TE","DST","K"]:
                if p in pos:
                    pos = p
            player = player.lower().split('jr')[0].split('sr')[0]
            player = player.split("d/st")[0]
            player = player.replace(".","")

            if price == '--':
                d[player] = {'price':1}
            else:
                d[player] = {'price': price.replace('$','')}
            d[player]['pos'] = pos

            



with open('num_fire_points.csv', 'rU') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for idx, row in enumerate(reader):
        if idx == 0:
            fieldnames = row
        else:
            firefactor,points,player = row
            player = player.lower().split('jr')[0]
            player = player.split("d/st")[0]
            player = player.replace(".","")

            if player in d:
                d[player]['points'] = points
                d[player]['firefactor'] = firefactor
            else:
                print player


d ={k: d[k] for k in d.keys() if 'points' in d[k] }
for k in d.keys():
    d[k]['player'] = k

dic = d.values()
print d["tyhilton"]
with open('data.csv', 'wb') as csvfile:
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(dic[0].keys())
    for d in dic:
        writer.writerow(d.values())

# json.dump(dic, open('data.json','w'))






