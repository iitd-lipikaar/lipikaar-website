import redis

class QueueManager:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Upload cancelling
    @classmethod
    def cancel_upload(cls, upload_id):
        cls.mark_upload_as_processed(upload_id)
        cls.redis_client.sadd('cancelled_queued_uploads', upload_id)
    
    @classmethod
    def check_if_upload_is_cancelled(cls, upload_id):
        return cls.redis_client.sismember('cancelled_queued_uploads', upload_id)

    @classmethod
    def remove_cancelled_upload(cls, upload_id):
        cls.redis_client.srem('cancelled_queued_uploads', upload_id)

    @classmethod
    def clear_cancelled_uploads(cls):
        cls.redis_client.delete('cancelled_queued_uploads')

    # Upload processing
    @classmethod
    def check_if_upload_is_being_processed(cls, upload_id):
        return cls.redis_client.hexists('upload_processing_statuses', upload_id)

    @classmethod
    def update_upload_processing_status(cls, upload_id, processing_status):
        cls.redis_client.hset('upload_processing_statuses', upload_id, processing_status)

    @classmethod
    def get_upload_processing_status(cls, upload_id):
        value = cls.redis_client.hget('upload_processing_statuses', upload_id)
        return value.decode('utf-8') if value else None

    @classmethod
    def mark_upload_as_processed(cls, upload_id):
        cls.redis_client.hdel('upload_processing_statuses', upload_id)

    @classmethod
    def get_num_uploads_in_queue(cls):
        return cls.redis_client.hlen('upload_processing_statuses')

    @classmethod
    def clear_upload_queue(cls):
        cls.redis_client.delete('upload_processing_statuses')
