import csv
import io

from .codec import decode


COLUMNS = ('环根', '起点引用', '终点引用', '起点样地', '终点样地', '起点 UTC', '终点 UTC', '秒数', '类型')
RANGE_COLUMNS = ('环根', '起点引用', '终点引用', '起点样地', '终点样地', '起点最早 UTC', '起点最晚 UTC',
                 '终点最早 UTC', '终点最晚 UTC', '最短秒数', '最长秒数', '类型')


def kind_label(row):
    return '移动' if row['kind'] == 'move' else '驻留'


def routes_csv(payload):
    snapshot = decode(payload)
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    range_format = snapshot.get('format', 1) >= 2
    writer.writerow(RANGE_COLUMNS if range_format else COLUMNS)
    for track in snapshot['routes']:
        for row in track['segments']:
            if range_format and 'start_until' in row:
                writer.writerow([track['root'], row['from_event'], row['to_event'], row['from_site'], row['to_site'],
                                 row['start'], row['start_until'], row['end'], row['end_until'],
                                 row['min_elapsed_seconds'], row['max_elapsed_seconds'], kind_label(row)])
            else:
                writer.writerow([track['root'], row['from_event'], row['to_event'], row['from_site'], row['to_site'],
                                 row['start'], row['end'], row['elapsed_seconds'], kind_label(row)])
    return output.getvalue().encode('utf-8-sig')
