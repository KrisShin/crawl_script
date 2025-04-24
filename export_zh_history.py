import json
from pymongo import MongoClient
from common.global_variant import mongo_uri
import csv


def main():
    # all_symbol = set()
    # with open('./symbol_all.json', 'r') as f:
    #     all_symbol = set(json.load(f))
    # mongo_symbol = set()
    # with open('./symbol_mongo.json', 'r') as f:
    #     mongo_symbol = set(json.load(f))
    # db_symbol = set()
    # with open('./symbol_db.json', 'r') as f:
    #     db_symbol = set(json.load(f))
    # rest = mongo_symbol - db_symbol
    # with open('./rest.json', 'w') as f:
    #     f.write(json.dumps(list(rest)))
    # print(len(rest))
    # s = True
    # index = 0
    # while s:
    #     with open('./rest.json', 'r') as f:
    #         rest = json.load(f)
    #     s = rest[index : index + 64375]
    #     index += 64375
    #     with open(f'./rest_{index}.json', 'w') as f:
    #         f.write(json.dumps(s))
    index = 64375
    step = 64375
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client['xueqiu']
    collection = db['zh_history']
    while True:
        with open(f'./rest_{index}.json', 'r') as f:
            rest = json.load(f)
        if not rest:
            break
        result = collection.find({'symbol': {'$in': rest}})
        with open(f'./zh_history_{index}.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'name', 'hisory'])
            data = []
            for item in result:
                data.append([item['symbol'], item['name'], item['history']])
            writer.writerows(data)
        if index == 515000:
            break
        index += step


if __name__ == '__main__':
    main()
