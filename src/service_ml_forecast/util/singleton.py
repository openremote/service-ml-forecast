from threading import Lock
from typing import Any, ClassVar, Generic, TypeVar, cast

T = TypeVar("T")


class Singleton(Generic[T]):
    """
    Thread-safe singleton class. -- Prevents multiple instances of the same class.
    """

    _singleton_lock: ClassVar[Lock] = Lock()
    _singleton_instances: ClassVar[dict[Any, Any]] = {}

    def __new__(cls, *args: object, **kwargs: object) -> Any:
        if cls not in Singleton._singleton_instances:
            with Singleton._singleton_lock:
                if cls not in Singleton._singleton_instances:
                    instance = super().__new__(cls)
                    Singleton._singleton_instances[cls] = instance
        return cast(T, Singleton._singleton_instances[cls])
