import csv
import io

from .codec import decode


COLUMNS = ('环根', '起点引用', '终点引用', '起点样地', '终点样地', '起点 UTC', '终点 UTC', '秒数', '类型')


def routes_csv(payload):
    snapshot = decode(payload)
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(COLUMNS)
    for track in snapshot['routes']:
        for row in track['segments']:
            writer.writerow([track['root'], row['from_event'], row['to_event'], row['from_site'], row['to_site'],
                             row['start'], row['end'], row['elapsed_seconds'], '移动' if row['kind'] == 'move' else '驻留'])
    return output.getvalue().encode('utf-8-sig')
