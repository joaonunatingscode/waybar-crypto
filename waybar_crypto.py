#!/usr/bin/env python3

import sys
import configparser
import os
import json
from decimal import Decimal

import requests

API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
API_KEY_ENV = "COINMARKETCAP_API_KEY"
CONFIG_FILE = "config.ini"
DATA_FILE = "data.ini"
CLASS_NAME = "crypto"


class WaybarError(Exception):

    def __init__(self, error_text: str, error_tooltip: str):
        self.errorText = error_text
        self.errorTooltip = error_tooltip
        super().__init__(self.errorText, self.errorTooltip)

    def __str__(self):
        output_obj = {
            "text": "crypto: " + self.errorText,
            "tooltip": self.errorTooltip,
            "class": CLASS_NAME
        }
        return json.dumps(output_obj)


class WaybarCrypto(object):

    def __init__(self):

        self.abs_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = f"{self.abs_dir}/{CONFIG_FILE}"
        self.data_path = f"{self.abs_dir}/{DATA_FILE}"

        self.config = self.__parse_config()

    def __parse_config(self):
        path = self.config_path
        try:
            config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
            config.read(path)
        except Exception as error:
            raise(WaybarError("parse config error", "Error while trying to read config file\nError: " + error.__str__()))

        if API_KEY_ENV in os.environ:
            api_key = str(os.environ[API_KEY_ENV])
        else:
            api_key = config["general"]["api_key"]

        currency = config["general"]["currency"].upper()
        currency_symbol = config["general"]["currency_symbol"]

        display_options = config["general"]["display"].split(",")
        display_mode = config["general"]["mode"].lower()

        if display_mode not in ['cycle', 'show_all']:
            raise(WaybarError("parse config error", "Invalid display mode: " + display_mode))

        coin_names = [section for section in config.sections() if section != "general"]

        coins = {}
        for coin_name in coin_names:
            try:
                price_precision = int(config[coin_name]["price_precision"])
                if price_precision < 0:
                    raise(Exception("Precision must be positive"))
            except Exception as error:
                raise(WaybarError("parse config error",
                                  "Invalid price precision for " + coin_name + ".\nError: " + error.__str__()))

            try:
                change_precision = int(config[coin_name]["change_precision"])
                if change_precision < 0:
                    raise (Exception("Precision must be positive"))
            except Exception as error:
                raise(WaybarError("parse config error",
                                  "Invalid change precision for " + coin_name + ".\nError: " + error.__str__()))

            try:
                volume_precision = int(config[coin_name]["volume_precision"])
                if volume_precision < 0:
                    raise(Exception("Precision must be positive"))
            except Exception as error:
                raise(WaybarError("parse config error",
                                  "Invalid volume precision for " + coin_name + ".\nError: " + error.__str__()))

            coins[coin_name] = {
                "icon": config[coin_name]["icon"],
                "price_precision": price_precision,
                "change_precision": change_precision,
                "volume_precision": volume_precision,
            }

        return {
            "coin_names": coin_names,
            "coins": coins,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "display_options": display_options,
            "display_mode": display_mode,
            "api_key": api_key,
        }

    def __get_coin_obj(self, coin_name: str):
        config = self.config
        coins = config["coins"]
        return {
            "icon": coins[coin_name]["icon"],
            "price_precision": coins[coin_name]["price_precision"],
            "change_precision": coins[coin_name]["change_precision"],
            "volume_precision": coins[coin_name]["volume_precision"]
        }

    def __get_coinmarketcap_latest(self):
        # Construct API query parameters
        params = {
            "convert": self.config["currency"].upper(),
            "symbol": ",".join(coin.upper() for coin in self.config["coins"]),
        }

        # Add the API key as the expected header field
        headers = {"X-CMC_PRO_API_KEY": self.config["api_key"]}

        # Request the chosen price pairs
        response = requests.get(API_URL, params=params, headers=headers, timeout=2)
        if response.status_code != 200:
            raise(Exception("Status code: " + str(response.status_code)))

        try:
            api_json = response.json()
        except ValueError as e:
            raise(Exception("Could not parse API response body as JSON. " + e.__str__()))

        try:
            with open(f"{self.abs_dir}/last_fetch.json", 'w') as file:
                json.dump(api_json, file)
        except Exception as e:
            raise(Exception("Could not save fetch to last_fetch.json. " + e.__str__()))

        return api_json

    def __get_last_fetch(self):

        try:
            with open(f"{self.abs_dir}/last_fetch.json", 'r') as file:
                last_fetch = json.load(file)
        except Exception as e:
            raise(Exception("Could not get last fetch information from last_fetch.json. " + e.__str__()))

        return last_fetch

    def __build_output(self, coin_name: str, pair_info: dict):
        coin_obj = self.__get_coin_obj(coin_name)
        icon = coin_obj["icon"]
        price_precision = coin_obj["price_precision"]
        volume_precision = coin_obj["volume_precision"]
        change_precision = coin_obj["change_precision"]
        config = self.config
        display_options = config["display_options"]
        currency_symbol = config["currency_symbol"]

        output = f"{icon} "

        # Shows price by default
        if "price" in display_options or not display_options:
            current_price = round(Decimal(pair_info["price"]), price_precision)
            output += f"{currency_symbol}{current_price} "

        if "volume24h" in display_options:
            percentage_change = round(Decimal(pair_info["volume_24h"]), volume_precision)
            output += f"24hV:{currency_symbol}{percentage_change:+} "

        if "change1h" in display_options:
            percentage_change = round(Decimal(pair_info["percent_change_1h"]), change_precision)
            output += f"1h:{percentage_change:+}% "

        if "change24h" in display_options:
            percentage_change = round(Decimal(pair_info["percent_change_24h"]), change_precision)
            output += f"24h:{percentage_change:+}% "

        if "change7d" in display_options:
            percentage_change = round(Decimal(pair_info["percent_change_7d"]), change_precision)
            output += f"7d:{percentage_change:+}% "

        return output

    def get_obj(self) -> dict:

        output_obj = {
            "text": "",
            "tooltip": "",
            "class": CLASS_NAME
        }

        config = self.config
        try:
            data = configparser.ConfigParser(allow_no_value=True, interpolation=None)
            data.read(self.data_path)
        except Exception as error:
            raise(WaybarError("parse data error", "Error while trying to read data file. " + error.__str__()))

        on_click = data.getboolean("general", "on_click")
        if not on_click:
            try:
                api_json = self.__get_coinmarketcap_latest()
            except Exception as error:
                raise(WaybarError("coinmarketcap error", error.__str__()))
        else:
            try:
                api_json = self.__get_last_fetch()
            except Exception as error:
                raise(WaybarError("local fetch error", error.__str__()))

        text = ""
        if config["display_mode"] == "cycle":
            output_obj["tooltip"] = "Cycle mode: press to view other coins"
            curr_coin_name = data["cycle"]["current"]
            if curr_coin_name is None or curr_coin_name not in config["coin_names"]:
                curr_coin_name = config["coin_names"][0]

            # Cycle next coin if user pressed
            if on_click:
                next_index = config["coin_names"].index(curr_coin_name).__add__(1) % len(config["coin_names"])
                curr_coin_name = config["coin_names"][next_index]
                data["cycle"]["current"] = curr_coin_name
                data["general"]["on_click"] = "false"
                try:
                    with open(self.data_path, 'w') as file:
                        data.write(file)
                except Exception as error:
                    raise(WaybarError("read data file error", "Error while trying to read data file. " + error.__str__()))

            pair_info = api_json["data"][curr_coin_name.upper()]["quote"][config["currency"]]
            text = self.__build_output(curr_coin_name, pair_info)

        elif config["display_mode"] == "show_all":
            for coin_name, coin_obj in config["coins"].items():
                pair_info = api_json["data"][coin_name.upper()]["quote"][config["currency"]]
                text += self.__build_output(coin_name, pair_info)
            output_obj["tooltip"] = "Show all mode: shows all coins"

            if on_click:
                data["general"]["on_click"] = "false"
                try:
                    with open(self.data_path, 'w') as file:
                        data.write(file)
                except Exception as error:
                    raise(WaybarError("write data file error", "Error while trying to write data file. " + error.__str__()))
        else:
            text = "No info"

        output_obj["text"] = text

        return output_obj


def print_output(output_str: str):
    sys.stdout.write(output_str)
    sys.stdout.flush()


def main():

    try:
        waybar_crypto = WaybarCrypto()

        obj = waybar_crypto.get_obj()

        obj_str = json.dumps(obj)
        print_output(obj_str)

    except WaybarError as error:
        print_output(error.__str__())


if __name__ == "__main__":
    main()
