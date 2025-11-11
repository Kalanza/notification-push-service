"""
Circuit Breaker pattern implementation.
Prevents cascading failures when push provider (FCM) fails repeatedly.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests fail immediately
- HALF_OPEN: Testing if service recovered
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    Args:
        max_failures: Number of failures before opening circuit
        reset_timeout: Seconds to wait before attempting reset
        half_open_max_calls: Max calls to test in HALF_OPEN state
    """
    
    def __init__(
        self,
        max_failures: int = 3,
        reset_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime = None
        self.half_open_calls = 0
        
        logger.info(
            f"Circuit breaker initialized: max_failures={max_failures}, "
            f"reset_timeout={reset_timeout}s"
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result from function
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from the function
        """
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                logger.warning(
                    f"Circuit breaker is OPEN. Failing fast. "
                    f"Reset in {self._time_until_reset()}s"
                )
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        # HALF_OPEN: Limit number of test calls
        if self.state == "HALF_OPEN":
            if self.half_open_calls >= self.half_open_max_calls:
                logger.warning("Circuit breaker HALF_OPEN call limit reached")
                raise CircuitBreakerOpenError(
                    "Circuit breaker is HALF_OPEN with max test calls reached"
                )
            self.half_open_calls += 1
        
        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self) -> None:
        """Handle successful call"""
        self.success_count += 1
        
        if self.state == "HALF_OPEN":
            # Successful test call, close circuit
            logger.info(
                f"✅ Circuit breaker test successful. Closing circuit. "
                f"Success count: {self.success_count}"
            )
            self._transition_to_closed()
        elif self.state == "CLOSED":
            # Reset failure count on success
            if self.failure_count > 0:
                logger.info(
                    f"Circuit breaker recovered. Resetting failure count from {self.failure_count}"
                )
                self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"⚠️ Circuit breaker failure {self.failure_count}/{self.max_failures}. "
            f"State: {self.state}"
        )
        
        if self.state == "HALF_OPEN":
            # Test failed, reopen circuit
            logger.error("Circuit breaker test failed. Reopening circuit.")
            self._transition_to_open()
        elif self.state == "CLOSED":
            # Check if threshold exceeded
            if self.failure_count >= self.max_failures:
                logger.error(
                    f"❌ Circuit breaker threshold exceeded ({self.failure_count} failures). "
                    f"Opening circuit for {self.reset_timeout}s"
                )
                self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.reset_timeout
    
    def _time_until_reset(self) -> int:
        """Calculate seconds until reset attempt"""
        if self.last_failure_time is None:
            return 0
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        remaining = max(0, self.reset_timeout - elapsed)
        return int(remaining)
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        self.state = "OPEN"
        self.half_open_calls = 0
        logger.error(
            f"🔴 Circuit breaker OPEN. Will attempt reset after {self.reset_timeout}s"
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        self.state = "HALF_OPEN"
        self.half_open_calls = 0
        logger.info(
            f"🟡 Circuit breaker HALF_OPEN. Testing with {self.half_open_max_calls} call(s)"
        )
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        self.state = "CLOSED"
        self.failure_count = 0
        self.half_open_calls = 0
        logger.info("🟢 Circuit breaker CLOSED. Normal operation resumed")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "max_failures": self.max_failures,
            "reset_timeout": self.reset_timeout,
            "time_until_reset": self._time_until_reset() if self.state == "OPEN" else 0
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker (admin function)"""
        logger.info("Circuit breaker manually reset")
        self._transition_to_closed()
