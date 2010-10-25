def get_registrar(name):
    pname = name.lower()
    name = name.title()
    result = __import__('lg_authority.registration.' + pname, globals(), locals(), ['*'])
    return getattr(result, name + 'Registrar')

