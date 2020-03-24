from io import BytesIO


def byte2int(a):
    return a[0]


class CorruptError(Exception):
    pass


def uncompress(src):
    """uncompress a block of lz4 data.

    :param bytes src: lz4 compressed data (LZ4 Blocks)
    :returns: uncompressed data
    :rtype: bytearray

    .. seealso:: http://cyan4973.github.io/lz4/lz4_Block_format.html
    """
    src = BytesIO(src)

    # if we have the original size, we could pre-allocate the buffer with
    # bytearray(original_size), but then we would have to use indexing
    # instad of .append() and .extend()
    dst = bytearray()
    min_match_len = 4

    def get_length(src, length):
        """get the length of a lz4 variable length integer."""
        if length != 0x0f:
            return length

        while True:
            read_buf = src.read(1)
            if len(read_buf) != 1:
                raise CorruptError("EOF at length read")
            len_part = byte2int(read_buf)

            length += len_part

            if len_part != 0xff:
                break

        return length

    while True:
        # decode a block
        read_buf = src.read(1)
        if len(read_buf) == 0:
            raise CorruptError("EOF at reading literal-len")
        token = byte2int(read_buf)

        literal_len = get_length(src, (token >> 4) & 0x0f)

        # copy the literal to the output buffer
        read_buf = src.read(literal_len)

        if len(read_buf) != literal_len:
            raise CorruptError("not literal data")
        dst.extend(read_buf)

        read_buf = src.read(2)
        if len(read_buf) == 0:
            if token & 0x0f != 0:
                raise CorruptError("EOF, but match-len > 0: %u" % (token % 0x0f,))
            break

        if len(read_buf) != 2:
            raise CorruptError("premature EOF")

        offset = byte2int([read_buf[0]]) | (byte2int([read_buf[1]]) << 8)

        if offset == 0:
            raise CorruptError("offset can't be 0")

        match_len = get_length(src, (token >> 0) & 0x0f)
        match_len += min_match_len

        # append the sliding window of the previous literals
        for _ in range(match_len):
            dst.append(dst[-offset])

    return dst
