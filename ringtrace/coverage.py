def by_site(sites, encounters, tracks):
    counters = {site: {'site': site, 'confirmed': 0, 'held_refs': set(), 'roots': set(), 'departures': 0}
                for site in sorted(sites)}
    for event in encounters:
        if event['state'] == 'confirmed':
            item = counters[event['site']]
            item['confirmed'] += 1
            item['roots'].add(event['root'])
            continue
        top_rank = max(row['priority'] for row in event['candidates'])
        for row in event['candidates']:
            if row['priority'] == top_rank:
                counters[row['site']]['held_refs'].add(event['event'])
    for track in tracks:
        for segment in track['segments']:
            if segment['kind'] == 'move':
                counters[segment['from_site']]['departures'] += 1
    return [{**item, 'held_refs': sorted(item['held_refs']), 'roots': sorted(item['roots'])}
            for item in counters.values()]
