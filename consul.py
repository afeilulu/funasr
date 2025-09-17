import consul
import socket
# import sys

consul_host = '192.168.5.127'
consul_port = 32591
consul_token = 'fff17c8b-0ce2-4fe5-aab2-1cfae02febca'

# Global variables to store service information
service_id = None
consul_client = None

# Get current IP address
def get_local_ip():
    try:
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)
        print("Your Computer Name is:" + hostname)
        print("Your Computer IP Address is:" + IPAddr)
        return IPAddr
    except Exception:
        return '127.0.0.1'

# Register service with Consul
def register_service(service_name, port):
    global service_id, consul_client
    
    # Connect to Consul agent
    consul_client = consul.Consul(host=consul_host, port=consul_port, token=consul_token)
    
    # Generate a unique service ID
    service_id = f"{service_name}-{get_local_ip()}-{port}"
    
    # Create health check
    check = consul.Check.http(
        f'http://{get_local_ip()}:{port}/health',
        interval='10s',
        timeout='5s',
        deregister='30s'
    )
    
    # Register the service
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=get_local_ip(),
        port=port,
        check=check
    )
    
    print(f"Registered service {service_name} with ID {service_id}")
    return service_id

# Deregister service from Consul
def deregister_service():
    global service_id, consul_client
    if service_id and consul_client:
        # consul_client.agent.service.deregister(service_id)
        print(f"Deregistered service {service_id}")

# # Signal handler for graceful shutdown
# def handle_shutdown(signal, frame):
#     print("Shutting down gracefully...")
#     deregister_service()
#     sys.exit(0)
