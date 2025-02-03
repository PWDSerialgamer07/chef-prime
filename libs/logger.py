import rich
from rich import print as log
from rich.console import Console
import datetime
import os
import traceback
from traceback import FrameSummary


class Logger:
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "ERROR": 40
    }

    def __init__(self, log_file_name: str = "log.txt", log_dir: str = "logs", level: str = "DEBUG") -> None:
        """
        Initializes the Logger object with the specified file name, directory, and log level.

        Parameters:
        log_file_name (str): The name of the log file (default is "log.txt").
        log_dir (str): The directory where the log file will be stored (default is "logs").
        level (str): The logging level (default is "DEBUG"). Can be one of: "DEBUG", "INFO", "WARN", "ERROR".
        """
        self.console = Console()
        self.log_file_name = log_file_name
        self.log_directory = log_dir
        self.level = level
        os.makedirs(self.log_directory, exist_ok=True)
        self.log_file = self.LogFile(self)  # Initialize the LogFile
        self.log_print = self.LogPrint(self)

    def get_current_time(self) -> str:
        """
        Returns the current time as a formatted string.

        Returns:
        str: The current time in "YYYY-MM-DD|HH:MM:SS" format.
        """
        return datetime.datetime.now().strftime("%Y-%m-%d|%H:%M:%S")

    def should_log(self, log_type: str) -> bool:
        """
        Determines if the given log message should be logged based on the current logging level.

        Parameters:
        log_type (str): The type of the log message (e.g., "DEBUG", "INFO", "WARN", "ERROR").

        Returns:
        bool: True if the message should be logged, False otherwise.
        """
        return self.LEVELS[log_type] >= self.LEVELS[self.level]

    class LogFile:
        def __init__(self, parent: "Logger") -> None:
            """
            Initializes the LogFile object and opens the log file for appending.

            Parameters:
            parent (Logger): The parent Logger object.
            """
            self.parent = parent
            self.log_file_path = os.path.join(
                self.parent.log_directory, self.parent.log_file_name)
            self.file = open(self.log_file_path, "a+")

        def log(self, message: str, log_type: str, tb: FrameSummary = None) -> None:
            """
            Writes the log entry to the file if the current log level allows it.

            Parameters:
            message (str): The log message.
            log_type (str): The type of the log message (e.g., "DEBUG", "INFO", "WARN", "ERROR").
            """
            if not self.parent.should_log(log_type):
                return
            current_time = self.parent.get_current_time()
            if tb:
                self.file.write(
                    f"{current_time} [{log_type}] {message} (File: {tb.filename}, Line: {tb.lineno})\n")
            else:
                self.file.write(
                    f"{current_time} [{log_type}] {message}\n")
            self.file.flush()

        def close(self) -> None:
            """
            Closes the log file when the logger is no longer needed.
            """
            self.file.close()

        def __del__(self) -> None:
            """
            Ensures the log file is closed when the LogFile object is destroyed.
            """
            self.close()

    class LogPrint:
        def __init__(self, parent: "Logger") -> None:
            """
            Initializes the LogPrint object.

            Parameters:
            parent (Logger): The parent Logger object.
            """
            self.parent = parent

        def error(self, message: str) -> None:
            """
            Logs an error message, prints it to the console, and writes it to the log file.

            Parameters:
            message (str): The error message to log.
            """
            if not self.parent.should_log("ERROR"):
                return
            current_time = self.parent.get_current_time()
            tb = traceback.extract_stack()[-2]  # Get the caller's line info
            log(f"[blue]{current_time}[/blue] [red][bold][ERROR][/bold] {message}(File:{tb.filename}, Line:{tb.lineno}[/red]")
            self.parent.log_file.log(message, "ERROR", tb)

        def info(self, message: str) -> None:
            """
            Logs an info message, prints it to the console, and writes it to the log file.

            Parameters:
            message (str): The info message to log.
            """
            if not self.parent.should_log("INFO"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [green][bold][INFO][/bold] {message}[/green]")
            self.parent.log_file.log(message, "INFO")

        def warn(self, message: str) -> None:
            """
            Logs a warning message, prints it to the console, and writes it to the log file.

            Parameters:
            message (str): The warning message to log.
            """
            if not self.parent.should_log("WARN"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [yellow][bold][WARN][/bold] {message}[/yellow]")
            self.parent.log_file.log(message, "WARN")

        def debug(self, message: str) -> None:
            """
            Logs a debug message, prints it to the console, and writes it to the log file.

            Parameters:
            message (str): The debug message to log.
            """
            if not self.parent.should_log("DEBUG"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [cyan][bold][DEBUG][/bold] {message}[/cyan]")
            self.parent.log_file.log(message, "DEBUG")
