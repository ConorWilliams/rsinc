# Provides functions for manipulating packed dictionarys


def empty():
    # Returns dict representing empty directory.
    return {"fold": {}, "file": {}}


def insert(nest, chain):
    # Inserts element at the end of the chain into packed dict, nest.
    if len(chain) == 2:
        nest["file"].update({chain[0]: chain[1]})
        return

    if chain[0] not in nest["fold"]:
        nest["fold"].update({chain[0]: empty()})

    insert(nest["fold"][chain[0]], chain[1:])


def pack(flat):
    # Converts flat, into packed dict.
    nest = empty()
    for name, file in flat.names.items():
        chain = name.split("/") + [file.uid]
        insert(nest, chain)

    return nest


def unpack(nest, flat, path=""):
    # Converts packed dict, nest, into flat.
    for k, v in nest["file"].items():
        flat.update(path + k, v)

    for k, v in nest["fold"].items():
        unpack(v, flat, path + k + "/")


def _get_branch(nest, chain):
    # Returns packed dict at end of chain in packed dict, nest.
    if len(chain) == 0:
        return nest
    else:
        return _get_branch(nest["fold"][chain[0]], chain[1:])


def get_branch(nest, path):
    # Helper function for _get_branch, converts path to chain.
    return _get_branch(nest, path.split("/"))


def _merge(nest, chain, new):
    # Merge packed dict, new, into packed dict, nest, at end of chain.
    if len(chain) == 1:
        nest["fold"].update({chain[0]: new})
        return

    if chain[0] not in nest["fold"]:
        nest["fold"].update({chain[0]: empty()})

    _merge(nest["fold"][chain[0]], chain[1:], new)


def merge(nest, path, new):
    # Helper function for _merge, converts path to chain.
    _merge(nest, path.split("/"), new)
