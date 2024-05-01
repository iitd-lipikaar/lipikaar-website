import redis


redis_client = redis.Redis(host='localhost', port=6379, db=0)
print("Connection to Redis established.")

def add_to_cancelled_queued_uploads(value):
    redis_client.sadd('cancelled_queued_uploads', value)

def check_in_cancelled_queued_uploads(value):
    return redis_client.sismember('cancelled_queued_uploads', value)

def remove_from_cancelled_queued_uploads(value):
    redis_client.srem('cancelled_queued_uploads', value)

def delete_cancelled_queued_uploads():
    redis_client.delete('cancelled_queued_uploads')


def add_to_queued_uploads(value):
    redis_client.sadd('queued_uploads', value)

def check_in_queued_uploads(value):
    return redis_client.sismember('queued_uploads', value)

def remove_from_queued_uploads(value):
    redis_client.srem('queued_uploads', value)

def delete_queued_uploads():
    redis_client.delete('queued_uploads')

def size_queued_uploads():
    if not redis_client.exists('queued_uploads'):
        return 0

    return redis_client.scard('queued_uploads')

def add_processing_upload_status(upload_id, processing_status):
    redis_client.set(upload_id, processing_status)

def update_processing_upload_status(upload_id, processing_status):
    if redis_client.exists(upload_id):
        redis_client.set(upload_id, processing_status)

def get_processing_upload_status(upload_id):
    value = redis_client.get(upload_id)
    return value.decode() if value else None

def remove_processing_upload_status( upload_id):
    redis_client.delete(upload_id)

def get_num_processing_uploads():
    return redis_client.dbsize()

redis_set_methods = {
    'cancelled_queued_uploads': {
        'add': add_to_cancelled_queued_uploads,
        'check': check_in_cancelled_queued_uploads,
        'remove': remove_from_cancelled_queued_uploads,
        'delete_set': delete_cancelled_queued_uploads,
    },
    'queued_uploads': {
        'add': add_to_queued_uploads,
        'check': check_in_queued_uploads,
        'remove': remove_from_queued_uploads,
        'delete_set': delete_queued_uploads,
        'size': size_queued_uploads,
    }
}

redis_map_methods = {
    'processing_uploads': {
        'add': add_processing_upload_status,
        'get': get_processing_upload_status,
        'update': update_processing_upload_status,
        'remove': remove_processing_upload_status,
        'size': get_num_processing_uploads,
    }
}