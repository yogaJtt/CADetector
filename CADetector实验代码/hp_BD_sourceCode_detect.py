import re
from loadJson import load_json

#对BD也不做token判断了
pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
# pattern_exclude_noToken_1 = re.compile(r'(\s+token\s+.*)', re.IGNORECASE)  #可能并不严谨
# pattern_exclude_noToken_2 = re.compile(r'(token.*)', re.IGNORECASE)  #可能并不严谨
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

#余额紊乱的匹配 - position 1
# pattern3 = re.compile(r'msg.value(.*)>\s*this.balance')
pattern3 = re.compile(r'msg.value\s*>(.*)')
#余额紊乱的匹配 - postion 2
pattern4 = re.compile(r'.transfer[(]this[.]balance\s*[+]\s*msg[.]value[)]')  #或者msg.value+this.balance, 或者this.balance + xx wei
pattern5 = re.compile(r'.send[(]this[.]balance\s*[+]\s*msg[.]value[)]')
pattern6 = re.compile(r'.call[.]value[(]this[.]balance\s*[+]\s*msg[.]value[)][(][)]')
pattern4_1 = re.compile(r'.transfer[(]msg[.]value\s*[+]\s*this[.]balance[)]')  #或者msg.value+this.balance, 或者this.balance + xx wei
pattern5_1 = re.compile(r'.send[(]msg[.]value\s*[+]\s*this[.]balance[)]')
pattern6_1 = re.compile(r'.call[.]value[(]msg[.]value\s*[+]\s*this[.]balance[)][(][)]')

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


def BD_deal(hp, vcode):
    is_BD_hp = False

    if (len(re.findall(pattern3, vcode, flags=0)) != 0) and \
            ((len(re.findall(pattern4, vcode, flags=0)) != 0) or (len(re.findall(pattern4_1, vcode, flags=0)) != 0) or \
             (len(re.findall(pattern5, vcode, flags=0)) != 0) or (len(re.findall(pattern5_1, vcode, flags=0)) != 0) or \
             (len(re.findall(pattern6, vcode, flags=0)) != 0) or (len(re.findall(pattern6_1, vcode, flags=0)) != 0)):
        print(hp, ' has a high possibility to be a BD hp.')
        is_BD_hp = True

    return is_BD_hp


def main():
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_8type_dict = load_json(hp_8type_path)
    for hp, vcode in hp_8type_dict.items():
            # if hp == '0xfb6e71e0800bccc0db8a9cf326fe3213ca1a0ea0':

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

            if (len(re.findall(pattern3, vcode, flags=0)) != 0) and \
                ((len(re.findall(pattern4, vcode, flags=0)) != 0) or (len(re.findall(pattern4_1, vcode, flags=0)) != 0) or\
                (len(re.findall(pattern5, vcode, flags=0)) != 0) or (len(re.findall(pattern5_1, vcode, flags=0)) != 0) or\
                (len(re.findall(pattern6, vcode, flags=0)) != 0) or (len(re.findall(pattern6_1, vcode, flags=0)) != 0)):
                print(hp,' has a high possibility to be a BD hp.')

if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'  # 行数区间[53, 201] --去掉注释--> [16, 83]
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
        # if hp == '0xfb6e71e0800bccc0db8a9cf326fe3213ca1a0ea0':
            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            BD_deal(hp, vcode)

'''
honeypots_all8tyes_truePositive.json --- 0漏报、0误报  (20个)
0x0bf0f154b176c5d90f24e506f10f7f583eb5334d  has a high possibility to be a BD hp.
0x0e77cb9d68b8bf3cc41561f8eda6c71e4a4b9ef7  has a high possibility to be a BD hp.
0x15d0e6cedd8ecc39daa60c63a3a5830eeca7d720  has a high possibility to be a BD hp.
0x1ebf20031b03b80e5f6fdbeb9f86d44145224006  has a high possibility to be a BD hp.
0x35c3034556b81132e682db2f879e6f30721b847c  has a high possibility to be a BD hp.
0x3bafb3af16203c817ee9208c6b8a748398dae689  has a high possibility to be a BD hp.
0x3e013fc32a54c4c5b6991ba539dcd0ec4355c859  has a high possibility to be a BD hp.
0x5aa88d2901c68fda244f1d0584400368d2c8e739  has a high possibility to be a BD hp.
0x5bb52e85c21ca3df3c71da6d03be19cff89e7cf9  has a high possibility to be a BD hp.
0x69bfbf000bd39444af2efba733829b04211252bc  has a high possibility to be a BD hp.
0x92e63be3a88df80f64ba4f829dd7ddf97e8b750b  has a high possibility to be a BD hp.
0x9cdfd805d73b4837bf3f7b2296996aaecc881e86  has a high possibility to be a BD hp.
0x9efc7a38552e63534a8e9b9558adabd73297f91d  has a high possibility to be a BD hp.
0x9f54d912a029380f2743aaf4ddd28c3f207cd719  has a high possibility to be a BD hp.
0xc7e4a9147601fdbc7d1c2fb8b6c2ffcb2469f293  has a high possibility to be a BD hp.
0xc9c8ef2588647e6f5acb6aaee637264d2632609d  has a high possibility to be a BD hp.
0xdf77e4a81fba17e0cc39dba521aa4167f388ed7c  has a high possibility to be a BD hp.
0xe0527863df8abcb3caca7da329eb9c747822aa98  has a high possibility to be a BD hp.
0xe26e90598190a98c92c75204c9a4ecfe5983f8e0  has a high possibility to be a BD hp.
0xfd1e3d3e641f224ce8e1117866cf3f01ed2d5d9f  has a high possibility to be a BD hp.
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''


'''
honeypots_more13_FromXGBootst_truePositive.json
无
'''

'''
honeypots_paper_new_addr2SouceCode.json
0xd7e3c6d99bc2ccdb6fe54b8a5888d14319e65c36  has a high possibility to be a BD hp.
'''