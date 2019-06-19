# https://stackoverflow.com/questions/9485788/convert-quadratic-curve-to-cubic-curve
# http://nowokay.hatenablog.com/entry/20070623/1182556929


# convert quadratic curve to cubic bezier
def quad2cubic(p1, c1, p2):
    cubic_p1 = p1
    cubic_c1 = ((p1[0] + 2 * c1[0]) / 3, (p1[1] + 2 * c1[1]) / 3)
    cubic_c2 = ((p2[0] + 2 * c1[0]) / 3, (p1[1] + 2 * c1[1]) / 3)
    cubic_p2 = p2
    return (cubic_p1, cubic_c1, cubic_c2, cubic_p2)
