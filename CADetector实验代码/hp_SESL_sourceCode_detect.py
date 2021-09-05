import re
from loadJson import load_json

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')


'''
1.有空字符串, ""后面一般跟着的还是msg.sender(或者调用者传入的地址, 或者tx.origin), 
               甚至还有可能是以太币的数额(比如:本来你给我转进来1ether, 我给你转回去10ether,但是用空字符串一搞,我给你转回去的是0.1ether)
2.版本<0.4.12, 但有时候源码中不一定有 --- 
3.有转账函数
'''
#跳过空字符串的匹配 - position 1 --- 必要的
# pattern_1 = re.compile(r'[(]""\s*,\s*(.*)[)];')
pattern_1 = re.compile(r'[(](.*)\"\"\s*,\s*(.*)[)];')
# position 2 --- 必要的(之一)
pattern_2_transfer_1 = re.compile(r'.transfer[(](.*)[)]')
pattern_2_send_2 = re.compile(r'.send[(](.*)[)]')
pattern_2_call_3 = re.compile(r'.call.value[(](.*)[)][(][)]')
#position3  <0.4.12版本之前 -- 如果数据库里有这个数据,就必须搞上,没有的话,就算了   ---- 一共也没几个蜜罐,手动给他们加上版本号
pattern_3 = re.compile(r'pragma solidity \^([.0-9]*);')

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

def SESL_deal(hp, vcode):
    is_SESL_hp = False

    list_empty_literal = re.findall(pattern_1, vcode, flags=0)
    # print(len(list_empty_literal))
    if len(list_empty_literal) < 1:
        # continue
        return is_SESL_hp

    list_transfer_1 = re.findall(pattern_2_transfer_1, vcode, flags=0)
    list_send_2 = re.findall(pattern_2_send_2, vcode, flags=0)
    list_call_3 = re.findall(pattern_2_call_3, vcode, flags=0)
    if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
        # continue
        return is_SESL_hp

    list_compiler = re.findall(pattern_3, vcode, flags=0)
    if len(list_compiler) == 0:
        # continue
        return is_SESL_hp
    minor_version = int(list_compiler[0].split('.')[1])
    patch_version = int(list_compiler[0].split('.')[2])
    minor_patch_v = minor_version * 100 + patch_version
    if minor_patch_v < 412:
        print(hp, ' has a high possibility to be a SESL hp.')
        is_SESL_hp = True
        return is_SESL_hp

    return is_SESL_hp


def main():
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_8type_dict = load_json(hp_8type_path)
    for hp, vcode in hp_8type_dict.items():
            # if hp == r'0x251848c3fc50274f5fda449919f083dc937b48b2':

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

            list_empty_literal = re.findall(pattern_1, vcode, flags=0)
            # print(len(list_empty_literal))
            if len(list_empty_literal) < 1:
                continue

            list_transfer_1 = re.findall(pattern_2_transfer_1, vcode, flags=0)
            list_send_2 = re.findall(pattern_2_send_2, vcode, flags=0)
            list_call_3 = re.findall(pattern_2_call_3, vcode, flags=0)
            if (len(list_transfer_1) == 0) and (len(list_send_2) == 0) and (len(list_call_3) == 0):
                continue

            list_compiler = re.findall(pattern_3, vcode, flags=0)
            if len(list_compiler) == 0:
                continue
            minor_version = int(list_compiler[0].split('.')[1])
            patch_version = int(list_compiler[0].split('.')[2])
            minor_patch_v = minor_version*100 + patch_version
            if minor_patch_v < 412:
                print(hp,' has a high possibility to be a SESL hp.')


if __name__ == '__main__':
    hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    hp_8type_dict = load_json(hp_8type_path)
    for hp, vcode in hp_8type_dict.items():
        # if hp == r'0x251848c3fc50274f5fda449919f083dc937b48b2':
        vcode = common_deal(hp, vcode)
        if vcode == 0:
            continue

        SESL_deal(hp, vcode)


'''
# 0误报 0漏报  ---- 漏报的合约没有开源源码,只有字节码,不在我们关注的范畴之内.
0x251848c3fc50274f5fda449919f083dc937b48b2  has a high possibility to be a SESL hp. √
0x7bc51b19abe2cfb15d58f845dad027feab01bfa0  has a high possibility to be a SESL hp. √
0x858c9eaf3ace37d2bedb4a1eb6b8805ffe801bba  has a high possibility to be a SESL hp. √
0xa0174f796d3b901adaa16cfbb589330462be0329  has a high possibility to be a SESL hp. √
0xa395480a4a90c7066c8ddb5db83e2718e750641c  has a high possibility to be a SESL hp. √
0xaa12936a79848938770bdbc5da0d49fe986678cc  has a high possibility to be a SESL hp. √
0xd022969da8a1ace11e2974b3e7ee476c3f9f99c6  has a high possibility to be a SESL hp. √
0xe63760e74ffd44ce7abdb7ca2e7fa01b357df460  has a high possibility to be a SESL hp. √
0xf4ac238121585456dee1096fed287f4d8906d519  has a high possibility to be a SESL hp. √   --- 也不算与HSU的结合， 重点在managers只有一个成员, 就是Shark的创建者, 较复杂逻辑的SESL.
'''

'''
paper_new_honeypot.csv中没有发现新的hp
'''

'''
honeypots_all8tyes_FalsePositive.json -- 理论上就是无
无
'''

'''
honeypots_more13_FromXGBootst_truePositive.json 
0x0xf03abd62c2d8b3a90db84b41ce3118c1291a198f  has a high possibility to be a SESL hp.  √
'''