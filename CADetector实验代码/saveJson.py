import json

def save_json(jsonFile, list_name):  #list or dict
    with open(jsonFile, 'w') as wf:
        json.dump(list_name, wf, indent=4)

def save_json_a(jsonFile, list_name):  #list or dict
    with open(jsonFile, 'a') as wf:
        json.dump(list_name, wf, indent=4)