def ConfigLog(log_path, timezone="America/Sao_Paulo", name=__name__):
    import datetime
    import pytz
    import logging
    import os
    import sys

    if log_path != "" and not os.path.exists(log_path):
        os.makedirs(log_path)

    tz = pytz.timezone(timezone)

    def except_handler(type, value, tb):
        logger.exception("Exception: {0}".format(str(value)))

    def timetz(*args):
        return datetime.datetime.now(tz).timetuple()

    logging.Formatter.converter = timetz

    logging.basicConfig(
        filename=log_path,
        filemode="w" if name == "__main__" else "a",
        format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%d/%b/%Y %H:%M:%S",
    )

    logger = logging.getLogger(name)

    logger.setLevel(logging.INFO)

    sys.excepthook = except_handler

    return logger

logger = ConfigLog(log_path="projects/b/out.log")