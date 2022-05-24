def chunkify(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]
