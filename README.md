# Tiktok_Downloader

## 介绍
- 只可下载抖音，国际版tiktok和其他平台都不行
- 只有命令行版本程式，未来也不打算做GUI图形化程式


## 安装教程

### 1.检查是否有python环境

- windows键 + R，输入`cmd`，回车确认打开命令行窗口，输入`python --version`查看python版本，若出现“Python 3.xx.x”字样说明电脑存在python环境，跳过步骤2执行步骤3

### 2.安装python环境

- 打开文件夹中python-3.11.4 x64.exe软体，勾选"Add Python to PATH"和"Install ...(reccommended)"，之后选择Customize installuion，全选所有复选框，执行下一步，取消勾选“Install for all users”，其他不变，选择安装路径（D盘E盘都可），安装即可

### 3.安装项目依赖库

- 在文件夹中的**导航栏**输入`cmd`（见REV1.gif动图操作），回车确认，首先升级pip安装管理工具：`python.exe -m pip install --upgrade pip`，回车确认
- 再输入`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`，最后的网址是阿里云镜像网站，如果电脑可以翻墙，可省去
- 安装完成后不要关闭窗口，接着第四步

### 4.最后一步

- 输入`clear`，回车确认，清除cmd窗口的冗余显示文字
- 输入`python TiktokVideo.py`，确认，大功告成，跟着cmd窗口做下去即可

## 说明

1.  后续本想加入多线程支持，但可能做不到，python水平还不行，程式第一版也是最后一版了
2.  config.ini配置文件可更改，利用 nodepad++或者visual studio code 打开即可，其次程序目前还有bug，下载的视频或者图集在video文件夹中，若程序出错，出错日志在video-log文件夹中，参照日志在TiktokVideo.py文件中也可以找到bug并改掉，可以的话希望将改动代码上传到本仓库内

## 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request


## 开源协议

- 采用BSD (3-Clause) 开源协议

## 其他说明

2023/7/8：最新的bug：在新开的chrome浏览器中，人机验证还未通过，就可以开始下载内容，可能是本地调试的时候多次重复登录抖音，cookie未清除，程式直接利用cookie，绕过人机验证程式，解决办法就是不解决，看着命令行窗口吃饭，建议还是把人机验证给过了，防止抖音后台限制

## 致谢

抖音不干人事的人机校验机制，利用selenium来获取cookie值，进而模拟访问，这些代码致谢知乎@QingTianGG

```python
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
 
s = Service(executable_path = 'Chrome/chromedriver.exe')
if os.path.exists('Chrome/chrome.exe'):
    browser = webdriver.Chrome(service=s)
else:
    browser = webdriver.Chrome()
browser.get(url)
WebDriverWait(browser, 30).until(EC.title_contains('抖音'))
header_add = ''
for cookie_dict in browser.get_cookies():
    header_add += cookie_dict['name']+'='+cookie_dict['value']+';' if cookie_dict['name'] != '' else cookie_dict['value']+';'
ini.header['cookie'] = header_add
```
