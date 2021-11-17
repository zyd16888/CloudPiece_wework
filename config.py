# python3
# -*- coding: utf-8 -*-
import configparser


class Configure:
    def __init__(self, config_file):
        self.config_file = config_file
        self.conf = configparser.ConfigParser()
        self.conf.read(self.config_file, encoding="utf-8")

    def get_config(self, section, key):
        if self.conf.has_option(section, key):
            if self.conf.get(section, key) == "":
                return None
            else:
                return (
                    self.conf.get(section, key)
                        .replace("'", "")
                        .replace('"', "")
                        .lstrip()
                        .rstrip()
                )
        else:
            return None

    def set_config(self, section, key, value):
        if self.conf.has_section(section):
            self.conf.set(section, key, value)
        else:
            self.conf.add_section(section)
            self.conf.set(section, key, value)
        with open("config.ini", "w+", encoding="utf-8") as f:
            self.conf.write(f)


if __name__ == "__main__":
    config = Configure("config.ini")

