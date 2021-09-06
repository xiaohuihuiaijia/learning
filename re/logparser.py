import datetime
import time
import random
from queue import Queue
import threading
import re
from pathlib import Path
from user_agents import parse

pattern = '(?P<remote>[\d\.]{7,}) - - \[(?P<datetime>[\w/: +-]+)\] "(?P<method>[A-Za-z]+) \
(?P<url>\S+) (?P<protocol>[\w/.]+)" (?P<status>\d+) (?P<length>\d+) "[^"]+" "(?P<useragent>.+)"'
regex = re.compile(pattern)

conversion = {
    'datetime':lambda timestr:datetime.datetime.strptime(timestr, '%d/%b/%Y:%H:%M:%S %z'),
    'status':int,
    'length':int,
    'useragent':lambda uastr: parse(uastr)
}

def extract(line:str):
    m = regex.match(line) # matcher None
    if m:
        return {k:conversion.get(k, lambda x:x)(v) for k,v in m.groupdict().items()}
    # else:
    #     #print() # log
    #     #raise Exception('Not match {}'.format(line))
    #     return None

def loadfile(filename:str, encoding='utf-8'):
    with open(str(filename), encoding=encoding) as f:
        for line in f:
            fields = extract(line)
            if fields:
                #print(fields) #  处理数据
                yield fields # 字典
            else:
                pass # 记录日志，记录这些解析失败的行 line


def load(*path, encoding='utf-8', exts='*.log', recursion=False):
    for x in path: # path tuple
        p = Path(x)
        if isinstance(exts, str):
            exts = [exts]
        else:
            exts = list(exts)
        if p.is_dir(): # 路径，目录
            for ext in exts:
                files = p.rglob(ext) if recursion else p.glob(ext)
                for file in files:
                    print(file, '++++++++++++++++++++++++++++++++++++++++')
                    yield from loadfile(str(file.absolute()), encoding=encoding)

        elif p.is_file():
            if '*' + p.suffix in exts:
                yield from loadfile(str(p.absolute()), encoding=encoding)

# def source(seconds=1):
#     while True:
#         yield {'datetime':datetime.datetime.now(), 'value':random.randint(1,10)}
#         time.sleep(seconds)

def window(q:Queue, handler, width:int, interval:int):
    start = datetime.datetime.strptime('20170101 000000 +0800', '%Y%m%d %H%M%S %z')
    current = datetime.datetime.strptime('20170101 010000 +0800', '%Y%m%d %H%M%S %z')

    buffer = []
    delta = datetime.timedelta(seconds=width - interval)

    while True:
        #data = next(iterator) # 拿一个数据
        data = q.get() # 阻塞等数据
        if data: # dict datetime, value
            buffer.append(data)
            current = data['datetime']

        if (current - start).total_seconds() >= interval:
            #print(buffer)
            ret = handler(buffer)
            print('{}'.format(ret)) # 去数据库存储
            #print('-' * 30)

            if delta.total_seconds() != 0:
                buffer = [x for x in buffer if x['datetime'] > current - delta]
            else:
                buffer = []
            print('=======================')
            start = current

def handler(iterable): #  平均数
    return sum(map(lambda x:x['value'], iterable)) / len(iterable)

def donothing_handler(iterable):
    return iterable

# 状态码分析
def status_handler(iterable): #[dict]
    status = {}
    for item in iterable:
        key = item['status']
        status[key] = status.get(key, 0) + 1

    #total = sum(status.values())
    total = len(iterable)
    return {k:v/total for k,v in status.items()}


# ua分析
allbrowsers = {}
def ua_handler(iterable): # [dict]
    browsers = {}
    for item in iterable:
        ua = item['useragent']

        key = (ua.browser.family, ua.browser.version_string)
        browsers[key] = browsers.get(key, 0) + 1
        allbrowsers[key] = allbrowsers.get(key, 0) + 1
    print('-' * 30)
    print(sorted(allbrowsers.items(), key=lambda x:x[1], reverse=True)[:10])
    print('-' * 30)
    return browsers


def dispatcher(src):
    queues = []
    handlers = []

    def reg(handler, width, interval):
        q = Queue()
        queues.append(q)

        t = threading.Thread(target=window, args=(q, handler, width, interval))
        handlers.append(t)

        #window(q, handler, width, interval)


    def run():
        for t in handlers:
            t.start() # target对应的函数的调用

        for item in src: # 数据的复制，一对多，分发
            for q in queues:
                q.put(item)

    return reg, run


if __name__ == '__main__':
    import sys
    #path = sys.argv[1]
    path = '.'
    s = load(path)

    reg, run = dispatcher(s)

    #reg(handler, 10, 5)
    reg(status_handler, 10, 5)
    reg(ua_handler, 5, 5)

    run()


