import re
from loadJson import load_json

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

'''
0. 转账函数
1. struct关键字: 获取一个字典, key为结构体的名字, value是一个列表, value列表中存放的是结构体中定义的变量.
2. 文件行数/文件体积 ----> 空格最大长度/源码长度 ----> 空格最大长度？
3. 
'''
# pattern_0_transfer_1 = re.compile(r'([^\s\n]*).transfer[(](.*)[)]')
# pattern_0_send_2 = re.compile(r'([^\s\n]*).send[(](.*)[)]')
# pattern_0_call_3 = re.compile(r'([^\s\n]*).call.value[(](.*)[)][(][)]')
# pattern_0_call = re.compile(r'[^\s\n]*.call.value[(].*[)](.*)')
pattern_0_call = re.compile(r'[^\s\n]*[.]call[.]value[(](.*)[)]')

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

def UC_deal(hp, vcode):
    is_UC_hp = False

    list_call = re.findall(pattern_0_call, vcode, flags=0)
    # print(list_call)
    if len(list_call) == 0:
        # continue
        return is_UC_hp

    for each_call_v in list_call:
        if ')(' not in each_call_v:
            # pattern_func_origin = re.compile(r'function ([\S\s]*?)[.]call[.]value[(]'+each_call_v+r'[)]')
            # func_origin_re = re.findall(pattern_func_origin, vcode, flags=0)
            # print(func_origin_re)
            func_splits = vcode.split('function ')
            for func_code in func_splits:
                if each_call_v in func_code:
                    if "onlyOwner" in func_code:
                        continue
                    else:
                        print(hp, ' has a high possibility to be a UC hp.')
                        is_UC_hp = True

                if is_UC_hp:
                    break
        if is_UC_hp:
            break

    return is_UC_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
            # if hp == r'0x25926eff952bdcd3cb395a5614ab5094474b2dba':
            # if hp == r'0x3d8a10ce3228cb428cb56baa058d4432464ea25d':

            # 0. 转账函数
            # list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
            # list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
            # list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
            # if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
            #     continue

            is_UC_hp = False
            list_call = re.findall(pattern_0_call, vcode, flags=0)
            # print(list_call)
            if len(list_call) == 0:
                continue

            for each_call_v in list_call:
                if ')(' not in each_call_v:
                    # pattern_func_origin = re.compile(r'function ([\S\s]*?)[.]call[.]value[(]'+each_call_v+r'[)]')
                    # func_origin_re = re.findall(pattern_func_origin, vcode, flags=0)
                    # print(func_origin_re)
                    func_splits = vcode.split('function ')
                    for func_code in func_splits:
                        if each_call_v in func_code:
                            if "onlyOwner" in func_code:
                                continue
                            else:
                                print(hp, ' has a high possibility to be a UC hp.')
                                is_UC_hp = True

                        if is_UC_hp:
                            break
                if is_UC_hp:
                    break

if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  # 行数区间[19, 185] --去掉注释--> [14, 152]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
        # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
        # if hp == r'0x7409bac00c479b0003651cc157a72d1a227eccfb':

            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            UC_deal(hp, vcode)



#0漏报, 0误, 两个新的发现 --- ID和UC的结合
'''
# honeypots_all8tyes_truePositive.json
无
'''

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json
0x25926eff952bdcd3cb395a5614ab5094474b2dba  has a high possibility to be a UC hp. √
0x32f14d71499fc2c1482eb275ec83ce5fb1d6c7ec  has a high possibility to be a UC hp. √
0x38acc6c57f3fea1d9dbffb395f3f7c3143f0d749  has a high possibility to be a UC hp. √
0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01  has a high possibility to be a UC hp. -×-- ID和UC的结合。 
0x8fd1e427396ddb511533cf9abdbebd0a7e08da35  has a high possibility to be a UC hp. -×-- ID和UC的结合。
0xda9378ae021239378752acfb1821bb6ed9309371  has a high possibility to be a UC hp. √

# 再次测试：
0x25926eff952bdcd3cb395a5614ab5094474b2dba  has a high possibility to be a UC hp. √
0x32f14d71499fc2c1482eb275ec83ce5fb1d6c7ec  has a high possibility to be a UC hp. √
0x38acc6c57f3fea1d9dbffb395f3f7c3143f0d749  has a high possibility to be a UC hp. √
0xda9378ae021239378752acfb1821bb6ed9309371  has a high possibility to be a UC hp. √
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
无
'''