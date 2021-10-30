def trunk(f, num_decimals):
    if isinstance(f, float):
        ret = ""
        count_decimals = 0
        in_decimals = False
        str_f = str(f)
        if "e" in str_f:
            end_e_idx = str_f.index("e")
            suffix = str_f[end_e_idx:]
        else:
            suffix = ""
        num_decimals-=len(suffix)
        num_decimals = max(1, num_decimals)
        for c in str_f:
            ret += c
            if in_decimals:
                count_decimals += 1
                if count_decimals == num_decimals:
                    break
                elif count_decimals > num_decimals:
                    assert False
            if c == ".":
                in_decimals = True
        return ret+suffix
    else:
        return str(f)