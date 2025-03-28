from threading import Lock
from typing import Any, ClassVar, Self, cast


class Singleton:
    """
    Thread-safe singleton class. -- Prevents multiple instances of the same class.
    """

    _singleton_lock: ClassVar[Lock] = Lock()
    _singleton_instances: ClassVar[dict[Any, Any]] = {}

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        if cls not in Singleton._singleton_instances:
            with Singleton._singleton_lock:
                if cls not in Singleton._singleton_instances:
                    instance = super().__new__(cls)
                    Singleton._singleton_instances[cls] = instance
        return cast(Self, Singleton._singleton_instances[cls])
