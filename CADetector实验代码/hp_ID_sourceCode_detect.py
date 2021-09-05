import re
from loadJson import load_json
from hp_BD_sourceCode_detect import BD_deal

# max_len = -1
# min_len = 10000

#ID的common_deal也要去掉token的判断
pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

#继承紊乱的匹配 - position 1
pattern_contractName = re.compile(r'(.*contract\s+.*)')
# positrion 2, 看它出现了几次
# pattern_owner = re.compile(r'address (.*owner.*);', re.IGNORECASE)
# pattern_owner = re.compile(r'address (.*Owner.*)')

# position 4
pattern_transfer_1 = re.compile(r'.transfer[(](.*)[)]')
pattern_send_2 = re.compile(r'.send[(](.*)[)]')
pattern_call_3 = re.compile(r'.call[.]value[(](.*)[)][(][)]')

def delect_more_space_row(vcode):
    return "".join([s for s in vcode.splitlines(True) if s.strip()])

def common_deal(hp, vcode):
    # token-1 不太严谨， 如果后续影响检测，可考虑删除，这里的目的纯粹是为了排除复杂逻辑
    # token_re_1 = re.findall(pattern_exclude_noToken_1, vcode, flags=0)
    # print(token_re_1)
    # print(len(token_re_1))

    # 删除多行注释
    # print(hp)
    patterrn_multiLine_comment = re.compile(r"/[*]([\s\S]*?)[*]/")
    multiLine_comments = re.findall(patterrn_multiLine_comment, vcode, flags=0)
    # print(multiLine_comments)
    for multiLine in multiLine_comments:
        vcode = vcode.replace(multiLine, '')

    vcode = delect_more_space_row(vcode)
    rows_list = vcode.split('\n')
    rows_len = len(rows_list)
    # print(rows_list)
    # print(len(rows_list))
    comment_record_list = []
    for i in rows_list:
        i = i.strip()
        # if (i == '') or (i[:2] == '//') or (i[:4] == '/**/'):
        if (len(i) > 2) and ((i[:2] == '//') or (i[:4] == '/**/')):
            # vcode = vcode.replace(i, '')
            comment_record_list.append(i)
            rows_len -= 1
    comment_record_list.sort(reverse=True)
    # print('comment_record_list is: ',comment_record_list)
    for comment_record in comment_record_list:
        vcode = vcode.replace(comment_record, '')
    # print(rows_len)  #排除注释后的行数
    # if rows_len > max:
    #     max = rows_len
    # if rows_len < min:
    #     min = rows_len
    # print(min, max)
    # 用超于当前蜜罐最大有效行数的三倍去定义复杂逻辑, 超过就等价于复杂逻辑, 对新手黑客不具有吸引力。
    if rows_len > 450:
        # continue
        return 0

    # 进一步删除注释
    vcode = vcode.replace('/**/', '')
    pattern_with_comment = re.compile(r'(//.*)')
    with_comment_re = re.findall(pattern_with_comment, vcode, flags=0)
    for i in with_comment_re:
        vcode = vcode.replace(i, '')

    # SafeMath_re = re.findall(pattern_exclude_1, vcode, flags=0)
    # # print(SafeMath_re)
    # # 其实, 还应该
    # SafeMath_exist = False
    # if (SafeMath_re != []):
    #     for i in SafeMath_re:
    #         if i[0] == '':
    #             SafeMath_exist = True
    #             break
    # if SafeMath_exist == True:
    #     # continue
    #     return 0

    if rows_len > 150:
        SafeMath_re = re.findall(pattern_exclude_1, vcode, flags=0)
        # print(SafeMath_re)
        # 其实, 还应该
        SafeMath_exist = False
        if (SafeMath_re != []):
            for i in SafeMath_re:
                if i[0] == '':
                    SafeMath_exist = True
                    break
        if SafeMath_exist == True:
            # continue
            return 0

        Interface_re = re.findall(pattern_exclude_noInterface, vcode, flags=0)
        # print(hp, "&&&&&&&&&&&&&&",Interface_re)
        if Interface_re != []:
            # continue
            return 0

    # # token-2 不太严谨， 如果后续影响检测，可考虑删除，这里的目的纯粹是为了排除复杂逻辑
    # token_re_2 = re.findall(pattern_exclude_noToken_2, vcode, flags=0)
    # # print(len(token_re))
    # # print(token_re)
    # if (token_re_1 != []) and (token_re_2 != []):
    #     # continue
    #     return 0

    list_compiler = re.findall(pattern_compiler, vcode, flags=0)
    if len(list_compiler) != 0:
        minor_version = int(list_compiler[0].split('.')[1])
        patch_version = int(list_compiler[0].split('.')[2])
        minor_patch_v = minor_version * 100 + patch_version
        if minor_patch_v >= 400:
            payable_re_list = re.findall(pattern_exclude_noPayable, vcode, flags=0)
            if payable_re_list == []:
                # continue
                return 0

    return vcode

def function_or_modifier_split(vcode, splitStr='function'):
    # 1-1. 在无注释的代码中, 按function 划分
    vcode_split_by_Function_list = vcode.split(splitStr)
    # print(vcode_split_by_Function_list)
    function_code_list = []
    for i in vcode_split_by_Function_list[1:]:
        # if (i.strip(' ')[-1] != '\n'):
        # print("i is: ",i)
        left_index = 0
        right_index = -1
        # 大括号或说花括号没太有可能成为智能合约中使用的字符
        left_BigBucket_indexs = [i.start() for i in re.finditer('{', i)]
        # print(left_BigBucket_indexs, "*********")
        right_BigBucket_indexs = [i.start() for i in re.finditer('}', i)]
        # print(right_BigBucket_indexs)
        if ((left_BigBucket_indexs == []) and (right_BigBucket_indexs == [])) or \
                ((left_BigBucket_indexs == []) and (right_BigBucket_indexs != [])) or \
                (right_BigBucket_indexs[0] < left_BigBucket_indexs[0]):
            semicolon_indexs = [i.start() for i in re.finditer(';', i)]
            if semicolon_indexs != []:
                left_index = semicolon_indexs[0]
                right_index = semicolon_indexs[0]
        else:
            # 这里可以有多种不同的判断方式
            left_index = left_BigBucket_indexs[0]
            right_index = -1
            merge_l_r_list = left_BigBucket_indexs + right_BigBucket_indexs
            merge_l_r_list.sort()
            # match_l_r = {}
            while merge_l_r_list:
                # print(merge_l_r_list,"YYYYYYYYYYYYYYYYmerge_l_r_listYY")
                for index in range(len(merge_l_r_list)):
                    if merge_l_r_list[index] in right_BigBucket_indexs:
                        if merge_l_r_list[index - 1] == left_index:
                            right_index = merge_l_r_list[index]
                        merge_l_r_list.pop(index)
                        if merge_l_r_list != []:
                            merge_l_r_list.pop(index - 1)
                        break
                if right_index != -1:
                    break
                # 异常情况退出
                len_intersec_left = len(set(merge_l_r_list).difference(set(left_BigBucket_indexs)))
                len_intersec_right = len(set(merge_l_r_list).difference(set(right_BigBucket_indexs)))
                if (len_intersec_left == 0) or (len_intersec_right == 0):
                    break
        # print(left_index, right_index)
        # 0到left_index处是形参部分; 从left_index到right_index是函数体部分。
        # function_code_list.append(i[left_index:right_index])
        # function_code_list.append(i[:right_index])
        function_code_list.append((i[:left_index], i[left_index:right_index]))

    return function_code_list

def ID_deal(hp, vcode):
    is_ID_hp = False

    contractName_list_temp = re.findall(pattern_contractName, vcode, flags=0)
    split_contract_str = ''
    contractName_list = []
    for contractName_i in contractName_list_temp:
        if (contractName_i.strip().split(r'\n')[-1][:len("contract")] != "contract"):
            continue
        contractName_list.append(contractName_i.strip().split('\n')[-1])
        split_contract_str = split_contract_str + contractName_i.strip() + '|'
    # print('contractName_list is: ',contractName_list)
    if (len(contractName_list) >= 2):
        # father = []
        child = []
        for index_i in range(len(contractName_list)):
            if 'is' in contractName_list[index_i]:
                split_list = contractName_list[index_i].split('is')
                child.append(split_list[0].strip())
                # father不准确，可能存在多重继承
                # father.append(split_list[1].strip())
        if len(child) == 0:
            # continue
            return is_ID_hp
    else:
        # continue
        return is_ID_hp

    # 分割合约代码: contract_list
    contract_code_list_temp = re.split(split_contract_str[:-1], vcode)[1:]
    contract_code_list = []
    for cN_temp in contract_code_list_temp:
        if cN_temp != None:
            contract_code_list.append(cN_temp)
    # print('split_contract_str is: ', split_contract_str[:-1])
    # print('contract_code_list is: ',contract_code_list)
    # 获取全局代码:
    function_code_list = function_or_modifier_split(vcode, 'function')
    function_code_list += function_or_modifier_split(vcode, 'modifier ')
    other_code_list = function_or_modifier_split(vcode, 'event ')
    other_code_list += function_or_modifier_split(vcode, 'struct ')
    global_var_code = vcode
    for function_code in function_code_list:
        # global_var_code = global_var_code.replace(function_code[0], '')
        global_var_code = global_var_code.replace(function_code[0] + function_code[1], '')
    for other_code in other_code_list:
        global_var_code = global_var_code.replace(other_code[0] + other_code[1], '')
    # print("gggggggg",global_var_code)
    # print("function_code_list is: ",function_code_list)

    # positrion 2, 看它出现了几次
    pattern_owner = re.compile(r'(address [^=>\[\]\n]*owner[^)\n=\s]*)\s*[^)\n]*;+', re.IGNORECASE)  #有一种address public owner = 0x0;
    owner_list_temp = re.findall(pattern_owner, global_var_code, flags=0)
    owner_list = owner_list_temp.copy()
    for owenr_var in owner_list_temp:
        if (')' in owenr_var) or ('(' in owenr_var):
            owner_list.remove(owenr_var)
    # owner变量在几个合约里有定义呢:
    owner_inXcN_num = 0
    for each_cN in contract_code_list:
        is_owner_exist = False
        for each_owner_i in owner_list:
            if each_owner_i in each_cN:
                is_owner_exist = True
        if is_owner_exist == True:
            owner_inXcN_num += 1
    if (len(owner_list) < 2) or (owner_inXcN_num < 2):
        return is_ID_hp
    # print("contract_code_list: ",contract_code_list)
    # for str in owner_list:
    #     print(str.split(';'))

    owner2msgSender_list = []
    owner_var_i_set = set()
    for owenr_var in owner_list:
        owenr_var_list = owenr_var.split(';')[0].split(',')[0].split(' ')
        # owenr_var_list中通常只有1个元素包含owner
        for var_i in owenr_var_list:
            # pattern_var = re.compile(r'(.*owner.*)', re.IGNORECASE)
            pattern_var = re.compile(r'(.*owner.*)', re.IGNORECASE)
            list_temp = re.findall(pattern_var, var_i, flags=0)
            if list_temp == []:
                continue
            owenr_var = var_i
            owner_var_i_set.add(var_i)
            # positrion 3, 看它出现了几次
            pattern_owner = re.compile(owenr_var + r'(.*)=(.*)msg.sender;')
            owner2msgSender_list += re.findall(pattern_owner, vcode, flags=0)
    # print(len(owner2msgSender_list))
    # print('owner2msgSender_list ', owner2msgSender_list)
    if len(owner2msgSender_list) < 2:
        # continue
        return is_ID_hp

    # 获取contractName
    contractName_set = set()
    for str_cN in contractName_list:
        singleCN_list = str_cN.split()
        if len(singleCN_list) < 2:
            continue
        contractName_set.add(singleCN_list[1])
    _count = 0
    for each_functionOrmodifyer in function_code_list:
        if ('onlyOwner' in each_functionOrmodifyer[0]):
            continue
        # print("contractName_set is: ",contractName_set)
        _count_v0 = 0
        for _contract_name in contractName_set:
            if (_contract_name+'(' in each_functionOrmodifyer[0]) or (_contract_name+' (' in each_functionOrmodifyer[0]):
                _count_v0 += 1
        if _count_v0 > 0:
            continue
        # print('***owner_var_i_set is: ', owner_var_i_set)
        for owner_var_i in owner_var_i_set:
            pattern_owner_assignment = re.compile('(.*'+owner_var_i + r'\s*=\s*[^)=>\n]*;+)')
            owner_assignment_result = re.findall(pattern_owner_assignment, each_functionOrmodifyer[1], 0)
            # print("^^",each_functionOrmodifyer[0],'///',each_functionOrmodifyer[1])
            # print("&&&&&&&&&&&&&", owner_assignment_result)
            if owner_assignment_result != []:
                # 下面这一段可能导致漏报？
                for e_i in owner_assignment_result:
                    for cN_index in range(len(contractName_list)):
                        if ('is' in contractName_list[cN_index]) and (e_i.strip() in contract_code_list[cN_index]):
                            if (e_i.strip()[0:len(owner_var_i)] != owner_var_i): #and (e_i[0][-1] != ' ') and (e_i[0][-1] != '\n'):
                                continue
                            else:
                                _count += 1

    if _count <= 0:
        return is_ID_hp
    # print("_count: ",_count)

    transfer_1_list = re.findall(pattern_transfer_1, vcode, flags=0)
    send_2_list = re.findall(pattern_send_2, vcode, flags=0)
    call_3_list = re.findall(pattern_call_3, vcode, flags=0)
    # print(transfer_1_list, '1')
    # print(send_2_list, '2')
    # print(call_3_list, '3')
    if (len(transfer_1_list) != 0) or (len(send_2_list) != 0) or (len(call_3_list) != 0):
        print(hp, ' has a high possibility to be a ID hp.')
        is_ID_hp = True

    return is_ID_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # hp_dict = load_json(paper_new_hp_path)
    for hp, vcode in hp_dict.items():
            # print(vcode)
            # if hp == r'0x017bcaee2456d8bd0e181f94165919a4a2ecc2d9':
            # if hp == r'0x33f82dfbaafb07c16e06f9f81187f78efa9d438c':

            # 删除多行注释
            # print(hp)
            patterrn_multiLine_comment = re.compile(r"/[*]([\s\S]*?)[*]/")
            multiLine_comments = re.findall(patterrn_multiLine_comment, vcode, flags=0)
            # print(multiLine_comments)
            for multiLine in multiLine_comments:
                vcode = vcode.replace(multiLine, '')

            rows_list = vcode.split('\n')
            rows_len = len(rows_list)
            # print(rows_list)
            # print(len(rows_list))
            for i in rows_list:
                i = i.strip()
                # if (i == '') or (i[:2] == '//') or (i[:4] == '/**/'):
                if (len(i) > 2) and ((i[:2] == '//') or (i[:4] == '/**/')):
                    vcode = vcode.replace(i, '')
                    rows_len -= 1
            # print(vcode)
            # print(rows_len)  #排除注释后的行数
            # if rows_len > max:
            #     max = rows_len
            # if rows_len < min:
            #     min = rows_len
            # print(min, max)
            # 用超于当前蜜罐最大有效行数的三倍去定义复杂逻辑, 超过就等价于复杂逻辑, 对新手黑客不具有吸引力。
            if rows_len > 500:
                continue

            SafeMath_re = re.findall(pattern_exclude_1, vcode, flags=0)
            # print(SafeMath_re)
            # 其实, 还应该
            SafeMath_exist = False
            if (SafeMath_re != []):
                for i in SafeMath_re:
                    if i[0] == '':
                        SafeMath_exist = True
                        break
            if SafeMath_exist == True:
                continue

            Interface_re = re.findall(pattern_exclude_noInterface, vcode, flags=0)
            # print(hp, "&&&&&&&&&&&&&&",Interface_re)
            if Interface_re != []:
                continue

            payable_re_list = re.findall(pattern_exclude_noPayable, vcode, flags=0)
            if payable_re_list == []:
                continue

            contractName_list = re.findall(pattern_contractName, vcode, flags=0)
            # print(contractName_list)
            if (len(contractName_list) >= 2):
                # father = []
                child = []
                for index_i in range(len(contractName_list)):
                    if 'is' in contractName_list[index_i]:
                        split_list = contractName_list[index_i].split('is')
                        child.append(split_list[0].strip())
                        # father不准确，可能存在多重继承
                        # father.append(split_list[1].strip())
                if len(child) == 0:
                    continue
            else:
                continue

            # positrion 2, 看它出现了几次
            pattern_owner = re.compile(r'address (.*owner[^)\n]*);', re.IGNORECASE)
            owner_list = re.findall(pattern_owner, vcode, flags=0)
            # print(hp, owner_list)
            if len(owner_list) < 2:
                continue
            # print(hp, owner_list)
            # for str in owner_list:
            #     print(str.split(';'))

            owner2msgSender_list = []
            for owenr_var in owner_list:
                owenr_var_list = owenr_var.split(';')[0].split(' ')
                # owenr_var_list中通常只有1个元素包含owner
                for var_i in owenr_var_list:
                    # pattern_var = re.compile(r'(.*owner.*)', re.IGNORECASE)
                    pattern_var = re.compile(r'(.*owner.*)', re.IGNORECASE)
                    list_temp = re.findall(pattern_var, var_i, flags=0)
                    if len(list_temp)!=0:
                        owenr_var = var_i
                    # print(owenr_var)
                    if ("(" in owenr_var) or (")" in owenr_var):
                        continue
                    # positrion 3, 看它出现了几次
                    pattern_owner = re.compile(owenr_var + r'(.*)=(.*)msg.sender;')
                    owner2msgSender_list += re.findall(pattern_owner, vcode, flags=0)
            # print(len(owner2msgSender_list))
            # print(owner2msgSender_list)
            if len(owner2msgSender_list) < 2:
                continue

            transfer_1_list = re.findall(pattern_transfer_1, vcode, flags=0)
            send_2_list = re.findall(pattern_send_2, vcode, flags=0)
            call_3_list = re.findall(pattern_call_3, vcode, flags=0)
            if (len(transfer_1_list)!=0) or (len(send_2_list)!=0) or (len(call_3_list)!=0):
                print(hp, ' has a high possibility to be a ID hp.')


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # hp_dict = load_json(paper_new_hp_path)
    for hp, vcode in hp_dict.items():
        # if hp == r'0xfbe2fa4d1eff72d1c0e7e06ec731f44a85fc76ec':
        # if hp == r'0xc710772a16fd040ed9c63de0679a57410981e3fc':
            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            if BD_deal(hp, vcode) == True:
                continue

            ID_deal(hp, vcode)


'''
# honeypots_all8tyes_truePositive.json: 0误报、0漏报
+++0x5bb52e85c21ca3df3c71da6d03be19cff89e7cf9  has a high possibility to be a ID hp.  ---- 既包含有余额紊乱, 也包含有继承紊乱 --(再次)- 0x5bb52e85c21ca3df3c71da6d03be19cff89e7cf9  has a high possibility to be a BD hp.
0x017bcaee2456d8bd0e181f94165919a4a2ecc2d9  has a high possibility to be a ID hp. √
0x038e20839aebfe12b7956adcbc2511f6f7085164  has a high possibility to be a ID hp. √
0x07f06a75ddf49de735d51dbf5c0a9062c034e7c6  has a high possibility to be a ID hp. √
0x0bcccba050c2ce6439c57bd203378b113cc3cfd6  has a high possibility to be a ID hp. √
0x11f3081cd6b2ac5a263e65e206f806bea7fa9c56  has a high possibility to be a ID hp. √
0x1767856bc75cf070de5e6ba3d0c718440f008c66  has a high possibility to be a ID hp. √
0x33685492a20234101b553d2a429ae8a6bf202e18  has a high possibility to be a ID hp. √
0x33b44a1d150f3feaa40503ad20a75634adc39b18  has a high possibility to be a ID hp. √
0x340844b39aacbdb4e7718fa14a95758f87a09a9a  has a high possibility to be a ID hp. √
0x3526cf7d12c95b11a680678cc1f705cba667578d  has a high possibility to be a ID hp. √
0x3e7840b88396acd80bac66021e1354064461a498  has a high possibility to be a ID hp. √
0x4ba0d338a7c41cc12778e0a2fa6df2361e8d8465  has a high possibility to be a ID hp. √
0x4c7c98c4d64c29ef8103b005eeccf5145cfdf8c1  has a high possibility to be a ID hp. √
0x4dc76cfc65b14b3fd83c8bc8b895482f3cbc150a  has a high possibility to be a ID hp. √
0x4fed7f5f0314bd156a8486fc41dc8bd4737c24fb  has a high possibility to be a ID hp. √
0x50abfc76b637b70571c301071f7ce660c1c3d847  has a high possibility to be a ID hp. √
0x50ddfe3722fc303cace413df41db23d55025e2e6  has a high possibility to be a ID hp. √
0x52c2d09acf0ef12c487ae0c20a92d4f9a4abbfd1  has a high possibility to be a ID hp. √
0x58978e8caccf56fadaa80ef52f5c684045306839  has a high possibility to be a ID hp. √ --- 相似字符混淆
0x5b2028602af2693d50b4157f4acf84d632ec8208  has a high possibility to be a ID hp. √
0x5c8546a7b86ba30202c09a84f5a72644a2a4f7ba  has a high possibility to be a ID hp. √
0x641074844a0dd00042347161f830346bdfe348bc  has a high possibility to be a ID hp. √
0x68563d2a5fc58f88db8140a981170989f001b746  has a high possibility to be a ID hp. √
0x6e843aefc1f2887e5b0aeb4002c1924c433d9a13  has a high possibility to be a ID hp. √
0x70c01853e4430cae353c9a7ae232a6a95f6cafd9  has a high possibility to be a ID hp. √
0x7704442e1005b9ab403463ed85e2fb24761a8738  has a high possibility to be a ID hp. √
0x787080326e1f7e0eae490efdb18e90cfd0ae2692  has a high possibility to be a ID hp. √
0x78faf034c61f4158a4a12bfa372187a21405ae33  has a high possibility to be a ID hp. √
0x7e97c48497a8d650dc030744b74c81e29816f8e3  has a high possibility to be a ID hp. √
0x81edefc64aabdce71f68347774bd4673d1d31419  has a high possibility to be a ID hp. √
0x849019a489c3c26c7a7668e468be81a4d132781f  has a high possibility to be a ID hp. √ --- 相似字符混淆
0x9168fdc9f9db7b71865fe4bfd6f78b3610ebc704  has a high possibility to be a ID hp. √
0x96050da7c01bbd4891ed766720a5c1c79b824163  has a high possibility to be a ID hp. √
0x98fe1d52649a3a13863647c6789f16e46e090377  has a high possibility to be a ID hp. √
0xa16cdcba1d6cb6874ff9fd8a6c8b82a3f834f512  has a high possibility to be a ID hp. √
0xb31820c1d84e183377030b6d3f0e1ee5c1cff643  has a high possibility to be a ID hp. √
0xc0c7d89e4968775931e53e9510ebad43644b0866  has a high possibility to be a ID hp. √
0xcacf9396a56e9ff1e3f6533be83a043c36ce0436  has a high possibility to be a ID hp. √
0xe65c53087e1a40b7c53b9a0ea3c2562ae2dfeb24  has a high possibility to be a ID hp. √
0xf1aab4171ceb49b6a276975347e3c1d4d5650e5a  has a high possibility to be a ID hp. √
0xfae0300c03a1ea898176bcb39f919c559f64f4ff  has a high possibility to be a ID hp. √
'''

'''
# honeypots_paper_new_addr2SouceCode.json
0x1235b9042f7fe167f09450eaffdc07efcc3acb38  has a high possibility to be a ID hp. √
0x33f82dfbaafb07c16e06f9f81187f78efa9d438c  has a high possibility to be a ID hp. √
0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01  has a high possibility to be a ID hp. √ --- 多重继承
0x4b17c05fc1566891e5a9220d22527b5aeab0e1d0  has a high possibility to be a ID hp. √
0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839  has a high possibility to be a ID hp. √ --- 多重继承
0x81c798ea668b6d7e07ea198014265e0c1d64b5a8  has a high possibility to be a ID hp. √
0x8fd1e427396ddb511533cf9abdbebd0a7e08da35  has a high possibility to be a ID hp. √ --- 多重继承
0xb11b2fed6c9354f7aa2f658d3b4d7b31d8a13b77  has a high possibility to be a ID hp. √
0xbaa3de6504690efb064420d89e871c27065cdd52  has a high possibility to be a ID hp. √
0xbebbfe5b549f5db6e6c78ca97cac19d1fb03082c  has a high possibility to be a ID hp. √
0xc710772a16fd040ed9c63de0679a57410981e3fc  has a high possibility to be a ID hp. √ --- 隐藏状态更新与继承紊乱结合使用 - 
0xe7e25a3d83abdc4a4273792cca7865889a7b0df3  has a high possibility to be a ID hp. √
0xf0cc17aa0ce1c6595e56c9c60b19c1c546ade50d  has a high possibility to be a ID hp. √ --- 隐藏状态更新与继承紊乱结合使用 - 
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
0xedf4597f75cd1773978eb51ad0b2c59d5d742756  has a high possibility to be a ID hp. √
0xeea07c4fef88f043102a45fae9c21a9154373a11  has a high possibility to be a ID hp. √
'''