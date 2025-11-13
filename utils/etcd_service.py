import asyncio
import json
import logging
import os
import threading
from typing import Optional, Dict, Any
from datetime import datetime
import etcd3

logger = logging.getLogger(__name__)

class EtcdService:
    def __init__(self, host: str = None, port: int = None):
        # Read from environment variable ETCD_URL
        etcd_url = os.getenv("ETCD_URL", "http://localhost:2379")
        
        # Parse the URL
        if etcd_url.startswith("http://"):
            etcd_url = etcd_url[7:]  # Remove http:// prefix
        
        if ":" in etcd_url:
            host, port_str = etcd_url.split(":")
            port = int(port_str)
        else:
            host = etcd_url
            port = 2379
            
        self.client = etcd3.client(host=host, port=port)
        self.service_prefix = "/services/"
        self.lease_ttl = 30  # 30 seconds
        self.active_leases = {}  # Track active leases
        logger.info(f"🔗 etcd client initialized: {host}:{port}")

    def register_service(self, service_name: str, service_id: str, host: str, port: int):
        """Register a service with etcd (synchronous)"""
        try:
            # Create a lease for automatic expiration
            lease = self.client.lease(ttl=self.lease_ttl)
            
            service_key = f"{self.service_prefix}{service_name}/{service_id}"
            service_data = {
                "name": service_name,
                "id": service_id,
                "address": host,
                "port": port,
                "registered_at": datetime.utcnow().isoformat()
            }
            
            # Store service info with lease
            self.client.put(service_key, json.dumps(service_data), lease=lease)
            
            # Store lease for later management
            self.active_leases[service_key] = lease
            
            # Start keep-alive in a background thread
            keep_alive_thread = threading.Thread(
                target=self._keep_lease_alive_sync,
                args=(lease, service_key),
                daemon=True
            )
            keep_alive_thread.start()
            
            logger.info(f"✅ Registered {service_name} with etcd")
        except Exception as e:
            logger.error(f"❌ Failed to register with etcd: {e}")
            raise

    def _keep_lease_alive_sync(self, lease, service_key: str):
        """Keep the lease alive in a background thread (synchronous)"""
        import time
        while service_key in self.active_leases:
            try:
                # Refresh the lease
                lease.refresh()
                time.sleep(self.lease_ttl // 2)  # Refresh halfway through TTL
            except Exception as e:
                logger.error(f"Failed to refresh lease for {service_key}: {e}")
                # Remove from active leases on failure
                self.active_leases.pop(service_key, None)
                break

    async def register_service_async(self, service_name: str, service_id: str, host: str, port: int):
        """Register a service with etcd (async wrapper)"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            self.register_service, 
            service_name, 
            service_id, 
            host, 
            port
        )

    async def _keep_lease_alive(self, lease, service_key: str):
        """Keep the lease alive to prevent service expiration (async version)"""
        while service_key in self.active_leases:
            try:
                # Run lease refresh in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lease.refresh)
                await asyncio.sleep(self.lease_ttl // 2)  # Refresh halfway through TTL
            except Exception as e:
                logger.error(f"Failed to refresh lease for {service_key}: {e}")
                # Remove from active leases on failure
                self.active_leases.pop(service_key, None)
                break

    def deregister_service(self, service_name: str, service_id: str):
        """Deregister a service from etcd (synchronous)"""
        try:
            service_key = f"{self.service_prefix}{service_name}/{service_id}"
            
            # Stop keeping the lease alive
            lease = self.active_leases.pop(service_key, None)
            if lease:
                try:
                    lease.revoke()
                except Exception as e:
                    logger.warning(f"Failed to revoke lease: {e}")
            
            # Delete the key
            self.client.delete(service_key)
            logger.info(f"✅ Deregistered {service_name} from etcd")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from etcd: {e}")

    async def deregister_service_async(self, service_name: str, service_id: str):
        """Deregister a service from etcd (async wrapper)"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            self.deregister_service, 
            service_name, 
            service_id
        )

    def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover a service by name (synchronous)"""
        try:
            prefix = f"{self.service_prefix}{service_name}/"
            
            # Get all services with this prefix
            services = []
            for value, metadata in self.client.get_prefix(prefix):
                if value:
                    service_data = json.loads(value.decode('utf-8'))
                    services.append(service_data)
            
            if services:
                # Return first available service (can add load balancing here)
                return services[0]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to discover service {service_name}: {e}")
            return None

    async def discover_service_async(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover a service by name (async wrapper)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.discover_service, service_name)

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the full URL for a service"""
        service = self.discover_service(service_name)
        if service:
            return f"http://{service['address']}:{service['port']}"
        return None

    async def get_service_url_async(self, service_name: str) -> Optional[str]:
        """Get the full URL for a service (async)"""
        service = await self.discover_service_async(service_name)
        if service:
            return f"http://{service['address']}:{service['port']}"
        return None

    def close(self):
        """Close the etcd client and cleanup"""
        # Revoke all active leases
        for service_key, lease in list(self.active_leases.items()):
            try:
                lease.revoke()
            except Exception as e:
                logger.warning(f"Failed to revoke lease for {service_key}: {e}")
        
        self.active_leases.clear()
        self.client.close()
        logger.info("🔒 etcd client closed")

# Global instance
etcd_service = EtcdService()