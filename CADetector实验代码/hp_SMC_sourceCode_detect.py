import re
from loadJson import load_json

'''
实际上, 稻草人合约是跟行为有关的, 其实应该是需要确定一下: 合约创建者创建的合约中的稻草人合约是否与传入地址对应的合约内容一致. 如果不一致就是稻草人。
对于在constructor函数中初始化的地址还可以从字节码中找到对应的地址, 也即只需要创建者创建合约这一次行为;
而对于以onlyOwner权限的函数传入的地址来说, 创建者还需要一次函数调用的行为。
比如,
0xf331f7887d31714dce936d9a9846e6afbe82e0a0这个地址就是在constructor中实现了稻草人合约的初始化, 但合约内容与对应地址内容是一致的, 因此就属于非蜜罐。
'''

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

#稻草人合约的匹配 - position 1
pattern_contractName = re.compile(r'(.*)contract\s+(.*)')
pattern_2_constructor_2 = re.compile(r"constructor(\s*)[(](.*)address (.*)[)]")  #可能也存在换行的情况, 还没有考虑进来。 参考0xf331f7887d31714dce936d9a9846e6afbe82e0a0这个良性合约地址中的function Ico(
pattern_2_function_onlyOwner_3 = re.compile(r'function (.*)[(](.*)address (.*)[)](.*)(\n*)(.*)(\n*)(.*)onlyOwner')
# pattern_2_function_onlyOwner_3 = re.compile(r'function (.*)[(](.*)address (.*)[)](.*)onlyOwner')

#稻草人合约的匹配 - position 2
pattern_3_delegatecall_1 = re.compile(r'.delegatecall[(](.*)[)]')
pattern_4_transfer_1 = re.compile(r'.transfer[(](.*)[)]')
pattern_4_send_2 = re.compile(r'.send[(](.*)[)]')
pattern_4_call_3 = re.compile(r'.call.value[(](.*)[)][(][)]')

#稻草人合约的匹配 - position 3
'''第三种其实就是隐藏状态更新，打算合并到隐藏状态更新中写'''  #真就是在HSU中实现的！

def delect_more_space_row(vcode):
    return "".join([s for s in vcode.splitlines(True) if s.strip()])

def function_or_modifier_split(vcode, splitStr='function'):
    # 1-1. 在无注释的代码中, 按function 划分
    vcode_split_by_Function_list = vcode.split(splitStr)
    # print('vcode_split_by_Function_list is: ',vcode_split_by_Function_list)
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
                ((left_BigBucket_indexs==[]) and (right_BigBucket_indexs!=[])) or \
                (right_BigBucket_indexs[0]<left_BigBucket_indexs[0]):
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

def SMC_deal(hp, vcode):
    is_SMC_hp = False

    transfer_1_list = re.findall(pattern_4_transfer_1, vcode, flags=0)
    send_2_list = re.findall(pattern_4_send_2, vcode, flags=0)
    call_3_list = re.findall(pattern_4_call_3, vcode, flags=0)
    if ((len(transfer_1_list) == 0) and (len(send_2_list) == 0) and (len(call_3_list) == 0)):
        return is_SMC_hp

    # 1. 获取contract name
    contractName_set = set()
    contractName_list_temp = re.findall(pattern_contractName, vcode, flags=0)
    for contractName in contractName_list_temp:
        if contractName[0] != '':
            continue
        _contract_name = contractName[1].split('{')[0].strip()
        contractName_set.add(_contract_name)
    # print(contractName_set,'**********')

    # 合约大于等于2个时, 执行构造函数型和onlyOwner型的检测
    first_two_detect_isOver = False
    if len(contractName_set) >= 2:
        # 2. 分割函数 （不考虑modifier）
        function_code_list = function_or_modifier_split(vcode, 'function')  #2-tuple List
        function_code_list_need = function_or_modifier_split(vcode, 'constructor(')  #2-tuple List
        function_code_list_modifier = function_or_modifier_split(vcode, 'modifier ')  #2-tuple List
        # 为constructor(分割后的结果加上(
        function_code_list_need = [('('+each_fNeed[0],each_fNeed[1]) for each_fNeed in function_code_list_need]

        # 2-1. 全局代码
        global_var_code = vcode
        for function_code in function_code_list:
            global_var_code = global_var_code.replace(function_code[0] + function_code[1], '')
        for function_code_need in function_code_list_need:
            global_var_code = global_var_code.replace(function_code_need[0] + function_code_need[1], '')
        for function_code_mf in function_code_list_modifier:
            global_var_code = global_var_code.replace(function_code_mf[0] + function_code_mf[1], '')
        # print(global_var_code,"WWWWWWW")
        # 2-2. 从全局代码中检查-合约初始定义
        for each_cN in contractName_set:
            pattern_cN_init = re.compile(r'(.*)(' + each_cN + r'\s+.*);')
            cN_init_result = re.findall(pattern_cN_init, global_var_code, flags=0)
            cN_init_name_set = set()
            for each_cN_init in cN_init_result:
                if (each_cN_init[0] != '') and (each_cN_init[0][-1] != ' ') and \
                        (each_cN_init[0][-1] != '\n') and (each_cN_init[0][-1] != '\t'):
                    continue
                # 获取合约初始定义的名称
                cN_init_name_set.add(each_cN_init[1].split('=')[0].strip())
        # 必须要有全局的初始化
        if cN_init_name_set == set():
            first_two_detect_isOver = True  #意味着一定不是构造函数型和onlyOwner型, 但是delegatecall还没检查

        if first_two_detect_isOver == False:
            # 3. 对构造函数和onlyOwner权限函数 - 只保留这两类函数
            for each_func_2_tuple in function_code_list:
                # 与合约同名函数-构造函数
                for each_contract_name in contractName_set:
                    if (each_func_2_tuple[0].split('(')[0].strip() == each_contract_name):
                        function_code_list_need.append(each_func_2_tuple)
                # onlyOwner权限函数
                if 'onlyOwner' in each_func_2_tuple[0]:
                    function_code_list_need.append(each_func_2_tuple)
            # print(function_code_list_need)
            # 4. 为每个函数检查形参是否用于初始化合约
            for func_need_2_tuple in function_code_list_need:
                # 获取函数形参地址集合
                func_addr_para_set = set()
                para_content = func_need_2_tuple[0].split('(')[1].split(')')[0]
                # 切分每个形参
                para_list = para_content.split(',')
                for each_para in para_list:
                    if 'address ' in each_para:
                        func_addr_para_set.add(each_para.split()[-1])
                if func_addr_para_set == set():
                    continue
                # 函数体中检查对初始化合约的实例化
                for cN_init_str in cN_init_name_set:
                    # 001. 分割
                    cN_init_str_list = cN_init_str.split()
                    if len(cN_init_str_list) < 2:
                        continue
                    # 002. 模板 - 获取结果为初始化的地址内容, 需要与形参集合求交集
                    if (")" in cN_init_str_list[-1]) or ("(" in cN_init_str_list[-1]):
                        continue
                    cN_instance_template = re.compile(cN_init_str_list[-1] + '\s*=\s*' + cN_init_str_list[0] + '[(](.*)[)]')
                    cN_instance_result = re.findall(cN_instance_template, func_need_2_tuple[1], flags=0)
                    if len(cN_instance_result) != 1:
                        continue
                    # 不为空的话, 只能有一个参数, 即列表长度为1:
                    if cN_instance_result[0] in func_addr_para_set:
                        print(hp, ' has a high possibility to be a SMC hp (constructor or onlyOwner type).')
                        is_SMC_hp = True
                        return is_SMC_hp

    # if hp == r'0xa91a453abde404a303fb118c46e00c8f630216a9':
    delegatecall_1_list = re.findall(pattern_3_delegatecall_1, vcode, flags=0)
    # transfer_1_list = re.findall(pattern_4_transfer_1, vcode, flags=0)
    # send_2_list = re.findall(pattern_4_send_2, vcode, flags=0)
    # call_3_list = re.findall(pattern_4_call_3, vcode, flags=0)
    if (len(delegatecall_1_list) != 0): #and \
           # ((len(transfer_1_list) != 0) or (len(send_2_list) != 0) or (len(call_3_list) != 0)):
        print(hp, ' has a high possibility to be a SMC hp (delegatecall type).')
        is_SMC_hp = True
        return is_SMC_hp

    return is_SMC_hp


def main():
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_dict = load_json(hp_8type_path)
    for hp, vcode in hp_8type_dict.items():
        # print(hp)
        #     if hp == r'0x95be22039da3114d17a38b9e7cd9b3576de83924':

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

            contractName_list = re.findall(pattern_contractName, vcode, flags=0)
            constructor_list_1 = []
            for contractName in contractName_list:
                if contractName[0] != '':
                    continue
                pattern_2_constructor_1 = re.compile(r'function ' + contractName[1].strip() + '([ ]*)[(](.*)address (.*)[)]')
                constructor_list_1 += re.findall(pattern_2_constructor_1, vcode, flags=0)
            constructor_list_2 = re.findall(pattern_2_constructor_2, vcode, flags=0)
            if (len(constructor_list_1) != 0) or (len(constructor_list_2) != 0):
                print(hp, ' has a high possibility to be a SMC hp (constructor type).')

            constructor_list_3 = re.findall(pattern_2_function_onlyOwner_3, vcode, flags=0)
            if (len(constructor_list_3) != 0):
                for list_i in range(len(constructor_list_3)):
                    addr_name = constructor_list_3[list_i][2]
                    pattern_2_function_onlyOwner_addrName = re.compile(r'(.*)=(.*)[(]'+addr_name+'[)];')
                    if (len(re.findall(pattern_2_function_onlyOwner_addrName, vcode, flags=0))!=0):
                        print(hp, ' has a high possibility to be a SMC hp (function_onlyOwner type).')
                        break


            # if hp == r'0xa91a453abde404a303fb118c46e00c8f630216a9':
            delegatecall_1_list = re.findall(pattern_3_delegatecall_1, vcode, flags=0)
            transfer_1_list = re.findall(pattern_4_transfer_1, vcode, flags=0)
            send_2_list = re.findall(pattern_4_send_2, vcode, flags=0)
            call_3_list = re.findall(pattern_4_call_3, vcode, flags=0)
            if (len(delegatecall_1_list) != 0) and  \
                 ((len(transfer_1_list) != 0) or (len(send_2_list) != 0) or (len(call_3_list) != 0)):
                print(hp, ' has a high possibility to be a SMC hp (delegatecall type).')

            # break

if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # hp_dict = load_json(paper_new_hp_path)
    for hp, vcode in hp_dict.items():
        # print(hp)
        # if hp == r'0x23a91059fdc9579a9fbd0edc5f2ea0bfdb70deb4':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            SMC_deal(hp, vcode)


'''
# honeypots_all8tyes_truePositive.json 除HSU式的SMC蜜罐（见HSU检测脚本）, 当前结果为0误报、0漏报
0x23a91059fdc9579a9fbd0edc5f2ea0bfdb70deb4  has a high possibility to be a SMC hp (constructor type). √
0x23f890c412f3f06784a30ba40ed4832a0fca55f0  has a high possibility to be a SMC hp (delegatecall type). √
0x463f235748bc7862deaa04d85b4b16ac8fafef39  has a high possibility to be a SMC hp (constructor type). √
0x477d1ee2f953a2f85dbecbcb371c2613809ea452  has a high possibility to be a SMC hp (delegatecall type). √
0x62d5c4a317b93085697cfb1c775be4398df0678c  has a high possibility to be a SMC hp (delegatecall type). √
0x7a7d08bcb2faf27414e86ecf9a0351d928054b6b  has a high possibility to be a SMC hp (delegatecall type). √
0x7a8721a9d64c74da899424c1b52acbf58ddc9782  has a high possibility to be a SMC hp (function_onlyOwner type). √
0x8c7777c45481dba411450c228cb692ac3d550344  has a high possibility to be a SMC hp (constructor type). √
0x941d225236464a25eb18076df7da6a91d0f95e9e  has a high possibility to be a SMC hp (constructor type). √
0x95d34980095380851902ccd9a1fb4c813c2cb639  has a high possibility to be a SMC hp (constructor type). √
0xa5d6accc5695327f65cbf38da29198df53efdcf0  has a high possibility to be a SMC hp (constructor type). √
0xa91a453abde404a303fb118c46e00c8f630216a9  has a high possibility to be a SMC hp (delegatecall type). √
0xb4c05e6e4cdb07c15095300d96a5735046eef999  has a high possibility to be a SMC hp (constructor type). √
0xb5e1b1ee15c6fa0e48fce100125569d430f1bd12  has a high possibility to be a SMC hp (constructor type). √
0xb93430ce38ac4a6bb47fb1fc085ea669353fd89e  has a high possibility to be a SMC hp (constructor type). √
0xbabfe0ae175b847543724c386700065137d30e3b  has a high possibility to be a SMC hp (constructor type). √
0xbaf51e761510c1a11bf48dd87c0307ac8a8c8a4f  has a high possibility to be a SMC hp (constructor type). √
0xd116d1349c1382b0b302086a4e4219ae4f8634ff  has a high possibility to be a SMC hp (constructor type). √
0xdad02644b70cbb20dec56d25282ddc65bb7805a1  has a high possibility to be a SMC hp (delegatecall type). √
0xe610af01f92f19679327715b426c35849c47c657  has a high possibility to be a SMC hp (constructor type). √
0xfa8bb2a68c67e39409cd336d1a8024a2ad9a62ff  has a high possibility to be a SMC hp (delegatecall type). √
0xff5a11c0442028ee2a60d31e6ebb3cbac121ffe5  has a high possibility to be a SMC hp (delegatecall type). √
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
0x65e5909d665cbda128de96aa9eb0160729eac1b0  has a high possibility to be a SMC hp (constructor type). √
'''

'''
# honeypots_paper_new_addr2SouceCode.json 通过HSU脚本检测到
0x85179ac15aa94e3ca32dd1cc04664e9bb0062115  has a high possibility to be a SMC (depended on HSU) hp.
0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b  has a high possibility to be a SMC (depended on HSU) hp.
------漏报--- 消除漏报的方法很简单, 只需要在当前SMC的检测脚本中将对转账指令的判断至于delegatecall绑定即可, 但这里在分析之后, 我认为时XGBoost他们的误报, 攻击者看不到明确的获利入口, 这样是无法吸引新手黑客的。
0xa6c76471cc89cff4e65cc1fc36613f3c31e4d0d1,Straw  Man  Contract  (SMC)
0xd754ee6a9e8964602f48e11971e79d0b2f6452d5,Straw  Man  Contract  (SMC)
0x2f846758e479ee7e0bd87cea5b9f8f3e314c6bd9,Straw  Man  Contract  (SMC)
'''


