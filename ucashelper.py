# @Author  : GentleCP
# @Email   : 574881148@qq.com
# @File    : ucashelper.py
# @Item    : PyCharm
# @Time    : 2019/11/28/028 13:58
# @WebSite : https://www.gentlecp.com


from select import select
import click
import sys
import os

from handler import ui
from core.wifi import AccHacker
from core.assess import Assesser
from core.grade import GradeObserver
from core.download import Downloader
from core.wifi import WifiLoginer
from core.course import CourseSelector

import settings

ROOT_PATH = os.path.dirname(__file__)
sys.path.append(ROOT_PATH)


@click.group()
def start():
    """UCASHelper is a useful tool for UCASer, following are the arguments that you could choose"""

@click.command(name='config',help='Set your user info and download path(not support on windows)')
def config():
    if not sys.platform.startswith('win'):
        from handler.configer import UCASHelperConfigApp
        UCASHelperConfigApp().run()
    else:
        print('config not support on windows. please set config in conf/user_config.ini by yourself.')


@click.command(name='ui',help='Get UI interface of UCASHelper')
def UI():
    ui.main(record_path=settings.RECORD_PATH)


@click.command(name='down',help='Download resources from sep website')
def download_source():
    downloader = Downloader(
        urls=settings.URLS,
        user_config_path=settings.USER_CONFIG_PATH,
        filter_list=settings.FILTER_LIST)
    downloader.run()


@click.command(name='assess',help='Auto assess courses and teachers')
def auto_assess():
    assesser = Assesser(
        urls=settings.URLS,
        user_config_path=settings.USER_CONFIG_PATH,
        assess_msgs=settings.ASSESS_MSG)
    assesser.run()


@click.command(name='grade',help='Query your grades')
def query_grades():
    gradeObserver = GradeObserver(
        urls=settings.URLS,
        user_config_path=settings.USER_CONFIG_PATH) # todo, delete
    gradeObserver.run()


@click.command(name='hack',help='Hack wifi accounts')
def hack_accounts():
    hacker = AccHacker(data_path='data/data.txt', password_path='data/password.txt')
    hacker.run()

@click.command(name='login',help='Login campus network')
def login_wifi():
    wifiLoginer = WifiLoginer(accounts_path=settings.ACCOUNTS_PATH)
    wifiLoginer.login()


@click.command(name='logout',help='Logout campus network')
def logout_wifi():
    wifiLoginer = WifiLoginer(accounts_path=settings.ACCOUNTS_PATH)
    wifiLoginer.logout()

@click.command(name='course', help='Select course')
def select_course():
    course_selector = CourseSelector(urls=settings.URLS, course_config_path='config.json')
    course_selector.run()

if __name__ == '__main__':
    commands = [UI,auto_assess,download_source,query_grades,hack_accounts,login_wifi,logout_wifi, config, select_course]
    for command in commands:
        start.add_command(command)
    start()
