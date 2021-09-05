import re
from loadJson import load_json
from hp_US_sourceCode_detect import US_deal
from hp_HT_sourceCode_detect import HT_deal
from hp_BD_sourceCode_detect import BD_deal
from hp_ID_sourceCode_detect import ID_deal


pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
# pattern_exclude_noToken_1 = re.compile(r'(\s+token\s+.*)', re.IGNORECASE)  #可能并不严谨
# pattern_exclude_noToken_2 = re.compile(r'(token.*)', re.IGNORECASE)  #可能并不严谨
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

'''
获取vcode中的所有function 
'''

'''
第一类: bool判断  -----》 是不是可以延申到uint等呢？
0. 转账函数
1. bool变量 --> 须得是storage存储, 也即全局变量或者函数内用"storage"声明的变量。
2. 翻转赋值
3. bool条件判断

第二类: 非bool的条件判断
0. 转账函数
1. byte32或其他类型定义的变量, 没有初始化赋值（默认是0或者0x0）
2-0.找出形参列表
2. 变量名被重新赋值, 且只能由形参或数字来赋值。---> 得到这些变量名集合
3. if中的判断有这么几种方式: if(xxx变量名xxx) / if(xxx!变量名xxx) / if(xxx变量名==0x0xxx) / if(xxx变量名!=0x0xxx) /if(xxx变量名==0xxx) / if(xxx变量名!=0xxx)
   还有: 1) 找出function xxx(形参), 以,分隔, 形成形参列表; 2) if(xxx变量名==[^&|><\n]形参名xxx) / if(xxx变量名!=[^&|><\n]形参名xxx)
4.? 要对应吗？
'''
#隐藏状态更新的匹配 - position 1
pattern_1_0 = re.compile(r'(bool public|bool private|bool external|bool internal|bool)\s+([^=)\n]+);+')
pattern_1_1 = re.compile(r'(bool public|bool private|bool external|bool internal|bool)\s+(.+)=\s*(.*);')
# 非bool判断的匹配
#2.1 非bool变量: 下面这个产生的一个3-tuple的list, list[x][-1].strip()为变量名
# pattern2_1 = re.compile(r'([u]*int[1-9]*|string|bytes[0-9]+)\s*(constant)*\s*(public|private|internal|external)*\s+([^=)\n]+);+')  #复杂版 --- 其实也可
# pattern2_1_1 = re.compile(r'([u]*int[1-9]*|string|bytes[0-9]+)\s*(constant)*\s*(public|private|internal|external)*\s+(.+)=\s*.*;+')  #复杂版 --- 其实也可
pattern2_1 = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+([^=)\n]*);+')  #简单版 --- 其实也可
pattern2_1_1 = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+(.*)=\s*.*;+')  #简单版 --- 其实也可
# pattern_2_int = re.compile(r'([u]*int[1-9]+)\s*(public|private|internal|external)*\s+([^=\n]*);+')  #str = 'uint8 pulivat;'
# pattern_2_string = re.compile(r'(string)\s*(public|private|internal|external)*\s+([^=\n]*);+')   #str = "string public question;"
# pattern_2_bytes = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+([^=\n]*);+')  #bytes32 responseHash;

#2.temp 形参列表: （不用考虑constructor）
pattern2_temp = re.compile(r'function [^()\n]*[(]([^()\n]*)[)].*')

# position 3 --- 必要的(之一)
pattern_0_transfer_1 = re.compile(r'[.]+transfer[(]+(.*)[)]+')
pattern_0_send_2 = re.compile(r'[.]+send[(]+(.*)[)]+')
pattern_0_call_3 = re.compile(r'[.]+call[.]+value[(]+(.*)[)]+[(]+[)]+')
#position3

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

    if rows_len > 100:
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

    pattern_msg_value_0 = re.compile(r'(msg.value\s*[>\|<\|==]+.*)')
    pattern_msg_value_1 = re.compile(r'([+\|+=\|=]+\s*msg.value.*)')
    result_msg_value_0 = re.findall(pattern_msg_value_0, vcode, 0)
    result_msg_value_1 = re.findall(pattern_msg_value_1, vcode, 0)
    if (result_msg_value_0 == []) and (result_msg_value_1 == []):
        print("************",hp, "**************")
        return 0

    return vcode

# 这个函数一定要放在马上要判定hp为HSU之前。
def SMC_dependOnHSU(hp, vcode):
    is_SMC_hp = False
    # *****************************SMC*********************************
    '''
    1) 获取智能合约的名称 contract_name
    2) 定义模板+获取结果 pattern_SMC = re.compile(r'\s*=\s*' + contract_name + r'(.*);')
    3) 定义模板找到当前的function pattern_smcFunc = re.compile(re'function [^}]*'+2)模板处获取到的结果)
    '''
    SMC_pattern_contractName = re.compile(r'(.*)contract\s+(.*)')
    contractNameList = re.findall(SMC_pattern_contractName, vcode, flags=0)
    # print(contractNameList, "******contractNameList****")
    contractNameList_temp = contractNameList.copy()
    for contract_name_temp in contractNameList_temp:
        if contract_name_temp[0] != '':
            contractNameList.remove(contract_name_temp)
    if len(contractNameList) >= 2:
        for contract_name in contractNameList:
            contract_name = contract_name[-1].split('{')[0].strip()
            SMC_pattern_initLog = re.compile(r'\s*=\s*' + contract_name + r'[(](.*)[)];')
            initLog_list = re.findall(SMC_pattern_initLog, vcode, flags=0)
            # print(initLog_list)
            if initLog_list != []:
                for initLog in initLog_list:
                    # print(initLog)
                    # pattern_smcFunc = re.compile(r'[^}]* function .*[(].*\s*address (.*)\s*.*[)]([\s\S]*?)'+initLog)
                    pattern_smcFunc = re.compile(r'[^}]* function .*[(].*\s*(address ' + initLog + ')\s*.*[)]')
                    # pattern_smcFunc = re.compile(r'function ([\s\S]*?)'+initLog)
                    smcFunc_list = re.findall(pattern_smcFunc, vcode, flags=0)
                    # print(smcFunc_list)
                    if smcFunc_list != []:
                        print(hp, ' has a high possibility to be a SMC (depended on HSU) hp.')
                        is_SMC_hp = True
    return is_SMC_hp
    # **************************************************************

def HSU_deal(hp, vcode):
    is_HSU_hp = False
    is_SMC_hp = False

    # 0. 转账函数
    list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
    list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
    list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
    if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
        # continue
        return is_HSU_hp, is_SMC_hp

    # boolJ
    is_HSU_hp, is_SMC_hp = boolJ_deal(hp,vcode)
    if (is_HSU_hp == False) and (is_SMC_hp == False):
        # nonBoolJ
        is_HSU_hp, is_SMC_hp = nonBoolJ_deal(hp,vcode)

    return is_HSU_hp, is_SMC_hp


# 注意: HSU中该函数的返回值 与 其他文件中定义的同名函数不太一样。这里返回的是一个2-tuple list.
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


def boolJ_deal(hp, vcode):
    is_boolJ_HSU_hp = False
    is_SMC_hp = False
    bool_hp_judge_over = False

    # 1. 重新获取bool变量
    # # 1-0. 进一步删除注释
    # pattern_with_comment = re.compile(r'(//.*)')
    # with_comment_re = re.findall(pattern_with_comment, vcode, flags=0)
    # for i in with_comment_re:
    #     vcode = vcode.replace(i, '')
    # 1-1. 在无注释的代码中, 按function 划分(这样会导致不能考虑fallback) --- 按function划分！
    function_code_list = function_or_modifier_split(vcode, 'function')
    function_code_list += function_or_modifier_split(vcode, 'modifier ')
    other_code_list = function_or_modifier_split(vcode, 'event ')
    other_code_list += function_or_modifier_split(vcode, 'struct ')
    # other_code_list += function_or_modifier_split(vcode, 'mapping ')

    # print(hp,"function_code_list, bool: ", function_code_list)  # 2-tuple List

    global_var_code = vcode
    for function_code in function_code_list:
        # global_var_code = global_var_code.replace(function_code[0], '')
        global_var_code = global_var_code.replace(function_code[0]+function_code[1], '')
    for other_code in other_code_list:
        global_var_code = global_var_code.replace(other_code[0] + other_code[1], '')
    # print("gggggggg",global_var_code)

    # 1. bool变量
    list_bool_0 = re.findall(pattern_1_0, global_var_code, flags=0)
    list_bool_1 = re.findall(pattern_1_1, global_var_code, flags=0)
    if (len(list_bool_0) < 1) and (len(list_bool_1) < 1):
        # continue
        return is_boolJ_HSU_hp, is_SMC_hp

    # 从匹配到的列表中提取定义的bool变量名
    false_define_list = []
    true_define_list = []
    for bool_0 in list_bool_0:
        false_define_list.append(bool_0[1].strip())
    for bool_1 in list_bool_1:
        if (bool_1[2].strip() == 'false') or (bool_1[2].strip() == '0'):
            false_define_list.append(bool_1[1].strip())
        elif (bool_1[2].strip() == 'true') or (bool_1[2].strip() == '1'):
            true_define_list.append(bool_1[1].strip())
    if (len(false_define_list) < 1) and (len(true_define_list) < 1):
        # continue
        return is_boolJ_HSU_hp, is_SMC_hp

    # print(false_define_list)
    # print(true_define_list)

    for false_define_bool in false_define_list:
        # 2. bool变量反转赋值
        if (')' in false_define_bool) or ('(' in false_define_bool) or ('=>' in false_define_bool):
            continue
        if bool_hp_judge_over == False:
            # print('false_define_bool is: ', false_define_bool)
            pattern_2_for_true = re.compile(false_define_bool + r'\s*=\s*(true|1);')
            list_vert_for_true = re.findall(pattern_2_for_true, vcode, flags=0)
            # 3. bool条件判断
            if len(list_vert_for_true) != 0:
                # print(false_define_bool)
                # pattern_3_falseBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)' + false_define_bool + r'(.*)\s*[)]') #可的
                pattern_3_falseBool_judge = re.compile(r'(if|require)\s*[(]+\s*(.*)' + false_define_bool + r'([^}\n]*)\s*[)]+([^}]*)[}]+') #改造开始
                list_falseBool_judge = re.findall(pattern_3_falseBool_judge, vcode, flags=0)
                # print("*0**********************************")
                # print("*1**********************************")
                if len(list_falseBool_judge) != 0:
                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                    if is_SMC_hp == False:
                        for judge_part_i in list_falseBool_judge:
                            if judge_part_i[-1] == '':
                                continue
                            #  转账函数
                            list_transfer_1 = re.findall(pattern_0_transfer_1, judge_part_i[-1], flags=0)
                            list_send_2 = re.findall(pattern_0_send_2, judge_part_i[-1], flags=0)
                            list_call_3 = re.findall(pattern_0_call_3, judge_part_i[-1], flags=0)
                            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                                continue
                                # return is_HSU_hp, is_SMC_hp
                            # print("**********************************1")
                            is_boolJ_HSU_hp = True
                            print(hp, ' has a high possibility to be a HSU (bool judge) hp.')
                    # 不论判断为是SMC, 还是HSU,都意味着判断结束了。
                    bool_hp_judge_over = True
                    # return
    if (bool_hp_judge_over == False) and (is_SMC_hp == False):  # and后的判断不起作用
        for true_define_bool in true_define_list:
            if (')' in true_define_bool) or ('(' in true_define_bool):
                continue
            pattern_2_for_false = re.compile(true_define_bool + r'\s*=\s*(false|0);')
            list_vert_for_false = re.findall(pattern_2_for_false, vcode, flags=0)
            # bool条件判断
            if len(list_vert_for_false) != 0:
                pattern_3_trueBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)' + true_define_bool + r'([^}\n]*)\s*[)]+([^}]*)[}]+')
                list_trueBool_judge = re.findall(pattern_3_trueBool_judge, vcode, flags=0)
                # print(list_trueBool_judge)
                if len(list_trueBool_judge) != 0:
                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                    if is_SMC_hp == False:
                        for judge_part_i in list_trueBool_judge:
                            if judge_part_i[-1] == '':
                                continue
                            #  转账函数
                            list_transfer_1 = re.findall(pattern_0_transfer_1, judge_part_i[-1], flags=0)
                            list_send_2 = re.findall(pattern_0_send_2, judge_part_i[-1], flags=0)
                            list_call_3 = re.findall(pattern_0_call_3, judge_part_i[-1], flags=0)
                            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                                continue
                                # return is_HSU_hp, is_SMC_hp
                            # print("**********************************1")
                            print(hp, ' has a high possibility to be a HSU (bool judge) hp.')
                            is_boolJ_HSU_hp = True


    return is_boolJ_HSU_hp, is_SMC_hp


def nonBoolJ_deal(hp, vcode):
    is_nonBoolJ_HSU_hp = False
    is_SMC_hp = False
    nonBool_hp_judge_over = False

    function_code_list = function_or_modifier_split(vcode, 'function')
    function_code_list += function_or_modifier_split(vcode, 'modifier ')
    other_code_list = function_or_modifier_split(vcode, 'event ')
    other_code_list += function_or_modifier_split(vcode, 'struct ')
    # other_code_list += function_or_modifier_split(vcode, 'mapping ')

    # print(hp,"function_code_list, bool: ", function_code_list)  # 2-tuple List

    global_var_code = vcode
    for function_code in function_code_list:
        # global_var_code = global_var_code.replace(function_code[0], '')
        global_var_code = global_var_code.replace(function_code[0] + function_code[1], '')
    for other_code in other_code_list:
        global_var_code = global_var_code.replace(other_code[0] + other_code[1], '')

    # 2.1 非bool型的全局变量
    list_NonBool_0 = re.findall(pattern2_1, global_var_code, flags=0)
    list_NonBool_1 = re.findall(pattern2_1_1, global_var_code, flags=0)
    list_NonBool = list_NonBool_0 + list_NonBool_1
    # print(list_NonBool)
    if list_NonBool == []:
        # continue
        return is_nonBoolJ_HSU_hp, is_SMC_hp


    nonBool_reValue_set = set()  # 记录被重新赋值过的变量名。
    # 2.temp 获取形参集合 - 每一个函数都有各自的形参集合
    form_parameters_set = set()  #所有函数的形参列表
    for each_func_code in function_code_list:
        if 'onlyOwner' in each_func_code[0]:
            continue

        # each_func_code[0]中存放的是形参信息
        function_para_list = each_func_code[0].split(')')[0].split(',')
        for func_para in function_para_list:  # ['string _question', 'string _response']
            type_para_list = func_para.split()  # ['string', '_question']
            if type_para_list != []:  # ---> '_question'
                form_parameters_set.add(type_para_list[-1])  # 扩展形参列表 -- 一个函数的形参列表。
        # print("****", form_parameters_set)


        # 2.3 变量名被重新赋值, 且只能由形参或数字来赋值。  #这里出现了一个问题，之前是0的, 就不能用0来赋值了  #被重新赋值的时候, 如果在onlyOwner的函数里赋值也太明显了
        for nonBool_var in list_NonBool:
            nonBool_var = nonBool_var[-1]  # 变量名（非形参）
            if ('(' in nonBool_var) or (')' in nonBool_var) or ('=>' in nonBool_var):
                continue
            # # *************************************************
            # # 遍历形参列表
            # for form_p in form_parameters_set:
            #     # vcode = 'question = 0;'
            #     # print(hp, nonBool_var, form_p)
            #     # pattern2_3 = re.compile(r'('+nonBool_var + r')\s*=\s*('+form_p+ r'|[0-9]+);')
            #     # pattern2_3 = re.compile(r'(.*'+nonBool_var + r')\s*=\s*('+form_p+ r'|[1-9]+);') ###
            #     # pattern2_3 = re.compile(r'(function [^}]*' + nonBool_var + r')\s*=\s*(' + form_p + r'|[1-9]+);')  # 2-tuple List #原本是可以的,但是有一个漏报0xb620cee6b52f96f3c6b253e6eea556aa2d214a99
            #     # 这样定义重新赋值（可以通过任意形式重新赋值）, 由于[^}]*的阻挡, 可能会产生漏报的。
            #     pattern2_3 = re.compile(r'(function [^}]*' + nonBool_var + r')\s*=\s*(.*);')  # 2-tuple List  #[^}]*好像写的不太好
            #     nonBool_reValue_L = re.findall(pattern2_3, vcode, flags=0)
            #     # print(nonBool_reValue_L,"*****", hp)   #2-tuple list
            #     for nonBool_reValue in nonBool_reValue_L:
            #         if 'onlyOwner' in nonBool_reValue[0]:
            #             continue
            #         if (nonBool_var != nonBool_reValue[0][-len(nonBool_var):]) and ((' ' != nonBool_reValue[0][-len(nonBool_var) - 1]) or \
            #                     ('\t' != nonBool_reValue[0][-len(nonBool_var) - 1]) or ('\n' != nonBool_reValue[0][-len(nonBool_var) - 1])):
            #             continue
            #         # if (len(nonBool_reValue[0].strip(nonBool_var)) != 0) and (nonBool_reValue[0].strip(nonBool_var)[-1] != ' '): #str
            #         #     continue
            #         nonBool_reValue = nonBool_var  # or nonBool_reValue[0].strip()
            #         nonBool_reValue_set.add(nonBool_reValue)
            # # *************************************************
            # pattern2_3 = re.compile(r'(function [^}]*\s+' + nonBool_var + r')\s*=\s*(.*);')  # 2-tuple List  #[^}]*好像写的不太好
            pattern2_3 = re.compile(r'(.*' + nonBool_var + r')\s*=\s*(.*);')  # 不在前面写\s+的原因是有可能有顶格写, 或者\n\t变量名
            nonBool_reValue_L = re.findall(pattern2_3, each_func_code[1], flags=0)
            # print(nonBool_reValue_L,"*****", hp)   #2-tuple list
            for nonBool_reValue in nonBool_reValue_L:
                if (nonBool_var != nonBool_reValue[0][-len(nonBool_var):]) and ((' ' != nonBool_reValue[0][-len(nonBool_var) - 1]) or \
                        ('\t' != nonBool_reValue[0][-len(nonBool_var) - 1]) or ('\n' != nonBool_reValue[0][-len(nonBool_var) - 1])):
                    continue
                # if (len(nonBool_reValue[0].strip(nonBool_var)) != 0) and (nonBool_reValue[0].strip(nonBool_var)[-1] != ' '): #str
                #     continue
                nonBool_reValue = nonBool_var  # or nonBool_reValue[0].strip()
                nonBool_reValue_set.add(nonBool_reValue)

    # print(nonBool_reValue_set)
    # 一定要有变量名被重新赋值
    if (len(nonBool_reValue_set) == 0):
        # continue
        return is_nonBoolJ_HSU_hp, is_SMC_hp

    # 2.4 if判断
    for nonBool_reV in nonBool_reValue_set:
        # if(xxx变量名xxx) / if(xxx!变量名xxx) / if(xxx变量名==0x0xxx) / if(xxx变量名!=0x0xxx) /if(xxx变量名==0xxx) / if(xxx变量名!=0xxx)
        # pattern2_4_0 = re.compile(r'(//)*\s*if\s*[(]([^!\n]*)(!)*\s*('+nonBool_reV+r')\s*(.*)[)]')   # if(responseHash)
        # pattern2_4_0 = re.compile(r'(//)*\s*(if|require)\s*[(]([^!\n]*)(!)*\s*(' + nonBool_reV + r')\s*(.*)[)]')  # if(responseHash)  #可的
        pattern2_4_0 = re.compile(r'(//)*\s*(if|require)\s*[(]([^!\n]*)(!)*\s*(' + nonBool_reV + r')\s*([^}\n]*)[)]+([^}]*)[}]+')  # if(responseHash)  # 改造开始
        # pattern2_4_1 = re.compile(r'if[(](.*)\s*'+nonBool_reV+r'(.*)[)]')  # if(!responseHash)  非判断
        # pattern2_4_2 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*(==|!=)\s*(0x0|0)(.*)[)]')  #if(responseHash==0x0)
        # pattern2_4_3 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*!=\s*(0x0)(.*)[)]')
        # pattern2_4_4 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*==\s*(0)(.*)[)]')
        # pattern2_4_5 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*!=\s*(0)(.*)[)]')

        list_if = re.findall(pattern2_4_0, vcode, flags=0)
        # print(hp, list_if)
        if list_if == []:
            continue

        for nonBool_5_tuple in list_if:
            if nonBool_5_tuple[0].strip() == '//':  #
                continue
            #
            if nonBool_5_tuple[-1] == '':
                continue
            #  转账函数
            list_transfer_1 = re.findall(pattern_0_transfer_1, nonBool_5_tuple[-1], flags=0)
            list_send_2 = re.findall(pattern_0_send_2, nonBool_5_tuple[-1], flags=0)
            list_call_3 = re.findall(pattern_0_call_3, nonBool_5_tuple[-1], flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue
                # return is_HSU_hp, is_SMC_hp
                # print("**********************************1")
            if nonBool_5_tuple[3].strip() == '!':  # 非判断
                is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                if is_SMC_hp == False:
                    print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                    is_nonBoolJ_HSU_hp = True
                # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                nonBool_hp_judge_over = True
                # print(hp, ' has a high possibility to be a HSU hp.')
                # hp_nonBool_set.add(hp)
            elif ((nonBool_hp_judge_over == False) and ((nonBool_5_tuple[5].strip() == '') or (nonBool_5_tuple[5].strip()[0] == '&') or (nonBool_5_tuple[5].strip()[0] == '|'))):
                # 是判断
                if ((nonBool_5_tuple[2].strip() == '') or (nonBool_5_tuple[2].strip()[-1] == '&') or (
                        nonBool_5_tuple[2].strip()[-1] == '|')):
                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                    if is_SMC_hp == False:
                        print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                        is_nonBoolJ_HSU_hp = True
                    # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                    nonBool_hp_judge_over = True
                    # print(hp, ' has a high possibility to be a HSU hp.-----')
                    # hp_nonBool_set.add(hp)
                # 比较判断
                if (nonBool_hp_judge_over == False) and ((nonBool_5_tuple[2].strip()[-1] == '=') or \
                    (nonBool_5_tuple[2].strip()[-1] == '>') or (nonBool_5_tuple[2].strip()[-1] == '<')):
                    nonBool_5_tuple_1 = nonBool_5_tuple[2].split('&')[-1].split('|')[-1]
                    for form_p in form_parameters_set:
                        if form_p in nonBool_5_tuple_1:
                            is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                            if is_SMC_hp == False:
                                print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                                is_nonBoolJ_HSU_hp = True
                            # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                            nonBool_hp_judge_over = True
                            break
                            # print(hp, ' has a high possibility to be a HSU hp.')
                            # hp_nonBool_set.add(hp)
            elif (nonBool_hp_judge_over == False) and ((nonBool_5_tuple[5].strip()[0] == '=') or (nonBool_5_tuple[5].strip()[0] == '!') or \
                    (nonBool_5_tuple[5].strip()[0] == '>') or (nonBool_5_tuple[5].strip()[0] == '<')):
                # 比较判断
                # print("+++++++++++")
                # print(nonBool_4_tuple[3])
                nonBool_5_tuple_4 = nonBool_5_tuple[5].split('&')[0].split('|')[0]
                # print("*****")
                # print(nonBool_4_tuple_3)
                for form_p in form_parameters_set:
                    if form_p in nonBool_5_tuple_4:
                        is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                        if is_SMC_hp == False:
                            print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                            is_nonBoolJ_HSU_hp = True
                        # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                        nonBool_hp_judge_over = True
                        break
                        # print(hp, ' has a high possibility to be a HSU hp.')
                        # hp_nonBool_set.add(hp)

            if nonBool_hp_judge_over == True:
                return is_nonBoolJ_HSU_hp, is_SMC_hp

    return is_nonBoolJ_HSU_hp, is_SMC_hp


def bool_judge():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)

    hp_bool_list = []
    for hp, vcode in hp_dict.items():
            # if hp == r'0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710':
            # if hp == r'0xbe4041d55db380c5ae9d4a9b9703f1ed4e7e3888':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            if HT_deal(hp, vcode) == True:
                continue

            if US_deal(hp, vcode) == True:
                continue

            if BD_deal(hp, vcode) == True:
                continue

            if ID_deal(hp, vcode) == True:
                continue

            # 0. 转账函数
            list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            # 1. 重新获取bool变量
            # 1-0. 进一步删除注释
            pattern_with_comment = re.compile(r'(//.*)')
            with_comment_re = re.findall(pattern_with_comment, vcode, flags=0)
            for i in with_comment_re:
                vcode = vcode.replace(i, '')
            # 1-1. 在无注释的代码中, 按function 划分
            vcode_split_by_Function_list = vcode.split('function ')
            # print(vcode_split_by_Function_list)
            function_code_list = []
            for i in vcode_split_by_Function_list[1:]:
                # if (i.strip(' ')[-1] != '\n'):
                # 大括号或说花括号没太有可能成为智能合约中使用的字符
                left_BigBucket_indexs = [i.start() for i in re.finditer('{', i)]
                # print(left_BigBucket_indexs, hp, "*********")
                right_BigBucket_indexs = [i.start() for i in re.finditer('}', i)]
                # print(right_BigBucket_indexs)
                # 这里可以有多种不同的判断方式
                left_index = left_BigBucket_indexs[0]
                right_index = -1
                merge_l_r_list = left_BigBucket_indexs + right_BigBucket_indexs
                merge_l_r_list.sort()
                # match_l_r = {}
                while merge_l_r_list:
                    for index in range(len(merge_l_r_list)):
                        if merge_l_r_list[index] in right_BigBucket_indexs:
                            if merge_l_r_list[index-1] == left_index:
                                right_index = merge_l_r_list[index]
                            merge_l_r_list.pop(index)
                            if merge_l_r_list != []:
                                merge_l_r_list.pop(index-1)
                            break
                    if right_index != -1:
                        break
                # print(left_index, right_index)
                function_code_list.append(i[left_index:right_index])
            # print(function_code_list)

            global_var_code = vcode
            for function_code in function_code_list:
                global_var_code = global_var_code.replace(function_code, '')
            # print(global_var_code)

            # 1. bool变量
            list_bool_0 = re.findall(pattern_1_0, global_var_code, flags=0)
            list_bool_1 = re.findall(pattern_1_1, global_var_code, flags=0)
            if (len(list_bool_0) < 1) and (len(list_bool_1) < 1):
                continue

            #从匹配到的列表中提取定义的bool变量名
            false_define_list = []
            true_define_list = []
            for bool_0 in list_bool_0:
                false_define_list.append(bool_0[1].strip())
            for bool_1 in list_bool_1:
                if (bool_1[2].strip() == 'false') or (bool_1[2].strip() == '0'):
                    false_define_list.append(bool_1[1].strip())
                elif (bool_1[2].strip() == 'true') or (bool_1[2].strip() == '1'):
                    true_define_list.append(bool_1[1].strip())
            if (len(false_define_list) < 1) and (len(true_define_list) < 1):
                continue

            # print(false_define_list)
            # print(true_define_list)


            bool_hp_judge_over = False
            is_SMC_hp = False
            for false_define_bool in false_define_list:
                # 2. bool变量反转赋值
                if (')' in false_define_bool) or ('(' in false_define_bool) :
                    continue
                if bool_hp_judge_over == False:
                    pattern_2_for_true = re.compile(false_define_bool + r'\s*=\s*(true|1);')
                    list_vert_for_true = re.findall(pattern_2_for_true, vcode, flags=0)
                    # 3. bool条件判断
                    if len(list_vert_for_true) != 0:
                        pattern_3_falseBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)'+ false_define_bool + r'(.*)\s*[)]')
                        list_falseBool_judge = re.findall(pattern_3_falseBool_judge, vcode, flags=0)
                        # print(list_falseBool_judge)
                        if len(list_falseBool_judge)!=0:
                            # *****************************SMC*********************************
                            # '''
                            # 1) 获取智能合约的名称 contract_name
                            # 2) 定义模板+获取结果 pattern_SMC = re.compile(r'\s*=\s*' + contract_name + r'(.*);')
                            # 3) 定义模板找到当前的function pattern_smcFunc = re.compile(re'function [^}]*'+2)模板处获取到的结果)
                            # '''
                            # SMC_pattern_contractName = re.compile(r'\s*contract\s*(.*)')
                            # contractNameList = re.findall(SMC_pattern_contractName, vcode, flags=0)
                            # print(contractNameList,"**********")
                            # if len(contractNameList) >= 2:
                            #     for contract_name in contractNameList:
                            #         SMC_pattern_initLog = re.compile(r'\s*=\s*' + contract_name + r'[(](.*)[)];')
                            #         initLog_list = re.findall(SMC_pattern_initLog, vcode, flags=0)
                            #         # print(initLog_list)
                            #         if initLog_list != []:
                            #             for initLog in initLog_list:
                            #                 # print(initLog)
                            #                 # pattern_smcFunc = re.compile(r'[^}]* function .*[(].*\s*address (.*)\s*.*[)]([\s\S]*?)'+initLog)
                            #                 pattern_smcFunc = re.compile(r'[^}]* function .*[(].*\s*(address '+initLog+')\s*.*[)]')
                            #                 # pattern_smcFunc = re.compile(r'function ([\s\S]*?)'+initLog)
                            #                 smcFunc_list = re.findall(pattern_smcFunc, vcode, flags=0)
                            #                 # print(smcFunc_list)
                            #                 if smcFunc_list != []:
                            #                     print(hp, ' has a high possibility to be a SMC (depended on HSU) hp.')
                            # **************************************************************
                            is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                            if is_SMC_hp == False:
                                print(hp, ' has a high possibility to be a HSU hp.')
                                hp_bool_list.append(hp)
                            # 不论判断为是SMC, 还是HSU,都意味着判断结束了。
                            bool_hp_judge_over = True
                            # return
            if (bool_hp_judge_over == False) and (is_SMC_hp == False): # and后的判断不起作用
                for true_define_bool in true_define_list:
                    if (')' in true_define_bool) or ('(' in true_define_bool):
                        continue
                    pattern_2_for_false = re.compile(true_define_bool + r'\s*=\s*(false|0);')
                    list_vert_for_false = re.findall(pattern_2_for_false, vcode, flags=0)
                    # bool条件判断
                    if len(list_vert_for_false) != 0:
                        pattern_3_trueBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)' + true_define_bool + r'(.*)\s*[)]')
                        list_trueBool_judge = re.findall(pattern_3_trueBool_judge, vcode, flags=0)
                        # print(list_trueBool_judge)
                        if len(list_trueBool_judge) != 0:
                            is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                            if is_SMC_hp == False:
                                print(hp, ' has a high possibility to be a HSU (bool judge) hp.')
                                hp_bool_list.append(hp)
                                # return

    # hp_bool_temp_list = load_json('hp_HSU_temp_nonBool.txt')
    # ret2 = list(set(hp_bool_temp_list) - set(hp_bool_list))
    # print("*******************************")
    # print(ret2)
    #
    # ret2 = list(set(hp_bool_list) - set(hp_bool_temp_list))
    # print("*******************************")
    # print(ret2)


def NotBool_judge(hp_path, hp_nonBool_set):
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_dict = load_json(hp_8type_path)
    #
    # # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # # hp_dict = load_json(paper_new_hp_path)
    #
    # hp_nonBool_set = set()

    hp_dict = load_json(hp_path)
    for hp, vcode in hp_dict.items():
            # if hp == r'0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710':
            # if hp == r'0xb620cee6b52f96f3c6b253e6eea556aa2d214a99':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            if HT_deal(hp, vcode) == True:
                continue

            if US_deal(hp, vcode) == True:
                continue

            if BD_deal(hp, vcode) == True:
                continue

            if ID_deal(hp, vcode) == True:
                continue

            nonBool_hp_judge_over = False
            is_SMC_hp = False

            # 0. 转账函数
            list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            # 2.1 非bool变量
            list_NonBool_0 = re.findall(pattern2_1, vcode, flags=0)
            list_NonBool_1 = re.findall(pattern2_1_1, vcode, flags=0)
            list_NonBool = list_NonBool_0 + list_NonBool_1
            # print(list_NonBool)
            if list_NonBool == []:
                continue

            # 2.temp 获取形参集合
            form_parameters_set = set()
            function_args_list = re.findall(pattern2_temp, vcode, flags=0)
            # print("*******")
            print(function_args_list)
            for function_args in function_args_list:
                function_para_list = function_args.split(',')  #'string _question,string _response'
                for func_para in function_para_list:    #['string _question', 'string _response']
                    type_para_list = func_para.split()   #['string', '_question']
                    if type_para_list != []:          #---> '_question'
                        form_parameters_set.add(type_para_list[-1])  #扩展形参列表
            # print("****", form_parameters_set)

            # 2.3 变量名被重新赋值, 且只能由形参或数字来赋值。  #这个出现了一个问题，之前是0的, 就不能用0来赋值了  #被重新赋值的时候, 如果在onlyOwner的函数里赋值也太明显了
            nonBool_reValue_set = set()
            for nonBool_var in list_NonBool:
                # nonBool_var = nonBool_var[-1]  #变量名（非形参）
                nonBool_var = nonBool_var[-1].strip()  #变量名（非形参）
                # print(nonBool_var)
                # # ***********************************************************
                # # 遍历形参列表
                # for form_p in form_parameters_set:
                #     # vcode = 'question = 0;'
                #     # print(hp, nonBool_var, form_p)
                #     # pattern2_3 = re.compile(r'('+nonBool_var + r')\s*=\s*('+form_p+ r'|[0-9]+);')
                #     # pattern2_3 = re.compile(r'(.*'+nonBool_var + r')\s*=\s*('+form_p+ r'|[1-9]+);') ###
                #     # pattern2_3 = re.compile(r'(function [^}]*'+nonBool_var + r')\s*=\s*('+form_p+ r'|[1-9]+);')  #2-tuple List  #[^}]*好像写的不太好 #****也可以******
                #     # 这样定义重新赋值（可以通过任意形式重新赋值）, 由于[^}]*的阻挡, 可能会产生漏报的。
                #     pattern2_3 = re.compile(r'(function [^}]*'+nonBool_var + r')\s*=\s*(.*);')  #2-tuple List  #[^}]*好像写的不太好
                #     nonBool_reValue_L = re.findall(pattern2_3, vcode, flags=0)
                #     # print(nonBool_reValue_L,"*****", hp)   #2-tuple list
                #     for nonBool_reValue in nonBool_reValue_L:
                #         if 'onlyOwner' in nonBool_reValue[0]:
                #             continue
                #         if (nonBool_var != nonBool_reValue[0][-len(nonBool_var):]) and ((' ' != nonBool_reValue[0][-len(nonBool_var)-1]) or \
                #                 ('\t' != nonBool_reValue[0][-len(nonBool_var)-1]) or ('\n' != nonBool_reValue[0][-len(nonBool_var)-1])):
                #             continue
                #         # if (len(nonBool_reValue[0].strip(nonBool_var)) != 0) and (nonBool_reValue[0].strip(nonBool_var)[-1] != ' '): #str
                #         #     continue
                #         nonBool_reValue = nonBool_var  #or nonBool_reValue[0].strip()
                #         nonBool_reValue_set.add(nonBool_reValue)
                # # ***********************************************************
                # 这样定义重新赋值（可以通过任意形式重新赋值）, 由于[^}]*的阻挡, 可能会产生漏报的。
                pattern2_3 = re.compile(r'(function [^}]*' + nonBool_var + r')\s*=\s*(.*);')  # 2-tuple List  #[^}]*好像写的不太好
                nonBool_reValue_L = re.findall(pattern2_3, vcode, flags=0)
                # print(nonBool_reValue_L,"*****", hp)   #2-tuple list
                for nonBool_reValue in nonBool_reValue_L:
                    if 'onlyOwner' in nonBool_reValue[0]:
                        continue
                    if (nonBool_var != nonBool_reValue[0][-len(nonBool_var):]) and ((' ' != nonBool_reValue[0][-len(nonBool_var) - 1]) or \
                            ('\t' != nonBool_reValue[0][-len(nonBool_var) - 1]) or ('\n' != nonBool_reValue[0][-len(nonBool_var) - 1])):
                        continue
                    # if (len(nonBool_reValue[0].strip(nonBool_var)) != 0) and (nonBool_reValue[0].strip(nonBool_var)[-1] != ' '): #str
                    #     continue
                    nonBool_reValue = nonBool_var  # or nonBool_reValue[0].strip()
                    nonBool_reValue_set.add(nonBool_reValue)
            # print(nonBool_reValue_set)
            # 一定要有变量名被重新赋值
            if(len(nonBool_reValue_set)==0):
                continue

            # 2.4 if判断
            for nonBool_reV in nonBool_reValue_set:
                # if(xxx变量名xxx) / if(xxx!变量名xxx) / if(xxx变量名==0x0xxx) / if(xxx变量名!=0x0xxx) /if(xxx变量名==0xxx) / if(xxx变量名!=0xxx)
                # pattern2_4_0 = re.compile(r'(//)*\s*if\s*[(]([^!\n]*)(!)*\s*('+nonBool_reV+r')\s*(.*)[)]')   # if(responseHash)
                pattern2_4_0 = re.compile(r'(//)*\s*(if|require)\s*[(]([^!\n]*)(!)*\s*('+nonBool_reV+r')\s*(.*)[)]')   # if(responseHash)
                # pattern2_4_1 = re.compile(r'if[(](.*)\s*'+nonBool_reV+r'(.*)[)]')  # if(!responseHash)  非判断
                # pattern2_4_2 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*(==|!=)\s*(0x0|0)(.*)[)]')  #if(responseHash==0x0)
                # pattern2_4_3 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*!=\s*(0x0)(.*)[)]')
                # pattern2_4_4 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*==\s*(0)(.*)[)]')
                # pattern2_4_5 = re.compile(r'if[(](.*)'+nonBool_reV+r'\s*!=\s*(0)(.*)[)]')

                list_if = re.findall(pattern2_4_0, vcode, flags=0)
                # print(hp, list_if)
                if list_if == []:
                    continue

                for nonBool_5_tuple in list_if:
                    if nonBool_5_tuple[0].strip() == '//':  #
                        continue
                    if nonBool_5_tuple[3].strip() == '!': #非判断
                        is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                        if is_SMC_hp == False:
                            print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                            hp_nonBool_set.add(hp)
                        # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                        nonBool_hp_judge_over = True
                        # print(hp, ' has a high possibility to be a HSU hp.')
                        # hp_nonBool_set.add(hp)
                    elif ((nonBool_hp_judge_over == False) and ((nonBool_5_tuple[5].strip() == '') or (nonBool_5_tuple[5].strip()[0] == '&') or (nonBool_5_tuple[5].strip()[0] == '|'))):
                        #是判断
                        if ((nonBool_5_tuple[2].strip() == '') or (nonBool_5_tuple[2].strip()[-1] == '&') or (nonBool_5_tuple[2].strip()[-1] == '|')):
                            is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                            if is_SMC_hp == False:
                                print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                                hp_nonBool_set.add(hp)
                            # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                            nonBool_hp_judge_over = True
                            # print(hp, ' has a high possibility to be a HSU hp.-----')
                            # hp_nonBool_set.add(hp)
                        #比较判断
                        if (nonBool_hp_judge_over == False) and ((nonBool_5_tuple[2].strip()[-1] == '=')  or \
                            (nonBool_5_tuple[2].strip()[-1] == '>') or (nonBool_5_tuple[2].strip()[-1] == '<')):
                            nonBool_5_tuple_1 = nonBool_5_tuple[2].split('&')[-1].split('|')[-1]
                            # print(nonBool_5_tuple_1,"***h*",form_parameters_set)
                            for form_p in form_parameters_set:
                                if form_p in nonBool_5_tuple_1:
                                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                                    if is_SMC_hp == False:
                                        print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                                        hp_nonBool_set.add(hp)
                                    # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                                    nonBool_hp_judge_over = True
                                    # print(hp, ' has a high possibility to be a HSU hp.')
                                    # hp_nonBool_set.add(hp)
                    elif (nonBool_hp_judge_over == False) and ((nonBool_5_tuple[5].strip()[0] == '=') or (nonBool_5_tuple[5].strip()[0] == '!') or \
                            (nonBool_5_tuple[5].strip()[0] == '>') or (nonBool_5_tuple[5].strip()[0] == '<')):
                        #比较判断
                        # print("+++++++++++")
                        # print(nonBool_4_tuple[3])
                        nonBool_5_tuple_4 = nonBool_5_tuple[5].split('&')[0].split('|')[0]
                        # print("*****")
                        # print(nonBool_4_tuple_3)
                        for form_p in form_parameters_set:
                            if form_p in nonBool_5_tuple_4:
                                is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                                if is_SMC_hp == False:
                                    print(hp, ' has a high possibility to be a HSU (non-bool judge) hp.')
                                    hp_nonBool_set.add(hp)
                                # 意思是: 不论判断为是SMC, 还是判断为HSU, 都已经确定是蜜罐了, 因此不需要后续的判断了。
                                nonBool_hp_judge_over = True
                                # print(hp, ' has a high possibility to be a HSU hp.')
                                # hp_nonBool_set.add(hp)

    print(hp_nonBool_set)
    print(len(hp_nonBool_set))  

    return hp_nonBool_set


def main_for_nonBool():
    hp_nonBool_set = set()
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    hp_nonBool_set = NotBool_judge(hp_8type_path, hp_nonBool_set)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_nonBool_set = NotBool_judge(paper_new_hp_path, hp_nonBool_set)  #hp_nonBool_set是持续增加的

    # 比对的对象： hp_HSU_temp_nonBool.txt中记录了手动分析为“非bool判断” 的蜜罐地址
    with open(r'E:\PyCharm_workspace\book_deeplearning\smart-contract\etherscan_api\hp_HSU_temp_nonBool.txt') as txtF:
        temp_list = txtF.readlines()
    for i in range(len(temp_list)):
        temp_list[i] = temp_list[i].split('\n')[0]
    # print(temp_list)

    # 真的属于非bool判断的蜜罐中, 哪些没有被检测到:
    hp_nonBool_undetected_list = list(set(temp_list) - hp_nonBool_set)
    print("*************漏报******************")
    print(hp_nonBool_undetected_list)
    print(len(hp_nonBool_undetected_list))

    # 误报了多少
    hp_nonBool_FalsePositive_list = list(hp_nonBool_set - set(temp_list))
    print("*************误报******************")
    print(hp_nonBool_FalsePositive_list)
    print(len(hp_nonBool_FalsePositive_list))
    for i in hp_nonBool_FalsePositive_list:
        print(i)

    # 计算一下误报的与bool判断蜜罐的重合度.
    with open(r'E:\PyCharm_workspace\book_deeplearning\smart-contract\etherscan_api\hp_HSU_temp_bool.txt') as txtF:
        temp_bool_list = txtF.readlines()
    for i in range(len(temp_bool_list)):
        temp_bool_list[i] = temp_bool_list[i].split('\n')[0]
    # ret3表示为: 减去重合部分的剩余误报(重合指:与“bool判断”类蜜罐地址列表的重合)
    ret3 = list(set(hp_nonBool_FalsePositive_list) - set(temp_bool_list))
    print(ret3)
    print(len(ret3))


def main():
    hp_nonBool_set = set()
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_nonBool_set = NotBool_judge(hp_8type_path, hp_nonBool_set)
    print(hp_nonBool_set)

    # bool_judge()


if __name__ == '__main__':
    # main_for_nonBool()

    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  # 行数区间[19, 185] --去掉注释--> [14, 152]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_dict = load_json(hp_8type_path)
    #
    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    # hp_dict = load_json(paper_new_hp_path)
    for hp, vcode in hp_dict.items():
        # if hp == r'0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710':
        # if hp == r'0xdd17afae8a3dd1936d1113998900447ab9aa9bc0':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            if HT_deal(hp, vcode) == True:
                continue

            if US_deal(hp, vcode) == True:
                continue

            if BD_deal(hp, vcode) == True:
                continue

            if ID_deal(hp, vcode) == True:
                continue

            HSU_deal(hp, vcode)


#bool判断: 0漏报, 0误报, 其中有13个蜜罐是HSU bool的条件判断和其他蜜罐类型的功能结合。
'''
# honeypots_all8tyes_truePositive.json
0x0595d187cac88f04466371eff3a6b6d1b12fb013  has a high possibility to be a HSU hp. √
0x062e659a3c8991bc1739e72c68edb9ac7b5a8ca7  has a high possibility to be a HSU hp. √
0x0cfa149c0a843e1f8d9bc5c6e6bebf901845cebe  has a high possibility to be a HSU hp. √
0x0e8f2803fa16492b948bc470c69e99460942db2b  has a high possibility to be a HSU hp. √
0x11f4306f9812b80e75c1411c1cf296b04917b2f0  has a high possibility to be a HSU hp. √
0x13c547ff0888a0a876e6f1304eaefe9e6e06fc4b  has a high possibility to be a HSU hp. √
0x197803b104641fbf6e206a425d9dc35dadc4f62f  has a high possibility to be a HSU hp. √
0x1dabd43e0f8a684a02712bcd767056e25026061c  has a high possibility to be a HSU hp. √
0x24cad91c063686c49f2ef26a24bf80329fb131c7  has a high possibility to be a HSU hp. √
0x2634baad203cba4aa4114c132b2e50a3a6027ff9  has a high possibility to be a HSU hp. √
0x265c91539255a96e1005a0fd11ca776c183d04f5  has a high possibility to be a HSU hp. √
0x26ae986bfab33f4cbadec30ea55b5eed9e883ecf  has a high possibility to be a HSU hp. √
0x2b98b39d39914b3aad05dd06a46868507156400d  has a high possibility to be a HSU hp.  ---- 非bool判断和bool判断的结合
0x2cc8e271f11934f5fa15942dfda2b59432c2e0f3  has a high possibility to be a HSU hp. √
0x2e4eb4585cb949e53212e796cef13d562c24374b  has a high possibility to be a HSU hp. √
0x2fe321bbb468d71cc392dd95082efef181df2038  has a high possibility to be a HSU hp. √
0x34bc4f174c027a68f94a7ea6a3b4930e0211b19d  has a high possibility to be a HSU hp. √
0x3597f78c7872db259ce023acc34511c7a79f42e3  has a high possibility to be a HSU hp. √
0x377f64e05c29309c8527022dbe5fbbfa8e40f6dd  has a high possibility to be a HSU hp. √
0x3c3f481950fa627bb9f39a04bccdc88f4130795b  has a high possibility to be a HSU hp. √
0x448fcea60482c0ea5d02fa44648c3749c46c4a29  has a high possibility to be a HSU hp. √
0x4876bca6feab4243e4370bddc92f5a8364de9df9  has a high possibility to be a HSU hp. √
0x4d200a0a7066af311baba7a647b1cce54ae2f9a5  has a high possibility to be a HSU hp. √
0x53018f93f9240cf7e01301cdc4b3e45d25481f73  has a high possibility to be a HSU hp. √
0x57684f9059afbf7bb11b07263500292ac9d78e7b  has a high possibility to be a HSU hp. √
0x611ae0be21a9c0ab284a4a68c8c44843330072a7  has a high possibility to be a HSU hp. √
0x64669148bca4f3d1216127a46380a67b37bbf63e  has a high possibility to be a HSU hp. √
0x6594ac0a2ba54885ff7d314eb27c9694cb25698b  has a high possibility to be a HSU hp. √
0x686847351a61eb1cae8ac0efa4208ff689fd53f2  has a high possibility to be a HSU hp. √
0x68af0f18c974a9603ec863fefcebb4ceb2589070  has a high possibility to be a HSU hp. √
0x6ce3fef99a6a4a8d1cc55d980966459854b3b021  has a high possibility to be a HSU hp. √
0x6f905e47d3e6a9cc286b8250181ee5a0441acc81  has a high possibility to be a HSU hp. √
0x75041597d8f6e869092d78b9814b7bcdeeb393b4  has a high possibility to be a HSU hp. √
0x75658ed3dba1e12644d2cd9272ba9ee888f4c417  has a high possibility to be a HSU hp. √
0x7b3c3a05fcbf18db060ef29250769cee961d75ac  has a high possibility to be a HSU hp. √
0x7fefc8bf6e44784ed016d08557e209169095f0f3  has a high possibility to be a HSU hp. √
0x7ffc2bd9431b059c509b45b33e77852d47de827d  has a high possibility to be a HSU hp. √
0x8bbf2d91e3c601df2c71c4ee98e87351922f8aa7  has a high possibility to be a HSU hp. √
0x8bce9d720745b93c58c505fc0d842a7d9cd59697  has a high possibility to be a HSU hp. √
0x8d056569b215c8b56e4b3a615dac425d8d2352a4  has a high possibility to be a HSU hp. √
0x8d4eb49f0ed7ee6d6e00fc76ea3e9c3898bf219d  has a high possibility to be a HSU hp. √
0x930dfbdc5e9f1984a8d87de29d6a79fbb2bb7b32  has a high possibility to be a HSU hp. √
0x99bab102c0a03438bcfd70119f07ee646db26ddf  has a high possibility to be a HSU hp. √
0x9bdb9d9bd3e348d93453400e46e71dd519c60503  has a high possibility to be a HSU hp. √
0xaa3a6f5bddd02a08c8651f7e285e2bec33ea5e53  has a high possibility to be a HSU hp. √
0xaa4fd1781246f0b9a63921f7aee292311ea05bf7  has a high possibility to be a HSU hp. √
0xabcdd0dbc5ba15804f5de963bd60491e48c3ef0b  has a high possibility to be a HSU hp. √
0xaded0438139b495db87d3f70f0991336df97136f  has a high possibility to be a HSU hp. √
0xae3bf0f077ed66dda9fb1b5475942c919ef3bb0d  has a high possibility to be a HSU hp. √
0xaec8162438b83646518f3bf3a70b048979f81fab  has a high possibility to be a HSU hp. √
0xaf531dc0b3b1151af48f3d638eeb6fe6acdfd59f  has a high possibility to be a HSU hp. √
0xb38beba95e0e21a97466c452454debe2658527f7  has a high possibility to be a HSU hp. √
0xb49b1dddf1b3d6e878fd9b73874da7ab0da7e004  has a high possibility to be a HSU hp. √
0xb6f6f6f47e92e517876d30c04198f45a3bc1b281  has a high possibility to be a HSU hp. √
0xb91a6c5c6362b10db6440d690e5391bb1eabe591  has a high possibility to be a HSU hp. √
0xbae339b730cb3a58eff2f2f2fa4af579332c3e1c  has a high possibility to be a HSU hp. √
0xbc272b58e7cd0a6002c95afd1f208898d756c580  has a high possibility to be a HSU hp. √
0xbf5fb038c28df2b8821988da78c3ebdbf7aa5ac7  has a high possibility to be a HSU hp. √
0xc1d73e148590b60ce9dd42d141f9b27bbad07879  has a high possibility to be a HSU hp. √
0xc304349d7cc07407b7844d54218d29d1a449b854  has a high possibility to be a HSU hp. √
0xc5ce9c06a0caf0e4cbd90572b6550feafd69b740  has a high possibility to be a HSU hp. √
0xc6389ef3d79cf17a5d103bd0f06f83cf76b14258  has a high possibility to be a HSU hp. √
0xcb71b51d9159a49050d56516737b4b497e98bb99  has a high possibility to be a HSU hp. √
0xd0981f1e922be67f2d0bb4f0c86f98f039dd24cc  has a high possibility to be a HSU hp. √
0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710  has a high possibility to be a HSU hp. √
0xd87eaad7afb256c69526a490f402a658f12246fd  has a high possibility to be a HSU hp. √
0xd8993f49f372bb014fb088eabec95cfdc795cbf6  has a high possibility to be a HSU hp. √
0xe3b0fe57f7de3281579a504dcc3af491afbb23e5  has a high possibility to be a HSU hp. √
0xe830d955cbe549d9bcf55e3960b86ffac6ef83f1  has a high possibility to be a HSU hp. √
0xef75f477126d05519d965d116fc9606e60fc70a8  has a high possibility to be a HSU hp. √
0xefbfc3f373c9cc5c0375403177d71bcc387d3597  has a high possibility to be a HSU hp. √
0xf3f3dd2b5d9f3de1b1ceb6ad84683bf31adf29d1  has a high possibility to be a HSU hp. √
0x01f8c4e3fa3edeb29e514cba738d87ce8c091d3f  has a high possibility to be a SMC (depended on HSU) hp.
0x4320e6f8c05b27ab4707cd1f6d5ce6f3e4b3a5a1  has a high possibility to be a SMC (depended on HSU) hp.
0x4e73b32ed6c35f570686b89848e5f39f20ecc106  has a high possibility to be a SMC (depended on HSU) hp.
0x561eac93c92360949ab1f1403323e6db345cbf31  has a high possibility to be a SMC (depended on HSU) hp.
0xaae1f51cf3339f18b6d3f3bdc75a5facd744b0b8  has a high possibility to be a SMC (depended on HSU) hp.
0xbe4041d55db380c5ae9d4a9b9703f1ed4e7e3888  has a high possibility to be a SMC (depended on HSU) hp.
0xd518db222f37f9109db8e86e2789186c7e340f12  has a high possibility to be a SMC (depended on HSU) hp.
0xdd17afae8a3dd1936d1113998900447ab9aa9bc0  has a high possibility to be a SMC (depended on HSU) hp.
'''

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json
0x21feda639f23647ac4066f25caaaa4fadb9eb595  has a high possibility to be a HSU hp. ---(UC) 不是UC, 而是US和HSU的结合, 本质上可能更倾向于是一个US ---这是paper_new_honeypot判断错误
0x5dac036595568ff792f5064451b6b37e801ecab9  has a high possibility to be a HSU hp. √
0x85179ac15aa94e3ca32dd1cc04664e9bb0062115  has a high possibility to be a SMC (depended on HSU) hp.
0x90302710ae7423ca1ee64907ba82b7f6854a5ddc  has a high possibility to be a HSU hp. √
0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b  has a high possibility to be a SMC (depended on HSU) hp.
0xc710772a16fd040ed9c63de0679a57410981e3fc  has a high possibility to be a HSU hp. ----(ID) 本质上我认识还是一个bool判断条件的HSU, 不过确实也是HSU和ID的结合
0xf0cc17aa0ce1c6595e56c9c60b19c1c546ade50d  has a high possibility to be a HSU hp. ----(ID) 本质上我认识还是一个bool判断条件的HSU, 不过确实也是HSU和ID的结合
0xf5b72a62d7575f3a03954d4d7de2a2701da16049  has a high possibility to be a HSU hp. --- US和bool判断的结合, 可以有两条路径完成蜜罐功能。

#第二次：
0x1235b9042f7fe167f09450eaffdc07efcc3acb38  has a high possibility to be a ID hp.
0x1f7725942d18118d34621c6eb106a3f418f66710  has a high possibility to be a US hp.
0x21feda639f23647ac4066f25caaaa4fadb9eb595  has a high possibility to be a US hp.
0x2bb5b9f83391d4190f8b283be0170570953c5a8e  has a high possibility to be a HT hp. 742
0x31fd65340a3d272e21fd6ac995f305cc1ad5f42a  has a high possibility to be a HT hp. 742
0x33f82dfbaafb07c16e06f9f81187f78efa9d438c  has a high possibility to be a ID hp.
0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01  has a high possibility to be a ID hp.
0x4b17c05fc1566891e5a9220d22527b5aeab0e1d0  has a high possibility to be a ID hp.
0x55bec5649fbb5f5be831ee5b0f7a8a8f02b25144  has a high possibility to be a HT hp. 1218
0x5abb8dda439becbd9585d1894bd96fd702400fa2  has a high possibility to be a HT hp. 742
0x5dac036595568ff792f5064451b6b37e801ecab9  has a high possibility to be a HSU hp.                 √
0x61dc347d7fa0f6e34c3112faf83a2e468d681f68  has a high possibility to be a HT hp. 887
0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839  has a high possibility to be a ID hp.
0x652eb151869c2e8fa354f29321ba192d5d9f84dc  has a high possibility to be a US hp.
0x656610729fc13e8283d96aa69cdf56c112222951  has a high possibility to be a US hp.
0x66385555fc121d18dc95ec3a8ecd51ab2b660de5  has a high possibility to be a HT hp. 734
0x81c798ea668b6d7e07ea198014265e0c1d64b5a8  has a high possibility to be a ID hp.
0x85179ac15aa94e3ca32dd1cc04664e9bb0062115  has a high possibility to be a SMC (depended on HSU) hp.
0x8fd1e427396ddb511533cf9abdbebd0a7e08da35  has a high possibility to be a ID hp.
0x90302710ae7423ca1ee64907ba82b7f6854a5ddc  has a high possibility to be a HSU hp.                 √
0x94602b0e2512ddad62a935763bf1277c973b2758  has a high possibility to be a US hp.
0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b  has a high possibility to be a SMC (depended on HSU) hp.
0x9823e4e4f4552cd84720dabbd6fb2c7b67066c6c  has a high possibility to be a US hp.
0xb11b2fed6c9354f7aa2f658d3b4d7b31d8a13b77  has a high possibility to be a ID hp.
0xbaa3de6504690efb064420d89e871c27065cdd52  has a high possibility to be a ID hp.
0xbebbfe5b549f5db6e6c78ca97cac19d1fb03082c  has a high possibility to be a ID hp.
0xc1fbb18de504e0bba8514ff741f3109d790ed087  has a high possibility to be a HT hp. 4467
0xcfebf8c78de81f804a694f4bb401e5d76b298be5  has a high possibility to be a HT hp. 901
0xd7e3c6d99bc2ccdb6fe54b8a5888d14319e65c36  has a high possibility to be a BD hp.
0xd887c0197881626b3091b41354f9a99432d91aba  has a high possibility to be a US hp.
0xe7e25a3d83abdc4a4273792cca7865889a7b0df3  has a high possibility to be a ID hp.
0xf5b72a62d7575f3a03954d4d7de2a2701da16049  has a high possibility to be a US hp.
'''

#非bool判断: honeypots_all8tyes_truePositive.json + honeypots_paper_new_addr2SouceCode.json （一块的）
'''
# 再次误报分析 (以下仅展示误报)
0x8cc5d9de2c8df87f2d40d84aa78049ea6e61f973  √ --- 手动判断时的失误,已经纠正

#**************************************

# 初次误报分析: (以下全是误报的)
#漏报0个, 误报(47)-->46个. 其中有34个是"HSU 的 bool判断与非bool判断的结合"; 8个属于超长空格和HSU的结合;
# #4个真正的误报: 2个是US, 2个是ID.
0x8685631276cfcf17a973d92f6dc11645e5158c0c   #---- 属于US  ---- 已删除
0x68af0f18c974a9603ec863fefcebb4ceb2589070   # √ HSU 的 bool判断与非bool判断的结合
0x6594ac0a2ba54885ff7d314eb27c9694cb25698b   # √ HSU 的 bool判断与非bool判断的结合
0xcfebf8c78de81f804a694f4bb401e5d76b298be5   #---- √ 超长空格和HSU的结合
0xb38beba95e0e21a97466c452454debe2658527f7   # √ HSU 的 bool判断与非bool判断的结合
0x4876bca6feab4243e4370bddc92f5a8364de9df9   # √ HSU 的 bool判断与非bool判断的结合
0x448fcea60482c0ea5d02fa44648c3749c46c4a29
0xaded0438139b495db87d3f70f0991336df97136f
0x0e8f2803fa16492b948bc470c69e99460942db2b
0xc6389ef3d79cf17a5d103bd0f06f83cf76b14258
0xefbfc3f373c9cc5c0375403177d71bcc387d3597
0x4d200a0a7066af311baba7a647b1cce54ae2f9a5
0x656610729fc13e8283d96aa69cdf56c112222951 #----- 属于US  ---- 已删除
0xe830d955cbe549d9bcf55e3960b86ffac6ef83f1
0xb49b1dddf1b3d6e878fd9b73874da7ab0da7e004
0x5dac036595568ff792f5064451b6b37e801ecab9
0xbf5fb038c28df2b8821988da78c3ebdbf7aa5ac7
0x7fefc8bf6e44784ed016d08557e209169095f0f3
0x24cad91c063686c49f2ef26a24bf80329fb131c7
0x50abfc76b637b70571c301071f7ce660c1c3d847 #----- 属于ID(继承紊乱) --- 应该是被pass了
0xd0981f1e922be67f2d0bb4f0c86f98f039dd24cc
0x55bec5649fbb5f5be831ee5b0f7a8a8f02b25144 #----- √ 超长空格和HSU的结合
0x34bc4f174c027a68f94a7ea6a3b4930e0211b19d
0xd8993f49f372bb014fb088eabec95cfdc795cbf6
0xc1fbb18de504e0bba8514ff741f3109d790ed087 #---- √ 超长空格和HSU的结合
0x1dabd43e0f8a684a02712bcd767056e25026061c
0x61dc347d7fa0f6e34c3112faf83a2e468d681f68 #----- √ 超长空格和HSU的结合
0x98fe1d52649a3a13863647c6789f16e46e090377 #----- 属于ID(继承紊乱)  --- 被pass了
0x5abb8dda439becbd9585d1894bd96fd702400fa2 #----- √ 超长空格和HSU的结合
0x66385555fc121d18dc95ec3a8ecd51ab2b660de5 #----- √ 超长空格和HSU的结合
0x0595d187cac88f04466371eff3a6b6d1b12fb013
0x64669148bca4f3d1216127a46380a67b37bbf63e
0x0cfa149c0a843e1f8d9bc5c6e6bebf901845cebe
0x8bbf2d91e3c601df2c71c4ee98e87351922f8aa7
0x2bb5b9f83391d4190f8b283be0170570953c5a8e  #---- √ 超长空格和HSU的结合
0x7b3c3a05fcbf18db060ef29250769cee961d75ac
0x90302710ae7423ca1ee64907ba82b7f6854a5ddc
0x99bab102c0a03438bcfd70119f07ee646db26ddf
0x75041597d8f6e869092d78b9814b7bcdeeb393b4
0xf3f3dd2b5d9f3de1b1ceb6ad84683bf31adf29d1
0x8cc5d9de2c8df87f2d40d84aa78049ea6e61f973 # √ --- 手动判断时的失误,已经纠正
0x9bdb9d9bd3e348d93453400e46e71dd519c60503
0x13c547ff0888a0a876e6f1304eaefe9e6e06fc4b
0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710
0x6ce3fef99a6a4a8d1cc55d980966459854b3b021
0x3597f78c7872db259ce023acc34511c7a79f42e3
0x31fd65340a3d272e21fd6ac995f305cc1ad5f42a  #---- √ 超长空格和HSU的结合
'''


'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
NotBool_judge: 无
Bool-judge: 无    #0xf331f7887d31714dce936d9a9846e6afbe82e0a0这个地址以行数(并没有得到实际解决)或者token出局的。
'''


'''
honeypots_more13_FromXGBootst_truePositive.json
Bool-judge:
0x788dcaa03860a44a98cc64652a3d1a16fbecee9d  # √
NotBool_judge: 
无              #0x8f3e10f9b0b9eebb2254fc6d6549bd7a8db9f10e  --- 已pass
'''

'''
honeypots_paper_new_addr2SouceCode.json
0x06c2452bcb4c1c1a046c520ffbad41fb8f48442b  has a high possibility to be a HSU (non-bool judge) hp.
0x2ad6bdedf16b32a925ba293ee07f9b3c1c5ab266  has a high possibility to be a HSU (non-bool judge) hp.
0x349d9314154ef0999facdbbcea2d9737b0529570  has a high possibility to be a HSU (non-bool judge) hp.
0x3fab284a3cd0a6d88d18d0fda4bc1a76cdacd68a  has a high possibility to be a HSU (non-bool judge) hp.
0x46de9ef59a51388961bfbe45fb89bedbdfaa32ac  has a high possibility to be a HSU (non-bool judge) hp.
0x51ae2f91619246ad3a20f4e76f3323a836bde6a5  has a high possibility to be a HSU (non-bool judge) hp.
0x5b39afa22a9debd9247bf84b68a79b8736c2ba4e  has a high possibility to be a HSU (non-bool judge) hp.
0x5dac036595568ff792f5064451b6b37e801ecab9  has a high possibility to be a HSU (bool judge) hp.
0x5e521b660fe8ac575f1d7201f2237724ee531f1d  has a high possibility to be a HSU (non-bool judge) hp.
0x6e6f819299e7809ce744f37fae9f84fe38d95f1c  has a high possibility to be a HSU (non-bool judge) hp.
0x6fc1ee575e9023aea1c45b4dfc9acf603ea9f63f  has a high possibility to be a HSU (non-bool judge) hp.
0x7bf5a0802a5eb74883806e60600290f53da339e1  has a high possibility to be a HSU (non-bool judge) hp.
0x7c52974b6eb8af0ddf874b3c4e03aa9a791d9632  has a high possibility to be a HSU (non-bool judge) hp.
0x90302710ae7423ca1ee64907ba82b7f6854a5ddc  has a high possibility to be a HSU (bool judge) hp.
0xaee056c6c1071512657f094af550d1af74db0622  has a high possibility to be a HSU (non-bool judge) hp.
0xcac14364754336d9759caafddef8d662dcca06a0  has a high possibility to be a HSU (non-bool judge) hp.
'''

'''
        "0x7753a9d834844cfde5c211ec3912b49f0d8b8e11", × - 没有直接左右转账指令的执行
        "0x615d2c5155ea9841f2a926c3a4953d140d407c99", × （同上）
        "0x0312855bb6e548578a36fa8de63b8f0d3d7d7dc2", × （同上）
        "0x181eec6b050ac30dff0c8b258ba0695339766734", × - 没有直接左右转账指令的执行 - 与bool判断并列
        "0xbf885158a5230dd185c9db354b1ea491c53bceb3",
        "0xced0b78dd06edfa8dcabff3782d7e159d39d71f4",
        "0x1ca4a86bba124426507d1ef67ad271cc5a02820a",
        "0x99925cc9a57f5e473ff22314cfe0627a0bfcceb4",
        "0x40360631db85eddab268dd1b6ffea4377733e125",
        "0xb56e95aea830b0242be6a5d0239ed7f71408563b",
        "0x0abce3be0075d067e12da8d266de752e20ff9842",
        "0xa1c1983aa3599657a74cf5a563e880eedc57ae4f",
        "0x75aa81161e07483f6ca199fef46c13eb13d190be",
        "0x66a8cc4cddd86a3d6ac34f553dd250983fee3fd4",
        "0xf184279e6d4654890b4410cf300ed55600f018be",
        "0x0f170120733474c6ec7daf6ae6aeeeb8b645e92c",
        "0x0763312005ddcc51f88e2518049635a1748c90a5",
        "0x1926a3254d6bb48f983d1890a993d618d1b6c9cf",
        "0x45435a8a8115603614f69526ea3a6e840cf62e04",
        "0x3e15c9eac04cbe4a191c6696982a29b62126039e",
        "0xdce94f49e659bd1335213a6e1c54d6cd171f97dd",
        "0xda922e473796bc372d4a2cb95395ed17af8b309b",
        "0x60f0ee673e413e1c134d1497eeecce8ddd2fdd74",
        "0x8b807cf49ca593c4678811211df2992e64f2f3ef",
        "0x5d39fcebe89ab0397947881539fd6dc7d99c6a87",
        "0x1b27996479b11abc8a8d0447deb3fb0183788484",
        "0xabcdd0dbc5ba15804f5de963bd60491e48c3ef0b",
        "0xf2b8e10e7b230cc55040a7a90be75c933719c507",
        "0xb78e82956b6037e13b83c287aa9047f748c0f55a",
        "0x022de2e28a61f9d197f8966dd0fc8f7ddf70f2dc",
        "0x33720000b3b3bd4b631b76f85049306be257ddc7",
        "0xe1e8eabd8fcf08ed50ae1f2ed4710c1a1f38542c",
        "0x0b983fa1bcbdf24bdbfacb660faa76c586a16c64",
        "0xe3c61a3bff7cb03ddd422258006fddd5ba1ed0fe",
        "0xe5b70a2ce2b507237baa81c98a5448431b1e8cb8",
        "0x7d01989c920ff8c45916195317381bb6a62352d1",
        "0x2a28cc275b458019910e3b8b8ee58f17eb6d38c8",
        "0xb2048d829482dbc9baf6951c28909e5c49686041",
        "0xd3f3eb105daa3712eda7709f59ac0ec0d2d202b5",
        "0xaffd8d333badb2a6dfab4854c5a30ac2dbb9db9f",
        "0x5ed5b9a13af4581524ebb7a0701bc4366d002289",
        "0xaedde4941e7eac04f97be3a89af50a454d7c5f89",
        "0xb9068705fbdc3b06c11763d2c260be682e6844ff",
        "0x3aaa5474a09804b08120e6e33bfc433367ab238c",
        "0x60b1bfaa999ab532df3ab804b43ed549a8636501",
        "0x5ae14c0101e0a40c709340592f1f1c052ef4ab92",
        "0x9bf233b2f9eea51708c0b345f28fc621f83daa78",
        "0x5dcec81f0b08229f866acd3cf814f7e0be3584e0",
        "0x6501e3e3e336cf94b6082a525792b14015672f90",
        "0x5965c4ee0e04ab0aa480527b7c91be8deca47f9c",
        "0xf1803ee1ddd9c709310e173d172673ffc9964542",
        "0x14045351539675dd455907d881ec9af4ad1b68c5",
        "0x85169e1f0d8c2f27dd44f1cfbb81172dfeafe7c1",
        "0x5a8576d31d9bf4f196bbf80f913c4ce5487b7873",
        "0x5e3741d9faa0f62660bdecdd3ac43c97c83a9881",
        "0x51dce38369b7d57d367fa1b738723a626f15b8ff",
        "0x4fd997ed7c10dbd04e95d3730cd77d79513076f2",
        "0x3cf853facae392c3e4310ab805da30a1da508609",
        "0x3ac26f27595effeb5e426bd093081ec30ebdd545",
        "0x7be89db09b0c1023fd0407b24b98810ae97f61c1",
        "0x0807a2d6a675e7196a3d9b1910700cae9795b72a",
        "0xf66ca56fc0cf7b5d9918349150026be80b327892",
        "0x362bb67f7fdbdd0dbba4bce16da6a284cf484ed6",
        "0x44e8173818a6fa6f36f2d5c385aa852703cb51b4",
        "0x999d5f024439a0ecfd554753e9e4a9eda9261b73",
        "0x065acf55df87b4bbbbf769d16b91ad706f0176dc",
        "0xf7bb54ca20962c6e513bf610657c23d82715bca2",
        "0x49e9279ddbe4c70480ebc2e3eeed3deaccf1909a",
        "0xa8855be2f7142f1485a958ca4135a7ee2752c732",
        "0xcf965cfe7c30323e9c9e41d4e398e2167506f764",
        "0x6eda6ca69d86d3207e3c26570f001309ec2f64f2",
        "0xcb9e262d909d0e94681c474da2c625801a0384b8",
        "0x68d44a267aa3c66242adf021d2d4658b6d60dd2c",
        "0xc81d7e536a613e902799af2c9955b73c94857afc",
        "0xe75509810e09b04eef4ebd0b471bacf5530b162e",
        "0x94deb5143345ec837f16d1144a2a109d648c4e2f",
        "0x67cf11dbb4bf45bf08ec4f4b9ace9983b5df1027",
        "0xfbe2fa4d1eff72d1c0e7e06ec731f44a85fc76ec",
        "0xec94d178d97bac527fdcd4b3d4bf41b57d640c5b",
        "0x3b6b74df081bc0e2c4776b3ceb3d4bc61c20ad32",
        "0xa1877c74562821ff59ffc0bc999e6a2e164f4d87",
        "0xaa14dbe6aa268662999c2bb2bc14d268c55de7f1",
        "0xca50d78b6b01f66496bf9ec61248c51647975ab4",
        "0xf74503c8d80b145d622c8f97a7ed322cbff23d61",
        "0x227c967c66aad3d4b652e9887eb95bc40fb63e6f",
        "0xb044a1f6352fadbb9cee1a499f2ccf17204f8afe",
        "0xa38d8109127028d3e1774413ef28db70c471cb54",
        "0x21c04ea21791cc35c17a0d33b083a8dcde04cc0b",
        "0xceffdb3f1aed635e94a0b565239d4353ae44c744",
        "0x6bd33d49d48f76abcd96652e5347e398aa3fda96",
        "0x8bbf2d91e3c601df2c71c4ee98e87351922f8aa7",
        "0x91aba36a26c653aba26bf768bc203254cb2bb910",
        "0xe9db9cff901ab53e869b1f8c8cceef0be60947b3",
        "0x4ade568854ed1fceeca5286ee68d17f48e7554e7",
        "0x103992432927f7ed1a5b3dc0e34186f80b16d93c",
        "0xde86f709f9001a155a4a7fd40f0f4bcdbe41b4db",
        "0x2e394f6a40bf502892a74c1f373cd36e0238785c",
        "0x59e900aa5af678550854dfb7c34b3acb6929f0e2",
        "0xed29ff5874fa64dcf47ed7dacb770857a5d164fb",
        "0x6f5c1ed62a4fa41cfc332d81fafd3cd38aacbd85",
        "0x39811d71d6d64552e532c165f37c4d09132fd4e1",
        "0x96114f9b22060e203dfb327c36bd3c1378590ef5",
        "0xca9b7047a30b48942f61a729ecb1905e4b2a98dc",
        "0x8231ce24732beeb67e99eab54accfcd9a33d96bd",
        "0xefc9815c824ce9cad76d9af87ae8480b7635079b",
        "0xf5ac04111dfecaf859071c4a424ebcda1379825b",
        "0xab50e301204aab5f0a14ad934f176e09b8216c15",
        "0xf5aca7f577de131c176d6a2069eb90b494a34fff",
        "0xce6a5b2516539aaf70d4c2969557144348895d31",
        "0x2e63cceffa42b095f0bd6d0fcadb521200b8fef5",
        "0x098af9afa803e2598bda464ea2fa0e144649f3f9",
        "0xcbce61316759d807c474441952ce41985bbc5a40",
        "0x0e9e062d7e60c8a6a406488631dae1c5f6db0e7d",
        "0xcc89405e3cfd38412093840a3ac2f851dd395dfb",
        "0x12444b6ec62e616ebc8a23e56e61f8f4c6da610c",
        "0x84e1eab8e5f8729fa93c8f68b88a2165c2534208",
        "0x403087fc37c9cd53475e77ce24071383c6ed02b6",
        "0x5cac5ac21b93095490f736205df600fb4449aee1",
        "0x3f418d108772412095c2959767ab7282971df516",
        "0x8d18fee3552179082064abc5ef0b97c529a616b0",
        "0x6085df4802721d24e39f69721b294a831cb2bd10",
        "0xabeeb06752a6da54773f00508baabb1c279f32d2",
        "0x146e59f69a68b645367bdc94f3855df0d8214f4d",
        "0x7b74e83cacf86443a1cad1152179cbeff8e25e29",
        "0x44e7786a9dd083ad147cec72cb3a5ef6b7b3f91f",
        "0x27f706edde3ad952ef647dd67e24e38cd0803dd6",
        "0x8c944c3f4029c14c22b6525ac3155482c2559541",
        "0x9922bff8380e9062eda0ad2f5712d96a88c3d0b3",
        "0x4e61ba9c25d43e802c6be8d160432e4989dea1fc",
        "0xd3e55b1c1da60e7e995e70d85c847c975fed5d37",
        "0x8e6057adfdafba64a69c53510197b6ea33367b74",
        "0x089431f295b58c17c0b1754be2e15d706e990151",
        "0x38bbe5d0926122900dd50741b051bf323cd401ae",
        "0x44f2f79343ac7244c09e0189df05588524a86515",
        "0xf0bb73649b3309b3a61b65b94eb7616967401606",
        "0xaa3f3485b5a009b34308707aa8e4c6f6c8e4dd49",
        "0x302ee98862a56ada967e7e61af3e3795d0d59712",
        "0x6fa89ed0f4c229226f94950a7e4132a9637af845",
        "0x5b399540a3cd4c6cc017bec2b9e29eb008390afc",
        "0x1556ef624b143556956055c281a08e588d422402",
        "0x4403e15053786abaef11d73f2a08a54c9f58fc34",
        "0x512238c600d187f375324936d701bace47e15d92",
        "0x386771ba5705da638d889381471ec1025a824f53",
        "0x1e0490d9515a2ef9c6e7ad8a598527b149a8e432",
        "0xafc36ac17c5d84504064f944b27292e795d03398",
        "0xa97c8e603d56d042943c5c341d83709edf749600",
        "0x94823127b7fef400be19c56d48d15a584d8dd2bb",
        "0xff4f3ab463056a5a63c0ed83ecaf57d78a2e53db",
        "0xe372dd32e141b019346f8ee8527d3049105a47b9",
        "0xf9ee6ac0e603b4d8f8a3d23c29b9bb5be84469f6",
        "0xdd607b5e9ac8ba51da2d8c99a9f69d3ba8d4846d",
        "0xb78af44145dc140749eeefe960ae9f71210621d3",
        "0x63c0f17c1f72e1315e3d4f8a89a37d95f1314793",
        "0x7e68e18fb83a8f1d092a9e4dbf36bd9dc3029ed0",
        "0xcda0f7d68eb1398d459458fa3b31751a65030e6e",
        "0x2160e6c0ae8ca7d62fe1f57fc049f8363283ff5f",
        "0xe9c417eae5e9be4a4837b844795f67f9681df69f",
        "0xfe2f0a2d25639366b19e4105068720837277e70f",
        "0x1443616b940aea9fd52add2ebdc6966a4ac5f27d",
        "0x59b8d11d50ab6615f9cd430743baf646fb8966c6",
        "0x5e7a9b977df27b80dfcb1bf015909d3a812d0556",
        "0xab1ea6360caab4825fc1a7bc4ab0fda5f484e064",
        "0x8b9c35c79af5319c70dd9a3e3850f368822ed64e",
        "0x4aeeccf1f828cf06fe302ed0c71acd65259f8c88",
        "0x82b279b585c7bb848c36f23919d68b4d0262c184",
        "0xd85f7bfd410c90ed2978cc8ef80ea1634636eb54",
        "0x33100e018d138676631542d7c6577953f721c57b",
        "0x4ab8510410a3a66b44631e403bdc1b4c799887ac",
        "0x2b6e630e79a2a01e564b800d0a12ac0d9744c775",
        "0x0f82c7eab8f7efb577a2de9d2b7e1da1d0b6870e",
        "0xd6dbdcdae636c758b7404e91e12a7cc58abb25ec",
        "0xe8205644fef286a2af423b72669e662feec127cd",
        "0x4f60d5605b4ceb8db307024eb5481af8e90ccfc7",
        "0xa9d8ac371a2d7873775697dadea9051933e241e1",
        "0x49488350b4b2ed2fd164dd0d50b00e7e3f531651",
        "0xfd3473ade3db26db08a42153bcfb64ffeb44a0c8",
        "0x22c84ba1f050f4ed6eed40d8a982340d1a5832b4",
        "0xb826e285eb1998181e11aed83b6617484d5cccaf",
        "0xb6346b0cf3925b8758b5d98cd19703d2c5239e99",
        "0xa60ea337ac5c771e4c04630e3bd052e373b40067",
        "0x0ccd5ea595a3e7537e471f40a4d90f88ed0cf5ec",
        "0x215a427c5f35c375525ecafa37c05d4b3ec9b573",
        "0xea091331357959a265b0075a3c084d7d92e2e176",
        "0xb2069ca2122e652c0f6ed4d408c915bc103e24b8",
        "0xc4524cd4ad9e5bd19a08aad023f298e21b17ea38",
        "0xee74792bd15d23a63e5357f599cbe1ec2f898bbc",
        "0x536d13e82d001c85f3fb9caaee004beaab62694f",
        "0x3686986e559f257cfaccb44f17af5b245e45814f",
        "0xafabe4280633530a015150f6acf2993112db6817",
        "0x3f17af8d4e950ecce6f24bfaf0e43a56d8fb3491",
        "0x94f211c0afa8f1ef70e1876cd3a4ff392a1d3f99",
        "0x041d26dcceda7fd82898cd7dce0ae7da6031ee51",
        "0x6959f7fa12392b93e6af39c300e67923928b184f",
        "0xc96567d557acf460c59cb2816f3ff65b907fde89",
        "0xa03739a3bf5cecd871121f488e27a79c98bb00f9",
        "0xc1d845de55dd6c88da2098a6be7042769bf29574",
        "0xceb279c001177101d4736d1fb2ba6133d0ea9fde",
        "0x2c39f92294f436c956f12dcd801a3181e77f8851",
        "0x7c48c6bf45510e06d9115e5f0a3722246478b449",
        "0x871ae94d2375f7a0d2fa584d0201c67ed2d35103",
        "0x9aca6abfe63a5ae0dc6258cefb65207ec990aa4d",
        "0xbee149d5cef48724918836c48f2749a5c5f75f8c",
        "0x1a9c1c1914a20fe9ae67b25913ffb8227c5cb617",
        "0x15a058323dcd425be52b9340fb13d7d1f135f554",
        "0x91126cfa7db2983527b0b749cc8a61fdeffedc28",
        "0xf4627de2dfa6a6c5e4710d24b113fda3e1ccd168",
        "0x12b75faf1d0b812fd607c40b4806f40f15405032",
        "0x6ce8b8eed077f9b49c1fa684008ebb7562bb41ad",
        "0x39f11a8a601cc962ac26219596af3750aa4395c2",
        "0x7ab1ab85fd3b4aaec73866c0bd646c301a1a6825",
        "0x8aa7fb11ed6893c8fea046a7f847fb834d9a9133",
        "0xab407a06a1e77c033e1d5f21a2045789b204fd51",
        "0xce46f8562eae3b1d7632be1e6da0553a2796a404",
        "0x52ff8b15ef6b38cf0554ba9207d70d0d2437c56a",
        "0xd3cbcbc2499269ad5d2b0f58de58628a258d938a",
        "0x88688596ab3acd07bb99f7a14af66f38be84f3e0",
        "0x675d3fec99bbdee31b8d562a5f9396c445304016",
        "0x636740e327726fa05f720b10ec2d71e0cd4ae2a4",
        "0x037b7cca59487b2711865ac1a00acd8e6c7ab6d2",
        "0x4fa09edccfdf5738a5493e40a4b5753cebc0078c",
        "0x4dc868d79611c2bdca51dee62873eb3a31423b47",
        "0xeabafcdc7a7ad024b3bfa76c5d9d768dd1c87a46",
        "0x6da1ac2756bbf05facc9a863fbe2e1a887d0d092",
        "0x2636e24d8c1c820ee786aa16df2085f852b677f5",
        "0x7ac75da20f75972618f3cf56cbcfe3994b962360",
        "0xcc9cceaeff5ffcf4c3657f78b11ad59a46da0b55",
        "0x9d1e27d75622cc16e35efb482cfbfa987da331a9",
        "0xfcbdc2443c21ed1279410a3ae8963789f09a7bf2",
        "0x9fadbdac1b57b08381e74a3591b84a138102dc23",
        "0x9a3da065e1100a5613dc15b594f0f6193b419e96",
        "0x0248f089a622b74cebaa62573605af9a44966bf1",
        "0xd173cbb6324c88b6ec969eb055124349181812c1",
        "0x3b1c6004e43bf49c521eb382dec02e6c3ff5272a",
        "0xf6acaf5aa6b25abdb2af45c7590948ee29a812b5",
        "0xaafcda1721cd51ed7dfc4dd23029db4c02e04eca",
        "0xe64287516518eda9f7092a0626cba00baf21a301",
        "0x2880f03f181ee0967a00bac5346574f58f91b615",
        "0xbd10c70e94aca5c0b9eb434a62f2d8444ec0649d",
        "0xe34cf351b3d64e7c7762e928e69cb87770e203c6",
        "0x2ad1ce69ea75a79f6070394a1b712db14965e3b4",
        "0x8b168e46281e72d410717b27a6ca97bf9f301173",
        "0xe22a1b2e1444ccdb730a58930819210ec75adc58",
        "0x741fc999f5b62c80831cf659aed04c64ac8ef24e",
        "0x7a1f4c713b7ced54b86a3baca9cbda91d2ef27fc",
        "0xe86c6b6c21de28da056e609bda3409ac60028e40",
        "0x31c44756a907a6585210c324cd4823f980aa7702",
        "0x168521b94eb0ca6f9aea34a735c53bcff79abdaf",
        "0xaafd4fc990ffa78ced015d77f04cc65842a3e78a",
        "0x820b5d21d1b1125b1aad51951f6e032a07caec65",
        "0x9ffe3a0864cce4995a6b385b99de3644cc8d2483",
        "0x207ff240d2f5baaefce160785f38ebd5d7bbdce4",
        "0x433ecdb79aeb4f3680de180f1bab43db5af1c258",
        "0x8a754e689f2fcba0c900028fa235043b595c994d",
        "0xcc88937f325d1c6b97da0afdbb4ca542efa70870",
        "0xfed8dfb896ff7081851c56a2652240568d2c513f",
        "0x61d8b11c05b637f913e3f7f957223400dcf20925",
        "0xb2f6ebe8e606e7b18c78b19a3c5969618fa599da",
        "0x8c5c3b13b832f46ed681dcd0e201d7cb1538e95b",
        "0x716525973aa2f59a6bb80b001f089da754b2c3be",
        "0x28863b9534af2a4c3d912e9a3b76b0b7b4fe2046",
        "0x41cece7e357f332eb9093d13138b02632cf0a3ca",
        "0x13407d93f343148bf03eacf482441dd526cd7ebd",
        "0x6f303642844f734ad4176d0dfe93ef7e0776ef46",
        "0x8476957a872ac0bc253333cc063b6a37f6a6faa3",
        "0xdcf533abdbae655e8fd438a9435733dbd9068b89",
        "0x14c7a2ce7482c3c66897dcae3eed5d62985f5e86",
        "0xc7a74785f4e12a3e1e30dea4ad9c6c88a90c8f9d",
        "0xe5221f29861508d7556249f19924effe391db237",
        "0x4473d7e836e473aba72af381536a979e5063f7f8",
        "0x22141343a20640daaf695226b2233baeef0f0d62",
        "0x18714dba089604fe18a7af33871198fd470ffb3a",
        "0xa49186e5c6ad0474cc5226ed7a2ee38578b0d901",
        "0x820b995cb1b46b36da607598d535ae9bc4d00953",
        "0x945400ae0c905725e3197cc37255241337301335",
        "0xfa21d56a4058e571da42c627e4f59826e78cf0b8",
        "0x9195c0345c5c6b88e71e5d3693ca9f5c2ca3b335",
        "0x81b0853bec4b8ced6d2df03f363c06ec4ce0883f",
        "0x915671b817bb779f41e605590e400514c8b63fff",
        "0xb3d5f0210cd4f4631aa634103388fb759a73385d",
        "0xf048bf43b31a10768ea29b4bdbb90b9bc7f6d7af",
        "0x88eeed5e40a9a33d49f964f337a3c413979e2973",
        "0x0b444993e305016f213a030c9af4013a8c537b63",
        "0x130282173b796f75e0eb65eaf9f4d10835e1287a",
        "0x96b26c1872566fd977e7a282a17bc0203a20a90e",
        "0xd3353412854f2f6e16d25beee977878aeb52b58d",
        "0x88aa2aa27cabfbf2245448d368fd336641477f0e",
        "0xb61d57a3eff8c3a1c011265ea2b01f47be671767",
        "0x4d56f1fbf4a4f6206094834cb88cc089a66a843b",
        "0xd872b86a0a60fa16b1193d2e2a8683d4ef034fac",
        "0x93bf8d1203ec4b6265e7bc14b6feeff48a49b66a",
        "0x24439df4af190d2f1b053dfd1775f3f14514ee73",
        "0x4affdf26e54917eddad5bf5ede9c99dc170d5479",
        "0x21cd5db524b815aacd5828242329d65de8898ed9",
        "0xd1b9be6f95e620f80d11b121176f67fef793977d",
        "0xf22d5e6abe2d35c9940540e212b7c6a0d04ba126",
        "0xfb7dcbf23df60033e265fc7092773a6fd88505b1",
        "0x2610c64270a323ebe18a9ced6d6bdabb84d80e96",
        "0x95253d3d64989c5c46414fd613d1c9782fcda23a",
        "0xc26659605bc17facd9349df4af7afb4729329515",
        "0xe973adb30ceac96b34a3286708f166fea6023741",
        "0xd81c61db6173ce8f071b74e98523019387c3b086",
        "0x3ce90722c9a7058a9fec33d98817230914eb8519",
        "0x78bdcf7837bf8304f9feb5127a365e6d677411af",
        "0x681a7f956d6aabd7eec198cdbdbd2883be1bca80",
        "0x4b568e798d6020abd5974388b02489544e7a214d",
        "0xa9dd36392e3e56dce6cf4f7e410991d6cbca5a95",
        "0x780de705ef3e8b19e01377d04dd137501ecf1783",
        "0x832a991994bb1b994b9eec344256075acd60cd99",
        "0xa5d8fcf8e0c66355ffd38ac68a71b79688b68b3f",
        "0x9ab630dc20f049f49ed6ca5e034cf6d8b69248ce",
        "0x25f3eb8be8f60e0dbfc0615b46aa0d475ba795c5",
        "0x7c2832ea0d3709699a39efaeb7c46740c97e9fa4",
        "0xf319a16037bad85bea8e8d821d2f1242ffe23592",
        "0xe7608bf96379826b91ea9fdbd4dc3feef173dc4c",
        "0x25d71f9e44d7411ad0d8d90000e6bbe53b11848f",
        "0xb2fc931b809c9329cdadd7177264ac156f9f833c",
        "0xf6d300c651e892e48718689b426757fbf01fab2b",
        "0x820d413cb4c38d3b328cefc3e661072102d3898e",
        "0xb186afcd36a6403ec957f5c74482aaac13b87eae",
        "0x09dc6a7d0fc62b02dba3652816125e45ffa872d7",
        "0x86621332963202937650cb9153b1afc8e73296a1",
        "0x23ff20255f478df0f0e4a59af84f8f392b6a8fb5",
        "0xcc1a13b76270a20a78f3bef434bdeb4a5eec6a31",
        "0xa6c122b11f20770250e2875f0e2eacddf3fcc609",
        "0x4177e5c07b209fdca95a6eade13bae4ddc6e543f",
        "0x0da854e6e64001369a9825166f2a436a3ad70404",
        "0xd37e1d4509838d65873609158d1471627f697874",
        "0x7eef3f256e868f3a8451bb954e7977ddcdb027ff",
        "0xcbeea2e0c48f5bed015fe53bdc8fb643cfef7969",
        "0xde39bcc574d7826f5ed64d045425571564dfea9e",
        "0xb3b476df77086b227d480c99b69b08a77631f2cf",
        "0x8c6f3d75873c66cf0300c9d6dfe8d607d1824204",
        "0x57a1acbf4205eef6a0ac6d41b481268c3db3d768",
        "0xb31ffc2eca634937a1acc375811d8a2c969ae61b",
        "0xe60b241a21dad25876379c617b846ad4143bd3c5",
        "0x625f220be6440c14f3481072f1cbe9a83a58ec75",
        "0xc3f2b61da3c3797930caf9e9ff174c2d70b2e8a5",
        "0x427e6460df1d9624f4e266f3dcc0c860fe5a6319",
        "0x954a36b1c1e5e42f884c4f7aa9522e6fd21b11c3",
        "0x5ab2e3f693e6961beea08c1db8a3602fcea6b36f",
        "0xea0822a17b62bf1be91fa8c98154ce42a87589ff",
        "0xc1d7ccb5cc1b4e0b1bba69657392e28f0c0514bc",
        "0x007df6ad281cbbb9e0e9373654fe588b2bd3b9af",
        "0x08ade307321221677e837c8150bdbd4e891daf09",
        "0x7229bb50da9c01b28b9f1aace7711605d88afbd3",
        "0x0ff758756e8f594ff463c9e7a41802e9ef717265",
        "0xbb22f3567119020cfc6a7eaadcb52638a51eb8e4",
        "0xa9ab0d74ae3c632193c6e42b44d71c09399f00e5",
        "0xff833d42c6a9953342dcb2e24f5579dea8305995",
        "0x82faeb0437bb469cd826b9a83d32d30d4d0ef2c0",
        "0x88d929680fa9d9921a2bcfec6c8f58c0586f4091",
        "0xd9b487b5db05dfb5df9b456c6259a821ffbaea30",
        "0x404803e04be686f70f69ea2c2bbd59c33fbb4db2",
        "0xb13f155d788de3e8bdd64a354c052dbf9adcdbad",
        "0xb29405833e303db3193cf7c058e2c81ef027c6c8",
        "0x8105cac7ae60fa550c58dfd1999ea7c34827802c",
        "0xa3d48af5b7541658e7b663905f11433f1b4074f5",
        "0x458a91ca044f21c04e4ebbb44769e32408d8121a",
        "0x66fa156e32608088da7d3c8cda3a04e9f7038997",
        "0x51d3aac348d1a26652c6e8eab065a269830d1930",
        "0xecb9dac84d77a4a31264cdb2f863288a6fc44235",
        "0x30d3a214d9f1f39a3c03de63d6df6f021fcdc674",
        "0x881f21d3e2d2d4f48d815f41bea8dbdcf0e24e50",
        "0x6612a2cac21a89159ad152488fd1f843d33843e4",
        "0xd0645acdf897a52e7bae4044879e7a9126ab299a",
        "0x290d7f8b8d7da1e92903405a74667c934ca8f086",
        "0xfe3101486b4f06fe9a5d210ff0294f6d4ec706cf",
        "0x65c52ae9b15dd6f30902e9f8164c91e912ee2be3",
        "0xe8ca6178e82120bb23c883c3778d048b1efbb072",
        "0x1ff826b46424033d54e5c9ef092ac575604f9295",
        "0x5437a3fd61795097280fa5312852442568ed85ce",
        "0x52c52944eaac353f054902225e1df036589fb6d7",
        "0xd71a90c6903c698b643ac007a7a279f34e444dc3",
        "0x08ad34f1a18285bf7bac2c68d0b7017a423fe1de",
        "0xbddd99e8aaeb85847703c31a83277856d49961d9",
        "0xd8993f49f372bb014fb088eabec95cfdc795cbf6",
        "0x0952702680b4bf531702385f948a7ee998b53580",
        "0x2b300b6f1465b7200f798558d028cb947d6c9e15",
        "0x4e09bec79180b52b8fa109099bb22e64e771c195",
        "0x95609c7c7cbc0f3ed3f7005379f5ae5f872408e2",
        "0xbbe534ade64ba84449af1ae1bae2275caaa1d499",
        "0xa543ef876888ae5e146c33dd515a29304d53ea73",
        "0x0180ec945191fda23c52b1d05eec64a2e3f68781",
        "0xc6715b8eed812477be1e634c3a6e0309f10da9a9",
        "0x61b84b8f683ae4408bdb87de9a6cb12ed60e475d",
        "0xda017d3417d7fcdd4db134e2491f30292ec647c7",
        "0x7facf5286883d4068b5adb4c7c4d3ef714fad5a9",
        "0x5ab5dded8c5c384015c8f3a27d59bf71b952a3a4",
        "0xf60efc8e10692b111f7e73af821ccfdbcd78eb45",
        "0x70c4949d483166abefb2b4b2be78e338cd8b2c40",
        "0xa96e6dbf0f21cfcc9934ad52dec8229e3321254e",
        "0x2d1e75f35c863f7e86ad0de2d802206b883769b8",
        "0x0b0dd5737eb7432c7c7054ef156628c6d7b9d2f4",
        "0xc2438ef1d2f2c1427bf0a39f02dba6a4a9de4793",
        "0x80a9ca0bee2a09753d27657f7ab6d6e018e78b55",
        "0x6ab7b3236a7df8e6b28f2310199edd0b5c228c17",
        "0xaa0e1bc5163293c2e335977d9478d741f3a4e372",
        "0x3ba2175a0791dbe272528893b6922b4bc19d1f18",
        "0xc37172f6a954e3a779f5117fd751c5e870164e01",
        "0x8e5a41d13c04028add9ccacd0a56af2df778543b",
        "0x742b41ebc3cf0c5576ad29960a92c7b25b3052e8",
        "0xb33e35c8e3b46a747a5fd5ea78d901aabe3f4f96",
        "0x25c08bb7aa204d221288d9739899f4edf96f5fba",
        "0xdbe46c0e6526e9068da1626acfddff2386635045",
        "0x472796507b77f6ffd14059c81ca77516905198e1",
        "0xc39be70b50ba867db776126986fb5b9fdaf4d8e5",
        "0x511c1343c41900dbd64ddbac04635f4ef25177c8",
        "0x6c508b8aacc804a9a359892a28081d25b3612123",
        "0xe381bc830432434133856ec4f185b1dd8e05cdb6",
        "0x7f9fa692e1b65d2b6d670feebd3e6bcc29606f14",
        "0x386faa4703a34a7fdb19bec2e14fd427c9638416",
        "0xc67c1f88f31e724b137a057292e55cb42a5f3241",
        "0xb1f9ccd66cd9bbfdeec82e29e19998f42424f5a0",
        "0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710",
        "0x4490f9807965c49a2471bd7b121a80f0b3861e5c",
        "0x468b840b64e2de2849cec1321fe8131070029770",
        "0xfc814639f7dcc2c7a3d5df3295e138ddfce60150",
        "0x995afd0c437f7a9de72816378b2883d5d006659a",
        "0x4d200a0a7066af311baba7a647b1cce54ae2f9a5",
        "0x75041597d8f6e869092d78b9814b7bcdeeb393b4",
        "0xe914e10f1c9c30c89511f4e7a0f5f7c9c46d6e10",
        "0x2d4f1883d7f6035298152b85b4e07459c216c317",
        "0xa54a1b3a6203cef877b759b64c6d205421e9f86c",
        "0x522e7ff686caf7ee5a4063b577ccc7f07054294b",
        "0xb38beba95e0e21a97466c452454debe2658527f7",
        "0x00346fddca107aec034a367b7324f0d6419bf4b9",
        "0xd946be2b7a614ca2d60bd042cf8a40d0d0af93b9",
        "0xb04ee6be2b98c9ed24be5585329891fea036829a",
        "0x64669148bca4f3d1216127a46380a67b37bbf63e",
        "0xed4ae9985461e7f54a37dc8647cf0902576ee08b",
        "0x126f7fc5e32905734c639d1708fdfe4b2c4e704b",
        "0x0920b6fa89cc70475c9725cf29169437131217d5",
        "0xb5042a8e68402c244e49ea936f31edc4f699903b",
        "0x9c35fd2d966bdf2c28d906b0d862acb6600d28c8",
        "0x3597f78c7872db259ce023acc34511c7a79f42e3",
        "0x80754f5833c606d6443cfa315d933ad599fc3d07",
        "0xd10e234f5583ee6d47710c05f1e9b5553bd5b0ed",
        "0x7b3c3a05fcbf18db060ef29250769cee961d75ac",
        "0xb690226d649701d7a7ef40161904cd814faf4f41",
        "0xc584a60e2cbedfe6a068371e6e34f05844b3111f",
        "0x07b1c32132c7a51c9ae92e1c401bc14726fe719e",
        "0x9bdb9d9bd3e348d93453400e46e71dd519c60503",
        "0x369d0db2c7d56b095d758379b75f64085953528a",
        "0x20041df9e7359c2d04e22322d5fabd04783da436",
        "0xc43fba7bf0250fcd88439af086475fdf117fa255",
        "0x16a5dba1d8d5dd53ad7bb9d8a8b97af577be753d",
        "0xd3a661f28b33167d0982e88caf431675bdf4a3d4",
        "0x11f05f64b0ddcea285d1bddc1d0f5b927bfb5b6c",
        "0x1b442a27fc37b5527ecd5c5ead301dac1638810d",
        "0x13c547ff0888a0a876e6f1304eaefe9e6e06fc4b",
        "0x6ddcc353122f36f6976baadd5ef62e56f39dd960",
        "0x2fb96a6ca0e940ed219e9386210e6cf299295ffe",
        "0x043a0f6f167c81d6bc22066c0525fe88a2da3c5a",
        "0xaf21ae125cb7c6fb29798b5835b806aeb6cd9aae",
        "0x91d0013742c6a6a033d46ac9da7b5e0416c35e24",
        "0xd827fe6499e16499bffa245cb8904d4cec20405d",
        "0x4c1551fb1297a7ef88257e8f81aad7fa25290584",
        "0xc7f4d34847f4f9601b32850b4b54e429f251774a",
        "0xdbc71d8c921b267e59a6ad92c4fbf4d597c83f44",
        "0xfff2821629a979fc29c334ad7648c6bf78ef32aa",
        "0x89aba6c49ad497cbb23282518f23183c958e8688",
        "0x248f27e8e8478c7fb745205a1e603982eaf4a273",
        "0x7a7ec07803ee7fea9566ae51ed1b63bc65dab867",
        "0x1963a22024a150a43586fa01c4d3f06e4784bc15",
        "0x96613deda35442b027b2d968c8e1919d2de16ded",
        "0xa2619e633077377106b8ab3d554b1f35fb1a177b",
        "0x73b5d7fc9fc1d2aab0122fb6242d16c753dd0df0",
        "0xf37b0473bf2e0648e29bfb07abe29af56648187c",
        "0xc316199225cf183c296e597f80366f5d8047e0c0",
        "0x61f60e1a20fdc2a451e2eec1f571ff38c08e115f",
        "0x6855e361bbbe7a5e6fd7321e5b6778484c7fab23",
        "0x46c55f25de7822ae8cffaa343a34b98310ecc495",
        "0x981806468140943f59ff3af0a6fda184d9a46a66",
        "0x832a9ffcafae8f0392ce1c2361d184958f2ded04",
        "0xedacb6f8cda349894df04e8eb9ef8e6507b0da37",
        "0x2f97dd7fa9ff51cd34ee30536ca915bfc85f6ca0",
        "0xec61ae640fba61c7de9d500c0776d3f6567d4ad4",
        "0x9b0345a70b1bab861b8d10307f14029906cf6e09",
        "0xe9c48b34e2498797b7f70d9fb5875805dd6bc8b4",
        "0x1b5ed05690a6b04533f09185afe03ff2371835c2",
        "0x2fd747959bb92e1e33e39c517605f0bc4bd12746",
        "0x1a468849923b441a10b2673af9a74b5b71906087",
        "0xb49b1dddf1b3d6e878fd9b73874da7ab0da7e004",
        "0xe147416564f94232e9111a5b71f5eac58aaea02a",
        "0x0e915b35cc269b2dfc8bbd8e4a88ed4884a53efc",
        "0x7dbe2567998b3f3ee6868804ba578cab91d1c0b4",
        "0x5094b50ac9b82ca53dd24ed67691d1bf7a92adc2",
        "0x01293cd77f68341635814c35299ed30ae212789e",
        "0x9c05d6ca98c7822a14e820d25d8b028301babc0a",
        "0x371715dda4cf2b4ca22c5995da8a86bc7c21837e",
        "0xad43e9372590b2b1c2414f250c0b6d55382ba272",
        "0x19516e7e6478f8ff67de5d15960e0fae60d8ad10",
        "0x8ab65829fb1b2f117fc0f593725f04d4f85d1a6f",
        "0x4876bca6feab4243e4370bddc92f5a8364de9df9",
        "0x9d282df895d805bb4e17f804c5af4e3191752b9e",
        "0xc1e37fc2a0a31c67452463ed95deacf32d4dce77",
        "0x980c8c1b4edad97f65f11cd73ec58bc340ff76ae",
        "0xecbd0854075009d23360c62da07047efc2312144",
        "0x1a7f7770de7fbbfe242db161e69bdf96e155f136",
        "0xca64a1f5437e74bb1b77c9a7618838e55f9ddf2d",
        "0xe4e8496ce658d7a188a099e2df2ba4867f7c4bd9",
        "0x4727829190b9867f6d01aacfbcbb8271e20c20f2",
        "0x50ad84b1f81fba29f7a32743cf8056c209e41c30",
        "0xbdbadbdae043513f839681bd89ccf5ca821ff8f5",
        "0xdec14d8f4da25108fd0d32bf2decd9538564d069",
        "0xf0d20ae17804be1e5fd400f04991aeb0ffed5a03",
        "0xd3e0f0e805f3fc592137df9bcfe61614380bf71c",
        "0x62dffbd49f35cb53868d091310cd4d0336b7c98b",
        "0xd2606c9bc5efe092a8925e7d6ae2f63a84c5fdea",
        "0xd8e409a52d8985d21e89c7628f0c2391b6f5ab42",
        "0x3d2380b2036e3ed8229fc8e3b9a62e7a10c073fd",
        "0xa42868496e6b98d655e4a820801d8df8f4abe2b3",
        "0x622ed7ab4574a16399780f612bfee3ec10f54f7a",
        "0xc0d72d45cca854e0f2fe3cd2d4bab91e772fe4c0",
        "0x0725f842ec582c515b2f6e2cd125b94aa1818fac",
        "0x8d4eb49f0ed7ee6d6e00fc76ea3e9c3898bf219d",
        "0x1f4b81fa77d621282780ccc52389523d642d0443",
        "0xde82658c23f034d71827c215fdfbce0d4e248ccd",
        "0x79e10a7324e97ef9d6ab9f5dd069b847f99ee851",
        "0xc3ed27288978282eed5524460db0a26f583dc392",
        "0xe9bebb13b801c72933fc79a5640a316a5213c380",
        "0x3b048ab84ddd61c2ffe89ede66d68ef27661c0f2",
        "0xed710216da4b1416a78768790ca9aa3633ca110f",
        "0x80e38d47b1dda527e45c353f6fadd133c7c21f35",
        "0x704079e823e42a936bbaac5163434c2515473836",
        "0xe13c798fcb949c5b9ca1fd818f5f04fb73dc343f",
        "0xa01a177b1c6d903c85dcfd98cb7e0749326e48a9",
        "0x6594ac0a2ba54885ff7d314eb27c9694cb25698b",
        "0x930dfbdc5e9f1984a8d87de29d6a79fbb2bb7b32",
        "0xaec8162438b83646518f3bf3a70b048979f81fab",
        "0x6f905e47d3e6a9cc286b8250181ee5a0441acc81",
        "0x2cc8e271f11934f5fa15942dfda2b59432c2e0f3",
        "0xd1a3ace46c98e028229974217201433e7163c4dd",
        "0xcf9af35057ef678f046bdaf0b0e6c11ef20c992b",
        "0xa949966baa94d94248d13e446b2a301480f6815a",
        "0x9f9ee7c5f0e11041918f60da937b67f8276cae10",
        "0x10321d95ea2dfce2f69d9020ffe419f7a2d3a29b",
        "0x5013d632908bbf0e73553810ec85f090a466bde4",
        "0x4341d82876ff3fc717a0f3b6d6329f9aacca3964",
        "0x8df6eba1a0225509c16d59f69f4495b6a1e7b0a1",
        "0x377f64e05c29309c8527022dbe5fbbfa8e40f6dd",
        "0x47eea2f1c9873504af884d89e028b28f32d3cdb2",
        "0xf6228fcd2a2fbcc29f629663689987bdcdba5d13",
        "0x7fae4e2e6e89c16ca497ef0c7710bbf10b1cde30",
        "0xb40c50ec723e3b909ea40f12a0fea22026e1ec35",
        "0xdc4a251dcbbfa62639d0545a90439a671359a626",
        "0x66a182f66e71b28e9eb9083b0953a2b8c008de85",
        "0x4225d4dc8fa09ca2e62ea7ddac8bd2d80ba5ce88",
        "0x9c97b8cc86b3c4ceec555b07d30420c25d16989a",
        "0x0c8931423583d9c1ff126d424e34656947876649",
        "0x66d725e68a6bc01b6e59d7921994144e5de02f88",
        "0x448fcea60482c0ea5d02fa44648c3749c46c4a29",
        "0x58a11a4445adc8384ccb69935162af2ca5ae7f63",
        "0x6f7d68ae5ecc966ff4415197de4756211deda0ff",
        "0xf2665a78aec490c1bb5ab3e0927050e1857f70f9",
        "0x5ccfcdc1c88134993f48a898ae8e9e35853b2068",
        "0xbf5fb038c28df2b8821988da78c3ebdbf7aa5ac7",
        "0x1efc39df484c7af7addaced79fea0e402776b17c",
        "0x25aa2d83d193f3d83c9fa2a5fa90b3d195d61355",
        "0x2dbfafd20f56213b75cf5c32a922b12d60de68ca",
        "0xf3f3dd2b5d9f3de1b1ceb6ad84683bf31adf29d1",
        "0xe3d085b7bdf97c6d003abcec2003b9c5b120d616",
        "0x8cc5d9de2c8df87f2d40d84aa78049ea6e61f973",
        "0x75658ed3dba1e12644d2cd9272ba9ee888f4c417",
        "0xb31209caa95b4475aae98a5c32dfa0129d154775",
        "0x0595d187cac88f04466371eff3a6b6d1b12fb013",
        "0x3caf97b4d97276d75185aaf1dcf3a2a8755afe27",
        "0xff45211ebdfc7ebcc458e584bcec4eac19d6a624",
        "0x686847351a61eb1cae8ac0efa4208ff689fd53f2",
        "0xbb39d3ffacc15270caafcaa81f0a4a95d7e0247e",
        "0x36bdfebc5c817bd1b1bc042410439170267b31e5",
        "0x3ae60a13da86d6edbd969aa2b9c26c2e10e0757f",
        "0x2fe321bbb468d71cc392dd95082efef181df2038",
        "0x16cd4356339f203642e92b463d5615766f011326",
        "0x4794c7319a69d50d9bab3164143d16bb4f2e52c7",
        "0xdd3b6b4b3d4aaf9874b3ff24dadb1c7f6f332524",
        "0x9b2de3808e64a2a7ddfab46e991d9f354acde54d",
        "0x3ee5b40f709c39d3812e8b074eadbb6c03b0f70e",
        "0xcd87e04272c79a47194b32acb85b74abdc5dd57c",
        "0x8cbcc2eaf2fdea56b6d7127f3a13828036e21d77",
        "0xfc560a12fb91c7b743d070e5764b4404de2f4883",
        "0x00822484be254581970ed737d20cf2d71f14e525",
        "0x433012ccf4ec79a305a88b536d06bd52fdb528d5",
        "0xf0344800bd3ffa687e4d780357961b28995a5f46",
        "0xe52ddc44e9247fc0e191a62f53811b5f5c739b55",
        "0x91d54d763d84cdc15007de426492ee1ac582bffc",
        "0xe3b0fe57f7de3281579a504dcc3af491afbb23e5",
        "0x6947c40ba3fa0e0b2689ea3983e57b746d4568a1",
        "0xf4894fdf87aa749badcb050694a90683671c2e0f",
        "0x063daa97a0616d2ea65214f8a4130ad3a3e4894e",
        "0x9d3053e598b3332dde14825c03141dc32eab4e77",
        "0x345e4fbdf60155b045e44e92bead5b61c5524139",
        "0xadaf163e835cd9203f902e7c8fb156b06a7fa06d",
        "0xd25cd68fd05176d6188c55eed8e2f079158b6237",
        "0xdc20655a6de13496dd385f7ab903e4e6150e55a5",
        "0xbd4c9ab2f3e241f1291d55af51cb0d949077b591",
        "0x911953208022030ad13074d2cb7c14fba4bee80a",
        "0x129e719c424a7a6fbdeb7ca3d65186892d54ea8c",
        "0xb9df29b983802242281ae3409454703ab7805c8c",
        "0x477f97ec5d39946bb5c2964ed523a99d5dfcdcf8",
        "0x2b2a506ebfa319cbf5b25b688c70304170b5bff0",
        "0x68512f25c762a61047e652c51c71757593a2e9e6",
        "0x24cad91c063686c49f2ef26a24bf80329fb131c7",
        "0x3285fd5707813fd5e07aa6f0ac37a8114c3d0dc0",
        "0xc83d46e4d1e290fa414a5775d90d5d50745c3281",
        "0xed55fb58ea9de1f484addcc970463218b4d89cfe",
        "0x4f3e1a467d2ce2e01941a789ab226c13202d880e",
        "0x94dca4f83bae48822e9cb011f02f1ac7b8f5e1ed",
        "0xe4889fa16ba797a8a51196ec9389e4764576deae",
        "0x6d5db58b8581c19098196ee1c175f2c6e08cecf2",
        "0x6e6f819299e7809ce744f37fae9f84fe38d95f1c",
        "0xb5c424cd005cd1ccc155654b551c4453346e0718",
        "0x8cdc892df28249ad590d07bdfd5ed6d496f29a01",
        "0x5d4df6dd12fc56a31e2550efd6414e47a676ecef",
        "0xbb51397fb8d3b91a08eff3c34d5c869c1d149ec5",
        "0x5b39afa22a9debd9247bf84b68a79b8736c2ba4e",
        "0x97d25094830592b0f9fa32f427779a722ed04b34",
        "0xae5e58aed25dd4ac35318aaba363c0b1f0fc8996",
        "0x2b5b729b38a4ab3eb0cef9d1a5dbd3e8a16adcfa",
        "0xc0fe4350a7da916ed7b4836e2b5e840b228855b5",
        "0xbd53a4db4003c59070abbfa4e6c31afbf0b26843",
        "0x955ccd9a4a415cd1170f00dbd834f52e78972643",
        "0x5b5b518d5eaaa14f790ba9b59a9a586c3a784d2f",
        "0x0069e491f2ed9e562a7c9c92ba40f73d946718e0",
        "0x1a3c2fd0983b6b37e83784ab70a8e9d8ae0474b0",
        "0xa6f52f3c64396ba39e9c959e18d53228d114a3cd",
        "0xda823ef2d0de994b329ca6e4e95934b3bc0db8d1",
        "0xd9831c42da5bfec63313defec951a7d40286cec1",
        "0x32353f618727f1272258b45a2aac1bf2335faa2a",
        "0x68af0f18c974a9603ec863fefcebb4ceb2589070",
        "0xc304349d7cc07407b7844d54218d29d1a449b854",
        "0x99bab102c0a03438bcfd70119f07ee646db26ddf",
        "0x4a73d9fe078fa67601047f88c3e6c270602e5709",
        "0x63c30c6a200963dd36dbcc82423a075e587d41d9",
        "0x4e73b32ed6c35f570686b89848e5f39f20ecc106",
        "0x2b78aeffb8f3b92f693cfb4f5ee86c99f9a1bcbb",
        "0xc3af01b683521e0206dc167ac4bd8acc8fa2b424",
        "0x735906d7ab237eeea06f4af86795bb4e0ec199e0",
        "0xa2f13a9d1641211ade896cd0e0a3716f51533cda",
        "0xc9ef94f7b7dd045cce2b0cab7ac3075d6b49f4b3",
        "0x3c5753b9de8c49101155a9b31116b965a5d82574",
        "0xfac1c7270bc5b0664e27e7f2e82281d564aedf4e",
        "0x7fefc8bf6e44784ed016d08557e209169095f0f3",
        "0x29cd957139dae4a381eac1913b2a41d432235637",
        "0xcb71b51d9159a49050d56516737b4b497e98bb99",
        "0xe1ccb3a5bae6fecdb9b60c0acf94989f48c10742",
        "0x3f90421fd22b7e3251c8600430acc82922d2a434",
        "0xafac96616383d825a86a1495fbeb7dda26b1fbd9",
        "0x4aec37ae465e1d78649aff117bab737c5fb4f214",
        "0x2b98b39d39914b3aad05dd06a46868507156400d",
        "0xb6f6f6f47e92e517876d30c04198f45a3bc1b281",
        "0xd87eaad7afb256c69526a490f402a658f12246fd",
        "0x062e659a3c8991bc1739e72c68edb9ac7b5a8ca7",
        "0x611ae0be21a9c0ab284a4a68c8c44843330072a7",
        "0x57684f9059afbf7bb11b07263500292ac9d78e7b",
        "0x197803b104641fbf6e206a425d9dc35dadc4f62f",
        "0x2392ccf7eab0010f0da5ec9504dcedb8b7259b6a",
        "0xaf531dc0b3b1151af48f3d638eeb6fe6acdfd59f",
        "0x6e38b747183bcb560bbb8a2812c66bf65509cc88",
        "0xbae339b730cb3a58eff2f2f2fa4af579332c3e1c",
        "0x788dcaa03860a44a98cc64652a3d1a16fbecee9d",
        "0x2ad6bdedf16b32a925ba293ee07f9b3c1c5ab266",
        "0x561eac93c92360949ab1f1403323e6db345cbf31",
        "0x6ce3fef99a6a4a8d1cc55d980966459854b3b021",
        "0xff9c25e5b8cb4f0df53ed8065877257170ac28e0",
        "0xa5b382f3735db81f4e31e2e706c5d5ca17c37fa7",
        "0x4aa4452cfa92e943555e1be7544d4e80a4dbe34d",
        "0x878e6c6f9a86a1e5d313e7b872ccd109135e91b4",
        "0xf7d9a45739d87c89b1791990b4aebab28f3880f8",
        "0x1c18b4463993a3e70503cc1e643afdf9c33fb3df",
        "0x4ca675d62a05c451555c93e456f902bd3e423586",
        "0xec71870d02ba5c392ec8f64837e314b28afa4222",
        "0xa0f9e5283fbf6d735e1e3a0f724ea6cccc13c27a",
        "0xed4ba2958a08511b615b6c92015a56c2ca05ba07",
        "0x4bc53ead2ae82e0c723ee8e3d7bacfb1fafea1ce",
        "0xce6b1aff0fe66da643d7a9a64d4747293628d667",
        "0x0e8f2803fa16492b948bc470c69e99460942db2b",
        "0xc5f8140f9c6787ef25d9d8f168e51fb30f5302f2",
        "0xc5ce9c06a0caf0e4cbd90572b6550feafd69b740",
        "0x70bf9df6967dc96156e76cc43b928a7ef02e159a",
        "0xcea86636608bacb632dfd1606a0dc1728b625387",
        "0xaa3a6f5bddd02a08c8651f7e285e2bec33ea5e53",
        "0x1237b26652eebf1cb8f59e07e07101c0df4f60f6",
        "0xc7e454770433c071dd1863eeb27fb7e1adbd3361",
        "0x8d056569b215c8b56e4b3a615dac425d8d2352a4",
        "0xc1574ab95106621686d6e480f378d79c0442fe33",
        "0x90302710ae7423ca1ee64907ba82b7f6854a5ddc",
        "0x40ef62929748b3e045fd2036322880ef486e4454",
        "0xd0981f1e922be67f2d0bb4f0c86f98f039dd24cc",
        "0x26ae986bfab33f4cbadec30ea55b5eed9e883ecf",
        "0x4c4757b23526ba13876f8ef3efe973618266e3e8",
        "0x4bb12d68c795462c12ec30ad82421218d9c32a7d",
        "0x159d2829613b0fe363e462b218c695c6eae0a5e1",
        "0x950ad688ade27bcaa6e890e9d86ba5a9293f4d8c",
        "0x36d5d7262784130de564e99f5c2eab2aa0484bce",
        "0x52682a037a8deab04e708055c751556a0840897a",
        "0xd518db222f37f9109db8e86e2789186c7e340f12",
        "0x7beb466c221d3bdf50b314beccef69acf0eed94d",
        "0x1fbf025ad94dde79f88732f79966a9a435f2772f",
        "0x1f7743a56badfec44cbc46fe4da0aca0d83a03f3",
        "0x3668eba58190c7bb2d63cb484467ff0a42fb3367",
        "0x2e4eb4585cb949e53212e796cef13d562c24374b",
        "0x01f8c4e3fa3edeb29e514cba738d87ce8c091d3f",
        "0x4320e6f8c05b27ab4707cd1f6d5ce6f3e4b3a5a1",
        "0x85044611b5954739dbde0ccb9aae6bb18e38e38b",
        "0x52a8908a90760898da84b430cbdda30d9bfae403",
        "0x0684a256b8a6434cf10ee81bc1bcdcbba3365daa",
        "0xc78f0fdfb708689cbe6629175b66958eaa89e7d0",
        "0x2e0794073ec7b08e40d80a41599bb31df042e4e5",
        "0xfb4f9e002763b9d8a48efce8ab8a33e4d3bc9efc",
        "0xd5278c0bbb7a3e5dd9c6bca5da814b989e266016",
        "0x1ef463b0195e163c93981eb96808ced96949c9a5",
        "0xdf401155b75cbe5b916a724873cf61f136900e75",
        "0x5ecbb3763d6435a2345a9f2e972e1b095f679a92",
        "0x35edb498de6827e73d00b3736019051655484655",
        "0x1e4122413c436a294b11ad238e2293de633f2581",
        "0x5e521b660fe8ac575f1d7201f2237724ee531f1d",
        "0x402cd1fa4ba4296f5503d1e86214b77ec7cfe840",
        "0x68824685b5a397500002751fd7212096a2247823",
        "0xf2d32cfa422a4a5b7074050651ca380eb0cf0a8c",
        "0x1f4a389887a2620e26feb059ed2d0971f0371e08",
        "0xc5b0a2c730b5716f3a2b5fbdd9dea05aaf9a3260",
        "0xdda2044b39fdb4db77ac085866179c548e5d0f15",
        "0xcac14364754336d9759caafddef8d662dcca06a0",
        "0xab9bd374cc164decd5c701d15ca12597b79e2ebf",
        "0x4ed60c1c3a5c81aa5e0a701ef92dbc8fc89a3fb8",
        "0x6ab80c3f237c47fe595abb7e43921dcdb19cf519",
        "0x3bff97751a79299d00815611e79687933f4310eb",
        "0xe0a159f8401b96e3ec0be1163243d860002d6bc0",
        "0x349d9314154ef0999facdbbcea2d9737b0529570",
        "0x53018f93f9240cf7e01301cdc4b3e45d25481f73",
        "0x6f5e7f39f96b882490643228a725a179f04feba5",
        "0x0f2a1a06024f6d2ceb2adf937732f9029ca97045"
'''

