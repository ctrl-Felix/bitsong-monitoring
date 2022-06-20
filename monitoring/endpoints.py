import os
from typing import Literal

import requests

from monitoring import *


class Endpoints:
    block: int
    chainid: str
    status = Literal['up', 'down', 'stuck']

    def __init__(self):
        file_url = "https://raw.githubusercontent.com/bitsongofficial/delegation-program/master/endpoints.json"
        self.endpoints = requests.get(file_url).json()
        self.rpc = os.getenv('RPC')

    def setChainData(self) -> None:
        r = requests.get(self.rpc + "/status").json()
        self.block = 0 if r['result']['sync_info']['catching_up'] else int(
            r['result']['sync_info']['latest_block_height'])
        self.chainid = r['result']['node_info']['network']
        logging.info(f"Current Block: {self.block}")

    def createUptimeReport(self) -> dict:
        self.setChainData()
        report = {}
        for addr, node in self.endpoints['rpc'].items():
            report[node] = self.checkRPC(node)
        for addr, node in self.endpoints['rpcarchive'].items():
            report[node] = self.checkRPC(node)
        for addr, node in self.endpoints['api'].items():
            report[node] = self.checkAPI(node)
        for addr, node in self.endpoints['apiarchive'].items():
            report[node] = self.checkAPI(node)
        logging.info("Uptime Report generated")
        return report

    def checkAPI(self, addr) -> status:
        try:
            r = requests.get(addr + "/cosmos/staking/v1beta1/params", timeout=20)
            if r.status_code != 200:
                return "down"
            p = r.json()
            # Check if node is on the right network
            if p['params']['bond_denom'] != "ubtsg":
                return "down"

            return "up"
        except requests.exceptions.RequestException:
            return "down"

    def checkRPC(self, addr) -> status:
        try:
            r = requests.get(addr + "/status", timeout=20)
            if r.status_code != 200:
                return "down"
            p = r.json()
            # Check if node is synced
            if p['result']['sync_info']['catching_up'] or int(
                    p['result']['sync_info']['latest_block_height']) < self.block - 10:
                return "stuck"
            # Check that node is on the right network
            if p['result']['node_info']['network'] != self.chainid:
                return "down"
            return "up"
        except requests.exceptions.RequestException:
            return "down"
