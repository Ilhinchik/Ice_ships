from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile


class MinioStorage:
    def __init__(self, endpoint, access_key, secret_key, secure, ):
        self._client = Minio(endpoint=endpoint,
                             access_key=access_key,
                             secret_key=secret_key,
                             secure=secure)

    def load_file(self, bucket_name: str, file_name: str, file: InMemoryUploadedFile):
        """
        Загрузка файла 'file' с именем 'file_name' в бакет 'bucket_name'
        """
        self._client.put_object(bucket_name, file_name, file, file.size)

    def delete_file(self, bucket_name: str, file_name: str):
        """
        Удаление файла с именем 'file_name' из бакета 'bucket_name'
        """
        self._client.remove_object(bucket_name, file_name)