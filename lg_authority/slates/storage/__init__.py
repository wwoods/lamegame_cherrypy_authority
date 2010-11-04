
def get_storage_class(name):
    pname = name.lower()
    name = name.title()
    result = __import__('lg_authority.slates.storage.' + pname + '_store', globals(), locals(), ['*'])
    return getattr(result, name + 'Storage')

