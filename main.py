import json
import os
import logging
import requests
from time import sleep
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv

load_dotenv()


BPS_TO_GBPS = 1_000_000_000


def main():
    logging.basicConfig(
        filename="traffic_provider.log",
        format="%(asctime)s %(levelname)-2s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    zabbix = ZabbixAPI(os.environ["ZABBIX_HOST"])
    zabbix.login(os.environ["ZABBIX_USER"], os.environ["ZABBIX_PASS"])
    logging.info("Connected to Zabbix API Version %s" % zabbix.api_version())
    while True:
        up_a = 0
        down_a = 0
        up_b = 0
        down_b = 0
        logging.info("getting provider traffic info")
        ruta_a_data = zabbix.item.get(
            output=["lastclock", "lastvalue", "name"],
            filter={
                "name": [
                    "RUTA_A_DOWN",
                    "RUTA_A_UP",
                ]
            },
        )
        ruta_b_data = zabbix.item.get(
            output=["lastclock", "lastvalue", "name"],
            filter={
                "name": [
                    "RUTA_B_UP",
                    "RUTA_B_DOWN",
                ]
            },
        )
        for ruta_a in ruta_a_data:
            if "DOWN" in ruta_a["name"]:
                down_a = ruta_a["lastvalue"]
            else:
                up_a = ruta_a["lastvalue"]

        for ruta_b in ruta_b_data:
            if "DOWN" in ruta_b["name"]:
                down_b = ruta_b["lastvalue"]
            else:
                up_b = ruta_b["lastvalue"]

        routes_rates = [
            {
                "name": "RUTA_A",
                "timestamp": int(ruta_a_data[0]["lastclock"]),
                "down": int(down_a) / BPS_TO_GBPS,
                "up": int(up_a) / BPS_TO_GBPS,
            },
            {
                "name": "RUTA_B",
                "timestamp": int(ruta_b_data[0]["lastclock"]),
                "down": int(down_b) / BPS_TO_GBPS,
                "up": int(up_b) / BPS_TO_GBPS,
            },
        ]
        logging.info(
            "RUTA A : ^ %s Gbps  | v %s Gbps @ %s || RUTA B : ^ %s Gbps  | v %s Gbps @ %s"
            % (
                int(up_a) / BPS_TO_GBPS,
                int(down_a) / BPS_TO_GBPS,
                ruta_a_data[0]["lastclock"],
                int(up_b) / BPS_TO_GBPS,
                int(down_b) / BPS_TO_GBPS,
                ruta_b_data[0]["lastclock"],
            ),
        )
        sleep(10)
        try:
            response = requests.put(
                "http://db-api.conext.net.ve/update-routes-rates",
                data=json.dumps({"rates":routes_rates, "API_KEY": os.environ["API_KEY"]}),
                headers={"Content-Type": "application/json"},
                verify=False,
            )
            if response.status_code != requests.codes.ok:
                logging.error(
                    "Request failed with status code: %s" % (response.status_code)
                )
            response_json = response.json()
            logging.info("Request response with success : %s"%(response_json))
        except requests.RequestException as e:
            logging.error("An error occurred: %s" % (e))


if __name__ == "__main__":
    main()
