import babel.dates
import datetime

from isserviceup.config import config
from flask import Flask, jsonify, render_template
from flask_cors import CORS, cross_origin
import redis

app = Flask(__name__, static_url_path='', static_folder='static')
app.config.from_object(config)
CORS(app)

rclient = redis.from_url(config.REDIS_URL, charset="utf-8", decode_responses=True)


@app.template_filter('timedelta')
def format_timedelta(value):
    now = datetime.datetime.now()
    return babel.dates.format_timedelta(value - now, add_direction=True)


@app.route('/', methods=['GET'])
def get_index():
    services = config.SERVICES

    status_values = {
        'ok': ('Operational', 'fa-check', 'green'),
        'minor': ('Degraded Performance', 'fa-minus-square', 'yellow'),
        'major': ('Partial Outage', 'fa-exclamation-triangle', 'orange'),
        'critical': ('Major Outage', 'fa-times', 'red'),
        'maintenance': ('Maintenance', 'fa-wrench', 'blue'),
    }

    pipe = rclient.pipeline()
    for service in services:
        pipe.hgetall('service:{}'.format(service.name))
    pipe.get('services:last_update')
    values = pipe.execute()

    data = []
    for i, service in enumerate(services):
        status = values[i]['status']
        last_service_update = float(values[i]['last_update'])
        s = {
            'name': service.name,
            'status_page_url': service.status_url,
            'icon_url': service.icon_url,
            'status': status_values[status][0],
            'last_update': last_service_update,
            'status_icon': status_values[status][1],
            'status_color': status_values[status][2],
        }
        data.append(s)

    last_update = float(values[-1]) if values[-1] else 0
    last_update = datetime.datetime.fromtimestamp(last_update)
    return render_template('index.html', services=data, last_update=last_update)


if __name__ == '__main__':
    app.debug = config.DEBUG
    app.run(host='0.0.0.0', port=8000)