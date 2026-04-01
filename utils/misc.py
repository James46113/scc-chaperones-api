def serialiseItem(item):
    item = item.__dict__
    item.pop('_sa_instance_state', None)
    return item


def serialiseItems(items):
    items_list = [serialiseItem(item) for item in items]
    return items_list

