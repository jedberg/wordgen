import sqlite3
import random
import math
import logging

from bisect import bisect

LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)

class ngram(object):
    def __init__(self):
        self.conn = sqlite3.connect('ngrams3.db')
        self.c = self.conn.cursor()

    def problist(self, pos=1, context="", reverse=False):
        #TODO: Error check the context to make sure it's 3 letters and only uses a % as a wildcard
        #TODO: Error check that the position isn't greater than 52
        #TODO: Error check that context and position make sense (ie. no context with position 1 if not being reversed

        rows = []
        whichletter = 3
        letter_position = "pos%d" % pos
        where_clause = "%%%"

        if len(context) == 2:
            if reverse:
                where_clause = "%%%s" % context
                whichletter = 1
            else:
                where_clause = "%s%%" % context

        if len(context) == 1:
            whichletter = 2
            if reverse:
                where_clause = "%%%%%s" % context
            else:
                where_clause = "%s%%%%" % context

        if "%" in context:
            whichletter = 2
            letter_position = "pos%d" % (pos - 1)
            where_clause = "%s" % context

        # No context? Then we return a list of possible letters for that position
        if context == "":
            whichletter = 1
            rows = [row for row in self.c.execute(
                "SELECT SUBSTR(ngram, %d, %d) as choices, SUM(%s) as vals from ngrams3 where %s > 0 group by choices" %
                (whichletter, 1, letter_position, letter_position))]

        else:
            rows = [row for row in self.c.execute(
                "SELECT SUBSTR(ngram, %d, %d) as choices, SUM(%s) as vals from ngrams3 where (ngram like ?) AND %s > 0 group by choices" %
                (whichletter, 1, letter_position, letter_position), (where_clause,))]

        # normalize values for probabilities
        # this will come out to around 100, but may be higher due to rounding
        # it's here so when we generate a list for selecting a letter the list isn't too big
        # Also it gives the less likely letters a slightly better chance, which
        # gives a better chance of not generating a real word.
        total = sum([v[1] for v in rows])
        return [(v[0].lower(), math.ceil((float(v[1])/float(total)*100))) for v in rows]

def weighted_choice(choices):
    values, weights = zip(*choices)
    total = 0
    cum_weights = []
    for w in weights:
        total += w
        cum_weights.append(total)
    x = random.random() * total
    i = bisect(cum_weights, x)
    return values[i]

def genword(length=6, prefix="", suffix=""):
    blanks = length - len(prefix) - len(suffix)
    result = list(prefix) + list("%" * blanks) + list(suffix)
    n = ngram()
    choice_list = []

    while "%" in result:
        position = result.index("%")
        context = ''.join(result[max(0,(position - 2)):max(0,(position))])
        if suffix and prefix == "":
            position = ''.join(result).rfind("%")
            context = ''.join(result[max(0,(position+1)):max(0,(position + 3))])
        if blanks == 1 and (position < length) and position != 0:
            infix_context = result[max(0,position-1)] + "%" + result[min(position+1,length - 1)]
            choice_list = n.problist(pos=(position + 1), context=context) + n.problist(pos=(position + 1), context=infix_context)
        else:
            if suffix and prefix == "":
                choice_list = n.problist(pos=(position + 1), context=context, reverse=True)
            else:
                choice_list = n.problist(pos=(position + 1), context=context)
        if len(choice_list) > 0:
            result[position] = weighted_choice(choice_list)
        else:
            # Went down a bad path, start over
            print "Whoops"
            blanks = length - len(prefix) - len(suffix)
            result = list(prefix) + list("%" * blanks) + list(suffix)

        blanks = blanks - 1
    return ''.join(result)

def handler(event, context):
    return {'status': 'success'}

def handler(event, context):
    ret = {}
    r = ""
    for x in xrange(int(event['words'])):
        w = genword(length=8, prefix=event['prefix'])
        ret[w.lower().title()] = ""
    return ret

