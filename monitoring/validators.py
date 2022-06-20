import datetime
import json
import os
import threading
import time
import traceback

import requests
import websocket
from joblib import Parallel, delayed

from monitoring import *
from database.Blocks import Blocks


class Validators:
    api = os.getenv('API')
    rpc = os.getenv('RPC')

    # Current parsing height which is network height - 1 to ensure the signatures for this block are already available
    height: int
    tmp = {'signatures': {}}

    def getBlockSignatures(self, height: int) -> list:
        """Get the Signatures of a givern block by querying them from the block before
        Note: If the next block isn't available yet this will fail"""
        rpc = os.getenv('RPC')
        api = os.getenv('API')

        # Get Signatures in Block, Check if they are in the tmp else query them. Note: They are stored in the following block,
        if height + 1 in self.tmp['signatures']:
            validators_raw = [x['validator_address'] for x in self.tmp['signatures'][height + 1]]
            del self.tmp['signatures'][height + 1]
        else:
            br = requests.get(rpc + "/block", params={'height': str(height + 1)})
            b = br.json()
            validators_raw = [x['validator_address'] for x in b['result']['block']['last_commit']['signatures'] if
                              x['validator_address'] != '']

        # Match the addresses with the validator pubkeys
        pr = requests.get(rpc + "/validators", params={'height': str(height), 'per_page': 300})
        p = pr.json()
        # Create a list with the converted 'addresses' from above to their according pubkey
        validators_pubkey = [
            list(filter(lambda val: a == val['address'], p['result']['validators']))[0]['pub_key']['value']
            for a in validators_raw]

        # Get all validators and match them with the pubkeys
        vr = requests.get(api + "/cosmos/staking/v1beta1/validators", params={'pagination.limit': 300})
        v = vr.json()
        validators = [
            list(filter(lambda val: c == val['consensus_pubkey']['key'], v['validators']))[0]['operator_address']
            for c in validators_pubkey]

        return validators

    def getBlockTimestamp(self, height) -> datetime.datetime:
        # Query timestamp
        tr = requests.get(self.rpc + "/block", params={'height': str(height)})
        t = tr.json()
        timestamp = datetime.datetime.strptime(t['result']['block']['header']['time'][:-4] + 'Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        return timestamp

    def getLastBlockInDb(self) -> int:
        x = Blocks.objects().order_by('-height').first()
        return x.height if x else -1

    def getFirstBlockInDb(self) -> int:
        x = Blocks.objects().order_by('+height').first()
        return x.height if x else -1

    def syncBlockByHeight(self, height: int, tries: int = 0) -> None:
        try:
            r = self.getBlockSignatures(height)
            t = self.getBlockTimestamp(height)

            bdb = Blocks(
                height=height,
                time=t,
                signed=r
            )
            bdb.save()
            logging.info(f"Synced block: {height}")

        except Exception as e:
            if tries < 5:
                logging.warning(f"Error while syncing block {height} | Try {tries + 1}")
                # logging.info(f"Trace: {traceback.format_exc()}")
                time.sleep((tries + 1)**2)
                self.syncBlockByHeight(height, tries=tries + 1)
            else:
                logging.error(f"Error while syncing block {height} | Try {tries + 1} | No retry left")
                logging.info(f"Trace: {traceback.format_exc()}")
                bdb = Blocks(
                    height=height,
                    time=0,
                    signed=[]
                )
                bdb.save()

    def on_block(self, ws, msg):
        try:
            j = json.loads(msg)
            if not j['result']: return
            data = j['result']['data']['value']['block']
            newheight = int(data['header']['height'])
            logging.info(f"New Block found: {newheight}")


            # Set new Block but reduce it by one to
            self.height = newheight - 1

            # Add signatures to tmp to not need the query
            self.tmp['signatures'][newheight] = data['last_commit']['signatures']

            # Trigger sync
            self.syncBlockByHeight(newheight - 1)
        except Exception as e:
            logging.warning(f"Failed to parse websocket event: {e}")
            logging.info(traceback.format_exc())

    def on_open(self, ws):
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "subscribe",
            "params": ["tm.event = 'NewBlock'"]
        }))

    def on_error(self, ws, error):
        logging.error(f"Websocket error: {error}")

    def catchUp(self, start, end):
        Parallel(n_jobs=4, prefer="threads")(
            delayed(self.syncBlockByHeight)(height, ) for height in range(start, end + 1))

    def start(self):
        n = self.getLastBlockInDb()
        rr = requests.get(self.rpc + "/status")
        r = rr.json()
        start = n if n != -1 else 6005720
        end = int(r['result']['sync_info']['latest_block_height'])
        logging.info(f"Last Block in Database: {start}")
        logging.info(f"Last Block on Chain: {end}")

        if end > start:
            logging.info("Starting to catch up missing blocks")
            t = threading.Thread(target=self.catchUp, args=(start, end), daemon=True)
            t.start()

        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(os.getenv('WEBSOCKET'),
                                    on_message=self.on_block,
                                    on_error=self.on_error
                                    )
        ws.on_open = self.on_open
        logging.info("Starting websocket")
        ws.run_forever()
