# 信息提取 - py与db文件的交互.docx
import sqlite3
from hp_All10Type_sourceCode_detect import detect_by_single_hpAndCode
from saveJson import save_json

'''
****************************************************************************
'''
from hp_All10Type_sourceCode_detect import common_deal
# 使用简单的模糊匹配
import difflib
benchmark_smartcontract_code = ''
hp_Type11_dict = {'NumGame':[]}
thred_line=0.8
sol_path = r'D:\Pycharm\dnn\smart-contract\All10TypeHp_sourceCode_detect_byMine\RACEFORETH.sol'

with open(sol_path) as solFile:
    benchmark_smartcontract_code = solFile.read()

def NumGame_deal(hp, vcode, hp_Type11_dict={'NumGame':[]},thred_line=0.9):
    if(difflib.SequenceMatcher(None,benchmark_smartcontract_code,vcode).ratio()>=thred_line):
        hp_Type11_dict['NumGame'] += [hp]
    return hp_Type11_dict

benchmark_smartcontract_code = common_deal('', benchmark_smartcontract_code)
# print(benchmark_smartcontract_code)
'''
****************************************************************************
'''

# 1020-1150w区块上智能合约源码存储的数据库文件
# honeypot_detection_db_path = r'D:\数据库文件\tian_tian_90\650w-850w\honeypot-detection_650w-850w.db'
# honeypot_detection_db_path = r'D:\数据库文件\tian_tian_90\1020w-1150w\honeypot-detection.db'
honeypot_detection_db_path = r'D:\数据库文件\fl68vps\honeypot-detection.db'

# # 连接到SQLite数据库：一个数据库连接称为Connection。
# conn = sqlite3.connect(honeypot_detection_db_path)
#
# # 连接到数据库后，需要打开游标，称之为Cursor，通过Cursor执行SQL语句，然后，获得执行结果。
# # 创建一个Cursor:
# cursor = conn.cursor()
# # 从contracts表中执行查询语句
# # cursor.execute('select * from contracts where source_code !=?', ('Null',))
# cursor.execute('select address, source_code, compiler_version_major_id, compiler_version_minor_id, compiler_version_patch_id from contracts where source_code !=?', ('Null',))
# # 获得查询结果集
# values = cursor.fetchall() # 5-tuple list

def connectDB_getCursor(db_path):
    # 连接到SQLite数据库：一个数据库连接称为Connection。
    conn = sqlite3.connect(db_path)
    # 连接到数据库后，需要打开游标，称之为Cursor，通过Cursor执行SQL语句，然后，获得执行结果。
    # 创建一个Cursor:
    cursor = conn.cursor()

    return cursor

def get_souceCode_info_from_contracts(cursor):
    # 从contracts表中执行查询语句
    # cursor.execute('select * from contracts where source_code !=?', ('Null',))
    cursor.execute('select address, source_code, compiler_version_major_id, compiler_version_minor_id, compiler_version_patch_id from contracts where source_code !=?', ('Null',))
    # 获得查询结果集
    values = cursor.fetchall()  # 5-tuple list
    return values

def get_compiler_version_integer(minor_v, patch_v):
    return int(minor_v) * 100 + int(patch_v)

def main():
    # 1. 用于存放蜜罐的字典
    hp_All10Type_dict = {'MKET': [], 'UC': [], 'TDO': [], 'SESL': [], 'HT': [], 'US': [], 'BD': [], 'ID': [], 'SMC': [], 'HSU': []}
    # 2. 查询数据库获取hp、vcode
    # cursor = connectDB_getCursor(honeypot_detection_db_path)
    # values = get_souceCode_info_from_contracts(cursor)
    # 连接到SQLite数据库：一个数据库连接称为Connection。
    conn = sqlite3.connect(honeypot_detection_db_path)

    # 连接到数据库后，需要打开游标，称之为Cursor，通过Cursor执行SQL语句，然后，获得执行结果。
    # 创建一个Cursor:
    cursor = conn.cursor()
    # 从contracts表中执行查询语句
    # cursor.execute('select * from contracts where source_code !=?', ('Null',))
    cursor.execute('select address, source_code, compiler_version_major_id, compiler_version_minor_id, compiler_version_patch_id from contracts where source_code !=?', ('Null',))
    # 获得查询结果集
    # values = cursor.fetchall() # 5-tuple list
    # for v_tuple in values:
    # 面对大型数据库时，使用迭代器而不用fetchall,即省内存又能很快拿到数据。
    v_tuple = cursor.fetchone()
    while v_tuple is not None:
        cursor_compiler = conn.cursor()
        major_v = cursor_compiler.execute('select value from contract_compiler_major_versions where id = ?', (v_tuple[2],)).fetchall()[0][0]
        minor_v = cursor_compiler.execute('select value from contract_compiler_minor_versions where id = ?', (v_tuple[3],)).fetchall()[0][0]
        patch_v = cursor_compiler.execute('select value from contract_compiler_patch_versions where id = ?', (v_tuple[4],)).fetchall()[0][0].split('+')[0].split('-')[0]
        # print(major_v, minor_v, patch_v, v_tuple[0])
        all_inter_v = get_compiler_version_integer(minor_v, patch_v)
        # print(all_inter_v, v_tuple[0])
        # 合约源码的地址
        hp = v_tuple[0]
        # 合约源码
        vcode = r'pragma solidity ^' + major_v + r'.' + minor_v + r'.' + patch_v + r';\n\n' + v_tuple[1]
        v_tuple = cursor.fetchone()
        # print(v_tuple)
        # 3. 使用hp、vcode进行检测
        # single_hp_dict = detect_by_single_hpAndCode(hp, vcode)
        # if single_hp_dict != None:
        #     for key_ad, v_hp in single_hp_dict.items():
        #         hp_All10Type_dict[key_ad] += v_hp
        #*******************************************
        # print(benchmark_smartcontract_code[50:])
        tmp_vcode = common_deal('', vcode)
        if tmp_vcode == 0:
            continue
        cmp_ratio = difflib.SequenceMatcher(None, benchmark_smartcontract_code, tmp_vcode).ratio()
        if cmp_ratio >= 0.5:
            print(hp, cmp_ratio)
        if (cmp_ratio >= thred_line):
            hp_Type11_dict['NumGame'] += [hp]

    # 4. 全部遍历完毕后, 关闭数据库连接
    cursor_compiler.close()
    cursor.close()
    conn.close()

    # 5. 保存为json文件
    # save_json('hp_All10Type_dict_from_tian_tian_90_650w-850wDB_rowThred=155_0320.json', hp_All10Type_dict)
    # save_json('hp_All10Type_dict_from_tian_tian_90_1050w-1150wDB_rowThred=155_0320.json', hp_All10Type_dict)
    # save_json('hp_All10Type_dict_from_XGBoost_fl68vps_DB_rowThred=155_0320.json', hp_All10Type_dict)
    #**********************************************************************************************
    save_json('hp_Type11_dict_from_XGBoost_fl68vps_DB_0331.json', hp_Type11_dict)
    # save_json('hp_Type11_dict_from_tian_tian_90_650w-850wDB_0331.json', hp_Type11_dict)
    # save_json('hp_Type11_dict_from_tian_tian_90_1020w-1150wDB_0331.json', hp_Type11_dict)

if __name__ == '__main__':
    main()