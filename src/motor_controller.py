import logging
from gpiozero import Motor

logger = logging.getLogger(__name__)


class MotorController:
    """Thin wrapper around gpiozero.Motor for easier mocking in tests."""

    def __init__(self, forward_pin: int, backward_pin: int) -> None:
        self._motor = Motor(forward=forward_pin, backward=backward_pin)
        logger.debug("MotorController initialised (fwd=%d, bwd=%d)", forward_pin, backward_pin)

    def forward(self) -> None:
        logger.debug("Motor → forward")
        self._motor.forward()

    def backward(self) -> None:
        logger.debug("Motor → backward")
        self._motor.backward()

    def stop(self) -> None:
        logger.debug("Motor → stop")
        self._motor.stop()

    @property
    def is_active(self) -> bool:
        return self._motor.value != 0

    def close(self) -> None:
        self._motor.close()
