import os
import json

from waybar_crypto import WaybarCrypto


class TestWaybarCrypto:
    """Tests for the WaybarCrypto."""

    def test_get_json(self):
        # Get the absolute path of this script
        abs_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = f"{abs_dir}/../config.ini"

        waybar_crypto = WaybarCrypto()

        result_json = waybar_crypto.get_obj()
        assert isinstance(result_json, dict)

        assert result_json["text"] and len(result_json["text"]) > 0
        assert result_json["class"] == "crypto"
