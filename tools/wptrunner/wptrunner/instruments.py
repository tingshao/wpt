import time
import threading
from Queue import Queue

"""Instrumentation for measuring high-level time spent on various tasks inside the runner.

This is lower fidelity than an actual profile, but allows custom data to be considered,
so that we can see the time spent in specific tests and test directories


Instruments are intended to be used as context managers with the return value of __enter__
containing the user-facing API e.g.

with Instrument(*args) as recording:
    recording.set(["init"])
    do_init()
    recording.pause()
    for thread in test_threads:
       thread.start(recording, *args)
    for thread in test_threads:
       thread.join()
    recording.set(["teardown"])
    do_teardown()
"""

class NullInstrument(object):
    def set(self, stack):
        """Set the current task to stack

        :param stack: A list of strings defining the current task.
                      These are interpreted like a stack trace so that ["foo"] and
                      ["foo", "bar"] both show up as decendents of "foo"
        """
        pass

    def pause(self):
        """Stop recording a task on the current thread. This is useful if the thread
        is purely waiting on the results of other threads"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return


class InstrumentWriter(object):
    def __init__(self, queue):
        self.queue = queue

    def set(self, stack):
        stack.insert(0, threading.current_thread().name)
        self.queue.put(("set", threading.current_thread().ident, time.time(), stack))

    def pause(self):
        self.queue.put(("pause", threading.current_thread().ident, time.time(), None))

    def _check_stack(self, stack):
        assert isinstance(stack, (tuple, list))
        return [item.replace(" ", "_") for item in stack]


class Instrument(object):
    """Instrument that collects data from multiple threads and sums the time in each
    thread. The output is in the format required by flamegraph.pl to enable visulisation
    of the time spent in each task."""
    def __init__(self, file_path):
        self.path = file_path
        self.queue = None
        self.current = None
        self.start_time = None
        self.thread = None

    def get_writer(self):
        return InstrumentWriter(self.queue)

    def __enter__(self):
        assert self.thread is None
        assert self.queue is None
        self.queue = Queue()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.get_writer()

    def __exit__(self, *args, **kwargs):
        self.queue.put(("stop", None, time.time(), None))
        self.thread.join()
        self.thread = None
        self.queue = None

    def run(self):
        with open(self.path, "w") as f:
            thread_data = {}
            while True:
                command, thread, t, stack = self.queue.get()
                items = []
                if command == "stop":
                    items = thread_data.values()
                else:
                    if thread in thread_data:
                        items.append(thread_data.pop(thread))
                for item in items:
                    f.write("%s %d\n" % (";".join(item[0]), int(1000 * (t - item[1]))))
                if command == "set":
                    thread_data[thread] = (stack, t)
                elif command == "stop":
                    break
