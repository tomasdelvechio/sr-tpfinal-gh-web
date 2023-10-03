"""
Testea y da ejemplos de consultas al indice creado por init.py
"""

import whoosh as wh
from whoosh import qparser

ix = wh.index.open_dir("indexdir")

q1_terms = [
    wh.query.Term("topics", "deep-learning"),
    wh.query.Term("language", "c++")
]
q2_terms = [
    qparser.QueryParser("about", schema=ix.schema),
]

queries = [
    wh.query.And(q1_terms),
    q2_terms[0].parse(u"open machine"),
]

with ix.searcher() as searcher:
    #print(list(searcher.lexicon("language")))
    for query in queries:
        print(query)
        results = searcher.search(query, terms=True)
        #print(results)
        for r in results:
            print(r)