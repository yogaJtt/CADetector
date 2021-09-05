import json

def load_json(jsonFile):  #list or dict
    with open(jsonFile, 'r') as rf:
        list_name = json.load(rf)
        return list_name

if __name__ == '__main__':
    list_name = load_json('latest_hrs_sc_urls.json')
    print(list_name)
    print(len(list_name))


