try:
    import pytm
    print('PYTM_OK')
    import inspect
    names = dir(pytm)
    print('\n'.join(names))
    for name in names:
        if name[0].isupper():
            obj = getattr(pytm, name)
            print(name, 'callable=', callable(obj))
except Exception as e:
    print('PYTM_IMPORT_ERROR', repr(e))
