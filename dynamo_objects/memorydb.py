import datetime

from boto.dynamodb2.exceptions import ItemNotFound

NOT_FOUND = 'missing'


class KeyValueStorage(object):

    def __init__(self):
        self.data = {}
        self.db_table = None

    def get_hash(self, *args):
        keys = self.db_table._check_keys(*args)
        return '#'.join(map(lambda it: str(it), keys))

    def has_item_key(self, *args):
        hashkey = self.get_hash(*args)
        return hashkey in self.data

    def has_item(self, *args):
        hashkey = self.get_hash(*args)
        return (hashkey in self.data) and (self.data[hashkey] is not None)

    def get_item(self, *args):
        hashkey = self.get_hash(*args)
        return self.data[hashkey] if hashkey in self.data else None

    def put_item(self, item, *args):
        hashkey = self.get_hash(*args)
        if args[0] == '2015-01-11':
            raise Exception('here')
        if not hashkey:
            raise Exception('Unable to get a hash key for item: %s' % item)
        if (hashkey in self.data) and (self.data[hashkey] is not None):
            raise Exception(
                'Item with %s key already exists in %s: %s' % (
                    hashkey, type(self), str(self.data[hashkey].get_dict())))
        self.data[hashkey] = item

    def delete_item(self, *args):
        hashkey = self.get_hash(*args)
        if hashkey in self.data:
            del self.data[hashkey]

    def reset(self):
        self.data = {}


class MemoryTable(KeyValueStorage):
    db_reads = 0
    hits = 0

    def __init__(self, db_table):
        self.db_table = db_table
        self.load_from_db = True
        super(MemoryTable, self).__init__()

    def get_db_table(self):
        raise Exception('Not implemented')

    def set_load_from_db(self, do_load):
        self.load_from_db = do_load

    def get_hash(self, *args):
        keys = self.db_table._check_keys(*args)
        return super(MemoryTable, self).get_hash(*keys)

    def get(self, hashkey, rangekey=None, create=False, times=None):
        start = datetime.datetime.now()
        st = datetime.datetime.now()
        item = self.get_item(hashkey, rangekey)
        if item == NOT_FOUND:
            self.hits += 1
            if not create:
                raise ItemNotFound
            item = None
        en = datetime.datetime.now()
        if times:
            times['mem_get_item'] += (en - st).total_seconds()
        if item is None:
            if self.load_from_db:
                st = datetime.datetime.now()
                self.db_reads += 1
                if times:
                    item = self.db_table.get(
                        hashkey, rangekey, create, times=times)
                else:
                    try:
                        item = self.db_table.get(hashkey, rangekey, create)
                    except:
                        self.put_item(NOT_FOUND, hashkey, rangekey)
                        raise
                self.put_item(item, hashkey, rangekey)
                en = datetime.datetime.now()
                if times:
                    times['mem_get_from_db'] += (en - st).total_seconds()
            else:
                st = datetime.datetime.now()
                item = self.db_table._create_record(hashkey, rangekey)
                self.put_item(item, hashkey, rangekey)
                en = datetime.datetime.now()
                if times:
                    times['mem_create_record'] += (en - st).total_seconds()
        else:
            self.hits += 1
        end = datetime.datetime.now()
        if times:
            times['mem_total'] += (end - start).total_seconds()
        return item

    def delete(self, hashkey, rangekey=None):
        item = self.db_table.delete(hashkey, rangekey)
        self.delete_item(item, hashkey, rangekey)
        return item

    def save(self, item):
        keys = self.db_table._get_record_keys(item)
        hashkey = self.get_hash(*keys)
        existed = self.data.get(hashkey)
        if existed == NOT_FOUND:
            del (self.data[hashkey])
        if existed in [NOT_FOUND, None]:
            self.put_item(item, *keys)

    def save_data(self, ignore_errors=False, overwrite=False):
        for hashkey in self.data:
            try:
                if self.data[hashkey] == NOT_FOUND:
                    continue
                item = self.db_table._get_item_for_record(self.data[hashkey])
                item.save(overwrite=overwrite)
            except Exception as e:
                if ignore_errors:
                    return e
                else:
                    raise
        return None

    def save_data_batch(self, ignore_errors=False, overwrite=False):
        with self.db_table.table.batch_write() as batch:
            for hashkey in self.data:
                try:
                    if self.data[hashkey] == NOT_FOUND:
                        continue
                    item = \
                        self.db_table._get_item_for_record(self.data[hashkey])
                    batch.put_item(item, overwrite=overwrite)
                except Exception as e:
                    if ignore_errors:
                        return e
                    else:
                        raise
        return None

    def get_data(self):
        return [item for __, item in self.data.items()]
