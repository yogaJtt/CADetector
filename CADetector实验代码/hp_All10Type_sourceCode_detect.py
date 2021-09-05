import re
from loadJson import load_json
from saveJson import save_json
from hp_MKET_sourceCode_detect import MKET_deal
from hp_UC_sourceCode_detect import UC_deal
from hp_TDO_sourceCode_detect import TDO_deal
from hp_SESL_sourceCode_detect import SESL_deal
from hp_HT_sourceCode_detect import HT_deal
from hp_US_sourceCode_detect import US_deal
from hp_BD_sourceCode_detect import BD_deal
from hp_ID_sourceCode_detect import ID_deal
from hp_SMC_sourceCode_detect import SMC_deal
from hp_HSU_sourceCode_detect import HSU_deal

pattern_exclude_1 = re.compile(r'(.*)library SafeMath\s*(.*)')
pattern_exclude_noPayable = re.compile(r'(.*payable.*)') #payable的强制要求是从0.4.x才要求的。
# pattern_exclude_noInterface = re.compile(r'function([\s\S]*?)[)];')
pattern_exclude_noInterface = re.compile(r'function([^{}]*?)[)];')
pattern_compiler = re.compile(r'pragma solidity \^([.0-9]*);')
pattern_string = re.compile(r'(["].*["])')

import csv
def write_csv(data_row):
    path  = "hp_code_lines.csv"
    with open(path,'a+') as f:
        csv_write = csv.writer(f)
        # data_row = ["1","2"]
        csv_write.writerow(data_row)

def delect_more_space_row(vcode):
    return "".join([s for s in vcode.splitlines(True) if s.strip()])

def common_deal(hp, vcode):
    # token-1 不太严谨， 如果后续影响检测，可考虑删除，这里的目的纯粹是为了排除复杂逻辑
    # token_re_1 = re.findall(pattern_exclude_noToken_1, vcode, flags=0)
    # print(token_re_1)
    # print(len(token_re_1))

    # 删除多行注释
    # print(hp)
    patterrn_multiLine_comment = re.compile(r"(/[*][\s\S]*?[*]/)")
    multiLine_comments = re.findall(patterrn_multiLine_comment, vcode, flags=0)
    # print("YYY",multiLine_comments,"****")
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
    if rows_len > 155:
        # continue
        return 0

    # 保存csv文件
    write_csv([rows_len, 'non-honeypot'])

    # 进一步删除注释
    vcode = vcode.replace('/**/', '')
    pattern_with_comment = re.compile(r'(//.*)')
    with_comment_re = re.findall(pattern_with_comment, vcode, flags=0)
    for i in with_comment_re:
        vcode = vcode.replace(i, '')

    string_result = re.findall(pattern_string, vcode, flags=0)
    # print('string_result is: ', string_result)
    for each_str in string_result:
        if ('function' in each_str) or ('modifier ' in each_str) or ('event ' in each_str) or ('struct ' in each_str):
            vcode = vcode.replace(each_str, '')

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

    if rows_len > 60:
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

    pattern_msg_value_0 = re.compile(r'(msg.value\s*[>\|<]+.*)')
    pattern_msg_value_1 = re.compile(r'([+\|+=\|=]\s*msg.value.*)')
    result_msg_value_0 = re.findall(pattern_msg_value_0, vcode, 0)
    result_msg_value_1 = re.findall(pattern_msg_value_1, vcode, 0)
    if (result_msg_value_0 ==[]) and (result_msg_value_1 ==[]):
        return 0

    return vcode

def detect_by_single_hpAndCode(hp, vcode):
    # if hp == '0xb175560a0fa3287ae93144ede14d8dcc90d765b5':
        print("hp", hp)
        vcode = common_deal(hp, vcode)
        if vcode == 0:
            return None

        if MKET_deal(hp, vcode) == True:
            # hp_All10Type_dict['MKET'].append(hp)
            return {'MKET': [hp]}
        # print("1************************", hp)

        if UC_deal(hp, vcode) == True:
            # hp_All10Type_dict['UC'].append(hp)
            return {'UC': [hp]}
        # print("2************************", hp)

        if TDO_deal(hp, vcode) == True:
            # hp_All10Type_dict['TDO'].append(hp)
            return {'TDO': [hp]}
        # print("3************************", hp)

        if SESL_deal(hp, vcode) == True:
            # hp_All10Type_dict['SESL'].append(hp)
            return {'SESL': [hp]}
        # print("4************************", hp)

        if HT_deal(hp, vcode) == True:
            # hp_All10Type_dict['HT'].append(hp)
            return {'HT': [hp]}
        # print("5************************", hp)

        if US_deal(hp, vcode) == True:
            # hp_All10Type_dict['US'].append(hp)
            return {'US': [hp]}
        # print("6************************", hp)

        if BD_deal(hp, vcode) == True:
            # hp_All10Type_dict['BD'].append(hp)
            return {'BD': [hp]}
        # print("7************************", hp)

        if ID_deal(hp, vcode) == True:
            # hp_All10Type_dict['ID'].append(hp)
            return {'ID': [hp]}
        # print("8************************", hp)

        if SMC_deal(hp, vcode) == True:
            # hp_All10Type_dict['SMC'].append(hp)
            return {'SMC': [hp]}
        # print("9************************", hp)

        is_HSU_hp, is_SMC_hp = HSU_deal(hp, vcode)
        # print(is_HSU_hp, is_SMC_hp)
        if (is_SMC_hp == True) and (is_HSU_hp == False):
            # hp_All10Type_dict['SMC'].append(hp)
            return {'SMC': [hp]}
        if (is_HSU_hp == True) and (is_SMC_hp == False):
            # hp_All10Type_dict['HSU'].append(hp)
            return {'HSU': [hp]}


if __name__ == '__main__':
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_truePositive.json'  # 行数区间[19, 185] --去掉注释--> [14, 152]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_all8tyes_FalsePositive.json'   #行数区间[27, 2406] --去掉注释--> [16, 1573]
    # hp_8type_path = r'E:\PyCharm_workspace\book_deeplearning\smart-contract\honeypots_more13_FromXGBootst_truePositive.json'
    # hp_dict = load_json(hp_8type_path)

    paper_new_hp_path = r'D:\Pycharm\dnn\smart-contract\All10TypeHp_sourceCode_detect_byMine\honeypots_paper_new_addr2SouceCode.json' #行数区间[53, 201] --去掉注释--> [16, 83]
    hp_dict = load_json(paper_new_hp_path)

    hp_All10Type_dict = {'MKET':[], 'UC':[], 'TDO':[], 'SESL':[], 'HT':[], 'US':[], 'BD':[], 'ID':[], 'SMC':[], 'HSU':[]}
    for hp, vcode in hp_dict.items():
        # if hp == r'0x559cc6564ef51bd1ad9fbe752c9455cb6fb7feb1':
        # if hp == r'0xd1915a2bcc4b77794d64c4e483e43444193373fa':
        # print("0************************",hp)

        vcode = common_deal(hp, vcode)
        if vcode == 0:
            continue

        if MKET_deal(hp, vcode) == True:
            hp_All10Type_dict['MKET'].append(hp)
            continue
        # print("1************************", hp)

        if UC_deal(hp, vcode) == True:
            hp_All10Type_dict['UC'].append(hp)
            continue
        # print("2************************", hp)

        if TDO_deal(hp, vcode) == True:
            hp_All10Type_dict['TDO'].append(hp)
            continue
        # print("3************************", hp)

        if SESL_deal(hp, vcode) == True:
            hp_All10Type_dict['SESL'].append(hp)
            continue
        # print("4************************", hp)

        if HT_deal(hp, vcode) == True:
            hp_All10Type_dict['HT'].append(hp)
            continue
        # print("5************************", hp)

        if US_deal(hp, vcode) == True:
            hp_All10Type_dict['US'].append(hp)
            continue
        # print("6************************", hp)

        if BD_deal(hp, vcode) == True:
            hp_All10Type_dict['BD'].append(hp)
            continue
        # print("7************************", hp)

        if ID_deal(hp, vcode) == True:
            hp_All10Type_dict['ID'].append(hp)
            continue
        # print("9************************", hp)

        if SMC_deal(hp, vcode) == True:
            hp_All10Type_dict['SMC'].append(hp)
            continue
        # print("10************************", hp)

        is_HSU_hp, is_SMC_hp = HSU_deal(hp, vcode)
        # print(is_HSU_hp, is_SMC_hp)
        if (is_SMC_hp == True) and (is_HSU_hp == False):
            hp_All10Type_dict['SMC'].append(hp)
        if (is_HSU_hp == True) and (is_SMC_hp == False):
            hp_All10Type_dict['HSU'].append(hp)
        # print("11************************", hp)

    save_json('hp_All10Type_dict_from_paperNew_TP.json', hp_All10Type_dict)



'''
# honeypots_all8tyes_truePositive.json
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
0x0595d187cac88f04466371eff3a6b6d1b12fb013  has a high possibility to be a HSU (bool judge) hp.
0x062e659a3c8991bc1739e72c68edb9ac7b5a8ca7  has a high possibility to be a HSU (bool judge) hp.
0x064656852581472f9b315fea4730fe18fb7c579a  has a high possibility to be a HSU (non-bool judge) hp.
0x0684a256b8a6434cf10ee81bc1bcdcbba3365daa  has a high possibility to be a HSU (non-bool judge) hp.
0x0cfa149c0a843e1f8d9bc5c6e6bebf901845cebe  has a high possibility to be a HSU (bool judge) hp.
0x0e35f4f608d4a8fa560595db79cfda02d790777b  has a high possibility to be a HSU (non-bool judge) hp.
0x0e8f2803fa16492b948bc470c69e99460942db2b  has a high possibility to be a HSU (bool judge) hp.
0x11f4306f9812b80e75c1411c1cf296b04917b2f0  has a high possibility to be a HSU (bool judge) hp.
0x1237b26652eebf1cb8f59e07e07101c0df4f60f6  has a high possibility to be a HSU (non-bool judge) hp.
0x129e719c424a7a6fbdeb7ca3d65186892d54ea8c  has a high possibility to be a HSU (non-bool judge) hp.
0x137e531680b5d1f5645cd73a450323f1645d5034  has a high possibility to be a HSU (non-bool judge) hp.
0x13c547ff0888a0a876e6f1304eaefe9e6e06fc4b  has a high possibility to be a HSU (bool judge) hp.
0x159d2829613b0fe363e462b218c695c6eae0a5e1  has a high possibility to be a HSU (non-bool judge) hp.
0x16aae4b322501c339ed31a41fb915ae305528585  has a high possibility to be a HSU (non-bool judge) hp.
0x197803b104641fbf6e206a425d9dc35dadc4f62f  has a high possibility to be a HSU (bool judge) hp.
0x19d0321ba91ed5edec4afe1da158a6b06bba03f0  has a high possibility to be a HSU (non-bool judge) hp.
0x1dabd43e0f8a684a02712bcd767056e25026061c  has a high possibility to be a HSU (bool judge) hp.
0x1fbf025ad94dde79f88732f79966a9a435f2772f  has a high possibility to be a HSU (non-bool judge) hp.
0x24cad91c063686c49f2ef26a24bf80329fb131c7  has a high possibility to be a HSU (bool judge) hp.
0x2634baad203cba4aa4114c132b2e50a3a6027ff9  has a high possibility to be a HSU (bool judge) hp.
0x265c91539255a96e1005a0fd11ca776c183d04f5  has a high possibility to be a HSU (bool judge) hp.
0x26ae986bfab33f4cbadec30ea55b5eed9e883ecf  has a high possibility to be a HSU (bool judge) hp.
0x2b98b39d39914b3aad05dd06a46868507156400d  has a high possibility to be a HSU (bool judge) hp.
0x2cc8e271f11934f5fa15942dfda2b59432c2e0f3  has a high possibility to be a HSU (bool judge) hp.
0x2e0794073ec7b08e40d80a41599bb31df042e4e5  has a high possibility to be a HSU (non-bool judge) hp.
0x2e4eb4585cb949e53212e796cef13d562c24374b  has a high possibility to be a HSU (bool judge) hp.
0x2fe321bbb468d71cc392dd95082efef181df2038  has a high possibility to be a HSU (bool judge) hp.
0x34bc4f174c027a68f94a7ea6a3b4930e0211b19d  has a high possibility to be a HSU (bool judge) hp.
0x3597f78c7872db259ce023acc34511c7a79f42e3  has a high possibility to be a HSU (bool judge) hp.
0x3668eba58190c7bb2d63cb484467ff0a42fb3367  has a high possibility to be a HSU (non-bool judge) hp.
0x36d5d7262784130de564e99f5c2eab2aa0484bce  has a high possibility to be a HSU (non-bool judge) hp.
0x377f64e05c29309c8527022dbe5fbbfa8e40f6dd  has a high possibility to be a HSU (bool judge) hp.
0x3b048ab84ddd61c2ffe89ede66d68ef27661c0f2  has a high possibility to be a HSU (non-bool judge) hp.
0x3c3f481950fa627bb9f39a04bccdc88f4130795b  has a high possibility to be a HSU (bool judge) hp.
0x3caf97b4d97276d75185aaf1dcf3a2a8755afe27  has a high possibility to be a HSU (non-bool judge) hp.
0x40ef62929748b3e045fd2036322880ef486e4454  has a high possibility to be a HSU (non-bool judge) hp.
0x448fcea60482c0ea5d02fa44648c3749c46c4a29  has a high possibility to be a HSU (bool judge) hp.
0x4876bca6feab4243e4370bddc92f5a8364de9df9  has a high possibility to be a HSU (bool judge) hp.
0x4a73d9fe078fa67601047f88c3e6c270602e5709  has a high possibility to be a HSU (non-bool judge) hp.
0x4aec37ae465e1d78649aff117bab737c5fb4f214  has a high possibility to be a HSU (non-bool judge) hp.
0x4bc53ead2ae82e0c723ee8e3d7bacfb1fafea1ce  has a high possibility to be a HSU (non-bool judge) hp.
0x4c4757b23526ba13876f8ef3efe973618266e3e8  has a high possibility to be a HSU (non-bool judge) hp.
0x4ca675d62a05c451555c93e456f902bd3e423586  has a high possibility to be a HSU (non-bool judge) hp.
0x4d200a0a7066af311baba7a647b1cce54ae2f9a5  has a high possibility to be a HSU (bool judge) hp.
0x52682a037a8deab04e708055c751556a0840897a  has a high possibility to be a HSU (non-bool judge) hp.
0x53018f93f9240cf7e01301cdc4b3e45d25481f73  has a high possibility to be a HSU (bool judge) hp.
0x57684f9059afbf7bb11b07263500292ac9d78e7b  has a high possibility to be a HSU (bool judge) hp.
0x590d1d5ba0feb249d42c527ae21d12f2e5768a87  has a high possibility to be a HSU (non-bool judge) hp.
0x59434a7b9aeebe94045d3715aa020f6a1d7875ad  has a high possibility to be a HSU (non-bool judge) hp.
0x5ccfcdc1c88134993f48a898ae8e9e35853b2068  has a high possibility to be a HSU (non-bool judge) hp.
0x611ae0be21a9c0ab284a4a68c8c44843330072a7  has a high possibility to be a HSU (bool judge) hp.
0x64669148bca4f3d1216127a46380a67b37bbf63e  has a high possibility to be a HSU (bool judge) hp.
0x6594ac0a2ba54885ff7d314eb27c9694cb25698b  has a high possibility to be a HSU (bool judge) hp.
0x686847351a61eb1cae8ac0efa4208ff689fd53f2  has a high possibility to be a HSU (bool judge) hp.
0x68af0f18c974a9603ec863fefcebb4ceb2589070  has a high possibility to be a HSU (bool judge) hp.
0x6ce3fef99a6a4a8d1cc55d980966459854b3b021  has a high possibility to be a HSU (bool judge) hp.
0x6f905e47d3e6a9cc286b8250181ee5a0441acc81  has a high possibility to be a HSU (bool judge) hp.
0x704079e823e42a936bbaac5163434c2515473836  has a high possibility to be a HSU (non-bool judge) hp.
0x70bf9df6967dc96156e76cc43b928a7ef02e159a  has a high possibility to be a HSU (non-bool judge) hp.
0x735906d7ab237eeea06f4af86795bb4e0ec199e0  has a high possibility to be a HSU (non-bool judge) hp.
0x75041597d8f6e869092d78b9814b7bcdeeb393b4  has a high possibility to be a HSU (bool judge) hp.
0x75658ed3dba1e12644d2cd9272ba9ee888f4c417  has a high possibility to be a HSU (bool judge) hp.
0x7b3c3a05fcbf18db060ef29250769cee961d75ac  has a high possibility to be a HSU (bool judge) hp.
0x7fefc8bf6e44784ed016d08557e209169095f0f3  has a high possibility to be a HSU (bool judge) hp.
0x7ffc2bd9431b059c509b45b33e77852d47de827d  has a high possibility to be a HSU (bool judge) hp.
0x85044611b5954739dbde0ccb9aae6bb18e38e38b  has a high possibility to be a HSU (non-bool judge) hp.
0x878e6c6f9a86a1e5d313e7b872ccd109135e91b4  has a high possibility to be a HSU (non-bool judge) hp.
0x8a36f3e0da7b36fd22fcf2844c21e812279372ac  has a high possibility to be a HSU (non-bool judge) hp.
0x8bbf2d91e3c601df2c71c4ee98e87351922f8aa7  has a high possibility to be a HSU (bool judge) hp.
0x8bce9d720745b93c58c505fc0d842a7d9cd59697  has a high possibility to be a HSU (bool judge) hp.
0x8cc5d9de2c8df87f2d40d84aa78049ea6e61f973  has a high possibility to be a HSU (non-bool judge) hp.
0x8d056569b215c8b56e4b3a615dac425d8d2352a4  has a high possibility to be a HSU (bool judge) hp.
0x8d4eb49f0ed7ee6d6e00fc76ea3e9c3898bf219d  has a high possibility to be a HSU (bool judge) hp.
0x930dfbdc5e9f1984a8d87de29d6a79fbb2bb7b32  has a high possibility to be a HSU (bool judge) hp.
0x96fa4b2bebbbc9ffdb7d64ed18058de27680752c  has a high possibility to be a HSU (non-bool judge) hp.
0x99bab102c0a03438bcfd70119f07ee646db26ddf  has a high possibility to be a HSU (bool judge) hp.
0x9bdb9d9bd3e348d93453400e46e71dd519c60503  has a high possibility to be a HSU (bool judge) hp.
0xa0f9e5283fbf6d735e1e3a0f724ea6cccc13c27a  has a high possibility to be a HSU (non-bool judge) hp.
0xa379eda47d90fb4bc2dfa54556421ff0f198ca47  has a high possibility to be a HSU (non-bool judge) hp.
0xa48a36d94024f861b453267468b9096e4a3eb8be  has a high possibility to be a HSU (non-bool judge) hp.
0xa630823bd70ab8e8e2d6e62089d3837db1887bf6  has a high possibility to be a HSU (non-bool judge) hp.
0xa9aebbf67433e3e8206af6fc2ddd99ff8e7cc137  has a high possibility to be a HSU (non-bool judge) hp.
0xaa3a6f5bddd02a08c8651f7e285e2bec33ea5e53  has a high possibility to be a HSU (bool judge) hp.
0xaa4fd1781246f0b9a63921f7aee292311ea05bf7  has a high possibility to be a HSU (bool judge) hp.
0xabcdd0dbc5ba15804f5de963bd60491e48c3ef0b  has a high possibility to be a HSU (bool judge) hp.
0xacfc9577583ded00ae53ae79a0346cca4655c0bb  has a high possibility to be a HSU (non-bool judge) hp.
0xaded0438139b495db87d3f70f0991336df97136f  has a high possibility to be a HSU (bool judge) hp.
0xae3bf0f077ed66dda9fb1b5475942c919ef3bb0d  has a high possibility to be a HSU (bool judge) hp.
0xaea5418057d0e37a6e69e588e7f393e946846d62  has a high possibility to be a HSU (non-bool judge) hp.
0xaec8162438b83646518f3bf3a70b048979f81fab  has a high possibility to be a HSU (bool judge) hp.
0xaf531dc0b3b1151af48f3d638eeb6fe6acdfd59f  has a high possibility to be a HSU (bool judge) hp.
0xb19117892e2b2aaa418e75f61d7d1c05f86b66bd  has a high possibility to be a HSU (non-bool judge) hp.
0xb38beba95e0e21a97466c452454debe2658527f7  has a high possibility to be a HSU (bool judge) hp.
0xb49b1dddf1b3d6e878fd9b73874da7ab0da7e004  has a high possibility to be a HSU (bool judge) hp.
0xb5c424cd005cd1ccc155654b551c4453346e0718  has a high possibility to be a HSU (non-bool judge) hp.
0xb620cee6b52f96f3c6b253e6eea556aa2d214a99  has a high possibility to be a HSU (non-bool judge) hp.
0xb6f6f6f47e92e517876d30c04198f45a3bc1b281  has a high possibility to be a HSU (bool judge) hp.
0xb91a6c5c6362b10db6440d690e5391bb1eabe591  has a high possibility to be a HSU (bool judge) hp.
0xbae339b730cb3a58eff2f2f2fa4af579332c3e1c  has a high possibility to be a HSU (bool judge) hp.
0xbb51397fb8d3b91a08eff3c34d5c869c1d149ec5  has a high possibility to be a HSU (non-bool judge) hp.
0xbc272b58e7cd0a6002c95afd1f208898d756c580  has a high possibility to be a HSU (bool judge) hp.
0xbd53a4db4003c59070abbfa4e6c31afbf0b26843  has a high possibility to be a HSU (non-bool judge) hp.
0xbf5fb038c28df2b8821988da78c3ebdbf7aa5ac7  has a high possibility to be a HSU (bool judge) hp.
0xc034cf94f7ced9c968cc75210d1b5ddaccacfbf4  has a high possibility to be a HSU (non-bool judge) hp.
0xc1574ab95106621686d6e480f378d79c0442fe33  has a high possibility to be a HSU (non-bool judge) hp.
0xc1d73e148590b60ce9dd42d141f9b27bbad07879  has a high possibility to be a HSU (bool judge) hp.
0xc304349d7cc07407b7844d54218d29d1a449b854  has a high possibility to be a HSU (bool judge) hp.
0xc5ce9c06a0caf0e4cbd90572b6550feafd69b740  has a high possibility to be a HSU (bool judge) hp.
0xc6389ef3d79cf17a5d103bd0f06f83cf76b14258  has a high possibility to be a HSU (bool judge) hp.
0xc77081641129a028d622f85671ea172ac5595938  has a high possibility to be a HSU (non-bool judge) hp.
0xc78f0fdfb708689cbe6629175b66958eaa89e7d0  has a high possibility to be a HSU (non-bool judge) hp.
0xc7e454770433c071dd1863eeb27fb7e1adbd3361  has a high possibility to be a HSU (non-bool judge) hp.
0xcaa7b8aa3bc78dda98af8fee1390f34e756a5f55  has a high possibility to be a HSU (non-bool judge) hp.
0xcb71b51d9159a49050d56516737b4b497e98bb99  has a high possibility to be a HSU (bool judge) hp.
0xce6b1aff0fe66da643d7a9a64d4747293628d667  has a high possibility to be a HSU (non-bool judge) hp.
0xcea86636608bacb632dfd1606a0dc1728b625387  has a high possibility to be a HSU (non-bool judge) hp.
0xd0981f1e922be67f2d0bb4f0c86f98f039dd24cc  has a high possibility to be a HSU (bool judge) hp.
0xd6bc92a0f5a2bc17207283679c5ddcc108fd3710  has a high possibility to be a HSU (bool judge) hp.
0xd87eaad7afb256c69526a490f402a658f12246fd  has a high possibility to be a HSU (bool judge) hp.
0xd8993f49f372bb014fb088eabec95cfdc795cbf6  has a high possibility to be a HSU (bool judge) hp.
0xdda2044b39fdb4db77ac085866179c548e5d0f15  has a high possibility to be a HSU (non-bool judge) hp.
0xde82658c23f034d71827c215fdfbce0d4e248ccd  has a high possibility to be a HSU (non-bool judge) hp.
0xe1ccb3a5bae6fecdb9b60c0acf94989f48c10742  has a high possibility to be a HSU (non-bool judge) hp.
0xe3b0fe57f7de3281579a504dcc3af491afbb23e5  has a high possibility to be a HSU (bool judge) hp.
0xe3d085b7bdf97c6d003abcec2003b9c5b120d616  has a high possibility to be a HSU (non-bool judge) hp.
0xe830d955cbe549d9bcf55e3960b86ffac6ef83f1  has a high possibility to be a HSU (bool judge) hp.
0xed55fb58ea9de1f484addcc970463218b4d89cfe  has a high possibility to be a HSU (non-bool judge) hp.
0xed710216da4b1416a78768790ca9aa3633ca110f  has a high possibility to be a HSU (non-bool judge) hp.
0xef75f477126d05519d965d116fc9606e60fc70a8  has a high possibility to be a HSU (bool judge) hp.
0xefbfc3f373c9cc5c0375403177d71bcc387d3597  has a high possibility to be a HSU (bool judge) hp.
0xf0344800bd3ffa687e4d780357961b28995a5f46  has a high possibility to be a HSU (non-bool judge) hp.
0xf3f3dd2b5d9f3de1b1ceb6ad84683bf31adf29d1  has a high possibility to be a HSU (bool judge) hp.
0xfac1c7270bc5b0664e27e7f2e82281d564aedf4e  has a high possibility to be a HSU (non-bool judge) hp.
0xff45211ebdfc7ebcc458e584bcec4eac19d6a624  has a high possibility to be a HSU (non-bool judge) hp.
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
0x017bcaee2456d8bd0e181f94165919a4a2ecc2d9  has a high possibility to be a ID hp.
0x038e20839aebfe12b7956adcbc2511f6f7085164  has a high possibility to be a ID hp.
0x07f06a75ddf49de735d51dbf5c0a9062c034e7c6  has a high possibility to be a ID hp.
0x0bcccba050c2ce6439c57bd203378b113cc3cfd6  has a high possibility to be a ID hp.
0x11f3081cd6b2ac5a263e65e206f806bea7fa9c56  has a high possibility to be a ID hp.
0x1767856bc75cf070de5e6ba3d0c718440f008c66  has a high possibility to be a ID hp.
0x33685492a20234101b553d2a429ae8a6bf202e18  has a high possibility to be a ID hp.
0x33b44a1d150f3feaa40503ad20a75634adc39b18  has a high possibility to be a ID hp.
0x340844b39aacbdb4e7718fa14a95758f87a09a9a  has a high possibility to be a ID hp.
0x3526cf7d12c95b11a680678cc1f705cba667578d  has a high possibility to be a ID hp.
0x3e7840b88396acd80bac66021e1354064461a498  has a high possibility to be a ID hp.
0x4ba0d338a7c41cc12778e0a2fa6df2361e8d8465  has a high possibility to be a ID hp.
0x4c7c98c4d64c29ef8103b005eeccf5145cfdf8c1  has a high possibility to be a ID hp.
0x4dc76cfc65b14b3fd83c8bc8b895482f3cbc150a  has a high possibility to be a ID hp.
0x4fed7f5f0314bd156a8486fc41dc8bd4737c24fb  has a high possibility to be a ID hp.
0x50abfc76b637b70571c301071f7ce660c1c3d847  has a high possibility to be a ID hp.
0x50ddfe3722fc303cace413df41db23d55025e2e6  has a high possibility to be a ID hp.
0x52c2d09acf0ef12c487ae0c20a92d4f9a4abbfd1  has a high possibility to be a ID hp.
0x58978e8caccf56fadaa80ef52f5c684045306839  has a high possibility to be a ID hp.
0x5b2028602af2693d50b4157f4acf84d632ec8208  has a high possibility to be a ID hp.
0x5c8546a7b86ba30202c09a84f5a72644a2a4f7ba  has a high possibility to be a ID hp.
0x641074844a0dd00042347161f830346bdfe348bc  has a high possibility to be a ID hp.
0x68563d2a5fc58f88db8140a981170989f001b746  has a high possibility to be a ID hp.
0x6e843aefc1f2887e5b0aeb4002c1924c433d9a13  has a high possibility to be a ID hp.
0x70c01853e4430cae353c9a7ae232a6a95f6cafd9  has a high possibility to be a ID hp.
0x7704442e1005b9ab403463ed85e2fb24761a8738  has a high possibility to be a ID hp.
0x787080326e1f7e0eae490efdb18e90cfd0ae2692  has a high possibility to be a ID hp.
0x78faf034c61f4158a4a12bfa372187a21405ae33  has a high possibility to be a ID hp.
0x7e97c48497a8d650dc030744b74c81e29816f8e3  has a high possibility to be a ID hp.
0x81edefc64aabdce71f68347774bd4673d1d31419  has a high possibility to be a ID hp.
0x849019a489c3c26c7a7668e468be81a4d132781f  has a high possibility to be a ID hp.
0x9168fdc9f9db7b71865fe4bfd6f78b3610ebc704  has a high possibility to be a ID hp.
0x96050da7c01bbd4891ed766720a5c1c79b824163  has a high possibility to be a ID hp.
0x98fe1d52649a3a13863647c6789f16e46e090377  has a high possibility to be a ID hp.
0xa16cdcba1d6cb6874ff9fd8a6c8b82a3f834f512  has a high possibility to be a ID hp.
0xb31820c1d84e183377030b6d3f0e1ee5c1cff643  has a high possibility to be a ID hp.
0xc0c7d89e4968775931e53e9510ebad43644b0866  has a high possibility to be a ID hp.
0xcacf9396a56e9ff1e3f6533be83a043c36ce0436  has a high possibility to be a ID hp.
0xe65c53087e1a40b7c53b9a0ea3c2562ae2dfeb24  has a high possibility to be a ID hp.
0xf1aab4171ceb49b6a276975347e3c1d4d5650e5a  has a high possibility to be a ID hp.
0xfae0300c03a1ea898176bcb39f919c559f64f4ff  has a high possibility to be a ID hp.
0x251848c3fc50274f5fda449919f083dc937b48b2  has a high possibility to be a SESL hp.
0x7bc51b19abe2cfb15d58f845dad027feab01bfa0  has a high possibility to be a SESL hp.
0x858c9eaf3ace37d2bedb4a1eb6b8805ffe801bba  has a high possibility to be a SESL hp.
0xa0174f796d3b901adaa16cfbb589330462be0329  has a high possibility to be a SESL hp.
0xa395480a4a90c7066c8ddb5db83e2718e750641c  has a high possibility to be a SESL hp.
0xaa12936a79848938770bdbc5da0d49fe986678cc  has a high possibility to be a SESL hp.
0xd022969da8a1ace11e2974b3e7ee476c3f9f99c6  has a high possibility to be a SESL hp.
0xe63760e74ffd44ce7abdb7ca2e7fa01b357df460  has a high possibility to be a SESL hp.
0xf4ac238121585456dee1096fed287f4d8906d519  has a high possibility to be a SESL hp.
0x01f8c4e3fa3edeb29e514cba738d87ce8c091d3f  has a high possibility to be a SMC (depended on HSU) hp.
0x23a91059fdc9579a9fbd0edc5f2ea0bfdb70deb4  has a high possibility to be a SMC hp (constructor type).
0x23f890c412f3f06784a30ba40ed4832a0fca55f0  has a high possibility to be a SMC hp (delegatecall type).
0x4320e6f8c05b27ab4707cd1f6d5ce6f3e4b3a5a1  has a high possibility to be a SMC (depended on HSU) hp.
0x463f235748bc7862deaa04d85b4b16ac8fafef39  has a high possibility to be a SMC hp (constructor type).
0x477d1ee2f953a2f85dbecbcb371c2613809ea452  has a high possibility to be a SMC hp (delegatecall type).
0x4e73b32ed6c35f570686b89848e5f39f20ecc106  has a high possibility to be a SMC (depended on HSU) hp.
0x561eac93c92360949ab1f1403323e6db345cbf31  has a high possibility to be a SMC (depended on HSU) hp.
0x62d5c4a317b93085697cfb1c775be4398df0678c  has a high possibility to be a SMC hp (delegatecall type).
0x7a7d08bcb2faf27414e86ecf9a0351d928054b6b  has a high possibility to be a SMC hp (delegatecall type).
0x7a8721a9d64c74da899424c1b52acbf58ddc9782  has a high possibility to be a SMC hp (function_onlyOwner type).
0x8c7777c45481dba411450c228cb692ac3d550344  has a high possibility to be a SMC hp (constructor type).
0x941d225236464a25eb18076df7da6a91d0f95e9e  has a high possibility to be a SMC hp (constructor type).
0x95d34980095380851902ccd9a1fb4c813c2cb639  has a high possibility to be a SMC hp (constructor type).
0xa5d6accc5695327f65cbf38da29198df53efdcf0  has a high possibility to be a SMC hp (constructor type).
0xa91a453abde404a303fb118c46e00c8f630216a9  has a high possibility to be a SMC hp (delegatecall type).
0xaae1f51cf3339f18b6d3f3bdc75a5facd744b0b8  has a high possibility to be a SMC (depended on HSU) hp.
0xb4c05e6e4cdb07c15095300d96a5735046eef999  has a high possibility to be a SMC hp (constructor type).
0xb5e1b1ee15c6fa0e48fce100125569d430f1bd12  has a high possibility to be a SMC hp (constructor type).
0xb93430ce38ac4a6bb47fb1fc085ea669353fd89e  has a high possibility to be a SMC hp (constructor type).
0xbabfe0ae175b847543724c386700065137d30e3b  has a high possibility to be a SMC hp (constructor type).
0xbaf51e761510c1a11bf48dd87c0307ac8a8c8a4f  has a high possibility to be a SMC hp (constructor type).
0xbe4041d55db380c5ae9d4a9b9703f1ed4e7e3888  has a high possibility to be a SMC (depended on HSU) hp.
0xd116d1349c1382b0b302086a4e4219ae4f8634ff  has a high possibility to be a SMC hp (constructor type).
0xd518db222f37f9109db8e86e2789186c7e340f12  has a high possibility to be a SMC (depended on HSU) hp.
0xdad02644b70cbb20dec56d25282ddc65bb7805a1  has a high possibility to be a SMC hp (delegatecall type).
0xdd17afae8a3dd1936d1113998900447ab9aa9bc0  has a high possibility to be a SMC (depended on HSU) hp.
0xe610af01f92f19679327715b426c35849c47c657  has a high possibility to be a SMC hp (constructor type).
0xfa8bb2a68c67e39409cd336d1a8024a2ad9a62ff  has a high possibility to be a SMC hp (delegatecall type).
0xff5a11c0442028ee2a60d31e6ebb3cbac121ffe5  has a high possibility to be a SMC hp (delegatecall type).
0x2ecf8d1f46dd3c2098de9352683444a0b69eb229  has a high possibility to be a TDO hp.
0x752406cbfd32593fc422da69cdd702d1eaadc121  has a high possibility to be a TDO hp.
0x791d0463b8813b827807a36852e4778be01b704e  has a high possibility to be a TDO hp.
0xf5b1d75f4415f853fef2466a5ab8e412d593dd44  has a high possibility to be a TDO hp.
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
0xad1aa68300588aa5842751ddcab2afd4a69e9016  has a high possibility to be a US hp.
0xadccea0b14d26d786b99cf3ba3e9812cd4d23a81  has a high possibility to be a US hp.
0xb1f4ca3c6256f415e420de511504af8ea8a9c8e0  has a high possibility to be a US hp.
0xc57fc2c9fd3130933bd29f01ff940dc52bc4115b  has a high possibility to be a US hp.
0xe19ca313512e0231340e778abe7110401c737c23  has a high possibility to be a US hp.
0xe6f245bb5268b16c5d79a349ec57673e477bd015  has a high possibility to be a US hp.
0xefba96262f277cc8073da87e564955666d30a03b  has a high possibility to be a US hp.
0xf6c61cb3b0add944ac53c9c2decaf2954f0515cb  has a high possibility to be a US hp.
0xfb6e71e0800bccc0db8a9cf326fe3213ca1a0ea0  has a high possibility to be a US hp.
'''

'''
honeypots_all8tyes_FalsePositive.json  理论上应该是无
0xf5615138a7f2605e382375fa33ab368661e017ff  has a high possibility to be a MKET hp. -- 这个也在honeypots_paper_new_addr2SouceCode.json中，属于honeyBadger的判断失误。
'''


'''
# paper_new_honeypots.csv --- honeypots_paper_new_addr2SouceCode.json --- 有3个SMC的漏报, 具体详见SMC检测脚本的分析。
0x06c2452bcb4c1c1a046c520ffbad41fb8f48442b  has a high possibility to be a HSU (non-bool judge) hp.
0x1235b9042f7fe167f09450eaffdc07efcc3acb38  has a high possibility to be a ID hp.
0x1f7725942d18118d34621c6eb106a3f418f66710  has a high possibility to be a US hp.
0x21feda639f23647ac4066f25caaaa4fadb9eb595  has a high possibility to be a US hp.
0x25926eff952bdcd3cb395a5614ab5094474b2dba  has a high possibility to be a UC hp.
0x2ad6bdedf16b32a925ba293ee07f9b3c1c5ab266  has a high possibility to be a HSU (non-bool judge) hp.
0x2bb5b9f83391d4190f8b283be0170570953c5a8e  has a high possibility to be a HT hp. 742
0x31fd65340a3d272e21fd6ac995f305cc1ad5f42a  has a high possibility to be a HT hp. 742
0x32f14d71499fc2c1482eb275ec83ce5fb1d6c7ec  has a high possibility to be a UC hp.
0x33f82dfbaafb07c16e06f9f81187f78efa9d438c  has a high possibility to be a ID hp.
0x349d9314154ef0999facdbbcea2d9737b0529570  has a high possibility to be a HSU (non-bool judge) hp.
0x38acc6c57f3fea1d9dbffb395f3f7c3143f0d749  has a high possibility to be a UC hp.
0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01  has a high possibility to be a ID hp.
0x3fab284a3cd0a6d88d18d0fda4bc1a76cdacd68a  has a high possibility to be a HSU (non-bool judge) hp.
0x46de9ef59a51388961bfbe45fb89bedbdfaa32ac  has a high possibility to be a HSU (non-bool judge) hp.
0x4b17c05fc1566891e5a9220d22527b5aeab0e1d0  has a high possibility to be a ID hp.
0x51ae2f91619246ad3a20f4e76f3323a836bde6a5  has a high possibility to be a HSU (non-bool judge) hp.
0x55bec5649fbb5f5be831ee5b0f7a8a8f02b25144  has a high possibility to be a HT hp. 1218
0x5abb8dda439becbd9585d1894bd96fd702400fa2  has a high possibility to be a HT hp. 742
0x5b39afa22a9debd9247bf84b68a79b8736c2ba4e  has a high possibility to be a HSU (non-bool judge) hp.
0x5dac036595568ff792f5064451b6b37e801ecab9  has a high possibility to be a HSU (bool judge) hp.
0x5e521b660fe8ac575f1d7201f2237724ee531f1d  has a high possibility to be a HSU (non-bool judge) hp.
0x61dc347d7fa0f6e34c3112faf83a2e468d681f68  has a high possibility to be a HT hp. 887
0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839  has a high possibility to be a ID hp.
0x652eb151869c2e8fa354f29321ba192d5d9f84dc  has a high possibility to be a US hp.
0x656610729fc13e8283d96aa69cdf56c112222951  has a high possibility to be a US hp.
0x66385555fc121d18dc95ec3a8ecd51ab2b660de5  has a high possibility to be a HT hp. 734
0x6e6f819299e7809ce744f37fae9f84fe38d95f1c  has a high possibility to be a HSU (non-bool judge) hp.
0x6fc1ee575e9023aea1c45b4dfc9acf603ea9f63f  has a high possibility to be a HSU (non-bool judge) hp.
0x7bf5a0802a5eb74883806e60600290f53da339e1  has a high possibility to be a HSU (non-bool judge) hp.
0x7c52974b6eb8af0ddf874b3c4e03aa9a791d9632  has a high possibility to be a HSU (non-bool judge) hp.
0x81c798ea668b6d7e07ea198014265e0c1d64b5a8  has a high possibility to be a ID hp.
0x85179ac15aa94e3ca32dd1cc04664e9bb0062115  has a high possibility to be a SMC (depended on HSU) hp.
0x8fd1e427396ddb511533cf9abdbebd0a7e08da35  has a high possibility to be a ID hp.
0x90302710ae7423ca1ee64907ba82b7f6854a5ddc  has a high possibility to be a HSU (bool judge) hp.
0x94602b0e2512ddad62a935763bf1277c973b2758  has a high possibility to be a US hp.
0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b  has a high possibility to be a SMC (depended on HSU) hp.
0x9823e4e4f4552cd84720dabbd6fb2c7b67066c6c  has a high possibility to be a US hp.
0xaee056c6c1071512657f094af550d1af74db0622  has a high possibility to be a HSU (non-bool judge) hp.
0xb11b2fed6c9354f7aa2f658d3b4d7b31d8a13b77  has a high possibility to be a ID hp.
0xbaa3de6504690efb064420d89e871c27065cdd52  has a high possibility to be a ID hp.
0xbebbfe5b549f5db6e6c78ca97cac19d1fb03082c  has a high possibility to be a ID hp.
0xc1fbb18de504e0bba8514ff741f3109d790ed087  has a high possibility to be a HT hp. 4467
0xc710772a16fd040ed9c63de0679a57410981e3fc  has a high possibility to be a ID hp.
0xcac14364754336d9759caafddef8d662dcca06a0  has a high possibility to be a HSU (non-bool judge) hp.
0xcfebf8c78de81f804a694f4bb401e5d76b298be5  has a high possibility to be a HT hp. 901
0xd2ea3d1be7b482966ba8627ff009b84bac3bf51e  has a high possibility to be a TDO hp.
0xd7e3c6d99bc2ccdb6fe54b8a5888d14319e65c36  has a high possibility to be a BD hp.
0xd887c0197881626b3091b41354f9a99432d91aba  has a high possibility to be a US hp.
0xda9378ae021239378752acfb1821bb6ed9309371  has a high possibility to be a UC hp.
0xe7e25a3d83abdc4a4273792cca7865889a7b0df3  has a high possibility to be a ID hp.
0xf0cc17aa0ce1c6595e56c9c60b19c1c546ade50d  has a high possibility to be a ID hp.
0xf5615138a7f2605e382375fa33ab368661e017ff  has a high possibility to be a MKET hp.
0xf5b72a62d7575f3a03954d4d7de2a2701da16049  has a high possibility to be a US hp.
'''

'''
honeypots_more13_FromXGBootst_truePositive.json  
0xf03abd62c2d8b3a90db84b41ce3118c1291a198f  has a high possibility to be a SESL hp.
0x1aa635be048b85716ebf9093d1bde5aa7df9fefc  has a high possibility to be a HT hp. 2823
0x37eb3cb268a0dd1bc2c383296fe34f58c5b5db8b  has a high possibility to be a US hp.
0x65e5909d665cbda128de96aa9eb0160729eac1b0  has a high possibility to be a SMC hp (constructor type).
0x788dcaa03860a44a98cc64652a3d1a16fbecee9d  has a high possibility to be a HSU (bool judge) hp.
0x8f3e10f9b0b9eebb2254fc6d6549bd7a8db9f10e  has a high possibility to be a US hp.
0xbacff8111bb7acfff885bad82239b74bc625a699  has a high possibility to be a US hp.
0xd1915a2bcc4b77794d64c4e483e43444193373fa  has a high possibility to be a US hp.
0xd4342df2c7cfe5938540648582c8d222f1513c50  has a high possibility to be a US hp.
0xedf4597f75cd1773978eb51ad0b2c59d5d742756  has a high possibility to be a ID hp.
0xeea07c4fef88f043102a45fae9c21a9154373a11  has a high possibility to be a ID hp.
0xf8e89d113924300b38615ceb5719709569ebec6b  has a high possibility to be a US hp.
0xfb294324c87f57f89c37d3fce66ca6d8212562b3  has a high possibility to be a US hp.
'''