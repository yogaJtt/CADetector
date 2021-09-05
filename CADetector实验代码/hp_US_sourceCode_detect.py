import re
from loadJson import load_json
# from hp_HSU_sourceCode_detect import function_split

'''
核心知识点： 
合约全局变量存储在storage中，局部变量一般存储在memory中。
但因为solidity语言的变量存储有一个特性，即数组、映射、结构体类型的局部变量默认是引用合约的storage ，
即若合约中包含未初始化的数组、映射、结构体类型的局部变量，可以通过他们覆盖存储在storage中的全局变量。
'''

'''
0. 转账函数
1. struct关键字: 获取一个字典, key为结构体的名字, value是一个列表, value列表中存放的是结构体中定义的变量.
2. 有以这个struct结构体定义的指针变量或指针变量数组
3. 存在于if判断中的状态变量, 声明在struct变量之前. --- (隐含了就是一定要有声明的其他状态变量)
4. 由指针变量或指针变量数组引出的结构体中的变量存在被赋值的过程.
5. ?要不要关注一下编译器版本, 这个问题存在于0.5.0版本之前. --- 比如可以尝试在源码中获取编译器版本,如果可以获取到作为判别标准, 否则就不作为判别标准.
'''

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')
# pattern_exclude_noToken_1 = re.compile(r'(\s+token\s+.*)', re.IGNORECASE)  #可能并不严谨
# pattern_exclude_noToken_2 = re.compile(r'(token.*)', re.IGNORECASE)  #可能并不严谨

#类型推导溢出的匹配 - position 1 --- 必要的
# pattern_1 = re.compile(r'var\s+(.*)=\s*([0-9]*);')
pattern_1_0 = re.compile(r'([^struct\n]*struct)\s+([^}{\n\s]*)\s*([^}]*)')  #3-tuple List
# pattern_1_1 = re.compile(r'var\s+(.*)([=\s;0-9]*)')
# position 2 --- 必要的(之一)
pattern_0_transfer_1 = re.compile(r'([^\s\n]*).transfer[(](.*)[)]')
pattern_0_send_2 = re.compile(r'([^\s\n]*).send[(](.*)[)]')
pattern_0_call_3 = re.compile(r'([^\s\n]*).call.value[(](.*)[)][(][)]')
#position3
# pattern_3_0 = re.compile(r'([u]*int[1-9]+|string|bool|address|bytes[0-9]+)([^(){]*)struct\s+([^{\n\s]*)') #3-tuple List
pattern_3_0 = re.compile(r'([u]*int[1-9]*|string|bool|address|bytes[0-9]+)\s*(public|private|internal|external)*\s+([^\n]*)')
# pattern_3_0 = re.compile(r'([u]*int[1-9]*|string|bool|address|bytes[0-9]+)\s*(public|private|internal|external)*\s+([^)\n]*)')
# pattern_3 = re.compile(r'([u]*int[1-9]+|string|bool|address|bytes[0-9]+)\s*(public|private|internal|external)*\s+([^=)\n]*);+[^{]*')

pattern_contractName = re.compile(r'(.*contract\s+.*)')

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

# 最终版本在这里
def US_deal(hp, vcode):
    contractName_list = []
    contractName_list_temp = re.findall(pattern_contractName, vcode, flags=0)
    # print(contractName_list_temp)
    for i in contractName_list_temp:
        if (i.strip()[:len('contract')] == "contract"):
            contractName_list.append(i)
    # print(contractName_list)

    # 2. 这里其实就是分割合约
    str_split = ''
    for contractName in contractName_list:
        contractName = contractName.strip() #如果携带'\r'为结束字符, 可能无法实现拼接。
        str_split = str_split + contractName + '|'
    str_split = str_split[:-1]
    vcode_list = re.split(str_split, vcode)[1:]
    # print(len(vcode_list))
    # print(vcode_list)

    # vcode_contract = {}
    # vcode_list = vcode.split('contract ')
    # # print(vcode_list[1].strip())
    # # print(vcode_list[2].strip())
    # for contractName in contractName_list:
    #     len_contractName = len(contractName)
    #     for i_code in vcode_list:
    #         if i_code.strip()[:len_contractName] == contractName:
    #             vcode_contract[contractName] = i_code

    is_US_hp = False
    for i_code in vcode_list:
        vcode = i_code

        if vcode == None:
            continue
        # 0. 转账函数
        list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
        list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
        list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
        if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
            continue

        # pattern1: get struct name set
        struct_info_dict = {}
        list_US_temp = re.findall(pattern_1_0, vcode, flags=0)
        list_US_1 = []
        for each_struct_temp in list_US_temp:
            if (each_struct_temp[0].strip()[:len('struct')] != 'struct'):
                continue
            list_US_1.append(each_struct_temp)
        # print("list_US_1 is: ", list_US_1)
        if (len(list_US_1) < 1):
            continue
        # print(list_US_1)

        for each_struct_info in list_US_1:
            # if ('' != each_struct_info[0]) and (' ' != each_struct_info[0][-1]) and ('\n' != each_struct_info[0][-1]) and ('\t' != each_struct_info[0][-1]):
            #     continue
            # if (each_struct_info[0].strip()[:len('struct')] != 'struct'):
            #     continue
            temp_paras_list = each_struct_info[2].split(';')
            if len(temp_paras_list) < 2:
                continue
            # each_struct_info[0]是key, struct定义的结构体名
            struct_info_dict[each_struct_info[1]] = []
            # 获取key对应的变量列表
            for i in range(len(temp_paras_list) - 1):
                # print(temp_paras_list[i].split(' ')[-1])
                # print(temp_paras_list,"++++++++")
                struct_info_dict[each_struct_info[1]].append(temp_paras_list[i].split(' ')[-1])
        # print(struct_info_dict)  #因为前面排除了，所以这里的struct_info_dict一定不为空

        count_len = 0
        for v_list in struct_info_dict.values():
            # print("vlist is: ", v_list)
            for v_para in v_list:
                pattern_1_1 = re.compile(r'\.+' + v_para + r'\s*=\s*(.*);')
                v_para_reValue = re.findall(pattern_1_1, vcode, flags=0)
                if v_para_reValue != []:
                    count_len += 1
        if count_len == 0:
            continue

        # 以struct结构体定义的指针变量或指针变量数组---（一定必须）
        function_or_modifier_code_list = function_or_modifier_split(vcode,'function')
        function_or_modifier_code_list += function_or_modifier_split(vcode,'modifier ')
        other_code_list = function_or_modifier_split(vcode,'event ')
        other_code_list += function_or_modifier_split(vcode,'struct ')
        # print(function_or_modifier_code_list)
        global_var_code = vcode
        for function_code in function_or_modifier_code_list:
            # global_var_code = global_var_code.replace(function_code[0], '')
            global_var_code = global_var_code.replace(function_code[0] + function_code[1], '')
        for other_code in other_code_list:
            global_var_code = global_var_code.replace(other_code[0] + other_code[1], '')
        # print("gggggggg",global_var_code)

        struct_define_para_set = set()
        # 按结构体名称的定义循环
        for struct_name in struct_info_dict:
            # 这个模式中, 不接受mapping的定义。
            pattern_2 = re.compile(struct_name + r'[\[\]]*\s+([^=;)\n]*);')
            # pattern_2 = re.compile(struct_name + r'(.*)\s+([^=;)\n]*);')
            # 在function中寻找 ---
            for each_function_code in function_or_modifier_code_list:  # 2-tuple list
                struct_define_list = re.findall(pattern_2, each_function_code[1], flags=0)
                # print(struct_define_list,"****")
                if struct_define_list == []:
                    continue
                # 获取以struct类型定义的变量名或数组名
                for struct_define in struct_define_list:
                    # if (struct_define[0][0] != '['):
                    #     continue
                    # struct_define = struct_define[1]
                    if 'memory ' in struct_define:
                        continue
                    else:
                        struct_define_para_set.add(struct_define.split()[-1])
        # print("**********",struct_define_para_set)
        if len(struct_define_para_set) == 0:
            continue

        # pattern3: 获取声明的状态变量
        state_para_info_list = re.findall(pattern_3_0, global_var_code, flags=0)  # 3-tuple List
        # print(state_para_info_list)
        # state_para_info_list不为空的话, 也并不意味着至少定义了一个状态变量
        if state_para_info_list == []:
            continue
        state_para_list = []
        for state_para_info in state_para_info_list:
            # 获取定义的变量, 每一个都对应一个列表
            state_para_list_temp = state_para_info[2].split(';')[:-1]
            # print("***",state_para_list_temp)
            if state_para_list_temp != []:
                state_para_list.append(state_para_list_temp[0].split('=')[0].strip())
                # state_para_list.append(state_para_list_temp.split('=')[0].strip().split()[-1])

        # 如果state_para_list不为空, 其里面也包含了struct中定义的变量.
        # print(state_para_list)
        # 把struct中定义的变量删除
        for v_list in struct_info_dict.values():
            state_para_list = list(set(state_para_list).difference(set(v_list)))
        # print(state_para_list)
        # 如果不存在声明的状态变量, 则该合约不是US
        if state_para_list == []:
            continue

        # pattern4: struct之前的变量有存在于if判断中(ps: require应该也可以)
        for stateP in state_para_list:
            # print("stateP is: ", stateP)
            pattern4_if_stateP = re.compile(r'if\s*[(]\s*(.*)' + stateP + r'(.*)\s*[)]')
            if_stateP_list = re.findall(pattern4_if_stateP, vcode, flags=0)
            # print(if_stateP_list)
            # 只要存在即可
            if if_stateP_list != []:
                print(hp, ' has a high possibility to be a US hp.')
                is_US_hp = True
                break

        # 意味着不用遍历其他子合约了
        if is_US_hp == True:
            break

        # 转账过程中涉及到的变量
        list_transfer_send_call = []
        for tranfer_i in list_transfer_1:
            list_transfer_send_call.append(tranfer_i[0])
            list_transfer_send_call.append(tranfer_i[1])
        for send_i in list_send_2:
            list_transfer_send_call.append(send_i[0])
            list_transfer_send_call.append(send_i[1])
        for call_i in list_call_3:
            list_transfer_send_call.append(call_i[0])
            list_transfer_send_call.append(call_i[1])
        # print(list_transfer_send_call)

        retA = [i for i in state_para_list if i in list_transfer_send_call]
        # print(retA)
        if retA != []:
            print(hp, ' has a high possibility to be a US hp.')
            is_US_hp = True

    return is_US_hp


def main():
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  #行数区间[19, 185] --去掉注释--> [14, 152]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    # hp_dict = load_json(paper_new_hp_path)

    # min = 10000
    # max = 0
    for hp, vcode in hp_dict.items():
            # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
            # if hp == r'0xd1915a2bcc4b77794d64c4e483e43444193373fa':

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
            # print(rows_len)  #排除注释后的行数
            # if rows_len > max:
            #     max = rows_len
            # if rows_len < min:
            #     min = rows_len
            # print(min, max)
            # 用超于当前蜜罐最大有效行数的三倍去定义复杂逻辑, 超过就等价于复杂逻辑, 对新手黑客不具有吸引力。
            if rows_len > 450:
                continue

            # 进一步删除注释
            pattern_with_comment = re.compile(r'(//.*)')
            with_comment_re = re.findall(pattern_with_comment, vcode, flags=0)
            for i in with_comment_re:
                vcode = vcode.replace(i, '')

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

            contractName_list = []
            contractName_list_temp = re.findall(pattern_contractName, vcode, flags=0)
            # print(contractName_list_temp)
            for i in contractName_list_temp:
                if(i.strip()[:len('contract')] == "contract"):
                    contractName_list.append(i)
            # print(contractName_list)

            # vcode_list = []
            str_split = ''
            for contractName in contractName_list:
                str_split = str_split +  contractName + '|'
            str_split = str_split[:-1]
            # print(str_split)
            vcode_list = re.split(str_split, vcode)[1:]
            # print(len(vcode_list))
            # print(vcode_list)

            # vcode_contract = {}
            # vcode_list = vcode.split('contract ')
            # # print(vcode_list[1].strip())
            # # print(vcode_list[2].strip())
            # for contractName in contractName_list:
            #     len_contractName = len(contractName)
            #     for i_code in vcode_list:
            #         if i_code.strip()[:len_contractName] == contractName:
            #             vcode_contract[contractName] = i_code

            is_US_hp = False
            for i_code in vcode_list:
                vcode = i_code

                if vcode == None:
                    continue
                # 0. 转账函数
                list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
                list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
                list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
                if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                    continue

                # pattern1: get struct name set
                struct_info_dict = {}
                list_US_1 = re.findall(pattern_1_0, vcode, flags=0)
                if (len(list_US_1) < 1):
                    continue
                # print(list_US_1)

                for each_struct_info in list_US_1:
                    if ('' != each_struct_info[0]) and (' ' != each_struct_info[0][-1]) and ('\n' != each_struct_info[0][-1]) and ('\t' != each_struct_info[0][-1]):
                        continue
                    temp_paras_list = each_struct_info[2].split(';')
                    if len(temp_paras_list) < 2:
                        continue
                    # each_struct_info[0]是key, struct定义的结构体名
                    struct_info_dict[each_struct_info[1]] = []
                    # 获取key对应的变量列表
                    for i in range(len(temp_paras_list)-1):
                        # print(temp_paras_list[i].split(' ')[-1])
                        # print(temp_paras_list,"++++++++")
                        struct_info_dict[each_struct_info[1]].append(temp_paras_list[i].split(' ')[-1])
                # print(struct_info_dict)  #因为前面排除了，所以这里的struct_info_dict一定不为空

                count_len = 0
                for v_list in struct_info_dict.values():
                    for v_para in v_list:
                        pattern_1_1 = re.compile(r'\.+'+v_para+r'\s*=\s*(.*);')
                        v_para_reValue = re.findall(pattern_1_1, vcode, flags=0)
                        if v_para_reValue != []:
                            count_len += 1
                if count_len == 0:
                    continue

                #以struct结构体定义的指针变量或指针变量数组---（一定必须）
                struct_define_para_set = set()
                for struct_name in struct_info_dict:
                    #这个模式中, 不接受mapping的定义。
                    pattern_2 = re.compile(struct_name + r'[\[\]]*\s+([^=;)\n]*);')
                    # pattern_2 = re.compile(struct_name + r'(.*)\s+([^=;)\n]*);')
                    struct_define_list = re.findall(pattern_2, vcode, flags=0)
                    # print(struct_define_list,"****")
                    if struct_define_list == []:
                        continue
                    #获取以struct类型定义的变量名或数组名
                    for struct_define in struct_define_list:
                        # if (struct_define[0][0] != '['):
                        #     continue
                        # struct_define = struct_define[1]
                        if 'memory ' in struct_define:
                            continue
                        else:
                            struct_define_para_set.add(struct_define.split()[-1])
                # print("**********",struct_define_para_set)
                if len(struct_define_para_set) == 0:
                    continue

                #pattern3: 获取声明的状态变量
                state_para_info_list = re.findall(pattern_3_0, vcode, flags=0)  #3-tuple List
                # print(state_para_info_list)
                # state_para_info_list不为空的话, 也并不意味着至少定义了一个状态变量
                if state_para_info_list == []:
                    continue
                state_para_list = []
                for state_para_info in state_para_info_list:
                    # 获取定义的变量, 每一个都对应一个列表
                    state_para_list_temp = state_para_info[2].split(';')[:-1]
                    # print("***",state_para_list_temp)
                    if state_para_list_temp != []:
                        state_para_list.append(state_para_list_temp[0].split('=')[0].strip())
                        # state_para_list.append(state_para_list_temp.split('=')[0].strip().split()[-1])

                # 如果state_para_list不为空, 其里面也包含了struct中定义的变量.
                # print(state_para_list)
                #把struct中定义的变量删除
                for v_list in struct_info_dict.values():
                    state_para_list = list(set(state_para_list).difference(set(v_list)))
                # print(state_para_list)
                #如果不存在声明的状态变量, 则该合约不是US
                if state_para_list == []:
                    continue

                # pattern4: struct之前的变量有存在于if判断中(ps: require应该也可以)
                for stateP in state_para_list:
                    pattern4_if_stateP = re.compile(r'if\s*[(]\s*(.*)'+ stateP + r'(.*)\s*[)]')
                    if_stateP_list = re.findall(pattern4_if_stateP, vcode, flags=0)
                    #只要存在即可
                    if if_stateP_list != []:
                        print(hp, ' has a high possibility to be a US hp.')
                        is_US_hp = True
                        break

                # 意味着不用遍历其他子合约了
                if is_US_hp == True:
                    break

                #转账过程中涉及到的变量
                list_transfer_send_call = []
                for tranfer_i in list_transfer_1:
                    list_transfer_send_call.append(tranfer_i[0])
                    list_transfer_send_call.append(tranfer_i[1])
                for send_i in list_send_2:
                    list_transfer_send_call.append(send_i[0])
                    list_transfer_send_call.append(send_i[1])
                for call_i in list_call_3:
                    list_transfer_send_call.append(call_i[0])
                    list_transfer_send_call.append(call_i[1])
                # print(list_transfer_send_call)

                retA = [i for i in state_para_list if i in list_transfer_send_call]
                # print(retA)
                if retA != []:
                    print(hp, ' has a high possibility to be a US hp.')
                    is_US_hp = True


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  # 行数区间[19, 185] --去掉注释--> [14, 152]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
            # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
            # if hp == r'0xad1aa68300588aa5842751ddcab2afd4a69e9016':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            US_deal(hp, vcode)



"""
# honeypots_all8tyes_truePositive.json  #0漏报, 0误报
0x01b21934ba28dfd8a22c4d21c710290500a5081f  has a high possibility to be a US hp.
0x04baddfb21723ec467e9993b715c5e0d673bac96  has a high possibility to be a US hp.
0x0d83102ec81853f3334bd2b9e9fcce7adf96ccc7  has a high possibility to be a US hp.
0x13b87fb8e6152032fd525f64f158c129a230b6ee  has a high possibility to be a US hp.
0x2075d158924f5030aece55179848c2bd7ec5833f  has a high possibility to be a US hp.
0x29d6cf436c893c7e44ea926411d5fd4dd763d9b3  has a high possibility to be a US hp.
0x2f069a1d7a052052458e8b5511e91221eb337c52  has a high possibility to be a US hp.
0x3268ecb4fcba1ca9f43da8ed05ffc80382cef1da  has a high possibility to be a US hp.
0x36f726e01cc85fdb0d998dfc442856379c569274  has a high possibility to be a US hp.
0x37541ebf8b4e25d36fbaa9b4c4eaad8c06314d6f  has a high possibility to be a US hp.
0x413c8657b6e6fa2b433db62271e662a470de4ba0  has a high possibility to be a US hp.
0x4fdc2078d8bc92e1ee594759d7362f94b60b1a3d  has a high possibility to be a US hp.
0x559be9a89db88794645abb93e3bfc1af2ee0be40  has a high possibility to be a US hp.
0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1  has a high possibility to be a US hp.
0x6324d9d0a23f5ddba165bf8cc61da455350895f2  has a high possibility to be a US hp.
0x650734bfd0465b7c6cd2932ea555e721308fd0b3  has a high possibility to be a US hp.
0x6a2e025f43ca4d0d3c61bdee85a8e37e81880528  has a high possibility to be a US hp.
0x741f1923974464efd0aa70e77800ba5d9ed18902  has a high possibility to be a US hp.
0x74808c86c6f0bc6f59a3a1430ddfcd2e29952eac  has a high possibility to be a US hp.
0x783cf9c6754bf826f1727620b4baa19714fedf8d  has a high possibility to be a US hp.
0x787b9a8978b21476abb78876f24c49c0e513065e  has a high possibility to be a US hp.
0x8685631276cfcf17a973d92f6dc11645e5158c0c  has a high possibility to be a US hp.
0x96830139e44251ddbe3d1c4c4110262b47cf6d34  has a high possibility to be a US hp.
0xad1aa68300588aa5842751ddcab2afd4a69e9016  has a high possibility to be a US hp.  #局部结构体未定义发生在modifier中
0xadccea0b14d26d786b99cf3ba3e9812cd4d23a81  has a high possibility to be a US hp.
0xb1f4ca3c6256f415e420de511504af8ea8a9c8e0  has a high possibility to be a US hp.
0xc57fc2c9fd3130933bd29f01ff940dc52bc4115b  has a high possibility to be a US hp.
0xe19ca313512e0231340e778abe7110401c737c23  has a high possibility to be a US hp.
0xe6f245bb5268b16c5d79a349ec57673e477bd015  has a high possibility to be a US hp.
0xefba96262f277cc8073da87e564955666d30a03b  has a high possibility to be a US hp.
0xf6c61cb3b0add944ac53c9c2decaf2954f0515cb  has a high possibility to be a US hp.
0xfb6e71e0800bccc0db8a9cf326fe3213ca1a0ea0  has a high possibility to be a US hp.
"""

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json #0漏报, 0误报。
0x1f7725942d18118d34621c6eb106a3f418f66710  has a high possibility to be a US hp. √
0x21feda639f23647ac4066f25caaaa4fadb9eb595  has a high possibility to be a US hp. --- √ --- 不是UC, 而是US和HSU的结合, 本质上可能更倾向于是一个US
0x652eb151869c2e8fa354f29321ba192d5d9f84dc  has a high possibility to be a US hp. √
0x656610729fc13e8283d96aa69cdf56c112222951  has a high possibility to be a US hp. √
0x94602b0e2512ddad62a935763bf1277c973b2758  has a high possibility to be a US hp. √
0x9823e4e4f4552cd84720dabbd6fb2c7b67066c6c  has a high possibility to be a US hp. √
0xd887c0197881626b3091b41354f9a99432d91aba  has a high possibility to be a US hp. --- √ --- 不是UC, 而是US和HSU的结合, 本质上可能更倾向于是一个US
0xf5b72a62d7575f3a03954d4d7de2a2701da16049  has a high possibility to be a US hp. √
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
0x37eb3cb268a0dd1bc2c383296fe34f58c5b5db8b  has a high possibility to be a US hp. √
0x8f3e10f9b0b9eebb2254fc6d6549bd7a8db9f10e  has a high possibility to be a US hp. √
0xbacff8111bb7acfff885bad82239b74bc625a699  has a high possibility to be a US hp. √
0xd1915a2bcc4b77794d64c4e483e43444193373fa  has a high possibility to be a US hp. √
0xd4342df2c7cfe5938540648582c8d222f1513c50  has a high possibility to be a US hp. √
0xf8e89d113924300b38615ceb5719709569ebec6b  has a high possibility to be a US hp. √
0xfb294324c87f57f89c37d3fce66ca6d8212562b3  has a high possibility to be a US hp. √
'''
