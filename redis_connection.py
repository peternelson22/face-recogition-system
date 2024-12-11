# redis_connection.py
import redis
import os
import logging


class RedisConnectionManager:
    """
    A centralized Redis connection manager to handle Redis connections
    across multiple modules with consistent error handling and logging.
    """

    _instance = None

    def __new__(cls, redis_host='localhost', redis_port=6379, images_path='static/uploads'):
        """
        Singleton implementation to ensure only one Redis connection is created.

        Args:
            redis_host (str): Redis server host
            redis_port (int): Redis server port
            images_path (str): Path for storing images
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(redis_host, redis_port, images_path)
        return cls._instance

    def _initialize(self, redis_host, redis_port, images_path):
        """
        Initialize the Redis connection and perform setup tasks.

        Args:
            redis_host (str): Redis server host
            redis_port (int): Redis server port
            images_path (str): Path for storing images
        """
        # Configure logging
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # Store configuration parameters
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.images_path = images_path

        # Attempt Redis connection
        self.redis_client = self._establish_redis_connection()

        # Ensure images directory exists
        self._create_images_directory()

    def _establish_redis_connection(self):
        """
        Establish a Redis connection with error handling.

        Returns:
            redis.Redis or None: Redis client connection or None if connection fails
        """
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )

            # Verify connection
            client.ping()
            self.logger.info("Redis connection established successfully.")
            return client

        except redis.ConnectionError as e:
            self.logger.error(f"Redis connection error: {e}")
            return None

    def _create_images_directory(self):
        """
        Create the images directory if it doesn't exist.
        """
        try:
            os.makedirs(self.images_path, exist_ok=True)
            self.logger.info(f"Images directory created/verified: {self.images_path}")
        except Exception as e:
            self.logger.error(f"Error creating images directory: {e}")

    def get_redis_client(self):
        """
        Get the Redis client connection.

        Returns:
            redis.Redis or None: Redis client connection
        """
        if not self.redis_client:
            self.logger.warning("Attempting to reconnect to Redis...")
            self.redis_client = self._establish_redis_connection()
        return self.redis_client

    def is_connected(self):
        """
        Check if Redis connection is active.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.redis_client is not None