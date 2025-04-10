# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from threading import Lock
from typing import Any, ClassVar, Self, cast


class Singleton:
    """Thread-safe singleton class. -- Prevents multiple instances of the same class."""

    _singleton_lock: ClassVar[Lock] = Lock()
    _singleton_instances: ClassVar[dict[Any, Any]] = {}

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        if cls not in Singleton._singleton_instances:
            with Singleton._singleton_lock:
                if cls not in Singleton._singleton_instances:
                    instance = super().__new__(cls)
                    Singleton._singleton_instances[cls] = instance
        return cast("Self", Singleton._singleton_instances[cls])
