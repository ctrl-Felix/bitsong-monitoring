import copy
import datetime
import json
from dateutil import relativedelta
from fastapi import APIRouter
from database.Endpoints import Endpoints
from database.Blocks import Blocks

router = APIRouter(
    prefix="/uptime",
    tags=['Uptime']
)


@router.get("/endpoints/current")
async def get_current_endpoint_status():
    o = Endpoints.objects().exclude('id').order_by('-id').first().to_json()
    j = json.loads(o)
    r = {
        'time': j['time']['$date'],
        'up': [],
        'down': [],
        'stuck': []
    }
    for a, s in j['report'].items():
        r[s].append(a)
    return r


@router.get("/endpoints/historic")
async def get_current_endpoint_status():
    total = 0
    d = {
        'day': {'up': 0, 'down': 0, 'stuck': 0},
        'week': {'up': 0, 'down': 0, 'stuck': 0},
        'month': {'up': 0, 'down': 0, 'stuck': 0},
        '3months': {'up': 0, 'down': 0, 'stuck': 0},

    }
    all_endpoints = Endpoints.objects(
        time__gt=datetime.datetime.utcnow() - relativedelta.relativedelta(months=3)).distinct('report')[0].keys()
    print(all_endpoints)
    x = {e: copy.deepcopy(d) for e in all_endpoints}
    o = Endpoints.objects(time__gt=datetime.datetime.utcnow() - relativedelta.relativedelta(months=3)).exclude(
        'id').to_json()
    j = json.loads(o)
    # Loop through each report
    now = datetime.datetime.now().timestamp()
    for report in j:
        # Go through each status: [endpoints] pair
        t = report['time']['$date']
        for e, status in report['report'].items():
            # increment the counter for each endpoint in the given status
            if (now-t) < 86400:
                x[e]['day'][status] += 1
            if (now-t) < 86400 * 7:
                x[e]['week'][status] += 1
            if (now-t) < 86400 * 30:
                x[e]['month'][status] += 1
            x[e]['3months'][status] += 1

    return x


@router.get("/validators/signatures/last")
async def get_signed_validators_for_last_block():
    o = Blocks.objects().exclude('id').order_by('-id').limit.to_json()
    j = json.loads(o)
    j['time'] = j['time']['$date']
    return j
