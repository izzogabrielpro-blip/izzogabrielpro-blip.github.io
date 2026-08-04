import socket
import subprocess
import platform
import concurrent.futures
import re


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def get_subnet_prefix(ip):
    parts = ip.split(".")
    return ".".join(parts[:3]) + "."


def ping(ip):
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", "500", ip]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", ip]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def get_arp_table():
    system = platform.system().lower()
    cmd = ["arp", "-a"]
    output = subprocess.run(cmd, capture_output=True, text=True).stdout

    devices = {}
    if system == "windows":
        # Format Windows : "  192.168.1.10          d8-3b-bf-xx-xx-xx     dynamique"
        pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})")
    else:
        # Format Linux/macOS : "? (192.168.1.10) at d8:3b:bf:xx:xx:xx [ether] on eth0"
        pattern = re.compile(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]{17})")

    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            devices[match.group(1)] = match.group(2)
    return devices


def main():
    local_ip = get_local_ip()
    prefix = get_subnet_prefix(local_ip)

    print(f"Ton adresse IP     : {local_ip}")
    print(f"Sous-réseau scanné : {prefix}0/24")
    print("Scan en cours (ça prend 10-20 secondes)...\n")

    ips_to_scan = [f"{prefix}{i}" for i in range(1, 255)]

    # On ping toutes les adresses en parallèle pour aller vite
    active_ips = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(ping, ips_to_scan)
        for ip, is_alive in zip(ips_to_scan, results):
            if is_alive:
                active_ips.append(ip)

    arp_table = get_arp_table()

    print(f"{len(active_ips)} appareil(s) trouvé(s) :\n")
    print(f"{'ADRESSE IP':<18}{'ADRESSE MAC':<20}")
    print("-" * 38)
    for ip in sorted(active_ips, key=lambda x: int(x.split('.')[-1])):
        mac = arp_table.get(ip, "inconnue")
        marker = "  <- ton PC" if ip == local_ip else ""
        print(f"{ip:<18}{mac:<20}{marker}")


if __name__ == "__main__":
    main()