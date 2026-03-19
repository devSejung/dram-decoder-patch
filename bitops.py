def cut_bits(num, msb, lsb):
    return (num >> lsb) & ((1 << (msb - lsb + 1)) - 1)


def inv_bits(num, bitlength):
    return pow(2, bitlength) - 1 - num


def parity(x):
    k = 0
    d = x
    while d != 0:
        k = k + 1
        d = d & (d - 1)
    return k % 2


def find_zero_lsb(num):
    ccc = "0" + bin(num)[2:]
    ddd = 0
    for i in range(len(ccc) - 1, -1, -1):
        if ccc[i] == "0":
            break
        ddd = ddd + 1
    return ddd
