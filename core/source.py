# @Author  : GentleCP
# @Email   : 574881148@qq.com
# @File    : source.py
# @Item    : PyCharm
# @Time    : 2019-11-18 15:51
# @WebSite : https://www.gentlecp.com

import os
import sys
import logging
import re
import requests

from bs4 import BeautifulSoup
from prettytable import PrettyTable


sys.setrecursionlimit(100000)

class BackToMain(Exception):
    pass
class Loginer:
    def __init__(self, user_info, urls):
        self._logger = logging.getLogger("Loginer")
        self._S = requests.session()
        self._user_info = user_info
        self._urls = urls

    def _login(self):
        headers = {
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'Origin': 'http://onestop.ucas.ac.cn',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'http://onestop.ucas.ac.cn/',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        try:
            res = self._S.post(url=self._urls["login_url"], data=self._user_info, headers=headers, timeout=2)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout):
            self._logger.error("网络连接失败，请确认你的网络环境后重试！")
            exit(400)
        else:
            json_res = res.json()
            if json_res["f"]:
                self._S.get(res.json()["msg"])
                self._logger.info("登录成功！")

            else:
                self._logger.error("登录失败，请检查settings下的USER_INFO是否正确！")
                exit(401)


class Downloader(Loginer):
    def __init__(self, user_info, urls, source_dir):
        super().__init__(user_info, urls)
        self._logger = logging.getLogger("Downloader")
        self._source_dir = source_dir
        self._update_sources = []
        self._l_course_info = []
        self._d_source_info = {}
        self._S = requests.session()
        self._cur_course_info = None

        self.__check_dir(self._source_dir)

    def __check_dir(self, dir):
        if not os.path.exists(dir):
            try:
                os.mkdir(dir)
            except FileNotFoundError:
                self._logger.error("资源存储路径非法或不正确，请检查settings中SOURCE_DIR配置！")
                exit(404)

    def _set_course_info(self):
        if not self._l_course_info:
            # 减少后续多次请求课程信息耗时
            res = self._S.get(url=self._urls['course_info_url'])
            bsobj = BeautifulSoup(res.text, "html.parser")
            refresh_url = bsobj.find("noscript").meta.get("content")[6:]  # 获取新的定向url
            res = self._S.get(refresh_url)
            bsobj = BeautifulSoup(res.text, "html.parser")
            new_course_url = bsobj.find('a', {"title": "我的课程 - 查看或加入站点"}).get("href")  # 获取到新的课程信息url
            res = self._S.get(new_course_url)
            bsobj = BeautifulSoup(res.text, "html.parser")
            course_list = bsobj.findAll('tr')  # 尚未筛选的杂乱信息
            i = 1
            for course in course_list:
                a = course.find('a')
                course_url = a.get("href")
                course_name = a.get_text()
                if "课程名称" not in course_name:
                    self._l_course_info.append({'id': i, 'name': course_name, 'url': course_url})
                    self._d_source_info.update({course_name: []})  # 为该课程开辟一个位置
                    i += 1

    def _set_source_info(self, course_info):
        '''
        给定一门课(name+url)，获取该课的所有课程资源
        :param course:
        :return:
        '''
        if not self._d_source_info[course_info["name"]]:
            # 该门课的资源信息尚未存储到内存
            res = self._S.get(course_info["url"])
            bs4obj = BeautifulSoup(res.text, "html.parser")
            source_url = bs4obj.find('a', {'title': '资源 - 上传、下载课件，发布文档，网址等信息'}).get("href")
            res = self._S.get(source_url)
            bs4obj = BeautifulSoup(res.text, "html.parser")
            i = 1
            for e in bs4obj.findAll('a'):
                try:
                    if 'http://course.ucas.ac.cn/access/content/group' in e["href"]:
                        filename = e.find('span', {'class': 'hidden-sm hidden-xs'}).get_text()
                        self._d_source_info[course_info["name"]].append({'id': i, 'name': filename, 'url': e["href"]})
                        i += 1
                except (KeyError, AttributeError):
                    continue

    def _download_one(self, course_info, source_info):
        '''
        给定一门课，下载该门课指定一个资源
        :return:
        '''
        dir = self._source_dir + '/' + course_info["name"]
        if not os.path.exists(dir):
            os.mkdir(dir)
        file_path = self._source_dir + '/' + course_info["name"] + '/' + source_info['name']
        if not os.path.isfile(file_path):
            # 只下载没有的文件，若存在不下载，节省流量
            self._logger.info("正在下载:{}".format(source_info['name']))
            content = self._S.get(source_info['url']).content
            with open(file_path, 'wb') as f:
                f.write(content)
            self._update_sources.append("[{}:{}]".format(course_info["name"], source_info['name']))  # 记录更新的课程数据

    def _download_course(self, course_info):
        '''
        下载一门课的所有资源
        :param S: 
        :param course_info:
        :return: 
        '''
        print("正在同步{}全部资源...".format(course_info["name"]))
        for source_info in self._d_source_info[course_info["name"]]:
            self._download_one(course_info, source_info)

    def _download_all(self):
        for course_info in self._l_course_info:
            self._set_source_info(course_info)
            self._download_course(course_info)
        if self._update_sources:
            self._logger.info("[同步完成] 本次更新资源列表如下：")

            for source in self._update_sources:
                print(source)
        else:
            self._logger.info("[同步完成] 本次无更新内容！")

    def _show(self, infos):
        if infos:
            for info in infos:
                print("[{}]:{}".format(info['id'], info['name']))
        else:
            print("尚无信息！")

    def __check_option(self, option):
        if option == 'q':
            raise BackToMain

        elif option == 'b' and self._cur_course_info:
            self._cur_course_info = None  # 清空
            return True

        elif option == 'd':
            self._download_all()
            return False

        elif option == 'a' and self._cur_course_info:
            self._download_course(course_info=self._cur_course_info)

        elif option.isdigit() and self._cur_course_info:
            # 课程界面操作
            try:
                source_info = self._d_source_info[self._cur_course_info["name"]][int(option) - 1]
            except IndexError:
                self._logger.warning("不存在该序号课程资源，请重新选择！")
            else:
                self._download_one(self._cur_course_info, source_info)

        elif option.isdigit():
            # 主界面操作
            try:
                self._cur_course_info = self._l_course_info[(int(option) - 1)]
            except IndexError:
                self._logger.warning("不存在该序号课程，请重新选择！")
            else:
                self._set_source_info(self._cur_course_info)
                return True

        else:
            self._logger.warning("非法操作，请重新输入")
            return False

    def _cmd(self):
        while True:
            print(">本学期课程列表：", flush=True)
            self._show(self._l_course_info)
            option = input("请输入你的操作（id:显示对应课程的所有资源;d:一键同步所有资源;q:回到主界面）：")
            if not self.__check_option(option):
                # 不进入下一级界面
                continue
            while True:
                print(">本学期课程列表>{}:".format(self._cur_course_info["name"]))
                self._show(self._d_source_info[self._cur_course_info["name"]])
                option = input("请输入你的操作（id:下载对应id资源;a:下载所有;b:返回上一级;q:回到主界面）：")
                if self.__check_option(option):
                    # 接收到返回上级界面信息
                    break

    def run(self):
        self._login()
        self._set_course_info()  # 添加所有课程信息到内存中
        self._cmd()  # 进入交互界面


import settings


class GradeObserver(Loginer):

    def __init__(self, user_info, urls):
        super().__init__(user_info, urls)
        self._logger = logging.getLogger("GradeObserver")


    def _check_apply(self):
        res = self._S.get(self._urls['gm_scholar_url'])
        bs4obj = BeautifulSoup(res.text,'html.parser')
        if bs4obj.find('button',{'value':'123'}).string.strip()=='提交导师审核':
            return True
        return False

    def _getinto_scholarship(self):
        res = self._S.get(url=self._urls['scholarship_url'])
        scholar_url = re.search(r"window.location.href='(?P<scholar_url>.*?)'", res.text).groupdict().get("scholar_url")
        self._S.get(scholar_url)

    def _post_scholarship_form(self):
        res = self._S.get(self._urls['zlyh_url'])
        bs4obj = BeautifulSoup(res.text, 'html.parser')
        person_id = bs4obj.find('input', {'id': 'Personid'}).get("value")
        data = {
            'person_id': person_id,
            'year_no': bs4obj.find('input', {'id': 'year_no'}).get("value"),
            'AwardId': '123',
            'Account': bs4obj.find('input', {'id': 'Account'}).get("value"),
            'Email': bs4obj.find('input', {'id': 'Email'}).get("value"),
            'Mobile': bs4obj.find('input', {'id': 'Mobile'}).get("value"),
            'start_end_time1': '',
            'study_work_unit1': '',
            'what_degree1': '',
            'start_end_time2': '',
            'study_work_unit2': '',
            'what_degree2': '',
            'start_end_time3': '',
            'study_work_unit3': '',
            'what_degree3': '',
            'start_end_time4': '',
            'study_work_unit4': '',
            'what_degree4': '',
            'gnkw': '',
            'gjkw': '',
            'gnxshy': '',
            'gjxshy': '',
            'hxqk': '',
            'sciei': '',
            'gnkw_dyzz': '',
            'gjkw_dyzz': '',
            'gnxshy_dyzz': '',
            'gjxshy_dyzz': '',
            'hxqk_dyzz': '',
            'sciei_dyzz': '',
            'lwmc_add': '',
            'lwsmsx_add': '',
            'fbsj_add': '',
            'kwmc_add': '',
            'zzmc_add': '',
            'zzsmsx_add': '',
            'cbsj_add': '',
            'cbsmc_add': '',
            'zlh_add': '',
            'zlmc_add': '',
            'hjsj_add': '',
            'qbfmrpx_add': '',
            'zlqr_add': '',
            'how_a_degree': '1',
            'title': '1',
            'category': '基础研究',
            'actual_performance': '1',
            'filevideo': '(binary)',
            'Personid': person_id,
            'StatusCode': '0',
            'Createtime': bs4obj.find('input', {'id': 'Createtime'}).get("value"),
            'xkq_id': '0',
            'display_order': '0'
        }
        self._S.post(self._urls['edit_zlyu_url'], data=data)

    def _show_grades(self):
        res = self._S.get(self._urls['zlyh_url'])
        bs4obj = BeautifulSoup(res.text, 'html.parser')
        grades_url = 'http://scholarship.ucas.ac.cn' + bs4obj.find('a', {'target': '_blank'}).get("href")
        res = self._S.get(grades_url)
        bs4obj = BeautifulSoup(res.text, 'html.parser')
        grades_info = bs4obj.find_all('table')[6].find_all('td')
        step = 6
        new_grades_info = [grades_info[i:i + step] for i in range(0, len(grades_info), step)][0:-1]
        new_grades_info = [[i.string for i in x] for x in new_grades_info]
        tb = PrettyTable()
        fields = ["学年学期", "课程名称", "学位课", "学时","学分","成绩"]
        tb.field_names = fields # 设置表头名称
        for info in new_grades_info:
            tb.add_row(info)
        self._logger.info("获取成绩成功，如下：")
        print(tb)


    def run(self):
        self._login()
        self._getinto_scholarship()
        if not self._check_apply():
            self._post_scholarship_form()
        self._show_grades()

