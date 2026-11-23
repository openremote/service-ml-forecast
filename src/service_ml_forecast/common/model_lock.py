# Copyright 2026, OpenRemote Inc.
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

"""Fail-fast advisory locks for callers sharing a local model directory."""

import sys
from collections.abc import Iterator
from contextlib import contextmanager

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.config import DIRS


@contextmanager
def model_operation_lock(model_id: object, operation: str) -> Iterator[None]:
    """Release OS locks after exceptions or process death; keep stable lock files.

    The model directory must be a local filesystem with working advisory locks.
    Separate operation locks let model fitting run beside pinned prediction.
    """
    path = DIRS.ML_MODELS_DATA_DIR / f".model-{model_id}.{operation}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if sys.platform == "win32":
            import msvcrt

            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ResourceValidationError(f"Model {model_id} {operation} is already in progress") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ResourceValidationError(f"Model {model_id} {operation} is already in progress") from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
