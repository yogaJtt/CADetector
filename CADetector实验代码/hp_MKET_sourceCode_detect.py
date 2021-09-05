import re
from loadJson import load_json

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')

'''
0. 转账函数
1. 识别或判断字符串中包含某些语言的字符
2. 还有一种: 相似字符混淆（0、O、o，1、l） ---- 没做
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


# pattern_1 = re.compile(r'(.*е.*)')
def contains_invalid_lang_chs(check_str):
    check_str=check_str.strip()
    return any((u'\u0600' <= c <= u'\u06FF') or (u'\u1100' <= c <= u'\u11FF') or (u'\u3040' <= c <= u'\u309F') or \
            (u'\u30A0' <= c <= u'\u30FF') or (u'\u31F0' <= c <= u'\u31FF') or (u'\uAC00' <= c <= u'\uD7AF') or \
            (u'\u0400' <= c <= u'\u052F') or (u'\u68b0' == c) for c in check_str)

# pattern_1_list = []
# for i in range(0x0000, 0x10000):
#     x = hex(i)[2:]
#     x = r'\u'+(4-len(x))*'0' + x
#     pattern_1_list.append(re.compile(r'(.*'+x[1:]+'.*)'))


def MKET_deal(hp, vcode):
    is_MKET_hp = False

    # 0. 转账函数
    list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
    list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
    list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
    if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
        # continue
        return is_MKET_hp

    eachLine_list = vcode.split('\n')
    special_string_set = set()
    for eachLine in eachLine_list:
        eachLine = eachLine.strip()
        if contains_invalid_lang_chs(eachLine) == True:
            # print(eachLine)
            special_char = ''
            comment_symbol = -1
            for c_i in range(len(eachLine)):
                if '//' == eachLine[c_i: c_i + 2]:
                    comment_symbol = c_i
                # (u'\u4e00' <= eachLine[c_i] <= u'\u9fa5') 代表的是对中文的匹配
                if ((u'\u0600' <= eachLine[c_i] <= u'\u06FF') or (u'\u1100' <= eachLine[c_i] <= u'\u11FF') or (u'\u3040' <= eachLine[c_i] <= u'\u309F') or \
                    (u'\u30A0' <= eachLine[c_i] <= u'\u30FF') or (u'\u31F0' <= eachLine[c_i] <= u'\u31FF') or (u'\uAC00' <= eachLine[c_i] <= u'\uD7AF') or \
                    (u'\u0400' <= eachLine[c_i] <= u'\u052F') or (u'\u68b0' == eachLine[c_i])): #(u'\u4e00' <= eachLine[c_i] <= u'\u9fa5')):
                    if (comment_symbol < 0) or (comment_symbol > c_i):
                        special_char = eachLine[c_i]
                        print('special_char is: ',special_char, '*****eachLine is:', eachLine)
                    # 这里其实可以每一行找出特殊字符后做个匹配模板，进行匹配, 做分割之后，找字符串中排除特殊字符后的匹配字符串。
                re.compile('(\s|\"|\'|=|;|,)+' + special_char + '(\s|\"|\'|=|;|,)+')
            if special_char == '':
                continue
            pattern_1 = re.compile(r'([A-Za-z0-9_]*)' + special_char + r'([A-Za-z0-9_]*)')
            string_around = re.findall(pattern_1, eachLine, flags=0)[0]
            # print(string_around)
            if string_around != []:
                print(hp, ' has a high possibility to be a MKET hp.')
                is_MKET_hp = True
                return is_MKET_hp

    return is_MKET_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_dict = load_json(hp_8type_path)

    # paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    # hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
            # if hp == r'0xa379eda47d90fb4bc2dfa54556421ff0f198ca47':
            # if hp == r'0x3d8a10ce3228cb428cb56baa058d4432464ea25d':

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

            # 0. 转账函数
            list_transfer_1 = re.findall(pattern_0_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_0_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_0_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            # #删除多行注释
            # # print(hp)
            # patterrn_multiLine_comment = re.compile(r"/[*]([\s\S]*)[*]/")
            # multiLine_comments = re.findall(patterrn_multiLine_comment, vcode, flags=0)
            # # print(multiLine_comments)
            # for multiLine in multiLine_comments:
            #     vcode = vcode.replace(multiLine, '')
            # # print(vcode)

            eachLine_list = vcode.split('\n')
            for eachLine in eachLine_list:
                eachLine = eachLine.strip()
                if contains_invalid_lang_chs(eachLine) == True:
                    # print(eachLine)
                    special_char = ''
                    comment_symbol = -1
                    for c_i in range(len(eachLine)):
                        if '//' == eachLine[c_i: c_i+2]:
                            comment_symbol = c_i
                        if ((u'\u0600' <= eachLine[c_i] <= u'\u06FF') or (u'\u1100' <= eachLine[c_i] <= u'\u11FF') or (u'\u3040' <= eachLine[c_i] <= u'\u309F') or \
                            (u'\u30A0' <= eachLine[c_i] <= u'\u30FF') or (u'\u31F0' <= eachLine[c_i] <= u'\u31FF') or (u'\uAC00' <= eachLine[c_i] <= u'\uD7AF') or \
                            (u'\u0400' <= eachLine[c_i] <= u'\u052F') or (u'\u4e00' <= eachLine[c_i] <= u'\u9fa5')):
                            if (comment_symbol < 0) or (comment_symbol > c_i):
                                special_char = eachLine[c_i]
                    if special_char == '':
                        continue
                    pattern_1 = re.compile(r'([A-Za-z0-9_]*)'+special_char+r'([A-Za-z0-9_]*)')
                    string_around = re.findall(pattern_1, eachLine, flags=0)[0]
                    # print(string_around)
                    if string_around != []:
                        print(hp, ' has a high possibility to be a MKET hp.')
                    # 后面本想用string_around来做匹配的, 但是考虑到special_char可能单独存在, 前后没有相邻的英文字符或数字,所以就不匹配, 默认只要有特殊字符,就告警.
                    # pattern_2 = re.compile()


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_paper_new_addr2SouceCode.json'
    hp_dict = load_json(paper_new_hp_path)

    for hp, vcode in hp_dict.items():
        # if hp == r'0xa379eda47d90fb4bc2dfa54556421ff0f198ca47':
        # if hp == r'0x3d8a10ce3228cb428cb56baa058d4432464ea25d':
        vcode = common_deal(hp, vcode)
        if vcode == 0:
            continue

        MKET_deal(hp, vcode)


#0漏报, 0误报
'''
# honeypots_all8tyes_truePositive.json
无
'''

'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json
0xf5615138a7f2605e382375fa33ab368661e017ff has a high possibility to be a MKET hp.
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
0xf5615138a7f2605e382375fa33ab368661e017ff  has a high possibility to be a MKET hp. --- 这个（honeypots_all8tyes_FalsePositive.json）判断错误 --- 属于新型蜜罐
'''