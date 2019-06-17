from operator import itemgetter
from xml.dom import minidom

import time
import json

from seoanalyzer.analyzer import Page, Manifest, check_dns, getText


def analyze(site, sitemap=None, verbose=False, **session_params):
    """Session params are  headers, default cookies, etc...

       To quickly see your options, go into python and type:
       >>> print(requests.Session.__attrs__)
    """
    start_time = time.time()

    # Init our HTTP session
    if session_params:
        Manifest.modify_session(**session_params)
    else:
        Manifest()

    def calc_total_time():
        return time.time() - start_time

    crawled = []
    output = {'pages': [], 'keywords': [], 'errors': [], 'total_time': calc_total_time()}

    if check_dns(site) is False:
        output['errors'].append('DNS Lookup Failed')
        output['total_time'] = calc_total_time()
        return output

    if sitemap is not None:
        page = Manifest.session.get(sitemap)
        xml_raw = page.text
        xmldoc = minidom.parseString(xml_raw)
        urls = xmldoc.getElementsByTagName('loc')

        for url in urls:
            Manifest.pages_to_crawl.append(getText(url.childNodes))

    pg = Page(site, site)
    pg.analyze()
    output['pages'].append(pg.talk())

    sorted_words = sorted(Manifest.wordcount.items(), key=itemgetter(1), reverse=True)
    sorted_bigrams = sorted(Manifest.bigrams.items(), key=itemgetter(1), reverse=True)
    sorted_trigrams = sorted(Manifest.trigrams.items(), key=itemgetter(1), reverse=True)

    output['keywords'] = []

    for w in sorted_words:
        if w[1] > 4:
            output['keywords'].append({
                'word': Manifest.stem_to_word[w[0]],
                'count': w[1],
            })

    for w, v in sorted_bigrams:
        if v > 4:
            output['keywords'].append({
                'word': w,
                'count': v,
            })

    for w, v in sorted_trigrams:
        if v > 4:
            output['keywords'].append({
                'word': w,
                'count': v,
            })

    # Sort one last time...
    output['keywords'] = sorted(output['keywords'], key=itemgetter('count'), reverse=True)

    output['total_time'] = calc_total_time()

    return output


if __name__ == "__main__":
    import sys
    print(sys.argv[-1:])
    output = analyze(sys.argv[-1])
    print(json.dumps(output, indent=4, separators=(',', ': ')))
