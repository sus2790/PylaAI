"""Dependency injection container for managing application components."""
from typing import Any, Dict, Optional, TypeVar, Type, Callable

from exceptions.base import PylaError


T = TypeVar('T')


class ServiceNotFoundError(PylaError):
    """Raised when a requested service is not found in the container."""

    pass


class Container:
    """
    Simple dependency injection container.

    Manages service lifecycles and resolves dependencies.
    """

    _instance: Optional['Container'] = None

    def __new__(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services: Dict[str, Any] = {}
            cls._instance._factories: Dict[str, Callable] = {}
            cls._instance._singletons: Dict[str, Any] = {}
        return cls._instance

    def register(self, name: str, service: Any) -> None:
        """
        Register a service instance.

        Args:
            name: Service name
            service: Service instance
        """
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable) -> None:
        """
        Register a factory function for creating services.

        Args:
            name: Service name
            factory: Factory callable
        """
        self._factories[name] = factory

    def register_singleton(self, name: str, factory: Callable) -> None:
        """
        Register a singleton factory.

        The factory will be called once and the result cached.

        Args:
            name: Service name
            factory: Factory callable
        """
        self.register_factory(name, factory)

    def get(self, name: str) -> Any:
        """
        Get a service by name.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service is not found
        """
        # Check singletons
        if name in self._singletons:
            return self._singletons[name]

        # Check factories
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance
            return instance

        # Check direct registrations
        if name in self._services:
            return self._services[name]

        raise ServiceNotFoundError(f"Service '{name}' not found in container")

    def try_get(self, name: str) -> Optional[Any]:
        """
        Try to get a service, returning None if not found.

        Args:
            name: Service name

        Returns:
            Service instance or None
        """
        try:
            return self.get(name)
        except ServiceNotFoundError:
            return None

    def has(self, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service name

        Returns:
            True if service exists
        """
        return name in self._services or name in self._factories

    def clear(self) -> None:
        """Clear all registered services and singletons."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


def get_container() -> Container:
    """Get the global container instance."""
    return Container()
