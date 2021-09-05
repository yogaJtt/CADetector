# 使用简单的模糊匹配
import difflib

benchmark_smartcontract_code = ''
sol_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\etherscan_api\RACEFORETH.sol'
with open(sol_path) as solFile:
    benchmark_smartcontract_code = solFile.read()
# print(benchmark_smartcontract_code)

#benchmark_smartcontract_code

thred_line = 0.9

# print(difflib.SequenceMatcher(None,"amazing","amaging").ratio())
hp = ''
vcode = ''
hp_Type11_dict = {'NumGame':[]}

def NumGame_deal(hp, vcode, hp_Type11_dict={'NumGame':[]},thred_line=0.9):
    if(difflib.SequenceMatcher(None,benchmark_smartcontract_code,vcode).ratio()>=thred_line):
        hp_Type11_dict['NumGame'] += [hp]
