import json
import sys

import uno


def parse_toc_entry(text):
    # separate by tab
    parts = text.split("\t")
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) == 3:
        # Format: "1.1  TITLE  5"
        return {"index": parts[0], "name": parts[1], "page": parts[2]}
    elif len(parts) == 2:
        # Format: "TITLE  5" ou "1  TITLE"
        # check if last is a page number
        if parts[-1].isdigit():
            return {"index": None, "name": parts[0], "page": parts[1]}
        else:
            return {"index": parts[0], "name": parts[1], "page": None}
    elif len(parts) == 1:
        return {"index": None, "name": parts[0], "page": None}
    else:
        return {"index": None, "name": text.strip(), "page": None}


def update_toc(file_path):
    result = []
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", localContext
    )
    ctx = resolver.resolve("uno:pipe,name=update_toc;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    # Open file
    sUrl = uno.systemPathToFileUrl(file_path)
    doc = desktop.loadComponentFromURL(sUrl, "_blank", 0, [])

    # Update ToC
    indexes = doc.getDocumentIndexes()
    for i in range(indexes.Count):
        index = indexes.getByIndex(i)
        index.update()

        anchor = index.Anchor
        enum = anchor.createEnumeration()
        j = 0
        while enum.hasMoreElements():
            paragraph = enum.nextElement()
            if paragraph.supportsService("com.sun.star.text.Paragraph"):
                entry_text = paragraph.getString()

                if entry_text.strip():
                    parsed = parse_toc_entry(entry_text)
                    result.append(
                        {
                            "toc_index": j,
                            "index": parsed["index"],
                            "name": parsed["name"],
                            "page": parsed["page"],
                        }
                    )
            j += 1

    # Save
    doc.close(True)
    return result


if __name__ == "__main__":
    file_path = sys.argv[1]

    result = update_toc(file_path)
    print(json.dumps(result, ensure_ascii=False))
