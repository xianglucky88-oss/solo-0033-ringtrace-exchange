SOURCES = {
    'DUNE-DESK': {'label': '沙脊协作站', 'priority': 30},
    'MUD-DESK': {'label': '泥湾协作站', 'priority': 30},
    'FIELD-NOTE': {'label': '样地记录组', 'priority': 10},
}
SITES = {'REED-INLET': '蒲湾', 'SAND-ISLET': '白沙洲', 'SALT-FLAT': '盐脊', 'STONE-SHOAL': '石浅滩'}
KINDS = {'mark': '初次登记', 'recapture': '复遇登记'}


def describe():
    return {'sources': SOURCES, 'sites': SITES, 'kinds': KINDS}
