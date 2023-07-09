import json
import os
import platform
import sys
import time
import traceback
import urllib
import threading
from urllib import parse
from urllib.parse import urlparse

import requests
import configparser
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from retrying import retry

class BaseError(ValueError):
    pass

class NoneDataError(BaseError):
    pass

class VideoInit:
    # 初始化游标
    max_cursor = 0
    # 初始化视频数量
    video_count = 0
    # 成功下载的视频数量
    success = 0
    # 失败下载的视频数量
    error = 0
    # 数据加载失败的次数
    noneDataError = 0
    # 数据加载失败的次数
    stopFlag = 0

    # 初始化类型
    video = 0
    image = 0
    url = ''
    path = ''
    fileSize = 0
    downloaded = 0

    # 浏览器对象
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    driver = None
    # driver = webdriver.Chrome(executable_path='Chrome/chromedriver.exe', desired_capabilities=caps)

    # 文件、图集文件夹命名变量
    authorName = 'none'
    desc = 'none'
    id = ''
    createTime = ''
    resolutionWidth = 1
    resolutionHeight = 1
    basename = 'none'
    ratio = 'none'
    dateTimeFormat = 'yyyyMMddHHmmss'
    descLength = 50
    videoName = '%authorName_%desc_%id'
    imageName = '%basename'
    imageAlbumName = '%authorName_%desc_%id'

    # 下载配置
    quickDownload = 1
    forceBestQuality = 0
    initURL = 'none'

    # 全局请求头
    header = {
        'authority': 'www.douyin.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="108", "Chromium";v="108", "Not=A?Brand";v="8"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    }

    # 初始化文件夹
    def __init__(self):
        # 判断文件夹是否存在
        if not os.path.exists('video'):
            os.mkdir('video')
        if not os.path.exists('video/主页'):
            os.mkdir('video/主页')
        if not os.path.exists('video/喜欢'):
            os.mkdir('video/喜欢')
        if not os.path.exists('video/合集'):
            os.mkdir('video/合集')
        if not os.path.exists('video/收藏'):
            os.mkdir('video/收藏')

        if os.path.exists('config.ini'):
            # 读取配置文件的命名规则
            cf = configparser.RawConfigParser()
            cf.read('config.ini', encoding='utf-8')
            self.dateTimeFormat = cf.get('NameRule', 'dateTimeFormat')
            self.descLength = int(cf.get('NameRule', 'descLength'))
            self.videoName = cf.get('NameRule', 'videoName')
            self.imageName = cf.get('NameRule', 'imageName')
            self.imageAlbumName = cf.get('NameRule', 'imageAlbumName')
            self.quickDownload = int(cf.get('DownloadSettings', 'quickDownload'))
            self.forceBestQuality = int(cf.get('DownloadSettings', 'forceBestQuality'))
            self.initURL = cf.get('DownloadSettings', 'initURL')
            self.header['cookie'] = cf.get('DownloadSettings', 'cookie')

    # 链接重定向
    def redirect(self, url):
        response = requests.get(url, headers=self.header)
        return response.url

    # 获取sec_uid
    @staticmethod
    def get_sec_uid(url):
        return url.split('user/')[1].split('?')[0]

    # 获取mix_id
    @staticmethod
    def get_mix_id(url):
        return url.split('detail/')[1].split('/')[0]

    # 获取用户信息
    def get_user_info(self, sec_uid):
        url = f'https://www.douyin.com/web/api/v2/user/info/?sec_uid={sec_uid}'
        response = requests.get(url, headers=self.header)
        return response.json()['user_info']['nickname']

    # 特殊字符处理
    @staticmethod
    def replace(title):
        title = title.replace('\\', '')
        title = title.replace('/', '')
        title = title.replace(':', '')
        title = title.replace('*', '')
        title = title.replace('?', '')
        title = title.replace('"', '')
        title = title.replace('<', '')
        title = title.replace('>', '')
        title = title.replace('|', '')
        title = title.replace(' ', '')
        title = title.replace('.', '')
        title = title.replace('\n', '')
        return title

    # 判断是视频还是图集
    @staticmethod
    def is_video(data):
        try:
            if 'download_addr' in data['video'] or data.get('images', "") is None:
                return True
        except KeyError:
            return False

    # 结束输出
    def end(self):
        print('=====================================================')
        print('* 全部作品下载完成')
        print(f'* 作品总数：{self.video_count}')
        print(f'* 成功下载：{self.success}')
        print(f'* 失败下载：{self.error}')
        print('=====================================================')
        # 数据重置
        self.max_cursor = 0
        self.video_count = 0
        self.success = 0
        self.error = 0
        self.video = 0
        self.image = 0
        # self.url = ''
        # self.path = ''
        self.driver.get('about:blank')


# 初始化浏览器
def GetWebdriver(ini):
    if ini.driver is None:
        print('init web browser\n')
        ini.driver = webdriver.Chrome(executable_path='Chrome/chromedriver.exe', desired_capabilities=ini.caps)
        print('init web browser competed\n')
        if len(ini.header['cookie']):
            print('检测cookie值并尝试缓存登录....')
            ini.driver.get('https://www.douyin.com/')
            ini.driver.delete_all_cookies()
            cookies_list = json.loads(ini.header['cookie'])
            for cookie in cookies_list:
                ini.driver.add_cookie(cookie)
            ini.driver.get('https://www.douyin.com/user/self')
            time.sleep(5)
        else:
            ini.driver.get('https://www.douyin.com/user/self')
            time.sleep(5)
            print('请在60s内登录抖音（WebDriverWait函数传参只有60秒，防止登录过期）')
            WebDriverWait(ini.driver, 60).until(ec.title_contains('- 抖音'))
        print('等待人机验证完成1')
        ini.driver.get(ini.initURL)
        time.sleep(5)
        print('等待人机验证完成2')
        WebDriverWait(ini.driver, 60).until(ec.title_contains('- 抖音'))
        GetCookies(ini)
        ini.driver.get('about:blank')
        print('浏览器准备完毕')


# 抓取cookies
def GetCookies(ini):
    print('正在更新cookie')

    ini.header['cookie'] = json.dumps(ini.driver.get_cookies())

    UpdateINI(ini)

    resCookie = ''
    for cookie_dict in ini.driver.get_cookies():
        resCookie += cookie_dict['name'] + '=' + cookie_dict['value'] + ';' if cookie_dict['name'] != '' else \
            cookie_dict['value'] + ';'
    ini.header['cookie'] = resCookie


# 更新配置文件
def UpdateINI(ini):
    # 原始配置文件
    with open('config.ini', encoding="utf-8") as f:
        oriLines = f.readlines()
        f.close()

    # 更新配置
    cf = configparser.RawConfigParser()
    cf.read('config.ini', encoding='utf-8')
    cf.set('DownloadSettings', 'cookie', ini.header['cookie'])
    o = open('config.ini', 'w')
    cf.write(o)
    o.close()

    # 更新后的配置文件
    with open('config.ini', encoding="utf-8") as f:
        updatedLines = f.readlines()
        f.close()

    # 生成配置文件，补充注释
    lineId = 0
    for i in range(len(oriLines)):
        if not oriLines[i].startswith('#'):
            oriLines[i]=updatedLines[lineId]
            lineId += 1

    # 重写配置文件
    with open('config.ini', encoding="utf-8", mode = "w+") as f:
        f.writelines(oriLines)
        f.close()


# 抓取首页script[id="RENDER_DATA"]数据
def GetFrontPageData(ini):
    print('处理首页数据中....')
    soup = BeautifulSoup(ini.driver.page_source, 'html.parser')
    response = soup.select('script[id="RENDER_DATA"]')[0].text
    response = urllib.parse.unquote(response)
    return json.loads(response)


# 滚动浏览器页面加载视频
def ScrollWebdrive(ini):
    while True:
        if not ini.stopFlag:
            ini.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            ini.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(5)
        else:
            return


# 获取浏览器里相应URL的数据包并解析下载
def DownloadByURL(ini, urlcontent):
    print('开始下载，浏览器不要最小化！')
    while True:
        logs_raw = ini.driver.get_log("performance")
        logs = [json.loads(lr["message"])["message"] for lr in logs_raw]
        logs = [log for log in logs if (
                log["method"] == "Network.responseReceived" and urlcontent in log["params"]["response"]["url"])]

        # 多次获取不到数据则抛异常，重新加载页面
        if ini.error > 5:
            ini.end()
            ini.quickDownload = 0
            print('连续6次未获取到数据，重新加载')
            raise NoneDataError('连续6次未获取到数据')

        if len(logs):
            print('获取到' + str(len(logs)) + '组数据，解析下载中')

            for log in logs:
                try:
                    request_id = log["params"]["requestId"]
                    response = ini.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    data = response["body"]
                    aweme_list = json.loads(data)
                    # 获取是否有后续资源标记
                    has_more = aweme_list['has_more']
                    # 获取作品列表
                    aweme_list = aweme_list['aweme_list']
                    DownloadAweme(ini, aweme_list)
                    # 快速下载
                    if ini.quickDownload:
                        if ini.downloaded:
                            print('最新视频已下载，重复内容pass')
                            ini.end()
                            return
                    # 判断作品是否下载完成
                    if not has_more:
                        ini.end()
                        return
                except Exception as e:
                    print(f'本组数据解析失败，自动跳过:{e}')
                    continue
            print('新作品下载完成，继续滚动加载作品，检测到新作品后开始下载')
        else:
            print('未获取到数据，重新获取中')
            ini.error += 1

        ini.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)


#下载作品集
def DownloadAweme(ini, aweme_list):
    # 读取作品
    for aweme in aweme_list:
        # 更新作品数量
        ini.video_count += 1
        # 作品标题
        title = 'None'
        # 初始化作品大小
        ini.fileSize = 0
        try:
            # 提取作品参数
            ini.authorName = ini.replace(aweme["author"]["nickname"])
            ini.desc = ini.replace(aweme["desc"])[:ini.descLength]
            ini.id = aweme["aweme_id"]
            ini.createTime = time.strftime(ini.dateTimeFormat, time.localtime(aweme['create_time']))

            # 判断是视频还是图集
            if ini.is_video(aweme):
                # 强制筛选最高视频清晰度
                if ini.forceBestQuality and len(aweme['video']['bit_rate']):
                    videoBitRateList = aweme['video']['bit_rate']
                    maxHeight = max(videoBitRateList, key=lambda x: x['play_addr']['height'])['play_addr']['height']
                    videoList = [i for i in videoBitRateList if i['play_addr']['height'] == maxHeight]
                    maxBitRate = max(videoList, key=lambda x: x['bit_rate'])['bit_rate']
                    videoList = [i for i in videoList if i['bit_rate'] == maxBitRate]

                    # 构造视频链接
                    video_url = videoList[0]['play_addr']['url_list'][0]
                    # 进一步提取视频参数
                    ini.resolutionWidth = videoList[0]['play_addr']['width']
                    ini.resolutionHeight = videoList[0]['play_addr']['height']
                    ini.ratio = videoList[0]['gear_name']
                else:
                    # 视频链接
                    video_url = aweme['video']['play_addr']['url_list'][0]
                    # 进一步提取视频参数
                    ini.resolutionWidth = aweme['video']['width']
                    ini.resolutionHeight = aweme['video']['height']
                    ini.ratio = aweme['video']['ratio']

                # 构造视频文件名
                title = ini.replace(ini.videoName.replace('%authorName', ini.authorName).replace(
                    '%desc', ini.desc).replace('%id', ini.id).replace('%createTime', ini.createTime).replace(
                    '%resolutionWidth', str(ini.resolutionWidth)).replace(
                    '%resolutionHeight', str(ini.resolutionHeight)).replace('%ratio', ini.ratio))
                # 下载视频并判断有没有被反爬
                print(f'正在下载：【{ini.video_count}】' + title)
                if 1000 > DownloadVideo(ini, video_url, title) > 1:
                    raise Exception(f'{title}视频数据异常，文件小于1KB。')
            else:
                # 构造图集文件夹名
                imageAlbumTitle = ini.replace(ini.imageAlbumName.replace('%authorName', ini.authorName).replace(
                    '%desc', ini.desc).replace('%id', ini.id).replace('%createTime', ini.createTime))
                # 下载图集
                print(f'正在下载：【{ini.video_count}】' + imageAlbumTitle + '图集')
                # 创建文件夹
                if not os.path.exists(ini.path + '/' + imageAlbumTitle):
                    os.makedirs(ini.path + '/' + imageAlbumTitle)
                # 获取图片列表
                images_list = aweme["images"]
                for image in images_list:
                    # 筛选jpg的图片地址
                    image_url = [i for i in image["url_list"] if ".jpeg" in i][0]
                    # 进一步提取图片参数
                    ini.resolutionWidth = image['width']
                    ini.resolutionHeight = image['height']
                    ini.basename = ini.replace(os.path.basename((urlparse(image_url)).path).split('.')[0])
                    # 构造图片文件名
                    title = ini.imageName.replace('%authorName', ini.authorName).replace(
                        '%desc', ini.desc).replace('%id', ini.id).replace(
                        '%createTime', ini.createTime).replace('%resolutionWidth', str(ini.resolutionWidth)).replace(
                        '%resolutionHeight', str(ini.resolutionHeight)).replace('%basename', ini.basename) + ".jpeg"
                    # 下载图片并判断有没有被反爬
                    if 1000 > DownloadImageOrMusic(ini, image_url, imageAlbumTitle, title) > 1:
                        raise Exception(f'{title}图片数据异常，文件小于1KB。')
            # 成功下载数量
            ini.success += 1
        except Exception as e:
            # 异常太多则终止下载
            if ini.error < 6:
                log_name = ErrorLog(e)
                ini.error += 1
                print('下载失败，自动跳过: ' + title)
                continue
            else:
                raise Exception('异常太多，终止下载！')


# 视频下载
@retry(stop_max_attempt_number=3, wait_incrementing_start=5000, wait_incrementing_increment=10000)
def DownloadVideo(ini, video, title):
    fileSize = 0
    ini.downloaded = 0

    # 已经下载的跳过
    if os.path.exists(f'{ini.path}/{title}.mp4'):
        print(f'{title} 文件已经存在，跳过')
        ini.downloaded = 1
        return fileSize
    # 请求视频
    response = requests.get(video, headers=ini.header)
    fileSize = len(response.content)
    # 写入视频
    with open(f'{ini.path}/{title}.mp4', 'wb') as f:
        f.write(response.content)
    response.close()
    return fileSize


# 图片和图片下载
@retry(stop_max_attempt_number=3, wait_incrementing_start=5000, wait_incrementing_increment=10000)
def DownloadImageOrMusic(ini, image_url, imageAlbumTitle, title):
    fileSize = 0
    ini.downloaded = 0

    # 已经下载的跳过
    if os.path.exists(f'{ini.path}/{imageAlbumTitle}/{title}'):
        print(f'{title} 文件已经存在，跳过')
        ini.downloaded = 1
        return fileSize
    # 请求文件
    print('正在下载：' + title + '文件')
    response = requests.get(image_url, headers=ini.header)
    fileSize = len(response.content)
    # 写入文件
    with open(f'{ini.path}/{imageAlbumTitle}/{title}', 'wb') as f:
        f.write(response.content)
    response.close()
    return fileSize


# 写入日志
def ErrorLog(error):
    if not os.path.exists('video/Log'):
        os.mkdir('video/Log')
    # 获取当前时间
    log_name = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    errorContent = f'====================={date}=====================\n' \
                   f'{error}\n' \
                   f'=============================================================\n'
    # 写入错误日志
    with open(f'video/Log/{log_name}.log', 'a', encoding='utf-8') as f:
        f.write(errorContent)
    return log_name


# 程序主入口
def Start():
    try:
        ini = VideoInit() #类初始化
        while True:
            print('=====================================================')
            print('1.下载用户主页全部作品\n2.下载用户喜欢作品\n3.下载视频播放合集\n4.下载自己的收藏作品\n5.退出程序\n')
            print('=====================================================')
            choice = input('请选择(1 ~ 5):')
            if choice == '1':
                try:
                    if ini.noneDataError < 2:
                        Home(ini)
                    else:
                        raise NoneDataError('加载异常，重试3次都失败，退出程序')
                except NoneDataError as e:
                    ini.noneDataError += 1
                    Home(ini, ini.url)
                # 正常下载完成清理标记数据
                ini.noneDataError = 0
            elif choice == '2':
                try:
                    if ini.noneDataError < 2:
                        Like(ini)
                    else:
                        raise NoneDataError('数据加载异常，重试3次失败，停止下载')
                except NoneDataError as e:
                    ini.noneDataError += 1
                    Like(ini, ini.url)
                # 正常下载完成清理标记数据
                ini.noneDataError = 0
            elif choice == '3':
                Collection(ini)
            elif choice == '4':
                try:
                    if ini.noneDataError < 2:
                        Favorite(ini)
                    else:
                        raise NoneDataError('数据加载异常，重试3次失败，停止下载')
                except NoneDataError as e:
                    ini.noneDataError += 1
                    Favorite(ini, ini.url)
                # 正常下载完成清理标记数据
                ini.noneDataError = 0
            elif choice == '5':
                ini.driver.quit()
                sys.exit()
            else:
                print('输入错误，请重新输入！')
    except Exception as e:
        log_name = ErrorLog(e)
        log_name = ErrorLog(ini.url)
        log_name = ErrorLog(str(platform.platform()))
        log_name = ErrorLog(traceback.format_exc())
        input(f'程序错误！错误日志保存在 video/Log 文件夹，Ctrl + C 退出')


# 下载主页作品
def Home(ini, *url):
    ini.url = url[0] if len(url) else input('请输入用户主页链接：')

    # 打开页面，通过人机认证
    print('等待人机验证完成')
    GetWebdriver(ini)
    ini.driver.get(ini.url)
    try:
        WebDriverWait(ini.driver, 30).until(ec.title_contains('抖音'))
    except:
        print('页面加载异常')
        ini.end()
        return
    time.sleep(5)

    # 获取cookies
    GetCookies(ini)

    # 处理首页数据
    data = GetFrontPageData(ini)

    # 数据节点的这个数字会变，所以直接查
    key = [a for a in data if 'uid' in data[a]][0]

    # 获取用户名称
    ini.authorName = ini.replace(data[key]["user"]["user"]["nickname"])

    # 创建文件夹
    ini.path = f'video/主页/{ini.authorName}'
    if not os.path.exists(ini.path):
        os.makedirs(ini.path)

    print('开始下载，浏览器不要最小化！')


    # 首页加载有时候不加载视频数据，直接跳过
    if data[key].get('post', "") is not None:
        # 获取作品列表
        aweme_list = data[key]["post"]["data"]
        # 获取是否有后续资源标记
        hasMore = data[key]["post"]["hasMore"] if 'hasMore' in data[key]["post"] else 0
        # 读取作品
        for aweme in aweme_list:
            # 更新作品数量
            ini.video_count += 1
            # 作品标题
            title = 'None'
            # 初始化作品大小
            ini.fileSize = 0
            try:
                # 提取作品参数
                ini.desc = ini.replace(aweme["desc"])[:ini.descLength]
                ini.id = aweme["awemeId"]
                ini.createTime = time.strftime(ini.dateTimeFormat, time.localtime(aweme['createTime']))

                # 判断是视频还是图集
                if aweme['awemeType'] == 0 or not len(aweme['images']):
                    # 强制筛选最高视频清晰度
                    if ini.forceBestQuality and len(aweme['video']['bitRateList']):
                        videoBitRateList = aweme['video']['bitRateList']
                        maxHeight = max(videoBitRateList, key=lambda x: x['height'])['height']
                        videoList = [i for i in videoBitRateList if i['height'] == maxHeight]
                        maxBitRate = max(videoList, key=lambda x: x['bitRate'])['bitRate']
                        videoList = [i for i in videoList if i['bitRate'] == maxBitRate]

                        # 构造视频链接
                        video_url = 'https:' + videoList[0]['playAddr'][0]['src']
                        # 进一步提取视频参数
                        ini.resolutionWidth = videoList[0]['width']
                        ini.resolutionHeight = videoList[0]['height']
                        ini.ratio = videoList[0]['gearName']
                    else:
                        # 构造视频链接
                        video_url = 'https:' + aweme['video']['playAddr'][0]['src']
                        # 进一步提取视频参数
                        ini.resolutionWidth = aweme['video']['width']
                        ini.resolutionHeight = aweme['video']['height']
                        ini.ratio = aweme['video']['ratio']

                    # 构造视频文件名
                    title = ini.replace(
                        ini.videoName.replace('%authorName', ini.authorName).replace('%desc', ini.desc).replace(
                            '%id', ini.id).replace('%createTime', ini.createTime).replace(
                            '%resolutionWidth', str(ini.resolutionWidth)).replace(
                            '%resolutionHeight', str(ini.resolutionHeight)).replace('%ratio', ini.ratio))
                    # 下载视频并判断有没有被反爬
                    print(f'正在下载：【{ini.video_count}】' + title)
                    if 1000 > DownloadVideo(ini, video_url, title) > 1:
                        raise Exception(f'{title}视频数据异常，文件小于1KB。')
                else:
                    # 构造图集文件夹名
                    imageAlbumTitle = ini.replace(
                        ini.imageAlbumName.replace('%authorName', ini.authorName).replace('%desc', ini.desc).replace(
                            '%id', ini.id).replace('%createTime', ini.createTime))
                    # 下载图集
                    print(f'正在下载：【{ini.video_count}】' + imageAlbumTitle + '图集')
                    # 创建图集文件夹
                    if not os.path.exists(ini.path + '/' + imageAlbumTitle):
                        os.makedirs(ini.path + '/' + imageAlbumTitle)
                    # 获取图片列表
                    images_list = aweme["images"]
                    for image in images_list:
                        # 筛选jpg的图片地址
                        image_url = [i for i in image["urlList"] if ".jpeg" in i][0]
                        # 进一步提取图片参数
                        ini.resolutionWidth = image['width']
                        ini.resolutionHeight = image['height']
                        ini.basename = ini.replace(os.path.basename((urlparse(image_url)).path).split('.')[0])
                        # 构造图片文件名
                        title = ini.replace(
                            ini.imageName.replace('%authorName', ini.authorName).replace('%desc', ini.desc).replace(
                                '%id', ini.id).replace('%createTime', ini.createTime).replace(
                                '%resolutionWidth', str(ini.resolutionWidth)).replace(
                                '%resolutionHeight', str(ini.resolutionHeight)).replace('%basename', ini.basename)) + ".jpeg"
                        # 下载图片并判断有没有被反爬
                        if 1000 > DownloadImageOrMusic(ini, image_url, imageAlbumTitle, title) > 1:
                            raise Exception(f'{title}图片数据异常，文件小于1KB。')
                # 成功下载数量
                ini.success += 1
            except Exception as e:
                # 异常太多则终止下载
                if ini.error < 6:
                    log_name = ErrorLog(e)
                    ini.error += 1
                    print('下载失败，自动跳过: ' + title)
                    continue
                else:
                    raise Exception('异常太多，终止下载！')
        # 快速下载，默认开启
        if ini.quickDownload:
            if ini.downloaded:
                print('最新视频已下载，重复内容pass')
                ini.end()
                return
        # 判断作品是否下载完成
        if not hasMore:
            ini.end()
            return

        print('首页作品下载完成，将自动滚动屏幕，加载作品，程序检测到新作品后会开始下载')
        ini.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

    # 首页数据搞定，循环下载后续数据
    DownloadByURL(ini, '/aweme/v1/web/aweme/post/')


# 下载喜欢作品
def Like(ini, *url):
    ini.url = url[0] if len(url) else input('请输入用户主页链接：')

    # 打开页面，通过人机认证
    print('等待人机验证完成')
    GetWebdriver(ini)
    ini.driver.get(ini.url)
    try:
        WebDriverWait(ini.driver, 30).until(ec.title_contains('抖音'))
    except:
        print('页面加载异常')
        ini.end()
        return
    time.sleep(5)

    # 获取cookies
    GetCookies(ini)

    # 处理首页数据
    data = GetFrontPageData(ini)

    # 数据节点的这个数字会变，所以直接查
    key = [a for a in data if 'uid' in data[a]][0]

    # 获取用户名称
    ini.authorName = ini.replace(data[key]["user"]["user"]["nickname"])

    # 创建文件夹
    ini.path = f'video/喜欢/{ini.authorName}'
    if not os.path.exists(ini.path):
        os.makedirs(ini.path)

    print('跳转喜欢列表页面')
    ini.driver.get(ini.driver.current_url + '?showTab=like')
    time.sleep(5)

    # 下载后续加载的作品
    DownloadByURL(ini, '/aweme/v1/web/aweme/favorite/')


# 下载合集作品
def Collection(ini, *url):
    ini.url = url[0] if len(url) else input('请输入视频合集链接：')

    # 打开页面，抓取cookie
    GetWebdriver(ini)
    ini.driver.get(ini.url)
    WebDriverWait(ini.driver, 30).until(ec.title_contains('抖音'))
    time.sleep(5)

    # 获取cookies
    GetCookies(ini)

    # 处理首页数据
    data = GetFrontPageData(ini)

    # 获取合集ID和用户昵称、合集ID、合集名称
    # 数据节点的这个数字会变，所以直接查
    key = [a for a in data if 'aweme' in data[a]][0]
    ini.authorName = ini.replace(data[key]["aweme"]['detail']["authorInfo"]["nickname"])
    mix_id = data[key]["aweme"]['detail']["mixInfo"]["mixId"]
    collection_name = ini.replace(data[key]["aweme"]['detail']["mixInfo"]["mixName"])

    # 下载路径
    ini.path = f'video/合集/{ini.authorName}/{collection_name}'
    # 创建文件夹
    if not os.path.exists(f'video/合集/{ini.replace(ini.authorName)}'):
        os.makedirs(f'video/合集/{ini.replace(ini.authorName)}')
    if not os.path.exists(ini.path):
        os.makedirs(ini.path)
    print('开始下载......')
    # 开始执行任务
    while True:
        url = f'https://www.douyin.com/web/api/mix/item/list/?reflow_source=reflow_page&mix_id={mix_id}&count=10&cursor={ini.max_cursor}'
        data = requests.get(url, headers=ini.header).json()
        # 获取作品列表数据
        aweme_list = data['aweme_list']
        DownloadAweme(ini, aweme_list)
        # 快速下载
        if ini.quickDownload:
            if ini.downloaded:
                print('最新视频已下载，重复内容pass')
                ini.end()
                return
        # 判断是否还有下一页
        if data['has_more']:
            # 更新游标
            ini.max_cursor = data['cursor']
        else:
            ini.end()
            return


# 下载收藏作品
def Favorite(ini):
    ini.url = 'https://www.douyin.com/'

    # 打开页面，抓取cookie
    GetWebdriver(ini)
    ini.driver.get(ini.url)
    WebDriverWait(ini.driver, 30).until(ec.title_contains('抖音'))

    # 获取cookies
    GetCookies(ini)

    # 处理首页数据
    data = GetFrontPageData(ini)

    # 获取用户数据
    ini.authorName = ini.replace(data['app']['user']['info']['nickname'])
    secUid = data['app']['user']['info']['secUid']

    # 构造收藏页面链接
    url = 'https://www.douyin.com/user/' + secUid + '?showTab=favorite_collection'
    ini.driver.get(url)
    time.sleep(5)

    # 下载路径
    ini.path = f'video/收藏/{ini.authorName}'
    # 创建文件夹
    if not os.path.exists(ini.path):
        os.makedirs(ini.path)

    # 下载后续加载的作品
    DownloadByURL(ini, '/aweme/v1/web/aweme/listcollection/')

if __name__ == '__main__':
    Start()
