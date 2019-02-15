"""
Shitcode containment zone
"""

from operator import eq
from collections import defaultdict

def find_first(pred, l):
    """Return the first element of the list l that satisfies the predictate pred or return None if couldnt find one"""
    return next(filter(pred, l), None)

def filter_none(xs):
    """returns the list with Nones (and Falses) filtered out"""
    return [x for x in xs if x]

def half_curry(f, x):# poor man's currying
    return lambda y: f(x,y)

# def list_intersect(xs, ys, eq1=eq):
#     """Return the intersection of two lists. Can take a custom equivalence relation."""
#     def f(x): # no haskell = suffer
#         c_eq = half_curry(eq1, x)
#         return find_first(c_eq,ys)
#     return filter_none(map(f, xs))

def list_subtract(xs,ys,eq1=eq):
    """Subtracts two lists. Can take a custom equivalence relation."""
    def f(x):
        c_eq = half_curry(eq1, x)
        found = find_first(c_eq,ys)
        return False if found else x
    return filter_none(map(f, xs))

def inverse_multidict(keyfun, xs):
    """Returns a dict d such that for every k, d[k] is the set of xs with keyfun(x) equal to k."""
    ret = defaultdict(set)
    for x in xs: #no obvious way to do this in functional style
        ret[keyfun(x)].add(x)
    return ret

def mapvalues(f, dct):
    """Apply f to values of dict and return the result dict (keys stay the same)."""
    return {k: f(v) for k, v in dct.items()}