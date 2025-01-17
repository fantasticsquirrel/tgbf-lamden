import os
import json
import logging
import tgbf.constants as con

from tgbf.tgbot import TelegramBot
from argparse import ArgumentParser
from tgbf.singleton import SingleInstance
from tgbf.config import ConfigManager as Cfg
from logging.handlers import TimedRotatingFileHandler


class TGBF:

    def __init__(self):
        # Parse command line arguments
        self.args = self._parse_args()

        # Set up logging
        self._init_logger()

        # Run only one instance
        SingleInstance()

        # Read global config file
        self.cfg = Cfg(os.path.join(con.DIR_CFG, con.FILE_CFG))

        # Create Telegram bot
        self.tgb = TelegramBot(self.cfg, self._get_tokens())

    def _parse_args(self):
        """ Parse command line arguments """

        parser = ArgumentParser(description=con.DESCRIPTION)

        # Save logfile
        parser.add_argument(
            "-nolog",
            dest="savelog",
            action="store_false",
            help="don't save log-files",
            required=False,
            default=True)

        # Log level
        parser.add_argument(
            "-log",
            dest="loglevel",
            type=int,
            choices=[0, 10, 20, 30, 40, 50],
            help="disabled, debug, info, warning, error, critical",
            default=30,
            required=False)

        # Module log level
        parser.add_argument(
            "-mlog",
            dest="mloglevel",
            help="set log level for a module",
            default=None,
            required=False)

        # Bot token
        parser.add_argument(
            "-tkn",
            dest="token",
            help="set Telegram bot token",
            required=False,
            default=None)

        # Bot token via input
        parser.add_argument(
            "-input-tkn",
            dest="input_token",
            action="store_true",
            help="set Telegram bot token",
            required=False,
            default=False)

        return parser.parse_args()

    # Configure logging
    def _init_logger(self):
        """ Initialize the console logger and file logger """

        logger = logging.getLogger()
        logger.setLevel(self.args.loglevel)

        log_file = os.path.join(con.DIR_LOG, con.FILE_LOG)
        log_format = "%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(funcName)s() --> %(message)s"

        # Log to console
        console_log = logging.StreamHandler()
        console_log.setFormatter(logging.Formatter(log_format))
        console_log.setLevel(self.args.loglevel)

        logger.addHandler(console_log)

        # Save logs if enabled
        if self.args.savelog:
            # Create 'log' directory if not present
            log_path = os.path.dirname(log_file)
            if not os.path.exists(log_path):
                os.makedirs(log_path)

            # Log to file
            file_log = TimedRotatingFileHandler(
                log_file,
                when="H",
                encoding="utf-8")

            file_log.setFormatter(logging.Formatter(log_format))
            file_log.setLevel(self.args.loglevel)

            logger.addHandler(file_log)

        # Set log level for specified modules
        if self.args.mloglevel:
            for modlvl in self.args.mloglevel.split(","):
                module, loglvl = modlvl.split("=")
                logr = logging.getLogger(module)
                logr.setLevel(int(loglvl))

    # Read bot token from file
    def _get_tokens(self):
        """ Read Telegram bot token from config file or command line or input """

        if self.args.input_token:
            return input("Enter Telegram Bot Token: ")
        if self.args.token:
            return self.args.token

        token_path = os.path.join(con.DIR_CFG, con.FILE_TKN)

        tokens = dict()

        try:
            if os.path.isfile(token_path):
                with open(token_path, "r", encoding="utf8") as file:
                    json_content = json.load(file)

                    tokens["telegram"] = json_content["telegram"]
                    tokens["bot-pk"] = json_content["bot-pk"]

                    return tokens
            else:
                exit(f"ERROR: No token file '{con.FILE_TKN}' found at '{token_path}'")
        except KeyError as e:
            cls_name = f"Class: {type(self).__name__}"
            logging.error(f"{repr(e)} - {cls_name}")
            exit("ERROR: Can't read bot token")

    def start(self):

        # Start bot in polling or webhook mode
        if self.cfg.get("webhook", "use_webhook"):
            self.tgb.bot_start_webhook()
        else:
            self.tgb.bot_start_polling()

        # Start web interface
        self.tgb.start_web()

        # Go in idle mode
        self.tgb.bot_idle()
