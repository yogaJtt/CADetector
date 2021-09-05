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
pattern2_1 = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+([^=)\n]+);+')  #简单版 --- 其实也可
pattern2_1_1 = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+(.+)=\s*.*;+')  #简单版 --- 其实也可
# pattern_2_int = re.compile(r'([u]*int[1-9]+)\s*(public|private|internal|external)*\s+([^=\n]*);+')  #str = 'uint8 pulivat;'
# pattern_2_string = re.compile(r'(string)\s*(public|private|internal|external)*\s+([^=\n]*);+')   #str = "string public question;"
# pattern_2_bytes = re.compile(r'(bytes[0-9]+)\s*(public|private|internal|external)*\s+([^=\n]*);+')  #bytes32 responseHash;

#2.temp 形参列表: （不用考虑constructor）
pattern2_temp = re.compile(r'function [^()\n]*[(]([^()\n]*)[)].*')

# position 3 --- 必要的(之一)
pattern_0_transfer_1 = re.compile(r'.transfer[(](.*)[)]')
pattern_0_send_2 = re.compile(r'.send[(](.*)[)]')
pattern_0_call_3 = re.compile(r'.call.value[(](.*)[)][(][)]')
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
        if contract_name_temp != '':
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

    pattern_exclude_noToken_1 = re.compile(r'(\s+token\s+.*)', re.IGNORECASE)  # 可能并不严谨
    token_relt = re.findall(pattern_exclude_noToken_1, vcode, 0)
    if token_relt != []:
        return is_HSU_hp, is_SMC_hp
    pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
    safeMath_result = re.findall(pattern_exclude_1, vcode, 0)
    if safeMath_result != []:
        return is_HSU_hp, is_SMC_hp

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
                pattern_3_falseBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)' + false_define_bool + r'(.*)\s*[)]')
                list_falseBool_judge = re.findall(pattern_3_falseBool_judge, vcode, flags=0)
                # print(list_falseBool_judge)
                if len(list_falseBool_judge) != 0:
                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                    if is_SMC_hp == False:
                        print(hp, ' has a high possibility to be a HSU (bool judge) hp.')
                        is_boolJ_HSU_hp = True
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
                pattern_3_trueBool_judge = re.compile(r'(if|require)\s*[(]\s*(.*)' + true_define_bool + r'(.*)\s*[)]')
                list_trueBool_judge = re.findall(pattern_3_trueBool_judge, vcode, flags=0)
                # print(list_trueBool_judge)
                if len(list_trueBool_judge) != 0:
                    is_SMC_hp = SMC_dependOnHSU(hp, vcode)
                    if is_SMC_hp == False:
                        print(hp, ' has a high possibility to be a HSU (bool judge) hp.')
                        is_boolJ_HSU_hp = True
                        # return

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
        pattern2_4_0 = re.compile(r'(//)*\s*(if|require)\s*[(]([^!\n]*)(!)*\s*(' + nonBool_reV + r')\s*(.*)[)]')  # if(responseHash)
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

    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  # 行数区间[19, 185] --去掉注释--> [14, 152]
    # # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)
    #
    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    hp_dict = load_json(paper_new_hp_path)
    for hp, vcode in hp_dict.items():
        # if hp == r'0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710':
        # if hp == r'0x06c2452bcb4c1c1a046c520ffbad41fb8f48442b':

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

