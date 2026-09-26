def classFactory(iface):
    from .plugin import MarkhojdPlugin

    return MarkhojdPlugin(iface)
