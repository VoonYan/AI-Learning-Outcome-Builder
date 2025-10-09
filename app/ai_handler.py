"""
AI Configuration Manager module for thread-safe configuration handling.

This module provides a thread-safe configuration manager for AI parameters
used in the learning outcome evaluation system. It handles reading, updating,
and resetting configuration parameters while preventing race conditions in
Flask's multi-threaded environment.
"""

import json
import threading


class ConfigManager:
    """
    Thread-safe configuration manager for AI parameters.

    This manager handles the AIConfig.json file that contains:
    - Available AI models and selected model
    - API keys for AI services
    - Bloom's Taxonomy verb lists for each level
    - Credit point ranges for learning outcome counts
    - Banned words that shouldn't appear in outcomes

    The manager uses thread locking to prevent race conditions when multiple
    requests try to read or modify the configuration simultaneously.

    Attributes:
        path: File path to the configuration JSON file
        lock: Threading lock for synchronization
        _AIParams: Private dictionary storing current configuration
    """

    def __init__(self, path):
        """
        Initialise the configuration manager.

        Args:
            path: Path to the AIConfig.json file
        """
        self.path = path
        self.lock = threading.Lock()
        self._AIParams = self._retrieveAIParams()

    def _retrieveAIParams(self):
        """
        Load AI parameters from the configuration file.

        Attempts to load from the specified path first, falls back to
        default configuration if the file doesn't exist or is corrupted.

        Returns:
            Dictionary containing AI configuration parameters
        """
        try:
            # Try to load the main configuration file
            with open(self.path) as file:
                return json.load(file)
        except:
            # Fall back to default configuration if main file fails
            # This ensures the application can still run with defaults
            with open('app/AIConfigDefault.json') as file:
                return json.load(file)

    def getCurrentParams(self):
        """
        Get a thread-safe copy of current configuration parameters.

        Uses locking to ensure consistent reads even when other threads
        are modifying the configuration.

        Returns:
            Dictionary copy of current AI parameters
        """
        with self.lock:
            # Return a copy to prevent external modifications
            return self._AIParams.copy()

    def replaceCurrentParameter(self, key, newValue):
        """
        Update a single configuration parameter thread-safely.

        Updates both the in-memory configuration and persists to disk.
        Uses locking to ensure atomic updates.

        Args:
            key: Configuration parameter key to update
            newValue: New value for the parameter
        """
        with self.lock:
            # Update in-memory configuration
            self._AIParams.update({key: newValue})

            # Persist changes to disk
            with open(self.path, 'w') as file:
                json.dump(self._AIParams, file)

    def resetParamsToDefault(self):
        """
        Reset all parameters to default values.

        Loads the default configuration from AIConfigDefault.json and
        replaces all current settings. Used by admin reset functionality.

        Note: This doesn't persist to disk automatically - the updated
        configuration remains in memory until explicitly saved.
        """
        # Load default configuration
        with open('app/AIConfigDefault.json') as file:
            self._AIParams = json.load(file)