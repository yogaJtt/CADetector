import re
from loadJson import load_json

'''
知识点:数词后面可以有一个后缀, wei, finney, szabo 或 ether 和 ether 相关量词 之间的转换,在以太币数量后若没有跟后缀，则缺省单位是“wei“,   如  2 ether  == 2000 finney   （这个表达式）计算结果为true。 
1. 存在var(自动推断类型)这种不指定类型的方式定义的变量; (其实uint8也是,可能会上溢为0; uint16则可能下溢为65535) (PS: var在0.5.0版本以后就不允许使用了)
2. 转账函数(transfer(), send(), call.value()()), 转账的对象可以是msg.sender, 也可以是tx.origin, 还可以是允许调用者传入的目标地址
3. 可选的: for循环或者while循环的存在,好像是一种假象, 不是必要存在的.
'''
pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')


#类型推导溢出的匹配 - position 1 --- 必要的
# pattern_1 = re.compile(r'var\s+(.*)=\s*([0-9]*);')
# pattern_1_0 = re.compile(r'var\s+([^=\n]*)\s*;+')
pattern_1_1 = re.compile(r'var\s+(.*)=\s*([0-9]+);')
# pattern_1_1 = re.compile(r'var\s+(.*)\s*=\s*.*;')  #一般是由数字或msg.value*2进行赋值---> msg.value的赋值应该不是uint8
# pattern_1_1 = re.compile(r'var\s+(.*)([=\s;0-9]*)')
# position 2 --- 必要的(之一)
pattern_2_transfer_1 = re.compile(r'.transfer[(](.*)[)]')
pattern_2_send_2 = re.compile(r'.send[(](.*)[)]')
pattern_2_call_3 = re.compile(r'.call.value[(](.*)[)][(][)]')
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

def list_filter_number(l):
    """
    去除列表中的数字
    :param l: 待过滤列表
    :return: 已过滤数字的列表
    """
    return list(filter(lambda x: not str(x).isdigit(), l))

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
def TDO_deal(hp, vcode):
    is_TDO_hp = False

    function_code_list = function_or_modifier_split(vcode, 'function')
    # print("function_code_list",function_code_list)
    for each_function in function_code_list:
        # list_var_0 = re.findall(pattern_1_0, vcode, flags=0)
        list_var_1 = re.findall(pattern_1_1, each_function[0]+each_function[1], flags=0)
        # print(list_var_0)
        # print(list_var_1)
        # if (len(list_var_0) < 1) and (len(list_var_1) < 1):
        if (len(list_var_1) < 1):
            continue
            # return is_TDO_hp
        list_var = []
        for each_var in list_var_1:
            print('each_var[1] is: ', each_var[1], each_var[1].strip(),int(each_var[1].strip()))
            if int(each_var[1].strip()) > 255:
                continue
            else:
                list_var.append(each_var[0].strip())
        if list_var == []:
            continue
            # return is_TDO_hp

        # list_var = list_var_0 + list_var_1
        # list_var = list_var_1
        # list_var = [var.strip() for var in list_var]
        # print(list_var)

        list_transfer_1 = re.findall(pattern_2_transfer_1, each_function[1], flags=0)
        list_send_2 = re.findall(pattern_2_send_2, each_function[1], flags=0)
        list_call_3 = re.findall(pattern_2_call_3, each_function[1], flags=0)
        if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
            continue
            # return is_TDO_hp

        list_transfer_send_call = list_transfer_1 + list_send_2 + list_call_3
        set_final_value_temp = set([each_value.strip() for each_value in list_transfer_send_call])
        # print(list_transfer_send_call)
        # 求交集, 即查询转账金额是否为一个var类型
        # inter_set = set(list_var).intersection(set(list_final_value))
        for final_v_temp in set_final_value_temp:
            set_final_value = set()
            # 01. 分割
            set_final_value.update(re.split(r'[+]|[-]|[*]|[/]|[(]|[)]',final_v_temp))
            # 02. 排除''
            if '' in set_final_value:
                set_final_value.remove('')
            # 03. 排除数字
            set_final_value = set(list_filter_number(set_final_value))
            # 04. 求当前分割后的长度
            first_len_of_final_value = len(set_final_value)
            # 05. 求交集, 如果长度相等, 就是TDO蜜罐
            inter_set = set(list_var).intersection(set_final_value)
            if len(inter_set) == first_len_of_final_value:
                print(hp, ' has a high possibility to be a TDO hp.')
                is_TDO_hp = True
                return is_TDO_hp
            else:
                # 06. 排除交集, 求差集
                set_final_value = set_final_value.difference(inter_set)
                already_test_value = set() #
                while set_final_value != set():
                    _value = set_final_value.pop()
                    already_test_value.add(_value)

                    payable_value = re.compile(_value + r'\s*[+]*=\s*(.*);')
                    # 01. 溯源: 寻找为转账金额变量的赋值变量
                    _value_origin_temp = re.findall(payable_value, each_function[0]+each_function[1], flags=0)
                    # print(_value_origin_0)
                    if _value_origin_temp == []:
                        continue
                    if _value_origin_temp != []:
                        # print('1',_value_origin_0)
                        _value_origin_0 = set()
                        for _origin in _value_origin_temp:
                            # 02. 分割
                            _value_origin_0.update(re.split(r'[+]|[-]|[*]|[/]|[(]|[)]', _origin))
                        # 03. 排除''
                        if '' in _value_origin_0:
                            _value_origin_0.remove('')
                        # 04. 排除数字
                        _value_origin_0 = set(list_filter_number(_value_origin_0))

                        # 05. 求当前分割后的长度
                        second_len_of_final_value = len(_value_origin_0)
                        # 06. 求交集: 为转账金额变量的（直接）赋值变量是var
                        second_inter_set = set(list_var).intersection(_value_origin_0)
                        if (len(second_inter_set) == second_len_of_final_value) and len(set_final_value) == 0:
                            print(hp, ' has a high possibility to be a TDO hp.')
                            is_TDO_hp = True
                            return is_TDO_hp
                        else:
                            # 07. 排除交集, 求差集
                            set_final_value.update(_value_origin_0.difference(second_inter_set))
                            for already_tv in already_test_value:
                                if already_tv in set_final_value:
                                    set_final_value.remove(already_tv)

        if is_TDO_hp == True:
            break
    return is_TDO_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)


    for hp, vcode in hp_dict.items():
            # if hp == r'0x2ecf8d1f46dd3c2098de9352683444a0b69eb229':
        # if hp == r'0x7409bac00c479b0003651cc157a72d1a227eccfb':

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

            is_TDO_hp = False
            # list_var_0 = re.findall(pattern_1_0, vcode, flags=0)
            list_var_1 = re.findall(pattern_1_1, vcode, flags=0)
            # print(list_var_0)
            # print(list_var_1)
            if (len(list_var_1) < 1):
                continue
            list_var = list_var_1
            list_var = [var.strip() for var in list_var]
            # print(list_var)

            list_transfer_1 = re.findall(pattern_2_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_2_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_2_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            list_transfer_send_call = list_transfer_1 + list_send_2 + list_call_3
            list_final_value = [each_value.strip() for each_value in list_transfer_send_call]
            # print(list_transfer_send_call)
            # 求交集, 即查询转账金额是否为一个var类型
            inter_set = set(list_var).intersection(set(list_final_value))
            if len(inter_set) != 0:
                print(hp, ' has a high possibility to be a TDO hp.')
                is_TDO_hp = True
            else:
                while list_final_value != []:
                    for _value in list_final_value:
                        payable_value = re.compile(_value+ r'\s*[+]*=\s*(.*);')
                        # 溯源: 寻找为转账金额变量的赋值变量
                        _value_origin_0 = re.findall(payable_value, vcode, flags=0)
                        # print(_value_origin_0)
                        if _value_origin_0 != []:
                            # print('1',_value_origin_0)
                            temp_origin_0 = _value_origin_0.copy()
                            for _origin in temp_origin_0:
                                # print('_origin', _origin, temp_origin_0)
                                if "+" in _origin:
                                    _value_origin_0 += _origin.split('+')
                                    _value_origin_0.remove(_origin)
                                if "-" in _origin:
                                    _value_origin_0 += _origin.split('-')
                                    _value_origin_0.remove(_origin)
                                if "*" in _origin:
                                    _value_origin_0 += _origin.split('*')
                                    _value_origin_0.remove(_origin)
                                if "/" in _origin:
                                    _value_origin_0 += _origin.split('/')
                                    _value_origin_0.remove(_origin)
                            _value_origin_0 = list(set(_value_origin_0))
                            # print('2', _value_origin_0)
                            # 排除''
                            temp_origin_1 = _value_origin_0.copy()
                            for _origin_1 in temp_origin_1:
                                if _origin_1 == '':
                                    _value_origin_0.remove(_origin_1)
                            # print('3', _value_origin_0)
                            # 排除数字
                            _value_origin_0 = list_filter_number(_value_origin_0)
                            # print(_value_origin_0)
                        # 为转账金额变量的（直接）赋值变量是var
                        if len(set(list_var).intersection(set(_value_origin_0))) != 0:
                            print(hp, ' has a high possibility to be a TDO hp.')
                            is_TDO_hp = True
                            break
                        else:
                            list_final_value.remove(_value)
                            list_final_value += list(set(_value_origin_0))
                    if  is_TDO_hp == True:
                        break


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
        # if hp == r'0x2ecf8d1f46dd3c2098de9352683444a0b69eb229':
        # if hp == r'0x791d0463b8813b827807a36852e4778be01b704e':
            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            TDO_deal(hp, vcode)


# 1漏报, 0误报.  漏报原因是因为源码未公开, 无法进行面向源码的检测.
# 0xf8f7d8a10f763e90e2cbefa753e411e8ac2e8e61是被漏报的, 应该可以在https://oko.palkeo.com/这个网站上找到源码
"""
# honeypots_all8tyes_truePositive.json
0x2ecf8d1f46dd3c2098de9352683444a0b69eb229  has a high possibility to be a TDO hp. √
0x752406cbfd32593fc422da69cdd702d1eaadc121  has a high possibility to be a TDO hp. √
0x791d0463b8813b827807a36852e4778be01b704e  has a high possibility to be a TDO hp. √
0xf5b1d75f4415f853fef2466a5ab8e412d593dd44  has a high possibility to be a TDO hp. √
"""

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json
0xd2ea3d1be7b482966ba8627ff009b84bac3bf51e  has a high possibility to be a TDO hp. √
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
无
'''