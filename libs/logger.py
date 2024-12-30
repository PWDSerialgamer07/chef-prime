import rich
from rich import print as log
from rich.console import Console
import datetime
import os


class Logger:
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "ERROR": 40
    }

    def __init__(self, log_file_name="log.txt", log_dir="logs", level="DEBUG"):
        self.console = Console()
        self.log_file_name = log_file_name
        self.log_directory = log_dir
        self.level = level
        os.makedirs(self.log_directory, exist_ok=True)
        self.log_file = self.LogFile(self)  # Initialize the LogFile
        self.log_print = self.LogPrint(self)

    def get_current_time(self):
        """Returns the current time as a formatted string."""
        return datetime.datetime.now().strftime("%Y-%m-%d|%H:%M:%S")

    def should_log(self, log_type):
        """Returns True if the message should be logged based on the current level."""
        return self.LEVELS[log_type] >= self.LEVELS[self.level]

    class LogFile:
        def __init__(self, parent):
            self.parent = parent
            # Open the file once during initialization
            self.log_file_path = os.path.join(
                self.parent.log_directory, self.parent.log_file_name)
            self.file = open(self.log_file_path, "a+")

        def log(self, message, log_type):
            """Write the log entry if the level allows it."""
            if not self.parent.should_log(log_type):
                return
            current_time = self.parent.get_current_time()
            # Write the log entry
            self.file.write(f"{current_time} [{log_type}] {message}\n")
            self.file.flush()  # Manually flush the buffer to ensure it's written to disk

        def close(self):
            """Close the log file when the logger is no longer needed."""
            self.file.close()

        def __del__(self):
            """Ensure the file is closed when the object is destroyed."""
            self.close()

    class LogPrint:
        def __init__(self, parent):
            self.parent = parent

        def error(self, message):
            if not self.parent.should_log("ERROR"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [red][bold][ERROR][/bold] {message}[/red]")
            self.parent.log_file.log(message, "ERROR")

        def info(self, message):
            if not self.parent.should_log("INFO"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [green][bold][INFO][/bold] {message}[/green]")
            self.parent.log_file.log(message, "INFO")

        def warn(self, message):
            if not self.parent.should_log("WARN"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [yellow][bold][WARN][/bold] {message}[/yellow]")
            self.parent.log_file.log(message, "WARN")

        def debug(self, message):
            if not self.parent.should_log("DEBUG"):
                return
            current_time = self.parent.get_current_time()
            log(f"[blue]{current_time}[/blue] [cyan][bold][DEBUG][/bold] {message}[/cyan]")
            self.parent.log_file.log(message, "DEBUG")


# Example usage:
logger = Logger(log_file_name="logs.txt", log_dir="my_logs", level="INFO")

# Won't print because level is INFO
logger.log_print.debug("This is a debug message.")
logger.log_print.info("This is an info message.")   # Will print
logger.log_print.warn("This is a warning message.")  # Will print
logger.log_print.error("This is an error message.")  # Will print

# Close the log file manually when done
logger.log_file.close()
