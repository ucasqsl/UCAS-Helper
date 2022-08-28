# -*- coding: utf-8 -*-
"""
-----------------Init-----------------------
            Name: course.py
            Description:
            Author: ucasqsl
            Email: qinsiliang18@mails.ucas.ac.cn
-------------Change Logs--------------------


--------------------------------------------
"""
import requests
import logging
from bs4 import BeautifulSoup
from prettytable import PrettyTable
import json
from core.login import Loginer
from handler.logger import LogHandler
from io import BytesIO
from PIL import Image
from util.ocr import do_ocr
import pandas as pd
from ddddocr import DdddOcr
from time import sleep

class CourseSelector(Loginer):
    """
    课程选择器
    """

    def __init__(self,
                 urls=None,
                 user_config_path='conf/user_config.ini',
                 course_config_path = "config.json",
                 *args, **kwargs):
        super().__init__(urls, user_config_path, *args, **kwargs)
        with open(course_config_path, "r") as f:
            course_config = json.load(f)
        self.depts = course_config['departments']
        self.course_ids = course_config['course_ids']
        self._logger = LogHandler('CourseSelector')
        self.ocr = DdddOcr(det=False, ocr=False, import_onnx_path="models/ucas_ocr_1.0_6_2000_2022-08-27-15-33-41.onnx", charsets_path="models/charsets.json")

    def _get_action(self):
        try:
            res = self._S.get(self._urls['base_select_url']['http'], headers=self.headers, timeout=5)
        except requests.Timeout:
            res = self._S.get(self._urls['base_select_url']['https'],headers=self.headers)
        bs4oj = BeautifulSoup(res.text, 'html.parser')
        form = bs4oj.find_all("form")[1]
        departments = form.find_all("div", {"class":"span2"})
        self._department = {}
        for department in departments:
            label = department.find("label")
            id = label.attrs['for']
            name = label.contents[0]
            self._department[name] = id[3:]
        action = form.attrs['action']
        self._s = action.split("?")

    def _get_selected_course(self):
        try:
            res = self._S.get(self._urls['base_select_url']['http'], headers=self.headers, timeout=5)
        except requests.Timeout:
            res = self._S.get(self._urls['base_select_url']['https'],headers=self.headers)
        bs4obj = BeautifulSoup(res.text, 'html.parser')
        thead = bs4obj.find('thead')
        data = []
        columns = [x.string for x in thead.find_all('th')[:-3]]
        tbody = bs4obj.find('tbody')
        for tr in tbody.find_all('tr'):
            # tr:每一门课程信息
            tds = tr.find_all('td')
            ids = [x.find("a").string.strip() for x in tds[:2]]
            row = ids + [x.text.lstrip().rstrip() for x in tds[2:-4]] + [tds[-4].find("a").string.strip()]
            data.append(row)
        df = pd.DataFrame(data, columns = columns)
        self._selected_course = df

    def _get_courses(self):
        deptIds = []
        for department in self.depts:
            deptIds.append(int(self._department[department]))
        post_data = {
            "deptIds": deptIds,
            "sb": 0
        }
        self.deptIds = deptIds
        try:
            res = self._S.post(self._urls['base_url']['http'] + f"/courseManage/selectCourse?{self._s}", data = post_data, headers=self.headers, timeout=5)
        except requests.Timeout:
            res = self._S.post(self._urls['base_url']['https'] + f"/courseManage/selectCourse?{self._s}", data = post_data, headers=self.headers)
        bs4obj = BeautifulSoup(res.text, 'html.parser')
        thead = bs4obj.find('thead')
        data = []
        columns = [x.string for x in thead.find_all('th')]
        tbody = bs4obj.find('tbody')
        for tr in tbody.find_all('tr'):
            # tr:每一门课程信息
            tds = tr.find_all('td')
            ids = [x.find("input").attrs["value"] for x in tds[:3]]
            row = ids + [x.string.strip() for x in tds[3:]]
            data.append(row)
        df = pd.DataFrame(data, columns = columns)
        # print(pt)
        self._df = df

    def _captcha(self, img):
        with open("captcha.png", "wb") as f:
            f.write(img)
        # return int(input("Solving the captcha in captcha.png >>"))
        text = self.ocr.classification(img)
        expr = text[:3]
        # self._logger.info(f"Captcha Content: {text}")
        # text2 = self.num_ocr.classification(img)
        # expr = text2[0] + text[1] + text2[2]
        self._logger.info(f"Captcha Content: {expr}")
        return int(eval(expr))

    def _validate(self):
        try:
            res = self._S.get(self._urls['base_url']['http'] + "/captchaImage",headers=self.headers, timeout=5)
        except requests.Timeout:
            res = self._S.get(self._urls['base_url']['https'] + "/captchaImage",headers=self.headers)
        validate = self._captcha(res.content)
        return validate

    def _select_course(self):
        self._df['限选'] = self._df['限选'].transform(int)
        self._df['已选'] = self._df['已选'].transform(int)
        course_ids = self._df.loc[
            self._df['课程编码'].isin(self.course_ids)
            & (self._df['限选'] > self._df['已选'])]['选课']
        if len(course_ids) == 0:
            self._logger.info(f"Courses not enough for {self.course_ids}")
            return
        while True:
            try:
                vcode=self._validate()
            except:
                continue
            break
        post_data = {
            "_csrftoken":"",
            "deptIds":self.deptIds,
            "sids":course_ids,
            "vcode": vcode
        }
        # try:
        #     res = self._S.post(self._urls['base_url']['http'] + self._action, data = post_data, headers=self.headers, timeout=5, proxies=proxies)
        # except requests.Timeout:
        #     res = self._S.post(self._urls['base_url']['https'] + self._action, data = post_data, headers=self.headers, proxies=proxies)
        try:
            res = self._S.post(self._urls['base_url']['http'] + f"/courseManage/saveCourse?{self._s}", data = post_data, headers=self.headers, timeout=5)
        except requests.Timeout:
            res = self._S.post(self._urls['base_url']['https'] + f"/courseManage/saveCourse?{self._s}", data = post_data, headers=self.headers)
        bs4obj = BeautifulSoup(res.content, 'html.parser')
        success = bs4obj.find("div", {"class": "mc-body"}).find("div", {"id":"messageBoxSuccess"}).find("label").decode_contents().replace('<br/>', '\n')
        if success:
            self._logger.info("\n" + success)

        error = bs4obj.find("div", {"class": "mc-body"}).find("div", {"id":"messageBoxError"}).find("label").decode_contents().replace('<br/>', '\n')
        if error:
            self._logger.error("\n" + error)

    def run(self):
        self.login()
        self._get_action()
        while self.course_ids:
            self._get_selected_course()
            course_todo = []
            for i in self.course_ids:
                if i not in self._selected_course['课程编码'].unique():
                    course_todo.append(i)
            self.course_ids = course_todo
            if self.course_ids:
                self._get_courses()
                self._select_course()
            else:
                return
            sleep(1)


import settings

if __name__ =='__main__':
    gradeObserver = CourseSelector(urls=settings.URLS)
    gradeObserver.run()