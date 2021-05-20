import logging
import schedule
import time
import datetime
import boto3
import json
import os
import redisdb
import user_utils

def backup_redis_db():
    scp_username = os.environ['RSYNC_NET_USER']
    scp_hostname = os.environ['RSYNC_NET_HOST']

    logging.info('backing up redis db')
    connection = redisdb.RedisDb()

    session = boto3.session.Session()
    client = session.client('s3',
                            region_name=os.environ['SPACE_REGION'],
                            endpoint_url=os.environ['SPACE_ENDPOINT_URL'],
                            aws_access_key_id=os.environ['SPACE_KEY'],
                            aws_secret_access_key=os.environ['SPACE_SECRET'])    
    bucket_name = 'cloud-language-tools-redis-backups'

    full_db_dump = connection.full_db_dump()
    time_str = datetime.datetime.now().strftime('%H')
    file_name = f'redis_backup_{time_str}.json'
    client.put_object(Body=str(json.dumps(full_db_dump)), Bucket=bucket_name, Key=file_name)
    logging.info(f'wrote {file_name} to {bucket_name}')

    # write to disk
    f = open(file_name, 'w')
    f.write(json.dumps(full_db_dump))
    f.close()
    
    # scp to rsync.net
    scp_commandline = f'scp -i ssh_id_rsync_redis_backup {file_name} {scp_username}@{scp_hostname}:backup/digitalocean_redis/'
    logging.info(f'scp commandline: [{scp_commandline}]')
    os.system(scp_commandline)



def update_airtable():
    logging.info('updating airtable')
    utils = user_utils.UserUtils()
    utils.update_airtable_all()

def setup_tasks():
    logging.info('running tasks once')
    backup_redis_db()
    update_airtable()
    logging.info('setting up tasks')
    schedule.every(1).hour.do(backup_redis_db)
    schedule.every(6).hours.do(update_airtable)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(5)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.INFO)    
    setup_tasks()
    run_scheduler()