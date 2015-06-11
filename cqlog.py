# -*- coding: utf-8 -*-

"""基于共享队列，支持在多线程/进程并发的环境下对同一个文件进行操作的日志模块"""

__version__  = '0.3'
__author__ = 'yi'
__all__ = [
    'init_log',
    'default_log_config',
]

import os
import sys
import multiprocessing
import logging
import logging.config

def init_log(concurrent=True, dict_config=None):
    """初始化log"""
    
    # 没有提供log配置就使用默认的
    if not dict_config:
        dict_config = default_log_config()
    
    if concurrent:
        log_queue = multiprocessing.Queue(-1)
        listener = multiprocessing.Process(target=queue_listener, args=(log_queue, dict_config))
        listener.start()
    
        return CQLog(log_queue)
    else:
        configure_log(dict_config)
        
        return logging.getLogger()

def default_log_config(fileName=None, maxBytes=10 * 1024 * 1024, backupCount=10, consoleLevel='DEBUG', fileLevel='INFO'):
    """log默认配置"""
    
    if not fileName:
        basename = os.path.basename(sys.argv[0])
        if basename:
            fileName = basename.split('.')[0] + '.log'
        else:
            fileName = 'cqlog.log'
    
    dict_config = {
        'version': 1,
        'formatters': {
            'detailed': {
                'class': 'logging.Formatter',
                'format': '%(levelname)s %(asctime)s  %(message)s\n',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'detailed',
                'level': consoleLevel,
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'level': fileLevel,
                'filename': fileName,
                'maxBytes': maxBytes,
                'backupCount': backupCount,
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
        },
    }
    
    return dict_config
    
def queue_listener(log_queue, dict_config):
    """log queue监听进程"""
    
    configure_log(dict_config)
    while True:
        record = log_queue.get(block=True)
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)
        
def configure_log(dict_config):
    #创建log目录
    dir = os.path.dirname(dict_config['handlers']['file']['filename'])
    if dir and not os.path.exists(dir):
        os.makedirs(dir)
        
    logging.config.dictConfig(dict_config)

class CQLog:
    """模拟logger对象的方法"""
    
    def __init__(self, log_queue, name=None):
        self.name = name
        self.log_queue = log_queue
        self.__virtual_methods = ('debug', 'info', 'warning', 'error', 'critical') # 虚拟的方法，统一处理
        
    def new_log(self, name=None):
        return CQLog(self.log_queue, name)
        
    def __getattr__(self, attr):
        """拦截对不存在的属性和方法的访问"""
    
        # 过滤对私有属性和方法的访问
        if attr.startswith('__'):
            raise AttributeError(attr)
        else:
            if attr in self.__virtual_methods:
                name = self.name
                level = {'debug':logging.DEBUG, 'info':logging.INFO, 'warning':logging.WARNING, 'error':logging.ERROR, 'critical':logging.CRITICAL}[attr]
                def caller(msg):
                    record = logging.LogRecord(name, level, None, None, msg, None, None, None)
                    self.log_queue.put_nowait(record)
                return caller
            else:
                raise AttributeError(attr)

def testfunc(log):
    import time
    import threading
    
    while True:
        log.debug(multiprocessing.current_process().name + ', ' + threading.current_thread().name + ', Debug')
        log.info(multiprocessing.current_process().name + ', ' + threading.current_thread().name + ', Info')
        log.warning(multiprocessing.current_process().name + ', ' + threading.current_thread().name + ', Warning')
        log.error(multiprocessing.current_process().name + ', ' + threading.current_thread().name + ', Error')
        log.critical(multiprocessing.current_process().name + ', ' + threading.current_thread().name + ', Critical')
        time.sleep(0.1)
    
if __name__ == '__main__':
    # Example, concurrent
    log = init_log()
    
    for i in range(10):
        #import threading
        #threading.Thread(target=testfunc, args=(log,)).start()
        multiprocessing.Process(target=testfunc, args=(log,)).start()
    
    # Example, not concurrent
    #log = init_log(False)
    #testfunc(log)