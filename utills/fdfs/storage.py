from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    '''fastdfs文件存储类'''
    def _open(self, name, mode='rb'):
        '''打开文件使用'''
        pass

    def _save(self, name, content):
        '''保存文件时使用'''
        #name:上传文件的名字
        #content:上传文件内容的File对象

        #创建一个fdfs_client对象
        client = Fdfs_client('./utills/fdfs/client.conf')

        #上传文件到fastdfs系统中
        res = client.upload_by_buffer(content.read())
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fastdfs系统失败')

        #获取返回的文件id
        filename = res.get('Remote file_id')

        return filename

    def exists(self, name):
        '''django判断文件名是否可用'''
        return False

    def url(self, name):
        '''返回访问文件的url路径'''
        return 'http://192.168.71.167:8888/'+name


