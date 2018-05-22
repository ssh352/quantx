
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2018 the QuantX authors
# All rights reserved.
#
# The project sponsor and lead author is Xu Rendong.
# E-mail: xrd@ustc.edu, QQ: 277195007, WeChat: ustc_xrd
# You can get more information at https://xurendong.github.io
# For names of other contributors see the contributors file.
#
# Commercial use of this code in source and binary forms is
# governed by a LGPL v3 license. You may get a copy from the
# root directory. Or else you should get a specific written 
# permission from the project author.
#
# Individual and educational use of this code in source and
# binary forms is governed by a 3-clause BSD license. You may
# get a copy from the root directory. Certainly welcome you
# to contribute code of all sorts.
#
# Be sure to retain the above copyright notice and conditions.

import os
import re
import threading

import numpy as np
import pandas as pd
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton, QTextEdit, QHBoxLayout, QVBoxLayout

import common
import dbm_mssql
import dbm_mysql

pd.set_option("max_colwidth", 200)
pd.set_option("display.width", 500)

DEF_EVENT_TEXT_INFO_PRINT = 1001

class CapitalItem(object):
    def __init__(self, **kwargs):
        self.inners = kwargs.get("inners", 0) # 内部代码
        self.market = kwargs.get("market", "") #֤ 证券市场
        self.code = kwargs.get("code", "") # 证券代码
        self.name = kwargs.get("name", "") # 证券名称
        self.end_date = kwargs.get("end_date", 0) # 截止日期
        self.total_shares = kwargs.get("total_shares", -1) # 总股本
        self.circu_shares = kwargs.get("circu_shares", -1) # 流通股本(A股)

    def SetEndDate(self, date): # 截止日期
        if date != None:
            self.end_date = date.year * 10000 + date.month * 100 + date.day

class ExRightsItem(object):
    def __init__(self, **kwargs):
        self.inners = kwargs.get("inners", 0) # 内部代码
        self.market = kwargs.get("market", "") #֤ 证券市场
        self.code = kwargs.get("code", "") # 证券代码
        self.date = kwargs.get("date", 0) # 除权除息日期
        self.muler = 0.0 # 乘数
        self.adder = 0.0 # 加数
        self.sg = 0.0 # 送股比率，每股
        self.pg = 0.0 # 配股比率，每股
        self.price = 0.0 # 配股价
        self.bonus = 0.0 # 现金红利

class IndustryItem(object):
    def __init__(self, **kwargs):
        self.standard = kwargs.get("standard", 0) # 行业划分标准
        self.industry = kwargs.get("industry", 0) # 所属行业
        self.industry_code_1 = kwargs.get("industry_code_1", "") # 一级行业代码
        self.industry_name_1 = kwargs.get("industry_name_1", "") # 一级行业名称
        self.industry_code_2 = kwargs.get("industry_code_2", "") # 二级行业代码
        self.industry_name_2 = kwargs.get("industry_name_2", "") # 二级行业名称
        self.industry_code_3 = kwargs.get("industry_code_3", "") # 三级行业代码
        self.industry_name_3 = kwargs.get("industry_name_3", "") # 三级行业名称
        self.industry_code_4 = kwargs.get("industry_code_4", "") # 四级行业代码
        self.industry_name_4 = kwargs.get("industry_name_4", "") # 四级行业名称
        self.inners = kwargs.get("inners", 0) # 证券内部编码
        self.market = kwargs.get("market", "") # 证券市场
        self.code = kwargs.get("code", "") # 证券代码
        self.name = kwargs.get("name", "") # 证券名称
        self.info_date = kwargs.get("info_date", 0) # 信息发布日期

    def SetInfoDate(self, date):
        if date != None:
            self.info_date = date.year * 10000 + date.month * 100 + date.day

class DataMaker_Capital():
    def __init__(self, parent = None):
        self.parent = parent
        self.capital_dict = {}
        self.count_zgb_none = 0 # 总股本缺失
        self.count_ltgb_none = 0 # 流通股本缺失
        self.count_zgb_zero = 0 # 总股本为零
        self.count_ltgb_zero = 0 # 流通股本为零
        self.count_zgb_ltgb = 0 # 全流通计数
        self.count_jzrq_none = 0 # 截止日期缺失

    def SendMessage(self, text_info):
        if self.parent != None:
            self.parent.SendMessage(text_info)

    def CheckStockGuBen(self):
        for item in self.capital_dict.values():
            if item.total_shares == -1:
                self.count_zgb_none += 1
                self.SendMessage("总股本缺失：%s %s" % (item.market, item.code))
            elif item.total_shares == 0:
                self.count_zgb_zero += 1
                self.SendMessage("总股本为零：%s %s" % (item.market, item.code))
            if item.circu_shares == -1:
                self.count_ltgb_none += 1
                self.SendMessage("流通股本缺失：%s %s" % (item.market, item.code))
            elif item.circu_shares == 0:
                self.count_ltgb_zero += 1
                self.SendMessage("流通股本为零：%s %s" % (item.market, item.code))
            if item.total_shares == item.circu_shares:
                self.count_zgb_ltgb += 1
            if item.end_date == 0:
                self.count_jzrq_none += 1
        self.SendMessage("总计：%s" % len(self.capital_dict))
        self.SendMessage("总股本缺失：%s" % self.count_zgb_none)
        self.SendMessage("总股本为零：%s" % self.count_zgb_zero)
        self.SendMessage("流通股本缺失：%s" % self.count_ltgb_none)
        self.SendMessage("流通股本为零：%s" % self.count_ltgb_zero)
        self.SendMessage("全流通股票：%s" % self.count_zgb_ltgb)
        self.SendMessage("截止日期缺失：%s" % self.count_jzrq_none)

    def PullData_Capital(self, dbm):
        if dbm == None:
            self.SendMessage("PullData_Capital 数据库 dbm 尚未连接！")
            return
        # 证券市场：83 上海证券交易所、90 深圳证券交易所
        # 证券类别：1 A股
        # 上市板块：1 主板、2 中小企业板、6 创业板
        # 查询字段：SecuMain：证券内部编码、证券代码、证券简称、证券市场
        # 查询字段：LC_ShareStru：截止日期、总股本(股)、已上市流通A股(股)
        # 唯一约束：SecuMain = InnerCode、LC_ShareStru = CompanyCode & EndDate
        str_sql = "SELECT SecuMain.InnerCode, SecuMain.SecuCode, SecuMain.SecuAbbr, SecuMain.SecuMarket, LC_ShareStru.EndDate, LC_ShareStru.TotalShares, LC_ShareStru.AFloatListed \
                  FROM SecuMain INNER JOIN LC_ShareStru \
                  ON SecuMain.CompanyCode = LC_ShareStru.CompanyCode \
                  WHERE (SecuMain.SecuMarket = 83 OR SecuMain.SecuMarket = 90) \
                    AND (SecuMain.SecuCategory = 1) \
                    AND (SecuMain.ListedSector = 1 or SecuMain.ListedSector = 2 or SecuMain.ListedSector = 6) \
                    AND CAST(LC_ShareStru.CompanyCode as nvarchar) + CAST(LC_ShareStru.EndDate as nvarchar) IN \
                      ( \
                        SELECT CAST(CompanyCode as nvarchar) + CAST(MAX(EndDate) as nvarchar) \
                        FROM LC_ShareStru \
                        GROUP BY CompanyCode \
                      ) \
                  ORDER BY SecuMain.SecuMarket ASC, SecuMain.SecuCode ASC"
        result_list = dbm.ExecQuery(str_sql)
        if result_list != None:
            for (InnerCode, SecuCode, SecuAbbr, SecuMarket, EndDate, TotalShares, AFloatListed) in result_list:
                if not SecuCode[0] == "X": # 排除未上市的新股
                    stock_market = ""
                    if SecuMarket == 83:
                        stock_market = "SH"
                    elif SecuMarket == 90:
                        stock_market = "SZ"
                    capital_item = CapitalItem(inners = InnerCode, market = stock_market, code = SecuCode, name = SecuAbbr)
                    capital_item.SetEndDate(EndDate) # 截止日期
                    if TotalShares != None:
                        capital_item.total_shares = TotalShares
                    if AFloatListed != None:
                        capital_item.circu_shares = AFloatListed
                    self.capital_dict[InnerCode] = capital_item
                    #print InnerCode, SecuCode, SecuAbbr, SecuMarket, EndDate, TotalShares, AFloatListed
            self.SendMessage("获取 股本结构 成功。总计 %d 个。" % len(result_list))
            self.CheckStockGuBen()
        else:
            self.SendMessage("获取 股本结构 失败！")

    def SaveData_Capital(self, dbm, table_name, save_path):
        capital_keys = list(self.capital_dict.keys())
        capital_keys.sort()
        capital_dict_list = [self.capital_dict[key] for key in capital_keys]
        total_record_num = len(capital_dict_list)
        
        if dbm != None:
            sql = "SHOW TABLES"
            result = dbm.QueryAllSql(sql)
            data_tables = list(result)
            #print(data_tables)
            have_tables = re.findall("(\'.*?\')", str(data_tables))
            have_tables = [re.sub("'", "", table) for table in have_tables]
            #print(have_tables)
            if table_name in have_tables:
                sql = "TRUNCATE TABLE %s" % table_name
                dbm.ExecuteSql(sql)
            else:
                sql = "CREATE TABLE `%s` (" % table_name + \
                      "`id` int(32) unsigned NOT NULL AUTO_INCREMENT COMMENT '序号'," + \
                      "`inners` int(32) unsigned NOT NULL DEFAULT '0' COMMENT '内部代码'," + \
                      "`market` varchar(32) NOT NULL DEFAULT '' COMMENT '证券市场，SH、SZ'," + \
                      "`code` varchar(32) NOT NULL DEFAULT '' COMMENT '证券代码'," + \
                      "`name` varchar(32) DEFAULT '' COMMENT '证券名称'," + \
                      "`end_date` date NOT NULL COMMENT '截止日期'," + \
                      "`total_shares` bigint(64) DEFAULT '0' COMMENT '总股本，股'," + \
                      "`circu_shares` bigint(64) DEFAULT '0' COMMENT '流通股本，股，A股'," + \
                      "PRIMARY KEY (`id`)," + \
                      "UNIQUE KEY `idx_market_code_end_date` (`market`,`code`,`end_date`)" + \
                      ") ENGINE=InnoDB DEFAULT CHARSET=utf8"
                dbm.ExecuteSql(sql)
            values = []
            save_record_failed = 0
            save_record_success = 0
            save_index_from = 0 #
            sql = "INSERT INTO %s" % table_name + "(inners, market, code, name, end_date, total_shares, circu_shares) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            for i in range(save_index_from, total_record_num):
                str_date = common.TransDateIntToStr(capital_dict_list[i].end_date)
                values.append((capital_dict_list[i].inners, capital_dict_list[i].market, capital_dict_list[i].code, capital_dict_list[i].name, str_date, capital_dict_list[i].total_shares, capital_dict_list[i].circu_shares))
                if (i - save_index_from + 1) % 3000 == 0: # 自定义每批次保存条数
                    if len(values) > 0: # 有记录需要保存
                        if dbm.ExecuteManySql(sql, values) == False:
                            save_record_failed += len(values)
                        else:
                            save_record_success += len(values)
                        #print("保存：", len(values))
                        values = [] #
            if len(values) > 0: # 有记录需要保存
                if dbm.ExecuteManySql(sql, values) == False:
                    save_record_failed += len(values)
                else:
                    save_record_success += len(values)
                #print("保存：", len(values))
            self.SendMessage("远程入库：总记录 %d，入库记录 %d，失败记录 %d。" % (total_record_num, save_record_success, save_record_failed))
        
        values = []
        for i in range(total_record_num):
            str_date = common.TransDateIntToStr(capital_dict_list[i].end_date)
            values.append((capital_dict_list[i].inners, capital_dict_list[i].market, capital_dict_list[i].code, capital_dict_list[i].name, str_date, capital_dict_list[i].total_shares, capital_dict_list[i].circu_shares))
        columns = ["inners", "market", "code", "name", "end_date", "total_shares", "circu_shares"]
        result = pd.DataFrame(columns = columns) # 空
        if len(values) > 0:
            result = pd.DataFrame(data = values, columns = columns)
        #print(result)
        result.to_pickle(save_path)
        self.SendMessage("本地保存：总记录 %d，保存记录 %d，失败记录 %d。" % (total_record_num, result.shape[0], total_record_num - result.shape[0]))

class DataMaker_ExRights():
    def __init__(self, parent = None):
        self.parent = parent
        self.exrights_dict_sh = {}
        self.exrights_dict_sz = {}

    def SendMessage(self, text_info):
        if self.parent != None:
            self.parent.SendMessage(text_info)

    def PullData_Stock(self, dbm):
        if dbm == None:
            self.SendMessage("PullData_Stock 数据库 dbm 尚未连接！")
            return
        # 证券市场：83 上海证券交易所、90 深圳证券交易所
        # 证券类别：1 A股、8 开放式基金、62 ETF基金
        # 上市板块：1 主板、2 中小企业板、6 创业板
        # 查询字段：SecuMain：证券内部编码、证券代码、证券市场、证券类别、上市板块
        # 唯一约束：SecuMain = InnerCode
        str_sql = "SELECT SecuMain.InnerCode, SecuMain.SecuCode, SecuMain.SecuMarket, SecuMain.SecuCategory, SecuMain.ListedSector \
                  FROM SecuMain \
                  WHERE (SecuMain.SecuMarket = 83 OR SecuMain.SecuMarket = 90) \
                    AND (SecuMain.SecuCategory = 1 OR SecuMain.SecuCategory = 8 OR SecuMain.SecuCategory = 62) \
                  ORDER BY SecuMain.SecuCode ASC"
        result_list = dbm.ExecQuery(str_sql)
        stock_count_sh = 0
        stock_count_sz = 0
        if result_list != None:
            for (InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector) in result_list:
                #print(InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector)
                if SecuMarket == 83:
                    stock_count_sh += 1
                    self.exrights_dict_sh[SecuCode] = {}
                elif SecuMarket == 90:
                    stock_count_sz += 1
                    self.exrights_dict_sz[SecuCode] = {}
            self.SendMessage("获取证券列表成功。上证 %d 个，深证 %d 个。" % (stock_count_sh, stock_count_sz))
        else:
            self.SendMessage("获取证券列表失败！")

    def PullData_PeiGu(self, dbm):
        if dbm == None:
            self.SendMessage("PullData_PeiGu 数据库 dbm 尚未连接！")
            return
        # 证券市场：83 上海证券交易所、90 深圳证券交易所
        # 证券类别：1 A股、8 开放式基金、62 ETF基金
        # 上市板块：1 主板、2 中小企业板、6 创业板
        # 查询字段：SecuMain：证券内部编码、证券代码、证券市场、证券类别、上市板块
        # 查询字段：LC_ASharePlacement：除权日、实际配股比例(10配X)、每股配股价格(元)
        # 唯一约束：SecuMain = InnerCode、LC_ASharePlacement = InnerCode, InitialInfoPublDate
        str_sql = "SELECT SecuMain.InnerCode, SecuMain.SecuCode, SecuMain.SecuMarket, SecuMain.SecuCategory, SecuMain.ListedSector, \
                         LC_ASharePlacement.ExRightDate, LC_ASharePlacement.ActualPlaRatio, LC_ASharePlacement.PlaPrice \
                  FROM SecuMain INNER JOIN LC_ASharePlacement \
                  ON SecuMain.InnerCode = LC_ASharePlacement.InnerCode \
                  WHERE (SecuMain.SecuMarket = 83 OR SecuMain.SecuMarket = 90) \
                    AND (SecuMain.SecuCategory = 1 OR SecuMain.SecuCategory = 8 OR SecuMain.SecuCategory = 62) \
                    AND LC_ASharePlacement.ExRightDate IS NOT NULL \
                  ORDER BY SecuMain.SecuCode ASC, LC_ASharePlacement.ExRightDate ASC"
        result_list = dbm.ExecQuery(str_sql)
        datas_count_sh = 0
        datas_count_sz = 0
        if result_list != None:
            for (InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector, ExRightDate, ActualPlaRatio, PlaPrice) in result_list:
                #print(InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector, ExRightDate, ActualPlaRatio, PlaPrice)
                #print(InnerCode, SecuCode, ExRightDate, ActualPlaRatio, PlaPrice)
                date = ExRightDate.year * 10000 + ExRightDate.month * 100 + ExRightDate.day
                if SecuMarket == 83:
                    market = "SH"
                    datas_count_sh += 1
                    if not SecuCode in self.exrights_dict_sh.keys():
                        self.exrights_dict_sh[SecuCode] = {}
                    exrights_item_dict = self.exrights_dict_sh[SecuCode]
                    if date in exrights_item_dict.keys():
                        exrights_item = exrights_item_dict[date]
                        if ActualPlaRatio != None:
                            exrights_item.pg = float(ActualPlaRatio) / 10.0
                        if PlaPrice != None:
                            exrights_item.price = float(PlaPrice)
                    else:
                        exrights_item = ExRightsItem(inners = InnerCode, market = market, code = SecuCode, date = date)
                        if ActualPlaRatio != None:
                            exrights_item.pg = float(ActualPlaRatio) / 10.0
                        if PlaPrice != None:
                            exrights_item.price = float(PlaPrice)
                        exrights_item_dict[date] = exrights_item
                elif SecuMarket == 90:
                    market = "SZ"
                    datas_count_sz += 1
                    if not SecuCode in self.exrights_dict_sz.keys():
                        self.exrights_dict_sz[SecuCode] = {}
                    exrights_item_dict = self.exrights_dict_sz[SecuCode]
                    if date in exrights_item_dict.keys():
                        exrights_item = exrights_item_dict[date]
                        if ActualPlaRatio != None:
                            exrights_item.pg = float(ActualPlaRatio) / 10.0
                        if PlaPrice != None:
                            exrights_item.price = float(PlaPrice)
                    else:
                        exrights_item = ExRightsItem(inners = InnerCode, market = market, code = SecuCode, date = date)
                        if ActualPlaRatio != None:
                            exrights_item.pg = float(ActualPlaRatio) / 10.0
                        if PlaPrice != None:
                            exrights_item.price = float(PlaPrice)
                        exrights_item_dict[date] = exrights_item
            self.SendMessage("获取配股数据成功。上证 %d 个，深证 %d 个。" % (datas_count_sh, datas_count_sz))
        else:
            self.SendMessage("获取配股数据失败！")

    def PullData_FenHong(self, dbm):
        if dbm == None:
            self.SendMessage("PullData_FenHong 数据库 dbm 尚未连接！")
            return
        # 证券市场：83 上海证券交易所、90 深圳证券交易所
        # 证券类别：1 A股、8 开放式基金、62 ETF基金
        # 上市板块：1 主板、2 中小企业板、6 创业板
        # 查询字段：SecuMain：证券内部编码、证券代码、证券市场、证券类别、上市板块
        # 查询字段：LC_Dividend：是否分红、除权除息日、送股比例(10送X)、转增股比例(10转增X)、派现(含税/人民币元)
        # 唯一约束：SecuMain = InnerCode、LC_Dividend = InnerCode, EndDate
        str_sql = "SELECT SecuMain.InnerCode, SecuMain.SecuCode, SecuMain.SecuMarket, SecuMain.SecuCategory, SecuMain.ListedSector, \
                         LC_Dividend.IfDividend, LC_Dividend.ExDiviDate, LC_Dividend.BonusShareRatio, LC_Dividend.TranAddShareRaio, LC_Dividend.CashDiviRMB \
                  FROM SecuMain INNER JOIN LC_Dividend \
                  ON SecuMain.InnerCode = LC_Dividend.InnerCode \
                  WHERE (SecuMain.SecuMarket = 83 OR SecuMain.SecuMarket = 90) \
                    AND (SecuMain.SecuCategory = 1 OR SecuMain.SecuCategory = 8 OR SecuMain.SecuCategory = 62) \
                    AND LC_Dividend.ExDiviDate IS NOT NULL \
                  ORDER BY SecuMain.SecuCode ASC, LC_Dividend.ExDiviDate ASC"
        result_list = dbm.ExecQuery(str_sql)
        datas_count_sh = 0
        datas_count_sz = 0
        if result_list != None:
            for (InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector, IfDividend, ExDiviDate, BonusShareRatio, TranAddShareRaio, CashDiviRMB) in result_list:
                #print(InnerCode, SecuCode, SecuMarket, SecuCategory, ListedSector, IfDividend, ExDiviDate, BonusShareRatio, TranAddShareRaio, CashDiviRMB)
                #print(InnerCode, SecuCode, IfDividend, ExDiviDate, BonusShareRatio, TranAddShareRaio, CashDiviRMB)
                date = ExDiviDate.year * 10000 + ExDiviDate.month * 100 + ExDiviDate.day
                if SecuMarket == 83:
                    market = "SH"
                    datas_count_sh += 1
                    if not SecuCode in self.exrights_dict_sh.keys():
                        self.exrights_dict_sh[SecuCode] = {}
                    exrights_item_dict = self.exrights_dict_sh[SecuCode]
                    if date in exrights_item_dict.keys():
                        exrights_item = exrights_item_dict[date]
                        if BonusShareRatio != None:
                            exrights_item.sg += float(BonusShareRatio) / 10.0
                        if TranAddShareRaio != None:
                            exrights_item.sg += float(TranAddShareRaio) / 10.0
                        if CashDiviRMB != None:
                            exrights_item.bonus += float(CashDiviRMB) / 10.0
                    else:
                        exrights_item = ExRightsItem(inners = InnerCode, market = market, code = SecuCode, date = date)
                        if BonusShareRatio != None:
                            exrights_item.sg += float(BonusShareRatio) / 10.0
                        if TranAddShareRaio != None:
                            exrights_item.sg += float(TranAddShareRaio) / 10.0
                        if CashDiviRMB != None:
                            exrights_item.bonus += float(CashDiviRMB) / 10.0
                        exrights_item_dict[date] = exrights_item
                elif SecuMarket == 90:
                    market = "SZ"
                    datas_count_sz += 1
                    if not SecuCode in self.exrights_dict_sz.keys():
                        self.exrights_dict_sz[SecuCode] = {}
                    exrights_item_dict = self.exrights_dict_sz[SecuCode]
                    if date in exrights_item_dict.keys():
                        exrights_item = exrights_item_dict[date]
                        if BonusShareRatio != None:
                            exrights_item.sg += float(BonusShareRatio) / 10.0
                        if TranAddShareRaio != None:
                            exrights_item.sg += float(TranAddShareRaio) / 10.0
                        if CashDiviRMB != None:
                            exrights_item.bonus += float(CashDiviRMB) / 10.0
                    else:
                        exrights_item = ExRightsItem(inners = InnerCode, market = market, code = SecuCode, date = date)
                        if BonusShareRatio != None:
                            exrights_item.sg += float(BonusShareRatio) / 10.0
                        if TranAddShareRaio != None:
                            exrights_item.sg += float(TranAddShareRaio) / 10.0
                        if CashDiviRMB != None:
                            exrights_item.bonus += float(CashDiviRMB) / 10.0
                        exrights_item_dict[date] = exrights_item
            self.SendMessage("获取分红数据成功。上证 %d 个，深证 %d 个。" % (datas_count_sh, datas_count_sz))
        else:
            self.SendMessage("获取分红数据失败！")

    def CalcMulerAdder(self):
        for value_dict in self.exrights_dict_sh.values():
            for value_item in value_dict.values():
                value_item.muler = 1.0 + value_item.sg + value_item.pg
                value_item.adder = 0.0 - value_item.bonus + value_item.pg * value_item.price
        for value_dict in self.exrights_dict_sz.values():
            for value_item in value_dict.values():
                value_item.muler = 1.0 + value_item.sg + value_item.pg
                value_item.adder = 0.0 - value_item.bonus + value_item.pg * value_item.price

    def SaveData_ExRights(self, dbm, table_name, save_path):
        record_list_temp = []
        exrights_keys_sh = list(self.exrights_dict_sh.keys())
        exrights_keys_sz = list(self.exrights_dict_sz.keys())
        exrights_keys_sh.sort()
        exrights_keys_sz.sort()
        exrights_item_dict_list_sh = [self.exrights_dict_sh[key] for key in exrights_keys_sh]
        exrights_item_dict_list_sz = [self.exrights_dict_sz[key] for key in exrights_keys_sz]
        for exrights_item_dict in exrights_item_dict_list_sh:
            exrights_item_keys = list(exrights_item_dict.keys())
            exrights_item_keys.sort()
            exrights_item_list = [exrights_item_dict[key] for key in exrights_item_keys]
            record_list_temp.extend(exrights_item_list)
            #for exrights_item in exrights_item_list:
            #    print(exrights_item.inners, exrights_item.market, exrights_item.code, exrights_item.date, \
            #          exrights_item.muler, exrights_item.adder, exrights_item.sg, exrights_item.pg, exrights_item.price, exrights_item.bonus)
        for exrights_item_dict in exrights_item_dict_list_sz:
            exrights_item_keys = list(exrights_item_dict.keys())
            exrights_item_keys.sort()
            exrights_item_list = [exrights_item_dict[key] for key in exrights_item_keys]
            record_list_temp.extend(exrights_item_list)
            #for exrights_item in exrights_item_list:
            #    print(exrights_item.inners, exrights_item.market, exrights_item.code, exrights_item.date, \
            #          exrights_item.muler, exrights_item.adder, exrights_item.sg, exrights_item.pg, exrights_item.price, exrights_item.bonus)
        total_record_num = len(record_list_temp)
        
        if dbm != None:
            sql = "SHOW TABLES"
            result = dbm.QueryAllSql(sql)
            data_tables = list(result)
            #print(data_tables)
            have_tables = re.findall("(\'.*?\')", str(data_tables))
            have_tables = [re.sub("'", "", table) for table in have_tables]
            #print(have_tables)
            if table_name in have_tables:
                sql = "TRUNCATE TABLE %s" % table_name
                dbm.ExecuteSql(sql)
            else:
                sql = "CREATE TABLE `%s` (" % table_name + \
                      "`id` int(32) unsigned NOT NULL AUTO_INCREMENT COMMENT '序号'," + \
                      "`inners` int(32) unsigned NOT NULL DEFAULT '0' COMMENT '内部代码'," + \
                      "`market` varchar(32) NOT NULL DEFAULT '' COMMENT '证券市场，SH、SZ'," + \
                      "`code` varchar(32) NOT NULL DEFAULT '' COMMENT '证券代码'," + \
                      "`date` date NOT NULL COMMENT '除权除息日期'," + \
                      "`muler` float(16,7) DEFAULT '0.0000000' COMMENT '乘数'," + \
                      "`adder` float(16,7) DEFAULT '0.0000000' COMMENT '加数'," + \
                      "`sg` float(16,7) DEFAULT '0.0000000' COMMENT '送股比率，每股，非百分比'," + \
                      "`pg` float(16,7) DEFAULT '0.0000000' COMMENT '配股比率，每股，非百分比'," + \
                      "`price` float(10,3) DEFAULT '0.000' COMMENT '配股价，元'," + \
                      "`bonus` float(16,7) DEFAULT '0.0000000' COMMENT '现金红利，每股，元'," + \
                      "PRIMARY KEY (`id`)," + \
                      "UNIQUE KEY `idx_market_code_date` (`market`,`code`,`date`)" + \
                      ") ENGINE=InnoDB DEFAULT CHARSET=utf8"
                dbm.ExecuteSql(sql)
            values = []
            save_record_failed = 0
            save_record_success = 0
            save_index_from = 0 #
            sql = "INSERT INTO %s" % table_name + "(inners, market, code, date, muler, adder, sg, pg, price, bonus) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            for i in range(save_index_from, total_record_num):
                str_date = common.TransDateIntToStr(record_list_temp[i].date)
                values.append((record_list_temp[i].inners, record_list_temp[i].market, record_list_temp[i].code, str_date, record_list_temp[i].muler, record_list_temp[i].adder, record_list_temp[i].sg, record_list_temp[i].pg, record_list_temp[i].price, record_list_temp[i].bonus))
                if (i - save_index_from + 1) % 3000 == 0: # 自定义每批次保存条数
                    if len(values) > 0: # 有记录需要保存
                        if dbm.ExecuteManySql(sql, values) == False:
                            save_record_failed += len(values)
                        else:
                            save_record_success += len(values)
                        #print("保存：", len(values))
                        values = [] #
            if len(values) > 0: # 有记录需要保存
                if dbm.ExecuteManySql(sql, values) == False:
                    save_record_failed += len(values)
                else:
                    save_record_success += len(values)
                #print("保存：", len(values))
            self.SendMessage("远程入库：总记录 %d，入库记录 %d，失败记录 %d。" % (total_record_num, save_record_success, save_record_failed))
        
        values = []
        for i in range(total_record_num):
            str_date = common.TransDateIntToStr(record_list_temp[i].date)
            values.append((record_list_temp[i].inners, record_list_temp[i].market, record_list_temp[i].code, str_date, record_list_temp[i].muler, record_list_temp[i].adder, record_list_temp[i].sg, record_list_temp[i].pg, record_list_temp[i].price, record_list_temp[i].bonus))
        columns = ["inners", "market", "code", "date", "muler", "adder", "sg", "pg", "price", "bonus"]
        result = pd.DataFrame(columns = columns) # 空
        if len(values) > 0:
            result = pd.DataFrame(data = values, columns = columns)
        #print(result)
        result.to_pickle(save_path)
        self.SendMessage("本地保存：总记录 %d，保存记录 %d，失败记录 %d。" % (total_record_num, result.shape[0], total_record_num - result.shape[0]))

class DataMaker_Industry():
    def __init__(self, parent = None):
        self.parent = parent
        self.industry_list = []

    def SendMessage(self, text_info):
        if self.parent != None:
            self.parent.SendMessage(text_info)

    def PullData_Industry(self, dbm):
        if dbm == None:
            self.SendMessage("PullData_Industry 数据库 dbm 尚未连接！")
            return
        self.industry_list = []
        # 证券市场：83 上海证券交易所、90 深圳证券交易所
        # 证券类别：1 A股
        # 上市板块：1 主板、2 中小企业板、6 创业板
        # 查询字段：SecuMain：证券内部编码、证券代码、证券简称、证券市场
        # 查询字段：LC_ExgIndustry：信息发布日期、行业划分标准、所属行业、是否执行、
        #                           一级行业代码、一级行业名称、二级行业代码、二级行业名称、三级行业代码、三级行业名称、四级行业代码、四级行业名称
        # 唯一约束：SecuMain = InnerCode、LC_ExgIndustry = CompanyCode & InfoPublDate & Standard & Industry & IfPerformed
        str_sql = "SELECT SecuMain.InnerCode, SecuMain.SecuCode, SecuMain.SecuAbbr, SecuMain.SecuMarket, \
                         LC_ExgIndustry.InfoPublDate, LC_ExgIndustry.Standard, LC_ExgIndustry.Industry, LC_ExgIndustry.IfPerformed, \
                         LC_ExgIndustry.FirstIndustryCode, LC_ExgIndustry.FirstIndustryName, LC_ExgIndustry.SecondIndustryCode, LC_ExgIndustry.SecondIndustryName, \
                         LC_ExgIndustry.ThirdIndustryCode, LC_ExgIndustry.ThirdIndustryName, LC_ExgIndustry.FourthIndustryCode, LC_ExgIndustry.FourthIndustryName \
                  FROM SecuMain INNER JOIN LC_ExgIndustry \
                  ON SecuMain.CompanyCode = LC_ExgIndustry.CompanyCode \
                  WHERE (SecuMain.SecuMarket = 83 OR SecuMain.SecuMarket = 90) \
                    AND (SecuMain.SecuCategory = 1) \
                    AND (SecuMain.ListedSector = 1 or SecuMain.ListedSector = 2 or SecuMain.ListedSector = 6) \
                    AND (LC_ExgIndustry.IfPerformed = 1) \
                  ORDER BY LC_ExgIndustry.Standard ASC, LC_ExgIndustry.Industry ASC, \
                           LC_ExgIndustry.FirstIndustryCode ASC, LC_ExgIndustry.SecondIndustryCode ASC, LC_ExgIndustry.ThirdIndustryCode ASC, LC_ExgIndustry.FourthIndustryCode ASC"
        result_list = dbm.ExecQuery(str_sql)
        if result_list != None:
            for (InnerCode, SecuCode, SecuAbbr, SecuMarket, InfoPublDate, Standard, Industry, IfPerformed, FirstIndustryCode, FirstIndustryName, SecondIndustryCode, SecondIndustryName, ThirdIndustryCode, ThirdIndustryName, FourthIndustryCode, FourthIndustryName) in result_list:
                stock_market = ""
                if SecuMarket == 83:
                    stock_market = "SH"
                elif SecuMarket == 90:
                    stock_market = "SZ"
                industry_item = IndustryItem(standard = Standard, industry = Industry, inners = InnerCode, market = stock_market, code = SecuCode, name = SecuAbbr, 
                                    industry_code_1 = FirstIndustryCode, industry_name_1 = FirstIndustryName, industry_code_2 = SecondIndustryCode, industry_name_2 = SecondIndustryName, 
                                    industry_code_3 = ThirdIndustryCode, industry_name_3 = ThirdIndustryName, industry_code_4 = FourthIndustryCode, industry_name_4 = FourthIndustryName)
                industry_item.SetInfoDate(InfoPublDate) #
                self.industry_list.append(industry_item)
                #print(InnerCode, SecuCode, SecuAbbr, SecuMarket, InfoPublDate, Standard, Industry, IfPerformed, FirstIndustryCode, FirstIndustryName, SecondIndustryCode, SecondIndustryName, ThirdIndustryCode, ThirdIndustryName, FourthIndustryCode, FourthIndustryName)
            self.SendMessage("获取 行业划分 成功。总计 %d 个。" % len(result_list))
        else:
            self.SendMessage("获取 行业划分 失败！")

    def SaveData_Industry(self, dbm, table_name, save_path):
        total_record_num = len(self.industry_list)
        
        if dbm != None:
            sql = "SHOW TABLES"
            result = dbm.QueryAllSql(sql)
            data_tables = list(result)
            #print(data_tables)
            have_tables = re.findall("(\'.*?\')", str(data_tables))
            have_tables = [re.sub("'", "", table) for table in have_tables]
            #print(have_tables)
            if table_name in have_tables:
                sql = "TRUNCATE TABLE %s" % table_name
                dbm.ExecuteSql(sql)
            else:
                sql = "CREATE TABLE `%s` (" % table_name + \
                      "`id` int(32) unsigned NOT NULL AUTO_INCREMENT COMMENT '序号'," + \
                      "`standard` int(32) NOT NULL DEFAULT '0' COMMENT '行业划分标准'," + \
                      "`industry` int(32) NOT NULL DEFAULT '0' COMMENT '所属行业'," + \
                      "`industry_code_1` varchar(32) DEFAULT '' COMMENT '一级行业代码'," + \
                      "`industry_name_1` varchar(100) DEFAULT '' COMMENT '一级行业名称'," + \
                      "`industry_code_2` varchar(32) DEFAULT '' COMMENT '二级行业代码'," + \
                      "`industry_name_2` varchar(100) DEFAULT '' COMMENT '二级行业名称'," + \
                      "`industry_code_3` varchar(32) DEFAULT '' COMMENT '三级行业代码'," + \
                      "`industry_name_3` varchar(100) DEFAULT '' COMMENT '三级行业名称'," + \
                      "`industry_code_4` varchar(32) DEFAULT '' COMMENT '四级行业代码'," + \
                      "`industry_name_4` varchar(100) DEFAULT '' COMMENT '四级行业名称'," + \
                      "`inners` int(32) unsigned NOT NULL DEFAULT '0' COMMENT '内部代码'," + \
                      "`market` varchar(32) NOT NULL DEFAULT '' COMMENT '证券市场，SH、SZ'," + \
                      "`code` varchar(32) NOT NULL DEFAULT '' COMMENT '证券代码'," + \
                      "`name` varchar(32) DEFAULT '' COMMENT '证券名称'," + \
                      "`info_date` date NOT NULL COMMENT '信息日期'," + \
                      "PRIMARY KEY (`id`)," + \
                      "UNIQUE KEY `idx_standard_industry_market_code_info_date` (`standard`,`industry`,`market`,`code`,`info_date`)" + \
                      ") ENGINE=InnoDB DEFAULT CHARSET=utf8"
                dbm.ExecuteSql(sql)
            values = []
            save_record_failed = 0
            save_record_success = 0
            save_index_from = 0 #
            sql = "INSERT INTO %s" % table_name + "(standard, industry, industry_code_1, industry_name_1, industry_code_2, industry_name_2, industry_code_3, industry_name_3, industry_code_4, industry_name_4, inners, market, code, name, info_date) \
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            for i in range(save_index_from, total_record_num):
                str_date = common.TransDateIntToStr(self.industry_list[i].info_date)
                values.append((self.industry_list[i].standard, self.industry_list[i].industry, 
                               self.industry_list[i].industry_code_1, self.industry_list[i].industry_name_1, self.industry_list[i].industry_code_2, self.industry_list[i].industry_name_2, 
                               self.industry_list[i].industry_code_3, self.industry_list[i].industry_name_3, self.industry_list[i].industry_code_4, self.industry_list[i].industry_name_4, 
                               self.industry_list[i].inners, self.industry_list[i].market, self.industry_list[i].code, self.industry_list[i].name, str_date))
                if (i - save_index_from + 1) % 3000 == 0: # 自定义每批次保存条数
                    if len(values) > 0: # 有记录需要保存
                        if dbm.ExecuteManySql(sql, values) == False:
                            save_record_failed += len(values)
                        else:
                            save_record_success += len(values)
                        #print("保存：", len(values))
                        values = [] #
            if len(values) > 0: # 有记录需要保存
                if dbm.ExecuteManySql(sql, values) == False:
                    save_record_failed += len(values)
                else:
                    save_record_success += len(values)
                #print("保存：", len(values))
            self.SendMessage("远程入库：总记录 %d，入库记录 %d，失败记录 %d。" % (total_record_num, save_record_success, save_record_failed))
        
        values = []
        for i in range(total_record_num):
            str_date = common.TransDateIntToStr(self.industry_list[i].info_date)
            values.append((self.industry_list[i].standard, self.industry_list[i].industry, 
                           self.industry_list[i].industry_code_1, self.industry_list[i].industry_name_1, self.industry_list[i].industry_code_2, self.industry_list[i].industry_name_2, 
                           self.industry_list[i].industry_code_3, self.industry_list[i].industry_name_3, self.industry_list[i].industry_code_4, self.industry_list[i].industry_name_4, 
                           self.industry_list[i].inners, self.industry_list[i].market, self.industry_list[i].code, self.industry_list[i].name, str_date))
        columns = ["standard", "industry", "industry_code_1", "industry_name_1", "industry_code_2", "industry_name_2", 
                   "industry_code_3", "industry_name_3", "industry_code_4", "industry_name_4", "inners", "market", "code", "name", "info_date"]
        result = pd.DataFrame(columns = columns) # 空
        if len(values) > 0:
            result = pd.DataFrame(data = values, columns = columns)
        #print(result)
        result.to_pickle(save_path)
        self.SendMessage("本地保存：总记录 %d，保存记录 %d，失败记录 %d。" % (total_record_num, result.shape[0], total_record_num - result.shape[0]))

class BasicDataMaker(QDialog):
    def __init__(self, **kwargs):
        super(BasicDataMaker, self).__init__()
        self.folder = kwargs.get("folder", "") # 数据文件缓存
        self.tb_trading_day = "trading_day"
        self.tb_industry_data = "industry_data"
        self.tb_security_info = "security_info"
        self.tb_capital_data = "capital_data"
        self.tb_ex_rights_data = "ex_rights_data"
        self.tb_tod_ting_pai = "tod_ting_pai"
        
        self.mssql_host = "0.0.0.0"
        self.mssql_port = 0
        self.mssql_user = "user"
        self.mssql_password = "123456"
        self.mssql_database = "test"
        self.mssql_charset = "utf8"
        
        self.mysql_host = "0.0.0.0"
        self.mysql_port = 0
        self.mysql_user = "user"
        self.mysql_passwd = "123456"
        self.mysql_database = "test"
        self.mysql_charset = "utf8"
        
        self.dbm_jydb = None
        self.dbm_financial = None
        
        self.text_info_list = []
        self.text_info_index = 0
        self.flag_data_make = False # 手动点击就不用锁了
        self.flag_use_database = False
        
        if self.folder != "":
            self.folder_financial = self.folder + "/financial" # 可能路径含中文
            self.folder_quotedata = self.folder + "/quotedata" # 可能路径含中文
            self.folder_quotedata_stock = self.folder_quotedata + "/stock"
            self.folder_quotedata_stock_daily = self.folder_quotedata_stock + "/daily"
            self.folder_quotedata_stock_kline_1_m = self.folder_quotedata_stock + "/kline_1_m"
            if not os.path.exists(self.folder_financial):
                os.makedirs(self.folder_financial)
            # 下面已包含 folder_quotedata 和 folder_quotedata_stock 文件夹创建
            if not os.path.exists(self.folder_quotedata_stock_daily):
                os.makedirs(self.folder_quotedata_stock_daily)
            if not os.path.exists(self.folder_quotedata_stock_kline_1_m):
                os.makedirs(self.folder_quotedata_stock_kline_1_m)
        
        self.InitUserInterface()

    def __del__(self):
        pass

    def event(self, event):
        if event.type() == DEF_EVENT_TEXT_INFO_PRINT:
            self.OnTextInfoPrint()
        return QDialog.event(self, event)

    def OnTextInfoPrint(self):
        text_info_count = len(self.text_info_list)
        if text_info_count > self.text_info_index:
            for i in range(self.text_info_index, text_info_count):
                self.text_edit_text_info.append(self.text_info_list[i])
            self.text_edit_text_info.moveCursor(QTextCursor.End)
            self.text_info_index = text_info_count #

    def SendMessage(self, text_info):
        self.text_info_list.append(text_info)
        QApplication.postEvent(self, QEvent(DEF_EVENT_TEXT_INFO_PRINT))

    def SetMsSQL(self, **kwargs):
        self.mssql_host = kwargs.get("host", "0.0.0.0")
        self.mssql_port = kwargs.get("port", "0")
        self.mssql_user = kwargs.get("user", "user")
        self.mssql_password = kwargs.get("password", "123456")
        self.mssql_database = kwargs.get("database", "test")
        self.mssql_charset = kwargs.get("charset", "utf8")

    def SetMySQL(self, **kwargs):
        self.mysql_host = kwargs.get("host", "0.0.0.0")
        self.mysql_port = kwargs.get("port", 0)
        self.mysql_user = kwargs.get("user", "user")
        self.mysql_passwd = kwargs.get("passwd", "123456")
        self.mysql_db = kwargs.get("db", "test")
        self.mysql_charset = kwargs.get("charset", "utf8")
        self.flag_use_database = True #

    def ConnectDB(self):
        self.DisconnectDB() #
        try:
            self.dbm_jydb = dbm_mssql.DBM_MsSQL(host = self.mssql_host, port = self.mssql_port, user = self.mssql_user, password = self.mssql_password, database = self.mssql_database, charset = self.mssql_charset)
            if self.dbm_jydb.Start() == True:
                self.SendMessage("数据库 jydb 连接完成。")
            else:
                self.SendMessage("数据库 jydb 连接失败！")
            if self.flag_use_database == True:
                self.dbm_financial = dbm_mysql.DBM_MySQL(host = self.mysql_host, port = self.mysql_port, user = self.mysql_user, passwd = self.mysql_passwd, db = self.mysql_db, charset = self.mysql_charset)
                if self.dbm_financial.Connect() == True:
                    self.SendMessage("数据库 financial 连接完成。")
                else:
                    self.SendMessage("数据库 financial 连接失败！")
            else:
                self.SendMessage("不使用数据库 financial 保存基础数据。")
        except Exception as e:
            self.SendMessage("建立数据库连接发生异常！%s" % e)

    def DisconnectDB(self):
        try:
            if self.dbm_jydb != None:
                self.dbm_jydb.Stop()
                self.dbm_jydb = None
                self.SendMessage("数据库 jydb 连接断开！")
            if self.flag_use_database == True:
                if self.dbm_financial != None:
                    self.dbm_financial.Disconnect()
                    self.dbm_financial = None
                    self.SendMessage("数据库 financial 连接断开！")
        except Exception as e:
            self.SendMessage("断开数据库连接发生异常！%s" % e)

    def InitUserInterface(self):
        self.setWindowTitle("基础数据生成")
        self.resize(400, 600)
        self.setFont(QFont("SimSun", 9))
        
        self.text_edit_text_info = QTextEdit()
        self.text_edit_text_info.setLineWrapMode(QTextEdit.NoWrap) # 不自动换行
        
        self.button_connect_db = QPushButton("数据库连接")
        self.button_connect_db.setFont(QFont("SimSun", 9))
        self.button_connect_db.setStyleSheet("color:black")
        self.button_connect_db.setFixedWidth(70)
        
        self.button_disconnect_db = QPushButton("数据库断开")
        self.button_disconnect_db.setFont(QFont("SimSun", 9))
        self.button_disconnect_db.setStyleSheet("color:black")
        self.button_disconnect_db.setFixedWidth(70)
        
        self.button_capital = QPushButton("股本结构")
        self.button_capital.setFont(QFont("SimSun", 9))
        self.button_capital.setStyleSheet("color:blue")
        self.button_capital.setFixedWidth(70)
        
        self.button_capital = QPushButton("股本结构")
        self.button_capital.setFont(QFont("SimSun", 9))
        self.button_capital.setStyleSheet("color:blue")
        self.button_capital.setFixedWidth(70)
        
        self.button_exrights = QPushButton("除权数据")
        self.button_exrights.setFont(QFont("SimSun", 9))
        self.button_exrights.setStyleSheet("color:blue")
        self.button_exrights.setFixedWidth(70)
        
        self.button_industry = QPushButton("行业划分")
        self.button_industry.setFont(QFont("SimSun", 9))
        self.button_industry.setStyleSheet("color:blue")
        self.button_industry.setFixedWidth(70)
        
        self.h_box_layout_database = QHBoxLayout()
        self.h_box_layout_database.setContentsMargins(-1, -1, -1, -1)
        self.h_box_layout_database.addWidget(self.button_connect_db)
        self.h_box_layout_database.addWidget(self.button_disconnect_db)
        self.h_box_layout_database.addStretch(1)
        
        self.h_box_layout_buttons = QHBoxLayout()
        self.h_box_layout_buttons.setContentsMargins(-1, -1, -1, -1)
        self.h_box_layout_buttons.addWidget(self.button_capital)
        self.h_box_layout_buttons.addWidget(self.button_exrights)
        self.h_box_layout_buttons.addWidget(self.button_industry)
        self.h_box_layout_buttons.addStretch(1)
        
        self.h_box_layout_text_info = QHBoxLayout()
        self.h_box_layout_text_info.setContentsMargins(-1, -1, -1, -1)
        self.h_box_layout_text_info.addWidget(self.text_edit_text_info)
        
        self.v_box_layout = QVBoxLayout()
        self.v_box_layout.setContentsMargins(-1, -1, -1, -1)
        self.v_box_layout.addLayout(self.h_box_layout_text_info)
        self.v_box_layout.addLayout(self.h_box_layout_database)
        self.v_box_layout.addLayout(self.h_box_layout_buttons)
        
        self.setLayout(self.v_box_layout)
        
        self.button_connect_db.clicked.connect(self.ConnectDB)
        self.button_disconnect_db.clicked.connect(self.DisconnectDB)
        self.button_capital.clicked.connect(self.OnButtonCapital)
        self.button_exrights.clicked.connect(self.OnButtonExRights)
        self.button_industry.clicked.connect(self.OnButtonIndustry)

    def Thread_Capital(self, data_type):
        if self.flag_data_make == False:
            self.flag_data_make = True
            try:
                self.SendMessage("\n# -------------------- %s -------------------- #" % data_type)
                save_path = "%s/%s" % (self.folder_financial, self.tb_capital_data)
                data_maker_capital = DataMaker_Capital(self)
                data_maker_capital.PullData_Capital(self.dbm_jydb)
                data_maker_capital.SaveData_Capital(self.dbm_financial, self.tb_capital_data, save_path)
                self.SendMessage("# -------------------- %s -------------------- #" % data_type)
            except Exception as e:
                self.SendMessage("生成 %s 发生异常！%s" % (data_type, e))
            self.flag_data_make = False #
        else:
            self.SendMessage("正在生成数据，请等待...")

    def Thread_ExRights(self, data_type):
        if self.flag_data_make == False:
            self.flag_data_make = True
            try:
                self.SendMessage("\n# -------------------- %s -------------------- #" % data_type)
                save_path = "%s/%s" % (self.folder_financial, self.tb_ex_rights_data)
                data_maker_exrights = DataMaker_ExRights(self)
                data_maker_exrights.PullData_Stock(self.dbm_jydb)
                data_maker_exrights.PullData_PeiGu(self.dbm_jydb)
                data_maker_exrights.PullData_FenHong(self.dbm_jydb)
                data_maker_exrights.CalcMulerAdder()
                data_maker_exrights.SaveData_ExRights(self.dbm_financial, self.tb_ex_rights_data, save_path)
                self.SendMessage("# -------------------- %s -------------------- #" % data_type)
            except Exception as e:
                self.SendMessage("生成 %s 发生异常！%s" % (data_type, e))
            self.flag_data_make = False #
        else:
            self.SendMessage("正在生成数据，请等待...")

    def Thread_Industry(self, data_type):
        if self.flag_data_make == False:
            self.flag_data_make = True
            try:
                self.SendMessage("\n# -------------------- %s -------------------- #" % data_type)
                save_path = "%s/%s" % (self.folder_financial, self.tb_industry_data)
                data_maker_industry = DataMaker_Industry(self)
                data_maker_industry.PullData_Industry(self.dbm_jydb)
                data_maker_industry.SaveData_Industry(self.dbm_financial, self.tb_industry_data, save_path)
                self.SendMessage("# -------------------- %s -------------------- #" % data_type)
            except Exception as e:
                self.SendMessage("生成 %s 发生异常！%s" % (data_type, e))
            self.flag_data_make = False #
        else:
            self.SendMessage("正在生成数据，请等待...")

    def OnButtonCapital(self):
        self.thread_make_data = threading.Thread(target = self.Thread_Capital, args = ("股本结构",))
        self.thread_make_data.start()

    def OnButtonExRights(self):
        self.thread_make_data = threading.Thread(target = self.Thread_ExRights, args = ("除权数据",))
        self.thread_make_data.start()

    def OnButtonIndustry(self):
        self.thread_make_data = threading.Thread(target = self.Thread_Industry, args = ("行业划分",))
        self.thread_make_data.start()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    basic_data_maker = BasicDataMaker(folder = "../data")
    basic_data_maker.SetMsSQL(host = "10.0.7.80", port = "1433", user = "user", password = "user", database = "JYDB_NEW", charset = "GBK")
    basic_data_maker.SetMySQL(host = "10.0.7.80", port = 3306, user = "user", passwd = "user", db = "financial", charset = "utf8")
    basic_data_maker.show()
    sys.exit(app.exec_())
