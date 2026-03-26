import sys

import uno


def update_toc(file_path):
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext
    )
    ctx = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
    )
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    # Open file
    sUrl = uno.systemPathToFileUrl(file_path)
    doc = desktop.loadComponentFromURL(sUrl, "_blank", 0, [])

    # Update ToC
    indexes = doc.getDocumentIndexes()
    for i in range(indexes.Count):
        indexes.getByIndex(i).update()

    # Save
    doc.store()
    doc.close(True)


if __name__ == "__main__":
    update_toc(sys.argv[1])
