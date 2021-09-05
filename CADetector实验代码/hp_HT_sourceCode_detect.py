import re
from loadJson import load_json

# 对于HT, 我想应该把token删掉
# pattern_exclude_noToken_1 = re.compile(r'(\s+token\s+.*)', re.IGNORECASE)  #可能并不严谨
# pattern_exclude_noToken_2 = re.compile(r'(token.*)', re.IGNORECASE)  #可能并不严谨
pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

'''
0. 转账函数
1. 文件行数/文件体积 ----> 空格最大长度/源码长度 ----> 空格最大长度？

'''
pattern_0_transfer_1 = re.compile(r'([^\s\n]*).transfer[(](.*)[)]')
pattern_0_send_2 = re.compile(r'([^\s\n]*).send[(](.*)[)]')
pattern_0_call_3 = re.compile(r'([^\s\n]*).call.value[(](.*)[)][(][)]')

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

def HT_deal(hp, vcode):
    is_HT_hp = False

    # 0. 转账函数
    list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
    list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
    list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
    if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
        # continue
        return False

    # print(len(vcode))
    space_str_len = 0
    for i in range(5000):
        if str(' ' * i) not in vcode:
            break
        else:
            space_str_len = i
    # print(space_str_len)

    if space_str_len > 300:
        print(hp, ' has a high possibility to be a HT hp.', space_str_len)
        is_HT_hp = True

    return is_HT_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
            # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
            # if hp == r'0x3d8a10ce3228cb428cb56baa058d4432464ea25d':

            # 0. 转账函数
            list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            # print(len(vcode))
            space_str_len = 0
            for i in range(5000):
                if str(' ' * i) not in vcode:
                    break
                else:
                    space_str_len = i
            # print(space_str_len)

            if space_str_len > 300:
                print(hp, ' has a high possibility to be a HT hp.', space_str_len)


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
        # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
        # if hp == r'0x3d8a10ce3228cb428cb56baa058d4432464ea25d':
            vcode = common_deal(hp, vcode)
            if vcode == 0:
                continue

            HT_deal(hp, vcode)


#0漏报, 0误报
'''
# honeypots_all8tyes_truePositive.json
0x3d8a10ce3228cb428cb56baa058d4432464ea25d  has a high possibility to be a HT hp. 369
0x3f2ef511aa6e75231e4deafc7a3d2ecab3741de2  has a high possibility to be a HT hp. 3460
0x55654a38372617aedd583009f76e28700e48fdad  has a high possibility to be a HT hp. 799
0x78c2a1e91b52bca4130b6ed9edd9fbcfd4671c37  has a high possibility to be a HT hp. 3460
0x7a4349a749e59a5736efb7826ee3496a2dfd5489  has a high possibility to be a HT hp. 3460
0x806a6bd219f162442d992bdc4ee6eba1f2c5a707  has a high possibility to be a HT hp. 2823
0xc7f4ade4874e06a20fab9c5dc4f1dd8b6d85faf2  has a high possibility to be a HT hp. 2823
0xd2018bfaa266a9ec0a1a84b061640faa009def76  has a high possibility to be a HT hp. 3004
0xdb1c55f6926e7d847ddf8678905ad871a68199d2  has a high possibility to be a HT hp. 1210
0xe4eabdca81e31d9acbc4af76b30f532b6ed7f3bf  has a high possibility to be a HT hp. 3460
0xe82f0742a71a02b9e9ffc142fdcb6eb1ed06fb87  has a high possibility to be a HT hp. 1210
0xf70d589d76eebdd7c12cc5eec99f8f6fa4233b9e  has a high possibility to be a HT hp. 3460
'''

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json
0x2bb5b9f83391d4190f8b283be0170570953c5a8e  has a high possibility to be a HT hp. 742   √
0x31fd65340a3d272e21fd6ac995f305cc1ad5f42a  has a high possibility to be a HT hp. 742   √
0x55bec5649fbb5f5be831ee5b0f7a8a8f02b25144  has a high possibility to be a HT hp. 1218  √
0x5abb8dda439becbd9585d1894bd96fd702400fa2  has a high possibility to be a HT hp. 742   √
0x61dc347d7fa0f6e34c3112faf83a2e468d681f68  has a high possibility to be a HT hp. 887   √
0x66385555fc121d18dc95ec3a8ecd51ab2b660de5  has a high possibility to be a HT hp. 734   √
0xc1fbb18de504e0bba8514ff741f3109d790ed087  has a high possibility to be a HT hp. 4467  √
0xcfebf8c78de81f804a694f4bb401e5d76b298be5  has a high possibility to be a HT hp. 901   √
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json
0x1aa635be048b85716ebf9093d1bde5aa7df9fefc  √
'''