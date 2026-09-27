"""Bounded PKWARE DCL decoder, adapted from Mark Adler's blast.c v1.3.1.

Copyright (C) 2003, 2012, 2013 Mark Adler. See blast-reference.c for the
unaltered upstream source and format, and blast.h for the full zlib license.
This is an altered Python implementation for local asset investigation.
"""
def table(rep):
    lengths = [n & 15 for n in rep for _ in range((n >> 4) + 1)]
    return ([lengths.count(n) for n in range(14)],
            sorted(range(len(lengths)), key=lambda i: (lengths[i], i)))

LIT = table([11,124,8,7,28,7,188,13,76,4,10,8,12,10,12,10,8,23,8,9,7,6,7,8,7,6,55,8,23,24,12,11,7,9,11,12,6,7,22,5,7,24,6,11,9,6,7,22,7,11,38,7,9,8,25,11,8,11,9,12,8,12,5,38,5,38,5,11,7,5,6,21,6,10,53,8,7,24,10,27,44,253,253,253,252,252,252,13,12,45,12,45,12,61,12,45,44,173])
LEN = table([2,35,36,53,38,23])
DIST = table([2,20,53,230,247,151,248])
BASE = [3,2,4,5,6,7,8,9,10,12,16,24,40,72,136,264]
EXTRA = [0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8]

def decompress(data, max_output=16_000_000):
    pos = hold = count = 0
    def bits(n):
        nonlocal pos, hold, count
        while count < n:
            if pos >= len(data):
                raise ValueError('Truncated DCL stream')
            hold |= data[pos] << count
            pos += 1
            count += 8
        result = hold & ((1 << n) - 1)
        hold >>= n
        count -= n
        return result
    def decode(t):
        counts, symbols = t
        code = first = index = 0
        for length in range(1,14):
            code |= bits(1) ^ 1
            amount = counts[length]
            if code < first + amount:
                return symbols[index + code - first]
            index += amount
            first = (first + amount) << 1
            code <<= 1
        raise ValueError('Invalid DCL Huffman code')
    coded = bits(8)
    dictionary = bits(8)
    if coded > 1 or dictionary not in (4,5,6):
        raise ValueError('Invalid DCL header')
    out = bytearray()
    while True:
        if bits(1):
            symbol = decode(LEN)
            length = BASE[symbol] + bits(EXTRA[symbol])
            if length == 519:
                return bytes(out), pos
            n = 2 if length == 2 else dictionary
            distance = (decode(DIST) << n) + bits(n) + 1
            if distance > len(out):
                raise ValueError('DCL distance before output')
            if len(out) + length > max_output:
                raise ValueError('DCL output limit')
            for _ in range(length):
                out.append(out[-distance])
        else:
            if len(out) >= max_output:
                raise ValueError('DCL output limit')
            out.append(decode(LIT) if coded else bits(8))
