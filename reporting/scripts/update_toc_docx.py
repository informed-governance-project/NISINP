import sys

import uno
from com.sun.star.beans import PropertyValue


def update_toc(file_path):
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )

    context = resolver.resolve(
        "uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"
    )

    desktop = context.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", context
    )

    url = uno.systemPathToFileUrl(file_path)

    props = (
        PropertyValue("Hidden", 0, True, 0),
        PropertyValue("UpdateDocMode", 0, 1, 0),
        PropertyValue("MacroExecutionMode", 0, 4, 0),
        PropertyValue("LoadReadonly", 0, False, 0),
        # 🔑 Ces deux-là préservent les styles Word :
        PropertyValue("FilterName", 0, "MS Word 2007 XML", 0),
        PropertyValue("FilterOptions", 0, "MSWordCompat", 0),
    )
    doc = desktop.loadComponentFromURL(url, "_blank", 0, props)

    try:
        indexes = doc.getDocumentIndexes()
        for i in range(indexes.getCount()):
            indexes.getByIndex(i).update()

        # 🔥 IMPORTANT : éviter store() brut
        export_props = (PropertyValue("FilterName", 0, "MS Word 2007 XML", 0),)

        doc.storeToURL(url, export_props)

    finally:
        doc.close(True)


if __name__ == "__main__":
    update_toc(sys.argv[1])
