from flask import Flask, render_template, jsonify
import os
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
import re
from typing import List, Dict
from dataclasses import dataclass
import logging
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

vpn = Flask(__name__)

@dataclass
class FortiGateConfig:
    device_type: str
    ip: str
    username: str
    password: str
    vdom: str = "VPN-CORP"

class FortiGateVPNMonitor:
    def __init__(self, config: FortiGateConfig):
        self.config = config
        self.vpn_names: List[str] = []
        self.device_params = {
            'device_type': config.device_type,
            'ip': config.ip,
            'username': config.username,
            'password': config.password,
        }
        self.prompt_pattern = r'.*.*'
        self.last_check_time = None

    def connect(self) -> ConnectHandler:
        """Establish connection to FortiGate device"""
        try:
            connection = ConnectHandler(**self.device_params)
            connection.send_command('config vdom', expect_string=self.prompt_pattern)
            connection.send_command(f'edit {self.config.vdom}', expect_string=self.prompt_pattern)
            return connection
        except NetmikoTimeoutException:
            logger.error(f"Timeout while connecting to {self.config.ip}")
            raise
        except NetmikoAuthenticationException:
            logger.error("Authentication failed")
            raise

    def get_vpn_status(self) -> Dict:
        """Get complete VPN status including names and Phase 1 status"""
        try:
            with self.connect() as ssh_client:

                vpn_summary = ssh_client.send_command('get vpn ipsec tunnel summary')
                pattern = r'[\'].*.*[\']'
                vpn_names_list = re.findall(pattern, vpn_summary)
                self.vpn_names = [name.strip('"\'') for name in vpn_names_list]


                status_dict = {}
                for vpn_name in self.vpn_names:
                    status = ssh_client.send_command(
                        f'diagnose vpn ike gateway list name {vpn_name}'
                    )
                    is_up = 'status: established' in status
                    status_dict[vpn_name] = {
                        'status': 'UP' if is_up else 'DOWN',
                        'is_up': is_up
                    }

                self.last_check_time = datetime.now()
                return {
                    'vpn_statuses': status_dict,
                    'last_check': self.last_check_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_vpns': len(self.vpn_names),
                    'vpns_up': sum(1 for vpn in status_dict.values() if vpn['is_up']),
                }

        except Exception as e:
            logger.error(f"Error getting VPN status: {str(e)}")
            raise


try:
    config = FortiGateConfig(
        device_type=os.environ['DEVTYPE'],
        ip=os.environ['FORTIIP'],
        username=os.environ['FORTIUSER'],
        password=os.environ['FORTIPASS']
    )
    monitor = FortiGateVPNMonitor(config)
except KeyError as e:
    logger.error(f"Missing environment variable: {str(e)}")
    monitor = None

@vpn.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

@vpn.route('/api/vpn-status')
def vpn_status():
    """API endpoint for VPN status"""
    if not monitor:
        return jsonify({'error': 'FortiGate configuration not properly initialized'}), 500

    try:
        status = monitor.get_vpn_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    vpn.run(debug=True, host="0.0.0.0")
