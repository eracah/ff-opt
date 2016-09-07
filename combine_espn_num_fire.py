__author__ = 'racah'
import csv
import json

d = {}
lines=[]
with open('espn_prices.csv', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for idx, row in enumerate(reader):
        if idx == 0:
            fieldnames = row
        else:
            player, pos, _, _, _, price = row
            player = player.lower().split(' jr.')[0]

            if price == '--':
                d[player] = {'price':1}
            else:
                d[player] = {'price': price.replace('$','')}
            d[player]['pos'] = pos



with open('num_fire_points.csv', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for idx, row in enumerate(reader):
        if idx == 0:
            fieldnames = row
        else:
            player, _, _, _, risk, points, firefactor = row
            player = player.lower()
            if player in d:
                d[player]['risk'] = risk
                d[player]['points'] = points
                d[player]['firefactor'] = firefactor
            else:
                print player


d ={k: d[k] for k in d.keys() if 'points' in d[k] }
for k in d.keys():
    d[k]['player'] = k

dic = d.values()
with open('data.csv', 'wb') as csvfile:
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(dic[0].keys())
    for d in dic:
        writer.writerow(d.values())

# json.dump(dic, open('data.json','w'))






