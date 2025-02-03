class queue:
    """
    Queue class for storing video URLs and timestamps.
    Might be overengineered for nothing but eh
    """

    def __init__(self):
        self.queue = []

    def append(self, url, timestamp=0):
        """
        Adds an element to the queue.
        IMPORTANT: Timestamps are stored in seconds like "360" for 5 minutes instead of "00:05:00"
        """
        self.queue.append({"url": url, "timestamp": timestamp})

    def pop(self):
        """Removes and returns the first element from the queue."""
        if self.queue:
            return self.queue.pop(0)
        else:
            return None

    def display(self):
        """Returns the current queue as a formatted string."""
        if self.queue:
            # Create the formatted string for each video
            queue_str = "\n".join(
                [f"{index + 1}: URL: {video['url']}, Timestamp: {video['timestamp']}"
                 for index, video in enumerate(self.queue)])
            return queue_str
        else:
            return "Queue is empty"

    def is_empty(self):
        """To check if the queue is empty
        Returns True if the queue is empty, False if it contains something
        """
        return not self.queue


url_queue = queue()

url_queue.append("https://example.com/video2")
url_queue.append("https://example.com/video3")

print(url_queue.display())
